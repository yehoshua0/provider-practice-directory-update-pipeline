# AI Pipeline for Provider Directory Accuracy at Scale

> **Kaggle submission — paste-ready.** Title ≤80 chars, subtitle ≤140 chars, then the full project description.

---

## Title (80 chars max)

```
AI Pipeline for Provider Directory Accuracy at Scale
```

## Subtitle (140 chars max)

```
A cost-efficient, repeatable AI pipeline that detects, verifies, and updates healthcare provider records using free public sources.
```

---

## Project Description

### The Problem

Healthcare provider directories rot fast. Providers move practices, groups merge or rebrand, phone numbers and addresses change, licenses lapse, and the same provider shows up differently across every source. Patients hit dead phone lines and wrong addresses; HealthLynked carries the maintenance cost. Manual upkeep does not scale to millions of records, and a one-time cleanup is stale the day it finishes.

The directory needs a system that runs **continuously**, pulls from **free public sources**, and spends money — human or machine — **only where it has to**.

### What We Built (Option C — Hybrid)

A working Python prototype demonstrating the full pipeline end-to-end on sample data, **plus** a production architecture proposal. The prototype is not a sketch: it is a 7-agent LangGraph pipeline with 39 passing tests, real NPPES/CMS clients, SQLite persistence, an audit log, and a human-review dashboard.

**Prototype demonstrates:**
- NPI Registry lookup via the free NPPES public API (no key)
- CMS Medicare provider lookup + state medical board scrape
- Rule-based normalization (USPS-style address, E.164 phone, NPI-canonical name)
- Field-level comparison against the existing record, with cross-source conflict detection
- Confidence scoring from weighted source agreement
- Auto-update / human-review / no-change routing with a stricter address guard
- Structured JSON audit log of every decision, written transactionally
- Human review queue dashboard (bonus)

**Architecture proposal covers:** full pipeline design, agent workflow diagram, source tier list, cost estimate per 1,000 records, the confidence formula, human-review queue design, duplicate + inactive-provider detection, safe auto-update rules, and a production roadmap.

---

### Pipeline Architecture

Seven discrete agents, each with one job, communicating through a single typed `PipelineState` object — no shared globals. Sources only *fetch*; agents do all *reasoning*. Adding a source never touches agent logic.

```
HealthLynked DB
    │
    ▼  StalenessDetector   — selects records past their re-verification age
    ▼  FetchAgent          — NPPES → CMS → State Board → Website (failures isolated)
    ▼  NormalizeAgent      — USPS address, E.164 phone, taxonomy→specialty, name casing
    ▼  CompareAgent        — field-level diff old vs new; flags inter-source conflicts
    ▼  ScoringAgent        — confidence = Σ(weight·match) / Σ(weight)
    ▼  RouterAgent         — ≥0.85 auto_update | 0.60–0.84 human_review | <0.60 no_change
    ▼  AuditLogger         — structured JSON → SQLite, every decision traceable
```

**Orchestration:** LangGraph runs the graph. Any node exception sets `state["error"]`, routes to an error handler, logs `action="pipeline_error"`, and skips the record — one bad record never halts the run.

---

### Confidence Scoring (explicit, auditable)

```
score = Σ(source_weight_i × field_match_i) / Σ(source_weight_i)
```

Source weights reflect trust, NPI Registry as ground-truth identity:

| Source | Weight |
|--------|--------|
| NPPES NPI Registry | 1.00 |
| CMS Medicare | 0.85 |
| State Medical Board | 0.80 |
| Practice Website | 0.65 |

A field's confidence is the weighted fraction of sources that agree with the reference value. Overall record confidence is the mean across changed fields; no changes detected → confidence 1.0 (confirmed accurate).

**Routing:** `≥0.85 → auto_update`, `0.60–0.84 → human_review`, `<0.60 → no_change`.

**Safe auto-update rule:** address is special. It auto-updates **only if NPPES agrees AND at least one other source agrees** — never on a single source. All other fields use the threshold directly.

```python
def safe_to_auto_update(diff):
    if diff["field"] == "address":
        return "nppes" in diff["supporting_sources"] and len(diff["supporting_sources"]) >= 2
    return diff["confidence_score"] >= 0.85
```

