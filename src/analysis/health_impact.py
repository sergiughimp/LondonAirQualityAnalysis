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

def risk_level(pct: float) -> str:
    if pct == 0:
        return "✅ None"
    elif pct <= 10:
        return "🟡 Low"
    elif pct <= 30:
        return "🟠 Moderate"
    elif pct <= 60:
        return "🔴 High"
    else:
        return "🚨 Very High"

# ─────────────────────────── MAIN ──────────────────────────────────
def render_health_impact(measurements_df: pd.DataFrame):

    st.title("🏥 Health Impact Analysis")
    st.write(
        "Understand how often pollution levels exceeded WHO safe limits across boroughs "
        "and which stations posed the greatest health risk over the dataset period."
    )

    # ─────────────────────────── PREPARE DATA ──────────────────────
    df = measurements_df.copy()
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["measurement_date"] = pd.to_datetime(df["measurement_date"], errors="coerce")

    # ─────────────────────────── SIDEBAR ───────────────────────────
    st.sidebar.header("🏥 Health Impact Settings")

    borough_options = ["All boroughs"] + BOROUGHS
    borough_selection = st.sidebar.selectbox(
        "Filter by borough", borough_options, index=0
    )
    borough_filter = BOROUGHS if borough_selection == "All boroughs" else [borough_selection]

    # ─────────────────────────── SECTION 1 — WHO EXCEEDANCE ────────
    st.divider()
    st.subheader("⏱️ WHO Exceedance Hours per Borough")

    exceedance_rows = []
    for pollutant_code, threshold in WHO_THRESHOLDS.items():
        if threshold is None:
            continue
        pol_df = df[
            (df["pollutant_code"] == pollutant_code) &
            (df["value"].notna()) &
            (df["value"] > 0) &
            (df["borough"].isin(borough_filter))
        ]
        if pol_df.empty:
            continue

        for borough in borough_filter:
            b_df = pol_df[pol_df["borough"] == borough]
            total_hours = len(b_df)
            exceeded = len(b_df[b_df["value"] > threshold])
            pct = round((exceeded / total_hours * 100), 1) if total_hours > 0 else 0
            exceedance_rows.append({
                "borough":        borough,
                "pollutant_code": pollutant_code,
                "total_hours":    total_hours,
                "exceeded_hours": exceeded,
                "pct_exceeded":   pct,
                "risk":           risk_level(pct),
            })

    exceedance_df = pd.DataFrame(exceedance_rows)

    if not exceedance_df.empty:
        colour_scale = alt.Scale(
            domain=BOROUGHS,
            range=list(BOROUGH_COLOURS.values()),
        )

        bar = alt.Chart(exceedance_df).mark_bar().encode(
            x=alt.X("pollutant_code:N", title="Pollutant"),
            y=alt.Y("pct_exceeded:Q", title="% Hours Above WHO Limit"),
            color=alt.Color("borough:N", scale=colour_scale, legend=alt.Legend(title="Borough")),
            column=alt.Column("borough:N", title="Borough"),
            tooltip=[
                alt.Tooltip("borough:N",        title="Borough"),
                alt.Tooltip("pollutant_code:N", title="Pollutant"),
                alt.Tooltip("exceeded_hours:Q", title="Hours Exceeded"),
                alt.Tooltip("total_hours:Q",    title="Total Hours"),
                alt.Tooltip("pct_exceeded:Q",   title="% Exceeded", format=".1f"),
                alt.Tooltip("risk:N",           title="Risk Level"),
            ],
        ).properties(width=160, height=300)

        st.altair_chart(bar)

        with st.expander("ℹ️ About this chart", expanded=False):
            st.markdown("""
            Each bar shows the **percentage of hourly readings that exceeded the WHO guideline**
            for each pollutant and borough. A higher bar means more hours of unsafe air quality.

            WHO thresholds used:
            - **NO₂** 25 µg/m³ — **PM2.5** 15 µg/m³ — **PM10** 45 µg/m³
            - **O₃** 100 µg/m³ — **SO₂** 40 µg/m³
            """)

    # ─────────────────────────── SECTION 2 — MOST AFFECTED STATION ─
    st.divider()
    st.subheader("📍 Most Affected Stations")

    station_rows = []
    for pollutant_code, threshold in WHO_THRESHOLDS.items():
        if threshold is None:
            continue
        pol_df = df[
            (df["pollutant_code"] == pollutant_code) &
            (df["value"].notna()) &
            (df["value"] > 0) &
            (df["borough"].isin(borough_filter))
        ]
        if pol_df.empty:
            continue

        for station in pol_df["station_name"].unique():
            s_df = pol_df[pol_df["station_name"] == station]
            borough = s_df["borough"].iloc[0]
            total = len(s_df)
            exceeded = len(s_df[s_df["value"] > threshold])
            pct = round((exceeded / total * 100), 1) if total > 0 else 0
            station_rows.append({
                "Borough":          borough,
                "Station":          station,
                "Pollutant":        pollutant_code,
                "Total Hours":      total,
                "Hours Exceeded":   exceeded,
                "% Exceeded":       pct,
                "Risk Level":       risk_level(pct),
            })

    station_df = pd.DataFrame(station_rows)

    if not station_df.empty:
        # overall risk score per station — average % exceeded across all pollutants
        risk_score = (
            station_df.groupby(["Borough", "Station"])["% Exceeded"]
            .mean()
            .round(1)
            .reset_index()
            .rename(columns={"% Exceeded": "Avg % Exceeded"})
            .sort_values("Avg % Exceeded", ascending=False)
        )
        risk_score["Overall Risk"] = risk_score["Avg % Exceeded"].apply(risk_level)

        st.markdown("#### 🏆 Overall Risk Ranking")
        st.dataframe(risk_score, use_container_width=True)

        st.markdown("#### 📋 Full Exceedance Breakdown by Station and Pollutant")
        st.dataframe(
            station_df.sort_values(["Borough", "% Exceeded"], ascending=[True, False]),
            use_container_width=True,
        )

        with st.expander("ℹ️ About this table", expanded=False):
            st.markdown("""
            **Overall Risk Ranking** shows each station's average exceedance rate across
            all pollutants — a single score summarising its overall health risk.

            **Full Breakdown** shows exceedance rates per station and pollutant individually,
            so you can identify which specific pollutant is driving the risk at each location.

            Risk levels:
            - **✅ None** — 0% exceedance
            - **🟡 Low** — up to 10% of hours exceeded
            - **🟠 Moderate** — 10–30% of hours exceeded
            - **🔴 High** — 30–60% of hours exceeded
            - **🚨 Very High** — more than 60% of hours exceeded
            """)