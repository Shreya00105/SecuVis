# app/utils/model_loader.py
"""
Model loading and prediction utilities for IsolationForest model.
Functions:
- load_model(model_path, scaler_path=None)
- predict_features(df_features, model, scaler=None) -> DataFrame with columns ['anomaly_label','anomaly_score']
"""
import os
import joblib
import numpy as np
import pandas as pd

def load_model(model_path, scaler_path=None):
    """
    Load IsolationForest model and optional scaler. Returns (model, scaler or None)
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")
    model = joblib.load(model_path)
    scaler = None
    if scaler_path and os.path.exists(scaler_path):
        scaler = joblib.load(scaler_path)
    return model, scaler

def predict_features(df_features: pd.DataFrame, model, scaler=None):
    """
    Predict anomalies on numeric DataFrame (index preserved).
    Returns df_features copy with columns:
      - _anomaly (1 normal / -1 anomaly)
      - _anomaly_score (raw model score; lower -> more anomalous for some models)
      - _anomaly_prob (optional normalized score scaled 0-1)
    """
    if df_features.empty:
        return df_features

    X = df_features.copy().astype(float).fillna(0.0)
    feature_cols = X.columns.tolist()
    if scaler:
        X_scaled = scaler.transform(X.values)
    else:
        X_scaled = X.values

    # IsolationForest: decision_function gives anomaly score (higher = more normal)
    labels = model.predict(X_scaled)  # returns 1 for normal, -1 for anomaly
    scores = model.decision_function(X_scaled)  # higher means more normal

    # normalize scores to 0-1 probability-like for display
    min_s, max_s = float(np.min(scores)), float(np.max(scores))
    if max_s - min_s == 0:
        probs = np.full_like(scores, 0.5)
    else:
        probs = (scores - min_s) / (max_s - min_s)

    out = X.copy()
    out['_anomaly'] = labels
    out['_anomaly_score'] = scores
    out['_anomaly_prob'] = probs
    # map label to readable
    out['_label'] = out['_anomaly'].apply(lambda x: 'Threat' if int(x) == -1 else 'Normal')
    return out
