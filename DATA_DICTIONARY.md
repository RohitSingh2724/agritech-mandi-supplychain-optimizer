# 📖 Data Dictionary — AgriTech Mandi-to-Market Supply Chain Optimizer

This document provides complete field-level definitions, data types, standard units, and description for all 5 cleaned datasets used in the platform.

---

## 1. Mandi Arrivals (`clean_mandi_arrivals.csv`)

| Column Name | Data Type | Units / Format | Description |
| :--- | :--- | :--- | :--- |
| `mandi_id` | String | `MANDI_XXX` | Canonical unique identifier for the local mandi facility. |
| `crop_name` | String | Categorical | Standardized English crop name (`Wheat`, `Rice`, `Mustard`, `Sugarcane`, `Cotton`, `Maize`). |
| `arrival_quantity_qtl` | Float | **Quintals (Qtl)** | Total crop arrival volume standardized into Quintals ($1\text{ Tonne} = 10\text{ Qtl}$, $100\text{ KG} = 1\text{ Qtl}$). |
| `clean_date` | Date | `YYYY-MM-DD` | Date of crop arrival aligned to `Asia/Kolkata` (IST) timezone. |
| `farmer_count` | Integer | Count | Number of individual farmers submitting crop lots on that date. |
| `state` | String | Categorical | Indian State where the mandi is located (`Punjab`, `Haryana`, `Uttar Pradesh`). |
| `district` | String | Categorical | District jurisdiction of the mandi facility. |
| `mandi_type` | String | Categorical | Classification of the market (`APMC`, `Private`, `Direct`). |

---

## 2. Price and MSP (`clean_price_and_msp.csv`)

| Column Name | Data Type | Units / Format | Description |
| :--- | :--- | :--- | :--- |
| `mandi_id` | String | `MANDI_XXX` | Unique Mandi facility key. |
| `crop_name` | String | Categorical | Standardized crop name. |
| `modal_price` | Float | **₹ / Quintal** | Prevailing wholesale modal price per quintal. Currency symbols stripped. |
| `msp` | Float | **₹ / Quintal** | Government Minimum Support Price benchmark for the crop. |
| `min_price` | Float | **₹ / Quintal** | Minimum recorded trading price for the day. |
| `max_price` | Float | **₹ / Quintal** | Maximum recorded trading price for the day. |
| `clean_date` | Date | `YYYY-MM-DD` | Price record date (IST timezone). |

---

## 3. Transport Logistics (`clean_transport_logistics.csv`)

| Column Name | Data Type | Units / Format | Description |
| :--- | :--- | :--- | :--- |
| `mandi_id` | String | `MANDI_XXX` | Origin Mandi facility identifier. |
| `destination_warehouse` | String | Categorical | Target receiving warehouse (`WH-North`, `WH-Central`, `WH-South`, `WH-East`, `WH-West`, `Export-Terminal`). |
| `distance_km` | Float | **Kilometers (KM)** | Route distance converted from miles ($1\text{ Mile} = 1.60934\text{ KM}$). |
| `clean_transit_hours` | Float | **Hours** | Trip duration in hours. Negative values fixed to positive absolute values. |
| `clean_vehicle_number` | String | `XX-00-XX-0000` | Standardized 10-character Indian vehicle registration number (e.g. `PB-01-AB-1234`). |
| `clean_dispatch_date` | Date | `YYYY-MM-DD` | Truck dispatch date (IST timezone). |

---

## 4. Weather Sensors (`clean_weather_sensors.csv`)

| Column Name | Data Type | Units / Format | Description |
| :--- | :--- | :--- | :--- |
| `clean_date` | Date | `YYYY-MM-DD` | Weather sensor reading date in IST timezone. |
| `temperature_celsius` | Float | **°Celsius** | Ambient temperature converted from Fahrenheit where applicable ($\text{°C} = (\text{°F} - 32) \times 5/9$). |
| `rainfall_mm` | Float | **Millimeters (mm)** | Precipitation level converted from inches ($1\text{ inch} = 25.4\text{ mm}$). |
| `humidity_pct` | Float | **% Percentage** | Relative humidity level recorded by IoT sensor. |

---

## 5. Mandi Master (`clean_mandi_master.csv`)

| Column Name | Data Type | Units / Format | Description |
| :--- | :--- | :--- | :--- |
| `mandi_id` | String | `MANDI_XXX` | Master Mandi identifier key. |
| `mandi_name` | String | Name | Human-readable name of the Mandi market facility. |
| `district` | String | Categorical | District name. |
| `state` | String | Categorical | Indian State name. |
| `mandi_type` | String | Categorical | Market management type (`APMC`, `Private`, `Direct`). |
| `total_area_acres` | Float | Acres | Facility land size in acres. |
