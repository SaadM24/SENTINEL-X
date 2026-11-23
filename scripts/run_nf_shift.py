"""Compare within-source and cross-corpus performance using identical NetFlow features."""
import argparse
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from fetch_nf_pilot import FEATURES

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as s:
        for chunk in iter(lambda: s.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def sample(path, limit, seed):
    """Use iid priorities to bound RAM when sampling very large CSVs."""
    rng = np.random.default_rng(seed)
    kept = pd.DataFrame()
    total = 0
    for block in pd.read_csv(path, usecols=FEATURES+["Label"], chunksize=50000):
        total += len(block)
        if not block.Label.isin([0,1]).all():
            raise ValueError("Expected binary integer labels")
        block[FEATURES] = block[FEATURES].apply(pd.to_numeric, errors="raise")
        if not np.isfinite(block[FEATURES]).all().all() or (block[FEATURES] < 0).any().any():
            raise ValueError("Invalid flow measurements")
        block["_priority"] = rng.random(len(block))
        kept = pd.concat([kept, block]).nsmallest(limit, "_priority")
    sampled = len(kept)
    groups = kept.groupby(FEATURES, sort=False).Label.agg(["min","max"])
    good = groups.loc[groups["min"] == groups["max"], ["min"]].rename(columns={"min":"Label"}).reset_index()
    return good, dict(raw=total, sampled=sampled, distinct_vectors=len(groups),
                      contradictory_vectors=int((groups["min"] != groups["max"]).sum()), retained=len(good)), groups.index

def scores(y, p):
    tn, fp, fn, tp = confusion_matrix(y, p >= .5, labels=[0,1]).ravel().tolist()
    both = len(set(y)) == 2
    return dict(n=len(y), prevalence=float(np.mean(y)), tn=tn, fp=fp, fn=fn, tp=tp,
                average_precision=float(average_precision_score(y,p)) if both else None,
                roc_auc=float(roc_auc_score(y,p)) if both else None, brier=float(brier_score_loss(y,p)),
                recall=tp/(tp+fn) if tp+fn else None, fpr=fp/(fp+tn) if fp+tn else None)

def main(source, target, output, cap=50000, version="v2"):
    started = time.perf_counter()
    if output.exists():
        raise FileExistsError(f"Choose an unused results directory: {output}")
    if source.resolve()==target.resolve() or digest(source)==digest(target):
        raise ValueError("Source and target must be two distinct corpora")
    a, sa, source_groups = sample(source,cap,71)
    b, sb, _ = sample(target,cap,72)
    overlap = b.set_index(FEATURES).index.isin(source_groups)
    b = b.loc[~overlap]
    train, test = train_test_split(a, test_size=.25, stratify=a.Label, random_state=23)
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=500,random_state=23))
    model.fit(np.log1p(train[FEATURES]),train.Label)
    result = dict(dataset_version=version, source=source.name,target=target.name,
                  sha256=[digest(source),digest(target)], features=FEATURES, seed=23, cap=cap,
                  source_counts=sa,target_counts=sb,target_overlap_removed=int(overlap.sum()), n_fit=len(train))
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as t:
        stage=Path(t)/"run"
        stage.mkdir()
        for name,frame in [("within_source",test),("external",b)]:
            p=model.predict_proba(np.log1p(frame[FEATURES]))[:,1]
            result[name]=scores(frame.Label,p)
            pd.DataFrame({"label":frame.Label,"probability":p}).to_csv(stage/f"{name}.csv",index=False)
        result["wall_seconds"]=time.perf_counter()-started
        (stage/"metrics.json").write_text(json.dumps(result,indent=2,allow_nan=False))
        joblib.dump(model,stage/"classifier.joblib")
        os.rename(stage,output)
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for k in ["source","target","output"]:
        p.add_argument("--"+k,type=Path,required=True)
    p.add_argument("--cap",type=int,default=50000)
    p.add_argument("--version",choices=["v2","v3-pilot"],default="v2")
    main(**vars(p.parse_args()))
