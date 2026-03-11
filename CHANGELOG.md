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

  data/raw/air_quality_3_day.json

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