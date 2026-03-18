import pandas as pd
import altair as alt
import streamlit as st
from src.analysis.constants import POLLUTANTS, WHO_THRESHOLDS, BOROUGH_COLOURS, BOROUGHS
from src.analysis.common import prepare_measurements, sidebar_borough_filter

# ─────────────────────────── MAIN ──────────────────────────────────
def render_box_plot(measurements_df: pd.DataFrame):

    st.title("📦 Box Plot")
    st.write(
        "Distribution of pollutant readings per station, grouped and colour-coded by borough. "
        "Each box shows the spread of hourly readings — median, interquartile range, and outliers."
    )

    # ─────────────────────────── PREPARE BASE DATA ─────────────────
    df = prepare_measurements(measurements_df)

    top_pollutants = (
        df.groupby("pollutant_code")["value"]
        .count()
        .sort_values(ascending=False)
        .head(3)
        .index.tolist()
    )
    # Note: sidebar_pollutant_selector() not used here — pollutant list is
    # restricted to top 3 by data coverage, not the full POLLUTANTS dict
    available_pollutants = {k: v for k, v in POLLUTANTS.items() if v in top_pollutants}

    # ─────────────────────────── SIDEBAR ───────────────────────────
    st.sidebar.header("📦 Box Plot Settings")

    pollutant_label = st.sidebar.selectbox("Pollutant", list(available_pollutants.keys()), index=0)
    pollutant_code  = available_pollutants[pollutant_label]
    threshold       = WHO_THRESHOLDS.get(pollutant_code)
    borough_filter  = sidebar_borough_filter()

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
        "mean", "std", "min", "q1", "median", "q3", "max",
    ]

    # ─────────────────────────── BUILD CHART ───────────────────────
    colour_scale = alt.Scale(
        domain=list(BOROUGH_COLOURS.keys()),
        range=list(BOROUGH_COLOURS.values()),
    )

    x_enc      = alt.X(
        "station_name:N",
        sort=sorted_stations,
        title="Station",
        axis=alt.Axis(labelAngle=-45, labelLimit=0, labelOverlap=False),
    )
    colour_enc = alt.Color("borough:N", scale=colour_scale, legend=alt.Legend(title="Borough"))

    base = alt.Chart(stats_chart)

    whisker = base.mark_rule(strokeWidth=1.5).encode(
        x=x_enc,
        y=alt.Y("min:Q", title=f"{pollutant_code} concentration (µg/m³)"),
        y2=alt.Y2("max:Q"),
        color=alt.Color("borough:N", scale=colour_scale, legend=None),
    )

    box = base.mark_bar(size=20).encode(
        x=x_enc,
        y=alt.Y("q1:Q"),
        y2=alt.Y2("q3:Q"),
        color=colour_enc,
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

    median_line = base.mark_tick(color="white", thickness=2, size=20).encode(
        x=alt.X("station_name:N", sort=sorted_stations),
        y=alt.Y("median:Q"),
    )

    layers = [whisker, box, median_line]

    if threshold:
        who_df = pd.DataFrame({"threshold": [threshold], "label": [f"WHO limit: {threshold} µg/m³"]})
        layers += [
            alt.Chart(who_df).mark_rule(
                color="red", strokeDash=[6, 3], strokeWidth=1.5
            ).encode(y=alt.Y("threshold:Q")),

            alt.Chart(who_df).mark_text(
                align="left", dx=5, dy=-8, color="red", fontSize=11
            ).encode(y=alt.Y("threshold:Q"), text=alt.Text("label:N")),
        ]

    chart = (
        alt.layer(*layers)
        .properties(height=450, padding={"bottom": 120})
        .interactive()
    )

    st.altair_chart(chart, use_container_width=True)

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