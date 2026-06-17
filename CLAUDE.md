# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Competition Context

This is a Kaggle competition submission for HealthLynked's **Provider & Practice Directory Update Pipeline** ($5,000 prize, deadline June 30 2026). We are targeting **Option C: Hybrid submission** — a working prototype plus a full architecture proposal.

Full competition brief: `context/INFO.md`  
Submission content outline: `context/WRITEUP.md`

## Submission Goal

Build a repeatable AI-powered pipeline that:
1. Detects stale provider/practice records
2. Fetches updated data from free public sources (NPPES NPI Registry, CMS, state medical boards, practice websites)
3. Normalizes and compares fields
4. Assigns confidence scores to proposed updates
5. Routes to auto-update (≥0.85) or human review (0.60–0.84)
6. Produces a structured audit log

## Key Constraints (Non-Negotiable)

- **No paid APIs** unless free alternatives genuinely fail — NPPES/CMS/state boards are free
- **Minimize LLM calls** — rule-based logic first; LLM only for unstructured text (website scraping, fuzzy name matching)
- **Minimize human review** — only truly ambiguous cases (conflicting sources, confidence < 0.85)
- Pipeline must be **repeatable** (runs periodically), not a one-time cleanup script

## MVP Fields

Provider name, NPI, specialty, practice name, address, phone, website, active/inactive status.

## Confidence Scoring Rule

`score = Σ(source_weight_i × field_match_i) / Σ(source_weight_i)`

Address auto-updates only if NPI Registry + at least one other source agree. NPI is the primary identity key.

## Bonus Points to Target

Agent workflow diagram, cost estimate per 1,000 records, confidence formula (done above), duplicate detection logic, inactive provider detection, human review dashboard, NPI validation, audit log.
