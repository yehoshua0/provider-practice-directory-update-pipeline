# Pipeline Architecture Design

**Date:** 2026-06-17  
**Competition:** HealthLynked — Provider & Practice Directory Update Pipeline  
**Submission track:** Option C (Hybrid: prototype + architecture proposal)  
**Status:** Approved

---

## 1. Components & Boundaries

Seven discrete units. Each has one job. Communication via typed `PipelineState` — no shared globals, no side channels.

```
┌─────────────────────────────────────────────────────┐
│                   Orchestrator                      │
│              (LangGraph graph runner)               │
└──────────┬──────────────────────────────────────────┘
           │  PipelineState flows through each node
           ▼
┌──────────────────┐
│ StalenessDetector│  Selects records due for re-verification
└────────┬─────────┘  (last_verified_date + age threshold)
         ▼
┌──────────────────┐
│   FetchAgent     │  Queries NPPES → CMS → State Board → Website
└────────┬─────────┘  Returns raw source payloads, no interpretation
         ▼
┌──────────────────┐
│ NormalizeAgent   │  Canonical addresses (USPS), E.164 phones,
└────────┬─────────┘  NPI taxonomy → specialty strings, name casing
         ▼
┌──────────────────┐
│ CompareAgent     │  Field-level diff: old_value vs new_value per source
└────────┬─────────┘  Detects conflicts between sources
         ▼
┌──────────────────┐
│  ScoringAgent    │  Confidence = Σ(weight_i × match_i) / Σ(weight_i)
└────────┬─────────┘  Source weights: NPI=1.0, CMS=0.85, Board=0.80, Web=0.65
         ▼
┌──────────────────┐
│  RouterAgent     │  ≥0.85 → auto_update | 0.60–0.84 → human_review
└────────┬─────────┘  <0.60 → no_change
         ▼
┌──────────────────┐
│   AuditLogger    │  Writes structured JSON to SQLite audit_log table
└──────────────────┘  Every decision traceable: field, old, new, score, sources
```

LLM (Claude Haiku) used only in `NormalizeAgent` for unstructured website parsing, and only after Scrapling and BS4 both fail to extract structured contact data. Rule-based everywhere else.

`pipeline/sources/` only fetches raw data — no interpretation. `pipeline/agents/` does all reasoning. Swapping or adding a source never touches agent logic.

---

## 2. Data Model & PipelineState

Single typed state object flows through all LangGraph nodes.

```python
class ProviderRecord(TypedDict):
    provider_id: str
    npi: str
    provider_name: str
    specialty: str
    practice_name: str
    address: str
    phone: str
    website: str
    active: bool
    last_verified_date: str  # ISO 8601

class FieldDiff(TypedDict):
    field: str
    old_value: str
    new_value: str
    confidence_score: float
    supporting_sources: list[str]

class PipelineState(TypedDict):
    record: ProviderRecord                  # original DB record
    raw_sources: dict[str, dict]            # source_name → raw payload
    normalized: dict[str, ProviderRecord]   # source_name → normalized record
    diffs: list[FieldDiff]                  # field-level changes detected
    overall_confidence: float
    recommended_action: Literal["auto_update", "human_review", "no_change"]
    reason: str
    error: str | None                       # set if any node fails
```

### SQLite Schema — 3 tables

```sql
CREATE TABLE providers (
    provider_id TEXT PRIMARY KEY,
    npi TEXT UNIQUE,
    provider_name TEXT,
    specialty TEXT,
    practice_name TEXT,
    address TEXT,
    phone TEXT,
    website TEXT,
    active INTEGER,
    last_verified_date TEXT
);

CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id TEXT,
    run_at TEXT,
    field TEXT,
    old_value TEXT,
    new_value TEXT,
    confidence_score REAL,
    supporting_sources TEXT,  -- JSON array
    action TEXT,
    reason TEXT
);

CREATE TABLE review_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id TEXT,
    queued_at TEXT,
    overall_confidence REAL,
    diffs TEXT,               -- JSON
    reason TEXT,
    resolved INTEGER DEFAULT 0
);
```

DB updates are transactional — full record update + audit log entry commit together or neither does.

---

## 3. Data Sources & Fetch Strategy

FetchAgent queries sources in priority order. Each source failure is isolated — one dead source does not abort the run.

| Priority | Source | Cost | API / Method |
|----------|--------|------|--------------|
| 1 | NPPES NPI Registry | Free | `GET https://npiregistry.cms.hhs.gov/api/?number={npi}&version=2.1` |
| 2 | CMS Medicare Provider | Free | `GET https://data.cms.gov/provider-data/api/1/datastore/query/mj5m-pzi6/0?conditions[0][property]=npi&conditions[0][value]={npi}` |
| 3 | State Medical Board | Free | HTML scrape (FL for MVP, extendable per-state module) |
| 4 | Practice Website | Free + ~$0.001 | Scrapling → BS4 → Claude Haiku |

### Website Fetch Chain

```
Scrapling (JS rendering + auto-adapt DOM)
    → structured contact block found? YES → done
    → NO
BS4 fallback (static HTML parse)
    → address/phone found? YES → done
    → NO
Claude Haiku (raw page text extraction)
    → extract address/phone from unstructured content
```

Scrapling handles JS-rendered pages (Wix, Squarespace, React) and auto-adapts to DOM changes after website redesigns. BS4 handles simple static pages. Haiku is last resort only — estimated hit rate ~5% of records.

### Source Weights

```python
SOURCE_WEIGHTS = {
    "nppes":   1.00,
    "cms":     0.85,
    "board":   0.80,
    "website": 0.65,
}
```

---

## 4. Confidence Scoring & Routing

