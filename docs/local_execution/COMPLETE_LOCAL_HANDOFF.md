# Run SENTINEL-X on Windows

Start in the extracted directory that contains `pyproject.toml` and `setup_windows.ps1`. Keep the directory structure intact. The release ships research outputs for inspection. New workflow names start with `local-` so the commands below preserve those outputs.

## Start here

Use Windows PowerShell 5.1 or PowerShell 7, 64-bit Python 3.11 and an internet connection for initial installation and any uncached benchmark downloads. A GPU, administrator account, API key and Git installation are optional. Install the usual Python launcher (`py`) with Python, or pass the absolute Python executable to setup. The CPU path is intended for the 8 GB laptop. Reserve an estimated 3 GiB of free disk for the environment, UNSW cache and checkpoints. Additional external NetFlow downloads require separate storage.

From a PowerShell window in the extracted repository, run the following single command for installation, tests, fixture training, evidence retrieval, triage, figures and verification.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_smoke_tests.ps1
```

The execution setting applies to this process. If running scripts is restricted on a managed computer, use the Python equivalents below under the applicable policy. The smoke test log identifies the installed dependencies, pytest results and individual stage runtimes.

To reproduce the bounded real benchmark, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_research_pipeline.ps1
```

To open the local dashboard, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\launch_dashboard.ps1
```

Open http://127.0.0.1:8765 and select a run. Review an alert, inspect its cited record, submit a decision and refresh the page. Analyst decisions persist in `outputs/feedback.sqlite3`. Use Ctrl+C to stop the server. Pass `-Port 8766` if the default port is occupied.

## Installation and inspection

```powershell
.\setup_windows.ps1
$py = ".\.venv\Scripts\python.exe"
& $py scripts/check_environment.py --require-tests
& $py scripts/run_pipeline.py --mode research --list
```

For a nonstandard interpreter use `.\setup_windows.ps1 -PythonExe "C:\path\to\python.exe"`. On a machine without PowerShell wrappers, the equivalent install is:

```powershell
py -3.11 -m venv .venv
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install -r requirements/research.txt -e ".[test]"
& $py -m pytest -q
& $py scripts/run_pipeline.py --mode smoke --run local-smoke --tests
```

The constraints file pins direct numerical dependencies. Wheel platforms, transitive dependencies, hardware and wall times may differ. Check the run-specific spec and environment JSON before comparing outputs. PowerShell and CUDA require local verification. A fresh Linux Python 3.11.18 virtual environment installed these pinned dependencies and passed the complete smoke workflow, including 49 tests collected at that execution. A separate Linux Python 3.12 run exercised the bounded real-data master and resume path. A Windows x86-64 Python 3.11 wheel-resolution dry run succeeded. Logs are in `results/v10/workflow_qa/`. All five PowerShell wrappers parsed with tree-sitter-powershell 0.26.4; their execution on Windows is pending.

## Datasets and cache

| Data | Cache path under project | Measured size / action |
|---|---|---|
| UNSW-NB15 prepared training source | `data/raw/unsw/train.csv` | 32,117,673 bytes. Retrieved on demand by `scripts/download_datasets.py --mode research`. |
| UNSW-NB15 prepared test source | `data/raw/unsw/test.csv` | 15,298,464 bytes. Same command. |
| ADFA-LD syscall archive | `data/raw/ADFA-LD.zip` | 2,381,193 bytes. The behaviour CLI verifies and caches it on first use. |
| Fixture flow CSV | `data/processed/smoke/events.csv` | Deterministic synthetic 560-row fixture created without internet access. |
| Bounded UNSW cohort | `data/processed/research/events.csv` | 6,000 fit, 1,500 calibration and 3,000 test rows. Its sibling manifest records the fingerprint. |
| All eligible UNSW vectors | `data/processed/research-full/events.csv` | Built with `--mode research --full` from the same sources. |
| External NetFlow pair | `data/raw/NF-UNSW-NB15-v2.csv` and `data/raw/NF-CSE-CIC-IDS2018-v2.csv` | Optional publisher CSV import. The byte-pinned script also accepts the compressed mirrors under `data/raw/nf-v2/` (709,422,414 bytes total). |

If an automatic download fails, take the **raw file bytes** from the linked pinned source, place them at the cache paths above, then rerun. The importer rejects HTML pages, modified line endings or incorrect versions through byte checks. Review permissions, class definitions and original publication attribution in [the dataset audit](../protocols/DATASET_AUDIT.md). [UNSW pinned train/test mirror](https://github.com/huangxyy/bdcc-ids-defense-selection/tree/a490371076ed35c1819815c2371874a8bebeb0b1/data) · [ADFA-LD pinned ZIP](https://raw.githubusercontent.com/verazuo/a-labelled-version-of-the-ADFA-LD-dataset/68bedf561f7b7abe9954a3ddc22dbf24c0d42372/ADFA-LD.zip)

## Full and independent experiments

For all eligible UNSW vectors, the full option retains the frozen detection configuration and increases sample size. The network and ensemble models fit one at a time. Data validation and sklearn models use CPU. A 4 GB CUDA card is optional for the two torch neural models. Use `-Device auto` only in an environment with a tested PyTorch installation. Check the environment inventory first. Device choice alters the model implementation and belongs in its own run. If CUDA memory is exhausted, use a new CPU run. Set the batch value in a **copy** of `configs/detection.json` and pass the copy via the direct detection CLI when experimenting with smaller neural batches.

```powershell
.\run_research_pipeline.ps1 -Full
.\resume_research_pipeline.ps1 -Full
.\run_research_pipeline.ps1 -Run local-seed43 -Seed 43
.\run_research_pipeline.ps1 -Run local-seed44 -Seed 44
```

Repeat seeds measure model randomisation on a fixed data split. Compare raw metrics in each run's `comparison.csv`. Repeated training leaves the common test set fixed. Independent data collections are needed to assess population variability.

The basic CPU configuration fit seven models within the bounded Linux experiment. Model timing is stored under each `results/v02/<run>/registry.json`; the bounded run took 3.6 aggregate model-seconds and the 132,175-row full filtered run took 41.0 aggregate model-seconds, excluding data preparation and the rest of the workflow. The external v2 transfer took 44.0 seconds on the Linux host. On an 8 GB Windows machine, allow several minutes for dependencies and data preparation; full-data models and slower disks can take substantially longer. These are planning estimates. Flow preprocessing uses disk-backed SQLite. Training loads the eligible numeric cohort into memory. ADFA-LD fits whole-trace models in memory; budget an estimated 400 MiB for the sequence job. Avoid concurrent full experiments on the laptop.

The cross-corpus NetFlow experiment is independent of the native UNSW and ADFA pipelines. For native v2, use the checksummed ZIP downloader below. Both ZIPs stay compressed during analysis. Alternatively, place the publisher CSVs in the paths from the table and supply those paths to the same runner. The script streams 50,000-row chunks and samples up to the specified cap per corpus. It reads both full files and can be I/O-bound. Use a fresh output directory per invocation. [Publisher NF-UNSW-NB15-v2](https://rdm.uq.edu.au/files/8c6e2a00-ef9c-11ed-827d-e762de186848) · [Publisher NF-CSE-CIC-IDS2018-v2](https://rdm.uq.edu.au/files/ce5161d0-ef9c-11ed-827d-e762de186848)

```powershell
$py = ".\.venv\Scripts\python.exe"
& $py scripts/download_nf_v2.py
& $py scripts/run_nf_shift.py --source data/raw/nf-v2/nf-unsw-nb15-v2.zip --target data/raw/nf-v2/nf-cse-cic-ids2018-v2.zip --output results/external/local-v2 --version v2 --cap 50000
```

To reproduce the separately versioned v3 pilot, use the released retrieval script and its matching CSV filenames:

```powershell
& $py scripts/fetch_nf_pilot.py --out data/raw/nf_pilot
& $py scripts/run_nf_shift.py --source data/raw/nf_pilot/NF-UNSW-NB15-v3.csv --target data/raw/nf_pilot/NF-CSE-CIC-IDS2018-v3.csv --output results/external/local-v3-pilot --version v3-pilot --cap 50000
```

Check `metrics.json`, `within_source.csv`, `external.csv` and `classifier.joblib` in each new external results directory. The cap is a sampling limit per corpus; it cannot enlarge the retrieved v3 pilot. Do not mix v2, v3 or native feature schemas.

## Direct recovery commands

Use a different simple name for an independent trial. For a readout of an existing run, use that exact name with the exporter and verifier. The following commands show each component's entry point:

```powershell
$py = ".\.venv\Scripts\python.exe"
$name = "local-manual"
& $py scripts/download_datasets.py --mode research
& $py -m sentinel_x.detection --input data/processed/research/events.csv --run $name --mode research --seed 42 --device cpu
& $py -m sentinel_x.behaviour --dataset adfa --out "results/v03/$name"
& $py -m sentinel_x.fusion --archive data/raw/ADFA-LD.zip --out "results/v03_fusion/$name"
& $py scripts/audit_detection.py --input data/processed/research/events.csv --results "results/v02/$name"
& $py scripts/audit_transformed_overlap.py --input data/processed/research/events.csv --results "results/v02/$name"
& $py -m sentinel_x.evidence.evaluate --output "results/v04/$name"
& $py -m sentinel_x.evidence.triage --predictions "results/v02/$name/predictions.csv" --output "results/v10/$name/triage"
& $py scripts/build_evidence_packet.py --predictions "results/v02/$name/predictions.csv" --events data/processed/research/events.csv --output "results/v10/$name/evidence_packet"
& $py scripts/export_research_results.py --run $name
& $py scripts/verify_results.py --run $name
& $py -m sentinel_x.dashboard --root . --port 8765
```

For offline interface testing use `--mode smoke` in data preparation and detection, `data/processed/smoke/events.csv` as detector input, and `--dataset fixture` for sequence modelling. Use `.\run_research_pipeline.ps1 -Run local-offline-sequences -Sequence fixture` if real sequence access remains unavailable and you wish to exercise all other research stages. Preserve the fixture provenance in downstream reports.

## Outputs and completion checks

| Location | Contents |
|---|---|
| `configs/`, `src/sentinel_x/`, `scripts/`, `tests/` | Frozen model settings, modules, runnable tools and automated tests. |
| `data/processed/<mode>/manifest.json` | Input versions, features, split counts, exclusions and CSV hash. |
| `results/v01/<run>/classical.csv` | Classical baseline comparison. |
| `results/v02/<run>/` | Registry, configuration spec, model checkpoints, comparison, reliability, risk/coverage, errors, attributions and scores. |
| `results/v03/<run>/` | Sequence summary, per-trace scores, transitions and manifest. |
| `results/v04/<run>/` | Investigation summary, cases, blinded review sheet and registry. |
| `results/v10/<run>/triage/` | Policy decisions, cited reports, summary and registry. |
| `reports/generated/<run>/` | Summary, comparison table and figures from stored metrics. |
| `results/workflow/<run>/<UTC attempt>/` | Per-stage logs, execution times, status and blocked dependencies. |

1. Check that the workflow command exits successfully, all stages in the latest `status.json` are `passed`, and the tests log reports the pass count. Distinguish a synthetic smoke run from a real research result.
2. Run `scripts/verify_results.py --run <run>`. Inspect the split counts, null/undefined rates, raw and calibrated model metrics, and cited-report JSONL. Review benchmark provenance before interpreting the results.
3. Launch the dashboard and confirm your run is selectable, displayed values match its CSV and a feedback edit survives refresh.
4. For human evidence review, give two reviewers copies of `review.csv`, the blinded `cases.jsonl` and the underlying fixture records. Withhold the condition mapping in `review_key.json`. Keep signed-off ratings separate, resolve disagreements, and report denominator, missing ratings and adjudication. The evaluation protocol defines the criteria. No software command substitutes for this study. [Evidence protocol](../protocols/EVIDENCE_AND_TRIAGE.md)
5. A successful software run supports reproduction of the stated experiments. Study outcomes on real analyst performance require independent participants and appropriate incident data.

### Independent rating files

After each reviewer has completed their own copy for the v0.4 controlled cases, run:

```powershell
& $py scripts/score_evidence_reviews.py reviewer_A.csv reviewer_B.csv --key results/v04/evidence/review_key.json --output ratings_initial.json
```

Use yes, no, unclear or na for each rating and one reviewer identifier per file. Inspect the disagreements in the output JSON. A third named adjudicator fills a complete sheet of the same format, retaining all agreements and resolving flagged items. Supply it with `--adjudication adjudicated.csv --output ratings_adjudicated.json` when ready. Use a fresh output filename. The separately blinded real-flow packet under `results/v10/<run>/evidence_packet` is exploratory and has a distinct review form.

## Resume and troubleshoot

For a stopped bounded run, use `.\resume_research_pipeline.ps1`. Include the original `-Full`, `-Seed`, `-Device`, `-Sequence` and `-Run` arguments if changed. For interrupted smoke use `.\run_smoke_tests.ps1 -Resume`. At model boundaries the detector saves its fitted object and result metadata; completed checksummed models are reused. Other stages verify complete outputs or regenerate inexpensive summaries. Each workflow attempt gets a fresh log directory. If only one stage failed, the independent stages still run when their own prerequisites pass. Read the first failed log; a blocked stage's status lists the failed prerequisite.

* **Missing dependencies.** Run setup from the extracted repository with 64-bit Python. An existing virtual environment retains its original interpreter; move the environment aside before recreating it. For a first-time install the package index must be accessible.
* **Fingerprint mismatch or interrupted write.** Preserve the suspect directory under a new name, then recreate the cache from the pinned source in the audit. For an experiment whose inputs, code or settings changed, choose a fresh run name. Model files use Python serialization; use only checkpoints you created or verified from the delivered archive.
* **Memory pressure or slow training.** Close competing workloads, choose bounded research and CPU, and review per-model durations and warnings in the registry. The external pilot cap may be reduced for a separately labelled trial. A lower cap can leave very few positive rows.
* **Evidence or sequence retrieval failure.** The workflow records independent stage outcomes. The evidence fixtures are offline. For real sequence replication restore the pinned archive in the table and rerun with the same settings. Do not relabel a synthetic result as a real-data experiment.
* **Labelling and chronology.** UNSW flow predictions have no reconstructed session timeline. ADFA-LD has ordered syscall tokens within a trace. An abstention or missing chronology on a flow record is a legitimate outcome.

### Optional local model and single-record inspection

With the environment installed, run the following from the project root. The first command exercises the deterministic investigation directly. If you already have a running local Ollama service and an installed model, supply its exact model name to request an ordering of the existing supported observations. Only field names are sent. The command neither downloads a model nor creates additional observations. An unreachable provider returns a report marked offline_fallback.

```powershell
& .\.venv\Scripts\python.exe scripts/investigate_record.py --event e2
& .\.venv\Scripts\python.exe scripts/investigate_record.py --event e2 --local-model YOUR_INSTALLED_MODEL
```

The alpha-numeric IDs in these examples belong to the synthetic evidence fixture. Use --records with a JSON list of your own authorized offline records and --event with the corresponding ID to inspect another dataset. The dashboard uses its stored prediction records directly.
