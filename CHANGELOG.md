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

### 15. Add box plot page
- Created `src/analysis/box_plot.py` with `render_box_plot()` function
- Manual box plot built with Altair using whisker, IQR box, and median tick layers
- Dynamically filters to the 3 pollutants with the most valid readings
- Borough filter selectbox with "All boroughs" option
- WHO guideline threshold line with label for each pollutant
- Full station labels shown with `labelLimit=0` and angled axis
- Summary statistics table below chart showing Min, Q1, Median, Q3, Max, Mean, Std Dev
- WHO exceedance flag per station in summary table
- Collapsible `ℹ️ About` expander explaining how to read the chart

### 16. Add missing data analysis page
- Created `src/analysis/missing_data.py` with `render_missing_data()` function
- Impact on analysis expander at the top of the page explaining how missing data
  affects time series, heatmap, choropleth, and box plot pages
- Four visualisations:
  - 🟥 Heatmap grid — station vs hour coloured by % missing
  - 📊 Bar chart — stations ranked by % missing, colour-coded by borough
  - 📅 Timeline — station vs day coloured by % missing
  - 📋 Summary table — total, missing, present counts and % per station
- Status flag per station: ✅ Good (<5%), ⚡ Moderate (5–20%), ⚠️ High (>20%)
- All six pollutants available in sidebar selector (NO₂, PM2.5, PM10, O₃, SO₂, CO)
- Borough filter with all boroughs or single borough view
- Collapsible `ℹ️ About` expander below each visualisation

### 17. Refactor app.py structure
- Added automatic data pipeline on first launch if processed data is missing
- Added `run_pipeline()` function to run fetch and process scripts sequentially with spinners
- Added `data_is_ready()` helper to check if processed data exists
- Added `clear_data()` helper to delete raw and processed files before refresh
- Added `load_measurements()` and `load_stations()` data loader helpers
- Added `render_sidebar()` function returning the selected page
- Added `render_page()` function routing to the correct page renderer
- Added `main()` function as single entry point called at module level
- Added 🔄 Refresh data button in sidebar under Data Management section
- File paths consolidated into `DATA_DIR` and `PROCESSING_DIR` constants

### 18. Add dynamic date range selection
- Removed hardcoded `START` and `END` dates from `fetch_air_quality_data.py`
- Added `argparse` to `fetch_air_quality_data.py` with `--start` and `--end` arguments
- Updated `run_pipeline()` in `app.py` to accept and pass `start_date` and `end_date`
- Added date pickers in sidebar under 📅 Date Range section
- Replaced automatic pipeline on first launch with manual **🔄 Fetch data** button
- App now prompts user to select a date range before fetching data

### 19. Add Health Impact and Correlation Analysis pages
- Created `src/analysis/health_impact.py` with `render_health_impact()` function
  - WHO exceedance hours per borough shown as grouped bar chart
  - Overall risk ranking per station based on average exceedance across all pollutants
  - Full exceedance breakdown table per station and pollutant
  - Risk levels: ✅ None, 🟡 Low, 🟠 Moderate, 🔴 High, 🚨 Very High
  - Borough filter in sidebar
- Created `src/analysis/correlation.py` with `render_correlation()` function
  - Pollutant correlation heatmap with Pearson coefficients
  - Interactive scatter plot with x and y pollutant selectors
  - Correlation matrix table
  - Borough filter in sidebar
- Removed 🎻 Violin Plot page
- Updated sidebar navigation and page router in `streamlit_app.py`

### 20. Add test suite
- Created `tests/__init__.py`
- Created `tests/test_data_pipeline.py` with 3 tests:
  - `test_stations_file_exists` — checks stations.csv is created after processing
  - `test_stations_has_required_columns` — checks all required columns are present
  - `test_stations_not_empty` — checks stations.csv contains at least one row
- Created `tests/test_data_quality.py` with 3 tests:
  - `test_borough_names_valid` — checks only Camden, Greenwich, Tower Hamlets present
  - `test_pollutant_codes_valid` — checks only known pollutant codes present
  - `test_measurement_dates_parseable` — checks all dates parse without errors
- Created `tests/test_analysis.py` with 3 tests:
  - `test_who_thresholds_correct` — checks WHO thresholds match expected values
  - `test_peak_value_matches_max` — checks peak calculation matches actual max
  - `test_missing_rate_calculation` — checks missing rate is between 0 and 100
