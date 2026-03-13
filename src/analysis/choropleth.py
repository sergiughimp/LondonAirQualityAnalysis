from pathlib import Path
import json

import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium

# ─────────────────────────── FILE PATHS ────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[2]

GEO_FILES = {
    "Camden":        BASE_DIR / "data" / "geo" / "camden.json",
    "Greenwich":     BASE_DIR / "data" / "geo" / "greenwich.json",
    "Tower Hamlets": BASE_DIR / "data" / "geo" / "tower_hamlets.json",
}

# ─────────────────────────── POLLUTANTS ────────────────────────────
POLLUTANTS = {
    "NO₂ — Nitrogen Dioxide":         "NO2",
    "PM2.5 — Particulate Matter 2.5": "PM25",
    "PM10 — Particulate Matter 10":   "PM10",
    "O₃ — Ozone":                     "O3",
    "SO₂ — Sulphur Dioxide":          "SO2",
    "CO — Carbon Monoxide":           "CO",
}

WHO_THRESHOLDS = {
    "NO2":  25,
    "PM25": 15,
    "PM10": 45,
    "O3":   100,
    "SO2":  40,
    "CO":   None,
}

BOROUGH_COLOURS = {
    "Camden":        "#1f77b4",
    "Greenwich":     "#2ca02c",
    "Tower Hamlets": "#d62728",
}

BOROUGHS = ["Camden", "Greenwich", "Tower Hamlets"]

# ─────────────────────────── HELPERS ───────────────────────────────
def load_geo(borough):
    path = GEO_FILES[borough]
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def add_borough_layer(m, borough, value, max_val, label, popup_html):
    geo_data = load_geo(borough)
    if geo_data is None:
        st.warning(f"GeoJSON not found for {borough}")
        return

    if value is None:
        fill_colour = "#cccccc"
        fill_opacity = 0.3
    else:
        normalised = value / max_val if max_val else 0
        fill_opacity = 0.15 + normalised * 0.70
        fill_colour = BOROUGH_COLOURS[borough]

    folium.GeoJson(
        geo_data,
        name=borough,
        style_function=lambda feature, fc=fill_colour, fo=fill_opacity: {
            "fillColor": fc,
            "color": fc,
            "weight": 2,
            "fillOpacity": fo,
        },
        tooltip=f"{borough}: {label}",
        popup=folium.Popup(popup_html, max_width=240),
    ).add_to(m)

def base_map():
    return folium.Map(location=[51.509, -0.118], zoom_start=11, tiles="CartoDB positron")

def prepare_df(measurements_df, stations_df):
    df = measurements_df.copy()
    sdf = stations_df.copy()
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    sdf.columns = sdf.columns.str.strip().str.lower().str.replace(" ", "_")
    if "borough" not in df.columns:
        df = df.merge(sdf[["station_name", "borough"]], on="station_name", how="left")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["measurement_date"] = pd.to_datetime(df["measurement_date"], errors="coerce")
    df["hour"] = df["measurement_date"].dt.hour
    df["date"] = df["measurement_date"].dt.date
    return df

# ─────────────────────────── MODES ─────────────────────────────────
def mode_peak(df, pollutant_code, threshold):
    filtered = df[(df["pollutant_code"] == pollutant_code) & (df["value"] > 0) & df["value"].notna()]
    peak_df = filtered.groupby("borough")["value"].max().reset_index().rename(columns={"value": "peak"})
    peak_lookup = dict(zip(peak_df["borough"], peak_df["peak"]))
    max_val = peak_df["peak"].max() if not peak_df.empty else 1

    m = base_map()
    for borough in BOROUGHS:
        val = peak_lookup.get(borough)
        label = f"{val:.1f} µg/m³" if val else "No data"
        popup = f"<b>{borough}</b><br>Pollutant: {pollutant_code}<br>Peak: {label}"
        if threshold and val:
            status = "⚠️ Above WHO limit" if val > threshold else "✅ Within WHO limit"
            popup += f"<br>WHO threshold: {threshold} µg/m³<br>{status}"
        add_borough_layer(m, borough, val, max_val, label, popup)

    folium.LayerControl().add_to(m)
    st.subheader(f"Peak {pollutant_code} concentration by borough")
    st_folium(m, width=None, height=500, use_container_width=True)

    st.divider()
    st.subheader("📊 Peak Readings Summary")
    rows = []
    for borough in BOROUGHS:
        val = peak_lookup.get(borough)
        status = ("⚠️ Above" if val > threshold else "✅ Within") if val and threshold else "N/A"
        rows.append({
            "Borough": borough,
            "Peak Reading (µg/m³)": round(val, 2) if val else "No data",
            "WHO Threshold (µg/m³)": threshold or "N/A",
            "Status": status,
        })
    st.dataframe(rows, use_container_width=True)

    with st.expander("ℹ️ About this view", expanded=False):
        st.markdown("""
        Each borough is shaded by its **single highest recorded reading** for the selected pollutant.
        A darker shade means a higher peak. Grey means no data.
        Peak readings highlight worst-case exposure moments across the dataset.
        """)


