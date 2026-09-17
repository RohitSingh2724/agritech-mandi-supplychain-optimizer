"""
Mandi Market Intelligence Dashboard (Executive Dark Theme)
---------------------------------------------------------
A Streamlit dashboard built on five cleaned agri-market CSVs (price & MSP,
arrivals, transport logistics, weather sensors, mandi master) integrated with
an AI Agent and natural language query capability.

Run with:  streamlit run app.py
"""

import re
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from agent import (AgentContext, SUGGESTED_QUESTIONS, answer_question, ask_claude, generate_insights, simulate_action_impact)

# PAGE CONFIG
st.set_page_config(
    page_title="Mandi Market Intelligence",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Flexible Data Directory Resolution
DATA_DIR = Path(__file__).parent / "data" / "processed"
if not (DATA_DIR / "clean_mandi_master.csv").exists():
    DATA_DIR = Path(__file__).parent / "data"
if not (DATA_DIR / "clean_mandi_master.csv").exists():
    DATA_DIR = Path(__file__).parent

# THEME / STYLE — Modern Dark Executive Theme
PRIMARY = "#38BDF8"       
PRIMARY_L = "#7DD3FC"    
PRIMARY_D = "#0284C7"    
SECONDARY = "#94A3B8"    
SECONDARY_L = "#CBD5E1"
DANGER = "#F87171"       
DANGER_L = "#FCA5A5"
GOOD = "#34D399"         
WARN = "#FBBF24"         
INK = "#F8FAFC"          
PAPER = "#0E1117"        
CARD = "#161B22"         
MUTED = "#94A3B8"        
LINE = "#30363D"         
SIDEBAR_BG = "#161B22"   
GRID = "#21262D"         

CROP_COLORS = {
    "Wheat": "#38BDF8",
    "Rice": "#34D399",
    "Maize": "#FBBF24",
    "Cotton": "#A78BFA",
    "Mustard": "#F87171",
    "Sugarcane": "#818CF8",
}

st.markdown(
    f"""
    <style>
    /* ---------- GLOBAL DARK THEME LOCK (PREVENTS LIGHT/DARK COLOR SHIFT) ---------- */
    html, body, [data-testid="stAppViewContainer"], .stApp {{
        background-color: #0E1117 !important;
        color: #F8FAFC !important;
    }}
    header[data-testid="stHeader"] {{
        background-color: #0E1117 !important;
    }}
    h1, h2, h3, h4, h5, h6, p, div, span, label, li {{
        color: #F8FAFC;
    }}
    div[data-testid="stMetricValue"] > div {{
        color: #38BDF8 !important;
    }}
    div[data-testid="stMetricLabel"] > div {{
        color: #94A3B8 !important;
    }}
    div[data-baseweb="select"] > div {{
        background-color: #1F242D !important;
        border-color: #30363D !important;
        color: #F8FAFC !important;
    }}
    div[data-baseweb="menu"], ul[role="listbox"], div[data-baseweb="popover"], div[data-baseweb="tooltip"] {{
        background-color: #161B22 !important;
        border: 1px solid #30363D !important;
        color: #F8FAFC !important;
    }}
    li[role="option"] {{
        background-color: #161B22 !important;
        color: #F8FAFC !important;
    }}
    li[role="option"]:hover, li[role="option"][aria-selected="true"] {{
        background-color: #1F242D !important;
        color: #38BDF8 !important;
    }}
    div[data-testid="stChatInput"] input, div[data-baseweb="input"] input {{
        background-color: #1F242D !important;
        color: #F8FAFC !important;
    }}

    /* ---------- canvas & typography ---------- */
    .stApp {{ background-color: #0E1117; color: #F8FAFC; }}
    h1, h2, h3 {{
        font-family: -apple-system, 'Segoe UI', 'Helvetica Neue', sans-serif;
        color: {INK}; letter-spacing: -0.01em;
    }}
    p, div, span, label {{ font-family: -apple-system, 'Segoe UI', 'Helvetica Neue', sans-serif; }}
    .block-container {{ padding-top: 1.1rem; max-width: 1500px; }}

    /* ---------- top bar ---------- */
    .topbar {{
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        border: 1px solid {LINE};
        border-left: 4px solid {PRIMARY};
        border-radius: 12px;
        padding: 18px 24px;
        margin-bottom: 16px;
        display: flex; align-items: center; justify-content: space-between;
        flex-wrap: wrap; gap: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.4);
    }}
    .topbar .tb-left {{ display: flex; align-items: center; gap: 14px; }}
    .topbar .tb-mark {{
        width: 44px; height: 44px; border-radius: 10px; flex-shrink: 0;
        background: linear-gradient(135deg, {PRIMARY_D} 0%, {PRIMARY} 100%);
        display: flex; align-items: center; justify-content: center; font-size: 1.3rem;
    }}
    .topbar h1 {{ margin: 0; font-size: 1.45rem; font-weight: 700; line-height: 1.2; color: #F8FAFC; }}
    .topbar .tb-sub {{ font-size: 0.84rem; color: {MUTED}; margin-top: 3px; }}
    .topbar .tb-right {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
    .pill {{
        background: #1F242D; border: 1px solid {LINE}; border-radius: 6px;
        padding: 6px 12px; font-size: 0.78rem; color: {INK}; font-weight: 600; white-space: nowrap;
    }}
    .pill .pill-k {{ color: {MUTED}; font-weight: 500; }}
    .pill-accent {{ background: {PRIMARY_D}; border-color: {PRIMARY}; color: #FFFFFF; }}

    /* ---------- Ultra-Modern KPI cards ---------- */
    .kpi-card {{
        background: linear-gradient(135deg, #161B22 0%, #1F242D 100%);
        border: 1px solid {LINE};
        border-radius: 12px;
        padding: 16px 18px;
        height: 136px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        position: relative; overflow: hidden;
        transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    }}
    .kpi-card:hover {{
        border-color: {PRIMARY};
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(56, 189, 248, 0.15);
    }}
    .kpi-card::after {{
        content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 3px;
        background: {PRIMARY};
    }}
    .kpi-card.risk::after {{ background: {DANGER}; }}
    .kpi-card.gold::after {{ background: {WARN}; }}
    .kpi-icon {{
        position: absolute; right: 14px; top: 13px; font-size: 1.1rem; opacity: 0.7;
    }}
    .kpi-label {{
        font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em;
        color: {MUTED}; margin-bottom: 8px; font-weight: 700;
    }}
    .kpi-value {{
        font-size: 1.7rem; font-weight: 700; color: {PRIMARY}; line-height: 1.1;
        font-variant-numeric: tabular-nums;
    }}
    .kpi-sub {{ font-size: 0.74rem; color: {MUTED}; margin-top: 5px; }}
    .kpi-delta {{
        font-size: 0.75rem; font-weight: 700; margin-top: 8px;
        display: inline-block; padding: 2px 8px; border-radius: 4px;
        font-variant-numeric: tabular-nums;
    }}
    .kpi-delta.up-good, .kpi-delta.down-good {{ color: {GOOD}; background: #064E3B; }}
    .kpi-delta.up-bad, .kpi-delta.down-bad {{ color: {DANGER}; background: #7F1D1D; }}
    .kpi-delta.flat {{ color: {MUTED}; background: #1F242D; }}

    /* ---------- panels & sections ---------- */
    .story-box {{
        background: {CARD};
        border: 1px solid {LINE}; border-left: 4px solid {PRIMARY};
        border-radius: 12px; padding: 18px 22px; margin-bottom: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        font-size: 0.92rem; line-height: 1.6; color: #E2E8F0;
    }}
    .section-head {{
        display: flex; align-items: baseline; gap: 9px;
        margin: 10px 0 10px 0; padding-bottom: 8px; border-bottom: 1px solid {LINE};
    }}
    .section-head .icon {{ font-size: 0.95rem; opacity: 0.8; }}
    .section-head .title {{ font-size: 1.0rem; font-weight: 700; color: #F8FAFC; letter-spacing: -0.01em; }}
    .section-head .caption {{ font-size: 0.78rem; color: {MUTED}; }}

    .badge {{
        display: inline-block; padding: 3px 9px; border-radius: 4px;
        font-size: 0.70rem; font-weight: 700; letter-spacing: 0.02em;
    }}
    .badge-high {{ background: #7F1D1D; color: {DANGER}; }}
    .badge-med {{ background: #78350F; color: {WARN}; }}
    .badge-low {{ background: #064E3B; color: {GOOD}; }}

    /* ---------- dark sidebar ---------- */
    section[data-testid="stSidebar"] {{ background-color: {SIDEBAR_BG} !important; border-right: 1px solid {LINE}; }}
    section[data-testid="stSidebar"] * {{ color: #E6EDF3 !important; }}
    section[data-testid="stSidebar"] label {{
        color: {PRIMARY} !important; font-size: 0.76rem !important;
        text-transform: uppercase; letter-spacing: 0.05em; font-weight: 700 !important;
    }}
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
        background-color: #1F242D !important; border-color: {LINE} !important;
        border-radius: 8px !important; color: #F8FAFC !important;
    }}

    /* ---------- tabs ---------- */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 6px; background: {CARD}; padding: 6px; border-radius: 10px;
        border: 1px solid {LINE}; box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: transparent; border-radius: 6px; padding: 9px 16px;
        border: none; font-weight: 600; font-size: 0.86rem; color: {MUTED} !important;
        transition: all 0.2s ease;
    }}
    .stTabs [data-baseweb="tab"]:hover {{ background-color: #1F242D !important; color: #F8FAFC !important; }}
    .stTabs [aria-selected="true"] {{
        background-color: #1F242D !important;
        color: {PRIMARY} !important;
        font-weight: 700 !important;
        border-bottom: 3px solid {PRIMARY} !important;
        border-radius: 6px 6px 2px 2px !important;
    }}
    .stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display: none; }}

    /* ---------- agent & cards ---------- */
    .insight {{
        background: {CARD}; border: 1px solid {LINE}; border-left: 4px solid {MUTED};
        border-radius: 10px; padding: 14px 18px; margin-bottom: 10px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }}
    .insight.high {{ border-left-color: {DANGER}; }}
    .insight.medium {{ border-left-color: {WARN}; }}
    .insight.low {{ border-left-color: {PRIMARY}; }}
    .insight.info {{ border-left-color: {SECONDARY}; }}
    .insight .ins-head {{ display: flex; align-items: center; gap: 9px; margin-bottom: 7px; }}
    .insight .ins-title {{ font-weight: 700; font-size: 0.95rem; color: #F8FAFC; }}
    .insight .ins-body {{ font-size: 0.87rem; line-height: 1.55; color: #CBD5E1; }}
    .insight .ins-meta {{
        font-size: 0.78rem; color: {MUTED}; margin-top: 7px;
        padding-top: 7px; border-top: 1px dashed {LINE};
    }}
    .insight .ins-meta b {{ color: #F8FAFC; }}
    .agent-answer {{
        background: {CARD}; border: 1px solid {LINE}; border-left: 4px solid {PRIMARY};
        border-radius: 10px; padding: 15px 18px; margin: 4px 0 12px 0;
        font-size: 0.9rem; line-height: 1.6; color: #E2E8F0;
    }}
    .agent-q {{
        font-size: 0.82rem; color: {PRIMARY}; font-weight: 600;
        margin: 14px 0 2px 0;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Number Formatting Helper (Clean Comma Separated Numbers)
def format_num(val, suffix=""):
    if pd.isna(val) or val is None:
        return "0"
    num = float(val)
    return f"{num:,.0f} {suffix}".strip()


def kpi_card(label, value, sub="", kind="", icon="🌾", delta=None, delta_good_when="up"):
    cls = f"kpi-card {kind}".strip()
    delta_html = ""
    if delta is not None:
        pct, direction = delta
        favourable = (direction == delta_good_when)
        arrow = "▲" if direction == "up" else "▼"
        tone = ("up-good" if (direction == "up" and favourable) else
                "down-good" if (direction == "down" and favourable) else
                "up-bad" if direction == "up" else "down-bad")
        delta_html = f'<div class="kpi-delta {tone}">{arrow} {abs(pct):,.1f}% vs prior period</div>'
    else:
        delta_html = '<div class="kpi-delta flat">— vs prior period n/a</div>'
    st.markdown(
        f"""<div class="{cls}">
                <span class="kpi-icon">{icon}</span>
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}</div>
                <div class="kpi-sub">{sub}</div>
                {delta_html}
            </div>""",
        unsafe_allow_html=True,
    )


def section_head(icon, title, caption=""):
    st.markdown(
        f"""<div class="section-head"><span class="icon">{icon}</span>
            <span class="title">{title}</span>
            <span class="caption">{caption}</span></div>""",
        unsafe_allow_html=True,
    )


SEV_RANK = {"high": 0, "medium": 1, "low": 2, "info": 3}


def risk_badge(score):
    if score >= 66:
        return '<span class="badge badge-high">High risk</span>'
    if score >= 33:
        return '<span class="badge badge-med">Medium risk</span>'
    return '<span class="badge badge-low">Low risk</span>'


CHART_TEMPLATE = dict(
    paper_bgcolor=CARD, plot_bgcolor=CARD,
    font=dict(family="-apple-system, Segoe UI, sans-serif", color=MUTED, size=11),
    title_font=dict(family="-apple-system, Segoe UI, sans-serif", size=14, color=INK),
    margin=dict(t=30, l=8, r=8, b=8),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10, color=INK)),
    xaxis=dict(gridcolor=GRID, linecolor=LINE, zerolinecolor=GRID),
    yaxis=dict(gridcolor=GRID, linecolor=LINE, zerolinecolor=GRID),
)

RISK_RAMP = ["#1F242D", "#C9A57A", DANGER]


# DATA LOADING + CLEANING
def normalize_mandi_id(x):
    if pd.isna(x):
        return np.nan
    digits = re.findall(r"\d+", str(x))
    if not digits:
        return np.nan
    return f"MANDI_{digits[0].zfill(3)}"


@st.cache_data(show_spinner=True)
def load_data():
    quality_log = {}

    master = pd.read_csv(DATA_DIR / "clean_mandi_master.csv")
    master["mandi_id"] = master["mandi_id"].apply(normalize_mandi_id)
    master["mandi_type"] = (
        master["mandi_type"].astype(str).str.strip().str.upper()
        .replace({"NAN": np.nan})
        .map({"APMC": "APMC", "PRIVATE": "Private", "DIRECT": "Direct"})
    )
    master["district"] = master["district"].astype(str).str.strip().str.title().replace("Nan", np.nan)
    master["state"] = master["state"].astype(str).str.strip().replace("nan", np.nan)
    master = master.drop_duplicates(subset="mandi_id")

    price_raw = pd.read_csv(DATA_DIR / "clean_price_and_msp.csv")
    price = price_raw.copy()
    price["mandi_id"] = price["mandi_id"].apply(normalize_mandi_id)
    price["clean_date"] = pd.to_datetime(price["clean_date"], errors="coerce")
    n_before = len(price)
    for c in ["min_price", "max_price", "modal_price", "msp"]:
        if c in price.columns:
            bad = price[c] < 50
            price.loc[bad, c] = np.nan
    price = price.dropna(subset=["clean_date", "modal_price", "mandi_id"])
    quality_log["price"] = dict(raw_rows=n_before, clean_rows=len(price), dropped_pct=round(100 * (1 - len(price) / n_before), 1))

    arr_raw = pd.read_csv(DATA_DIR / "clean_mandi_arrivals.csv")
    arr = arr_raw.copy()
    arr["mandi_id"] = arr["mandi_id"].apply(normalize_mandi_id)
    arr["clean_date"] = pd.to_datetime(arr["clean_date"], errors="coerce")
    n_before = len(arr)
    arr["arrival_quantity_qtl"] = arr["arrival_quantity_qtl"].abs()
    arr = arr.dropna(subset=["clean_date", "mandi_id", "arrival_quantity_qtl"])
    quality_log["arrivals"] = dict(raw_rows=n_before, clean_rows=len(arr), dropped_pct=round(100 * (1 - len(arr) / n_before), 1))

    trans_raw = pd.read_csv(DATA_DIR / "clean_transport_logistics.csv")
    trans = trans_raw.copy()
    trans["mandi_id"] = trans["mandi_id"].apply(normalize_mandi_id)
    trans["clean_date"] = pd.to_datetime(trans["clean_date"], errors="coerce")
    trans["distance_km"] = pd.to_numeric(trans["distance_km"], errors="coerce")
    n_before = len(trans)
    trans.loc[trans["clean_transit_hours"] > 200, "clean_transit_hours"] = np.nan
    trans = trans.dropna(subset=["mandi_id", "clean_transit_hours"])
    quality_log["transport"] = dict(raw_rows=n_before, clean_rows=len(trans), dropped_pct=round(100 * (1 - len(trans) / n_before), 1))

    weather_raw = pd.read_csv(DATA_DIR / "clean_weather_sensors.csv")
    weather = weather_raw.copy()
    weather["clean_date"] = pd.to_datetime(weather["clean_date"], errors="coerce")
    n_before = len(weather)
    weather = weather.dropna(subset=["clean_date"])
    quality_log["weather"] = dict(raw_rows=n_before, clean_rows=len(weather), dropped_pct=round(100 * (1 - len(weather) / n_before), 1))

    price = price.drop(columns=["district"], errors="ignore").merge(master[["mandi_id", "state", "district", "mandi_type"]], on="mandi_id", how="left")
    arr = arr.merge(master[["mandi_id", "state", "district", "mandi_type"]], on="mandi_id", how="left")
    trans = trans.merge(master[["mandi_id", "state", "district", "mandi_type"]], on="mandi_id", how="left")

    return master, price, arr, trans, weather, quality_log


master, price, arr, trans, weather, quality_log = load_data()

# SIDEBAR FILTERS (CLEAN DROPDOWNS)
st.sidebar.markdown(
    """<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 20px;">
        <div style="font-size: 1.5rem;">🌾</div>
        <div>
            <div style="font-weight: 700; font-size: 1.1rem; color: #F8FAFC;">MandiPulse</div>
            <div style="font-size: 0.72rem; color: #94A3B8;">Executive Dark Intelligence</div>
        </div>
       </div>""",
    unsafe_allow_html=True,
)

st.sidebar.markdown("### 🔍 Filter Scope")

# 1. State Dropdown
states_list = ["All States"] + sorted([s for s in master["state"].dropna().unique()])
selected_state = st.sidebar.selectbox("State", states_list)

# 2. District Dropdown
if selected_state != "All States":
    districts_pool = sorted(master.loc[master["state"] == selected_state, "district"].dropna().unique())
else:
    districts_pool = sorted(master["district"].dropna().unique())
selected_district = st.sidebar.selectbox("District", ["All Districts"] + districts_pool)

# 3. Crop Dropdown
crops_list = ["All Crops"] + sorted([c for c in price["crop_name"].dropna().unique() if c != "Unknown"])
selected_crop = st.sidebar.selectbox("Crop Variety", crops_list)

# 4. Friendly Mandi Dropdown
master["mandi_label"] = master.apply(
    lambda r: f"{r.get('mandi_name', 'Mandi')} ({r.get('district', 'District')}, {r.get('state', 'State')})", axis=1
)
mandi_label_dict = dict(zip(master["mandi_id"], master["mandi_label"]))
price["mandi_display"] = price["mandi_id"].map(mandi_label_dict).fillna(price["mandi_id"])
arr["mandi_display"] = arr["mandi_id"].map(mandi_label_dict).fillna(arr["mandi_id"])

mandis_list = ["All Mandis"] + sorted(list(set(arr["mandi_display"].dropna())))
selected_mandi_label = st.sidebar.selectbox("Mandi Market", mandis_list)

# Date Range Filter
st.sidebar.markdown("---")
min_date = min(price["clean_date"].min(), arr["clean_date"].min()).date()
max_date = max(price["clean_date"].max(), arr["clean_date"].max()).date()
date_range = st.sidebar.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date, key="f_date")
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Risk Score Weights")
w_price = st.sidebar.slider("Price / MSP weight", 0, 100, 45)
w_vol = st.sidebar.slider("Price volatility weight", 0, 100, 25)
w_log = st.sidebar.slider("Logistics delay weight", 0, 100, 30)
w_total = max(w_price + w_vol + w_log, 1)

st.sidebar.markdown("---")
claude_key = st.sidebar.text_input("Anthropic API key (optional)", type="password", placeholder="sk-ant-...")
claude_model = st.sidebar.text_input("Model", value="claude-sonnet-5")

# APPLY FILTERS
def apply_filters(df):
    m = df["clean_date"].between(pd.Timestamp(start_date), pd.Timestamp(end_date))
    if selected_state != "All States" and "state" in df.columns:
        m &= (df["state"] == selected_state)
    if selected_district != "All Districts" and "district" in df.columns:
        m &= (df["district"] == selected_district)
    if selected_crop != "All Crops" and "crop_name" in df.columns:
        m &= (df["crop_name"] == selected_crop)
    if selected_mandi_label != "All Mandis" and "mandi_display" in df.columns:
        m &= (df["mandi_display"] == selected_mandi_label)
    return df[m]

f_price = apply_filters(price)
f_arr = apply_filters(arr)
f_trans = apply_filters(trans)

if f_price.empty or f_arr.empty:
    st.warning("No data matches the current filters — reset your selections.")
    st.stop()

# METRIC CALCULATIONS
f_price["ym"] = f_price["clean_date"].dt.to_period("M")
f_arr["ym"] = f_arr["clean_date"].dt.to_period("M")

mandi_month_price = f_price.groupby(["mandi_id", "crop_name", "ym"])["modal_price"].mean().reset_index()
crop_month_price = f_price.groupby(["crop_name", "ym"])["modal_price"].mean().reset_index().rename(columns={"modal_price": "crop_modal_price"})

valued = f_arr.merge(mandi_month_price, on=["mandi_id", "crop_name", "ym"], how="left")
valued = valued.merge(crop_month_price, on=["crop_name", "ym"], how="left")
valued["modal_price"] = valued["modal_price"].fillna(valued["crop_modal_price"])
valued["market_value"] = valued["arrival_quantity_qtl"] * valued["modal_price"]

total_revenue = valued["market_value"].sum()
total_arrivals = f_arr["arrival_quantity_qtl"].sum()

msp_scope = f_price.dropna(subset=["msp"]).copy()
msp_scope["below_msp"] = msp_scope["modal_price"] < msp_scope["msp"]
churn_risk_rate = msp_scope["below_msp"].mean() if len(msp_scope) else np.nan
msp_compliance_rate = 1 - churn_risk_rate if pd.notna(churn_risk_rate) else np.nan

avg_transit = f_trans["clean_transit_hours"].mean() if len(f_trans) else np.nan
avg_distance = f_trans["distance_km"].mean() if len(f_trans) else np.nan

w_in_range = weather[weather["clean_date"].between(pd.Timestamp(start_date), pd.Timestamp(end_date))]
if len(w_in_range):
    heat_days = (w_in_range["temperature_celsius"] > 35).mean()
    heavy_rain_days = (w_in_range["rainfall_mm"] > w_in_range["rainfall_mm"].quantile(0.85)).mean()
    weather_risk_index = 100 * np.nanmean([heat_days, heavy_rain_days])
else:
    weather_risk_index = np.nan

# PRIOR PERIOD DELTA ENGINE
cur_days = (end_date - start_date).days + 1
prior_start = start_date - pd.Timedelta(days=cur_days)
prior_end = start_date - pd.Timedelta(days=1)

if prior_start < min_date:
    half_days = max(cur_days // 2, 1)
    prior_start_ts = pd.Timestamp(start_date)
    prior_end_ts = pd.Timestamp(start_date + pd.Timedelta(days=half_days - 1))
    cur_start_ts = pd.Timestamp(start_date + pd.Timedelta(days=half_days))
    cur_end_ts = pd.Timestamp(end_date)
else:
    prior_start_ts = pd.Timestamp(prior_start)
    prior_end_ts = pd.Timestamp(prior_end)
    cur_start_ts = pd.Timestamp(start_date)
    cur_end_ts = pd.Timestamp(end_date)

def get_filtered_window(df, s_ts, e_ts):
    if df.empty or "clean_date" not in df.columns:
        return pd.DataFrame()
    m = df["clean_date"].between(s_ts, e_ts)
    if selected_state != "All States" and "state" in df.columns:
        m &= (df["state"] == selected_state)
    if selected_district != "All Districts" and "district" in df.columns:
        m &= (df["district"] == selected_district)
    if selected_crop != "All Crops" and "crop_name" in df.columns:
        m &= (df["crop_name"] == selected_crop)
    if selected_mandi_label != "All Mandis" and "mandi_display" in df.columns:
        m &= (df["mandi_display"] == selected_mandi_label)
    return df[m]

p_price = get_filtered_window(price, prior_start_ts, prior_end_ts)
p_arr = get_filtered_window(arr, prior_start_ts, prior_end_ts)
p_trans = get_filtered_window(trans, prior_start_ts, prior_end_ts)

if not p_arr.empty and not p_price.empty:
    p_price["ym"] = p_price["clean_date"].dt.to_period("M")
    p_arr["ym"] = p_arr["clean_date"].dt.to_period("M")
    p_mandi_p = p_price.groupby(["mandi_id", "crop_name", "ym"])["modal_price"].mean().reset_index()
    p_crop_p = p_price.groupby(["crop_name", "ym"])["modal_price"].mean().reset_index().rename(columns={"modal_price": "crop_modal_price"})
    p_valued = p_arr.merge(p_mandi_p, on=["mandi_id", "crop_name", "ym"], how="left")
    p_valued = p_valued.merge(p_crop_p, on=["crop_name", "ym"], how="left")
    p_valued["modal_price"] = p_valued["modal_price"].fillna(p_valued["crop_modal_price"])
    p_rev = (p_valued["arrival_quantity_qtl"] * p_valued["modal_price"]).sum()
    p_arrivals = p_arr["arrival_quantity_qtl"].sum()
else:
    p_rev, p_arrivals = np.nan, np.nan

def calc_delta(cur, prior):
    if pd.isna(cur) or pd.isna(prior) or prior == 0:
        return None
    pct = 100 * (cur - prior) / prior
    direction = "up" if pct >= 0 else "down"
    return (pct, direction)

delta_rev = calc_delta(total_revenue, p_rev)
delta_arr = calc_delta(total_arrivals, p_arrivals)

p_msp = p_price.dropna(subset=["msp"]).copy() if not p_price.empty else pd.DataFrame()
if not p_msp.empty:
    p_msp["below_msp"] = p_msp["modal_price"] < p_msp["msp"]
    p_churn = p_msp["below_msp"].mean()
    p_compliance = 1 - p_churn
else:
    p_churn, p_compliance = np.nan, np.nan

delta_compliance = calc_delta(msp_compliance_rate, p_compliance)
delta_churn = calc_delta(churn_risk_rate, p_churn)

p_avg_transit = p_trans["clean_transit_hours"].mean() if not p_trans.empty else np.nan
delta_transit = calc_delta(avg_transit, p_avg_transit)

p_w = weather[weather["clean_date"].between(prior_start_ts, prior_end_ts)] if not weather.empty else pd.DataFrame()
if not p_w.empty:
    p_heat = (p_w["temperature_celsius"] > 35).mean()
    p_rain = (p_w["rainfall_mm"] > p_w["rainfall_mm"].quantile(0.85)).mean()
    p_weather_risk = 100 * np.nanmean([p_heat, p_rain])
else:
    p_weather_risk = np.nan

delta_weather = calc_delta(weather_risk_index, p_weather_risk)

# HEADER
st.markdown(
    f"""<div class="topbar">
        <div class="tb-left">
            <div class="tb-mark">🌾</div>
            <div>
                <h1>MandiPulse — Market Intelligence</h1>
                <div class="tb-sub">Where is the mandi network losing value for farmers, and why?</div>
            </div>
        </div>
        <div class="tb-right">
            <span class="pill pill-accent">{start_date:%d %b %Y} – {end_date:%d %b %Y}</span>
            <span class="pill"><span class="pill-k">State</span> {selected_state}</span>
            <span class="pill"><span class="pill-k">Crop</span> {selected_crop}</span>
        </div>
       </div>""",
    unsafe_allow_html=True,
)

# KPI GRID (ULTRA-MODERN DARK CARDS)
r1c1, r1c2, r1c3 = st.columns(3)
with r1c1:
    kpi_card("Est. Market Revenue", f"₹{total_revenue/1e7:,.1f} Cr", f"across filtered mandis", icon="💰", delta=delta_rev, delta_good_when="up")
with r1c2:
    kpi_card("Total Arrivals", f"{total_arrivals:,.0f} Qtl", f"crop volume in scope", icon="🚜", delta=delta_arr, delta_good_when="up")
with r1c3:
    kpi_card("MSP Compliance", f"{msp_compliance_rate*100:,.1f}%" if pd.notna(msp_compliance_rate) else "N/A", "sales at or above MSP", icon="✅", delta=delta_compliance, delta_good_when="up")

st.write("")

r2c1, r2c2, r2c3 = st.columns(3)
with r2c1:
    kpi_card("Farmer 'Churn' Risk", f"{churn_risk_rate*100:,.1f}%" if pd.notna(churn_risk_rate) else "N/A", "sales priced below MSP", kind="risk", icon="⚠️", delta=delta_churn, delta_good_when="down")
with r2c2:
    kpi_card("Avg Transit Time", f"{avg_transit:,.1f} hrs" if pd.notna(avg_transit) else "N/A", f"~{avg_distance:,.0f} km average trip", kind="gold", icon="🚚", delta=delta_transit, delta_good_when="down")
with r2c3:
    kpi_card("Weather Risk Index", f"{weather_risk_index:,.0f} / 100" if pd.notna(weather_risk_index) else "N/A", "heat + heavy-rain exposure", kind="risk", icon="🌦️", delta=delta_weather, delta_good_when="down")

st.write("")

# COMPOSITE MANDI RISK SCORE
sel_mandis = f_arr["mandi_id"].unique()
price_risk = msp_scope[msp_scope["mandi_id"].isin(sel_mandis)].groupby("mandi_id")["below_msp"].mean()
vol = f_price.groupby("mandi_id")["modal_price"].agg(["mean", "std"])
vol["cv"] = (vol["std"] / vol["mean"]).fillna(0)
log_risk = f_trans.groupby("mandi_id")["clean_transit_hours"].mean()

risk_df = pd.DataFrame(index=sel_mandis)
risk_df["price_risk"] = price_risk
risk_df["volatility"] = vol["cv"]
risk_df["transit_hrs"] = log_risk
risk_df = risk_df.dropna(how="all")

def _norm(s):
    s = s.astype(float)
    if s.max() == s.min(): return s * 0
    return (s - s.min()) / (s.max() - s.min())

risk_df["score"] = (
    _norm(risk_df["price_risk"].fillna(risk_df["price_risk"].median())) * (w_price / w_total)
    + _norm(risk_df["volatility"].fillna(risk_df["volatility"].median())) * (w_vol / w_total)
    + _norm(risk_df["transit_hrs"].fillna(risk_df["transit_hrs"].median())) * (w_log / w_total)
) * 100
risk_df = risk_df.merge(master[["mandi_id", "mandi_name", "district", "state"]], left_index=True, right_on="mandi_id")
risk_df = risk_df.sort_values("score", ascending=False)

agent_ctx = AgentContext(
    price=f_price, arrivals=f_arr, transport=f_trans, weather=w_in_range,
    valued=valued, risk=risk_df, master=master,
    metrics=dict(
        total_revenue=total_revenue, total_arrivals=total_arrivals,
        churn_rate=churn_risk_rate, avg_transit=avg_transit,
        start=f"{start_date:%d %b %Y}", end=f"{end_date:%d %b %Y}",
    ),
)

# TABS
tab_story, tab_agent, tab_price, tab_supply, tab_logistics, tab_weather, tab_quality = st.tabs(
    ["Overview & Risk", "🤖 AI Agent", "Price & MSP", "Arrivals & Supply", "Logistics", "Weather", "Data Quality"]
)

# TAB 1 — STORYTELLING & COMPOSITE RISK
with tab_story:
    st.markdown(
        f"""
        <div class="story-box">
        <b>Executive Overview:</b> Analyzing mandi operations across filtered selections. 
        <b>{churn_risk_rate*100:,.1f}%</b> of transactions were priced below MSP. 
        Mandi Risk Scores combine price risk, price volatility, and transport delay to highlight vulnerable market hubs.
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([1.3, 1])
    with c1:
        section_head("📊", "Riskiest mandis", "weighted composite risk score")
        top_risk = risk_df.head(12).sort_values("score")
        fig = px.bar(
            top_risk, x="score", y="mandi_name", orientation="h",
            color="score", color_continuous_scale=RISK_RAMP,
            labels={"score": "Risk score (0-100)", "mandi_name": ""},
        )
        fig.update_layout(coloraxis_showscale=False, **CHART_TEMPLATE, height=420)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section_head("🎯", "Mandi drill-down", "vs. network average")
        pick = st.selectbox("Inspect a mandi", risk_df["mandi_name"].tolist())
        row = risk_df[risk_df["mandi_name"] == pick].iloc[0]
        avg_row = risk_df[["price_risk", "volatility", "transit_hrs"]].mean()
        categories = ["Price risk", "Volatility", "Transit delay"]
        radar = go.Figure()
        radar.add_trace(go.Scatterpolar(
            r=[row["price_risk"] or 0, row["volatility"] or 0, (row["transit_hrs"] or 0) / max(risk_df["transit_hrs"].max(), 1)],
            theta=categories, fill="toself", name=pick, line_color=DANGER,
        ))
        radar.add_trace(go.Scatterpolar(
            r=[avg_row["price_risk"] or 0, avg_row["volatility"] or 0, (avg_row["transit_hrs"] or 0) / max(risk_df["transit_hrs"].max(), 1)],
            theta=categories, fill="toself", name="Network avg", line_color=PRIMARY, opacity=0.5,
        ))
        radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1], gridcolor=GRID)),
            showlegend=True, height=340, paper_bgcolor=CARD,
            font=CHART_TEMPLATE["font"], margin=CHART_TEMPLATE["margin"],
        )
        st.plotly_chart(radar, use_container_width=True)

