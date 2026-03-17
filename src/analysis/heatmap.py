import altair as alt
import pandas as pd
import streamlit as st
from src.analysis.constants import POLLUTANTS, WHO_THRESHOLDS, BOROUGH_COLOURS, BOROUGHS

# ─────────────────────────── MAIN ──────────────────────────────────
def render_heatmap(df: pd.DataFrame):

    st.title("🔥 Pollution Heatmap")
    st.markdown(
        """
        Explore average pollutant concentrations across monitoring stations and hours of the day.
        Each cell represents the mean reading for a given station and hour —
        darker cells indicate higher pollution levels. Charts are split by day for accurate comparison.
        """
    )

    # ─────────────────────────── DATA PREP ─────────────────────────
    df = df.copy()
    df.columns             = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df["measurement_date"] = pd.to_datetime(df["measurement_date"], errors="coerce")
    df["value"]            = pd.to_numeric(df["value"], errors="coerce")
    df["hour"]             = df["measurement_date"].dt.hour
    df["date"]             = df["measurement_date"].dt.date.astype(str)

    # ─────────────────────────── SIDEBAR ───────────────────────────
    st.sidebar.header("🔥 Heatmap Settings")

    selected_pollutant_label = st.sidebar.selectbox(
        "Pollutant", list(POLLUTANTS.keys()), index=0
    )
    selected_pollutant_code = POLLUTANTS[selected_pollutant_label]
    threshold               = WHO_THRESHOLDS.get(selected_pollutant_code)

    boroughs         = ["All boroughs"] + sorted(df["borough"].dropna().unique().tolist())
    selected_borough = st.sidebar.selectbox("Filter by borough", boroughs, index=0)

    # ─────────────────────────── FILTER DATA ───────────────────────
    filtered = df[df["pollutant_code"] == selected_pollutant_code].copy()
    filtered = filtered.dropna(subset=["value"])
    filtered = filtered[filtered["value"] > 0]

    if selected_borough != "All boroughs":
        filtered = filtered[filtered["borough"] == selected_borough]

    if filtered.empty:
        st.warning(
            f"⚠️ No data available for **{selected_pollutant_label}** "
            f"in the selected borough. Try a different combination."
        )
        return

    sorted_stations = sorted(filtered["station_name"].dropna().unique().tolist())
    pollutant_short = selected_pollutant_label.split(" — ")[0]

    # ─────────────────────────── AGGREGATE ─────────────────────────
    heatmap_df = (
        filtered.groupby(["station_name", "hour", "date"])["value"]
        .mean()
        .round(2)
        .reset_index()
        .rename(columns={"value": "avg_value"})
    )

    # ─────────────────────────── HEATMAP CHARTS ────────────────────
    dates = sorted(heatmap_df["date"].unique().tolist())

    for day in dates:
        day_df = heatmap_df[heatmap_df["date"] == day]

        chart = alt.Chart(day_df).mark_rect().encode(
            x=alt.X(
                "hour:O",
                title="Hour of Day",
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y(
                "station_name:N",
                title="Station",
                sort=sorted_stations,
                axis=alt.Axis(labelLimit=0),
            ),
            color=alt.Color(
                "avg_value:Q",
                title=f"Avg {pollutant_short} (µg/m³)",
                scale=alt.Scale(scheme="orangered"),
                legend=alt.Legend(labelLimit=300),
            ),
            tooltip=[
                alt.Tooltip("station_name:N", title="Station"),
                alt.Tooltip("hour:O",          title="Hour"),
                alt.Tooltip("avg_value:Q",     title=f"Avg {pollutant_short} (µg/m³)", format=".2f"),
            ],
        ).properties(
            width="container",
            height=max(300, len(sorted_stations) * 25),
            title=f"{pollutant_short} Average Concentration — {day}",
        )

        st.altair_chart(chart, use_container_width=True)

    with st.expander("ℹ️ About this chart", expanded=False):
        st.markdown(f"""
        **How to read this heatmap:**
        - Each **row** represents a monitoring station
        - Each **column** represents an hour of the day (00:00 to 23:00)
        - Each **cell colour** shows the average {pollutant_short} concentration
        recorded at that station during that hour across all days shown
        - **Darker red cells** indicate higher average pollution levels
        - **Light or white cells** indicate low or near-zero concentrations

        **Interpretation guidance:**
        - Columns that are consistently dark across multiple stations suggest
        a time of day with elevated pollution network-wide — often linked to
        rush hour traffic or overnight industrial activity
        - Rows that are consistently dark indicate stations with persistently
        high pollution regardless of time — typically roadside sites near busy corridors
        - Gaps or blank cells indicate missing data — see the
        **📉 Missing Data** page for a full data quality analysis
        {f'- The WHO guideline for {pollutant_short} is **{threshold} µg/m³** — cells significantly above this value represent hours of unsafe air quality' if threshold else ''}
        """)

    # ─────────────────────────── SUMMARY TABLE ─────────────────────
    st.divider()
    st.subheader(f"📊 Average {pollutant_short} by Station")
    st.caption(
        f"Mean concentration of **{pollutant_short}** across all valid hourly readings "
        f"for each monitoring station in the selected view."
        + (f" WHO guideline: **{threshold} µg/m³**." if threshold else "")
    )

    summary = (
        filtered.groupby(["borough", "station_name"])["value"]
        .agg(
            Average="mean",
            Peak="max",
            Min="min",
            Readings="count",
        )
        .round(2)
        .reset_index()
        .rename(columns={
            "borough":      "Borough",
            "station_name": "Station",
            "Average":      "Average (µg/m³)",
            "Peak":         "Peak (µg/m³)",
            "Min":          "Min (µg/m³)",
        })
        .sort_values(["Borough", "Station"])
        .drop(columns=["Borough"])
    )

    if threshold:
        summary["Above WHO"] = summary["Peak (µg/m³)"].apply(
            lambda x: "⚠️ Yes" if x > threshold else "✅ No"
        )

    st.dataframe(summary, use_container_width=True)

    with st.expander("ℹ️ About this table", expanded=False):
        st.markdown(f"""
        - **Average** — mean concentration across all valid hourly readings for this station
        - **Peak** — the single highest hourly reading recorded for this station
        - **Min** — the lowest valid hourly reading recorded
        - **Readings** — total number of valid hourly readings included in the summary
        {f'- **Above WHO** — flags stations where the peak reading exceeded the WHO guideline of **{threshold} µg/m³** for {pollutant_short}' if threshold else ''}

        Stations marked **⚠️ Yes** recorded at least one hour where pollution
        exceeded the recommended safe limit — indicating a potential health risk
        for residents and commuters near that location.
        """ if threshold else """
        - **Average** — mean concentration across all valid hourly readings for this station
        - **Peak** — the single highest hourly reading recorded for this station
        - **Min** — the lowest valid hourly reading recorded
        - **Readings** — total number of valid hourly readings included in the summary
        """)