import joblib
import numpy as np
import pandas as pd
import pytest

from sentinel_x.detection.__main__ import read_input
from sentinel_x.detection.metrics import Calibration, assess, reliability, selection
from sentinel_x.detection.models import Preprocessor, models


def test_preprocessing_reuses_train_statistics():
    train = np.array([[0., 2], [2., 3], [4., 4]])
    pipe = Preprocessor().fit(train)
    z = pipe.transform(np.array([[np.nan, 1e9]]))
    np.testing.assert_allclose(z, pipe.transform(np.array([[2., 4]])))


def test_accuracy_metrics_and_boundary_bins():
    y = np.array([0, 0, 1, 1])
    p = np.array([0, .5, .8, 1.])
    result = assess(y, p)
    assert [result[k] for k in ['tn','fp','fn','tp']] == [1,1,0,2]
    assert result['false_alarms_per_1000'] == 500
    assert result['brier'] == pytest.approx((.25+.04)/4)
    assert result['ece'] == pytest.approx((.5+.2)/4)
    assert [r['bin'] for r in reliability(y, p)] == [0,5,8,9]


@pytest.mark.parametrize('method', ['raw','temperature','platt','isotonic'])
def test_calibration_finite(method):
    p = np.array([0,.15,.6,.7,.8,1])
    y = np.array([0,0,0,1,1,1])
    output = Calibration(method).fit(p,y).predict(p)
    assert np.all(np.isfinite(output) & (output >= 0) & (output <= 1))


def test_selective_budget_ties():
    p = np.array([.5,.5,.5,.5])
    rows = list(selection(p,p,np.array([1,1,0,0])))
    assert all(r['review_count'] == 0 and r['risk'] == .5 for r in rows)


def test_reject_cross_split_feature_duplicates(tmp_path):
    path = tmp_path/'events.csv'
    pd.DataFrame(dict(split=['train','cal','test']*2, event_id=list('abcdef'), label=[0]*3+[1]*3,
                      attack_category=['x']*6, f_value=[1,2,1,4,5,6])).to_csv(path,index=False)
    with pytest.raises(ValueError,match='cross partitions'):
        read_input(path)


@pytest.mark.parametrize('name',['logistic','forest','boost','isolation','mlp','autoencoder','rbf'])
def test_model_round_trip(name,tmp_path):
    rng = np.random.default_rng(1)
    x = rng.normal(size=(40,6)).astype('float32')
    y = np.tile([0,1],20)
    choices = models(dict(epochs=2,trees=3,iterations=2,rbf_centres=3),1,8)
    model = choices[name].fit(x,y)
    p = model.predict_proba(x)[:,1]
    assert np.isfinite(p).all() and np.all((p>=0) & (p<=1))
    target=tmp_path/'m.joblib'
    joblib.dump(model,target)
    np.testing.assert_allclose(p,joblib.load(target).predict_proba(x)[:,1])
