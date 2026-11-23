# Application evidence

**Portfolio description:** SENTINEL-X is a reproducible defensive security research workbench covering intrusion detection, confidence calibration, selective prediction, system-call sequence modelling and record-grounded alert investigation.

**Evidence suitable for a technical interview**

- Evaluated seven model families on 44,759 held-out UNSW-NB15 flow vectors after auditing exact overlap. A raw forest achieved 0.800 macro-F1 and generated 258 false alerts per 1,000 eligible benign vectors.
- Compared token frequencies with ordered system-call transitions on ADFA-LD. A Markov detector improved average precision by 0.147, but adding its score to a calibrated frequency classifier did not improve error at a matched review budget.
- Measured a fall in ROC-AUC from 0.888 to 0.298 when a frozen NetFlow classifier transferred between two benchmark collections. The source files, checksums, sampling rule and code are documented.

The implementation and first experiment runs were produced in an AI-assisted Work session. Before using first-person contribution claims, distinguish the design decisions, implementation, replication and analysis you personally carried out. The study has no independent human review or institutional endorsement.
