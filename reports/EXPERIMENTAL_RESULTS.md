# Experiment outputs

| Experiment | Primary evidence | Reproduction check |
|---|---|---|
| 1. Native detection | results/v02/research-full/comparison.csv, categories.csv | Reload seven checkpoints; reproduce confusion matrices, scores and primary event IDs |
| 2. Calibration | results/v02/research-full/reliability.csv, comparison.csv | Check all 28 model-map rows and bin totals |
| 3. Selective decisions | results/v02/research-full/coverage.csv | Compare actual workload, coverage and retained error arithmetic |
| 4. Trace order and fusion | results/v03/scores.csv, results/v03_fusion/summary.json | Recompute per-trace AP and verify disjoint scenarios; compare fixed-queue errors |
| 5. Transfer | results/external/nf-v2/metrics.json and nf-v3-pilot/metrics.json | Check both domains' scores and full native v2 label/count mappings |
| 6. Attribution | results/v02/research-full/importance.csv and transformed_overlap.csv | Inspect signed coefficients and perturbations; remove transformed-vector overlaps |
| 7. Investigation | results/v04/evidence/summary.json and cases.jsonl | Compare claims, citations and related-ID retrieval with controlled keys |
| 8. Integrated triage | results/v10/research-full/triage/summary.json and evidence_packet/summary.json | Compare fixed thresholds, queue counts and record identity; independent rating pending |

[Full numerical results and interpretation](FINAL_RESEARCH_REPORT.md) · [Individual model comparisons](DETECTION_FINDINGS.md) · [Derived full-cohort plots](generated/research-full/summary.md)
