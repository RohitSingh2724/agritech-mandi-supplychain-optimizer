import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------------
# PAGE CONFIGURATION & THEME
# ---------------------------------------------------------
st.set_page_config(
    page_title="AgriTech Mandi Optimizer",
    page_icon="🌾",
    layout="wide"
)

st.title("🌾 AgriTech Mandi-to-Market Supply Chain Optimizer")
st.markdown("##### *Comprehensive Supply Chain Analytics, Geospatial Map & Multi-Granularity Time Series Platform*")
st.markdown("---")

# ---------------------------------------------------------
# NUMBER FORMATTING HELPER (Millions & Thousands)
# ---------------------------------------------------------
def format_num(val, suffix=""):
    if pd.isna(val) or val is None:
        return "0"
    num = float(val)
    if abs(num) >= 1_000_000:
        return f"{num / 1_000_000:.2f} M {suffix}".strip()
    elif abs(num) >= 1_000:
        return f"{num / 1_000:.2f} K {suffix}".strip()
    else:
        return f"{num:,.2f} {suffix}".strip()

# ---------------------------------------------------------
# DATABASE CONNECTION & DATA LOADING
# ---------------------------------------------------------
@st.cache_resource
def get_connection():
    return sqlite3.connect("agritech_mandi.db", check_same_thread=False)

conn = get_connection()

@st.cache_data
def load_dashboard_data():
    df_arr = pd.read_sql("SELECT * FROM mandi_arrivals", conn)
    df_prc = pd.read_sql("SELECT * FROM price_and_msp", conn)
    df_trn = pd.read_sql("SELECT * FROM transport_logistics", conn)
    df_wth = pd.read_sql("SELECT * FROM weather_sensors", conn)
    df_mst = pd.read_sql("SELECT * FROM mandi_master", conn)
    return df_arr, df_prc, df_trn, df_wth, df_mst

df_arrivals, df_price, df_transport, df_weather, df_master = load_dashboard_data()

# Standardize Mandi IDs
m_col = [c for c in df_arrivals.columns if 'mandi' in c.lower()][0]
if m_col in df_master.columns:
    df_master[m_col] = df_master[m_col].astype(str).str.strip().str.upper()

# Coordinates mapping for Indian Districts
DISTRICT_COORDS = {
    'ludhiana': (30.9010, 75.8573),
    'amritsar': (31.6340, 74.8723),
    'patiala': (30.3398, 76.3869),
    'jalandhar': (31.3260, 75.5762),
    'bathinda': (30.2110, 74.9455),
    'moga': (30.8230, 75.1734),
    'ferozepur': (30.9237, 74.6124),
    'ambala': (30.3782, 76.7767),
    'karnal': (29.6857, 76.9905),
    'kurukshetra': (29.9695, 76.8783),
    'hisar': (29.1492, 75.7217),
    'sirsa': (29.5321, 75.0318),
    'fatehabad': (29.5152, 75.4544),
    'agra': (27.1767, 78.0081),
    'bareilly': (28.3670, 79.4304),
    'saharanpur': (29.9640, 77.5460),
    'muzaffarnagar': (29.4727, 77.7085),
    'meerut': (28.9845, 77.7064)
}

if "district" in df_master.columns:
    df_master["clean_district"] = df_master["district"].astype(str).str.strip().str.lower()
    df_master["lat"] = df_master["clean_district"].map(lambda d: DISTRICT_COORDS.get(d, (30.2, 75.8))[0])
    df_master["lon"] = df_master["clean_district"].map(lambda d: DISTRICT_COORDS.get(d, (30.2, 75.8))[1])

df_master["mandi_label"] = df_master.apply(
    lambda r: f"{r.get('mandi_name', 'Mandi')} ({r.get('district', 'District')}, {r.get('state', 'State')})", axis=1
)

mandi_label_dict = dict(zip(df_master[m_col], df_master["mandi_label"]))
df_arrivals["mandi_display"] = df_arrivals[m_col].map(mandi_label_dict).fillna(df_arrivals[m_col])
df_price["mandi_display"] = df_price[m_col].map(mandi_label_dict).fillna(df_price[m_col])

# ---------------------------------------------------------
# SIDEBAR FILTERS
# ---------------------------------------------------------
st.sidebar.header("🔍 Interactive Filters")

