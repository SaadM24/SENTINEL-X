"""Run from the project root. Each completed model is independently resumable."""
import argparse
import hashlib
import importlib.metadata as md
import json
import os
import platform
import re
import sys
import time
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score
from threadpoolctl import threadpool_limits

from .metrics import Calibration, assess, reliability, selection
from .models import BenignScorer, Preprocessor, models


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def atomic_json(path, payload):
    tmp = path.with_suffix('.pending')
    tmp.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding='utf-8')
    tmp.replace(path)


def read_input(path):
    data = pd.read_csv(path)
    features = [c for c in data if c.startswith('f_')]
    if not features or not {'event_id', 'split', 'label', 'attack_category'} <= set(data):
        raise ValueError('Expected split, event_id, label, attack_category and f_* features')
    if data.event_id.isna().any() or data.event_id.duplicated().any():
        raise ValueError('Invalid or repeated event IDs')
    if set(data.split) != {'train', 'cal', 'test'}:
        raise ValueError('Expected exactly train, cal and test')
    if any(set(y) != {0, 1} for _, y in data.groupby('split').label):
        raise ValueError('Both binary outcomes required per partition')
    x = data[features].astype('float32').to_numpy()
    hashes = pd.util.hash_pandas_object(data[features], index=False)
    if pd.DataFrame({'key': hashes, 'split': data.split}).groupby('key').split.nunique().max() > 1:
        raise ValueError('Identical feature vectors cross partitions; rerun dataset preparation')
    return data, x, features


def primary_details(out, model, mapper, features, prep, xt, yt, frame, dataset, seed):
    raw = model.predict_proba(xt)[:, 1]
    p = mapper.predict(raw)
    pd.DataFrame(dict(event_id=frame.event_id, y_true=yt, probability=p, raw_probability=raw,
                      model='logistic', dataset=dataset, category=frame.attack_category)).to_csv(out/'predictions.csv', index=False)
    attribution = []
    rng = np.random.default_rng(seed)
    for i, name in enumerate(features):
        permuted = xt.copy()
        permuted[:, i] = rng.permutation(permuted[:, i])
        drop = average_precision_score(yt,p)-average_precision_score(yt, mapper.predict(model.predict_proba(permuted)[:,1]))
        attribution.append(dict(feature=name, ap_drop=drop, coefficient_standardized=model.coef_[0,i]))
    pd.DataFrame(attribution).to_csv(out/'importance.csv', index=False)
    for_shift = xt.copy()
    for_shift[:, 0] = prep.transform(prep.median[None, :])[0, 0]
    shifted = mapper.predict(model.predict_proba(for_shift)[:, 1])
    atomic_json(out/'shift.json', dict(feature=features[0], reference=assess(yt,p), masked=assess(yt,shifted)))
    categories = []
    for cat in frame.attack_category.unique():
        mask = frame.attack_category.to_numpy() == cat
        pred = p[mask] >= .5
        categories.append(dict(category=cat, count=int(mask.sum()), fp=int((pred & (yt[mask]==0)).sum()),
                               fn=int((~pred & (yt[mask]==1)).sum()), mean_p=float(p[mask].mean())))
    pd.DataFrame(categories).to_csv(out/'categories.csv', index=False)
    n = len(yt)
    rate = np.mean((p>=.5)!=yt)
    z = 1.95996398454
    mid = (rate+z*z/(2*n))/(1+z*z/n)
    half = z*np.sqrt(rate*(1-rate)/n+z*z/(4*n*n))/(1+z*z/n)
    atomic_json(out/'error_interval.json', dict(error=rate, wilson95=[mid-half,mid+half], n=n))


