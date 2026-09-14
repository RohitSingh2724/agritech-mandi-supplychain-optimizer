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
st.markdown("##### *Supply Chain Analytics, Geospatial Discovery, Weather IoT & Logistics Efficiency Platform*")
st.markdown("---")

# ---------------------------------------------------------
# NUMBER FORMATTING HELPER (M & K)
# ---------------------------------------------------------
def format_num(val, suffix=""):
    if pd.isna(val) or val is None:
        return "0"
    num = float(val)
    if abs(num) >= 1_000_000:
        return f"{num / 1_000_000:.2f}M {suffix}".strip()
    elif abs(num) >= 1_000:
        return f"{num / 1_000:.2f}K {suffix}".strip()
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

# Latitude & Longitude mapping for Indian Districts
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

# Filter Datasets
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
col1, col2, col3, col4, col5 = st.columns(5)

total_arrivals = df_arr_filtered["arrival_quantity_qtl"].sum()

modal_col = [c for c in df_prc_filtered.columns if 'modal' in c.lower()][0]
msp_col = [c for c in df_prc_filtered.columns if 'msp' in c.lower()][0]

price_crashes = len(df_prc_filtered[(df_prc_filtered[modal_col].notnull()) & 
                                    (df_prc_filtered[msp_col].notnull()) & 
                                    (df_prc_filtered[modal_col] < df_prc_filtered[msp_col])])

avg_delay_rate = (len(df_transport[df_transport["clean_transit_hours"] > 24]) / len(df_transport) * 100) if len(df_transport) > 0 else 0
avg_transit_h = df_transport["clean_transit_hours"].mean()

rain_col = [c for c in df_weather.columns if 'rain' in c.lower()][0]
avg_rain = df_weather[rain_col].mean() if rain_col in df_weather.columns else 0.0

with col1:
    st.metric("📦 Total Arrival Volume", format_num(total_arrivals, "Qtl"))

with col2:
    st.metric("🚨 Price Crash Alerts", format_num(price_crashes, "Incidents"))

with col3:
    st.metric("🚚 Transit Delay Rate", f"{avg_delay_rate:.2f}%")

with col4:
    st.metric("⏱️ Avg Transit Time", f"{avg_transit_h:.1f} Hours")

with col5:
    st.metric("🌧️ Avg Rainfall Level", f"{avg_rain:.2f} mm")

st.markdown("---")

# ---------------------------------------------------------
# INTERACTIVE DASHBOARD TABS
# ---------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Arrival Trends & Volume Share",
    "💰 Price Crashes (Price vs. MSP)",
    "🗺️ Mandi Network Map",
    "🚚 Logistics & Fleet Efficiency",
    "🌧️ Weather Impact & Heatmap"
])

# TAB 1: ARRIVAL TRENDS & PIE CHART VOLUME SHARE
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
            labels={"period": "Timeline", "arrival_quantity_qtl": "Arrival Volume (Qtl)", "crop_name": "Crop"},
            title=f"Crop Arrival Volume Over Time ({time_granularity} View)"
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    st.markdown("---")
    col_c1, col_c2 = st.columns(2)
    
    crop_summary = df_arr_filtered.groupby("crop_name")["arrival_quantity_qtl"].sum().reset_index().sort_values(by="arrival_quantity_qtl", ascending=True)
    
    with col_c1:
        st.subheader("1. Horizontal Volume Ranking")
        fig_bar = px.bar(
            crop_summary, 
            y="crop_name", 
            x="arrival_quantity_qtl", 
            orientation="h",
            color="crop_name",
            labels={"crop_name": "Crop Variety", "arrival_quantity_qtl": "Volume (Quintals)"},
            title="Total Arrival Volume Ranking"
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with col_c2:
        st.subheader("2. Crop Variety Volume Share (Donut Chart)")
        fig_donut = px.pie(
            crop_summary, 
            values="arrival_quantity_qtl", 
            names="crop_name", 
            hole=0.5,  # Creates the hollow center for a Donut Chart
            title="Percentage Volume Share by Crop Variety"
    )
    st.plotly_chart(fig_donut, use_container_width=True)

# TAB 2: PRICE CRASHES (PRICE VS MSP)
with tab2:
    st.subheader("Modal Price vs. Minimum Support Price (MSP)")
    
    crashes_df = df_prc_filtered[(df_prc_filtered[modal_col].notnull()) & 
                                 (df_prc_filtered[msp_col].notnull()) & 
                                 (df_prc_filtered[modal_col] < df_prc_filtered[msp_col])].copy()
    crashes_df["price_deficit"] = crashes_df[msp_col] - crashes_df[modal_col]
    
    if 'clean_date' in df_prc_filtered.columns:
        price_trend = df_prc_filtered.groupby('clean_date')[[modal_col, msp_col]].mean().reset_index()
        fig_price = go.Figure()
        fig_price.add_trace(go.Scatter(x=price_trend['clean_date'], y=price_trend[modal_col], mode='lines', name='Wholesale Modal Price'))
        fig_price.add_trace(go.Scatter(x=price_trend['clean_date'], y=price_trend[msp_col], mode='lines', name='MSP Benchmark', line=dict(dash='dash', color='red')))
        fig_price.update_layout(title="Multi-Line Timeline: Modal Price vs MSP Benchmark (Crashes Below Red Line)", xaxis_title="Date", yaxis_title="Price (₹ / Qtl)")
        st.plotly_chart(fig_price, use_container_width=True)

    st.markdown("---")
    st.subheader("Top Price Crash Deficit Instances")
    st.dataframe(
        crashes_df[["crop_name", "clean_date", modal_col, msp_col, "price_deficit"]].sort_values(by="price_deficit", ascending=False).head(50),
        use_container_width=True
    )

# TAB 3: GEOSPATIAL MAP
with tab3:
    st.subheader("Geospatial Mandi Network Map (Punjab, Haryana, UP)")
    
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
            title="Interactive Mandi Bubble Map (Bubble Size = Arrival Volume)"
        )
        st.plotly_chart(fig_map, use_container_width=True)

