import re
from dateutil import parser as dateparser
from datetime import datetime, timezone

IP_REGEX = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')

def normalize_timestamp(ts_str, year_hint=None):
    """
    Parse a timestamp string (various formats) and return an ISO8601 UTC string.
    Linux auth.log typically lacks year — year_hint can be provided (int).
    """
    if ts_str is None:
        return None
    try:
        # If no year present, dateutil can still parse but assume the current year
        dt = dateparser.parse(ts_str, fuzzy=True, default=datetime.now())
        if year_hint:
            dt = dt.replace(year=year_hint)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_utc = dt.astimezone(timezone.utc)
        return dt_utc.isoformat()
    except Exception:
        return None

def extract_ip(text):
    """Return first IPv4 address found in text or None."""
    if not isinstance(text, str):
        return None
    m = IP_REGEX.search(text)
    return m.group(0) if m else None

def clean_message(msg):
    """
    Basic whitespace normalization and removal of non-printable chars.
    Keep punctuation minimal because certain tokens (user@host) matter.
    """
    if msg is None:
        return ''
    # remove control chars
    cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', str(msg))
    # collapse whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned
