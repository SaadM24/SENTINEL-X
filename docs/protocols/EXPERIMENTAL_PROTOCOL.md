# Experimental protocol
Recorded before the project-level final comparison. The component protocols specify estimators, fixtures and scoring details. Use separate names and keep prior outputs when changing a protocol.

| Experiment | Unit and comparison | Decision rule and interpretation |
|---|---|---|
| 1 | Held-out labelled flows. Compare supervised linear, tree and neural models with benign-trained novelty scores. | Report macro-F1, positive-class AP, class counts and confusion matrices. Use train-derived calibration and decisions. |
| 2 | Same test rows for raw and calibrated scores | Compare paired Brier scores and equal-width ECE. A better rank score alone cannot establish better calibration. |
| 3 | Fixed review policies | Record accepted error count, accepted count and fraction escalated. Analyst capacity and decision quality are distinct. |
| 4 | Entire traces with legitimate ordering | Compare order-sensitive and bag-of-events scores. Preserve trace boundaries. Interpret results in the source domain. |
| 5 | Train NF-UNSW, transfer frozen detector to NF-CSE-CIC | Version and units must match within a pair. Never join native UNSW with NetFlow derivatives. Prespecified v3 mirror pilot samples 32 disjoint blocks of 100 flows per corpus, one seeded random offset per equal-width stratum. Collapse identical model inputs within a domain; discard contradictory groups and any target overlap with source. Fit fixed logistic regression on 75% of unique source vectors and evaluate remaining source and target at 0.5. Compare AP, ROC-AUC, FPR, recall and Brier with prevalence differences. Exploratory block samples cannot support population intervals. The same script supports two publisher v2 CSVs. |
| 6 | Feature perturbations and errors by category | Measure score sensitivity at fixed model settings; correlated predictors make causal attribution impossible. |
| 7 | Investigation request and its cited records | Check factual claims, record membership, coverage, abstention and time order. Human judgments require independent reviewers. |
| 8 | Fixed offline review queue with identical budget | Compare errors routed for review by competing policies. Any modeled resolution benefit assumes a correct reviewer. Time savings require a prospective human study. |

Never select the best-looking test variant as the deployment default. Use a named detector for downstream experiments, record the selection rule, and retain the other rows. A single trace collection cannot establish generalization to new environments. A passing software test or agreement with fixture assertions cannot establish analyst benefit.
