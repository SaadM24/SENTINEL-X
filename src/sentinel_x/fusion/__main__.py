"""Exploratory supervised combination of syscall counts and adjacent-event surprise."""
import argparse
from collections import Counter, defaultdict
import hashlib
from pathlib import Path
import platform
import time

import numpy as np
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss, confusion_matrix,
                             roc_auc_score)
from sklearn.preprocessing import StandardScaler

from sentinel_x.behaviour.dataset import ARCHIVE_SHA, adfa, digest
from sentinel_x.behaviour.model import TraceModel
from sentinel_x.behaviour.__main__ import json_out, csv_out, checksum


def salted(value):
    return hashlib.sha256(("sentinel-fusion-216|" + value).encode()).hexdigest()


def groupsplit(keys):
    ordered = sorted(set(keys), key=salted)
    return {key: ("test" if i % 5 == 0 else "calibration" if i % 5 == 1 else "fit")
            for i,key in enumerate(ordered)}


def supervised_parts(records):
    density, held = {}, defaultdict(list)
    for row in records:
        key = digest(row.tokens)
        if row.partition == "development":
            if row.label:
                raise ValueError("density pool must be benign")
            density.setdefault(key,row)
        else:
            held[key].append(row)
    audit = Counter()
    kept = []
    for key, rows in sorted(held.items()):
        if key in density:
            audit["overlapping_rows_removed"] += len(rows)
            continue
        if len({r.label for r in rows}) > 1:
            audit["conflicting_rows_removed"] += len(rows)
            continue
        groups = {Path(r.name).parent.name for r in rows if r.label}
        if len(groups) > 1:
            audit["ambiguous_scenario_rows_removed"] += len(rows)
            continue
        row = min(rows,key=lambda r:r.name)
        kept.append((key,row,next(iter(groups),key)))
        audit["duplicate_rows_removed"] += len(rows)-1
    families = defaultdict(list)
    for _, row, group in kept:
        families[row.family].append(group)
    assignments = {family:groupsplit(groups) for family,groups in families.items()}
    parts = defaultdict(list)
    for key,row,group in kept:
        parts[assignments[row.family][group]].append((key,row,group))
    return density, parts, dict(audit)


def feature_table(rows,vocab,model):
    x = np.zeros((len(rows),len(vocab)+2))
    for i, (_,r,_) in enumerate(rows):
        for token,count in Counter(r.tokens).items():
            x[i,vocab.get(token,len(vocab))] += count/len(r.tokens)
        x[i,-1] = model.score(r.tokens)[1]
    return x


def reliability(p,y):
    bucket = np.minimum(np.floor(p*10).astype(int),9)
    ece = sum(np.sum(bucket==i)*abs(p[bucket==i].mean()-y[bucket==i].mean())
              for i in np.unique(bucket))/len(y)
    return {"brier":float(brier_score_loss(y,p)),"ece10":float(ece)}


def coverage(errors,review):
    return {"review_n":int(review.sum()),"coverage":float((~review).mean()),
            "accepted_n":int((~review).sum()),"accepted_errors":int(errors[~review].sum()),
            "accepted_error_rate":float(errors[~review].mean()) if (~review).any() else None}


