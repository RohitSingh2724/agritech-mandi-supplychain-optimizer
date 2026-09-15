# 🌾 AgriTech Mandi-to-Market Supply Chain Optimizer & Price Discovery Platform

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://agritech-mandi-supplychain-optimizer.streamlit.app/)

An end-to-end data engineering pipeline, interactive Streamlit analytics dashboard, and proactive AI Agent built for **TransOrg AgentIQ Datathon (Track 3)**.

> **🌐 Live Interactive Dashboard**: [agritech-mandi-supplychain-optimizer.streamlit.app](https://agritech-mandi-supplychain-optimizer.streamlit.app/)  
> **⚡ 1-Click Deploy to Streamlit Cloud**: [Deploy Here](https://share.streamlit.io/deploy?repository=RohitSingh2724/agritech-mandi-supplychain-optimizer&branch=main&mainModule=app.py)  
> **Core Business Question Addressed:** *"Where is the Mandi supply chain losing value for farmers, and why?"*

---

## 🏗️ Project Architecture & Folder Structure

```text
agritech-mandi-supplychain-optimizer/
│
├── .streamlit/
│   └── config.toml            # Global Dark Theme Configuration
│
├── data/
│   ├── raw/                   # Raw Datathon CSV, JSON & Excel files
│   │   ├── track3_mandi_arrivals.csv
│   │   ├── track3_mandi_master.csv
│   │   ├── track3_price_and_msp.json
│   │   ├── track3_transport_logistics.csv
│   │   └── track3_weather_sensors.xlsx
│   │
│   └── processed/             # Cleaned & standardized CSV files
│       ├── clean_mandi_arrivals.csv
│       ├── clean_mandi_master.csv
│       ├── clean_price_and_msp.csv
│       ├── clean_transport_logistics.csv
│       └── clean_weather_sensors.csv
│
├── app.py                     # Main Streamlit Executive Dashboard Application
├── agent.py                   # AI Analyst Agent, Q&A Chatbot & Action Simulator
├── agritech_mandi.db          # Embedded SQLite Database
├── requirements.txt           # Python Project Dependencies
├── README.md                  # Project Documentation & Setup Guide
└── DATA_DICTIONARY.md         # Data Dictionary
```

---

## 🚪 Gate 1 Proof of Data Cleaning (Raw vs. Clean Row Counts)

To ensure data integrity without lazily dropping records, messy inputs were standardized (Mandi IDs, crop name variants, currency symbols, mixed units, and dates).

| Dataset | Raw Row Count | Clean Row Count | Dropped / Filtered % | Key Data Quality Transformations |
| :--- | :---: | :---: | :---: | :--- |
| **Mandi Arrivals** | `4,500` | `4,500` | `0.0%` | Standardized crop aliases (`Kanak`, `Dhaan`, `Sarson` $\rightarrow$ `Wheat`, `Rice`, `Mustard`). Converted mixed units (Tonnes, KG) to **Quintals (Qtl)**. |
| **Price & MSP** | `5,200` | `5,185` | `0.3%` | Stripped currency symbols (`₹`, `Rs.`, `INR`, commas). Filtered unit-entry errors ($< ₹50/\text{qtl}$). |
| **Mandi Master** | `62` | `58` | `6.4%` | Standardized Mandi IDs (`M001`, `MANDI-001` $\rightarrow$ `MANDI_001`). Filtered duplicate entries. |
| **Transport Logistics** | `10,000` | `9,980` | `0.2%` | Converted Miles to **Kilometers (KM)**. Fixed negative transit times using absolute values. Standardized vehicle reg numbers. |
| **Weather Sensors** | `3,600` | `3,600` | `0.0%` | Aligned UTC/IST timezones to `Asia/Kolkata`. Converted °F to °C and inches of rain to mm. |

---

## 📖 Data Dictionary Summary

Detailed descriptions are provided in [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md).

### Key Entities & Metrics:
* **Quintals (Qtl)**: Standardized unit for all crop arrival volumes ($1\text{ Tonne} = 10\text{ Qtl}$, $100\text{ KG} = 1\text{ Qtl}$).
* **Kilometers (KM)**: Standardized distance unit for logistics ($1\text{ Mile} = 1.60934\text{ KM}$).
* **Price Crash Alert**: Flagged when Wholesale Modal Price is less than the Minimum Support Price ($\text{Modal Price} < \text{MSP}$).
* **Transit Delay Rate**: Percentage of truck trips taking $> 24\text{ Hours}$ to reach destination warehouses.

---

## ⚙️ How to Setup & Run the Project Locally

### 1. Clone Repository & Install Dependencies
```bash
git clone https://github.com/RohitSingh2724/agritech-mandi-supplychain-optimizer.git
cd agritech-mandi-supplychain-optimizer
pip install -r requirements.txt
```

### 2. Launch Streamlit Dashboard
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501` to view the interactive application!

---

## 📊 Key Analytical Features & Dashboards

1. **Top Executive KPI Scorecards:** Real-time visibility into Estimated Market Revenue (`₹43,913.5 Cr`), Total Arrivals (`114,905,081 Qtl`), MSP Compliance %, Farmer 'Churn' Risk %, Avg Transit Time, and Weather Risk Index.
2. **AI Agent & Natural Language Chatbot:** Interactive Q&A chatbot (`st.expander`), top priority findings, and optional Claude LLM API integration.
3. **⚡ Executive Action Simulator & ROI Calculator:** Interactive scenario modeler to simulate Government MSP Procurement Desk interventions, Logistics Route Optimization, and Mobile Cold Storage deployment.
4. **Price & MSP Analytics:** Trendlines of Modal Prices vs. MSP thresholds across Wheat, Rice, Mustard, Cotton, and Maize.
5. **Logistics Bottleneck Analysis:** Transit time distribution histograms, warehouse delay rankings, and distance-vs-time scatter plots.
6. **Weather & Environmental Correlation:** Dual-axis charts linking rainfall and temperature exposure to mandi arrival drops.