crops_list = ["All Crops"] + sorted([c for c in df_arrivals["crop_name"].dropna().unique() if c != "Unknown"])
selected_crop = st.sidebar.selectbox("Filter by Crop Type", crops_list)

mandis_list = ["All Mandis"] + sorted(list(set(df_arrivals["mandi_display"].dropna())))
selected_mandi_label = st.sidebar.selectbox("Filter by Mandi (Market)", mandis_list)

time_granularity = st.sidebar.radio("Time Granularity View", ["Daily", "Weekly", "Monthly"])

# Filter Data
df_arr_filtered = df_arrivals.copy()
df_prc_filtered = df_price.copy()

if selected_crop != "All Crops":
    df_arr_filtered = df_arr_filtered[df_arr_filtered["crop_name"] == selected_crop]
    df_prc_filtered = df_prc_filtered[df_prc_filtered["crop_name"] == selected_crop]

if selected_mandi_label != "All Mandis":
    df_arr_filtered = df_arr_filtered[df_arr_filtered["mandi_display"] == selected_mandi_label]
    df_prc_filtered = df_prc_filtered[df_prc_filtered["mandi_display"] == selected_mandi_label]

st.sidebar.markdown("---")
st.sidebar.download_button(
    label="📥 Download Clean Data CSV",
    data=df_arr_filtered.to_csv(index=False).encode('utf-8'),
    file_name="mandi_arrivals_analytics.csv",
    mime="text/csv"
)

# ---------------------------------------------------------
# TOP KPI CARDS
# ---------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

total_arrivals = df_arr_filtered["arrival_quantity_qtl"].sum()

modal_col = [c for c in df_prc_filtered.columns if 'modal' in c.lower()][0]
msp_col = [c for c in df_prc_filtered.columns if 'msp' in c.lower()][0]

price_crashes = len(df_prc_filtered[(df_prc_filtered[modal_col].notnull()) & 
                                    (df_prc_filtered[msp_col].notnull()) & 
                                    (df_prc_filtered[modal_col] < df_prc_filtered[msp_col])])

avg_delay_rate = (len(df_transport[df_transport["clean_transit_hours"] > 24]) / len(df_transport) * 100) if len(df_transport) > 0 else 0
avg_transit_h = df_transport["clean_transit_hours"].mean()

with col1:
    st.metric("📦 Total Arrival Volume", format_num(total_arrivals, "Qtl"))

with col2:
    st.metric("🚨 Price Crash Alerts (Price < MSP)", format_num(price_crashes, "Incidents"))

with col3:
    st.metric("🚚 Transit Delay Rate (>24h)", f"{avg_delay_rate:.2f}%")

with col4:
    st.metric("⏱️ Avg Transit Time", f"{avg_transit_h:.1f} Hours")

st.markdown("---")

# ---------------------------------------------------------
# DASHBOARD TABS
# ---------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Arrival Trends",
    "🗺️ Interactive Mandi Map",
    "💰 Price Crash Analysis",
    "🚚 Warehouse Logistics",
    "🌧️ Weather Sensor Impact"
])

# TAB 1: ARRIVAL TRENDS (DAILY / WEEKLY / MONTHLY)
with tab1:
    st.subheader(f"Crop Arrival Trends ({time_granularity} View)")
    
    if "clean_date" in df_arr_filtered.columns:
        df_arr_time = df_arr_filtered.copy()
        df_arr_time["datetime"] = pd.to_datetime(df_arr_time["clean_date"])
        
        if time_granularity == "Weekly":
            df_arr_time["period"] = df_arr_time["datetime"].dt.to_period("W").dt.start_time
        elif time_granularity == "Monthly":
            df_arr_time["period"] = df_arr_time["datetime"].dt.to_period("M").dt.start_time
        else:
            df_arr_time["period"] = df_arr_time["datetime"]
            
        time_summary = df_arr_time.groupby(["period", "crop_name"])["arrival_quantity_qtl"].sum().reset_index()
        
        fig_trend = px.line(
            time_summary, 
            x="period", 
            y="arrival_quantity_qtl", 
            color="crop_name",
            labels={"period": "Timeline", "arrival_quantity_qtl": "Arrival Volume (Quintals)", "crop_name": "Crop"},
            title=f"Crop Arrival Volume Over Time ({time_granularity} View)"
        )
        st.plotly_chart(fig_trend, use_container_width=True)