def mode_peak_hour(df, pollutant_code):
    filtered = df[(df["pollutant_code"] == pollutant_code) & (df["value"] > 0) & df["value"].notna()]
    hour_df = filtered.groupby(["borough", "hour"])["value"].mean().reset_index()
    peak_hour_df = hour_df.loc[hour_df.groupby("borough")["value"].idxmax()]
    peak_hour_lookup = dict(zip(peak_hour_df["borough"], peak_hour_df["hour"]))
    peak_val_lookup = dict(zip(peak_hour_df["borough"], peak_hour_df["value"]))
    max_val = peak_hour_df["value"].max() if not peak_hour_df.empty else 1

    m = base_map()
    for borough in BOROUGHS:
        hour = peak_hour_lookup.get(borough)
        val = peak_val_lookup.get(borough)
        label = f"{int(hour):02d}:00 (avg {val:.1f} µg/m³)" if hour is not None else "No data"
        popup = f"<b>{borough}</b><br>Pollutant: {pollutant_code}<br>Peak hour: {label}"
        add_borough_layer(m, borough, val, max_val, label, popup)

    folium.LayerControl().add_to(m)
    st.subheader(f"Most polluted hour of day — {pollutant_code}")
    st_folium(m, width=None, height=500, use_container_width=True)

    st.divider()
    st.subheader("📊 Peak Hour Summary")
    rows = []
    for borough in BOROUGHS:
        hour = peak_hour_lookup.get(borough)
        val = peak_val_lookup.get(borough)
        rows.append({
            "Borough": borough,
            "Peak Hour": f"{int(hour):02d}:00" if hour is not None else "No data",
            "Avg Concentration (µg/m³)": round(val, 2) if val else "No data",
        })
    st.dataframe(rows, use_container_width=True)

    with st.expander("ℹ️ About this view", expanded=False):
        st.markdown("""
        Each borough is shaded by the **hour of day with the highest average concentration**
        for the selected pollutant. Darker shading means the peak hour had a higher average reading.
        This view highlights rush hour and other daily pollution patterns across boroughs.
        """)


def mode_daily(df, pollutant_code, threshold):
    filtered = df[(df["pollutant_code"] == pollutant_code) & (df["value"] > 0) & df["value"].notna()]
    available_dates = sorted(filtered["date"].dropna().unique())

    if not available_dates:
        st.warning("No data available for this pollutant.")
        return

    selected_date = st.sidebar.select_slider(
        "Select date",
        options=available_dates,
        format_func=lambda d: d.strftime("%d %b %Y"),
    )

    day_df = filtered[filtered["date"] == selected_date]
    daily_df = day_df.groupby("borough")["value"].mean().reset_index().rename(columns={"value": "avg"})
    daily_lookup = dict(zip(daily_df["borough"], daily_df["avg"]))
    max_val = daily_df["avg"].max() if not daily_df.empty else 1

    m = base_map()
    for borough in BOROUGHS:
        val = daily_lookup.get(borough)
        label = f"{val:.1f} µg/m³" if val else "No data"
        popup = f"<b>{borough}</b><br>Pollutant: {pollutant_code}<br>Date: {selected_date}<br>Avg: {label}"
        if threshold and val:
            status = "⚠️ Above WHO limit" if val > threshold else "✅ Within WHO limit"
            popup += f"<br>WHO threshold: {threshold} µg/m³<br>{status}"
        add_borough_layer(m, borough, val, max_val, label, popup)

    folium.LayerControl().add_to(m)
    st.subheader(f"{pollutant_code} average — {selected_date.strftime('%d %b %Y')}")
    st_folium(m, width=None, height=500, use_container_width=True)

    st.divider()
    st.subheader("📊 Daily Average Summary")
    rows = []
    for borough in BOROUGHS:
        val = daily_lookup.get(borough)
        status = ("⚠️ Above" if val > threshold else "✅ Within") if val and threshold else "N/A"
        rows.append({
            "Borough": borough,
            "Daily Avg (µg/m³)": round(val, 2) if val else "No data",
            "WHO Threshold (µg/m³)": threshold or "N/A",
            "Status": status,
        })
    st.dataframe(rows, use_container_width=True)

    with st.expander("ℹ️ About this view", expanded=False):
        st.markdown("""
        Each borough is shaded by its **average concentration on the selected day**.
        Use the date slider in the sidebar to step through the dataset day by day.
        Darker shading means a higher daily average. Compare days to spot how pollution
        levels shift across the monitoring period.
        """)


