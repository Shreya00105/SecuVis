import os
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

DATA_PATH = "data/cleaned_logs/"
SAVE_PATH = "models/saved/"

def load_data():
    files = [f for f in os.listdir(DATA_PATH) if f.endswith(".csv")]
    if not files:
        raise FileNotFoundError("No cleaned log files found in data/cleaned_logs/")
    
    dfs = [pd.read_csv(os.path.join(DATA_PATH, f)) for f in files]
    df = pd.concat(dfs, ignore_index=True)
    df.dropna(subset=["message"], inplace=True)
    return df

def train_model():
    df = load_data()
    print(f"[INFO] Loaded {len(df)} log entries")

    # Feature extraction
    vectorizer = TfidfVectorizer(max_features=5000, stop_words='english')
    X = vectorizer.fit_transform(df['message'])

    # Unsupervised anomaly detection
    model = IsolationForest(n_estimators=150, contamination=0.05, random_state=42)
    model.fit(X)

    os.makedirs(SAVE_PATH, exist_ok=True)
    joblib.dump(model, os.path.join(SAVE_PATH, "anomaly_model.pkl"))
    joblib.dump(vectorizer, os.path.join(SAVE_PATH, "vectorizer.pkl"))
    print("[✔] Model and vectorizer saved successfully!")

if __name__ == "__main__":
    train_model()
