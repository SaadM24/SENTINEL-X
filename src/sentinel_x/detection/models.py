"""Train-only preprocessing and comparable binary scorers."""
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import rbf_kernel
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.preprocessing import StandardScaler


class Preprocessor:
    def fit(self, values):
        clean = np.where(np.isfinite(values), values, np.nan)
        self.median = np.nan_to_num(np.nanmedian(clean, axis=0))
        clean = np.where(np.isfinite(clean), clean, self.median)
        self.lo, self.hi = np.quantile(clean, [0.005, 0.995], axis=0)
        self.scaler = StandardScaler().fit(np.clip(clean, self.lo, self.hi))
        return self

    def transform(self, values):
        clean = np.where(np.isfinite(values), values, self.median)
        return self.scaler.transform(np.clip(clean, self.lo, self.hi)).astype('float32')


class BenignScorer:
    def __init__(self, model, reconstruct=False):
        self.model = model
        self.reconstruct = reconstruct

    def anomaly(self, x):
        if self.reconstruct:
            return np.mean((self.model.predict(x).reshape(x.shape) - x) ** 2, axis=1)
        return -self.model.score_samples(x)

    def fit(self, x, y):
        benign = x[y == 0]
        if self.reconstruct:
            self.model.fit(benign, benign)
        else:
            self.model.fit(benign)
        self.reference = np.sort(self.anomaly(benign))
        return self

    def predict_proba(self, x):
        p = (1 + np.searchsorted(self.reference, self.anomaly(x))) / (1 + len(self.reference))
        return np.column_stack((1-p, p))


class RadialClassifier:
    def __init__(self, count, seed):
        self.count = count
        self.seed = seed
        self.head = LogisticRegression(class_weight='balanced', max_iter=400, random_state=seed)

    def basis(self, x):
        return rbf_kernel(x, self.centres, gamma=1 / max(1, x.shape[1]))

    def fit(self, x, y):
        rng = np.random.default_rng(self.seed)
        self.centres = x[rng.choice(len(x), min(self.count, len(x)), replace=False)]
        self.head.fit(self.basis(x), y)
        return self

    def predict_proba(self, x):
        return self.head.predict_proba(self.basis(x))


def models(cfg, seed, batch):
    return {
        'logistic': LogisticRegression(class_weight='balanced', max_iter=400, random_state=seed),
        'forest': RandomForestClassifier(n_estimators=cfg['trees'], min_samples_leaf=2,
                                         class_weight='balanced_subsample', n_jobs=1, random_state=seed),
        'boost': HistGradientBoostingClassifier(max_iter=cfg['iterations'], max_leaf_nodes=15,
                                                early_stopping=False, random_state=seed),
        'isolation': BenignScorer(IsolationForest(n_estimators=cfg['trees'], random_state=seed)),
        'mlp': MLPClassifier(hidden_layer_sizes=(32, 16), max_iter=cfg['epochs'],
                             batch_size=batch, random_state=seed),
        'autoencoder': BenignScorer(MLPRegressor(hidden_layer_sizes=(16, 3, 16), max_iter=cfg['epochs'],
                                                batch_size=batch, random_state=seed), reconstruct=True),
        'rbf': RadialClassifier(cfg['rbf_centres'], seed)
    }
