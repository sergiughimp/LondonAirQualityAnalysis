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

# ─────────────────────────── MAIN ──────────────────────────────────
def render_box_plot(measurements_df: pd.DataFrame):

    st.title("📦 Box Plot")
    st.write(
        "Distribution of pollutant readings per station, grouped and colour-coded by borough. "
        "Each box shows the spread of hourly readings — median, interquartile range, and outliers."
    )

    # ─────────────────────────── PREPARE BASE DATA ─────────────────
    df = measurements_df.copy()
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # find top 3 pollutants by number of valid readings
    top_pollutants = (
        df[df["value"].notna() & (df["value"] > 0)]
        .groupby("pollutant_code")["value"]
        .count()
        .sort_values(ascending=False)
        .head(3)
        .index.tolist()
    )

    # filter POLLUTANTS dict to only top 3
    available_pollutants = {k: v for k, v in POLLUTANTS.items() if v in top_pollutants}

    # ─────────────────────────── SIDEBAR ───────────────────────────
    st.sidebar.header("📦 Box Plot Settings")

    pollutant_label = st.sidebar.selectbox(
        "Pollutant", list(available_pollutants.keys()), index=0
    )
    pollutant_code = available_pollutants[pollutant_label]
    threshold = WHO_THRESHOLDS.get(pollutant_code)

    borough_options = ["All boroughs"] + BOROUGHS
    borough_selection = st.sidebar.selectbox(
        "Filter by borough",
        borough_options,
        index=0,
    )
    borough_filter = BOROUGHS if borough_selection == "All boroughs" else [borough_selection]

    # ─────────────────────────── FILTER DATA ───────────────────────
    filtered = df[
        (df["pollutant_code"] == pollutant_code) &
        (df["value"].notna()) &
        (df["value"] > 0) &
        (df["borough"].isin(borough_filter))
    ]

    if filtered.empty:
        st.warning("No data available for the selected pollutant and borough combination.")
        return

    sorted_stations = sorted(filtered["station_name"].unique())

    # ─────────────────────────── COMPUTE STATS ─────────────────────
    stats_chart = (
        filtered.groupby(["borough", "station_name"])["value"]
        .describe(percentiles=[0.25, 0.5, 0.75])
        .reset_index()
    )
    stats_chart.columns = [
        "borough", "station_name", "count",
        "mean", "std", "min", "q1", "median", "q3", "max"
    ]

    # ─────────────────────────── BUILD CHART ───────────────────────
    colour_scale = alt.Scale(
        domain=list(BOROUGH_COLOURS.keys()),
        range=list(BOROUGH_COLOURS.values()),
    )

    # whisker — min to max
    whisker = alt.Chart(stats_chart).mark_rule(
        strokeWidth=1.5,
    ).encode(
        x=alt.X(
            "station_name:N",
            sort=sorted_stations,
            title=None,
            axis=alt.Axis(labelAngle=-45, labelLimit=0, labelOverlap=False),
        ),
        y=alt.Y("min:Q", title=f"{pollutant_code} concentration (µg/m³)"),
        y2=alt.Y2("max:Q"),
        color=alt.Color("borough:N", scale=colour_scale, legend=None),
    )

    # IQR box
    box = alt.Chart(stats_chart).mark_bar(
        size=20,
    ).encode(
        x=alt.X(
            "station_name:N",
            sort=sorted_stations,
            title="Station",
            axis=alt.Axis(labelAngle=-45, labelLimit=0, labelOverlap=False),
        ),
        y=alt.Y("q1:Q"),
        y2=alt.Y2("q3:Q"),
        color=alt.Color(
            "borough:N",
            scale=colour_scale,
            legend=alt.Legend(title="Borough"),
        ),
        tooltip=[
            alt.Tooltip("station_name:N", title="Station"),
            alt.Tooltip("borough:N",      title="Borough"),
            alt.Tooltip("min:Q",          title="Min",    format=".1f"),
            alt.Tooltip("q1:Q",           title="Q1",     format=".1f"),
            alt.Tooltip("median:Q",       title="Median", format=".1f"),
            alt.Tooltip("q3:Q",           title="Q3",     format=".1f"),
            alt.Tooltip("max:Q",          title="Max",    format=".1f"),
            alt.Tooltip("mean:Q",         title="Mean",   format=".1f"),
        ],
    )

    # median tick
    median_line = alt.Chart(stats_chart).mark_tick(
        color="white",
        thickness=2,
        size=20,
    ).encode(
        x=alt.X("station_name:N", sort=sorted_stations),
        y=alt.Y("median:Q"),
    )

    # WHO threshold line
    if threshold:
        who_line = alt.Chart(
            pd.DataFrame({"threshold": [threshold]})
        ).mark_rule(
            color="red",
            strokeDash=[6, 3],
            strokeWidth=1.5,
        ).encode(
            y=alt.Y("threshold:Q"),
        )

        who_label = alt.Chart(
            pd.DataFrame({
                "threshold": [threshold],
                "label": [f"WHO limit: {threshold} µg/m³"],
            })
        ).mark_text(
            align="left",
            dx=5,
            dy=-8,
            color="red",
            fontSize=11,
        ).encode(
            y=alt.Y("threshold:Q"),
            text=alt.Text("label:N"),
        )

        chart = (
            whisker + box + median_line + who_line + who_label
        ).properties(
            height=450,
            padding={"bottom": 120},
        )
    else:
        chart = (whisker + box + median_line).properties(
            height=450,
            padding={"bottom": 120},
        )

    st.altair_chart(chart.interactive(), use_container_width=True)

    # ─────────────────────────── SUMMARY TABLE ─────────────────────
    st.divider()
    st.subheader("📊 Station Statistics")

    stats = (
        filtered.groupby(["borough", "station_name"])["value"]
        .agg(
            Count="count",
            Min="min",
            Q1=lambda x: x.quantile(0.25),
            Median="median",
            Q3=lambda x: x.quantile(0.75),
            Max="max",
            Mean="mean",
            Std="std",
        )
        .round(2)
        .reset_index()
        .sort_values(["borough", "station_name"])
    )
    stats.columns = [
        "Borough", "Station", "Count",
        "Min", "Q1", "Median", "Q3", "Max", "Mean", "Std Dev",
    ]

    if threshold:
        stats["Above WHO"] = stats["Max"].apply(
            lambda x: "⚠️ Yes" if x > threshold else "✅ No"
        )

    st.dataframe(stats, use_container_width=True)

    with st.expander("ℹ️ About this chart", expanded=False):
        st.markdown("""
        Each box represents the **distribution of all hourly readings** for a single
        monitoring station. Stations are grouped and colour-coded by borough.
        Only the **3 pollutants with the most data** are available for selection.

        How to read the boxes:
        - **Middle white line** — median (50th percentile)
        - **Box edges** — Q1 (25th) and Q3 (75th) percentile — the interquartile range (IQR)
        - **Vertical line (whisker)** — extends from minimum to maximum recorded value

        The **red dashed line** marks the WHO guideline threshold for the selected pollutant.
        Any station whose whisker extends above this line has recorded at least one reading
        that exceeds the recommended safe limit.
        """)