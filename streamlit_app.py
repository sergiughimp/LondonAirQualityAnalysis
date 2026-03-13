import sys
import subprocess
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

# ─────────────────────────── FILE PATHS ────────────────────────────
DATA_DIR          = BASE_DIR / "data"
RAW_FILE          = DATA_DIR / "raw"       / "air_quality_3_days.json"
STATIONS_FILE     = DATA_DIR / "processed" / "stations.csv"
MEASUREMENTS_FILE = DATA_DIR / "processed" / "measurements.csv"

PROCESSING_DIR    = BASE_DIR / "src" / "processing"
FETCH_SCRIPT      = PROCESSING_DIR / "fetch_air_quality_data.py"
PROCESS_SCRIPT    = PROCESSING_DIR / "process_air_quality_data.py"

# ─────────────────────────── PIPELINE ──────────────────────────────
def run_pipeline():
    steps = [
        ("🌐 Fetching air quality data from LondonAir API...", FETCH_SCRIPT),
        ("⚙️ Processing raw data...",                          PROCESS_SCRIPT),
    ]
    for message, script in steps:
        with st.spinner(message):
            result = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                st.error(f"❌ Pipeline failed at: {script.name}")
                st.code(result.stderr)
                st.stop()
    st.success("✅ Data pipeline complete.")
    st.rerun()

def data_is_ready() -> bool:
    return STATIONS_FILE.exists() and MEASUREMENTS_FILE.exists()

def clear_data():
    for f in [RAW_FILE, STATIONS_FILE, MEASUREMENTS_FILE]:
        f.unlink(missing_ok=True)

# ─────────────────────────── DATA LOADERS ──────────────────────────
def load_measurements() -> pd.DataFrame:
    return pd.read_csv(MEASUREMENTS_FILE)

def load_stations() -> pd.DataFrame:
    return pd.read_csv(STATIONS_FILE)

# ─────────────────────────── SIDEBAR ───────────────────────────────
def render_sidebar() -> str:
    st.sidebar.title("🗺️ Navigation")

    page = st.sidebar.radio(
        "Select page",
        [
            "🗺️ Geospatial Map",
            "📈 Time Series",
            "🔥 Heatmap",
            "🗺️ Choropleth",
            "📦 Box Plot",
            "📉 Missing Data",
        ]
    )

    st.sidebar.divider()
    st.sidebar.caption("Data Management")
    if st.sidebar.button("🔄 Refresh data"):
        clear_data()
        run_pipeline()

    return page

# ─────────────────────────── PAGE ROUTER ───────────────────────────
def render_page(page: str):
    if page == "🗺️ Geospatial Map":
        from src.visualization.geospatial_mapping import render_map
        render_map()

    elif page == "📈 Time Series":
        from src.analysis.time_series import render_time_series
        render_time_series(load_measurements())

    elif page == "🔥 Heatmap":
        from src.analysis.heatmap import render_heatmap
        render_heatmap(load_measurements())

    elif page == "🗺️ Choropleth":
        from src.analysis.choropleth import render_choropleth
        render_choropleth(load_measurements(), load_stations())

    elif page == "📦 Box Plot":
        from src.analysis.box_plot import render_box_plot
        render_box_plot(load_measurements())

    elif page == "📉 Missing Data":
        from src.analysis.missing_data import render_missing_data
        render_missing_data(load_measurements())

# ─────────────────────────── MAIN ──────────────────────────────────
def main():
    if not data_is_ready():
        st.title("🗺️ London Air Quality Analysis")
        st.info("📦 Processed data not found. Running data pipeline...")
        run_pipeline()

    page = render_sidebar()
    render_page(page)


main()