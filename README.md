# 🗺️ London Air Quality Analysis

An interactive multi-page air quality analysis application built with **Streamlit**, **Folium**, and **Altair**.  
It displays borough boundaries, monitoring stations, and pollution data across Camden, Greenwich, and Tower Hamlets.

## Features

### 🗺️ Geospatial Map
- Visualizes borough boundaries using **GeoJSON data**
- Supports viewing a single borough or all boroughs together
- Displays borough centre markers, labels, and polygon fill
- Displays air quality monitoring stations as markers on the map
- Multiple map styles (OpenStreetMap, CartoDB Positron, CartoDB Dark Matter)
- Adjustable zoom level
- Sidebar toggles for stations, pollutants, and measurements tables
- Collapsible **ℹ️ About** descriptions below each table
- London air pollution context with key hotspots and project relevance

### 📈 Time Series
- Hourly pollutant concentrations per station over the full dataset period
- Rush hour bands annotated (07:00–09:00 and 17:00–19:00)
- WHO guideline threshold line with label
- Pollutant selector for NO₂, PM2.5, and PM10
- Borough filter and peak readings summary table

### 🔥 Heatmap
- Matrix of average pollutant concentration by station and hour of day
- Split into separate heatmaps per day
- Pollutant selector for NO₂, PM2.5, and PM10
- Borough filter and average summary table

### 🗺️ Choropleth
- Borough shading based on four view modes:
  - 🏔️ Peak reading — highest recorded concentration per borough
  - 🕐 Most polluted hour — hour of day with highest average per borough
  - 📅 Day-by-day — date slider to step through daily averages
  - 📊 vs London average — deviation from overall average across all boroughs
- All six pollutants selectable (NO₂, PM2.5, PM10, O₃, SO₂, CO)
- WHO threshold status shown in summary tables

### 📦 Box Plot
- Distribution of hourly readings per station, colour-coded by borough
- Top 3 pollutants with most data dynamically selected
- IQR box, min-max whisker, and median line per station
- WHO threshold line with label
- Full station statistics table with WHO exceedance flag

### 📉 Missing Data Analysis
- Impact on analysis section at the top explaining how gaps affect every other page
- Four visualisations:
  - 🟥 Heatmap grid — % missing per station and hour of day
  - 📊 Bar chart — stations ranked by % missing, colour-coded by borough
  - 📅 Timeline — % missing per station and day
  - 📋 Summary table — total, missing, and present counts per station
- Status flag per station: ✅ Good (<5%), ⚡ Moderate (5–20%), ⚠️ High (>20%)
- All six pollutants available

## Installation

Clone the repository and install the required Python libraries:
```bash
pip install -r requirements.txt
```

## Run

Run the application with:
```bash
streamlit run streamlit_app.py
```

## App Structure

`app.py` is organised into the following functions:

- `run_pipeline()` — fetches and processes data sequentially with progress spinners
- `data_is_ready()` — checks whether processed CSV files exist
- `clear_data()` — deletes raw and processed files to force a fresh pipeline run
- `load_measurements()` — loads `measurements.csv` into a DataFrame
- `load_stations()` — loads `stations.csv` into a DataFrame
- `render_sidebar()` — renders navigation and data management controls, returns selected page
- `render_page()` — routes to the correct page renderer based on sidebar selection
- `main()` — entry point, runs pipeline if data is missing then renders the app

On first launch, if processed data is not found, the pipeline runs automatically.
Use the **🔄 Refresh data** button in the sidebar to re-fetch and reprocess at any time.

## Data Collection

Air quality data is collected from the LondonAir (LAQN) API.

Script used:
```bash
src/processing/fetch_air_quality_data.py
```

The script:

- retrieves monitoring site metadata
- retrieves pollutant species information
- fetches pollutant measurements for 23–26 Feb 2026
- filters results for the following boroughs:
  - Camden
  - Greenwich
  - Tower Hamlets

The raw dataset is stored in:
```bash
data/raw/air_quality_3_days.json
```

## Data Processing

The raw JSON dataset is transformed into structured datasets for analysis and visualisation.

Script used:
```bash
src/processing/process_air_quality_data.py
```

This script generates two datasets.

### Stations dataset
```bash
data/processed/stations.csv
```

Contains:

- borough
- station name
- station code
- site type
- latitude
- longitude

### Measurements dataset
```bash
data/processed/measurements.csv
```

Contains:

- borough
- station name
- station code
- pollutant code
- pollutant name
- measurement date
- value

## Data Pipeline Overview
```
LondonAir API
      ↓
fetch_air_quality_data.py
      ↓
data/raw/air_quality_3_days.json
      ↓
process_air_quality_data.py
      ↓
data/processed/stations.csv
data/processed/measurements.csv
      ↓
Streamlit + Folium + Altair visualisation
```

## Project Structure
```
london-air-quality-analysis/
│
├── README.md
├── CHANGELOG.md
├── requirements.txt
├── .gitignore
├── app.py
│
├── data/
│   ├── raw/
│   │   └── air_quality_3_days.json
│   │
│   ├── processed/
│   │   ├── stations.csv
│   │   └── measurements.csv
│   │
│   └── geo/
│       ├── camden.json
│       ├── greenwich.json
│       └── tower_hamlets.json
│
├── src/
│   ├── __init__.py
│   ├── processing/
│   │   ├── fetch_air_quality_data.py
│   │   └── process_air_quality_data.py
│   │
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── time_series.py
│   │   ├── heatmap.py
│   │   ├── choropleth.py
│   │   ├── box_plot.py
│   │   └── missing_data.py
│   │
│   └── visualization/
│       ├── __init__.py
│       └── geospatial_mapping.py
│
├── notebooks/
│   └── exploratory_analysis.ipynb
│
├── docs/
│   └── project_plan.md
│
└── tests/
    └── test_data_pipeline.py
```

## Data Source

Air quality data is retrieved from the LondonAir / LAQN API:
```bash
https://api.erg.ic.ac.uk/AirQuality
```

The dataset contains monitoring station measurements for:

- Camden
- Greenwich
- Tower Hamlets

## Borough Boundary Data

The polygon boundary data was obtained from **MapIt by mySociety**.

Source:
```bash
https://mapit.mysociety.org/area/2493.html
```

Boundary polygons stored as GeoJSON files:
```bash
data/geo/camden.json
data/geo/greenwich.json
data/geo/tower_hamlets.json
```

These files contain the geographic coordinates used to render borough shapes on the interactive map using **Folium**.