import sys
import streamlit as st
import pandas as pd
from pathlib import Path

# ─────────────────────────── PATH SETUP ────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

st.set_page_config(
    page_title="London Air Quality Analysis",
    page_icon="🗺️",
    layout="wide"
)

# ─────────────────────────── NAVIGATION ────────────────────────────
st.sidebar.title("🗺️ Navigation")

page = st.sidebar.radio(
    "Select page",
    [
        "🗺️ Geospatial Map",
        "📈 Time Series",
        "🔥 Heatmap",
        "🗺️ Choropleth",
        "📦 Box Plot",
        "📉 Missing Data"
    ]
)

# ─────────────────────────── PAGES ─────────────────────────────────
if page == "🗺️ Geospatial Map":
    from src.visualization.geospatial_mapping import render_map
    render_map()

elif page == "📈 Time Series":
    from src.analysis.time_series import render_time_series
    measurements_df = pd.read_csv(BASE_DIR / "data" / "processed" / "measurements.csv")
    render_time_series(measurements_df)

elif page == "🔥 Heatmap":
    from src.analysis.heatmap import render_heatmap
    measurements_df = pd.read_csv(BASE_DIR / "data" / "processed" / "measurements.csv")
    render_heatmap(measurements_df)

elif page == "🗺️ Choropleth":
    from src.analysis.choropleth import render_choropleth
    measurements_df = pd.read_csv(BASE_DIR / "data" / "processed" / "measurements.csv")
    stations_df = pd.read_csv(BASE_DIR / "data" / "processed" / "stations.csv")
    render_choropleth(measurements_df, stations_df)

elif page == "📦 Box Plot":
    from src.analysis.box_plot import render_box_plot
    measurements_df = pd.read_csv(BASE_DIR / "data" / "processed" / "measurements.csv")
    render_box_plot(measurements_df)

elif page == "📉 Missing Data":
    from src.analysis.missing_data import render_missing_data
    measurements_df = pd.read_csv(BASE_DIR / "data" / "processed" / "measurements.csv")
    render_missing_data(measurements_df)