import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import expit, logit
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn import metrics as m


def logits(p):
    return logit(np.clip(p, 1e-7, 1-1e-7))


class Calibration:
    def __init__(self, method):
        self.method = method

    def fit(self, p, y):
        z = logits(p)
        if self.method == 'temperature':
            def loss(t):
                return np.mean(np.logaddexp(0, z / t) - y*z/t)
            self.model = minimize_scalar(loss, bounds=(0.05, 20), method='bounded').x
        elif self.method == 'platt':
            self.model = LogisticRegression(C=10).fit(z[:, None], y)
        elif self.method == 'isotonic':
            self.model = IsotonicRegression(out_of_bounds='clip').fit(p, y)
        elif self.method != 'raw':
            raise ValueError(self.method)
        return self

    def predict(self, p):
        if self.method == 'temperature':
            return expit(logits(p) / self.model)
        if self.method == 'platt':
            return self.model.predict_proba(logits(p)[:, None])[:, 1]
        if self.method == 'isotonic':
            return self.model.predict(p)
        return p


def reliability(y, p):
    bins = np.minimum(9, (10*p).astype(int))
    rows = []
    for i in range(10):
        mask = bins == i
        if mask.any():
            rows.append(dict(bin=i, count=int(mask.sum()), mean_probability=float(p[mask].mean()),
                             observed_rate=float(y[mask].mean())))
    return rows


def assess(y, p):
    pred = p >= 0.5
    tn, fp, fn, tp = map(int, m.confusion_matrix(y, pred, labels=[0, 1]).ravel())
    precision, recall, _ = m.precision_recall_curve(y, p)
    bins = reliability(y, p)
    return dict(precision=m.precision_score(y, pred, zero_division=0), recall=m.recall_score(y, pred),
                f1=m.f1_score(y, pred), macro_f1=m.f1_score(y, pred, average='macro', zero_division=0),
                average_precision=m.average_precision_score(y, p), pr_auc=m.auc(recall, precision),
                roc_auc=m.roc_auc_score(y, p), tn=tn, fp=fp, fn=fn, tp=tp,
                brier=m.brier_score_loss(y, p), ece=sum(b['count']*abs(b['mean_probability']-b['observed_rate'])
                                                       for b in bins)/len(y),
                fpr=fp/(fp+tn), false_alarms_per_1000=1000*fp/(fp+tn))


def selection(cal, test, y):
    conf = np.maximum(test, 1-test)
    for target in [0, .05, .1, .2, .5]:
        threshold = 0.5 if target == 0 else np.quantile(np.maximum(cal, 1-cal), target)
        mask = conf >= threshold
        yield dict(target_review=target, threshold=float(threshold), coverage=float(mask.mean()),
                   review_count=int((~mask).sum()), risk=float(((test[mask]>=.5)!=y[mask]).mean()) if mask.any() else None)
