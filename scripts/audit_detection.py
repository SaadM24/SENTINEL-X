"""Replay trusted local checkpoints and check stored decision counts and reliability summaries."""
import argparse
import json
import math
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report
from threadpoolctl import threadpool_limits

from sentinel_x.detection.__main__ import digest


def replay(folder, source):
    folder = Path(folder)
    spec = json.loads((folder/'spec.json').read_text())
    if digest(source) != spec['dataset_sha256']:
        raise ValueError('Dataset hash differs from the frozen run')
    records = pd.read_csv(source)
    test = records.loc[records.split.eq('test')]
    cal = records.loc[records.split.eq('cal')]
    y = test.label.to_numpy()
    table = pd.read_csv(folder/'comparison.csv').set_index(['model','calibration'])
    review = pd.read_csv(folder/'coverage.csv')
    checkpoints = json.loads((folder/'registry.json').read_text())['runs']
    checked = []
    per_class = []
    for item in checkpoints:
        name = item['model']
        path = folder / (name+'.joblib')
        if digest(path) != item['checkpoint_sha256']:
            raise ValueError('Checkpoint hash differs: '+name)
        checkpoint = joblib.load(path)
        pipe = checkpoint['preprocessor']
        features = checkpoint['features']
        x = pipe.transform(test[features].to_numpy(dtype='float32'))
        xc = pipe.transform(cal[features].to_numpy(dtype='float32'))
        model = checkpoint['model']
        raw = model.predict_proba(x)[:,1]
        rawcal = model.predict_proba(xc)[:,1]
        for method, mapper in checkpoint['calibrators'].items():
            p = mapper.predict(raw)
            c = mapper.predict(rawcal)
            pred = p >= .5
            row = table.loc[(name, method)]
            pairs = np.bincount(2*y+pred,minlength=4)
            np.testing.assert_equal(pairs, row[['tn','fp','fn','tp']].to_numpy())
            np.testing.assert_allclose(row.brier, np.square(y-p).mean(), atol=1e-9)
            if name=='logistic' and method=='platt':
                saved = pd.read_csv(folder/'predictions.csv')
                np.testing.assert_array_equal(saved.event_id, test.event_id)
                np.testing.assert_allclose(p, saved.probability, atol=1e-9)
            for r in review[(review.model==name)&(review.calibration==method)].itertuples():
                threshold = .5 if r.target_review==0 else np.quantile(np.maximum(c,1-c),r.target_review)
                accept = np.maximum(p,1-p)>=threshold
                np.testing.assert_equal(int((~accept).sum()),r.review_count)
                np.testing.assert_allclose(accept.mean(),r.coverage)
                if accept.any():
                    np.testing.assert_allclose(np.mean(pred[accept]!=y[accept]),r.risk)
                else:
                    assert math.isnan(r.risk)
            labels = classification_report(y,pred,output_dict=True,zero_division=0)
            for binary in ['0','1']:
                per_class.append(dict(model=name,calibration=method,label=int(binary),**labels[binary]))
            checked.append([name,method])
    pd.DataFrame(per_class).to_csv(folder/'per_class.csv',index=False)
    output = dict(checked=len(checked), verified=['dataset and checkpoint hashes','replayed binary confusion counts',
                 'Brier scores','primary event IDs and predictions','coverage, error and realized review counts'],
                 limitations='Internal artifact and arithmetic audit. Collection independence and transportability untested.')
    (folder/'replay_audit.json').write_text(json.dumps(output,indent=2))
    print(folder,output['checked'],'model/calibrator combinations reproduced')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results',required=True)
    p.add_argument('--input',required=True)
    args=p.parse_args()
    with threadpool_limits(limits=1):
        replay(args.results,args.input)
