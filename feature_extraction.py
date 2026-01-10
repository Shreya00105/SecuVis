"""
Feature engineering utilities for Linux auth logs.
Produce numeric features aggregated per src_ip (or per log row) to feed IsolationForest.

Functions:
- build_srcip_aggregate_features(docs) -> DataFrame
- build_row_level_features(docs) -> DataFrame
"""
import pandas as pd
import numpy as np
from datetime import datetime, timezone

def _to_datetime(x):
    try:
        return pd.to_datetime(x)
    except Exception:
        return pd.to_datetime(datetime.utcnow())

def build_row_level_features(docs):
    """
    Build per-log-row features (useful for row-level anomaly detection).
    Input: list of parsed docs (dicts from log_parser)
    Output: DataFrame with features: msg_len, has_ip, is_failed, hour_of_day, port, username_present
    """
    rows = []
    for d in docs:
        ts = _to_datetime(d.get('timestamp'))
        msg = d.get('raw_message','') or ''
        src = d.get('src_ip')
        port = d.get('port')
        action = d.get('action', '').lower()

        rows.append({
            'timestamp': ts,
            'src_ip': src,
            'msg_len': len(msg),
            'has_ip': 1 if src else 0,
            'is_failed': 1 if 'failed' in action else 0,
            'is_success': 1 if 'accept' in action or 'accepted' in action else 0,
            'hour_of_day': ts.hour,
            'port': int(port) if port else 0,
            'username_present': 1 if d.get('username') else 0
        })
    df = pd.DataFrame(rows)
    # fillna and types
    df['port'] = df['port'].fillna(0).astype(int)
    return df

def build_srcip_aggregate_features(docs, window_minutes=60):
    """
    Aggregate features per src_ip over entire uploaded docs.
    Example features:
      - failed_count
      - success_count
      - unique_ports
      - total_attempts
      - attempts_per_minute (approx)
      - avg_msg_len
      - active_hours_entropy (approx using hour_of_day variance)
    Returns DataFrame indexed by src_ip.
    """
    row_df = build_row_level_features(docs)
    if row_df.empty:
        return pd.DataFrame()

    now = datetime.now(timezone.utc)
    # group by src_ip
    aggs = []
    grouped = row_df.groupby('src_ip')
    for src, grp in grouped:
        total = len(grp)
        failed = int(grp['is_failed'].sum())
        success = int(grp['is_success'].sum())
        unique_ports = int(grp['port'].nunique())
        avg_msg_len = float(grp['msg_len'].mean() if not grp['msg_len'].empty else 0)
        duration_minutes = max((grp['timestamp'].max() - grp['timestamp'].min()).total_seconds()/60.0, 1.0)
        attempts_per_minute = total / duration_minutes
        hour_var = float(grp['hour_of_day'].var()) if grp['hour_of_day'].nunique() > 1 else 0.0

        aggs.append({
            'src_ip': src,
            'total_attempts': total,
            'failed_count': failed,
            'success_count': success,
            'unique_ports': unique_ports,
            'avg_msg_len': avg_msg_len,
            'attempts_per_minute': attempts_per_minute,
            'hour_variance': hour_var
        })

    agg_df = pd.DataFrame(aggs).set_index('src_ip').fillna(0)
    return agg_df

def prepare_model_input_from_docs(docs, per='src_ip'):
    """
    Convenience wrapper:
      - if per=='src_ip' -> returns aggregated features per src_ip (DataFrame)
      - if per=='row' -> returns row-level features per log row
    """
    if per == 'row':
        return build_row_level_features(docs)
    return build_srcip_aggregate_features(docs)
