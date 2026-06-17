# HealthLynked — Provider & Practice Directory Update Pipeline

**Platform:** Kaggle  
**Prize:** $5,000 (Proposal track)  
**Deadline:** June 30, 2026 06:00 AM GMT  
**Submission:** Option C — Hybrid (prototype + architecture proposal)  
**Winning team** gets a 3-month paid consulting contract to implement the solution.

---

## Problem

HealthLynked maintains a provider/practice directory used by patients to find doctors. Data goes stale constantly:

- Providers move practices
- Practices close, merge, or rebrand
- Phone numbers and addresses change
- Providers join or leave groups
- Specialties/credentials appear differently across sources
- Multiple sources conflict with each other

Manual maintenance doesn't scale.

---

## What the System Must Do

1. **Identify** outdated or risky records
2. **Search** reliable public sources (NPI Registry, CMS, state boards, practice websites)
3. **Compare** existing HealthLynked data vs. external sources
4. **Normalize** names, addresses, phones, specialties, affiliations
5. **Detect** duplicates, inactive providers, moved providers, practice changes
6. **Score** each proposed update with a confidence score
7. **Auto-approve** high-confidence updates
8. **Flag** uncertain/conflicting records for human review
9. **Audit** every change: what changed, why, which sources supported it

---

## Pipeline Architecture (Required Shape)

```
HealthLynked DB
    ↓
Find Outdated / Risky Records
    ↓
Search Trusted Sources (NPI, CMS, state boards, practice websites)
    ↓
Collect Updated Data
    ↓
Clean & Normalize (names, addresses, phones, specialties)
    ↓
Match Provider / Practice Records
    ↓
Assign Confidence Score
    ↓
Decision:
  - No change        → record confirmed accurate
  - Auto-update      → high-confidence update applied
  - Human review     → low-confidence or conflicting data
    ↓
Save Audit Log + Update Directory
```

---

## Output Format

### When update found (high confidence):
```json
{
  "provider_id": "HL_001",
  "npi": "1234567890",
  "change_detected": true,
  "changes": [
    {
      "field": "address",
      "old_value": "100 Main St, Naples, FL 34102",
      "new_value": "250 Health Park Dr, Fort Myers, FL 33908",
      "confidence_score": 0.92,
      "supporting_sources": ["NPI Registry", "Practice Website", "State Medical Board"]
    }
  ],
  "overall_confidence": 0.90,
  "recommended_action": "auto_update",
  "reason": "Updated address confirmed by multiple reliable sources."
}
```

### When sources conflict (low confidence):
```json
{
  "provider_id": "HL_001",
  "npi": "1234567890",
  "change_detected": true,
  "overall_confidence": 0.61,
  "recommended_action": "human_review",
  "reason": "Practice website and NPI Registry show different addresses."
}
```

---

## MVP Scope (Fields to Cover)

- Provider name
- NPI
- Specialty
- Practice name
- Address
- Phone number
- Website
- Active/inactive status

---

## Evaluation Criteria

| Criterion | What judges look for |
|-----------|---------------------|
| Accuracy | Correct updates, avoids false positives |
| Scalability | Works for millions of records |
| Cost Efficiency | Minimizes API/LLM/scraping/manual costs |
| Practicality | Lean team can implement it |
| Explainability | Clear reasoning for each update |
| Data Quality | Proper normalization across all fields |
| Source Reliability | Trustworthy sources, handles conflicts |
| Human Review Design | Reduces manual review to true edge cases |
| Audit Trail | Every change traceable to source + logic |

---

## Bonus Points

- Working prototype
- Agent workflow diagram
- Cost estimate per 1,000 provider records
- Confidence scoring formula (explicit)
- Sample human review dashboard
- Duplicate detection logic
- Address normalization strategy
- NPI validation
- Practice-location matching
- Provider movement detection
- Inactive/retired provider detection
- Change history and audit log
- Safe auto-update rules
- Clear implementation roadmap

---

## Key Constraints

- **No unnecessary paid APIs** — prefer free public sources (NPPES, CMS, state boards)
- **No unnecessary LLM calls** — use LLMs only where rule-based logic fails
- **No unnecessary manual review** — route to human only when confidence < threshold
- Repeatable pipeline (runs continuously or periodically) — not a one-time cleanup
