import streamlit as st
import pandas as pd

def _severity_badge(sev):
    """Return colored HTML badge for severity (0-10)"""
    try:
        sev = int(sev)
    except Exception:
        sev = 0
    if sev >= 8:
        color = '#ff4c4c'  # critical
    elif sev >= 5:
        color = '#ffb86b'  # mid
    else:
        color = '#9ad1a6'  # low
    return f'<span style="background:{color};padding:4px 8px;border-radius:6px;color:#0b0b0b;font-weight:600">{sev}</span>'

def render_log_table(df: pd.DataFrame, max_rows: int = 200):
    """
    Render the alerts/log table with some HTML formatting for severity and status.
    df: DataFrame with columns: alert_id, alert_type, severity, status, created_at, description
    """
    if df.empty:
        st.info("No log entries to render.")
        return

    # prepare display DataFrame
    disp = df.copy()
    # Format time column
    if 'created_at' in disp.columns:
        disp['created_at'] = pd.to_datetime(disp['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')

    # severity badges
    if 'severity' in disp.columns:
        disp['severity_badge'] = disp['severity'].apply(_severity_badge)
    else:
        disp['severity_badge'] = ''

    # short description
    if 'description' in disp.columns:
        disp['description'] = disp['description'].astype(str).str.slice(0, 120)

    # columns order
    columns = []
    for c in ['alert_id','alert_type','severity_badge','status','created_at','description']:
        if c in disp.columns:
            columns.append(c)

    # use st.markdown with unsafe_allow_html for custom badges
    # build HTML table because Streamlit DataFrame does not render HTML per cell
    html = "<div style='font-family:Arial,sans-serif'>"
    html += "<table style='width:100%;border-collapse:collapse'>"
    # headers
    html += "<thead><tr>"
    header_map = {'alert_id':'Alert ID','alert_type':'Type','severity_badge':'Severity','status':'Status','created_at':'Time','description':'Description'}
    for col in columns:
        html += f"<th style='text-align:left;padding:8px;border-bottom:1px solid #ddd'>{header_map.get(col,col)}</th>"
    html += "</tr></thead>"
    # rows
    html += "<tbody>"
    for _, row in disp.head(max_rows).iterrows():
        html += "<tr style='border-bottom:1px solid #f1f1f1'>"
        for col in columns:
            val = row[col]
            # status tag
            if col == 'status':
                status_val = str(val)
                if status_val.lower() == 'new':
                    badge = "<span style='color:#ffffff;background:#ff6b6b;padding:4px 8px;border-radius:6px'>NEW</span>"
                elif status_val.lower() == 'in_progress':
                    badge = "<span style='color:#0b0b0b;background:#ffd166;padding:4px 8px;border-radius:6px'>IN PROGRESS</span>"
                elif status_val.lower() == 'resolved':
                    badge = "<span style='color:#ffffff;background:#06d6a0;padding:4px 8px;border-radius:6px'>RESOLVED</span>"
                else:
                    badge = f"<span style='padding:4px 8px;border-radius:6px;background:#e0e0e0;color:#000'>{status_val}</span>"
                html += f"<td style='padding:8px'>{badge}</td>"
            elif col == 'severity_badge':
                html += f"<td style='padding:8px'>{val}</td>"
            else:
                safe = str(val) if pd.notna(val) else ''
                html += f"<td style='padding:8px;color:#0b0b0b'>{safe}</td>"
        html += "</tr>"
    html += "</tbody></table></div>"

    st.markdown(html, unsafe_allow_html=True)
