"""Execute the frozen sequence ablation and preserve trace-level evidence."""
import argparse
import csv
import hashlib
import json
import platform
from pathlib import Path
import time

import numpy as np
import sklearn
from sklearn.metrics import (average_precision_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)

from .dataset import ARCHIVE_SHA, ARCHIVE_URL, adfa, digest, fixture, partition
from .model import TraceModel


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_out(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8")


def csv_out(path, headers, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def metrics(labels, scores, threshold):
    predicted = scores > threshold
    matrix = confusion_matrix(labels, predicted, labels=[0, 1])
    tn, fp, fn, tp = matrix.ravel()
    return {"roc_auc": float(roc_auc_score(labels, scores)),
            "average_precision": float(average_precision_score(labels, scores)),
            "macro_f1": float(f1_score(labels, predicted, average="macro")),
            "precision": float(precision_score(labels, predicted, zero_division=0)),
            "recall": float(recall_score(labels, predicted)),
            "false_positive_rate": float(fp / (fp + tn)), "confusion_matrix": matrix.tolist(),
            "threshold": float(threshold)}


def run(out, dataset, archive):
    out = Path(out)
    here = Path(__file__).parent
    config = {"dataset": dataset, "archive_sha256": ARCHIVE_SHA if dataset == "adfa" else None,
              "alpha": 0.5, "calibration_quantile": 0.95, "fixture_seed": 216,
              "module_sha256": {p.name: checksum(p) for p in here.glob("*.py")}}
    manifest = out / "manifest.json"
    if manifest.is_file():
        old = json.loads(manifest.read_text())
        if (old["configuration"] == config and
                all(checksum(out / p) == h for p, h in old["files"].items())):
            return json.loads((out / "summary.json").read_text())
        raise ValueError("existing result has a different fingerprint; choose a new --out")
    # Re-run incomplete stages in a new directory; never modify a released result.
    if out.exists() and any(out.iterdir()):
        raise ValueError("incomplete or unrelated outputs; choose a fresh --out")
    out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    records = adfa(archive) if dataset == "adfa" else fixture()
    train, cal, test, audit = partition(records)
    model = TraceModel().fit(r.tokens for r in train)
    cal_scores = np.array([model.score(row.tokens)[:2] for row in cal])
    cutoffs = np.quantile(cal_scores, 0.95, axis=0, method="higher")
    all_scores = [model.score(row.tokens) for row in test]
    scores = np.array([s[:2] for s in all_scores])
    labels = np.array([r.label for r in test])
    families = np.array([r.family for r in test])
    groups = sorted(set(families) - {"benign"})
    evaluations = {}
    for i, name in enumerate(("unigram", "markov")):
        values = metrics(labels, scores[:, i], cutoffs[i])
        values["family_recall"] = {
            str(g): {"n": int((families == g).sum()),
                     "recall": float((scores[families == g, i] > cutoffs[i]).mean())}
            for g in groups}
        evaluations[name] = values
    csv_out(out / "scores.csv", ["trace_id","family","label","length","unigram","markov",
            "unigram_alarm","markov_alarm","rarest_edge_target_index","source","target"],
            ([r.name,r.family,r.label,len(r.tokens),s[0],s[1],int(s[0]>cutoffs[0]),
              int(s[1]>cutoffs[1]),s[2],*s[3]] for r,s in zip(test,all_scores)))
    csv_out(out / "partitions.csv", ["partition","trace_id","token_sha256","n_tokens","label"],
            ([part,r.name,digest(r.tokens),len(r.tokens),r.label]
             for part,rows in (("train",train),("calibration",cal),("test",test)) for r in rows))
    csv_out(out / "transitions.csv", ["source","target","count","probability"],
            ([s,t,n,model.probability(s,t)] for (s,t),n in sorted(model.edges.items())))
    json_out(out / "model.json", {"alpha": model.alpha, "tokens": model.tokens,
             "edges": [[s,t,n] for (s,t),n in sorted(model.edges.items())],
             "reserved": {"start":-1,"end":-2,"unknown":-3}})
    summary = {"dataset": "ADFA-LD (pinned mirror)" if dataset == "adfa" else "synthetic-order-fixture",
               "counts": {"train":len(train),"calibration":len(cal),"test":len(test),
                          "test_positive":int(labels.sum())}, "audit":audit,"metrics":evaluations,
               "delta_average_precision_markov_minus_unigram":
                   evaluations["markov"]["average_precision"] - evaluations["unigram"]["average_precision"]}
    json_out(out / "summary.json",summary)
    files = {f.name:checksum(f) for f in sorted(out.iterdir()) if f.is_file()}
    json_out(manifest, {"experiment_id": "E4-"+dataset, "configuration":config, "status":"executed",
                        "metrics":"summary.json","duration_s":time.perf_counter()-started,
                        "environment":{"python":platform.python_version(),"sklearn":sklearn.__version__,
                                       "numpy":np.__version__,"platform":platform.platform()},
                        "split_protocol":"docs/protocols/SEQUENCE_PROTOCOL.md",
                        "limitations":["scenario-level weak labels","no wall-clock time",
                                       "dependent processes within scenario"] if dataset=="adfa" else
                                      ["order anomaly encoded by generator"],
                        "url": ARCHIVE_URL if dataset == "adfa" else None, "files":files})
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=["fixture","adfa"], default="fixture")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--archive", type=Path, default=Path("data/raw/ADFA-LD.zip"))
    args = parser.parse_args()
    print(json.dumps(run(args.out, args.dataset, args.archive), indent=2))
