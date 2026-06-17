# Kaggle Writeup — Submission Content

**Track:** Proposal ($5,000)  
**Option:** C — Hybrid (prototype + architecture proposal)  
**Deadline:** June 30, 2026

---

## Title (max 80 chars)

```
AI Pipeline for Provider Directory Accuracy at Scale
```

## Subtitle (max 140 chars)

```
A cost-efficient, repeatable AI pipeline that detects, verifies, and updates 
healthcare provider records using public sources and confidence-based routing.
```

---

## Project Description

> Fill this section before submitting. Structure below is the intended outline.

### The Problem

Healthcare provider directories go stale fast — providers move, practices merge, phone numbers change. Manual updates don't scale. HealthLynked needs a system that runs continuously, uses public data sources, and minimizes both cost and human intervention.

### What We Built

A hybrid submission: a working Python prototype demonstrating the core pipeline on sample data, plus a full architecture proposal for production scale.

**Prototype covers:**
- NPI Registry lookup via NPPES public API (free, no key)
- Address + phone comparison against existing record
- Confidence scoring based on source agreement
- Auto-update vs. human-review routing decision
- Structured audit log output

**Architecture covers:**
- Full pipeline design (staleness detection → enrichment → normalization → scoring → routing → audit)
- Agent workflow diagram
- Data source tier list (free public → paid fallback)
- Cost estimate per 1,000 records
- Confidence scoring formula
- Human review queue design
- Duplicate / inactive provider detection logic
- Safe auto-update rules
- Production implementation roadmap

### Pipeline Architecture

```
HealthLynked DB
    ↓ [Staleness Detector]
Find Outdated / Risky Records (last_verified_date + change signals)
    ↓ [Source Fetcher]
Query: NPPES NPI Registry → CMS Provider Data → State Medical Boards → Practice Website
    ↓ [Normalizer]
Standardize addresses (USPS CASS), phones (E.164), names (NPI canonical), specialties (taxonomy codes)
    ↓ [Comparator]
Field-level diff against existing record
    ↓ [Confidence Scorer]
Score = weighted average of (source count × source reliability × field match strength)
    ↓ [Router]
≥ 0.85 → auto_update | 0.60–0.84 → human_review | < 0.60 → no_change / flag
    ↓ [Audit Logger]
JSON log: provider_id, field, old_value, new_value, confidence, sources, timestamp, action
```

### Cost Controls

- NPPES API: free, no rate limit concern at low scale
- LLM used only for: fuzzy name matching, unstructured website parsing
- Estimated cost per 1,000 records: `$X.XX` ← fill after benchmarking prototype
- Human review routed only for confidence < 0.85 (estimated X% of records)

### Key Design Decisions

1. **Source priority:** NPI Registry is ground truth for identity; address corroborated by ≥2 sources for auto-update
2. **No-LLM fast path:** structured sources processed rule-based; LLM only on unstructured (website scrape)
3. **Confidence formula:** `score = Σ(source_weight_i × field_match_i) / Σ(source_weight_i)` — explicit, auditable
4. **Safe auto-update rule:** address auto-updates only if NPI Registry + 1 other source agree
5. **Duplicate detection:** NPI as primary key; fuzzy name + address match for records without NPI

---

## Attachments / Links

- [ ] GitHub repo link
- [ ] Prototype demo (notebook or script)
- [ ] Agent workflow diagram (image)
- [ ] Sample audit log output
- [ ] Human review dashboard screenshot (bonus)

---

## Checklist Before Submitting

- [ ] Title filled (≤80 chars)
- [ ] Subtitle filled (≤140 chars)
- [ ] Thumbnail image uploaded (560×280)
- [ ] Project description complete
- [ ] GitHub/code link attached
- [ ] Prototype runs end-to-end on sample data
- [ ] Cost per 1,000 records calculated
- [ ] Confidence formula documented
- [ ] Audit log sample shown
- [ ] Architecture diagram included
