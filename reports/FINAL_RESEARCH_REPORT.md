# SENTINEL-X
## Trustworthy, explainable and human-centred AI for cyber threat detection and investigation

**Research release 1.0 · 20 November 2026**

### Finding

Order matters for standalone detection on genuine Linux system-call traces. Its value was much smaller once a calibrated classifier already knew the syscall frequencies. At a fixed budget of 124 reviewed traces, the classifier left 37 errors among the remaining 497 cases. Adding Markov surprise left 39. The experiments demonstrate measurable ranking and review trade-offs; they do not establish a reduction in analyst effort from combining the components.

### Design and populations

We studied three kinds of decisions. Native UNSW-NB15 experiments classify completed network flows from its published train/test sources. ADFA-LD experiments score ordered traces of Linux system calls. Investigation experiments ask whether statements about an alert and its timeline can be traced to specific records. Distinct labels, units and datasets preclude correlating the first two into a common incident.

For native detection we projected the two published input files onto 19 numeric fields. Training-source vectors took precedence, 1,076 shared vectors were excluded from the test source, and within-source category conflicts were removed. All 132,175 eligible vectors were used: 70,021 for training, 17,395 for calibration and 44,759 for testing. The full test set contained 14,710 attack and 30,049 benign vectors. Seven fixed model families were evaluated with raw, Platt, temperature and isotonic score mappings. Configuration and threshold choices were frozen before the primary comparison. Bounded runs used three seeds on one fixed split. A post-hoc check measured duplicate model inputs after numeric preprocessing.

### H1 and H2. Ranking, decisions and probabilities

| Model on the full native test | Raw macro-F1 | Raw AP | False alarms / 1,000 benign |
|---|---:|---:|---:|
| Logistic regression | 0.671 | 0.472 | 446.7 |
| Random forest | 0.800 | 0.912 | 258.1 |
| Histogram gradient boosting | 0.782 | 0.918 | 294.3 |
| Isolation forest | 0.505 | 0.412 | 607.2 |
| Multilayer perceptron | 0.759 | 0.870 | 329.2 |
| Autoencoder | 0.566 | 0.523 | 553.6 |
| Radial basis classifier | 0.689 | 0.551 | 422.1 |

The forest had the highest raw macro-F1, and boosting had the highest raw AP. Even the forest issued 7,755 false positives. The anomaly baselines map raw novelty scores to training-benign percentiles; 0.5 has a different operational meaning for those scores. Logistic Platt calibration improved Brier from 0.23336 to 0.22587 and ten-bin ECE from 0.19168 to 0.17206. Its AP stayed 0.47241. Platt worsened the forest's Brier from 0.11840 to 0.11937. These results support model-dependent calibration effects.

### H3. A smaller automatic error rate has a queue cost

Logistic regression with Platt scaling was the preselected operating model. The target of 20% escalation, set on calibration scores, sent 9,830 of 44,759 test vectors to review (21.96%). Error among automatically decided cases went from 32.70% with full coverage to 29.55%. Under a separate, fixed 0.85 confidence requirement, the queue grew to 25,755 cases, including 10,772 errors and 14,983 decisions the model had already got right. The 19,004 automatic decisions still contained 3,864 errors. No human corrections are assumed in these rates.

### H4. Sequence gains depend on the comparator

On 3,070 distinct test traces (730 attack-directory labels), a first-order smoothed Markov density improved AP from 0.3142 to 0.4614 over a unigram density. It also increased false positives from 326 to 401 of 2,340 benign traces. Both thresholds were set at a benign calibration quantile. Learnable order improved ranking without guaranteeing a particular false-positive rate on held-out data.

The exploratory fusion comparison used disjoint attack-scenario directories for supervised fit, calibration and test, and a separate set of 780 benign traces for density fitting. On 621 test traces, AP moved from 0.7565 to 0.7573, while Brier moved from 0.09780 to 0.09799. At the matched review budget, accepted error increased from 7.44% to 7.85%. The direction and small magnitude give no convincing evidence of a reliability benefit. Both experiments use collection-directory labels, so an individual process may be benign even inside an attack directory.

### H5. Generalisation to another collection

A separate fixed logistic model used eleven compatible NetFlow measurements. It drew reproducible 50,000-row samples per native v2 corpus, collapsed matching representations, removed ambiguity and excluded target overlap. It trained on 4,462 NF-UNSW vectors. The source test comprised 1,488 vectors; the external NF-CSE-CIC test comprised 12,889.

| Metric | Within source | External |
|---|---:|---:|
| Attack fraction | 0.1841 | 0.2399 |
| ROC-AUC | 0.8883 | 0.2980 |
| Average precision | 0.5670 | 0.1675 |
| Brier | 0.1042 | 0.3300 |
| False-positive rate | 0.0470 | 0.6590 |
| Recall | 0.2993 | 0.5847 |

A complete scan of the two native files verified class counts and the binary/category mapping. The record-level, class-stratified 500-draw interval for the external-minus-source AUC difference was approximately [-0.611, -0.569], conditional on the model and strata. Another exploratory v3 block sample gave AUC 0.9244 within source and 0.5636 externally. The smaller v3 pilot reuses the same underlying collections; it is a sensitivity check, not an independent site replication. Changing collector, prevalence and attack mix together prevents causal attribution of the drop.

### H6. Supported facts and human usefulness

Eight controlled queries yielded 24 blinded case-condition review units. Same-session retrieval recovered 12/12 expected related IDs versus 6/12 with the anchor alone. Both produced nine correct field observations. Removing citations left the same values in place but removed their direct evidential links. This comparison establishes verifiability properties of the constrained implementation. It does not compare with a live ungrounded LLM.

On the full real-flow queue, 51,510 cited model/score statements could be matched mechanically to their stored records. These statements describe model outputs, not attack causation. A separate 20-case real-flow review packet samples five cases in each confusion cell. Deliberate citation substitution showed why event identity matters: generic model names matched even when every reference pointed to the wrong record. No independent analyst has rated either packet. Investigation accuracy, time saved and operational workload after human decisions remain open.

### Interpretation and reproducibility

Perturbing ACK timing reduced primary AP by 0.0816, but it shares information with other connection-timing features. Model associations do not identify causes. The transformed-overlap audit found 62 test rows identical to an earlier transformed vector; excluding them changed logistic macro-F1 from 0.67008 to 0.66970. Exact vector deduplication cannot remove all related-source dependence.

The evidence supports a reproducible empirical case study and an application portfolio artifact. Claims of novel automata learning, improved human performance, universal calibration gains or deployment readiness exceed the observations. For individual model metrics, provenance and experiment-level checks, see [detection findings](DETECTION_FINDINGS.md), [trace experiments](sequence/BEHAVIOUR.md), [ablation studies](ABLATION_STUDIES.md), [reproducibility](REPRODUCIBILITY_REPORT.md), [limitations](SCIENTIFIC_LIMITATIONS.md) and the [source literature](../docs/research/LITERATURE_REVIEW.md).