### Scoring Formula

```python
def score_field(field: str, diffs_by_source: dict[str, str], existing_value: str) -> FieldDiff:
    agreeing_sources = [s for s, v in diffs_by_source.items() if v == diffs_by_source.get("nppes")]

    weighted_score = sum(SOURCE_WEIGHTS[s] for s in agreeing_sources)
    max_possible   = sum(SOURCE_WEIGHTS[s] for s in diffs_by_source)
    confidence     = weighted_score / max_possible if max_possible else 0.0

    return FieldDiff(
        field=field,
        old_value=existing_value,
        new_value=diffs_by_source.get("nppes", ""),
        confidence_score=round(confidence, 4),
        supporting_sources=agreeing_sources,
    )

def overall_confidence(diffs: list[FieldDiff]) -> float:
    if not diffs:
        return 1.0  # no changes detected = confirmed accurate
    return round(sum(d["confidence_score"] for d in diffs) / len(diffs), 4)
```

### Routing Thresholds

```python
THRESHOLDS = {
    "auto_update":  0.85,
    "human_review": 0.60,
    # below 0.60 → no_change
}
```

### Safe Auto-Update Rule

Address field requires stricter guard than other fields:

```python
def safe_to_auto_update(diff: FieldDiff) -> bool:
    if diff["field"] == "address":
        return "nppes" in diff["supporting_sources"] and len(diff["supporting_sources"]) >= 2
    return diff["confidence_score"] >= THRESHOLDS["auto_update"]
```

### Duplicate Detection

- **Primary:** NPI exact match → same provider, update in place
- **Secondary:** fuzzy name (token sort ratio ≥ 0.90 via `rapidfuzz`) + address proximity → flag for human review as possible duplicate
- No API cost — `rapidfuzz` is pure Python

### Inactive Provider Detection

- CMS returns no active claims in last 24 months → `active=False` candidate
- State board shows license expired/lapsed → auto-set `active=False`
- If both agree: confidence 1.0, auto-update

---

## 5. Repo Structure

```
provider-practice-directory-update-pipeline/
│
├── pipeline/
│   ├── orchestrator.py        # LangGraph graph definition + runner
│   ├── state.py               # PipelineState, ProviderRecord, FieldDiff TypedDicts
│   ├── agents/
│   │   ├── staleness.py       # StalenessDetector
│   │   ├── fetch.py           # FetchAgent
│   │   ├── normalize.py       # NormalizeAgent
│   │   ├── compare.py         # CompareAgent
│   │   ├── score.py           # ScoringAgent
│   │   └── router.py          # RouterAgent
│   ├── sources/
│   │   ├── nppes.py           # NPPES REST client
│   │   ├── cms.py             # CMS provider data client
│   │   ├── board/
│   │   │   └── florida.py     # FL state board scraper
│   │   └── website.py         # Scrapling → BS4 → Haiku chain
│   ├── normalizers/
│   │   ├── address.py         # USPS CASS-style normalization
│   │   ├── phone.py           # E.164 formatting
│   │   └── name.py            # NPI canonical name casing
│   └── db/
│       ├── schema.sql
│       ├── store.py           # SQLite read/write helpers
│       └── audit.py           # AuditLogger
│
├── data/
│   ├── sample_providers.json  # 10–20 sample records for demo
│   └── pipeline.db            # SQLite DB (gitignored)
│
├── review/
│   └── dashboard.py           # Human review queue viewer (bonus)
│
├── tests/
│   ├── test_scoring.py
│   ├── test_normalize.py
│   └── test_fetch.py          # mocked HTTP responses
│
├── notebooks/
│   └── demo.ipynb             # End-to-end walkthrough for judges
│
├── context/
├── docs/
├── CLAUDE.md
├── README.md
├── pyproject.toml
└── .env.example               # ANTHROPIC_API_KEY only
```

---

## 6. Error Handling & Resilience

Per-source failure is non-fatal. FetchAgent catches exceptions independently per source:

```python
for source_name, fetcher in SOURCES.items():
    try:
        raw_sources[source_name] = fetcher.fetch(npi)
    except Exception as e:
        raw_sources[source_name] = None  # scored as absent
        log.warning(f"{source_name} fetch failed for {npi}: {e}")
```

**Minimum viable fetch:** NPPES failure → entire record goes to `human_review` regardless of other sources. NPI Registry is identity ground truth.

**LangGraph error node:** unhandled exception in any node sets `state["error"]`, routes to `error_handler` node, writes failure to `audit_log` with `action="pipeline_error"`, skips record.

**Retry logic:** NPPES and CMS get 3 retries with exponential backoff (`tenacity`). Website scrape gets 1 retry. If Scrapling + BS4 + Haiku all fail, source is marked absent.

---

## 7. Cost Estimate per 1,000 Records

| Cost driver | Assumption | Cost / 1k records |
|-------------|-----------|-------------------|
| NPPES API | Free, no rate limit | $0.00 |
| CMS API | Free, no rate limit | $0.00 |
| State board scrape | Scrapling, free | $0.00 |
| Website (Scrapling + BS4) | ~95% success rate | $0.00 |
| Claude Haiku (~5% hit rate) | 500 input + 200 output tokens avg | ~$0.04 |
| **Total** | | **~$0.04 / 1k records** |

At 1M records: ~$40 LLM cost. Human review labor excluded — pipeline targets <15% routed to review queue.

---

## Dependencies

```toml
[project]
dependencies = [
    "langgraph",
    "anthropic",
    "scrapling",
    "beautifulsoup4",
    "rapidfuzz",
    "tenacity",
    "httpx",
]
```

---

## Open Items

None. Design is complete and approved.
