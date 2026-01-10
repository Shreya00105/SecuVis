# tests/test_model.py
import os
import tempfile
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from app.utils.model_loader import predict_features, load_model

def make_synthetic_features(n_normal=50, n_anom=5, seed=42):
    rng = np.random.RandomState(seed)
    # normal cluster
    normal = rng.normal(loc=0.0, scale=1.0, size=(n_normal, 4))
    # anomalous cluster
    anom = rng.normal(loc=6.0, scale=1.0, size=(n_anom, 4))
    X = np.vstack([normal, anom])
    cols = ['f1','f2','f3','f4']
    df = pd.DataFrame(X, columns=cols)
    return df, list(range(n_normal, n_normal+n_anom))  # return indexes of anomalies for reference

def test_train_save_load_and_predict_features(tmp_path):
    # create synthetic features
    df_features, anom_idxs = make_synthetic_features()
    # scale and train model
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_features)
    model = IsolationForest(n_estimators=50, contamination=0.05, random_state=0)
    model.fit(X_scaled)

    # save model & scaler to temp files
    model_file = tmp_path / "if_model.pkl"
    scaler_file = tmp_path / "scaler.pkl"
    joblib.dump(model, str(model_file))
    joblib.dump(scaler, str(scaler_file))

    # load via load_model
    loaded_model, loaded_scaler = load_model(str(model_file), str(scaler_file))
    assert loaded_model is not None
    assert loaded_scaler is not None

    # predict using predict_features
    out = predict_features(df_features, loaded_model, loaded_scaler)
    # Output should be a DataFrame containing _anomaly, _anomaly_score, _anomaly_prob, _label
    for col in ['_anomaly','_anomaly_score','_anomaly_prob','_label']:
        assert col in out.columns

    # Check that at least some anomalies were detected (-1)
    detected = out['_anomaly'].values
    assert -1 in detected or any(out['_label'] == 'Threat')
