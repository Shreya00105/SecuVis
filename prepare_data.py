import pandas as pd
from utils.log_parser import parse_auth_log

RAW_LOG_FILE = "data/raw_logs/auth_sample.log"
STRUCTURED_OUTPUT = "data/processed/structured_logs.csv"

def main():
    print("📌 Step 1: Parsing raw Linux auth logs...")

    df = parse_auth_log(RAW_LOG_FILE)

    if df.empty:
        print("❌ ERROR: No valid log entries parsed. Check the log format.")
        return

    df.to_csv(STRUCTURED_OUTPUT, index=False)
    print(f"✅ Structured log file created: {STRUCTURED_OUTPUT}")
    print(df.head())

if __name__ == "__main__":
    main()
