# Independent investigation review

This release includes 24 shuffled report units for eight synthetic queries and three deterministic systems. No independent reviews were collected. Each observed field is a quotation of a stored value. A field containing instruction-like prose is evidence of that stored text only.

## Procedure

Give each of two independent reviewers (A and B) an untouched copy of `results/v04/evidence/review.csv`, `cases.jsonl`, and `data/fixtures/evidence_records.json`. Ask them to work separately. Withhold `review_key.json`, `evidence_key.json` and machine-scored results until their sheets are locked. Some behaviour is inferable from report contents even with anonymous system identifiers. The samples overlap within query. They cannot support independent-alert confidence intervals.

Each line of cases.jsonl gives the review ID, the query event ID, and the displayed report. Examine original records for the queried event, its exact nonempty session identifier and admissible offset-aware timestamps. Exclude unrelated sessions and undated events from the ordered timeline. Review observations as assertions about alert records only. In each row, enter a distinct assessor identifier and one of yes, no, unclear or na for every question. Mark na only when the item has no applicable evidence or claim. Record supporting event IDs in notes for disputed or unclear claims.

| Column | Question |
|---|---|
| citation_precision | Does every supplied claim citation point to the right event and support the field and value? Use na if no citations were supplied. |
| evidence_sufficiency | Does the report supply all needed evidence for the investigation scope, including relevant records? Use na on appropriate abstentions. |
| factual_support | Are all asserted observation values present in the source under the stated meaning? Use na when no observations are present. |
| unsupported_claims | Does the report contain any observation without a supporting citation? Yes here represents a defect. Use na when there are no observations. |
| correct_abstention | Is the decision to report or abstain justified by a score or signal on the anchor? |
| timeline_consistency | Does the ordered list match all and only relevant dated records? An appropriately empty timeline can satisfy this. |
| completeness | Does the report identify each relevant record without introducing unrelated records? |

Run from the repository root after filling both sheets:

```powershell
python scripts/score_evidence_reviews.py A.csv B.csv --output agreement.json
```

For each field the script computes exact agreement and nominal Cohen's kappa over all four labels, treating unclear and na as distinct categories. Kappa is undefined for identical constant assessments. Output includes disagreements and grouped counts. Binary rates exclude unclear, na and unresolved ratings; the denominator is explicit. Before adjudication they cover only decisive agreements. Where ratings differ, a third assessor should enter a final resolution in a full copy of the sheet, preserving agreed ratings. Then run:

```powershell
python scripts/score_evidence_reviews.py A.csv B.csv --adjudication resolved.csv --output final_agreement.json
```

Distinct identifiers and complete sheets are enforced; human independence cannot be certified by software. Output files must be new. Do not publish notes or assessor identifiers without their permission.

## Exploratory benchmark packet

The research release also includes 20 matched UNSW-NB15 examples under `results/v10/research/evidence_packet/`. Its separate `blinded_cases.jsonl` contains measured fields and the recorded score for each case. The binary decision uses p ≥ 0.5; escalation uses max(p,1−p) < 0.85. Before revealing `coordinator_key.json`, complete the packet-specific `review.csv` and record discrepancies in source-record accuracy, threshold interpretation or attack-attribution sufficiency. Distinguish the event having a particular dataset label from any claim about the cause of a real incident. The packet is deliberately balanced across the four prediction outcomes and unsuitable for estimating ordinary queue prevalence. The double-review scorer above is for the synthetic seven-question rubric only. To regenerate the benchmark packet after the main research run:

```powershell
python scripts/build_evidence_packet.py
```
