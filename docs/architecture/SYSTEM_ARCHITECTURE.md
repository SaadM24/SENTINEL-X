# System architecture

The flow, trace and evidence pipelines share a local results directory. They keep their observational units separate. The server reads saved artifacts directly, so an analyst can inspect an experiment without loading a serialized model or fitting it again.

| Component | Input | Operation and output |
|---|---|---|
| Data | Pinned CSV sources | Project onto allowed numeric fields, disk-backed deduplication, partition, fingerprint; produce events.csv and manifest.json |
| Detection | Disjoint train/cal/test rows | Fit preprocessor and seven estimators, map scores on calibration partition; checkpoint estimator, feature order, preprocessor and calibrators; emit held-out metrics and primary event scores |
| Sequence | Verified ZIP of trace text | Split by trace digest, estimate token and transition densities; export edges, rarest transition and per-trace scores |
| Fusion | Separate ADFA scenario splits | Estimate benign transition density; evaluate calibrated frequencies alone and frequencies plus density score on the same records |
| Transfer | Two compatible versioned NetFlow corpora | Stream chunks, sample model inputs, remove overlaps, train only on source; score both domains with identical parameters |
| Investigation | Allowlisted record fields, anchor ID | Retrieve same-session evidence when possible; validate identity, probabilities and chronology; cite fields or abstain |
| Triage | Primary detector output | Apply locked confidence rules, write decisions and cited reports; labels used only for retrospective scoring |
| Dashboard | Local CSV/JSON results | Serve tables, graphs, evidence and reports on loopback; store versioned analyst decisions in SQLite |

The optional local language-model adapter may reorder already-supported observations. It accepts only permutations of indices and falls back to deterministic order. The model has no authority over evidence, labels or scoring. See [dashboard endpoints](DASHBOARD.md) and [investigation protocol](../protocols/EVIDENCE_AND_TRIAGE.md).

Result directories are scoped by experiment. The master saves per-stage logs and independent failure status; detection resumes at verified model boundaries. Native benchmark, cross-domain pilot, trace and synthetic evidence outputs retain separate provenance. Full training and bounded mode fit in host memory with one model active at a time. Processed feature matrices are smaller than source packet captures; the release needs no packet inspection or network connectivity to view packaged results.
