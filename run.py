# run.py

import os
import pandas as pd
from utils.log_parser import parse_auth_log
from app.utils.model_loader import load_model, predict_features

RAW_LOGS = "data/raw_logs/"
CLEANED = "data/cleaned_logs/cleaned.csv"
MODEL = "models/if_model.pkl"
SCALER = "models/scaler.pkl"

def pipeline():
    print("=== SECUVIS PIPELINE STARTED ===")

    docs = []
    for file in os.listdir(RAW_LOGS):
        if file.endswith(".log"):
            p = os.path.join(RAW_LOGS, file)
            docs.extend(parse_auth_log(p))

    df = pd.DataFrame(docs)
    print("Parsed:", len(df))

    df.to_csv(CLEANED, index=False)
    print("Saved cleaned logs.")

    model, scaler = load_model(MODEL, SCALER)
    if model is None:
        print("MODEL NOT FOUND.")
        return

    result = predict_features(df, model, scaler)
    print(result.head())

    print("=== PIPELINE COMPLETE ===")

if __name__ == "__main__":
    pipeline()
