import os
import pandas as pd
import re
from datetime import datetime

RAW_PATH = "data/raw_logs/"
CLEAN_PATH = "data/cleaned_logs/"

def clean_message(msg):
    """Remove unwanted chars, lowercasing"""
    msg = re.sub(r'[^a-zA-Z0-9:. ]', '', str(msg))
    return msg.lower().strip()

def extract_ip(msg):
    """Extract first IP address from log message if exists"""
    match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', msg)
    return match.group(0) if match else None

def preprocess_log_file(file_path):
    """Clean and standardize raw log file"""
    try:
        df = pd.read_csv(file_path)
    except Exception:
        df = pd.read_json(file_path, lines=True)

    if 'message' not in df.columns:
        raise ValueError("Log file must contain a 'message' column")

    df['message'] = df['message'].apply(clean_message)
    df['source_ip'] = df['message'].apply(extract_ip)
    df['timestamp'] = df.get('timestamp', pd.Timestamp.now())

    df.dropna(subset=['message'], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

def save_cleaned(df, filename):
    os.makedirs(CLEAN_PATH, exist_ok=True)
    output_path = os.path.join(CLEAN_PATH, filename)
    df.to_csv(output_path, index=False)
    print(f"[✔] Saved cleaned logs to {output_path}")

def run_preprocessing():
    os.makedirs(CLEAN_PATH, exist_ok=True)
    files = [f for f in os.listdir(RAW_PATH) if f.endswith(('.csv', '.json'))]
    if not files:
        print("⚠ No raw log files found in 'data/raw_logs/'.")
        return

    for file in files:
        raw_path = os.path.join(RAW_PATH, file)
        print(f"→ Processing {file}...")
        df = preprocess_log_file(raw_path)
        save_cleaned(df, f"cleaned_{file.split('.')[0]}.csv")

if __name__ == "__main__":
    run_preprocessing()
