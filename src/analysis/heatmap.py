import altair as alt
import pandas as pd
import streamlit as st

POLLUTANTS = {
    "NO₂ — Nitrogen Dioxide": "NO2",
    "PM2.5 — Particulate Matter 2.5": "PM25",
    "PM10 — Particulate Matter 10": "PM10",
}

def render_heatmap(df: pd.DataFrame):

    st.title("🔥 Pollution Heatmap — Station vs Hour of Day")
    st.write(
        "Each cell shows the average pollutant concentration for a given station and hour of the day. "
        "Darker cells indicate higher pollution levels. Charts are split by day."
    )

    # ─────────────────────────── DATA PREP ─────────────────────────
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df["measurement_date"] = pd.to_datetime(df["measurement_date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["hour"] = df["measurement_date"].dt.hour
    df["date"] = df["measurement_date"].dt.date.astype(str)

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
    unit = "µg/m³"
    pollutant_short = selected_pollutant_label.split(" — ")[0]

    # ─────────────────────────── AGGREGATE ─────────────────────────
    heatmap_df = (
        df.groupby(["station_name", "hour", "date"])["value"]
        .mean()
        .round(2)
        .reset_index()
        .rename(columns={"value": "avg_value"})
    )

    # ─────────────────────────── SPLIT BY DAY ──────────────────────
    dates = sorted(heatmap_df["date"].unique().tolist())

    for day in dates:
        day_df = heatmap_df[heatmap_df["date"] == day]

        chart = alt.Chart(day_df).mark_rect().encode(
            x=alt.X("hour:O", title="Hour of Day", axis=alt.Axis(labelAngle=0)),
            y=alt.Y(
                "station_name:N",
                title="Station",
                sort=sorted_stations,
                axis=alt.Axis(labelLimit=300)
            ),
            color=alt.Color(
                "avg_value:Q",
                title=f"Avg {pollutant_short} ({unit})",
                scale=alt.Scale(scheme="orangered"),
                legend=alt.Legend(labelLimit=300)
            ),
            tooltip=[
                alt.Tooltip("station_name:N", title="Station"),
                alt.Tooltip("hour:O", title="Hour"),
                alt.Tooltip("avg_value:Q", title=f"Avg {pollutant_short} ({unit})", format=".2f"),
            ]
        ).properties(
            width="container",
            height=400,
            title=f"{pollutant_short} Concentration — {day}"
        )

        st.altair_chart(chart, use_container_width=True)

    # ─────────────────────────── SUMMARY TABLE ─────────────────────
    st.divider()
    st.subheader(f"📊 Average {pollutant_short} by Station")

    summary = (
        df.groupby("station_name")["value"]
        .mean()
        .round(2)
        .reset_index()
        .rename(columns={"station_name": "Station", "value": f"Average {pollutant_short} ({unit})"})
        .sort_values("Station", ascending=True)
    )

    st.dataframe(summary, use_container_width=True)