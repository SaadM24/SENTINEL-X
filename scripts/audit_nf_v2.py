"""Verify binary categories on the complete archives and bootstrap held-out predictions."""
import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from download_nf_v2 import ARCHIVES, check

# Raw full-volume counts from UQ's v2 catalogue (not evaluation denominators).
EXPECTED = {
    "nf-unsw-nb15-v2": (2390275, 95053),
    "nf-cse-cic-ids2018-v2": (18893708, 2258141),
}


def audit_sources(directory):
    audit = {}
    for slug, sha in ARCHIVES.items():
        path = directory / (slug + ".zip")
        check(path, sha)
        counts = Counter()
        for group in pd.read_csv(path, usecols=["Label","Attack"], chunksize=250000):
            if group.isna().any().any() or not group.Label.isin([0,1]).all():
                raise ValueError(f"Missing or nonbinary ground truth in {slug}")
            benign = group.Attack.str.strip().str.lower().eq("benign")
            if not benign.eq(group.Label.eq(0)).all():
                raise ValueError(f"Category/label mismatch in {slug}")
            counts.update(group.Attack.value_counts().to_dict())
        total = sum(counts.values())
        attacks = total - counts["Benign"]
        if (total, attacks) != EXPECTED[slug]:
            raise ValueError("Source volume or class balance mismatch")
        audit[path.name] = {"bytes":path.stat().st_size,"categories":dict(counts),"total":total,"attack":attacks,
                            "unique_label_definition":"Benign iff Label equals zero on every row"}
    return audit


def bootstrap(directory, draws, seed):
    if draws < 100:
        raise ValueError("Use at least 100 replicates")
    rng = np.random.default_rng(seed)
    scores = {}
    for cohort in ["within_source","external"]:
        data = pd.read_csv(directory/(cohort+".csv"))
        y, p = data.label.to_numpy(), data.probability.to_numpy()
        groups = [np.flatnonzero(y == c) for c in [0,1]]
        if any(not len(g) for g in groups) or sum(map(len,groups)) != len(y):
            raise ValueError("Both binary classes required")
        trials = []
        for _ in range(draws):
            ids = np.concatenate([rng.choice(g,size=len(g),replace=True) for g in groups])
            yc, pc = y[ids], p[ids]
            trials.append([roc_auc_score(yc,pc), average_precision_score(yc,pc),
                           brier_score_loss(yc,pc), np.mean(pc[yc==0]>=.5)])
        scores[cohort] = np.array(trials)
    scores["external_minus_within"] = scores["external"] - scores["within_source"]
    intervals = {}
    for cohort, matrix in scores.items():
        limits = np.quantile(matrix,[.025,.975],axis=0)
        intervals[cohort] = dict(zip(["roc_auc","average_precision","brier","fpr"], limits.T.tolist()))
    return {"seed":seed,"draws":draws,"interval":"2.5% and 97.5% sample percentiles, independent within-class resampling by cohort",
            "scope":"Conditional on fitted model, selected records, fixed empirical prevalence and independent vectors. No host grouping, retraining or future-site uncertainty.",
            "intervals":intervals}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archives", type=Path, default=Path("data/raw/nf-v2"))
    parser.add_argument("--run", type=Path, default=Path("results/external/nf-v2"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--draws", type=int, default=500)
    args = parser.parse_args()
    result = {"sources":audit_sources(args.archives),"conditional_intervals":bootstrap(args.run,args.draws,119)}
    with args.output.open("x",encoding="utf-8") as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write("\n")
