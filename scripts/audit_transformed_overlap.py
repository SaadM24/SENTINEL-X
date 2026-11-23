"""Check whether clipping and float32 conversion introduce identical model inputs."""
import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


def audit(source, result):
    result = Path(result)
    records = pd.read_csv(source)
    checkpoint = joblib.load(result/'logistic.joblib')
    x = records[checkpoint['features']].to_numpy(dtype=np.float32)
    xx = checkpoint['preprocessor'].transform(x)
    keys = pd.util.hash_pandas_object(pd.DataFrame(xx),index=False)
    rows = []
    for a,b in [('train','cal'),('train','test'),('cal','test')]:
        prior = set(keys[records.split==a])
        later = keys[records.split==b]
        hits = later.isin(prior)
        rows.append(dict(reference=a,query=b,query_rows=len(later),matching_query_rows=int(hits.sum()),
                         fraction=float(hits.mean())))
    pd.DataFrame(rows).to_csv(result/'transformed_overlap.csv',index=False)
    score_errors(records, xx, keys, checkpoint, result)


def score_errors(records, xx, keys, checkpoint, result):
    from sentinel_x.detection.metrics import assess
    test_mask = records.split.eq('test').to_numpy()
    earlier = set(keys[~test_mask])
    novel = (~keys[test_mask].isin(earlier)).to_numpy()
    y = records.label.to_numpy()[test_mask]
    raw = checkpoint['model'].predict_proba(xx[test_mask])[:,1]
    p = checkpoint['calibrators']['platt'].predict(raw)
    rows = []
    for tag, mask in [('all', np.ones(len(y), dtype=bool)), ('unseen_transformed_vector', novel)]:
        rows.append(dict(population=tag,n=int(mask.sum()),**assess(y[mask],p[mask])))
    pd.DataFrame(rows).to_csv(result/'overlap_sensitivity.csv',index=False)
    contributions = xx[test_mask]*checkpoint['model'].coef_[0]
    rows = []
    for tag, mask in [('false_positive',(p>=.5)&(y==0)),('true_negative',(p<.5)&(y==0)),
                      ('false_negative',(p<.5)&(y==1)),('true_positive',(p>=.5)&(y==1))]:
        for i, feature in enumerate(checkpoint['features']):
            rows.append(dict(decision=tag,n=int(mask.sum()),feature=feature,
                             mean_signed_logit_contribution=float(contributions[mask,i].mean()) if mask.any() else None))
    pd.DataFrame(rows).to_csv(result/'error_contributions.csv',index=False)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True)
    parser.add_argument('--results',required=True)
    args = parser.parse_args()
    audit(args.input,args.results)
