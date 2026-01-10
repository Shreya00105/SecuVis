import joblib
import pandas as pd
import os

MODEL_PATH = "models/saved/anomaly_model.pkl"
VEC_PATH = "models/saved/vectorizer.pkl"

model = joblib.load(MODEL_PATH)
vectorizer = joblib.load(VEC_PATH)

def predict_log(log_entry: str):
    """Predict if a given log message is normal or anomalous"""
    X = vectorizer.transform([log_entry])
    pred = model.predict(X)[0]
    # IsolationForest returns -1 for anomaly, 1 for normal
    return "Threat" if pred == -1 else "Safe"

if __name__ == "__main__":
    sample_log = "Multiple failed login attempts from 10.0.0.23"
    print(f"Log: {sample_log}")
    print(f"Prediction: {predict_log(sample_log)}")
