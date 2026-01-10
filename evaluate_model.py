# scripts/evaluate_model.py

import pandas as pd
import joblib
from sklearn.metrics import classification_report, confusion_matrix
from utils.feature_extraction import extract_features
from utils.preprocessing import load_structured_logs

FEATURE_FILE = "data/model_input/features.csv"
STRUCTURED_LOGS = "data/processed/structured_logs.csv"
MODEL_FILE = "models/isolation_forest.pkl"
SCALER_FILE = "models/scaler.pkl"

def main():
    print("📌 Step 5: Loading files...")

    df = pd.read_csv(STRUCTURED_LOGS)
    features = extract_features(df)

    scaler = joblib.load(SCALER_FILE)
    model = joblib.load(MODEL_FILE)

    X_scaled = scaler.transform(features)

    print("📌 Step 6: Predicting anomalies...")
    predictions = model.predict(X_scaled)

    # Isolation Forest output: -1 = anomaly, 1 = normal
    predictions = [1 if p == -1 else 0 for p in predictions]

    # True labels (FAILED = anomaly, SUCCESS = normal)
    true_labels = df["status"].apply(lambda x: 1 if x == "FAILED" else 0)

    print("\n📌 Confusion Matrix:")
    print(confusion_matrix(true_labels, predictions))

    print("\n📌 Classification Report:")
    print(classification_report(true_labels, predictions))

if __name__ == "__main__":
    main()
