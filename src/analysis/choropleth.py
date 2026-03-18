from pathlib import Path
import json

import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
from src.analysis.constants import POLLUTANTS, WHO_THRESHOLDS, BOROUGH_COLOURS, BOROUGHS
from src.analysis.common import sidebar_pollutant_selector

# ─────────────────────────── FILE PATHS ────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[2]

GEO_FILES = {
    "Camden":        BASE_DIR / "data" / "geo" / "camden.json",
    "Greenwich":     BASE_DIR / "data" / "geo" / "greenwich.json",
    "Tower Hamlets": BASE_DIR / "data" / "geo" / "tower_hamlets.json",
}

# ─────────────────────────── HELPERS ───────────────────────────────
def load_geo(borough):
    path = GEO_FILES[borough]
    if not path.exists():
        st.warning(f"⚠️ GeoJSON boundary file not found for {borough}.")
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def base_map():
    return folium.Map(location=[51.509, -0.118], zoom_start=11, tiles="CartoDB positron")

def filter_df(df, pollutant_code):
    return df[(df["pollutant_code"] == pollutant_code) & (df["value"] > 0) & df["value"].notna()]

def who_status(val, threshold):
    if val and threshold:
        return "⚠️ Above" if val > threshold else "✅ Within"
    return "N/A"

def who_popup_suffix(val, threshold):
    if threshold and val:
        status = "⚠️ Above WHO limit" if val > threshold else "✅ Within WHO limit"
        return f"<br>WHO threshold: {threshold} µg/m³<br>{status}"
    return ""

def who_note(pollutant_code, threshold):
    return f"\n- WHO guideline for {pollutant_code}: **{threshold} µg/m³**" if threshold else ""

def render_map_section(m, title, about_markdown):
    folium.LayerControl().add_to(m)
    st.subheader(title)
    st_folium(m, width=None, height=500, use_container_width=True)
    with st.expander("ℹ️ About this view", expanded=False):
        st.markdown(about_markdown)

def render_table_header(title, caption):
    st.divider()
    st.subheader(title)
    st.caption(caption)

def add_borough_layer(m, borough, value, max_val, label, popup_html):
    geo_data = load_geo(borough)
    if geo_data is None:
        return

    if value is None:
        fill_colour  = "#cccccc"
        fill_opacity = 0.3
    else:
        normalised   = value / max_val if max_val else 0
        fill_opacity = 0.15 + normalised * 0.70
        fill_colour  = BOROUGH_COLOURS[borough]

    folium.GeoJson(
        geo_data,
        name=borough,
        style_function=lambda feature, fc=fill_colour, fo=fill_opacity: {
            "fillColor":   fc,
            "color":       fc,
            "weight":      2,
            "fillOpacity": fo,
        },
        tooltip=f"{borough}: {label}",
        popup=folium.Popup(popup_html, max_width=240),
    ).add_to(m)

def prepare_df(measurements_df, stations_df):
    # Note: not replaced by prepare_measurements() — this file needs to merge
    # stations for borough info and adds hour/date columns specific to choropleth
    df  = measurements_df.copy()
    sdf = stations_df.copy()

    df.columns  = df.columns.str.strip().str.lower().str.replace(" ", "_")
    sdf.columns = sdf.columns.str.strip().str.lower().str.replace(" ", "_")

    if "borough" not in df.columns:
        df = df.merge(sdf[["station_name", "borough"]], on="station_name", how="left")

    df["value"]            = pd.to_numeric(df["value"], errors="coerce")
    df["measurement_date"] = pd.to_datetime(df["measurement_date"], errors="coerce")
    df["hour"]             = df["measurement_date"].dt.hour
    df["date"]             = df["measurement_date"].dt.date
    return df