# TAB 2 — AI AGENT
with tab_agent:
    # 1. Ask the Data Toggle Box (at the top)
    with st.expander("💬 Ask the Data (Interactive Q&A Chatbot)", expanded=True):
        if "agent_chat" not in st.session_state: st.session_state.agent_chat = []
        if "pending_q" not in st.session_state: st.session_state.pending_q = None

        qcols = st.columns(4)
        for idx, sq in enumerate(SUGGESTED_QUESTIONS):
            if qcols[idx % 4].button(sq, key=f"sq_{idx}", use_container_width=True):
                st.session_state.pending_q = sq

        typed = st.chat_input("Ask about risk, MSP, revenue, arrivals, prices, logistics or weather...")
        question = typed or st.session_state.pending_q
        st.session_state.pending_q = None

        if question:
            result = answer_question(question, agent_ctx)
            entry = {"q": question, "a": result["answer"], "table": result["table"], "llm": None}
            if bool(claude_key.strip()) and result["answer"].startswith("I couldn't map that"):
                with st.spinner("Asking Claude..."):
                    entry["llm"] = ask_claude(question, agent_ctx, claude_key.strip(), claude_model.strip() or "claude-sonnet-5")
            st.session_state.agent_chat.insert(0, entry)

        if st.session_state.agent_chat:
            for entry in st.session_state.agent_chat[:10]:
                st.markdown(f'<div class="agent-q">❓ {entry["q"]}</div>', unsafe_allow_html=True)
                body = entry["llm"] if entry["llm"] else entry["a"]
                st.markdown(f'<div class="agent-answer">{body}</div>', unsafe_allow_html=True)
                if entry["table"] is not None and not entry["table"].empty:
                    st.dataframe(entry["table"], use_container_width=True, hide_index=True)

    st.write("")

    # 2. Agent Findings (Top 3 priority alerts)
    a1, a2 = st.columns([3, 1])
    with a1:
        section_head("🧠", "Top Priority Agent Findings", "top 3 priority alerts")
    with a2:
        st.write("")
        rerun_agent = st.button("↻ Re-run analysis", use_container_width=True)

    with st.spinner("Agent is analyzing the selection..."):
        insights = generate_insights(agent_ctx)

    if insights:
        icons = {"high": "🔴", "medium": "🟠", "low": "🟢", "info": "🔵"}
        top_insights = insights[:3]
        for ins in top_insights:
            st.markdown(
                f"""<div class="insight {ins.severity}">
                    <div class="ins-head">
                        <span>{icons.get(ins.severity, '•')}</span>
                        <span class="ins-title">{ins.title}</span>
                        <span class="badge badge-{"high" if ins.severity=="high" else "med" if ins.severity=="medium" else "low"}">{ins.severity}</span>
                    </div>
                    <div class="ins-body">{ins.finding}</div>
                    <div class="ins-meta"><b>Evidence:</b> {ins.evidence}</div>
                    <div class="ins-meta"><b>Recommended action:</b> {ins.action}</div>
                   </div>""",
                unsafe_allow_html=True,
            )
        
        if len(insights) > 3:
            with st.expander(f"📋 View remaining {len(insights)-3} minor findings..."):
                for ins in insights[3:]:
                    st.markdown(
                        f"""<div class="insight {ins.severity}">
                            <div class="ins-head">
                                <span>{icons.get(ins.severity, '•')}</span>
                                <span class="ins-title">{ins.title}</span>
                                <span class="badge badge-{"high" if ins.severity=="high" else "med" if ins.severity=="medium" else "low"}">{ins.severity}</span>
                            </div>
                            <div class="ins-body">{ins.finding}</div>
                            <div class="ins-meta"><b>Evidence:</b> {ins.evidence}</div>
                            <div class="ins-meta"><b>Recommended action:</b> {ins.action}</div>
                           </div>""",
                        unsafe_allow_html=True,
                    )

    st.write("")
    section_head("⚡", "Executive action simulator & impact calculator", "model ROI & risk reduction live")
    sim_col1, sim_col2 = st.columns([1.2, 1])
    with sim_col1:
        act_choice = st.selectbox(
            "Select Mitigation Intervention",
            [
                "🎯 Government MSP Procurement Desk Intervention",
                "🚛 Logistics & Warehouse Route Optimization",
                "❄️ Mobile Cold Storage & Spoilage Mitigation",
            ],
            key="sim_act_choice"
        )
        cov_target = st.slider("Target Implementation Coverage (%)", 10, 100, 75, 5, key="sim_cov_slider") / 100.0

    act_key = "msp_procurement" if "MSP" in act_choice else "route_rerouting" if "Logistics" in act_choice else "cold_storage"
    impact = simulate_action_impact(act_key, agent_ctx, target_pct=cov_target)

    with sim_col2:
        st.markdown(f"**{impact.title}**")
        st.markdown(impact.summary)
    
    if impact.metrics:
        mcols = st.columns(len(impact.metrics))
        for idx, (k, v) in enumerate(impact.metrics.items()):
            mcols[idx].metric(k, v)
    
    if impact.details is not None and not impact.details.empty:
        st.dataframe(impact.details, use_container_width=True, hide_index=True)

