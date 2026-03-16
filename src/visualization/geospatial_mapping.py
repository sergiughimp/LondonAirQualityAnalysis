import json
from pathlib import Path

import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium

# ─────────────────────────── FILE PATHS ────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[2]

DATA_FILES = {
    "Tower Hamlets": BASE_DIR / "data" / "geo" / "tower_hamlets.json",
    "Camden":        BASE_DIR / "data" / "geo" / "camden.json",
    "Greenwich":     BASE_DIR / "data" / "geo" / "greenwich.json",
}

STATIONS_FILE     = BASE_DIR / "data" / "processed" / "stations.csv"
MEASUREMENTS_FILE = BASE_DIR / "data" / "processed" / "measurements.csv"

# ─────────────────────────── HELPERS ───────────────────────────────
def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def extract_all_coordinates(geojson_data):
    coords = []

    def walk_geometry(geometry):
        gtype   = geometry.get("type")
        gcoords = geometry.get("coordinates", [])

        if gtype == "Polygon":
            for ring in gcoords:
                for lon, lat in ring:
                    coords.append((lat, lon))
        elif gtype == "MultiPolygon":
            for polygon in gcoords:
                for ring in polygon:
                    for lon, lat in ring:
                        coords.append((lat, lon))

    if geojson_data.get("type") == "FeatureCollection":
        for feature in geojson_data.get("features", []):
            walk_geometry(feature.get("geometry", {}))
    elif geojson_data.get("type") == "Feature":
        walk_geometry(geojson_data.get("geometry", {}))

    return coords

def get_center_from_coords(coords):
    if not coords:
        return 51.509, -0.118
    avg_lat = sum(lat for lat, _ in coords) / len(coords)
    avg_lon = sum(lon for _, lon in coords) / len(coords)
    return avg_lat, avg_lon

def make_feature_collection_if_needed(data, name):
    if data.get("type") == "FeatureCollection":
        for feature in data.get("features", []):
            if "properties" not in feature or feature["properties"] is None:
                feature["properties"] = {"name": name}
        return data

    if data.get("type") == "Feature":
        if "properties" not in data or data["properties"] is None:
            data["properties"] = {"name": name}
        return {"type": "FeatureCollection", "features": [data]}

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": name},
                "geometry": data,
            }
        ],
    }

