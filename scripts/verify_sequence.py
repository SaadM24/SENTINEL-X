"""Independent checks against the stored ADFA-LD trace and fusion score tables."""
import csv
import json
from hashlib import sha256
from pathlib import Path
import argparse
import numpy as np
from sklearn.metrics import average_precision_score, confusion_matrix, brier_score_loss


def read(path):
    with path.open(encoding="utf-8",newline="") as f:
        return list(csv.DictReader(f))


def verify(path, fusion=False):
    manifest=json.loads((path/"manifest.json").read_text())
    for name, ref in manifest["files"].items():
        if sha256((path/name).read_bytes()).hexdigest()!=ref:
            raise ValueError(f"checksum mismatch: {name}")
    parts=read(path/"partitions.csv")
    keys=[r["digest" if fusion else "token_sha256"] for r in parts]
    if len(keys)!=len(set(keys)):
        raise ValueError("cross-partition or within-partition repeated traces")
    rows=read(path/"scores.csv")
    ids = {r["trace_id"] for r in parts if r["partition"]=="test"}
    if len(ids)!=len(rows) or ids!={r["trace_id"] for r in rows}:
        raise ValueError("test rows and scores disagree")
    y=np.array([int(r["label"]) for r in rows])
    summary=json.loads((path/"summary.json").read_text())
    for name,m in summary["metrics"].items():
        col=name+"_calibrated" if fusion else name
        p=np.array([float(r[col]) for r in rows])
        np.testing.assert_allclose(m["ap" if fusion else "average_precision"], average_precision_score(y,p))
        decisions=(p>=.5) if fusion else (p>m["threshold"])
        np.testing.assert_array_equal(m["confusion_matrix"],confusion_matrix(y,decisions))
        if fusion:
            np.testing.assert_allclose(m["calibrated"]["brier"],brier_score_loss(y,p))
            accepted=np.array([r[name+"_queue_review"]=="0" for r in rows])
            np.testing.assert_allclose(m["fixed_queue_budget"]["accepted_error_rate"],
                                       np.mean((y!=decisions)[accepted]))
    if fusion:
        groups={}
        for r in parts:
            if r["label"]=="1":
                g=r["scenario_or_digest"]
                if g in groups and groups[g]!=r["partition"]:
                    raise ValueError("cross-partition scenario")
                groups[g]=r["partition"]
    print(f"{path}: hashes, unique splits and paired metrics verified ({len(rows)} scores)")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sequence",type=Path, default=Path("results/v03"))
    p.add_argument("--fusion",type=Path,default=Path("results/v03_fusion"))
    args=p.parse_args()
    verify(args.sequence)
    verify(args.fusion,True)
