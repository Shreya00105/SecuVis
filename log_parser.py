"""
Parse uploaded Linux auth logs (or CSV/JSON with message column) into structured JSON docs.

Exposed function:
    parse_uploaded_file(file_path, source='manual', log_type='auth') -> List[dict]
Each returned dict contains:
    - ingest metadata will be added by caller (ingest_id, ingested_at)
    - raw_message
    - timestamp (ISO)
    - log_type
    - source
    - parsed: { src_ip, dst_ip, username, action, port, extra }
"""
import os
import re
import csv
import json
from datetime import datetime
from typing import List
import pandas as pd

from .preprocessing import normalize_timestamp, extract_ip, clean_message

# Common regex patterns for auth logs (OpenSSH typical)
RE_FAILED_PASS = re.compile(r'Failed password for (invalid user )?(?P<user>\S+) from (?P<ip>(?:\d{1,3}\.){3}\d{1,3})(?: port (?P<port>\d+))?', re.IGNORECASE)
RE_ACCEPTED_PASS = re.compile(r'Accepted password for (?P<user>\S+) from (?P<ip>(?:\d{1,3}\.){3}\d{1,3})', re.IGNORECASE)
RE_INVALID_USER = re.compile(r'invalid user (?P<user>\S+) from (?P<ip>(?:\d{1,3}\.){3}\d{1,3})', re.IGNORECASE)
RE_SUDO = re.compile(r'(?P<user>\S+) :.*session opened for user (?P<target>\S+)', re.IGNORECASE)
RE_CONNECTION = re.compile(r'Connection closed by (?P<ip>(?:\d{1,3}\.){3}\d{1,3})|Disconnect from (?P<ip2>(?:\d{1,3}\.){3}\d{1,3})', re.IGNORECASE)

def _parse_line_authlog(line: str, year_hint=None):
    """
    Parse a single auth.log line (string). Return parsed dict or None.
    Attempt multiple regexes to extract user, ip, action, port.
    """
    raw = line.strip()
    if not raw:
        return None

    # Timestamp may be at start like: "Nov  7 10:01:12 hostname sshd[1234]: ..."
    # We'll attempt to split timestamp from the rest by finding first timestamp-like pattern.
    # Simpler approach: take first 3 tokens as month day time for linux format
    tokens = raw.split()
    timestamp_candidate = None
    message_part = raw
    if len(tokens) >= 3:
        ts = ' '.join(tokens[0:3])
        rest = ' '.join(tokens[3:])
        # try to parse ts
        parsed_ts = normalize_timestamp(ts)
        if parsed_ts:
            timestamp_candidate = parsed_ts
            message_part = rest

    # Try CSV/structured message fallback if timestamp parsing failed
    parsed = {
        'raw_message': raw,
        'timestamp': timestamp_candidate,
        'log_type': 'auth',
        'src_ip': None,
        'dst_ip': None,
        'username': None,
        'action': None,
        'port': None,
        'extra': {}
    }

    msg = message_part

    # Try failed password
    m = RE_FAILED_PASS.search(msg)
    if m:
        parsed['action'] = 'failed_password'
        parsed['username'] = m.group('user')
        parsed['src_ip'] = m.group('ip')
        parsed['port'] = int(m.group('port')) if m.group('port') else None
        return parsed

    m = RE_ACCEPTED_PASS.search(msg)
    if m:
        parsed['action'] = 'accepted_password'
        parsed['username'] = m.group('user')
        parsed['src_ip'] = m.group('ip')
        return parsed

    m = RE_INVALID_USER.search(msg)
    if m:
        parsed['action'] = 'invalid_user'
        parsed['username'] = m.group('user')
        parsed['src_ip'] = m.group('ip')
        return parsed

    # connection/close patterns
    m = RE_CONNECTION.search(msg)
    if m:
        ip = m.group('ip') or m.group('ip2')
        parsed['action'] = 'connection_close'
        parsed['src_ip'] = ip
        return parsed

    # sudo/session opened
    m = RE_SUDO.search(msg)
    if m:
        parsed['action'] = 'session_opened'
        parsed['username'] = m.group('user')
        parsed['extra']['target'] = m.group('target')
        return parsed

    # fallback: extract any IP and treat as generic event
    ip = extract_ip(msg)
    if ip:
        parsed['src_ip'] = ip
        parsed['action'] = 'unknown'
        parsed['extra']['note'] = 'generic parsed'
        return parsed

    # If nothing found, return generic doc
    parsed['action'] = 'unparsed'
    return parsed