def run(out, archive):
    out = Path(out)
    code = Path(__file__)
    base = code.parent.parent / "behaviour"
    config = {"corpus_sha256":ARCHIVE_SHA,"seed_salt":"sentinel-fusion-216","C":1,
              "protocol":"docs/protocols/FUSION_PROTOCOL.md","code":checksum(code),
              "density_code":checksum(base/"model.py"),"dataset_code":checksum(base/"dataset.py")}
    if (out/"manifest.json").exists():
        import json
        old = json.loads((out/"manifest.json").read_text())
        if old["configuration"] != config or any(checksum(out/k)!=v for k,v in old["files"].items()):
            raise ValueError("fusion results differ; use new output directory")
        return json.loads((out/"summary.json").read_text())
    if out.exists() and any(out.iterdir()):
        raise ValueError("requested output is nonempty")
    out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    density,parts,audit = supervised_parts(adfa(archive))
    model = TraceModel().fit(r.tokens for r in density.values())
    vocab = {t:i for i,t in enumerate(sorted(t for t in model.alphabet if t>=0))}
    features = {k:feature_table(rows,vocab,model) for k,rows in parts.items()}
    labels = {k:np.array([r.label for _,r,_ in rows]) for k,rows in parts.items()}
    y = labels["test"]
    estimates, coefficients, paired = {}, {}, {}
    for name in ("frequencies","frequencies_markov"):
        x = features if name=="frequencies_markov" else {k:a[:,:-1] for k,a in features.items()}
        scaler = StandardScaler().fit(x["fit"])
        scaled = {k:scaler.transform(a) for k,a in x.items()}
        classifier = LogisticRegression(C=1,max_iter=2000).fit(scaled["fit"],labels["fit"])
        if classifier.n_iter_.max()>=2000:
            raise RuntimeError("fit failed convergence")
        raw = classifier.predict_proba(scaled["test"])[:,1]
        # Effectively unregularized two-parameter sigmoid on development-only scores.
        platt = LogisticRegression(C=1e6,max_iter=2000).fit(
            classifier.decision_function(scaled["calibration"]).reshape(-1,1),labels["calibration"])
        def prob(split):
            return platt.predict_proba(classifier.decision_function(scaled[split]).reshape(-1,1))[:,1]
        p = prob("test")
        confidence = np.maximum(p,1-p)
        pc = prob("calibration")
        cutoff = float(np.quantile(np.maximum(pc,1-pc),0.20,method="lower"))
        queue = sorted(range(len(y)), key=lambda i:(confidence[i],salted(parts["test"][i][0])))
        review = np.zeros(len(y),dtype=bool)
        review[queue[:int(0.20*len(y))]] = True
        errors = (p>=0.5)!=y
        estimates[name] = {"ap":float(average_precision_score(y,p)),"roc_auc":float(roc_auc_score(y,p)),
                           "raw":reliability(raw,y),"calibrated":reliability(p,y),
                           "error":float(errors.mean()),
                           "confusion_matrix":confusion_matrix(y,p>=0.5).tolist(),
                           "confidence_cutoff":cutoff,"development_cutoff":coverage(errors,confidence<=cutoff),
                           "fixed_queue_budget":coverage(errors,review)}
        coefficients[name] = {"mean":scaler.mean_.tolist(),"scale":scaler.scale_.tolist(),
                              "coef":classifier.coef_[0].tolist(),"intercept":float(classifier.intercept_[0]),
                              "platt_slope":float(platt.coef_[0,0]),"platt_intercept":float(platt.intercept_[0])}
        paired[name] = list(zip(raw,p,(confidence<=cutoff).astype(int),review.astype(int)))
    csv_out(out/"scores.csv",["digest","trace_id","family","scenario_or_digest","label"]+
            [f"{name}_{field}" for name in paired for field in ("raw","calibrated","review","queue_review")],
            ([key,row.name,row.family,group,row.label,*(v for scores in paired.values() for v in scores[i])]
             for i,(key,row,group) in enumerate(parts["test"])))
    csv_out(out/"partitions.csv",["partition","digest","trace_id","family","scenario_or_digest","label"],
            ([split,key,row.name,row.family,group,row.label] for split,rows in
             ({"density":[(k,r,k) for k,r in density.items()]}|parts).items() for key,row,group in rows))
    json_out(out/"model.json",{"density":{"alpha":model.alpha,
             "edges":[[s,t,n] for (s,t),n in sorted(model.edges.items())]},
             "vocabulary":vocab,"models":coefficients,"features":"ordered vocabulary, unknown, optional markov"})
    summary = {"metrics":estimates,"audit":audit,"density_unique":len(density),
               "counts":{k:{"n":len(v),"positive":int(v.sum())} for k,v in labels.items()},
               "status":"executed; exploratory reuse of ADFA-LD, weak scenario labels"}
    json_out(out/"summary.json",summary)
    json_out(out/"manifest.json",{"experiment_id":"E4-fusion","status":"executed","configuration":config,
             "dataset":"ADFA-LD","duration_s":time.perf_counter()-started,"python":platform.python_version(),
             "numpy":np.__version__,"sklearn":sklearn.__version__,
             "files":{p.name:checksum(p) for p in sorted(out.iterdir()) if p.is_file()}})
    return summary


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive",type=Path,default=Path("data/raw/ADFA-LD.zip"))
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    print(run(args.out,args.archive))
