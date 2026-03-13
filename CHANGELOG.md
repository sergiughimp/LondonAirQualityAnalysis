# Changelog

## Borough Coordinates and Map Improvements

### 1. Add the coordinates of the boroughs
- Added GeoJSON coordinate files for:
  - Camden
  - Greenwich
  - Tower Hamlets

### 2. Add interactive borough map using Streamlit and Folium
- Display Camden, Greenwich, and Tower Hamlets borough boundaries
- Add sidebar controls to view individual boroughs or all boroughs together
- Improve map styling with polygon fill, labels, and centre markers
- Fix zoom slider so map zoom level works correctly
- Set OpenStreetMap as the default map style

---

## Data Collection and Processing Pipeline

### 3. Implement air quality data collection
- Created `fetch_air_quality_data.py` to retrieve air quality data from the **LondonAir (LAQN) API**
- Implement request retry logic to handle temporary API failures
- Retrieve monitoring site metadata and pollutant species information
- Collect pollutant measurements for the following boroughs:
  - Camden
  - Greenwich
  - Tower Hamlets
- Store the raw dataset in:

  data/raw/air_quality_3_days.json

### 4. Implement data processing
- Created `process_air_quality_data.py` to transform raw JSON data into structured datasets
- Extract monitoring station metadata
- Extract pollutant measurement records
- Convert measurement values to numeric format
- Parse measurement timestamps

### 5. Generate processed datasets
- Generate two structured datasets from the raw data

**Stations dataset**

data/processed/stations.csv

Contains:
- borough
- station name
- station code
- site type
- latitude
- longitude

**Measurements dataset**

data/processed/measurements.csv

Contains:
- borough
- station name
- station code
- pollutant code
- pollutant name
- measurement date
- measurement value

---

## Monitoring Stations Map Layer

### 6. Add monitoring stations to the interactive map
- Load monitoring station data from `data/processed/stations.csv`
- Render stations as small circle markers on the interactive map
- Markers are small and semi-transparent to avoid obscuring borough boundaries
- Add sidebar toggle to show or hide monitoring stations
- Stations are added to a dedicated layer group visible in the map layer control
- Each station marker displays a tooltip with the station name and a popup with:
  - borough
  - station code
  - site type
- Add monitoring station count per borough to the Borough Summary table
- Add a filterable stations table below the map, filtered to the current borough selection

### 7. Filter stations table columns
- Stations table now displays only station name and site type
- Removed borough, station code, latitude, and longitude from the table view

### 8. Add measurements table
- Load measurement data from `data/processed/measurements.csv`
- Display measurements filtered to the current borough selection
- Table shows station name, pollutant code, pollutant name, measurement date, and value
- Add sidebar toggle to show or hide the measurements table

### 9. Add London air pollution context section
- Added 🏙️ London Air Pollution — Project Context section below the Borough Summary
- Explains why Camden, Tower Hamlets, and Greenwich were selected
- Lists key monitoring stations per borough with their pollution drivers:
  - Camden: Euston Road, Swiss Cottage, Bloomsbury
  - Tower Hamlets: Mile End Road, Blackwall, Bethnal Green
  - Greenwich: Trafalgar Road, Woolwich Flyover, Tunnel Avenue
- Highlights NO₂, PM2.5, and PM10 as the key pollutants of concern

---

## Application Restructure

### 10. Restructure app to run from app.py with sidebar navigation
- Moved `st.set_page_config` from `geospatial_mapping.py` to `app.py`
- Wrapped all geospatial mapping code inside `render_map()` function
- Added `sys.path` fix to `app.py` to resolve module imports correctly
- Added `__init__.py` to `src/` and `src/visualization/` directories
- Added multi-page sidebar navigation in `app.py` with the following pages:
  - 🗺️ Geospatial Map
  - 📈 Time Series
  - 🔥 Heatmap
  - 🗺️ Choropleth
  - 📦 Box Plot
  - 📉 Missing Data
- Fixed `BASE_DIR` in `geospatial_mapping.py` to correctly resolve project root using `parents[2]`

---

## Analysis Charts

### 11. Add hourly pollutant time series
- Created `src/analysis/time_series.py` with `render_time_series()` function
- Line chart tracking hourly pollutant concentrations per station over 48 hours
- Rush hour bands annotated for morning (07:00–09:00) and evening (17:00–19:00)
- WHO guideline threshold line with label (NO₂: 25 µg/m³, PM2.5: 15 µg/m³, PM10: 45 µg/m³)
- Pollutant selector for NO₂, PM2.5, and PM10
- Borough filter in sidebar
- Station names sorted alphabetically in legend with full label visibility
- Peak readings summary table below chart sorted alphabetically by station

### 12. Add pollution heatmap
- Created `src/analysis/heatmap.py` with `render_heatmap()` function
- Matrix visualisation of average pollutant concentration by station and hour of day
- Split into separate heatmaps per day for accurate temporal comparison
- Pollutant selector for NO₂, PM2.5, and PM10
- Borough filter in sidebar
- Station names sorted alphabetically on y-axis with full label visibility
- Average pollutant summary table below chart sorted alphabetically by station

### 13. Add pollutants reference table with sidebar toggle and expander descriptions
- Added pollutants reference table on the Geospatial Map page showing pollutant code and name
- Added sidebar checkbox to toggle pollutants table visibility (`Show pollutants`)
- Added collapsible `ℹ️ About` expanders below Monitoring Stations, Pollutants, and Measurements tables with contextual descriptions

### 14. Add choropleth map with four view modes
- Created `src/analysis/choropleth.py` with `render_choropleth()` function
- Added sidebar mode selector with four views:
  - 🏔️ Peak reading — shades each borough by its highest recorded concentration
  - 🕐 Most polluted hour — shades by the hour of day with the highest average concentration
  - 📅 Day-by-day — date slider to step through daily averages across the dataset
  - 📊 vs London average — shades by how far each borough deviates from the overall average
- Added pollutant selector for all six pollutants (NO₂, PM2.5, PM10, O₃, SO₂, CO)
- Added WHO threshold comparison in peak reading and day-by-day views
- Added summary table below each map view
- Added collapsible `ℹ️ About` expander below each view