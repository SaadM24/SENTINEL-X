# Local security analytics dashboard

Run `python -m sentinel_x.dashboard --root . --port 8765` from the project root after installation. Visit [the local dashboard](http://127.0.0.1:8765). Stop the process with Ctrl+C. The server binds to IPv4 loopback and checks Host and Origin headers. Its static assets load from the installed package. It reads results in the specified project directory. The application uses Python's HTTP server, CSV reader and SQLite module, and plain browser JavaScript. No external service or CDN is required.

## Reading the views

* **Overview** shows the test event count, true attack count, number of evaluated detection architectures and number of distinct events receiving feedback. The model table and confusion matrix share a calibration selector. The category counts describe the published test sample.
* **Model reliability** reads populated calibration bins and realised risk and coverage under the registered budget thresholds. A point on a curve represents an aggregate over the held-out sample. The metrics in this view cannot establish a prospective analyst workload.
* **Alert triage** ranks stored prediction rows by distance from 0.5, with event ID tie-breaking. The queue and report exclude benchmark categories and target labels. Model scores observed in the predictions file carry the associated ID as a citation. A report displays uncertainty, retrieved evidence and any admissible timestamped timeline. Independent UNSW observations have no inferred chronology. A separately marked synthetic fixture demonstrates session correlation and timelines.
* **Event sequences** reads the behavioural experiment independently of the selected detection run. The directed edges represent the twelve most frequent observed training transitions. The sequence model table includes measured average precision and ROC AUC.
* **Reproducibility** displays the selected run's experiment registry, with its environment, sample manifest, hashes and reported limitations as supplied by the pipeline.

## Data and feedback

A new run becomes visible on page reload after both `results/v02/<run>/comparison.csv` and `predictions.csv` exist. Keep finished run directories immutable and use distinct run names for new inputs. The server accepts run names only from the discovered set. Tables and charts read stored CSVs, and investigation reuses the evidence module. Behaviour uses `results/v03/summary.json` and `transitions.csv`.

Feedback is stored in `outputs/feedback.sqlite3`, keyed by run, event ID and revision. Each save appends a revision under an immediate SQLite transaction. Concurrent edits with a stale revision receive HTTP 409. Refresh, reopen the event, reconcile the change and save again. There is no automatic retraining from feedback. Back up this database separately if annotation is valuable. This is a single-machine study interface. The application has no multi-user authentication or reviewer-identity model.

## Interface

| Route | Purpose |
|---|---|
| GET /api/runs | Discover stored detection runs |
| GET /api/overview?run=NAME | Metrics, counts, risk, calibration and registry |
| GET /api/queue?run=NAME | 25 records; optional q, decision and offset parameters |
| GET /api/evidence?run=NAME&event=ID | Projected evidence and deterministic investigation |
| GET /api/fixture-ids | Available synthetic example anchors |
| GET /api/behaviour | Sequence experiment summary and transitions |
| POST /api/feedback | JSON run, event_id, decision, note and integer version; start at 0 |

## Verification

Four HTTP-level tests exercise temporary artifacts, queue ranking, grounding, durable writes, conflict handling, rejected foreign origins and unknown runs. A real research run was inspected through Chromium headless shell at widths of 1380 and 390 pixels. The check exercises a feedback correction on a temporary data copy. A separate DOM check verifies navigation, chart construction, case reports and a fixture timeline. Logs, screenshot and machine-readable results are in `results/v05/`. The system Chromium executable failed during startup on a sandbox-restricted singleton socket. Headless-shell Chromium 138 completed the same test. These checks establish software behaviour only. No independent analyst usability, investigation-time or productivity measurements were collected.

To rerun the optional visual check on Windows, install Playwright into the project environment with `python -m pip install playwright`, run `python -m playwright install chromium`, then run `python scripts/check_dashboard_browser.py --output outputs/browser-check`. You can specify an installed compatible browser with `--chromium <executable>`.