# TAB 3 — PRICE & MSP
with tab_price:
    left, right = st.columns([1.4, 1])
    with left:
        section_head("💹", "Modal price trend", "by crop, monthly average")
        trend = f_price.groupby(["ym", "crop_name"])["modal_price"].mean().reset_index()
        trend["ym_ts"] = trend["ym"].dt.to_timestamp()
        fig = px.line(trend, x="ym_ts", y="modal_price", color="crop_name", markers=True,
                       labels={"ym_ts": "", "modal_price": "Modal price (₹/qtl)", "crop_name": "Crop"},
                       color_discrete_map=CROP_COLORS)
        fig.update_layout(**CHART_TEMPLATE, height=380)
        st.plotly_chart(fig, use_container_width=True)
    with right:
        section_head("📉", "MSP shortfall rate", "by crop")
        comp = msp_scope[msp_scope["mandi_id"].isin(sel_mandis)].groupby("crop_name")["below_msp"].mean().sort_values(ascending=False).reset_index()
        comp["below_msp"] *= 100
        fig2 = px.bar(comp, x="below_msp", y="crop_name", orientation="h",
                       labels={"below_msp": "% sales below MSP", "crop_name": ""},
                       color="below_msp", color_continuous_scale=RISK_RAMP)
        fig2.update_layout(coloraxis_showscale=False, **CHART_TEMPLATE, height=380)
        st.plotly_chart(fig2, use_container_width=True)

