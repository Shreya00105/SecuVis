import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd

def plot_time_series(df, time_col='created_at', label_col='alert_type'):
    """
    Plots a stacked time-series of alert counts per day/hour by type.
    df: pandas DataFrame with time_col as datetime
    """
    if df.empty:
        st.info("No data to plot.")
        return

    # group by hour
    df = df.copy()
    df[time_col] = pd.to_datetime(df[time_col])
    df['hour'] = df[time_col].dt.floor('H')
    grouped = df.groupby(['hour', label_col]).size().unstack(fill_value=0)
    fig, ax = plt.subplots(figsize=(10,4))
    grouped.plot(ax=ax, legend=True)
    ax.set_xlabel("Time (hour)")
    ax.set_ylabel("Alert Count")
    ax.set_title("Alerts per Hour by Type")
    ax.grid(alpha=0.2)
    st.pyplot(fig)

def plot_pie_distribution(df, col='alert_type'):
    if df.empty or col not in df.columns:
        st.info("No data for distribution.")
        return
    counts = df[col].value_counts()
    fig, ax = plt.subplots(figsize=(4,4))
    ax.pie(counts.values, labels=counts.index, autopct='%1.1f%%', startangle=140)
    ax.set_title(f"Distribution by {col}")
    st.pyplot(fig)

def plot_top_sources(df, field='network_events'):
    """
    Attempts to extract top source IPs or top network events.
    For generic display, it will look for src_ip inside the nested network_events or top 'src_ip' column.
    """
    if df.empty:
        st.info("No data")
        return

    # Try to find src_ip column
    if 'src_ip' in df.columns:
        tops = df['src_ip'].value_counts().head(8)
    else:
        # attempt nested field if network_events column exists and is list-like
        if field in df.columns:
            # attempt to flatten
            s = df[field].dropna().astype(str)
            # naive parsing: find ip-like tokens
            ip_series = s.str.extractall(r'(\b(?:\d{1,3}\.){3}\d{1,3}\b)')[0]
            if ip_series is not None and not ip_series.empty:
                tops = ip_series.value_counts().head(8)
            else:
                st.info("No detectable source IPs")
                return
        else:
            st.info("No source field available")
            return

    fig, ax = plt.subplots(figsize=(4,3))
    tops.plot(kind='barh', ax=ax)
    ax.invert_yaxis()
    ax.set_xlabel("Count")
    ax.set_ylabel("Source")
    ax.set_title("Top Sources")
    st.pyplot(fig)