- Created `tests/test_api.py` with 3 tests:
  - `test_api_species_endpoint_reachable` — checks species endpoint returns 200
  - `test_api_sites_endpoint_reachable` — checks sites endpoint returns 200
  - `test_api_returns_json` — checks API response is a valid JSON object
- Updated project structure in README.md to include all test files

### 21. Improve geospatial mapping measurements table
- Measurements table now grouped by day showing Daily Mean, Daily Max, Daily Min and Readings count
- Borough column added to daily summary table
- Three inline filters added above the table — Filter by borough, Filter by pollutant, Filter by date
- Date parsing moved before filters to support date filter dropdown
- Empty filter result handled gracefully with info message
- Row count caption added below table showing number of summaries, stations and pollutants visible
- Negative values excluded from daily summaries
- About expander updated to explain all columns and reflect daily summary format
- Caption updated to describe daily summary format

### 22. Refactor and improve time series page
- Added all 6 pollutants to selector (NO₂, PM2.5, PM10, O₃, SO₂, CO)
- Added `WHO_THRESHOLDS` and `BOROUGH_COLOURS` constants block at top of file
- Replaced `st.write()` with `st.markdown()` for professional intro description
- Sidebar header renamed from `⚙️ Filters` to `📈 Time Series Settings`
- Borough filter label updated to `Filter by borough` for consistency
- Added `.copy()` to avoid pandas `SettingWithCopyWarning`
- Added `filtered["value"] > 0` to exclude negative and zero readings
- Added `label` field to rush hour bands for tooltip context
- Borough added to chart tooltip
- WHO label text updated to `WHO guideline: {threshold} µg/m³`
- Chart title updated to be more descriptive
- Added `ℹ️ About this chart` expander explaining rush hour bands and WHO line
- Summary table expanded with Min column, Borough grouping, and WHO exceedance flag
- `st.caption()` added above summary table with context
- Added `ℹ️ About this table` expander explaining each column
- Borough column removed from summary table display with `.drop(columns=["Borough"])`

### 23. Refactor and improve heatmap page
- Added all 6 pollutants to selector (NO₂, PM2.5, PM10, O₃, SO₂, CO)
- Added `WHO_THRESHOLDS` and `BOROUGH_COLOURS` constants block at top of file
- Replaced `st.write()` with `st.markdown()` for professional intro description
- Sidebar header renamed from `⚙️ Filters` to `🔥 Heatmap Settings`
- Borough filter label updated to `Filter by borough` for consistency
- Added `.copy()` to avoid pandas `SettingWithCopyWarning`
- Added `filtered["value"] > 0` to exclude negative and zero readings
- Chart height made dynamic based on number of stations
- `labelLimit=0` added to y-axis so all station names display fully
- Added `ℹ️ About this chart` expander explaining how to read the heatmap
- Summary table expanded with Peak, Min, Readings, and WHO exceedance flag
- `st.caption()` added above summary table with context
- Borough column removed from summary table display with `.drop(columns=["Borough"])`
- Added `ℹ️ About this table` expander explaining each column

### 24. Refactor and improve choropleth page
- Added `st.markdown()` intro to `render_choropleth()` explaining the four view modes
- Added `⚠️` prefix to all warning messages for consistency
- Subheaders updated with `📍` emoji for all map sections
- `ℹ️ About this view` expanders moved above summary tables with richer pollutant-specific descriptions
- `st.caption()` added above every summary table with contextual description
- `load_geo()` warning message updated to use `⚠️` prefix
- Code style fully aligned across all four view mode functions

### 25. Refactor and improve correlation analysis page
- Replaced `st.write()` with `st.markdown()` for professional intro description
- Removed unused `numpy` import
- Added `df["value"] > 0` to exclude negative and zero readings
- Sidebar header updated to `📊 Correlation Settings` for consistency
- `st.caption()` added above all three sections with contextual descriptions
- Correlation heatmap centred and enlarged using `st.columns([1, 3, 1])` with `width=500, height=500`
- Heatmap text labels made bold and slightly larger for readability
- `labelAngle=0` added to x-axis for cleaner label display
- `⚠️` prefix added to all warning messages for consistency
- `ℹ️ About this chart` expander added below correlation heatmap with detailed interpretation guidance
- `ℹ️ About this chart` expander added below scatter plot with interpretation guidance
- `ℹ️ About this table` expander added below correlation matrix table
- Scatter plot warning message updated to reference specific pollutant names
- Scatter plot tooltip updated to include units in label
- Section title updated from `📋 Correlation Matrix` to `📋 Full Correlation Matrix`