# ─────────────────────────── VIEW MODES ────────────────────────────
def mode_peak(df, pollutant_code, threshold):
    filtered    = filter_df(df, pollutant_code)
    peak_df     = filtered.groupby("borough")["value"].max().reset_index().rename(columns={"value": "peak"})
    peak_lookup = dict(zip(peak_df["borough"], peak_df["peak"]))
    max_val     = peak_df["peak"].max() if not peak_df.empty else 1

    m = base_map()
    for borough in BOROUGHS:
        val   = peak_lookup.get(borough)
        label = f"{val:.1f} µg/m³" if val else "No data"
        popup = f"<b>{borough}</b><br>Pollutant: {pollutant_code}<br>Peak: {label}" + who_popup_suffix(val, threshold)
        add_borough_layer(m, borough, val, max_val, label, popup)

    render_map_section(m, f"📍 Peak {pollutant_code} Concentration by Borough", f"""
        Each borough is shaded by its **single highest recorded reading** for the selected pollutant.
        A darker shade means a higher peak concentration — grey indicates no data was recorded.

        Peak readings reflect worst-case exposure moments across the dataset.
        Compare against the WHO guideline threshold in the summary table below
        to identify where safe limits were exceeded.{who_note(pollutant_code, threshold)}
    """)

    render_table_header(
        "📊 Peak Readings Summary",
        f"Highest recorded {pollutant_code} concentration per borough across the full dataset."
        + (f" WHO guideline: **{threshold} µg/m³**." if threshold else ""),
    )
    st.dataframe([
        {
            "Borough":               borough,
            "Peak Reading (µg/m³)":  round(val, 2) if (val := peak_lookup.get(borough)) else "No data",
            "WHO Threshold (µg/m³)": threshold or "N/A",
            "Status":                who_status(val, threshold),
        }
        for borough in BOROUGHS
    ], use_container_width=True)


def mode_peak_hour(df, pollutant_code):
    filtered         = filter_df(df, pollutant_code)
    hour_df          = filtered.groupby(["borough", "hour"])["value"].mean().reset_index()
    peak_hour_df     = hour_df.loc[hour_df.groupby("borough")["value"].idxmax()]
    peak_hour_lookup = dict(zip(peak_hour_df["borough"], peak_hour_df["hour"]))
    peak_val_lookup  = dict(zip(peak_hour_df["borough"], peak_hour_df["value"]))
    max_val          = peak_hour_df["value"].max() if not peak_hour_df.empty else 1

    m = base_map()
    for borough in BOROUGHS:
        hour  = peak_hour_lookup.get(borough)
        val   = peak_val_lookup.get(borough)
        label = f"{int(hour):02d}:00 (avg {val:.1f} µg/m³)" if hour is not None else "No data"
        popup = f"<b>{borough}</b><br>Pollutant: {pollutant_code}<br>Peak hour: {label}"
        add_borough_layer(m, borough, val, max_val, label, popup)

    render_map_section(m, f"📍 Most Polluted Hour of Day — {pollutant_code}", f"""
        Each borough is shaded by the **hour of day with the highest average {pollutant_code} concentration**.
        Darker shading means the peak hour had a higher average reading across all stations in that borough.

        This view is useful for identifying whether pollution peaks align with
        morning or evening rush hours — or whether elevated readings occur at
        unexpected times, which may indicate industrial or non-traffic sources.
    """)

    render_table_header(
        "📊 Peak Hour Summary",
        f"The hour of day with the highest average {pollutant_code} concentration per borough, "
        f"based on readings across all stations and all days in the dataset.",
    )
    st.dataframe([
        {
            "Borough":                   borough,
            "Peak Hour":                 f"{int(hour):02d}:00" if (hour := peak_hour_lookup.get(borough)) is not None else "No data",
            "Avg Concentration (µg/m³)": round(val, 2) if (val := peak_val_lookup.get(borough)) else "No data",
        }
        for borough in BOROUGHS
    ], use_container_width=True)


def mode_daily(df, pollutant_code, threshold):
    filtered        = filter_df(df, pollutant_code)
    available_dates = sorted(filtered["date"].dropna().unique())

    if not available_dates:
        st.warning("⚠️ No data available for this pollutant.")
        return

    selected_date = st.sidebar.select_slider(
        "Select date",
        options=available_dates,
        format_func=lambda d: d.strftime("%d %b %Y"),
    )

    day_df       = filtered[filtered["date"] == selected_date]
    daily_df     = day_df.groupby("borough")["value"].mean().reset_index().rename(columns={"value": "avg"})
    daily_lookup = dict(zip(daily_df["borough"], daily_df["avg"]))
    max_val      = daily_df["avg"].max() if not daily_df.empty else 1

    m = base_map()
    for borough in BOROUGHS:
        val   = daily_lookup.get(borough)
        label = f"{val:.1f} µg/m³" if val else "No data"
        popup = (
            f"<b>{borough}</b><br>Pollutant: {pollutant_code}<br>"
            f"Date: {selected_date}<br>Avg: {label}"
            + who_popup_suffix(val, threshold)
        )
        add_borough_layer(m, borough, val, max_val, label, popup)

    date_str = selected_date.strftime("%d %b %Y")
    render_map_section(m, f"📍 {pollutant_code} Daily Average — {date_str}", f"""
        Each borough is shaded by its **average {pollutant_code} concentration on the selected day**.
        Use the date slider in the sidebar to step through the dataset day by day.

        Darker shading means a higher daily average. Comparing days can reveal
        how pollution levels shift across the monitoring period — for example,
        whether weekday traffic patterns produce higher readings than quieter days.{who_note(pollutant_code, threshold)}
    """)

    render_table_header(
        "📊 Daily Average Summary",
        f"Average {pollutant_code} concentration per borough on {date_str}."
        + (f" WHO guideline: **{threshold} µg/m³**." if threshold else ""),
    )
    st.dataframe([
        {
            "Borough":               borough,
            "Daily Avg (µg/m³)":     round(val, 2) if (val := daily_lookup.get(borough)) else "No data",
            "WHO Threshold (µg/m³)": threshold or "N/A",
            "Status":                who_status(val, threshold),
        }
        for borough in BOROUGHS
    ], use_container_width=True)