def run(args):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.run):
        raise ValueError('Use an alphanumeric run name with optional hyphens and underscores')
    cfg = json.loads(Path(args.config).read_text())
    seed = args.seed if args.seed is not None else cfg['seed']
    data, x, features = read_input(args.input)
    out = Path('results/v02') / args.run
    classical = Path('results/v01') / args.run
    out.mkdir(parents=True, exist_ok=True)
    classical.mkdir(parents=True, exist_ok=True)
    mode = cfg[args.mode]
    device = 'cpu'
    if args.device != 'cpu':
        try:
            import torch
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        except ImportError:
            pass
        if args.device=='cuda' and device!='cuda':
            raise RuntimeError('CUDA unavailable; select auto or cpu')
    manifest = Path(args.input).with_name('manifest.json')
    source = json.loads(manifest.read_text()) if manifest.exists() else {'dataset':Path(args.input).parent.name}
    deps = {n:md.version(n) for n in ['numpy','pandas','scikit-learn','scipy','joblib','threadpoolctl']}
    spec = dict(dataset=source.get('dataset'), dataset_sha256=digest(args.input), seed=seed,
                mode=args.mode, config=mode, device=device, batch=cfg['batch'], features=features, dependencies=deps,
                source_sha256={f.name:digest(f) for f in sorted(Path(__file__).parent.glob('*.py'))})
    specfile = out/'spec.json'
    if specfile.exists() and (not args.resume or json.loads(specfile.read_text()) != spec):
        raise RuntimeError('Choose a fresh --run or --resume with identical data, model source, environment and settings.')
    atomic_json(specfile, spec)
    mtrain, mcal, mtest = (data.split.eq(s).to_numpy() for s in ['train','cal','test'])
    prep = Preprocessor().fit(x[mtrain])
    xx = prep.transform(x)
    y = data.label.to_numpy()
    train, cal, test = xx[mtrain], xx[mcal], xx[mtest]
    yt = y[mtest]
    algorithms = models(mode, seed, cfg['batch'])
    if device == 'cuda':
        from .accelerated import TorchNet
        for name in ['mlp','autoencoder']:
            reconstruct = name=='autoencoder'
            net = TorchNet(reconstruct, mode['epochs'], cfg['batch'], seed)
            algorithms[name] = BenignScorer(net,reconstruct=True) if reconstruct else net
    rows, bins, coverage, runs = [], [], [], []
    for name, model in algorithms.items():
        start = time.perf_counter()
        checkpoint = out/f'{name}.joblib'
        done = out/f'{name}.json'
        if done.exists() and args.resume:
            result = json.loads(done.read_text())
            if not checkpoint.exists() or result['run']['checkpoint_sha256'] != digest(checkpoint):
                raise ValueError('Checkpoint missing or changed: '+str(checkpoint))
        else:
            print('Training',name,flush=True)
            with warnings.catch_warnings(record=True) as messages:
                warnings.simplefilter('always')
                model.fit(train, y[mtrain])
                cp = model.predict_proba(cal)[:, 1]
                t0 = time.perf_counter()
                tp = model.predict_proba(test)[:, 1]
                latency = 1e6*(time.perf_counter()-t0)/len(tp)
                calibrators, scores, rel, cov = {}, [], [], []
                for method in ['raw','platt','temperature','isotonic']:
                    mapper = Calibration(method).fit(cp,y[mcal])
                    calibrators[method] = mapper
                    p = mapper.predict(tp)
                    key = dict(model=name,calibration=method)
                    scores.append(dict(**key,**assess(yt,p), microseconds_per_event=latency))
                    rel.extend(dict(**key,**v) for v in reliability(yt,p))
                    cov.extend(dict(**key,**v) for v in selection(mapper.predict(cp),p,yt))
                if name=='logistic':
                    primary_details(out,model,calibrators['platt'],features,prep,test,yt,data[mtest],str(spec['dataset']),seed)
                tmp = checkpoint.with_suffix('.tmp')
                joblib.dump(dict(model=model,preprocessor=prep,calibrators=calibrators,features=features),tmp,compress=3)
                tmp.replace(checkpoint)
            result = dict(scores=scores, reliability=rel, coverage=cov,
                          run=dict(model=name,status='executed',seconds=time.perf_counter()-start,
                                   checkpoint=str(checkpoint),checkpoint_sha256=digest(checkpoint),
                                   warnings=sorted(set(str(w.message) for w in messages))))
            atomic_json(done,result)
        rows.extend(result['scores'])
        bins.extend(result['reliability'])
        coverage.extend(result['coverage'])
        runs.append(result['run'])
    table = pd.DataFrame(rows)
    table.to_csv(out/'comparison.csv',index=False)
    table[(table.calibration=='raw') & table.model.isin(['logistic','forest','boost','isolation'])].to_csv(classical/'classical.csv',index=False)
    pd.DataFrame(bins).to_csv(out/'reliability.csv',index=False)
    pd.DataFrame(coverage).to_csv(out/'coverage.csv',index=False)
    atomic_json(out/'registry.json',dict(experiment_id=args.run,environment=platform.platform(),python=sys.version,
                                         split_counts=data.split.value_counts().to_dict(),data_manifest=source,
                                         spec='spec.json',results='comparison.csv',runs=runs))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--config',default='configs/detection.json')
    parser.add_argument('--mode',choices=['smoke','research'],default='smoke')
    parser.add_argument('--seed',type=int)
    parser.add_argument('--device',choices=['cpu','cuda','auto'],default='cpu')
    parser.add_argument('--resume',action='store_true')
    with threadpool_limits(limits=1):
        run(parser.parse_args())

if __name__=='__main__':
    main()