# TAB 4 — ARRIVALS & SUPPLY
with tab_supply:
    left, right = st.columns(2)
    with left:
        section_head("📥", "Arrivals over time", "by crop, monthly total")
        arr_trend = f_arr.groupby(["ym", "crop_name"])["arrival_quantity_qtl"].sum().reset_index()
        arr_trend["ym_ts"] = arr_trend["ym"].dt.to_timestamp()
        fig = px.area(arr_trend, x="ym_ts", y="arrival_quantity_qtl", color="crop_name",
                       labels={"ym_ts": "", "arrival_quantity_qtl": "Arrivals (Qtl)"},
                       color_discrete_map=CROP_COLORS)
        fig.update_layout(**CHART_TEMPLATE, height=400)
        st.plotly_chart(fig, use_container_width=True)
    with right:
        section_head("🍩", "Crop Volume Share (Centered Donut Chart)", "")
        crop_donut = f_arr.groupby("crop_name")["arrival_quantity_qtl"].sum().reset_index()
        fig_donut = px.pie(crop_donut, values="arrival_quantity_qtl", names="crop_name", hole=0.5)
        fig_donut.update_traces(textposition='inside', textinfo='percent+label')
        
        donut_template = {k: v for k, v in CHART_TEMPLATE.items() if k != "legend"}
        fig_donut.update_layout(
            **donut_template, height=400,
            legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_donut, use_container_width=True)

