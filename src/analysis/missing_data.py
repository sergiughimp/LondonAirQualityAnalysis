import pandas as pd
import altair as alt
import streamlit as st
from src.analysis.constants import POLLUTANTS, WHO_THRESHOLDS, BOROUGH_COLOURS, BOROUGHS

# ─────────────────────────── MAIN ──────────────────────────────────
def render_missing_data(measurements_df: pd.DataFrame):

    st.title("📉 Missing Data Analysis")
    st.markdown(
        """
        Explore where data gaps occur across stations, hours, and days.
        Missing readings affect the reliability of every other chart in this app —
        understanding where they occur is essential for interpreting the analysis correctly.
        """
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

        - **🏥 Health Impact** — WHO exceedance rates are based only on available readings.
        High missing rates may undercount the true number of hours that exceeded safe limits.

        - **📊 Correlation Analysis** — correlations are computed only where both pollutants
        have readings at the same time. Missing data reduces the sample size and may
        weaken or distort observed relationships.

        ### Common causes in this dataset
        - **Sensor calibration drift** — gradual degradation causing readings to drop to zero
        - **Temporary outages** — power or connectivity issues at the monitoring site
        - **Scheduled maintenance** — planned downtime at certain stations
        - **Detection limits** — pollutant concentrations below instrument sensitivity recorded as null

        > Stations with more than **20% missing data** should be treated with caution
        when drawing conclusions from any chart in this app.
        """)

    # ─────────────────────────── DATA PREP ─────────────────────────
    df = measurements_df.copy()
    df.columns             = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df["value"]            = pd.to_numeric(df["value"], errors="coerce")
    df["measurement_date"] = pd.to_datetime(df["measurement_date"], errors="coerce")
    df["hour"]             = df["measurement_date"].dt.hour
    df["date"]             = df["measurement_date"].dt.date
    df["is_missing"]       = df["value"].isna() | (df["value"] <= 0)

    # ─────────────────────────── SIDEBAR ───────────────────────────
    st.sidebar.header("📉 Missing Data Settings")

    pollutant_label = st.sidebar.selectbox(
        "Pollutant", list(POLLUTANTS.keys()), index=0
    )
    pollutant_code = POLLUTANTS[pollutant_label]

    borough_options   = ["All boroughs"] + BOROUGHS
    borough_selection = st.sidebar.selectbox(
        "Filter by borough", borough_options, index=0
    )
    borough_filter = BOROUGHS if borough_selection == "All boroughs" else [borough_selection]

    # ─────────────────────────── FILTER DATA ───────────────────────
    filtered = df[
        (df["pollutant_code"] == pollutant_code) &
        (df["borough"].isin(borough_filter))
    ]

    if filtered.empty:
        st.warning("⚠️ No data available for the selected combination.")
        return

    sorted_stations = sorted(filtered["station_name"].unique())

    # ─────────────────────────── HEATMAP GRID ──────────────────────
    st.divider()
    st.subheader("🟥 Missing Data Heatmap — Station vs Hour")
    st.caption(
        "Each cell shows the percentage of missing readings for a station at a given hour. "
        "Dark red indicates most or all readings are missing — white or light cells mean data is mostly present."
    )

    heatmap_df = (
        filtered.groupby(["station_name", "hour"])["is_missing"]
        .mean()
        .reset_index()
    )
    heatmap_df.columns        = ["station_name", "hour", "missing_rate"]
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
        **How to read this heatmap:**
        - Each **row** represents a monitoring station
        - Each **column** represents an hour of the day (00:00 to 23:00)
        - **Dark red cells** — most or all readings are missing at that station and hour
        - **White or light cells** — data is mostly present

        **Interpretation guidance:**
        - **Horizontal bands of red** indicate a station was offline for extended periods —
        likely a sensor outage or scheduled maintenance
        - **Vertical bands of red** suggest a systematic gap at a specific time of day
        across multiple stations — which may indicate a network-wide data collection issue
        rather than a single sensor fault
        - Gaps in this heatmap directly correspond to missing lines in the
        **📈 Time Series** page
        """)

    # ─────────────────────────── BAR CHART ─────────────────────────
    st.divider()
    st.subheader("📊 % Missing Readings per Station")
    st.caption(
        "Stations ranked from most to least missing data. "
        "Colour indicates the borough each station belongs to."
    )

    bar_df = (
        filtered.groupby(["borough", "station_name"])["is_missing"]
        .mean()
        .reset_index()
    )
    bar_df.columns        = ["borough", "station_name", "missing_rate"]
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
            alt.Tooltip("missing_pct:Q",  title="% Missing",  format=".1f"),
            alt.Tooltip("present_pct:Q",  title="% Present",  format=".1f"),
        ],
    ).properties(
        height=max(300, len(sorted_stations) * 25),
    )

    st.altair_chart(bar.interactive(), use_container_width=True)

    with st.expander("ℹ️ About this chart", expanded=False):
        st.markdown("""
        **How to read this chart:**
        - Each **bar** represents a monitoring station ranked by its missing data rate
        - **Longer bars** mean more missing readings for the selected pollutant
        - **Colour** indicates the borough the station belongs to

        **Interpretation guidance:**
        - Stations with high missing rates should be treated with caution across all
        analysis pages — averages, peaks, and correlations will be based on fewer
        observations and may not represent the full pollution picture
        - If multiple stations from the same borough show high missing rates,
        it may indicate a borough-wide data collection issue during the monitoring period
        """)

    # ─────────────────────────── TIMELINE ──────────────────────────
    st.divider()
    st.subheader("📅 Missing Data Timeline — by Day")
    st.caption(
        "Each cell shows the percentage of missing readings on a given day for each station. "
        "Use this to distinguish between random sensor faults, prolonged outages, and network-wide issues."
    )

    timeline_df = (
        filtered.groupby(["station_name", "date"])["is_missing"]
        .mean()
        .reset_index()
    )
    timeline_df.columns        = ["station_name", "date", "missing_rate"]
    timeline_df["missing_pct"] = (timeline_df["missing_rate"] * 100).round(1)
    timeline_df["date_str"]    = timeline_df["date"].astype(str)

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
        **How to read this chart:**
        - Each **row** represents a monitoring station
        - Each **column** represents a day in the dataset
        - **Dark red cells** — high percentage of missing readings on that day
        - **White or light cells** — data is mostly present on that day

        **Interpretation guidance:**
        - **Isolated red cells** — random sensor faults on a single day for one station
        - **Horizontal red bands** — prolonged outages affecting a station across
        multiple consecutive days
        - **Vertical red columns** — network-wide issues affecting all stations on
        the same day, possibly due to API or data collection failures
        - Days with high missing rates directly reduce the reliability of daily averages
        shown in the **🗺️ Choropleth** day-by-day view
        """)

    # ─────────────────────────── SUMMARY TABLE ─────────────────────
    st.divider()
    st.subheader("📋 Missing Data Summary Table")
    st.caption(
        "Complete breakdown of total, missing, and present readings per station "
        "for the selected pollutant. Status flags stations that may produce unreliable results."
    )

    summary = (
        filtered.groupby(["borough", "station_name"])
        .agg(
            Total=("value", "count"),
            Missing=("is_missing", "sum"),
        )
        .reset_index()
    )
    summary["Present"]   = summary["Total"] - summary["Missing"]
    summary["% Missing"] = ((summary["Missing"] / summary["Total"]) * 100).round(1)
    summary["% Present"] = (100 - summary["% Missing"]).round(1)
    summary["Status"]    = summary["% Missing"].apply(
        lambda x: "⚠️ High" if x > 20 else ("⚡ Moderate" if x > 5 else "✅ Good")
    )
    summary = summary.sort_values(["borough", "% Missing"], ascending=[True, False])
    summary.columns = [
        "Borough", "Station", "Total Readings",
        "Missing", "Present", "% Missing", "% Present", "Status",
    ]

    st.dataframe(
        summary.drop(columns=["Borough"]),
        use_container_width=True,
    )

    with st.expander("ℹ️ About this table", expanded=False):
        st.markdown("""
        **Status flags explained:**
        | Status | Threshold | Meaning |
        |---|---|---|
        | ✅ Good | < 5% missing | Station data is reliable for analysis |
        | ⚡ Moderate | 5–20% missing | Use with some caution — gaps may affect averages |
        | ⚠️ High | > 20% missing | Conclusions from this station may be unreliable |

        **Column definitions:**
        - **Total Readings** — all rows recorded for this station and pollutant combination
        - **Missing** — readings that are null or zero (zero concentrations are not
        physically meaningful for these pollutants in an urban environment)
        - **Present** — valid readings available for analysis
        - **% Missing / % Present** — proportion of the total readings in each category
        """)