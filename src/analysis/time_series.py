import altair as alt
import pandas as pd
import streamlit as st

POLLUTANTS = {
    "NO₂ — Nitrogen Dioxide": "NO2",
    "PM2.5 — Particulate Matter 2.5": "PM25",
    "PM10 — Particulate Matter 10": "PM10",
}

def render_time_series(df: pd.DataFrame):

    st.title("📈 Hourly Pollutant Time Series")
    st.write(
        "Hourly pollutant concentrations per monitoring station over the 48-hour observation window. "
        "Rush hour bands and the WHO annual guideline threshold are annotated."
    )

    # ─────────────────────────── DATA PREP ─────────────────────────
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df["measurement_date"] = pd.to_datetime(df["measurement_date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # ─────────────────────────── SIDEBAR FILTERS ───────────────────
    st.sidebar.header("⚙️ Filters")

    selected_pollutant_label = st.sidebar.selectbox(
        "Pollutant", list(POLLUTANTS.keys()), index=0
    )
    selected_pollutant_code = POLLUTANTS[selected_pollutant_label]

    boroughs = ["All boroughs"] + sorted(df["borough"].dropna().unique().tolist())
    selected_borough = st.sidebar.selectbox("Borough", boroughs, index=0)

    # ─────────────────────────── FILTER DATA ───────────────────────
    df = df[df["pollutant_code"] == selected_pollutant_code].copy()
    df = df.dropna(subset=["value"])

    if selected_borough != "All boroughs":
        df = df[df["borough"] == selected_borough]

    if df.empty:
        st.warning(f"No {selected_pollutant_label} data available for the selected filters.")
        return

    sorted_stations = sorted(df["station_name"].dropna().unique().tolist())

    # ─────────────────────────── WHO THRESHOLDS ────────────────────
    who_thresholds = {"NO2": 25, "PM25": 15, "PM10": 45}
    who_units = {"NO2": "µg/m³", "PM25": "µg/m³", "PM10": "µg/m³"}
    threshold = who_thresholds.get(selected_pollutant_code)
    unit = who_units.get(selected_pollutant_code, "µg/m³")

    # ─────────────────────────── RUSH HOUR BANDS ───────────────────
    dates = df["measurement_date"].dt.normalize().unique()
    rush_bands = []
    for date in dates:
        rush_bands.append({"start": pd.Timestamp(date) + pd.Timedelta(hours=7),
                           "end":   pd.Timestamp(date) + pd.Timedelta(hours=9)})
        rush_bands.append({"start": pd.Timestamp(date) + pd.Timedelta(hours=17),
                           "end":   pd.Timestamp(date) + pd.Timedelta(hours=19)})
    rush_df = pd.DataFrame(rush_bands)

    # ─────────────────────────── CHARTS ────────────────────────────
    bands = alt.Chart(rush_df).mark_rect(opacity=0.15, color="#FFA500").encode(
        x=alt.X("start:T"),
        x2=alt.X2("end:T"),
    )

    line = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X("measurement_date:T", title="Date / Time"),
        y=alt.Y("value:Q", title=f"{selected_pollutant_label.split(' — ')[0]} ({unit})"),
        color=alt.Color(
            "station_name:N",
            title="Station",
            sort=sorted_stations,
            legend=alt.Legend(labelLimit=300)
        ),
        tooltip=[
            alt.Tooltip("station_name:N", title="Station"),
            alt.Tooltip("measurement_date:T", title="Time"),
            alt.Tooltip("value:Q", title=f"{selected_pollutant_label.split(' — ')[0]} ({unit})", format=".1f"),
        ]
    )

    chart = bands + line

    if threshold:
        who_df = pd.DataFrame([{"threshold": threshold}])
        who_line = alt.Chart(who_df).mark_rule(
            color="red", strokeDash=[6, 4], strokeWidth=1.5
        ).encode(y=alt.Y("threshold:Q"))

        who_label = alt.Chart(who_df).mark_text(
            align="left", dx=4, dy=-6, color="red", fontSize=11
        ).encode(
            y=alt.Y("threshold:Q"),
            text=alt.value(f"WHO guideline {threshold} {unit}")
        )
        chart = bands + who_line + who_label + line

    chart = chart.properties(
        width="container",
        height=450,
        title=f"Hourly {selected_pollutant_label.split(' — ')[0]} Concentrations with Rush Hour Annotations"
    ).interactive()

    st.altair_chart(chart, use_container_width=True)

    # ─────────────────────────── SUMMARY TABLE ─────────────────────
    st.divider()
    st.subheader(f"📊 Peak {selected_pollutant_label.split(' — ')[0]} Readings")

    summary = (
        df.groupby("station_name")["value"]
        .agg(["max", "mean", "count"])
        .rename(columns={"max": f"Peak ({unit})", "mean": f"Average ({unit})", "count": "Readings"})
        .round(2)
        .reset_index()
        .rename(columns={"station_name": "Station"})
        .sort_values("Station", ascending=True)
    )

    st.dataframe(summary, use_container_width=True)