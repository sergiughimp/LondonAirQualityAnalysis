import altair as alt
import pandas as pd
import streamlit as st
from src.analysis.constants import POLLUTANTS, WHO_THRESHOLDS, BOROUGH_COLOURS, BOROUGHS

# ─────────────────────────── MAIN ──────────────────────────────────
def render_time_series(df: pd.DataFrame):

    st.title("📈 Hourly Pollutant Time Series")
    st.markdown(
        """
        Track how pollutant concentrations change hour by hour across monitoring stations.
        Rush hour bands highlight morning and evening traffic peaks, and the
        **WHO annual guideline threshold** is overlaid for direct health context.
        """
    )

    # ─────────────────────────── DATA PREP ─────────────────────────
    df = df.copy()
    df.columns          = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df["measurement_date"] = pd.to_datetime(df["measurement_date"], errors="coerce")
    df["value"]            = pd.to_numeric(df["value"], errors="coerce")

    # ─────────────────────────── SIDEBAR ───────────────────────────
    st.sidebar.header("📈 Time Series Settings")

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

    # ─────────────────────────── RUSH HOUR BANDS ───────────────────
    dates      = filtered["measurement_date"].dt.normalize().unique()
    rush_bands = []
    for date in dates:
        rush_bands.append({
            "start": pd.Timestamp(date) + pd.Timedelta(hours=7),
            "end":   pd.Timestamp(date) + pd.Timedelta(hours=9),
            "label": "Morning rush",
        })
        rush_bands.append({
            "start": pd.Timestamp(date) + pd.Timedelta(hours=17),
            "end":   pd.Timestamp(date) + pd.Timedelta(hours=19),
            "label": "Evening rush",
        })
    rush_df = pd.DataFrame(rush_bands)

    # ─────────────────────────── BUILD CHART ───────────────────────
    bands = alt.Chart(rush_df).mark_rect(
        opacity=0.12, color="#FFA500"
    ).encode(
        x=alt.X("start:T"),
        x2=alt.X2("end:T"),
        tooltip=[alt.Tooltip("label:N", title="Period")],
    )

    line = alt.Chart(filtered).mark_line(point=True).encode(
        x=alt.X(
            "measurement_date:T",
            title="Date / Time",
        ),
        y=alt.Y(
            "value:Q",
            title=f"{pollutant_short} concentration (µg/m³)",
        ),
        color=alt.Color(
            "station_name:N",
            title="Station",
            sort=sorted_stations,
            legend=alt.Legend(labelLimit=300),
        ),
        tooltip=[
            alt.Tooltip("station_name:N",    title="Station"),
            alt.Tooltip("borough:N",          title="Borough"),
            alt.Tooltip("measurement_date:T", title="Time"),
            alt.Tooltip("value:Q",            title=f"{pollutant_short} (µg/m³)", format=".1f"),
        ],
    )

    chart = bands + line

    if threshold:
        who_df = pd.DataFrame([{"threshold": threshold}])

        who_line = alt.Chart(who_df).mark_rule(
            color="red", strokeDash=[6, 4], strokeWidth=1.5
        ).encode(
            y=alt.Y("threshold:Q"),
        )

        who_label = alt.Chart(who_df).mark_text(
            align="left", dx=4, dy=-6, color="red", fontSize=11
        ).encode(
            y=alt.Y("threshold:Q"),
            text=alt.value(f"WHO guideline: {threshold} µg/m³"),
        )

        chart = bands + who_line + who_label + line

    chart = chart.properties(
        width="container",
        height=450,
        title=f"Hourly {pollutant_short} Concentrations — Rush Hour Bands and WHO Threshold",
    ).interactive()

    st.altair_chart(chart, use_container_width=True)

    with st.expander("ℹ️ About this chart", expanded=False):
        st.markdown(f"""
        **How to read this chart:**
        - Each **coloured line** represents a single monitoring station
        - **Orange shaded bands** mark morning (07:00–09:00) and evening (17:00–19:00)
        rush hours — periods of typically elevated road traffic emissions
        - The **red dashed line** marks the WHO annual mean guideline for
        {pollutant_short} at **{threshold} µg/m³** — any readings above this line
        indicate concentrations that exceed recommended safe limits

        **Interpretation guidance:**
        - Stations that consistently peak during rush hour bands are likely
        capturing direct traffic emissions — typically roadside sites
        - Stations with elevated readings outside rush hours may reflect
        industrial sources, background pollution, or data anomalies
        - Gaps in lines indicate missing or invalid readings — see the
        **📉 Missing Data** page for a full data quality analysis
        """ if threshold else """
        **How to read this chart:**
        - Each **coloured line** represents a single monitoring station
        - **Orange shaded bands** mark morning (07:00–09:00) and evening (17:00–19:00)
        rush hours — periods of typically elevated road traffic emissions

        **Interpretation guidance:**
        - Stations that consistently peak during rush hour bands are likely
        capturing direct traffic emissions — typically roadside sites
        - Gaps in lines indicate missing or invalid readings — see the
        **📉 Missing Data** page for a full data quality analysis
        """)

    # ─────────────────────────── SUMMARY TABLE ─────────────────────
    st.divider()
    st.subheader(f"📊 Peak {pollutant_short} Readings by Station")
    st.caption(
        f"Summary statistics for **{pollutant_short}** across all monitoring stations "
        f"in the selected view. Peak readings above the WHO threshold of "
        f"**{threshold} µg/m³** are flagged."
        if threshold else
        f"Summary statistics for **{pollutant_short}** across all monitoring stations."
    )

    summary = (
        filtered.groupby(["borough", "station_name"])["value"]
        .agg(
            Peak="max",
            Average="mean",
            Min="min",
            Readings="count",
        )
        .round(2)
        .reset_index()
        .rename(columns={
            "borough":      "Borough",
            "station_name": "Station",
            "Peak":         "Peak (µg/m³)",
            "Average":      "Average (µg/m³)",
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
        - **Peak** — the single highest hourly reading recorded for this station
        - **Average** — mean concentration across all valid hourly readings
        - **Min** — the lowest valid hourly reading recorded
        - **Readings** — total number of valid hourly readings included in the summary
        {f'- **Above WHO** — flags stations where the peak reading exceeded the WHO guideline of **{threshold} µg/m³** for {pollutant_short}' if threshold else ''}

        Stations marked **⚠️ Yes** recorded at least one hour where pollution
        exceeded the recommended safe limit — indicating a potential health risk
        for residents and commuters near that location.
        """ if threshold else """
        - **Peak** — the single highest hourly reading recorded for this station
        - **Average** — mean concentration across all valid hourly readings
        - **Min** — the lowest valid hourly reading recorded
        - **Readings** — total number of valid hourly readings included in the summary
        """)