def _read_text_log(path: str) -> List[str]:
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.readlines()

def _read_csv_or_json(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.csv',):
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    elif ext in ('.json',):
        try:
            return pd.read_json(path, lines=True)
        except ValueError:
            return pd.read_json(path)
    else:
        raise ValueError("Unsupported structured file type for CSV/JSON loader")

def parse_uploaded_file(file_path: str, source: str = 'manual_upload', log_type: str = 'auth') -> List[dict]:
    """
    Main entry - parse an uploaded file into list of structured documents.
    Supports: raw text auth.log, CSV with 'message' or 'raw_message' column, JSON lines.
    Returns list suitable for insertion into raw_logs collection.
    """
    docs = []
    basename = os.path.basename(file_path)
    year_hint = None
    # if filename contains a year, try to use it as hint (common in rotated logs)
    m = re.search(r'(\d{4})', basename)
    if m:
        try:
            year_hint = int(m.group(1))
        except Exception:
            year_hint = None

    ext = os.path.splitext(file_path)[1].lower()
    if ext in ('.log', '.txt'):
        lines = _read_text_log(file_path)
        for line in lines:
            cleaned = clean_message(line)
            parsed = _parse_line_authlog(cleaned, year_hint=year_hint)
            if parsed:
                # If timestamp was not parsed by _parse_line_authlog, try to recover in-line
                if not parsed.get('timestamp'):
                    # try to find any complete timestamp in the line
                    ts = normalize_timestamp(cleaned, year_hint=year_hint)
                    parsed['timestamp'] = ts
                parsed['source'] = source
                parsed['log_type'] = log_type
                docs.append(parsed)
    elif ext in ('.csv', '.json'):
        df = _read_csv_or_json(file_path)
        # Expect column 'message' or 'raw_message' or 'log'
        if 'message' in df.columns:
            msg_col = 'message'
        elif 'raw_message' in df.columns:
            msg_col = 'raw_message'
        elif 'log' in df.columns:
            msg_col = 'log'
        else:
            # if no message column, try to combine row into a raw string
            df['raw_message'] = df.apply(lambda r: ' '.join([str(v) for v in r.values if v]), axis=1)
            msg_col = 'raw_message'

        ts_col = None
        for candidate in ['timestamp', 'time', 'date']:
            if candidate in df.columns:
                ts_col = candidate
                break

        for _, row in df.iterrows():
            raw_msg = clean_message(row.get(msg_col, ''))
            parsed = _parse_line_authlog(raw_msg, year_hint=year_hint)
            # override timestamp if structured file contains it
            if ts_col and row.get(ts_col):
                parsed_ts = normalize_timestamp(row.get(ts_col), year_hint=year_hint)
                if parsed_ts:
                    parsed['timestamp'] = parsed_ts
            parsed['source'] = source
            parsed['log_type'] = log_type
            docs.append(parsed)
    else:
        raise ValueError("Unsupported upload file type")

    # Final normalization: ensure timestamp present, set ingest metadata later
    for d in docs:
        if not d.get('timestamp'):
            d['timestamp'] = datetime.utcnow().isoformat()
        d['raw_message'] = d.get('raw_message') or ''
        # convert port to int if possible
        if d.get('port') is not None:
            try:
                d['port'] = int(d['port'])
            except Exception:
                d['port'] = None

    return docs