# ─────────────────────────── MAIN ──────────────────────────────────
def render_map():

    # ─────────────────────────── LOAD BOROUGH GEOJSON ──────────────────
    borough_geojson = {}
    borough_coords  = {}
    missing_files   = []

    for borough, filepath in DATA_FILES.items():
        if filepath.exists():
            raw      = load_json(filepath)
            prepared = make_feature_collection_if_needed(raw, borough)
            borough_geojson[borough] = prepared
            borough_coords[borough]  = extract_all_coordinates(prepared)
        else:
            missing_files.append(str(filepath))

    # ─────────────────────────── LOAD STATIONS ─────────────────────────
    stations_df      = pd.DataFrame()
    stations_missing = False

    if STATIONS_FILE.exists():
        stations_df = pd.read_csv(STATIONS_FILE)
        stations_df.columns = (
            stations_df.columns.str.strip().str.lower().str.replace(" ", "_")
        )
    else:
        stations_missing = True

    # ─────────────────────────── TITLE ─────────────────────────────────
    st.markdown(
        """
        <style>
        .block-container {
            padding-left: 4rem;
            padding-right: 4rem;
            max-width: 100%;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("🗺️ Geospatial Mapping Tool")
    st.markdown(
        """
        Explore the administrative boundaries of **Camden**, **Greenwich**, and **Tower Hamlets**
        alongside their air quality monitoring infrastructure. Use the sidebar to customise the
        map view, toggle data layers, and filter by borough.
        """
    )

    if missing_files:
        st.error("⚠️ Borough boundary files not found: " + ", ".join(missing_files))

    if stations_missing:
        st.warning("⚠️ Stations file not found. Station markers will not be displayed.")

    if not borough_geojson:
        st.stop()

    # ─────────────────────────── SIDEBAR ───────────────────────────────
    st.sidebar.header("🗺️ Map Settings")

    tile_style = st.sidebar.selectbox(
        "Map style",
        ["OpenStreetMap", "CartoDB positron", "CartoDB dark_matter"],
        index=0,
    )

    view_mode = st.sidebar.radio(
        "View option",
        ["Show all boroughs", "Show one borough"],
    )

    selected_borough = None
    if view_mode == "Show one borough":
        selected_borough = st.sidebar.selectbox(
            "Choose borough",
            list(borough_geojson.keys()),
            index=0,
        )

    show_fill          = st.sidebar.checkbox("Fill polygons",              value=True)
    show_center_marker = st.sidebar.checkbox("Show borough centre marker",  value=True)
    show_labels        = st.sidebar.checkbox("Show borough labels",         value=True)
    zoom_start         = st.sidebar.slider("Zoom level", 9, 15, 11)

    st.sidebar.divider()
    st.sidebar.header("📍 Data Layers")

    show_stations     = st.sidebar.checkbox("Show monitoring stations", value=True)
    show_pollutants   = st.sidebar.checkbox("Show pollutants",          value=True)
    show_measurements = st.sidebar.checkbox("Show measurements",        value=True)

    # ─────────────────────────── MAP SETUP ─────────────────────────────
    if selected_borough:
        map_coords             = borough_coords[selected_borough]
        center_lat, center_lon = get_center_from_coords(map_coords)
    else:
        all_coords = []
        for coords in borough_coords.values():
            all_coords.extend(coords)
        center_lat, center_lon = get_center_from_coords(all_coords)

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_start,
        tiles=tile_style,
    )

    # ─────────────────────────── DRAW BOROUGHS ─────────────────────────
    colour_map = {
        "Tower Hamlets": "#d62728",
        "Camden":        "#1f77b4",
        "Greenwich":     "#2ca02c",
    }

    boroughs_to_draw = (
        [selected_borough] if selected_borough else list(borough_geojson.keys())
    )

    for borough in boroughs_to_draw:
        geojson_data = borough_geojson[borough]
        base_colour  = colour_map.get(borough, "#444444")
        is_selected  = borough == selected_borough if selected_borough else True

        folium.GeoJson(
            geojson_data,
            name=borough,
            style_function=lambda feature, is_selected=is_selected, base_colour=base_colour: {
                "fillColor":   base_colour if show_fill else "transparent",
                "color":       base_colour,
                "weight":      4 if is_selected else 2,
                "fillOpacity": 0.30 if show_fill and is_selected else (0.15 if show_fill else 0.0),
            },
            tooltip=borough if show_labels else None,
            popup=folium.Popup(f"<b>{borough}</b>", max_width=200),
        ).add_to(m)

        if show_center_marker:
            b_lat, b_lon = get_center_from_coords(borough_coords[borough])
            folium.Marker(
                location=[b_lat, b_lon],
                tooltip=borough,
                popup=f"{borough} centre",
                icon=folium.Icon(
                    color="red" if selected_borough == borough else "blue",
                    icon="info-sign",
                    prefix="glyphicon",
                ),
            ).add_to(m)

    # ─────────────────────────── DRAW STATIONS ─────────────────────────
    if show_stations and not stations_df.empty:
        boroughs_to_filter = (
            [selected_borough] if selected_borough else list(borough_geojson.keys())
        )

        filtered_stations = stations_df[
            stations_df["borough"].isin(boroughs_to_filter)
        ]

        station_layer = folium.FeatureGroup(name="Monitoring Stations")

        for _, row in filtered_stations.iterrows():
            try:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
            except (ValueError, KeyError):
                continue

            popup_html = f"""
                <b>{row.get('station_name', 'Unknown')}</b><br>
                <hr style='margin:4px 0'>
                Borough: {row.get('borough', 'N/A')}<br>
                Station Code: {row.get('station_code', 'N/A')}<br>
                Site Type: {row.get('site_type', 'N/A')}
            """

            folium.CircleMarker(
                location=[lat, lon],
                radius=2,
                color="#800080",
                fill=True,
                fill_color="#800080",
                fill_opacity=0.5,
                tooltip=row.get("station_name", "Station"),
                popup=folium.Popup(popup_html, max_width=220),
            ).add_to(station_layer)

        station_layer.add_to(m)

    folium.LayerControl().add_to(m)

    # ─────────────────────────── RENDER MAP ────────────────────────────
    st.subheader(
        f"📍 Map: {selected_borough}" if selected_borough else "📍 Map: All Boroughs"
    )
    st_folium(m, width=None, height=500, use_container_width=True)

    # ─────────────────────────── SUMMARY ───────────────────────────────
    st.divider()
    st.subheader("📌 Borough Summary")
    st.caption(
        "A high-level overview of each borough's geographic coverage and monitoring "
        "infrastructure. Boundary Points indicates the number of coordinate vertices "
        "used to define the borough polygon — a higher count reflects a more detailed boundary."
    )

    summary_rows = []
    for borough in boroughs_to_draw:
        coords = borough_coords[borough]
        center = get_center_from_coords(coords)
        station_count = (
            len(stations_df[stations_df["borough"] == borough])
            if not stations_df.empty
            else "N/A"
        )
        summary_rows.append({
            "Borough":             borough,
            "Boundary Points":     len(coords),
            "Monitoring Stations": station_count,
            "Centre Latitude":     round(center[0], 6),
            "Centre Longitude":    round(center[1], 6),
        })

    st.dataframe(summary_rows, use_container_width=True)

    # ─────────────────────────── POLLUTION CONTEXT ─────────────────────
    st.divider()
    with st.expander("🏙️ London Air Pollution — Project Context", expanded=True):
        st.markdown("""
        ### Why These Boroughs?
        London's worst air pollution follows its busiest roads. Camden, Greenwich, and Tower Hamlets
        sit directly on major pollution corridors — making them ideal subjects for monitoring
        the real-world health impact of urban air quality on East and Central London communities.

        ### Key Pollution Hotspots

        | Borough | Key Station | Pollution Driver |
        |---|---|---|
        | Camden | Euston Road, London NW1 | Major traffic corridor — consistently high NO₂ and PM2.5 |
        | Camden | Swiss Cottage, London NW3 | Kerbside exposure from diesel vehicles |
        | Camden | Bloomsbury, London WC1 | Urban background — mixed residential and traffic exposure |
        | Tower Hamlets | Mile End Road, London E1 | Heavy commuter and freight traffic |
        | Tower Hamlets | Blackwall, London E14 | Dense urban congestion — roadside hotspot |
        | Tower Hamlets | Bethnal Green, London E2 | Urban background — residential and road pollution |
        | Greenwich | Trafalgar Road, London SE10 | High-density road corridor |
        | Greenwich | Woolwich Flyover, London SE18 | Heavy vehicle and freight movement |
        | Greenwich | Tunnel Avenue, London SE10 | Industrial and road corridor exposure |

        ### Why It Matters
        Prolonged exposure to **NO₂**, **PM2.5**, and **PM10** is directly linked to respiratory
        disease, cardiovascular conditions, and reduced life expectancy — with the most severe
        impacts felt by children, the elderly, and those with pre-existing health conditions.

        > Camden, Tower Hamlets, and Greenwich together form a cross-city transect of Central,
        East, and South-East London — capturing both roadside peaks and typical urban background
        levels across diverse residential communities.
        """)

    # ─────────────────────────── STATIONS TABLE ────────────────────────
    if show_stations and not stations_df.empty:
        st.divider()
        st.subheader("📍 Monitoring Stations")
        st.caption(
            "Active air quality monitoring stations operated by the London Air Quality Network (LAQN) "
            "within the selected borough(s). Each station is classified by site type — "
            "**Roadside** stations are placed directly beside busy roads to capture peak exposure, "
            "while **Urban Background** stations reflect typical residential air quality away from traffic."
        )

        boroughs_to_filter = (
            [selected_borough] if selected_borough else list(borough_geojson.keys())
        )
        filtered_stations = stations_df[stations_df["borough"].isin(boroughs_to_filter)]

        display_stations = filtered_stations[["station_name", "site_type"]].reset_index(drop=True)
        display_stations.columns = ["Station Name", "Site Type"]

        st.dataframe(display_stations, use_container_width=True)

        with st.expander("ℹ️ About these stations", expanded=False):
            st.markdown("""
            Air quality monitoring stations in this dataset are part of the
            **London Air Quality Network (LAQN)**, one of the most comprehensive urban
            monitoring networks in the world, maintained in partnership with local councils
            and King's College London.

            **Station types explained:**
            - **Roadside** — located within 1 metre of a busy road carriageway, capturing
            the highest pollution exposure experienced by pedestrians and cyclists
            - **Urban Background** — located away from direct traffic sources, representing
            the baseline air quality that residents breathe in homes, schools, and parks

            The combination of both types across Camden, Tower Hamlets, and Greenwich
            provides a realistic picture of pollution at its worst and at typical residential levels —
            essential for assessing the true health burden on local communities.
            """)

    # ─────────────────────────── POLLUTANTS TABLE ──────────────────────
    if show_pollutants and MEASUREMENTS_FILE.exists():
        st.divider()
        st.subheader("🧪 Pollutants in This Dataset")
        st.caption(
            "The pollutants actively monitored across the selected borough(s) during the dataset period. "
            "Each pollutant has a distinct health impact profile and WHO guideline threshold."
        )

        boroughs_to_filter = (
            [selected_borough] if selected_borough else list(borough_geojson.keys())
        )

        _mdf = pd.read_csv(MEASUREMENTS_FILE)
        _mdf.columns = _mdf.columns.str.strip().str.lower().str.replace(" ", "_")
        _filtered = _mdf[
            _mdf["station_name"].isin(
                stations_df[stations_df["borough"].isin(boroughs_to_filter)]["station_name"]
            )
        ]

        pollutant_ref = (
            _filtered[["pollutant_code", "pollutant_name"]]
            .drop_duplicates()
            .sort_values("pollutant_code")
            .reset_index(drop=True)
        )
        pollutant_ref.columns = ["Pollutant Code", "Pollutant Name"]
        st.dataframe(pollutant_ref, use_container_width=True)

        with st.expander("ℹ️ About these pollutants", expanded=False):
            st.markdown("""
            | Pollutant | Code | Primary Source | WHO Threshold | Health Impact |
            |---|---|---|---|---|
            | Nitrogen Dioxide | NO₂ | Diesel vehicles, gas boilers | 25 µg/m³ | Airway irritation, worsens asthma and lung disease |
            | Particulate Matter 2.5 | PM2.5 | Exhaust, tyre/brake wear | 15 µg/m³ | Penetrates deep into lungs and bloodstream — linked to heart disease |
            | Particulate Matter 10 | PM10 | Construction dust, road wear | 45 µg/m³ | Respiratory inflammation, aggravates existing conditions |
            | Ozone | O₃ | Sunlight reacting with vehicle emissions | 100 µg/m³ | Breathing difficulties, particularly in summer months |
            | Sulphur Dioxide | SO₂ | Burning fossil fuels | 40 µg/m³ | Triggers asthma attacks, reduces lung function |
            | Carbon Monoxide | CO | Incomplete combustion | — | Reduces oxygen delivery in the body — readings largely absent in this dataset |

            > CO readings in this dataset are largely empty, indicating sensors were either
            inactive or concentrations fell below instrument detection limits during the monitoring period.
            """)

    # ─────────────────────────── MEASUREMENTS TABLE ────────────────────
    if show_measurements and MEASUREMENTS_FILE.exists():
        measurements_df = pd.read_csv(MEASUREMENTS_FILE)
        measurements_df.columns = (
            measurements_df.columns.str.strip().str.lower().str.replace(" ", "_")
        )

        # parse dates early for filtering
        measurements_df["measurement_date"] = pd.to_datetime(
            measurements_df["measurement_date"], errors="coerce"
        )

        st.divider()
        st.subheader("📊 Measurements")
        st.caption(
            "Daily summary of pollutant readings grouped by station, pollutant, and date. "
            "Each row shows the daily mean, maximum, minimum, and number of hourly readings recorded. "
            "Use the filters below to narrow down by borough, pollutant, or date."
        )

        # ── Filters ────────────────────────────────────────────────
        boroughs_to_filter = (
            [selected_borough] if selected_borough else list(borough_geojson.keys())
        )

        available_dates = sorted(
            measurements_df["measurement_date"].dt.date.dropna().unique()
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            borough_options       = ["All boroughs"] + boroughs_to_filter
            selected_meas_borough = st.selectbox(
                "Filter by borough",
                borough_options,
                index=0,
                key="meas_borough",
            )
        with col2:
            all_pollutants          = measurements_df["pollutant_code"].dropna().unique().tolist()
            pollutant_options       = ["All pollutants"] + sorted(all_pollutants)
            selected_meas_pollutant = st.selectbox(
                "Filter by pollutant",
                pollutant_options,
                index=0,
                key="meas_pollutant",
            )
        with col3:
            date_options       = ["All dates"] + [str(d) for d in available_dates]
            selected_meas_date = st.selectbox(
                "Filter by date",
                date_options,
                index=0,
                key="meas_date",
            )

        # ── Apply filters ───────────────────────────────────────────
        borough_filter_list = (
            boroughs_to_filter if selected_meas_borough == "All boroughs"
            else [selected_meas_borough]
        )

        filtered_measurements = measurements_df[
            measurements_df["station_name"].isin(
                stations_df[stations_df["borough"].isin(borough_filter_list)]["station_name"]
            )
        ]

        if selected_meas_pollutant != "All pollutants":
            filtered_measurements = filtered_measurements[
                filtered_measurements["pollutant_code"] == selected_meas_pollutant
            ]

        if selected_meas_date != "All dates":
            filtered_measurements = filtered_measurements[
                filtered_measurements["measurement_date"].dt.date.astype(str) == selected_meas_date
            ]

        if filtered_measurements.empty:
            st.info("No measurements found for the selected filters.")
        else:
            # ── Group by day ────────────────────────────────────────
            filtered_measurements = filtered_measurements.copy()
            filtered_measurements["date"] = filtered_measurements["measurement_date"].dt.date

            daily = (
                filtered_measurements.groupby(
                    ["borough", "station_name", "pollutant_code", "pollutant_name", "date"]
                )["value"]
                .agg(
                    Mean="mean",
                    Max="max",
                    Min="min",
                    Readings="count",
                )
                .round(2)
                .reset_index()
                .sort_values(["date", "borough", "station_name", "pollutant_code"])
            )

            daily.columns = [
                            "Borough", "Station Name", "Pollutant Code", "Pollutant Name", "Date",
                            "Daily Mean (µg/m³)", "Daily Max (µg/m³)", "Daily Min (µg/m³)", "Readings",
                        ]

            daily = daily.drop(columns=["Borough", "Pollutant Name"])
            st.dataframe(daily, use_container_width=True)

            # ── row count indicator ─────────────────────────────────
            st.caption(
                f"Showing **{len(daily):,}** daily summaries across "
                f"**{daily['Station Name'].nunique()}** station(s) and "
                f"**{daily['Pollutant Code'].nunique()}** pollutant(s)."
            )

        with st.expander("ℹ️ About these measurements", expanded=False):
            st.markdown("""
            **Data collection:** Readings are recorded **hourly** by each LAQN monitoring station
            and reported in **µg/m³** (micrograms per cubic metre) — the standard unit for
            ambient air quality measurement. Hourly readings are summarised here into
            daily statistics for clarity.

            **Columns explained:**
            - **Daily Mean** — average concentration across all hourly readings on that day
            - **Daily Max** — highest single hourly reading recorded on that day
            - **Daily Min** — lowest valid hourly reading recorded on that day
            - **Readings** — number of valid hourly readings that contributed to the daily summary

            **Data quality notes:**
            - Some stations exhibit **mid-dataset gaps** caused by temporary sensor outages
            or scheduled maintenance windows
            - A small number of stations record **anomalously high spikes** which may reflect
            calibration drift or localised pollution events rather than sustained exposure
            - **Negative values** are excluded from daily summaries as they indicate
            sensor calibration issues

            **Interpretation guidance:**
            Compare readings against WHO annual mean guideline thresholds:

            | Pollutant | WHO Guideline |
            |---|---|
            | NO₂ | 25 µg/m³ |
            | PM2.5 | 15 µg/m³ |
            | PM10 | 45 µg/m³ |
            | O₃ | 100 µg/m³ |
            | SO₂ | 40 µg/m³ |

            For a full analysis of exceedances and health risk by station,
            visit the **🏥 Health Impact** page.
            """)

    elif not MEASUREMENTS_FILE.exists():
        st.warning(
            "⚠️ Measurements file not found. "
            "Please fetch data using the **🔄 Fetch data** button in the sidebar."
        )