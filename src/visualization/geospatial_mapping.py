import json
from pathlib import Path

import streamlit as st
import folium
from streamlit_folium import st_folium

# ─────────────────────────── PAGE CONFIG ───────────────────────────
st.set_page_config(
    page_title="London Borough Geospatial Mapping",
    page_icon="🗺️",
    layout="wide"
)

# ─────────────────────────── FILE PATHS ────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[2]

DATA_FILES = {
    "Tower Hamlets": BASE_DIR / "data" / "geo" / "tower_hamlets.json",
    "Camden": BASE_DIR / "data" / "geo" / "camden.json",
    "Greenwich": BASE_DIR / "data" / "geo" / "greenwich.json",
}

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

# ─────────────────────────── TITLE ─────────────────────────────────
st.title("🗺️ Geospatial Mapping Tool")
st.write(
    "Explore the borough boundaries of Camden, Greenwich, and Tower Hamlets "
    "individually or together."
)

if missing_files:
    st.error("These borough files were not found: " + ", ".join(missing_files))

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

folium.LayerControl().add_to(m)

# ─────────────────────────── RENDER MAP ────────────────────────────
st.subheader(
    f"Map: {selected_borough}" if selected_borough else "Map: All Boroughs"
)
st_folium(m, width=None, height=650, use_container_width=True)

# ─────────────────────────── SUMMARY ───────────────────────────────
st.divider()
st.subheader("📌 Borough Summary")

summary_rows = []
for borough in boroughs_to_draw:
    coords = borough_coords[borough]
    center = get_center_from_coords(coords)
    summary_rows.append({
        "Borough": borough,
        "Boundary Points": len(coords),
        "Centre Latitude": round(center[0], 6),
        "Centre Longitude": round(center[1], 6),
    })

st.dataframe(summary_rows, use_container_width=True)