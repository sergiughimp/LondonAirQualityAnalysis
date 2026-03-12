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
    "Camden": BASE_DIR / "data" / "geo" / "camden.json",
    "Greenwich": BASE_DIR / "data" / "geo" / "greenwich.json",
}

STATIONS_FILE = BASE_DIR / "data" / "processed" / "stations.csv"
MEASUREMENTS_FILE = BASE_DIR / "data" / "processed" / "measurements.csv"

# ─────────────────────────── HELPERS ───────────────────────────────
def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def extract_all_coordinates(geojson_data):
    coords = []

    def walk_geometry(geometry):
        gtype = geometry.get("type")
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
            geometry = feature.get("geometry", {})
            walk_geometry(geometry)
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
    borough_coords = {}
    missing_files = []

    for borough, filepath in DATA_FILES.items():
        if filepath.exists():
            raw = load_json(filepath)
            prepared = make_feature_collection_if_needed(raw, borough)
            borough_geojson[borough] = prepared
            borough_coords[borough] = extract_all_coordinates(prepared)
        else:
            missing_files.append(str(filepath))

    # ─────────────────────────── LOAD STATIONS ─────────────────────────
    stations_df = pd.DataFrame()
    stations_missing = False

    if STATIONS_FILE.exists():
        stations_df = pd.read_csv(STATIONS_FILE)
        stations_df.columns = stations_df.columns.str.strip().str.lower().str.replace(" ", "_")
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
    st.write(
        "Explore the borough boundaries of Camden, Greenwich, and Tower Hamlets "
        "individually or together."
    )

    if missing_files:
        st.error("These borough files were not found: " + ", ".join(missing_files))

    if stations_missing:
        st.warning("Stations file not found: " + str(STATIONS_FILE))

    if not borough_geojson:
        st.stop()

    # ─────────────────────────── SIDEBAR ───────────────────────────────
    st.sidebar.header("🗺️ Map Settings")

    tile_style = st.sidebar.selectbox(
        "Map style",
        ["OpenStreetMap", "CartoDB positron", "CartoDB dark_matter"],
        index=0
    )

    view_mode = st.sidebar.radio(
        "View option",
        ["Show all boroughs", "Show one borough"]
    )

    selected_borough = None
    if view_mode == "Show one borough":
        selected_borough = st.sidebar.selectbox(
            "Choose borough",
            list(borough_geojson.keys()),
            index=0
        )

    show_fill = st.sidebar.checkbox("Fill polygons", value=True)
    show_center_marker = st.sidebar.checkbox("Show borough centre marker", value=True)
    show_labels = st.sidebar.checkbox("Show borough labels", value=True)
    zoom_start = st.sidebar.slider("Zoom level", 9, 15, 11)

    st.sidebar.divider()
    st.sidebar.header("📍 Stations")

    show_stations = st.sidebar.checkbox("Show monitoring stations", value=True)
    show_measurements = st.sidebar.checkbox("Show measurements", value=True)

    # ─────────────────────────── MAP SETUP ─────────────────────────────
    if selected_borough:
        map_coords = borough_coords[selected_borough]
        center_lat, center_lon = get_center_from_coords(map_coords)
    else:
        all_coords = []
        for coords in borough_coords.values():
            all_coords.extend(coords)
        center_lat, center_lon = get_center_from_coords(all_coords)

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_start,
        tiles=tile_style
    )

    # ─────────────────────────── DRAW BOROUGHS ─────────────────────────
    colour_map = {
        "Tower Hamlets": "#d62728",
        "Camden": "#1f77b4",
        "Greenwich": "#2ca02c",
    }

    boroughs_to_draw = (
        [selected_borough] if selected_borough else list(borough_geojson.keys())
    )

    for borough in boroughs_to_draw:
        geojson_data = borough_geojson[borough]
        base_colour = colour_map.get(borough, "#444444")
        is_selected = borough == selected_borough if selected_borough else True

        folium.GeoJson(
            geojson_data,
            name=borough,
            style_function=lambda feature, is_selected=is_selected, base_colour=base_colour: {
                "fillColor": base_colour if show_fill else "transparent",
                "color": base_colour,
                "weight": 4 if is_selected else 2,
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
                Borough: {row.get('borough', 'N/A')}<br>
                Code: {row.get('station_code', 'N/A')}<br>
                Site type: {row.get('site_type', 'N/A')}
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
        f"Map: {selected_borough}" if selected_borough else "Map: All Boroughs"
    )
    st_folium(m, width=None, height=500, use_container_width=True)

    # ─────────────────────────── SUMMARY ───────────────────────────────
    st.divider()
    st.subheader("📌 Borough Summary")

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
            "Borough": borough,
            "Boundary Points": len(coords),
            "Monitoring Stations": station_count,
            "Centre Latitude": round(center[0], 6),
            "Centre Longitude": round(center[1], 6),
        })

    st.dataframe(summary_rows, use_container_width=True)

    # ─────────────────────────── POLLUTION CONTEXT ─────────────────────
    st.divider()
    with st.expander("🏙️ London Air Pollution — Project Context", expanded=True):
        st.markdown("""
        ### Why These Boroughs?
        London's worst air pollution follows its busiest roads. This project monitors three boroughs
        that sit directly on major pollution corridors.

        ### Key Pollution Hotspots

        | Borough | Key Station | Pollution Driver |
        |---|---|---|
        | Camden | Euston Road, London NW1 | Major traffic corridor, high NO₂ and PM2.5 |
        | Camden | Swiss Cottage, London NW3 | Kerbside exposure, diesel vehicles |
        | Camden | Bloomsbury, London WC1 | Urban background, mixed traffic exposure |
        | Tower Hamlets | Mile End Road, London E1 | Commuter and freight traffic |
        | Tower Hamlets | Blackwall, London E14 | Urban congestion, roadside exposure |
        | Tower Hamlets | Bethnal Green, London E2 | Urban background, residential and road pollution |
        | Greenwich | Trafalgar Road, London SE10 | High-density road corridor |
        | Greenwich | Woolwich Flyover, London SE18 | Heavy vehicle and freight movement |
        | Greenwich | Tunnel Avenue, London SE10 | Industrial and road corridor exposure |

        ### Why It Matters
        These stations capture real-world exposure to **NO₂**, **PM2.5**, and **PM10** — the three
        pollutants most linked to respiratory and cardiovascular health impacts in urban populations.

        > Camden, Tower Hamlets, and Greenwich together represent central, east, and south-east London
        — giving a cross-city picture of roadside and urban background pollution.
        """)

    # ─────────────────────────── STATIONS TABLE ────────────────────────
    if show_stations and not stations_df.empty:
        st.divider()
        st.subheader("📍 Monitoring Stations")

        boroughs_to_filter = (
            [selected_borough] if selected_borough else list(borough_geojson.keys())
        )
        filtered_stations = stations_df[stations_df["borough"].isin(boroughs_to_filter)]

        display_cols = ["station_name", "site_type"]
        display_stations = filtered_stations[display_cols].reset_index(drop=True)
        display_stations.columns = ["Station Name", "Site Type"]

        st.dataframe(display_stations, use_container_width=True)

    # ─────────────────────────── MEASUREMENTS TABLE ────────────────────
    if show_measurements and MEASUREMENTS_FILE.exists():
        measurements_df = pd.read_csv(MEASUREMENTS_FILE)
        measurements_df.columns = measurements_df.columns.str.strip().str.lower().str.replace(" ", "_")

        st.divider()
        st.subheader("📊 Measurements")

        boroughs_to_filter = (
            [selected_borough] if selected_borough else list(borough_geojson.keys())
        )

        filtered_measurements = measurements_df[
            measurements_df["station_name"].isin(
                stations_df[stations_df["borough"].isin(boroughs_to_filter)]["station_name"]
            )
        ]

        display_cols = ["station_name", "pollutant_code", "pollutant_name", "measurement_date", "value"]
        display_measurements = filtered_measurements[display_cols].reset_index(drop=True)
        display_measurements.columns = ["Station Name", "Pollutant Code", "Pollutant Name", "Measurement Date", "Value"]

        st.dataframe(display_measurements, use_container_width=True)
    elif not MEASUREMENTS_FILE.exists():
        st.warning("Measurements file not found: " + str(MEASUREMENTS_FILE))