# TAB 5 — LOGISTICS
with tab_logistics:
    left, right = st.columns(2)
    with left:
        section_head("⏱️", "Transit time distribution", "histogram")
        fig = px.histogram(f_trans, x="clean_transit_hours", nbins=30, color_discrete_sequence=[PRIMARY],
                            labels={"clean_transit_hours": "Transit hours"})
        fig.update_layout(**CHART_TEMPLATE, height=380)
        st.plotly_chart(fig, use_container_width=True)
    with right:
        section_head("🏭", "Avg delay by warehouse", "")
        wh = f_trans.groupby("destination_warehouse").agg(
            trips=("mandi_id", "count"), avg_hrs=("clean_transit_hours", "mean")
        ).reset_index().sort_values("avg_hrs", ascending=False)
        fig2 = px.bar(wh, x="destination_warehouse", y="avg_hrs", color="avg_hrs",
                       color_continuous_scale=RISK_RAMP,
                       labels={"destination_warehouse": "", "avg_hrs": "Avg transit hrs"})
        fig2.update_layout(coloraxis_showscale=False, **CHART_TEMPLATE, height=380)
        st.plotly_chart(fig2, use_container_width=True)

# TAB 6 — WEATHER
with tab_weather:
    w_f = weather[weather["clean_date"].between(pd.Timestamp(start_date), pd.Timestamp(end_date))].copy()
    w_f["ym"] = w_f["clean_date"].dt.to_period("M").dt.to_timestamp()
    left, right = st.columns(2)
    with left:
        section_head("🌡️", "Temperature & rainfall", "over time")
        wt = w_f.groupby("ym").agg(avg_temp=("temperature_celsius", "mean"), avg_rain=("rainfall_mm", "mean")).reset_index()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=wt["ym"], y=wt["avg_temp"], name="Avg temp (°C)", line=dict(color=DANGER)))
        fig.add_trace(go.Bar(x=wt["ym"], y=wt["avg_rain"], name="Avg rainfall (mm)", marker_color="#9AAEC4", yaxis="y2", opacity=0.6))
        fig.update_layout(
            **{k: v for k, v in CHART_TEMPLATE.items() if k != "yaxis"}, height=380,
            yaxis=dict(title="°C", gridcolor=GRID, linecolor=LINE),
            yaxis2=dict(title="mm", overlaying="y", side="right", showgrid=False),
        )
        st.plotly_chart(fig, use_container_width=True)
    with right:
        section_head("☔", "Rainfall vs. arrivals", "correlation scatter")
        arr_month = f_arr.groupby(f_arr["clean_date"].dt.to_period("M").dt.to_timestamp())["arrival_quantity_qtl"].sum().reset_index()
        arr_month.columns = ["ym", "arrivals"]
        merged_w = wt.merge(arr_month, on="ym", how="inner")
        fig2 = px.scatter(merged_w, x="avg_rain", y="arrivals", trendline="ols" if len(merged_w) > 3 else None,
                           labels={"avg_rain": "Avg monthly rainfall (mm)", "arrivals": "Arrivals (Qtl)"},
                           color_discrete_sequence=[PRIMARY])
        fig2.update_layout(**CHART_TEMPLATE, height=380)
        st.plotly_chart(fig2, use_container_width=True)

# TAB 7 — DATA QUALITY
with tab_quality:
    section_head("🔍", "Data quality & row audit log", "")
    q = pd.DataFrame(quality_log).T
    q.columns = ["Raw rows", "Usable rows", "Dropped %"]
    st.dataframe(q, use_container_width=True)
    st.markdown("---")
    st.download_button(
        "⬇ Download filtered valuation dataset as CSV",
        data=valued.to_csv(index=False).encode("utf-8"),
        file_name="mandi_filtered_valuation.csv",
        mime="text/csv",
    )

# FOOTER
st.markdown(
    f"""<div style="margin-top: 30px; padding: 16px 4px; border-top: 1px solid {LINE}; display: flex; justify-content: space-between; font-size: 0.76rem; color: {MUTED};">
        <span>🌾 MandiPulse — Executive Dark Intelligence Dashboard</span>
        <span>Showing {len(sel_mandis)} mandis · {start_date:%d %b %Y}–{end_date:%d %b %Y}</span>
       </div>""",
    unsafe_allow_html=True,
)