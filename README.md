# Provider & Practice Directory Update Pipeline

Kaggle competition submission for [HealthLynked](https://kaggle.com/competitions/provider-practice-directory-update-pipeline).

**Track:** Proposal · **Prize:** $5,000 · **Deadline:** June 30, 2026

## What This Is

A hybrid submission (Option C): a working Python prototype + full architecture proposal for an AI-powered pipeline that keeps a healthcare provider directory accurate and up to date.

The pipeline detects stale records, fetches data from free public sources, normalizes and compares fields, scores confidence, and routes updates to either auto-apply or human review.

## Approach

```
Stale Record Detection
    → Fetch: NPPES NPI Registry + CMS + State Medical Boards + Practice Website
    → Normalize: addresses, phones, names, specialties
    → Compare: field-level diff vs. existing record
    → Score: confidence = weighted source agreement
    → Route: auto_update (≥0.85) | human_review (0.60–0.84) | no_change
    → Audit: structured JSON log of every decision
```

**Cost controls:** no paid APIs, LLM only on unstructured text, human review minimized to true conflicts.

## Repo Structure

```
context/
  INFO.md       # Competition brief (clean reference)
  WRITEUP.md    # Submission content outline + checklist
CLAUDE.md       # AI session context
README.md       # This file
```

> Prototype and architecture docs will be added as development progresses.

## Data Sources

| Source | Cost | Used for |
|--------|------|----------|
| NPPES NPI Registry | Free | Identity, address, phone, specialty |
| CMS Provider Data | Free | Practice affiliations, active status |
| State Medical Boards | Free | License status, specialty verification |
| Practice Website | Free (scrape) | Address, phone, hours confirmation |

## Submission Checklist

See `context/WRITEUP.md` for the full checklist before the Kaggle submission deadline.