def mode_vs_average(df, pollutant_code, threshold):
    filtered    = filter_df(df, pollutant_code)
    london_avg  = filtered["value"].mean()
    borough_avg = filtered.groupby("borough")["value"].mean().reset_index().rename(columns={"value": "avg"})
    borough_avg["diff"] = borough_avg["avg"] - london_avg
    diff_lookup = dict(zip(borough_avg["borough"], borough_avg["diff"]))
    avg_lookup  = dict(zip(borough_avg["borough"], borough_avg["avg"]))
    max_val     = borough_avg["diff"].abs().max() if not borough_avg.empty else 1

    m = base_map()
    for borough in BOROUGHS:
        diff = diff_lookup.get(borough)
        avg  = avg_lookup.get(borough)
        if diff is None:
            label    = "No data"
            fill_val = None
        else:
            sign     = "+" if diff >= 0 else ""
            label    = f"{sign}{diff:.1f} µg/m³ vs London avg ({avg:.1f} µg/m³)"
            fill_val = abs(diff)

        popup = f"<b>{borough}</b><br>Pollutant: {pollutant_code}<br>{label}" + who_popup_suffix(avg, threshold)
        add_borough_layer(m, borough, fill_val, max_val, label, popup)

    render_map_section(m, f"📍 {pollutant_code} — Difference from London Average ({london_avg:.1f} µg/m³)", f"""
        Each borough is shaded by how far its average {pollutant_code} concentration sits
        **above or below the overall London average** across all three boroughs
        ({london_avg:.1f} µg/m³).

        Darker shading means a larger deviation from the average — highlighting relative
        hotspots rather than absolute values. This is useful for identifying which borough
        is disproportionately affected compared to its neighbours.{who_note(pollutant_code, threshold)}
    """)

    render_table_header(
        "📊 Difference from London Average",
        f"How each borough's average {pollutant_code} concentration compares to the "
        f"overall London average of **{london_avg:.1f} µg/m³** across all three boroughs.",
    )
    st.dataframe([
        {
            "Borough":             borough,
            "Borough Avg (µg/m³)": round(avg, 2) if (avg := avg_lookup.get(borough)) else "No data",
            "London Avg (µg/m³)":  round(london_avg, 2),
            "Difference":          f"{'+'if (diff := diff_lookup.get(borough)) and diff >= 0 else ''}{diff:.2f}" if diff is not None else "No data",
        }
        for borough in BOROUGHS
    ], use_container_width=True)


# ─────────────────────────── MAIN ──────────────────────────────────
def render_choropleth(measurements_df: pd.DataFrame, stations_df: pd.DataFrame):

    st.title("🗺️ Choropleth Map")
    st.markdown(
        """
        Explore borough-level air quality patterns through four different analytical views.
        Each borough is shaded based on the selected metric — darker colours indicate
        higher pollution levels or greater deviation from the average.
        Use the sidebar to switch between views and select a pollutant.
        """
    )

    st.sidebar.header("🗺️ Choropleth Settings")

    mode = st.sidebar.radio(
        "View mode",
        ["🏔️ Peak reading", "🕐 Most polluted hour", "📅 Day-by-day", "📊 vs London average"],
    )

    pollutant_label, pollutant_code, threshold = sidebar_pollutant_selector()

    df = prepare_df(measurements_df, stations_df)

    if mode == "🏔️ Peak reading":
        mode_peak(df, pollutant_code, threshold)
    elif mode == "🕐 Most polluted hour":
        mode_peak_hour(df, pollutant_code)
    elif mode == "📅 Day-by-day":
        mode_daily(df, pollutant_code, threshold)
    elif mode == "📊 vs London average":
        mode_vs_average(df, pollutant_code, threshold)