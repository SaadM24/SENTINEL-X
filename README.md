# SENTINEL-X

A local research platform for trustworthy intrusion detection and evidence-grounded alert investigation. The release includes working code, checkpoints, held-out predictions, an interactive dashboard and a complete benchmark report.

**Main result.** Ordered system calls improved standalone anomaly ranking. Adding a Markov score to a calibrated syscall-frequency classifier left 39 errors among 497 automatically accepted traces, compared with 37 without the score at exactly the same review budget. The full UNSW-NB15 benchmark and separate NetFlow transfer experiments also expose the cost of false alarms and changes in collection.

## Start on Windows

Extract the archive. In the directory containing this file, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_smoke_tests.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\launch_dashboard.ps1
```

Open http://127.0.0.1:8765 and choose **research-full** for the complete eligible native flow benchmark. The saved results can be viewed immediately after setup. The basic dashboard reads files and needs no GPU or external account. A new full reproduction can be launched with `.\run_research_pipeline.ps1 -Full`.

| Read or reproduce | Entry point |
|---|---|
| Findings and limits | [Research report](reports/FINAL_RESEARCH_REPORT.md) Â· [PDF](reports/SENTINEL-X-Research-Report.pdf) |
| What is complete | [Completion matrix](reports/COMPLETION_MATRIX.md) Â· [Integrity audit](reports/REPRODUCIBILITY_REPORT.md) |
| Exact commands and recovery | [Windows handoff](docs/local_execution/COMPLETE_LOCAL_HANDOFF.md) |
| Protocol and sources | [Protocol](docs/protocols/EXPERIMENTAL_PROTOCOL.md) Â· [Dataset audit](docs/protocols/DATASET_AUDIT.md) Â· [Literature](docs/research/LITERATURE_REVIEW.md) |
| Run index | [Experiment registry](experiments/registry.json) Â· [Release manifests](releases/index.json) |
| Check release integrity | `python scripts/verify_results.py --run research-full` and `python scripts/verify_sequence.py` |
| Independent evidence review | [Reviewer instructions](docs/evaluation/INDEPENDENT_INVESTIGATION_REVIEW.md) |
| Application wording | [Verified project evidence](reports/PHD_APPLICATION_EVIDENCE.md) |

## Repository map

`src/sentinel_x` holds flow preparation, detection, calibration, sequence models, fusion, evidence retrieval and the dashboard. `scripts` exposes acquisition, verification, plotting, scoring and pipeline commands. `data/processed` contains eligible native cohorts and their manifests. `results` stores experiment records by release and dataset; `reports` contains derived analysis. All integrations default to local operation.

Machine-specific paths in preserved logs identify the execution environment. New runs use their own relative artifact paths. Raw third-party datasets can be reacquired from the pinned sources. Models can be inspected through the dashboard without deserializing their Python checkpoints.


## Public repository scope

This Git snapshot excludes sampled third-party NetFlow v3 CSVs and blinded-review answer keys. Dataset retrieval scripts and the research protocols remain available.

The historical releases/archive_sha256.json records the original packaged release, not this redacted Git snapshot. Its complete archive-wide hash check is not expected to pass on a fresh public clone.

To verify the supplied full intrusion-detection results, run:
python scripts/verify_results.py --run research-full

The Windows SQLite connection fix was applied after the original research experiments. No published scientific findings were changed for that compatibility fix.

Python joblib checkpoints should only be loaded from trusted, verified sources.
