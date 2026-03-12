# 🗺️ Geospatial Mapping Tool

This project is an interactive geospatial visualization application built with **Streamlit** and **Folium**.  
It displays the boundaries of selected London boroughs and allows users to explore them interactively on a map.

## Features

- Visualizes borough boundaries using **GeoJSON data**
- Supports viewing **a single borough or all boroughs together**
- Displays **borough centre markers**
- Displays **air quality monitoring stations** as markers on the map
- Toggle to show or hide monitoring stations
- Displays **London air pollution context** with key hotspots and project relevance
- Stations table showing **station name** and **site type**
- Displays **air quality measurements** in a table below the map
- Toggle to show or hide measurements table
- Interactive map controls through a **Streamlit sidebar**
- Adjustable **zoom level**
- Multiple map styles (OpenStreetMap, CartoDB Positron, CartoDB Dark Matter)
- Multi-page navigation with sidebar for geospatial map and analysis pages

## Installation

Clone the repository and install the required Python libraries:

```bash
pip install -r requirements.txt
```

## Run

Run the application with:

```bash
streamlit run src/visualisation/geospatial_mapping.py
```

## Data Collection

Air quality data is collected from the LondonAir (LAQN) API.

Script used:

```bash
src/processing/fetch_air_quality_data.py
```

The script:

- retrieves monitoring site metadata
- retrieves pollutant species information
- fetches pollutant measurements
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

The workflow of the project is:

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
Streamlit + Folium visualisation
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

The polygon boundary data used to visualise the London boroughs in this project was obtained from **MapIt by mySociety**, a service that provides geographic boundary data for UK administrative areas.

Source:

```bash
https://mapit.mysociety.org/area/2493.html
```

The boundary polygons for the following boroughs were extracted and stored as GeoJSON files in the project:

```bash
data/geo/camden.json
data/geo/greenwich.json
data/geo/tower_hamlets.json
```

These GeoJSON files contain the geographic coordinates that define the administrative boundaries of each borough.  
The polygons are used by the application to render borough shapes on the interactive map using **Folium**.