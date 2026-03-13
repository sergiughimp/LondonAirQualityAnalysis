import pandas as pd
import altair as alt
import streamlit as st

# ─────────────────────────── CONSTANTS ─────────────────────────────
POLLUTANTS = {
    "NO₂ — Nitrogen Dioxide":         "NO2",
    "PM2.5 — Particulate Matter 2.5": "PM25",
    "PM10 — Particulate Matter 10":   "PM10",
    "O₃ — Ozone":                     "O3",
    "SO₂ — Sulphur Dioxide":          "SO2",
    "CO — Carbon Monoxide":           "CO",
}

BOROUGH_COLOURS = {
    "Camden":        "#1f77b4",
    "Greenwich":     "#2ca02c",
    "Tower Hamlets": "#d62728",
}

BOROUGHS = ["Camden", "Greenwich", "Tower Hamlets"]

# ─────────────────────────── MAIN ──────────────────────────────────
def render_missing_data(measurements_df: pd.DataFrame):

    st.title("📉 Missing Data Analysis")
    st.write(
        "Explore where data gaps occur across stations, hours, and days. "
        "Missing readings affect the reliability of every other chart in this app — "
        "understanding where they occur is essential for interpreting the analysis correctly."
    )

    # ─────────────────────────── IMPACT ON ANALYSIS ────────────────
    with st.expander("⚠️ Impact of Missing Data on This App", expanded=True):
        st.markdown("""
        ### How missing data affects each page in this app

        - **📈 Time Series** — gaps appear as broken lines. Stations with many missing hours
        will show incomplete trends, making it harder to identify rush hour peaks accurately.

        - **🔥 Heatmap** — missing cells are excluded from hourly averages. If a station
        consistently misses readings at certain hours, the heatmap will underrepresent
        pollution at those times.

        - **🗺️ Choropleth** — peak and average values are calculated only from present readings.
        A borough with many missing readings may appear cleaner than it actually is,
        distorting the borough-level comparison.

        - **📦 Box Plot** — the IQR and median are computed from available readings only.
        Stations with sparse data will have wider, less reliable boxes that do not
        accurately reflect typical exposure levels.

        ### Common causes in this dataset
        - **Sensor calibration drift** — gradual degradation causing readings to drop to zero
        - **Temporary outages** — power or connectivity issues at the monitoring site
        - **Scheduled maintenance** — planned downtime at certain stations
        - **Detection limits** — pollutant concentrations below instrument sensitivity recorded as null

        > Stations with more than **20% missing data** should be treated with caution
        when drawing conclusions from any chart in this app.
        """)

    # ─────────────────────────── PREPARE DATA ──────────────────────
    df = measurements_df.copy()
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["measurement_date"] = pd.to_datetime(df["measurement_date"], errors="coerce")
    df["hour"] = df["measurement_date"].dt.hour
    df["date"] = df["measurement_date"].dt.date
    df["is_missing"] = df["value"].isna() | (df["value"] <= 0)

    # ─────────────────────────── SIDEBAR ───────────────────────────
    st.sidebar.header("📉 Missing Data Settings")

    pollutant_label = st.sidebar.selectbox(
        "Pollutant", list(POLLUTANTS.keys()), index=0
    )
    pollutant_code = POLLUTANTS[pollutant_label]

    borough_options = ["All boroughs"] + BOROUGHS
    borough_selection = st.sidebar.selectbox(
        "Filter by borough",
        borough_options,
        index=0,
    )
    borough_filter = BOROUGHS if borough_selection == "All boroughs" else [borough_selection]

    # filter to selected pollutant and borough
    filtered = df[
        (df["pollutant_code"] == pollutant_code) &
        (df["borough"].isin(borough_filter))
    ]

    if filtered.empty:
        st.warning("No data available for the selected combination.")
        return

    sorted_stations = sorted(filtered["station_name"].unique())

    # ─────────────────────────── 1. HEATMAP GRID ───────────────────
    st.divider()
    st.subheader("🟥 Missing Data Heatmap — Station vs Hour")

    heatmap_df = (
        filtered.groupby(["station_name", "hour"])["is_missing"]
        .mean()
        .reset_index()
    )
    heatmap_df.columns = ["station_name", "hour", "missing_rate"]
    heatmap_df["missing_pct"] = (heatmap_df["missing_rate"] * 100).round(1)

    heatmap = alt.Chart(heatmap_df).mark_rect().encode(
        x=alt.X(
            "hour:O",
            title="Hour of Day",
            axis=alt.Axis(labelAngle=0),
        ),
        y=alt.Y(
            "station_name:N",
            sort=sorted_stations,
            title="Station",
            axis=alt.Axis(labelLimit=0),
        ),
        color=alt.Color(
            "missing_pct:Q",
            title="% Missing",
            scale=alt.Scale(scheme="reds", domain=[0, 100]),
        ),
        tooltip=[
            alt.Tooltip("station_name:N", title="Station"),
            alt.Tooltip("hour:O",         title="Hour"),
            alt.Tooltip("missing_pct:Q",  title="% Missing", format=".1f"),
        ],
    ).properties(
        height=max(300, len(sorted_stations) * 25),
    )

    st.altair_chart(heatmap.interactive(), use_container_width=True)

    with st.expander("ℹ️ About this chart", expanded=False):
        st.markdown("""
        Each cell shows the **percentage of missing readings** for a station at a given hour.
        **Dark red** means most or all readings are missing at that hour.
        **White/light** means data is mostly present.

        Horizontal bands of red indicate a station was offline for extended periods.
        Vertical bands suggest a systematic gap at a specific time of day across multiple stations —
        which could indicate a network-wide collection issue rather than a single sensor fault.
        """)

    # ─────────────────────────── 2. BAR CHART ──────────────────────
    st.divider()
    st.subheader("📊 % Missing Readings per Station")

    bar_df = (
        filtered.groupby(["borough", "station_name"])["is_missing"]
        .mean()
        .reset_index()
    )
    bar_df.columns = ["borough", "station_name", "missing_rate"]
    bar_df["missing_pct"] = (bar_df["missing_rate"] * 100).round(1)
    bar_df["present_pct"] = 100 - bar_df["missing_pct"]

    colour_scale = alt.Scale(
        domain=list(BOROUGH_COLOURS.keys()),
        range=list(BOROUGH_COLOURS.values()),
    )

    bar = alt.Chart(bar_df).mark_bar().encode(
        x=alt.X(
            "missing_pct:Q",
            title="% Missing",
            scale=alt.Scale(domain=[0, 100]),
        ),
        y=alt.Y(
            "station_name:N",
            sort=alt.EncodingSortField(field="missing_pct", order="descending"),
            title="Station",
            axis=alt.Axis(labelLimit=0),
        ),
        color=alt.Color(
            "borough:N",
            scale=colour_scale,
            legend=alt.Legend(title="Borough"),
        ),
        tooltip=[
            alt.Tooltip("station_name:N", title="Station"),
            alt.Tooltip("borough:N",      title="Borough"),
            alt.Tooltip("missing_pct:Q",  title="% Missing", format=".1f"),
            alt.Tooltip("present_pct:Q",  title="% Present", format=".1f"),
        ],
    ).properties(
        height=max(300, len(sorted_stations) * 25),
    )

    st.altair_chart(bar.interactive(), use_container_width=True)

    with st.expander("ℹ️ About this chart", expanded=False):
        st.markdown("""
        Stations are ranked from **most to least missing data**.
        Colour shows which borough the station belongs to.

        A high missing percentage for a station means its readings should be treated with caution
        in the time series, heatmap, and box plot pages — averages and peaks will be based on
        fewer observations and may not represent the full picture.
        """)

    # ─────────────────────────── 3. TIMELINE ───────────────────────
    st.divider()
    st.subheader("📅 Missing Data Timeline — by Day")

    timeline_df = (
        filtered.groupby(["station_name", "date"])["is_missing"]
        .mean()
        .reset_index()
    )
    timeline_df.columns = ["station_name", "date", "missing_rate"]
    timeline_df["missing_pct"] = (timeline_df["missing_rate"] * 100).round(1)
    timeline_df["date_str"] = timeline_df["date"].astype(str)

    timeline = alt.Chart(timeline_df).mark_rect().encode(
        x=alt.X(
            "date_str:O",
            title="Date",
            axis=alt.Axis(labelAngle=-30),
        ),
        y=alt.Y(
            "station_name:N",
            sort=sorted_stations,
            title="Station",
            axis=alt.Axis(labelLimit=0),
        ),
        color=alt.Color(
            "missing_pct:Q",
            title="% Missing",
            scale=alt.Scale(scheme="reds", domain=[0, 100]),
        ),
        tooltip=[
            alt.Tooltip("station_name:N", title="Station"),
            alt.Tooltip("date_str:O",     title="Date"),
            alt.Tooltip("missing_pct:Q",  title="% Missing", format=".1f"),
        ],
    ).properties(
        height=max(300, len(sorted_stations) * 25),
    )

    st.altair_chart(timeline.interactive(), use_container_width=True)

    with st.expander("ℹ️ About this chart", expanded=False):
        st.markdown("""
        Each cell shows the **percentage of missing readings on a given day** for each station.
        This helps distinguish between:
        - **Random sensor faults** — isolated red cells on a single day for one station
        - **Prolonged outages** — a station showing red across multiple consecutive days
        - **Network-wide issues** — a full column of red affecting all stations on the same day

        Days with high missing rates will directly reduce the reliability of daily averages
        shown in the choropleth day-by-day view.
        """)

    # ─────────────────────────── 4. SUMMARY TABLE ──────────────────
    st.divider()
    st.subheader("📋 Missing Data Summary Table")

    summary = (
        filtered.groupby(["borough", "station_name"])
        .agg(
            Total=("value", "count"),
            Missing=("is_missing", "sum"),
        )
        .reset_index()
    )
    summary["Present"] = summary["Total"] - summary["Missing"]
    summary["% Missing"] = ((summary["Missing"] / summary["Total"]) * 100).round(1)
    summary["% Present"] = (100 - summary["% Missing"]).round(1)
    summary["Status"] = summary["% Missing"].apply(
        lambda x: "⚠️ High" if x > 20 else ("⚡ Moderate" if x > 5 else "✅ Good")
    )
    summary = summary.sort_values(["borough", "% Missing"], ascending=[True, False])
    summary.columns = [
        "Borough", "Station", "Total Readings",
        "Missing", "Present", "% Missing", "% Present", "Status",
    ]

    st.dataframe(summary, use_container_width=True)

    with st.expander("ℹ️ About this table", expanded=False):
        st.markdown("""
        - **✅ Good** — less than 5% missing, station data is reliable
        - **⚡ Moderate** — 5–20% missing, use with some caution
        - **⚠️ High** — more than 20% missing, conclusions from this station may be unreliable

        Total readings counts all rows for the station and pollutant combination.
        Missing includes both null values and zero readings, as zero concentrations
        are not physically meaningful for these pollutants in an urban environment.
        """)