# TAB 2: INTERACTIVE MAP
with tab2:
    st.subheader("Geospatial Mandi Network Map (Punjab, Haryana, Uttar Pradesh)")
    
    geo_df = pd.merge(df_arr_filtered, df_master[[m_col, "mandi_name", "district", "state", "lat", "lon"]].drop_duplicates(), on=m_col, how="left")
    geo_summary = geo_df.groupby([m_col, "mandi_name", "district", "state", "lat", "lon"])["arrival_quantity_qtl"].sum().reset_index()
    
    if not geo_summary.empty and geo_summary["lat"].notnull().any():
        fig_map = px.scatter_mapbox(
            geo_summary,
            lat="lat",
            lon="lon",
            size="arrival_quantity_qtl",
            color="district",
            hover_name="mandi_name",
            hover_data={"district": True, "state": True, "arrival_quantity_qtl": ":,.2f"},
            size_max=35,
            zoom=6,
            center={"lat": 30.2, "lon": 75.8},
            mapbox_style="open-street-map",
            title="Interactive Mandi Map (Bubble Size = Total Arrival Volume)"
        )
        st.plotly_chart(fig_map, use_container_width=True)

# TAB 3: PRICE CRASH ANALYSIS
with tab3:
    st.subheader("Wholesale Modal Price vs. Minimum Support Price (MSP)")
    
    crashes_df = df_prc_filtered[(df_prc_filtered[modal_col].notnull()) & 
                                 (df_prc_filtered[msp_col].notnull()) & 
                                 (df_prc_filtered[modal_col] < df_prc_filtered[msp_col])].copy()
    crashes_df["price_loss"] = crashes_df[msp_col] - crashes_df[modal_col]
    
    col_p1, col_p2 = st.columns([2, 1])
    with col_p1:
        fig_prc = px.scatter(
            df_prc_filtered, 
            x=modal_col, 
            y=msp_col, 
            color="crop_name",
            labels={modal_col: "Modal Price (₹)", msp_col: "MSP Benchmark (₹)"},
            title="Modal Price vs MSP Comparison"
        )
        st.plotly_chart(fig_prc, use_container_width=True)
    with col_p2:
        st.subheader("Price Crash Deficit Table")
        st.dataframe(crashes_df[["crop_name", "clean_date", modal_col, msp_col, "price_loss"]].sort_values(by="price_loss", ascending=False).head(50), use_container_width=True)

# TAB 4: LOGISTICS & WAREHOUSES
with tab4:
    st.subheader("Warehouse Route Logistics Performance")
    wh_col = [c for c in df_transport.columns if 'ware' in c.lower() or 'dest' in c.lower() or 'wh' in c.lower()][0]
    wh_summary = df_transport.groupby(wh_col).agg(
        total_trips=("clean_transit_hours", "count"),
        avg_transit_hours=("clean_transit_hours", "mean")
    ).reset_index()
    
    fig_wh = px.bar(wh_summary, x=wh_col, y="avg_transit_hours", color=wh_col, title="Average Transit Hours by Warehouse")
    st.plotly_chart(fig_wh, use_container_width=True)

# TAB 5: WEATHER SENSOR IMPACT
with tab5:
    st.subheader("Weather Sensor Impact on Crop Arrivals")
    rain_col = [c for c in df_weather.columns if 'rain' in c.lower()][0]
    if 'clean_date' in df_arrivals.columns and 'clean_date' in df_weather.columns:
        daily_arr = df_arrivals.groupby('clean_date')['arrival_quantity_qtl'].sum().reset_index()
        daily_wth = df_weather.groupby('clean_date')[rain_col].mean().reset_index()
        weather_arr = pd.merge(daily_arr, daily_wth, on='clean_date')
        
        fig_weather = px.scatter(
            weather_arr, 
            x=rain_col, 
            y="arrival_quantity_qtl",
            labels={rain_col: "Rainfall (mm)", "arrival_quantity_qtl": "Daily Arrival Volume (Qtl)"},
            trendline="ols",
            title="Correlation Between Heavy Rainfall Days and Arrival Drops"
        )
        st.plotly_chart(fig_weather, use_container_width=True)