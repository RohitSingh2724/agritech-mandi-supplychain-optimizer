"""
Mandi Market Intelligence Dashboard
------------------------------------
A Streamlit dashboard built on five raw agri-market CSVs (price & MSP,
arrivals, transport logistics, weather sensors, mandi master) to answer one
business question:

    "Where is the mandi network losing value for farmers, and why?"

Run with:  streamlit run app.py
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from agent import (AgentContext, SUGGESTED_QUESTIONS, answer_question,
                   ask_claude, generate_insights)

# --------------------------------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Mandi Market Intelligence",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR = Path(__file__).parent / "data"

# --------------------------------------------------------------------------
# THEME / STYLE  —  slate / grey analytics theme
# --------------------------------------------------------------------------
PRIMARY = "#4A6FA5"      # slate blue (primary accent)
PRIMARY_L = "#6B8CBE"    # lighter slate for gradients
PRIMARY_D = "#33507A"    # deep slate
SECONDARY = "#8A94A6"    # cool grey (neutral series)
SECONDARY_L = "#AEB6C4"
DANGER = "#B4553F"       # muted brick (risk / alert)
DANGER_L = "#C97D6A"
GOOD = "#3E7D62"         # muted teal-green (positive delta)
WARN = "#A8792C"         # amber (medium risk)
INK = "#1B1F24"          # near-black text
PAPER = "#EEF1F4"        # light grey canvas
CARD = "#FFFFFF"
MUTED = "#6B7280"        # secondary text grey
LINE = "#DDE2E8"         # hairline borders
SIDEBAR_BG = "#22272E"   # charcoal sidebar
GRID = "#EDF0F3"         # chart gridlines

# One fixed color per crop so the same crop is always the same color,
# on every chart, in every tab — a hallmark of a "real" BI tool.
# Tuned to sit calmly against the grey canvas.
CROP_COLORS = {
    "Wheat": "#4A6FA5",
    "Rice": "#3E7D62",
    "Maize": "#A8792C",
    "Cotton": "#7D8597",
    "Mustard": "#B4553F",
    "Sugarcane": "#5C7C99",
}

st.markdown(
    f"""
    <style>
    /* ---------- canvas & typography ---------- */
    .stApp {{ background-color: {PAPER}; color: {INK}; }}
    h1, h2, h3 {{
        font-family: -apple-system, 'Segoe UI', 'Helvetica Neue', sans-serif;
        color: {INK}; letter-spacing: -0.01em;
    }}
    p, div, span, label {{ font-family: -apple-system, 'Segoe UI', 'Helvetica Neue', sans-serif; }}
    .block-container {{ padding-top: 1.1rem; max-width: 1500px; }}

    /* ---------- top bar ---------- */
    .topbar {{
        background: {CARD};
        border: 1px solid {LINE};
        border-top: 3px solid {PRIMARY};
        border-radius: 8px;
        padding: 16px 22px;
        margin-bottom: 12px;
        display: flex; align-items: center; justify-content: space-between;
        flex-wrap: wrap; gap: 12px;
        box-shadow: 0 1px 3px rgba(27,31,36,0.06);
    }}
    .topbar .tb-left {{ display: flex; align-items: center; gap: 14px; }}
    .topbar .tb-mark {{
        width: 42px; height: 42px; border-radius: 8px; flex-shrink: 0;
        background: linear-gradient(135deg, {PRIMARY_D} 0%, {PRIMARY} 100%);
        display: flex; align-items: center; justify-content: center; font-size: 1.25rem;
    }}
    .topbar h1 {{ margin: 0; font-size: 1.4rem; font-weight: 700; line-height: 1.2; }}
    .topbar .tb-sub {{ font-size: 0.83rem; color: {MUTED}; margin-top: 2px; }}
    .topbar .tb-right {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
    .pill {{
        background: {PAPER}; border: 1px solid {LINE}; border-radius: 6px;
        padding: 6px 12px; font-size: 0.78rem; color: {INK}; font-weight: 600; white-space: nowrap;
    }}
    .pill .pill-k {{ color: {MUTED}; font-weight: 500; }}
    .pill-accent {{ background: {PRIMARY}; border-color: {PRIMARY}; color: #FFFFFF; }}

    /* ---------- KPI cards ---------- */
    .kpi-card {{
        background: {CARD};
        border: 1px solid {LINE};
        border-radius: 8px;
        padding: 15px 17px;
        height: 132px;
        box-shadow: 0 1px 3px rgba(27,31,36,0.06);
        position: relative; overflow: hidden;
        transition: box-shadow 0.15s ease, border-color 0.15s ease;
    }}
    .kpi-card:hover {{ box-shadow: 0 4px 12px rgba(27,31,36,0.10); border-color: #C9D1DA; }}
    .kpi-card::after {{
        content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 3px;
        background: {PRIMARY};
    }}
    .kpi-card.risk::after {{ background: {DANGER}; }}
    .kpi-card.gold::after {{ background: {WARN}; }}
    .kpi-icon {{
        position: absolute; right: 14px; top: 13px; font-size: 0.95rem; opacity: 0.45;
    }}
    .kpi-label {{
        font-size: 0.70rem; text-transform: uppercase; letter-spacing: 0.06em;
        color: {MUTED}; margin-bottom: 9px; font-weight: 700;
    }}
    .kpi-value {{
        font-size: 1.6rem; font-weight: 700; color: {INK}; line-height: 1.1;
        font-variant-numeric: tabular-nums;
    }}
    .kpi-sub {{ font-size: 0.74rem; color: {MUTED}; margin-top: 5px; }}
    .kpi-delta {{
        font-size: 0.75rem; font-weight: 700; margin-top: 8px;
        display: inline-block; padding: 2px 8px; border-radius: 4px;
        font-variant-numeric: tabular-nums;
    }}
    .kpi-delta.up-good, .kpi-delta.down-good {{ color: {GOOD}; background: #E8F1ED; }}
    .kpi-delta.up-bad, .kpi-delta.down-bad {{ color: {DANGER}; background: #F7E9E5; }}
    .kpi-delta.flat {{ color: {MUTED}; background: {PAPER}; }}

    /* ---------- panels & sections ---------- */
    .story-box {{
        background: {CARD};
        border: 1px solid {LINE}; border-left: 3px solid {PRIMARY};
        border-radius: 8px; padding: 18px 22px; margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(27,31,36,0.06);
        font-size: 0.92rem; line-height: 1.6;
    }}
    .section-head {{
        display: flex; align-items: baseline; gap: 9px;
        margin: 10px 0 10px 0; padding-bottom: 8px; border-bottom: 1px solid {LINE};
    }}
    .section-head .icon {{ font-size: 0.95rem; opacity: 0.7; }}
    .section-head .title {{ font-size: 1.0rem; font-weight: 700; color: {INK}; letter-spacing: -0.01em; }}
    .section-head .caption {{ font-size: 0.78rem; color: {MUTED}; }}

    .badge {{
        display: inline-block; padding: 3px 9px; border-radius: 4px;
        font-size: 0.70rem; font-weight: 700; letter-spacing: 0.02em;
    }}
    .badge-high {{ background: #F7E9E5; color: {DANGER}; }}
    .badge-med {{ background: #F7EFE0; color: {WARN}; }}
    .badge-low {{ background: #E8F1ED; color: {GOOD}; }}

    /* ---------- dark sidebar ---------- */
    section[data-testid="stSidebar"] {{ background-color: {SIDEBAR_BG}; }}
    section[data-testid="stSidebar"] * {{ color: #D5DAE1; }}
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4 {{ color: #FFFFFF; }}
    section[data-testid="stSidebar"] label {{
        color: #9BA4B0 !important; font-size: 0.74rem !important;
        text-transform: uppercase; letter-spacing: 0.05em; font-weight: 700 !important;
    }}
    /* sidebar inputs on dark */
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div,
    section[data-testid="stSidebar"] div[data-baseweb="input"] > div {{
        background-color: #2C323A !important; border-color: #3A424C !important;
    }}
    section[data-testid="stSidebar"] div[data-baseweb="tag"] {{
        background-color: {PRIMARY} !important; color: #FFFFFF !important;
    }}
    section[data-testid="stSidebar"] div[data-baseweb="tag"] span {{ color: #FFFFFF !important; }}
    section[data-testid="stSidebar"] .stButton button {{
        background-color: #2C323A; color: #D5DAE1; border: 1px solid #3A424C;
        border-radius: 6px; font-weight: 600;
    }}
    section[data-testid="stSidebar"] .stButton button:hover {{
        background-color: {PRIMARY}; border-color: {PRIMARY}; color: #FFFFFF;
    }}
    .sidebar-brand {{
        display: flex; align-items: center; gap: 11px; padding: 2px 0 16px 0;
        border-bottom: 1px solid #333A44; margin-bottom: 16px;
    }}
    .sidebar-brand .logo {{
        width: 36px; height: 36px; border-radius: 8px;
        background: linear-gradient(135deg, {PRIMARY_D} 0%, {PRIMARY} 100%);
        display: flex; align-items: center; justify-content: center; font-size: 1.1rem;
    }}
    .sidebar-brand .name {{ font-weight: 700; font-size: 1.0rem; color: #FFFFFF; line-height: 1.15; }}
    .sidebar-brand .tag {{ font-size: 0.70rem; color: #8993A1; letter-spacing: 0.04em; text-transform: uppercase; }}
    .side-divider {{
        border-top: 1px solid #333A44; margin: 18px 0 14px 0;
        font-size: 0.68rem; color: #8993A1; text-transform: uppercase;
        letter-spacing: 0.08em; font-weight: 700; padding-top: 12px;
    }}

    /* ---------- tabs ---------- */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 2px; background: {CARD}; padding: 5px; border-radius: 8px;
        border: 1px solid {LINE}; box-shadow: 0 1px 3px rgba(27,31,36,0.05);
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: transparent; border-radius: 6px; padding: 9px 16px;
        border: none; font-weight: 600; font-size: 0.86rem; color: {MUTED};
    }}
    .stTabs [data-baseweb="tab"]:hover {{ background-color: {PAPER}; color: {INK}; }}
    .stTabs [aria-selected="true"] {{
        background-color: {PRIMARY} !important; color: #FFFFFF !important;
    }}
    .stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display: none; }}

    /* ---------- misc ---------- */
    div[data-testid="stMetric"] {{
        background: {CARD}; border: 1px solid {LINE}; border-radius: 8px; padding: 10px 14px;
    }}
    div[data-testid="stDataFrame"] {{ border: 1px solid {LINE}; border-radius: 8px; }}
    .stDownloadButton button {{
        background-color: {PRIMARY}; color: #FFFFFF; border: none;
        border-radius: 6px; font-weight: 600;
    }}
    .stDownloadButton button:hover {{ background-color: {PRIMARY_D}; color: #FFFFFF; }}

    .app-footer {{
        margin-top: 30px; padding: 16px 4px; border-top: 1px solid {LINE};
        display: flex; justify-content: space-between; flex-wrap: wrap; gap: 6px;
        font-size: 0.76rem; color: {MUTED};
    }}

    table {{ width: 100%; border-collapse: collapse; font-size: 0.84rem; }}
    table th {{
        text-align: left; padding: 9px 10px; border-bottom: 1px solid {LINE};
        color: {MUTED}; text-transform: uppercase; font-size: 0.68rem;
        letter-spacing: 0.05em; font-weight: 700;
    }}
    table td {{ padding: 9px 10px; border-bottom: 1px solid {LINE}; }}
    table tr:hover td {{ background: {PAPER}; }}

    /* ---------- agent ---------- */
    .insight {{
        background: {CARD}; border: 1px solid {LINE}; border-left: 3px solid {MUTED};
        border-radius: 8px; padding: 14px 18px; margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(27,31,36,0.05);
    }}
    .insight.high {{ border-left-color: {DANGER}; }}
    .insight.medium {{ border-left-color: {WARN}; }}
    .insight.low {{ border-left-color: {PRIMARY}; }}
    .insight.info {{ border-left-color: {SECONDARY}; }}
    .insight .ins-head {{ display: flex; align-items: center; gap: 9px; margin-bottom: 7px; }}
    .insight .ins-title {{ font-weight: 700; font-size: 0.95rem; color: {INK}; }}
    .insight .ins-body {{ font-size: 0.87rem; line-height: 1.55; color: #333A42; }}
    .insight .ins-meta {{
        font-size: 0.78rem; color: {MUTED}; margin-top: 7px;
        padding-top: 7px; border-top: 1px dashed {LINE};
    }}
    .insight .ins-meta b {{ color: {INK}; }}
    .agent-answer {{
        background: {CARD}; border: 1px solid {LINE}; border-left: 3px solid {PRIMARY};
        border-radius: 8px; padding: 15px 18px; margin: 4px 0 12px 0;
        font-size: 0.9rem; line-height: 1.6;
        box-shadow: 0 1px 3px rgba(27,31,36,0.05);
    }}
    .agent-q {{
        font-size: 0.82rem; color: {MUTED}; font-weight: 600;
        margin: 14px 0 2px 0;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


def kpi_card(label, value, sub="", kind="", icon="🌾", delta=None, delta_good_when="up"):
    """delta: (pct_change, direction 'up'/'down') or None. delta_good_when: 'up' means
    an increase is favourable (green), 'down' means a decrease is favourable (e.g. risk)."""
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
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
    xaxis=dict(gridcolor=GRID, linecolor=LINE, zerolinecolor=GRID),
    yaxis=dict(gridcolor=GRID, linecolor=LINE, zerolinecolor=GRID),
)

# Neutral grey-to-accent ramp used for every continuous (risk/intensity) scale
GREY_RAMP = ["#E4E8ED", SECONDARY_L, PRIMARY]
RISK_RAMP = ["#E4E8ED", "#C9A57A", DANGER]


# --------------------------------------------------------------------------
# DATA LOADING + CLEANING  (cached — raw messy CSVs in, tidy frames out)
# --------------------------------------------------------------------------
def normalize_mandi_id(x):
    """MANDI-042 / mandi_019 / '038' / MANDI050  ->  MANDI_038 (one format)."""
    if pd.isna(x):
        return np.nan
    digits = re.findall(r"\d+", str(x))
    if not digits:
        return np.nan
    return f"MANDI_{digits[0].zfill(3)}"


@st.cache_data(show_spinner=True)
def load_data():
    quality_log = {}

    # ---- mandi master -----------------------------------------------
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

    # ---- price & MSP ---------------------------------------------------
    price_raw = pd.read_csv(DATA_DIR / "clean_price_and_msp.csv")
    price = price_raw.copy()
    price["mandi_id"] = price["mandi_id"].apply(normalize_mandi_id)
    price["clean_date"] = pd.to_datetime(price["clean_date"], errors="coerce")
    n_before = len(price)
    # Values under 50 are unit/decimal entry errors for these crops (real
    # modal prices run into the thousands per quintal) -> treat as missing.
    for c in ["min_price", "max_price", "modal_price", "msp"]:
        bad = price[c] < 50
        price.loc[bad, c] = np.nan
    price = price.dropna(subset=["clean_date", "modal_price", "mandi_id"])
    quality_log["price"] = dict(
        raw_rows=n_before,
        clean_rows=len(price),
        dropped_pct=round(100 * (1 - len(price) / n_before), 1),
    )

    # ---- arrivals --------------------------------------------------------
    arr_raw = pd.read_csv(DATA_DIR / "clean_mandi_arrivals.csv")
    arr = arr_raw.copy()
    arr["mandi_id"] = arr["mandi_id"].apply(normalize_mandi_id)
    arr["clean_date"] = pd.to_datetime(arr["clean_date"], errors="coerce")
    n_before = len(arr)
    arr["arrival_quantity_qtl"] = arr["arrival_quantity_qtl"].abs()  # fix sign errors
    arr = arr.dropna(subset=["clean_date", "mandi_id", "arrival_quantity_qtl"])
    quality_log["arrivals"] = dict(
        raw_rows=n_before,
        clean_rows=len(arr),
        dropped_pct=round(100 * (1 - len(arr) / n_before), 1),
    )

    # ---- transport logistics ---------------------------------------------
    trans_raw = pd.read_csv(DATA_DIR / "clean_transport_logistics.csv")
    trans = trans_raw.copy()
    trans["mandi_id"] = trans["mandi_id"].apply(normalize_mandi_id)
    trans["clean_date"] = pd.to_datetime(trans["clean_date"], errors="coerce")
    trans["distance_km"] = pd.to_numeric(trans["distance_km"], errors="coerce")
    n_before = len(trans)
    # transit-hour parsing occasionally leaked a 4-digit year into the field
    trans.loc[trans["clean_transit_hours"] > 200, "clean_transit_hours"] = np.nan
    trans = trans.dropna(subset=["mandi_id", "clean_transit_hours"])
    quality_log["transport"] = dict(
        raw_rows=n_before,
        clean_rows=len(trans),
        dropped_pct=round(100 * (1 - len(trans) / n_before), 1),
    )

    # ---- weather -----------------------------------------------------------
    weather_raw = pd.read_csv(DATA_DIR / "clean_weather_sensors.csv")
    weather = weather_raw.copy()
    weather["clean_date"] = pd.to_datetime(weather["clean_date"], errors="coerce")
    n_before = len(weather)
    weather = weather.dropna(subset=["clean_date"])
    quality_log["weather"] = dict(
        raw_rows=n_before,
        clean_rows=len(weather),
        dropped_pct=round(100 * (1 - len(weather) / n_before), 1),
    )

    # ---- enrich price / arrivals / transport with master geography -------
    # (master is the canonical mandi -> geography map; drop each file's own
    # loosely-formatted district field in favour of it for consistency)
    price = price.drop(columns=["district"], errors="ignore").merge(
        master[["mandi_id", "state", "district", "mandi_type"]], on="mandi_id", how="left"
    )
    arr = arr.merge(master[["mandi_id", "state", "district", "mandi_type"]], on="mandi_id", how="left")
    trans = trans.merge(master[["mandi_id", "state", "district", "mandi_type"]], on="mandi_id", how="left")

    return master, price, arr, trans, weather, quality_log


master, price, arr, trans, weather, quality_log = load_data()

# --------------------------------------------------------------------------
# SIDEBAR FILTERS
# --------------------------------------------------------------------------
st.sidebar.markdown(
    """<div class="sidebar-brand">
        <div class="logo">🌾</div>
        <div><div class="name">MandiPulse</div><div class="tag">Market Intelligence</div></div>
       </div>""",
    unsafe_allow_html=True,
)

FILTER_KEYS = ["f_date", "f_state", "f_district", "f_type", "f_crop", "f_mandi", "f_wp", "f_wv", "f_wl"]
if st.sidebar.button("↺ Reset all filters", width="stretch"):
    for k in FILTER_KEYS:
        st.session_state.pop(k, None)
    st.rerun()

ALL = "🟢 ALL"


def multiselect_all(label, options, key):
    """Multiselect with a single-click 'ALL' entry at the top.

    Picking ALL selects every option at once. The widget defaults to ALL, so the
    dashboard opens on the full dataset. Stale selections (e.g. districts that
    disappear after changing the State filter) are dropped automatically so the
    widget never errors on a value that is no longer a valid option.
    """
    options = list(options)
    choices = [ALL] + options

    # Drop any previously-selected values that are no longer valid options.
    if key in st.session_state:
        kept = [v for v in st.session_state[key] if v in choices]
        st.session_state[key] = kept if kept else [ALL]
    else:
        st.session_state[key] = [ALL]

    picked = st.sidebar.multiselect(label, choices, key=key)

    if ALL in picked or not picked:
        return options
    return picked


st.sidebar.markdown('<div class="side-divider">Scope</div>', unsafe_allow_html=True)

min_date = min(price["clean_date"].min(), arr["clean_date"].min()).date()
max_date = max(price["clean_date"].max(), arr["clean_date"].max()).date()
date_range = st.sidebar.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date, key="f_date")
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

states = sorted([s for s in master["state"].dropna().unique()])
sel_states = multiselect_all("State", states, "f_state")

districts_pool = sorted(master.loc[master["state"].isin(sel_states), "district"].dropna().unique())
sel_districts = multiselect_all("District", districts_pool, "f_district")

mandi_types = sorted(master["mandi_type"].dropna().unique())
sel_types = multiselect_all("Mandi type", mandi_types, "f_type")

crops = sorted(price["crop_name"].dropna().unique())
sel_crops = multiselect_all("Crop", crops, "f_crop")

eligible_mandis = sorted(
    master.loc[
        master["state"].isin(sel_states)
        & master["district"].isin(sel_districts)
        & master["mandi_type"].isin(sel_types),
        "mandi_id",
    ].unique()
)
sel_mandis = multiselect_all("Mandi", eligible_mandis, "f_mandi")

st.sidebar.markdown('<div class="side-divider">Risk score weights</div>', unsafe_allow_html=True)
st.sidebar.caption("Tune how the composite Mandi Risk Score (Storytelling tab) is built.")
w_price = st.sidebar.slider("Price / MSP weight", 0, 100, 45, key="f_wp")
w_vol = st.sidebar.slider("Price volatility weight", 0, 100, 25, key="f_wv")
w_log = st.sidebar.slider("Logistics delay weight", 0, 100, 30, key="f_wl")
w_total = max(w_price + w_vol + w_log, 1)

st.sidebar.markdown('<div class="side-divider">AI Agent</div>', unsafe_allow_html=True)
st.sidebar.caption(
    "The agent analyses the filtered data on its own — no key needed. "
    "Add a Claude API key only if you also want free-form questions answered in natural language."
)
claude_key = st.sidebar.text_input("Anthropic API key (optional)", type="password", key="f_key",
                                   placeholder="sk-ant-...")
claude_model = st.sidebar.text_input("Model", value="claude-sonnet-5", key="f_model")


def in_filters(df):
    m = (
        df["clean_date"].between(pd.Timestamp(start_date), pd.Timestamp(end_date))
        & df["mandi_id"].isin(sel_mandis)
    )
    if "crop_name" in df.columns:
        m &= df["crop_name"].isin(sel_crops)
    return df[m]


f_price = in_filters(price)
f_arr = in_filters(arr)
f_trans = in_filters(trans)

if f_price.empty or f_arr.empty:
    st.warning("No data matches the current filters — widen the date range or selection.")
    st.stop()

# --------------------------------------------------------------------------
# CORE METRIC CALCULATIONS
# --------------------------------------------------------------------------
f_price = f_price.copy()
f_arr = f_arr.copy()
f_price["ym"] = f_price["clean_date"].dt.to_period("M")
f_arr["ym"] = f_arr["clean_date"].dt.to_period("M")

mandi_month_price = f_price.groupby(["mandi_id", "crop_name", "ym"])["modal_price"].mean().reset_index()
crop_month_price = f_price.groupby(["crop_name", "ym"])["modal_price"].mean().reset_index().rename(
    columns={"modal_price": "crop_modal_price"}
)

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

# ---- period-over-period comparison (same-length window immediately before) ----
period_days = (end_date - start_date).days + 1
prev_end = pd.Timestamp(start_date) - pd.Timedelta(days=1)
prev_start = prev_end - pd.Timedelta(days=period_days - 1)

def prev_period(df):
    m = df["clean_date"].between(prev_start, prev_end) & df["mandi_id"].isin(sel_mandis)
    if "crop_name" in df.columns:
        m &= df["crop_name"].isin(sel_crops)
    return df[m]

p_price = prev_period(price)
p_arr = prev_period(arr)
p_trans = prev_period(trans)

def pct_delta(curr, prev):
    if prev is None or pd.isna(prev) or prev == 0 or pd.isna(curr):
        return None
    change = 100 * (curr - prev) / prev
    return (change, "up" if change >= 0 else "down")

if len(p_arr) and len(p_price):
    p_price_ = p_price.copy()
    p_arr_ = p_arr.copy()
    p_price_["ym"] = p_price_["clean_date"].dt.to_period("M")
    p_arr_["ym"] = p_arr_["clean_date"].dt.to_period("M")
    p_mmp = p_price_.groupby(["mandi_id", "crop_name", "ym"])["modal_price"].mean().reset_index()
    p_cmp = p_price_.groupby(["crop_name", "ym"])["modal_price"].mean().reset_index().rename(columns={"modal_price": "crop_modal_price"})
    p_valued = p_arr_.merge(p_mmp, on=["mandi_id", "crop_name", "ym"], how="left").merge(p_cmp, on=["crop_name", "ym"], how="left")
    p_valued["modal_price"] = p_valued["modal_price"].fillna(p_valued["crop_modal_price"])
    prev_revenue = (p_valued["arrival_quantity_qtl"] * p_valued["modal_price"]).sum()
    prev_arrivals = p_arr_["arrival_quantity_qtl"].sum()
    p_msp = p_price_.dropna(subset=["msp"]).copy()
    p_msp["below_msp"] = p_msp["modal_price"] < p_msp["msp"]
    prev_churn = p_msp["below_msp"].mean() if len(p_msp) else np.nan
else:
    prev_revenue = prev_arrivals = prev_churn = np.nan

prev_transit = p_trans["clean_transit_hours"].mean() if len(p_trans) else np.nan

delta_revenue = pct_delta(total_revenue, prev_revenue)
delta_arrivals = pct_delta(total_arrivals, prev_arrivals)
delta_churn = pct_delta(churn_risk_rate * 100 if pd.notna(churn_risk_rate) else np.nan, prev_churn * 100 if pd.notna(prev_churn) else np.nan)
prev_compliance = (1 - prev_churn) * 100 if pd.notna(prev_churn) else np.nan
delta_compliance = pct_delta(msp_compliance_rate * 100 if pd.notna(msp_compliance_rate) else np.nan, prev_compliance)
delta_transit = pct_delta(avg_transit, prev_transit)

# --------------------------------------------------------------------------
# HEADER
# --------------------------------------------------------------------------
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
            <span class="pill"><span class="pill-k">States</span> {len(sel_states)}</span>
            <span class="pill"><span class="pill-k">Mandis</span> {len(sel_mandis)}</span>
            <span class="pill"><span class="pill-k">Crops</span> {len(sel_crops)}</span>
            <span class="pill"><span class="pill-k">Records</span> {len(f_arr) + len(f_price):,}</span>
        </div>
       </div>""",
    unsafe_allow_html=True,
)

# KPI grid — two rows of three so each card has room to breathe
r1c1, r1c2, r1c3 = st.columns(3)
with r1c1:
    kpi_card("Est. Market Revenue", f"₹{total_revenue/1e7:,.1f} Cr", f"across {len(sel_mandis)} mandis",
              icon="💰", delta=delta_revenue, delta_good_when="up")
with r1c2:
    kpi_card("Total Arrivals", f"{total_arrivals:,.0f} Qtl", f"{f_arr['crop_name'].nunique()} crops in scope",
              icon="🚜", delta=delta_arrivals, delta_good_when="up")
with r1c3:
    kpi_card("MSP Compliance", f"{msp_compliance_rate*100:,.1f}%" if pd.notna(msp_compliance_rate) else "N/A",
              "sales at or above MSP", icon="✅", delta=delta_compliance, delta_good_when="up")

st.write("")

r2c1, r2c2, r2c3 = st.columns(3)
with r2c1:
    kpi_card("Farmer 'Churn' Risk", f"{churn_risk_rate*100:,.1f}%" if pd.notna(churn_risk_rate) else "N/A",
              "sales priced below MSP", kind="risk", icon="⚠️", delta=delta_churn, delta_good_when="down")
with r2c2:
    kpi_card("Avg Transit Time", f"{avg_transit:,.1f} hrs" if pd.notna(avg_transit) else "N/A",
              f"~{avg_distance:,.0f} km average trip", kind="gold", icon="🚚", delta=delta_transit, delta_good_when="down")
with r2c3:
    kpi_card("Weather Risk Index", f"{weather_risk_index:,.0f} / 100" if pd.notna(weather_risk_index) else "N/A",
              "heat + heavy-rain exposure", kind="risk", icon="🌦️")

st.write("")

# --------------------------------------------------------------------------
# COMPOSITE MANDI RISK SCORE  (used by the Overview tab and the Agent)
# --------------------------------------------------------------------------
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
    if s.max() == s.min():
        return s * 0
    return (s - s.min()) / (s.max() - s.min())


risk_df["score"] = (
    _norm(risk_df["price_risk"].fillna(risk_df["price_risk"].median())) * (w_price / w_total)
    + _norm(risk_df["volatility"].fillna(risk_df["volatility"].median())) * (w_vol / w_total)
    + _norm(risk_df["transit_hrs"].fillna(risk_df["transit_hrs"].median())) * (w_log / w_total)
) * 100
risk_df = risk_df.merge(master[["mandi_id", "mandi_name", "district", "state"]], left_index=True, right_on="mandi_id")
risk_df = risk_df.sort_values("score", ascending=False)

# --------------------------------------------------------------------------
# AGENT CONTEXT — the agent only ever sees the filtered view
# --------------------------------------------------------------------------
agent_ctx = AgentContext(
    price=f_price, arrivals=f_arr, transport=f_trans, weather=w_in_range,
    valued=valued, risk=risk_df, master=master,
    metrics=dict(
        total_revenue=total_revenue, total_arrivals=total_arrivals,
        churn_rate=churn_risk_rate, avg_transit=avg_transit,
        start=f"{start_date:%d %b %Y}", end=f"{end_date:%d %b %Y}",
    ),
)

# --------------------------------------------------------------------------
# TABS
# --------------------------------------------------------------------------
tab_story, tab_agent, tab_price, tab_supply, tab_logistics, tab_weather, tab_quality = st.tabs(
    ["Overview & Risk", "🤖 AI Agent", "Price & MSP", "Arrivals & Supply", "Logistics", "Weather", "Data Quality"]
)

# ==========================================================================
# TAB 1 — STORYTELLING & COMPOSITE RISK
# ==========================================================================
with tab_story:
    st.markdown(
        f"""
        <div class="story-box">
        <b>The business problem:</b> farmers bring produce to mandis expecting at least
        the Minimum Support Price (MSP). In the current selection,
        <b>{churn_risk_rate*100:,.1f}%</b> of recorded sales cleared <i>below</i> MSP —
        that's the farmer-side "churn" risk: the share of transactions where a farmer
        effectively lost guaranteed value. Below, that price risk is combined with
        price volatility and logistics delay into one <b>Mandi Risk Score</b>, so it's
        clear <i>which mandis</i> are driving the problem rather than just that it exists.
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([1.3, 1])
    with c1:
        section_head("📊", "Riskiest mandis", "weighted composite score")
        top_risk = risk_df.head(12).sort_values("score")
        fig = px.bar(
            top_risk, x="score", y="mandi_name", orientation="h",
            color="score", color_continuous_scale=RISK_RAMP,
            labels={"score": "Risk score (0-100)", "mandi_name": ""},
        )
        fig.update_layout(coloraxis_showscale=False, **CHART_TEMPLATE, height=420)
        st.plotly_chart(fig, width='stretch')
    with c2:
        section_head("🎯", "Mandi drill-down", "vs. network average")
        pick = st.selectbox("Inspect a mandi", risk_df["mandi_name"].tolist(), label_visibility="collapsed")
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
            polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
            showlegend=True, height=340, paper_bgcolor=CARD,
            font=CHART_TEMPLATE["font"], margin=CHART_TEMPLATE["margin"],
        )
        st.plotly_chart(radar, width='stretch')
        badge = risk_badge(row["score"])
        st.markdown(f"**{pick}** — {row['district']}, {row['state']} &nbsp; {badge} &nbsp; ({row['score']:,.0f}/100)", unsafe_allow_html=True)

    # ---- risk leaderboard table (riskiest 5 vs safest 5, side by side) ----
    section_head("🏆", "Risk leaderboard", "riskiest vs. safest mandis in scope")
    lb1, lb2 = st.columns(2)
    with lb1:
        st.caption("⚠️ Highest risk")
        worst = risk_df.head(5)[["mandi_name", "district", "score"]].copy()
        worst["Risk"] = worst["score"].apply(risk_badge)
        worst = worst.rename(columns={"mandi_name": "Mandi", "district": "District", "score": "Score"})
        worst["Score"] = worst["Score"].round(0).astype(int)
        st.write(worst.to_html(escape=False, index=False), unsafe_allow_html=True)
    with lb2:
        st.caption("✅ Lowest risk")
        best = risk_df.tail(5).sort_values("score")[["mandi_name", "district", "score"]].copy()
        best["Risk"] = best["score"].apply(risk_badge)
        best = best.rename(columns={"mandi_name": "Mandi", "district": "District", "score": "Score"})
        best["Score"] = best["Score"].round(0).astype(int)
        st.write(best.to_html(escape=False, index=False), unsafe_allow_html=True)

    # ---- simple 2-month forward revenue signal (innovative extra) ----
    section_head("📈", "Revenue trend & short-term signal", "")
    monthly_rev = valued.groupby("ym")["market_value"].sum().reset_index()
    monthly_rev["ym_ts"] = monthly_rev["ym"].dt.to_timestamp()
    if len(monthly_rev) >= 3:
        x = np.arange(len(monthly_rev))
        coeffs = np.polyfit(x, monthly_rev["market_value"], 1)
        future_x = np.arange(len(monthly_rev), len(monthly_rev) + 2)
        future_vals = np.polyval(coeffs, future_x)
        future_dates = pd.date_range(monthly_rev["ym_ts"].iloc[-1] + pd.offsets.MonthBegin(1), periods=2, freq="MS")
        trend_fig = go.Figure()
        trend_fig.add_trace(go.Bar(x=monthly_rev["ym_ts"], y=monthly_rev["market_value"], name="Actual", marker_color=PRIMARY))
        trend_fig.add_trace(go.Bar(x=future_dates, y=future_vals, name="Projected (linear trend)", marker_color=SECONDARY, opacity=0.6))
        trend_fig.update_layout(**CHART_TEMPLATE, height=340, yaxis_title="₹ market value")
        st.plotly_chart(trend_fig, width='stretch')
        direction = "growing" if coeffs[0] > 0 else "softening"
        st.caption(f"Linear trend on the selected window is **{direction}** month-over-month — projection is illustrative, not a forecasting model.")
    else:
        st.info("Select a wider date range to see a trend projection.")

# ==========================================================================
# TAB — AI AGENT
# ==========================================================================
with tab_agent:
    st.markdown(
        """
        <div class="story-box">
        <b>What this agent does:</b> it re-analyses whatever the sidebar filters currently show and
        reports back what it found — ranked by urgency, each finding backed by the numbers it used and
        a recommended next step. It also answers questions about the selection by computing over the
        data rather than guessing, so every figure it quotes is real.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---------------- proactive insights ----------------
    a1, a2 = st.columns([3, 1])
    with a1:
        section_head("🧠", "Agent findings", "auto-generated from the current selection")
    with a2:
        st.write("")
        rerun_agent = st.button("↻ Re-run analysis", width="stretch")

    with st.spinner("Agent is analysing the current selection..."):
        insights = generate_insights(agent_ctx)

    if not insights:
        st.info("The agent found nothing noteworthy in this selection — try widening the filters.")
    else:
        sev_counts = {}
        for i in insights:
            sev_counts[i.severity] = sev_counts.get(i.severity, 0) + 1
        st.markdown(
            " ".join(
                f'<span class="badge badge-{"high" if s=="high" else "med" if s=="medium" else "low"}">'
                f'{n} {s}</span>'
                for s, n in sorted(sev_counts.items(), key=lambda kv: SEV_RANK.get(kv[0], 9))
            ),
            unsafe_allow_html=True,
        )
        st.write("")
        icons = {"high": "🔴", "medium": "🟠", "low": "🟢", "info": "🔵"}
        for ins in insights:
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
    section_head("💬", "Ask the data", "answers computed live from the filtered tables")

    if "agent_chat" not in st.session_state:
        st.session_state.agent_chat = []
    if "pending_q" not in st.session_state:
        st.session_state.pending_q = None

    st.caption("Suggested questions")
    qcols = st.columns(4)
    for idx, sq in enumerate(SUGGESTED_QUESTIONS):
        if qcols[idx % 4].button(sq, key=f"sq_{idx}", width="stretch"):
            st.session_state.pending_q = sq

    typed = st.chat_input("Ask about risk, MSP, revenue, arrivals, prices, logistics or weather...")
    question = typed or st.session_state.pending_q
    st.session_state.pending_q = None

    use_llm = bool(claude_key.strip())
    if use_llm:
        st.caption(f"🔗 Claude API connected — free-form questions will also be sent to `{claude_model}`.")

    if question:
        result = answer_question(question, agent_ctx)
        entry = {"q": question, "a": result["answer"], "table": result["table"], "llm": None}
        # If the rule-based router couldn't map it and a key is present, escalate to Claude.
        if use_llm and result["answer"].startswith("I couldn't map that"):
            with st.spinner("Asking Claude..."):
                entry["llm"] = ask_claude(question, agent_ctx, claude_key.strip(), claude_model.strip() or "claude-sonnet-5")
        st.session_state.agent_chat.insert(0, entry)

    if st.session_state.agent_chat:
        if st.button("Clear conversation"):
            st.session_state.agent_chat = []
            st.rerun()
        for entry in st.session_state.agent_chat[:12]:
            st.markdown(f'<div class="agent-q">❓ {entry["q"]}</div>', unsafe_allow_html=True)
            body = entry["llm"] if entry["llm"] else entry["a"]
            st.markdown(f'<div class="agent-answer">{body}</div>', unsafe_allow_html=True)
            if entry["table"] is not None and not entry["table"].empty:
                st.dataframe(entry["table"], width='stretch', hide_index=True)
    else:
        st.caption("Tap a suggested question above or type your own to get started.")


# ==========================================================================
# TAB 2 — PRICE & MSP
# ==========================================================================
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
        st.plotly_chart(fig, width='stretch')
    with right:
        section_head("📉", "MSP shortfall rate", "by crop")
        comp = msp_scope[msp_scope["mandi_id"].isin(sel_mandis)].groupby("crop_name")["below_msp"].mean().sort_values(ascending=False).reset_index()
        comp["below_msp"] *= 100
        fig2 = px.bar(comp, x="below_msp", y="crop_name", orientation="h",
                       labels={"below_msp": "% sales below MSP", "crop_name": ""},
                       color="below_msp", color_continuous_scale=RISK_RAMP)
        fig2.update_layout(coloraxis_showscale=False, **CHART_TEMPLATE, height=380)
        st.plotly_chart(fig2, width='stretch')

    section_head("📦", "Price spread", "min / modal / max vs MSP, by crop")
    box_df = f_price.melt(id_vars=["crop_name"], value_vars=["min_price", "modal_price", "max_price", "msp"],
                           var_name="metric", value_name="value")
    fig3 = px.box(box_df, x="crop_name", y="value", color="metric", points=False,
                   color_discrete_map={"min_price": "#C3CBD5", "modal_price": PRIMARY, "max_price": "#7D8597", "msp": DANGER})
    fig3.update_layout(**CHART_TEMPLATE, height=420, yaxis_title="₹ / quintal")
    st.plotly_chart(fig3, width='stretch')

# ==========================================================================
# TAB 3 — ARRIVALS & SUPPLY
# ==========================================================================
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
        st.plotly_chart(fig, width='stretch')
    with right:
        section_head("🏆", "Top mandis by volume", "")
        top_mandis = f_arr.groupby("mandi_id")["arrival_quantity_qtl"].sum().sort_values(ascending=False).head(10).reset_index()
        top_mandis = top_mandis.merge(master[["mandi_id", "mandi_name"]], on="mandi_id", how="left")
        fig2 = px.bar(top_mandis.sort_values("arrival_quantity_qtl"), x="arrival_quantity_qtl", y="mandi_name",
                       orientation="h", labels={"arrival_quantity_qtl": "Arrivals (Qtl)", "mandi_name": ""},
                       color_discrete_sequence=[PRIMARY])
        fig2.update_layout(**CHART_TEMPLATE, height=400)
        st.plotly_chart(fig2, width='stretch')

    section_head("👥", "Farmer footfall vs. average lot size", "bubble size = total volume")
    fs = f_arr.groupby("mandi_id").agg(farmers=("farmer_count", "sum"), qty=("arrival_quantity_qtl", "sum")).reset_index()
    fs = fs.merge(master[["mandi_id", "mandi_name", "state"]], on="mandi_id", how="left")
    fs["avg_lot_qtl"] = fs["qty"] / fs["farmers"].replace(0, np.nan)
    fig3 = px.scatter(fs, x="farmers", y="avg_lot_qtl", size="qty", color="state", hover_name="mandi_name",
                       labels={"farmers": "Farmers served", "avg_lot_qtl": "Avg lot size (Qtl/farmer)"},
                       title="Which mandis serve many small farmers vs. few large sellers?")
    fig3.update_layout(**CHART_TEMPLATE, height=420)
    st.plotly_chart(fig3, width='stretch')

# ==========================================================================
# TAB 4 — LOGISTICS
# ==========================================================================
with tab_logistics:
    left, right = st.columns(2)
    with left:
        section_head("⏱️", "Transit time distribution", "")
        fig = px.histogram(f_trans, x="clean_transit_hours", nbins=30, color_discrete_sequence=[PRIMARY],
                            labels={"clean_transit_hours": "Transit hours"})
        fig.update_layout(**CHART_TEMPLATE, height=380)
        st.plotly_chart(fig, width='stretch')
    with right:
        section_head("🏭", "Avg delay by warehouse", "")
        wh = f_trans.groupby("destination_warehouse").agg(
            trips=("trip_id", "count"), avg_hrs=("clean_transit_hours", "mean")
        ).reset_index().sort_values("avg_hrs", ascending=False)
        fig2 = px.bar(wh, x="destination_warehouse", y="avg_hrs", color="avg_hrs",
                       color_continuous_scale=RISK_RAMP,
                       labels={"destination_warehouse": "", "avg_hrs": "Avg transit hrs"})
        fig2.update_layout(coloraxis_showscale=False, **CHART_TEMPLATE, height=380)
        st.plotly_chart(fig2, width='stretch')

    section_head("🛣️", "Distance vs. transit time", "spot the outlier routes")
    fig3 = px.scatter(f_trans, x="distance_km", y="clean_transit_hours", color="destination_warehouse",
                       trendline="ols" if len(f_trans) > 5 else None,
                       labels={"distance_km": "Distance (km)", "clean_transit_hours": "Transit hours"})
    fig3.update_layout(**CHART_TEMPLATE, height=420)
    st.plotly_chart(fig3, width='stretch')

# ==========================================================================
# TAB 5 — WEATHER
# ==========================================================================
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
        st.plotly_chart(fig, width='stretch')
    with right:
        section_head("☔", "Rainfall vs. arrivals", "does heavy rain suppress supply?")
        arr_month = f_arr.groupby(f_arr["clean_date"].dt.to_period("M").dt.to_timestamp())["arrival_quantity_qtl"].sum().reset_index()
        arr_month.columns = ["ym", "arrivals"]
        merged_w = wt.merge(arr_month, on="ym", how="inner")
        fig2 = px.scatter(merged_w, x="avg_rain", y="arrivals", trendline="ols" if len(merged_w) > 3 else None,
                           labels={"avg_rain": "Avg monthly rainfall (mm)", "arrivals": "Arrivals (Qtl)"},
                           color_discrete_sequence=[PRIMARY])
        fig2.update_layout(**CHART_TEMPLATE, height=380)
        st.plotly_chart(fig2, width='stretch')
    st.caption("Weather sensors aren't tagged to individual mandis in the source data, so this view is network-wide, aligned by month.")

# ==========================================================================
# TAB 6 — DATA QUALITY (transparency, not a dump of charts)
# ==========================================================================
with tab_quality:
    section_head("🔍", "What the raw files actually looked like", "")
    st.write(
        "Every source file had entry errors — wrong units, swapped decimals, inconsistent "
        "mandi ID formats, dates in 4+ formats. Rows that couldn't be trusted were "
        "excluded rather than guessed at, so every KPI above is computed on the clean subset."
    )
    q = pd.DataFrame(quality_log).T
    q.columns = ["Raw rows", "Usable rows", "Dropped %"]
    st.dataframe(q, width='stretch')
    st.markdown(
        """
        - **Mandi IDs** arrived as `MANDI_001`, `MANDI-042`, `mandi_019`, `MANDI050`, and bare `'038'` — all normalized to one `MANDI_0NN` format before any join.
        - **Prices** under ₹50/quintal are decimal-entry errors (real modal prices for these six crops run ₹1,000–8,000/qtl) — set to missing rather than used.
        - **Transit hours** occasionally captured a 4-digit year (e.g. `2026`) instead of a duration — capped and dropped above 200 hours.
        - **Arrival quantity** had a small number of negative values — corrected with `abs()`.
        """
    )

    section_head("📄", "Filtered data", "for your own analysis")
    st.dataframe(valued[["clean_date", "mandi_id", "crop_name", "arrival_quantity_qtl", "modal_price", "market_value"]].sort_values("clean_date", ascending=False).head(500), width='stretch')
    st.download_button(
        "⬇ Download filtered arrivals + valuation as CSV",
        data=valued.to_csv(index=False).encode("utf-8"),
        file_name="mandi_filtered_valuation.csv",
        mime="text/csv",
    )

# --------------------------------------------------------------------------
# FOOTER
# --------------------------------------------------------------------------
st.markdown(
    f"""<div class="app-footer">
        <span>🌾 MandiPulse — built from clean_mandi_master, clean_price_and_msp, clean_mandi_arrivals,
        clean_transport_logistics &amp; clean_weather_sensors</span>
        <span>Showing {len(sel_mandis)} of {master['mandi_id'].nunique()} mandis · {start_date:%d %b %Y}–{end_date:%d %b %Y}</span>
       </div>""",
    unsafe_allow_html=True,
)