---

### Cost Controls — ~$0.04 per 1,000 records

Every structured source is free and rule-based. The LLM (Claude Haiku) is invoked **only** for unstructured website parsing, and **only** after Scrapling and BeautifulSoup both fail to extract a contact block — an estimated ~5% of records.

| Cost driver | Assumption | Cost / 1k records |
|-------------|-----------|-------------------|
| NPPES API | Free | $0.00 |
| CMS API | Free | $0.00 |
| State board scrape | Free | $0.00 |
| Website (Scrapling + BS4, ~95% success) | Free | $0.00 |
| Claude Haiku (~5% hit, ~700 tok avg) | LLM fallback only | ~$0.04 |
| **Total** | | **~$0.04 / 1k records** |

At **1M records: ~$40** in LLM cost. Human review is targeted to **<15%** of records (true conflicts and sub-0.85 confidence only).

---

### Data Quality & Reliability

- **Normalization:** addresses to USPS canonical form, phones to E.164, names to NPI casing, specialties via taxonomy codes — so comparison is apples-to-apples, not string noise.
- **Duplicate detection:** NPI exact match = same provider, update in place. No NPI → fuzzy name (rapidfuzz token-sort ≥0.90) + address proximity → flag as possible duplicate. Pure Python, zero API cost.
- **Inactive provider detection:** CMS shows no claims in 24 months *and* state board shows license lapsed → both agree → confidence 1.0, auto-set inactive.
- **Resilience:** per-source failures are non-fatal (scored as absent). NPPES is the exception — if identity ground-truth fails, the record goes straight to human review. NPPES/CMS get 3 retries with exponential backoff.
- **Audit trail:** every change row records provider_id, field, old → new, confidence, supporting sources, action, reason, timestamp. Record update + audit entry commit in one transaction or neither does.

---

### Why This Wins on the Judging Criteria

| Criterion | How this submission answers it |
|-----------|-------------------------------|
| Accuracy | NPPES ground truth + multi-source agreement; address needs 2+ sources |
| Scalability | Stateless per-record agents, free APIs, ~$40 LLM cost at 1M records |
| Cost efficiency | Rule-based first; LLM only on ~5% unstructured cases |
| Practicality | 7 small agents, SQLite, standard libs — a lean team can run it |
| Explainability | Explicit weighted formula; every decision carries its reason + sources |
| Data quality | Canonical normalization across all 8 MVP fields |
| Source reliability | Weighted trust tiers; conflicts routed, not guessed |
| Human review | <15% target; only sub-0.85 and conflicting records |
| Audit trail | Transactional JSON log, fully traceable |

---

### Production Roadmap

1. **Scale fetch** — batch NPPES/CMS, add per-state board modules beyond the FL MVP.
2. **Scheduler** — cron/Airflow re-verification by record age + change signals (continuous, not one-shot).
3. **Review UI** — promote the dashboard to a triage app with one-click accept/reject feeding back into weights.
4. **Feedback loop** — reviewer decisions tune source weights and thresholds over time.
5. **Observability** — per-run metrics: auto-update rate, review rate, source hit rates, LLM spend.

---

## Attachments / Links

- [ ] GitHub repo link — *(no git remote configured yet; push and paste URL)*
- [x] Prototype demo — `notebooks/demo_executed.ipynb` (end-to-end, executed)
- [x] Agent workflow diagram — included above + `docs/.../pipeline-architecture-design.md`
- [x] Sample audit log output — SQLite `audit_log` table, shown in demo
- [x] Human review dashboard — `review/dashboard.py` (bonus)

## Pre-submission checklist

- [x] Title ≤80 / subtitle ≤140
- [x] Project description complete
- [x] Cost per 1,000 records calculated (~$0.04)
- [x] Confidence formula documented
- [x] Audit log sample shown
- [x] Architecture diagram included
- [x] Prototype runs end-to-end (39/39 tests pass)
- [ ] GitHub/code link attached *(needs remote)*
- [ ] Thumbnail image uploaded (560×280)