def mode_vs_average(df, pollutant_code, threshold):
    filtered = df[(df["pollutant_code"] == pollutant_code) & (df["value"] > 0) & df["value"].notna()]
    london_avg = filtered["value"].mean()
    borough_avg = filtered.groupby("borough")["value"].mean().reset_index().rename(columns={"value": "avg"})
    borough_avg["diff"] = borough_avg["avg"] - london_avg
    diff_lookup = dict(zip(borough_avg["borough"], borough_avg["diff"]))
    avg_lookup = dict(zip(borough_avg["borough"], borough_avg["avg"]))
    max_val = borough_avg["diff"].abs().max() if not borough_avg.empty else 1

    m = base_map()
    for borough in BOROUGHS:
        diff = diff_lookup.get(borough)
        avg = avg_lookup.get(borough)
        if diff is None:
            label = "No data"
            fill_val = None
        else:
            sign = "+" if diff >= 0 else ""
            label = f"{sign}{diff:.1f} µg/m³ vs London avg ({avg:.1f} µg/m³)"
            fill_val = abs(diff)

        popup = f"<b>{borough}</b><br>Pollutant: {pollutant_code}<br>{label}"
        if threshold and avg:
            status = "⚠️ Above WHO limit" if avg > threshold else "✅ Within WHO limit"
            popup += f"<br>WHO threshold: {threshold} µg/m³<br>{status}"

        add_borough_layer(m, borough, fill_val, max_val, label, popup)

    folium.LayerControl().add_to(m)
    st.subheader(f"{pollutant_code} — difference from London average ({london_avg:.1f} µg/m³)")
    st_folium(m, width=None, height=500, use_container_width=True)

    st.divider()
    st.subheader("📊 Difference from London Average")
    rows = []
    for borough in BOROUGHS:
        diff = diff_lookup.get(borough)
        avg = avg_lookup.get(borough)
        sign = "+" if diff and diff >= 0 else ""
        rows.append({
            "Borough": borough,
            "Borough Avg (µg/m³)": round(avg, 2) if avg else "No data",
            "London Avg (µg/m³)": round(london_avg, 2),
            "Difference": f"{sign}{diff:.2f}" if diff is not None else "No data",
        })
    st.dataframe(rows, use_container_width=True)

    with st.expander("ℹ️ About this view", expanded=False):
        st.markdown("""
        Each borough is shaded by how far its average concentration sits **above or below
        the overall London average** across all three boroughs. Darker shading means a larger
        deviation from the average — either above or below. This highlights relative hotspots
        rather than absolute values.
        """)


# ─────────────────────────── MAIN ──────────────────────────────────
def render_choropleth(measurements_df: pd.DataFrame, stations_df: pd.DataFrame):

    st.title("🗺️ Choropleth Map")

    # ─────────────────────────── SIDEBAR ───────────────────────────
    st.sidebar.header("🗺️ Choropleth Settings")

    mode = st.sidebar.radio(
        "View mode",
        [
            "🏔️ Peak reading",
            "🕐 Most polluted hour",
            "📅 Day-by-day",
            "📊 vs London average",
        ]
    )

    pollutant_label = st.sidebar.selectbox(
        "Pollutant", list(POLLUTANTS.keys()), index=0
    )
    pollutant_code = POLLUTANTS[pollutant_label]
    threshold = WHO_THRESHOLDS.get(pollutant_code)

    # ─────────────────────────── PREPARE ───────────────────────────
    df = prepare_df(measurements_df, stations_df)

    # ─────────────────────────── DISPATCH ──────────────────────────
    if mode == "🏔️ Peak reading":
        mode_peak(df, pollutant_code, threshold)
    elif mode == "🕐 Most polluted hour":
        mode_peak_hour(df, pollutant_code)
    elif mode == "📅 Day-by-day":
        mode_daily(df, pollutant_code, threshold)
    elif mode == "📊 vs London average":
        mode_vs_average(df, pollutant_code, threshold)