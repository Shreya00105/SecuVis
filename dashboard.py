import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from pymongo import MongoClient, errors
from charts import plot_time_series, plot_pie_distribution, plot_top_sources
from components.log_table import render_log_table

st.set_page_config(
    page_title="SecuVis — Threat Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- Config ----------
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "secuvis"
COLLECTION = "correlated_alerts"  # main alerts collection
VISUAL_COLLECTION = "visual_events"
NETWORK_COLLECTION = "network_events"

CSV_FALLBACK = "data/processed/structured_logs.csv"  # fallback path if no MongoDB

# ---------- Helpers ----------
@st.cache_data(ttl=300)
def load_from_mongo():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        client.server_info()  # trigger exception if cannot connect
        db = client[DB_NAME]
        alerts = list(db[COLLECTION].find({}))
        visuals = list(db[VISUAL_COLLECTION].find({}))
        networks = list(db[NETWORK_COLLECTION].find({}))
        df_alerts = pd.DataFrame(alerts)
        df_visuals = pd.DataFrame(visuals)
        df_networks = pd.DataFrame(networks)
        return df_alerts, df_visuals, df_networks
    except errors.ServerSelectionTimeoutError:
        return None, None, None

@st.cache_data(ttl=300)
def load_from_csv(path=CSV_FALLBACK):
    try:
        df = pd.read_csv(path, parse_dates=['timestamp'])
        return df
    except Exception:
        return pd.DataFrame()

# ---------- Load Data ----------
df_alerts, df_visuals, df_networks = load_from_mongo()

if df_alerts is None:
    st.warning("Could not connect to MongoDB. Falling back to CSV dataset (demo mode).")
    df = load_from_csv()
    # emulate alert dataframe with necessary fields:
    if not df.empty:
        df_alerts = df.rename(columns={'timestamp': 'created_at'})
        df_visuals = pd.DataFrame()
        df_networks = pd.DataFrame()
    else:
        df_alerts = pd.DataFrame()
        df_visuals = pd.DataFrame()
        df_networks = pd.DataFrame()

# ---------- Sidebar: Filters ----------
st.sidebar.header("Filters & Controls")
date_min = None
date_max = None
if not df_alerts.empty and 'created_at' in df_alerts.columns:
    try:
        df_alerts['created_at'] = pd.to_datetime(df_alerts['created_at'])
    except Exception:
        pass
    date_min = df_alerts['created_at'].min().date()
    date_max = df_alerts['created_at'].max().date()

start_date = st.sidebar.date_input("Start date", value=(date_min or (datetime.now() - timedelta(days=7)).date()))
end_date = st.sidebar.date_input("End date", value=(date_max or datetime.now().date()))
status_options = ["All", "new", "in_progress", "resolved"]
status = st.sidebar.selectbox("Status", status_options)
min_severity = st.sidebar.slider("Minimum severity", 0, 10, 4)

st.sidebar.markdown("---")
st.sidebar.write("Display options")
show_network = st.sidebar.checkbox("Show network events panel", value=True)
show_visual = st.sidebar.checkbox("Show visual events panel", value=True)
auto_refresh = st.sidebar.checkbox("Auto refresh (every 5 min)", value=True)

# ---------- Main UI ----------
st.title("🛡️ SECUVIS — Enterprise Threat Dashboard")
st.markdown("**Unified visual + network correlation** — YOLOv8 detections + rule-based network events")

# KPIs row
col1, col2, col3, col4 = st.columns([1.2,1.2,1.2,2])
total_alerts = len(df_alerts)
active_alerts = len(df_alerts[df_alerts.get('status','')!='resolved'])
avg_severity = round(df_alerts['severity'].mean(),2) if 'severity' in df_alerts.columns and not df_alerts.empty else 0
alerts_today = len(df_alerts[df_alerts.get('created_at', pd.Timestamp(0)) >= pd.Timestamp(datetime.now()-timedelta(days=1))])

col1.metric("Total Alerts", total_alerts)
col2.metric("Active Alerts", active_alerts)
col3.metric("Avg Severity", avg_severity)
col4.metric("Alerts (last 24h)", alerts_today)

st.markdown("---")

# Time series + distribution
left, right = st.columns([2,1.2])

with left:
    st.subheader("Threat Activity Over Time")
    if not df_alerts.empty and 'created_at' in df_alerts.columns:
        filtered = df_alerts[
            (df_alerts['created_at'].dt.date >= start_date) &
            (df_alerts['created_at'].dt.date <= end_date)
        ]
        if status != "All":
            filtered = filtered[filtered.get('status','') == status]
        filtered = filtered[filtered.get('severity',0) >= min_severity]
        plot_time_series(filtered, time_col='created_at', label_col='alert_type')
    else:
        st.info("No alert time-series data to display.")

with right:
    st.subheader("Threat Distribution")
    if not df_alerts.empty:
        plot_pie_distribution(df_alerts, col='alert_type')
        st.markdown("---")
        st.subheader("Top Sources")
        plot_top_sources(df_alerts, field='network_events')
    else:
        st.info("No distribution data available.")

st.markdown("---")

# Panels for raw events
if show_network:
    st.subheader("Network Events (Rule Engine Output)")
    if not df_networks.empty:
        st.dataframe(df_networks.sort_values('first_seen', ascending=False).head(200))
    else:
        st.info("No network events available.")

if show_visual:
    st.subheader("Visual Events (YOLOv8 Detections)")
    if not df_visuals.empty:
        # quick visual sample
        sample_vis = df_visuals.sort_values('frame_ts', ascending=False).head(200)
        st.dataframe(sample_vis[['camera_id','frame_ts','label','confidence']].reset_index(drop=True))
    else:
        st.info("No visual events available.")

st.markdown("---")

# Alerts table (big)
st.subheader("Correlated Alerts")
if not df_alerts.empty:
    # apply same filters to table
    table_df = filtered.copy() if 'filtered' in locals() else df_alerts.copy()
    # pick display columns
    cols = ['alert_id','alert_type','severity','status','created_at','description']
    display_df = table_df[[c for c in cols if c in table_df.columns]].sort_values('created_at', ascending=False)
    render_log_table(display_df)
else:
    st.info("No correlated alerts to show.")

st.markdown("---")
st.caption("SECUVIS — Enterprise Edition • YOLOv8 visual detection • MongoDB-backed event store")

# Auto-refresh hint (Streamlit has limited auto refresh; user can use the 'R' key)
if auto_refresh:
    st.experimental_rerun()