# TAB 4: LOGISTICS & FLEET EFFICIENCY
with tab4:
    col_l1, col_l2 = st.columns(2)
    
    with col_l1:
        st.subheader("1. Warehouse Route Delay Ranking")
        wh_col = [c for c in df_transport.columns if 'ware' in c.lower() or 'dest' in c.lower() or 'wh' in c.lower()][0]
        wh_summary = df_transport.groupby(wh_col).agg(
            total_trips=("clean_transit_hours", "count"),
            avg_transit_hours=("clean_transit_hours", "mean")
        ).reset_index().sort_values(by="avg_transit_hours", ascending=True)
        
        fig_wh = px.bar(
            wh_summary, 
            y=wh_col, 
            x="avg_transit_hours", 
            orientation="h",
            color="avg_transit_hours",
            title="Average Transit Hours by Destination Warehouse"
        )
        st.plotly_chart(fig_wh, use_container_width=True)

    with col_l2:
        st.subheader("2. Distance (KM) vs. Transit Time Efficiency")
        if "distance_km" in df_transport.columns:
            fig_eff = px.scatter(
                df_transport, 
                x="distance_km", 
                y="clean_transit_hours",
                trendline="ols",
                color="destination_warehouse",
                title="Trip Efficiency Scatter Plot (Points above line indicate Delays)"
            )
            st.plotly_chart(fig_eff, use_container_width=True)

# TAB 5: WEATHER SENSOR IMPACT & HEATMAP
with tab5:
    col_w1, col_w2 = st.columns(2)
    
    with col_w1:
        st.subheader("1. Rainfall vs. Arrival Volume Correlation")
        if 'clean_date' in df_arrivals.columns and 'clean_date' in df_weather.columns:
            daily_arr = df_arrivals.groupby('clean_date')['arrival_quantity_qtl'].sum().reset_index()
            daily_wth = df_weather.groupby('clean_date')[rain_col].mean().reset_index()
            weather_arr = pd.merge(daily_arr, daily_wth, on='clean_date')
            
            fig_weather = px.scatter(
                weather_arr, 
                x=rain_col, 
                y="arrival_quantity_qtl",
                trendline="ols",
                labels={rain_col: "Rainfall (mm)", "arrival_quantity_qtl": "Daily Arrival Volume (Qtl)"},
                title="Rainfall (mm) vs Arrival Volumes"
            )
            st.plotly_chart(fig_weather, use_container_width=True)

    with col_w2:
        st.subheader("2. Weather & Metrics Correlation Heatmap")
        if 'clean_date' in df_arrivals.columns and 'clean_date' in df_weather.columns:
            merged_metrics = pd.merge(daily_arr, df_weather, on='clean_date', how='inner')
            corr_mat = merged_metrics.select_dtypes(include=['float64', 'int64']).corr()
            
            fig_heat = px.imshow(
                corr_mat, 
                text_auto=".2f",
                color_continuous_scale="Viridis",
                title="Cross-Metric Correlation Heatmap"
            )
            st.plotly_chart(fig_heat, use_container_width=True)