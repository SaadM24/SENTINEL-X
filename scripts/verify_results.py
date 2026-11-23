"""Audit results without deserializing executable model objects."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, confusion_matrix, f1_score, roc_auc_score

def require(condition, message):
    if not condition:
        raise ValueError(message)

def sha(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source,"sha256").hexdigest()

def verify(folder):
    reg=json.loads((folder/"registry.json").read_text())
    pred=pd.read_csv(folder/"predictions.csv")
    comp=pd.read_csv(folder/"comparison.csv").set_index(["model","calibration"],verify_integrity=True)
    n=reg["split_counts"]["test"]
    require(len(pred)==n and pred.event_id.is_unique,"Wrong test count or duplicate ID")
    require(pred.y_true.isin([0,1]).all(), "Invalid truth labels")
    require(len(comp)==28,"Missing model/calibration pairs")
    require((comp[["tn","fp","fn","tp"]].sum(axis=1)==n).all(),"Confusion total mismatch")
    require(np.allclose(comp.fp/(comp.fp+comp.tn),comp.fpr),"FPR mismatch")
    require(np.allclose(comp.fpr*1000,comp.false_alarms_per_1000),"False-alarm units mismatch")
    for tag,column in [("platt","probability"),("raw","raw_probability")]:
        p=pred[column]
        y=pred.y_true
        require(p.between(0,1).all(),"Invalid probability")
        row=comp.loc[("logistic",tag)]
        # Restore IEEE doubles exactly when threshold ties exist.
        precise=pd.read_csv(folder/"predictions.csv",float_precision="round_trip")[column]
        decision=precise>=.5
        require(np.array_equal(confusion_matrix(y,decision,labels=[0,1]).ravel(),row[["tn","fp","fn","tp"]]),"Primary confusion mismatch")
        for field,actual in {"average_precision":average_precision_score(y,precise),"brier":brier_score_loss(y,precise),
                             "roc_auc":roc_auc_score(y,precise),"macro_f1":f1_score(y,decision,average="macro")}.items():
            require(np.isclose(row[field],actual),f"Primary {field} mismatch")
    for run in reg["runs"]:
        require(run["status"]=="executed","Incomplete model run")
        require(sha(folder/Path(run["checkpoint"]).name)==run["checkpoint_sha256"],"Checkpoint digest mismatch")
    bins=pd.read_csv(folder/"reliability.csv")
    require((bins.groupby(["model","calibration"])["count"].sum()==n).all(),"Bin totals mismatch")
    coverage=pd.read_csv(folder/"coverage.csv")
    require(np.allclose(1-coverage.review_count/n,coverage.coverage),"Coverage mismatch")
    print(f"{folder.name}: verified {n} predictions, 28 comparison rows, seven checkpoint hashes")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",type=Path,default=Path.cwd())
    p.add_argument("--run")
    args=p.parse_args()
    base=args.root/"results/v02"
    folders=[base/args.run] if args.run else sorted(f.parent for f in base.glob("*/registry.json"))
    require(bool(folders),"No experiment registry found")
    for folder in folders:
        verify(folder)
    manifest=args.root/"releases/archive_sha256.json"
    if not args.run and manifest.exists():
        entries=json.loads(manifest.read_text())
        for path,expected in entries.items():
            require(sha(args.root/path)==expected,f"Release digest mismatch: {path}")
        print(f"{len(entries)} packaged file hashes match")

if __name__=="__main__":
    main()
