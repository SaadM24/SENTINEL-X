# Metrics and splits

The positive class is an attack-labelled flow or attack-directory trace. Precision is TP/(TP+FP), recall is TP/(TP+FN), and the harmonic mean gives positive F1. Macro-F1 equally weights the two class-specific F1 values. A confusion matrix has true rows and predicted columns ordered benign, attack. False alarms per 1,000 benign events equals 1000 FP/(TN+FP); it depends on the decision threshold and only represents the evaluated cohort.

AP averages precision over recall increments; the separate PR-AUC column uses trapezoidal interpolation. ROC-AUC measures ranking and does not encode deployment prevalence. Brier is mean squared probability error. Ten equal-width probability bins give ECE as the weighted average absolute difference between attack frequency and mean score. Empty bins contribute zero. Inspect bin counts alongside a curve.

Confidence is max(p,1-p). Coverage is accepted/total; selective risk is errors among accepted divided by accepted. The complement of coverage gives queue volume, not analyst time. Distinguish calibration-quantile policies used to approximate budgets from absolute thresholds used by triage. For a very small group, retain the count. Treat unsupported classes and undefined metrics as missing.

See the [data audit](../protocols/DATASET_AUDIT.md), [detection protocol](../protocols/DETECTION_PROTOCOL.md), [sequence protocol](../protocols/SEQUENCE_PROTOCOL.md) and [investigation protocol](../protocols/EVIDENCE_AND_TRIAGE.md) for unit-specific rules. The 3,000-flow bounded test is nested in the full 44,759-flow test. These runs are sensitivity comparisons, never independent replications. Seed changes hold the split fixed and quantify optimization sensitivity only.
