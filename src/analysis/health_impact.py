import pandas as pd
import altair as alt
import streamlit as st
from src.analysis.constants import POLLUTANTS, WHO_THRESHOLDS, BOROUGH_COLOURS, BOROUGHS

# ─────────────────────────── HELPERS ───────────────────────────────
def risk_level(pct: float) -> str:
    if pct == 0:     return "✅ None"
    elif pct <= 10:  return "🟡 Low"
    elif pct <= 30:  return "🟠 Moderate"
    elif pct <= 60:  return "🔴 High"
    else:            return "🚨 Very High"

# ─────────────────────────── MAIN ──────────────────────────────────
def render_health_impact(measurements_df: pd.DataFrame):

    st.title("🏥 Health Impact Analysis")
    st.markdown(
        """
        Understand how often pollution levels exceeded WHO safe limits across boroughs
        and which stations posed the greatest health risk over the dataset period.
        Use the sidebar to filter by borough and explore exceedance patterns by pollutant.
        """
    )

    # ─────────────────────────── DATA PREP ─────────────────────────
    df = measurements_df.copy()
    df.columns             = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df["value"]            = pd.to_numeric(df["value"], errors="coerce")
    df["measurement_date"] = pd.to_datetime(df["measurement_date"], errors="coerce")
    df                     = df[df["value"] > 0]

    # ─────────────────────────── SIDEBAR ───────────────────────────
    st.sidebar.header("🏥 Health Impact Settings")

    borough_options   = ["All boroughs"] + BOROUGHS
    borough_selection = st.sidebar.selectbox(
        "Filter by borough", borough_options, index=0
    )
    borough_filter = BOROUGHS if borough_selection == "All boroughs" else [borough_selection]

    # ─────────────────────────── WHO EXCEEDANCE ────────────────────
    st.divider()
    st.subheader("⏱️ WHO Exceedance Hours per Borough")
    st.caption(
        "Percentage of hourly readings that exceeded the WHO annual mean guideline "
        "for each pollutant and borough. A higher bar means more hours of unsafe air quality "
        "recorded during the monitoring period."
    )

    exceedance_rows = []
    for pollutant_code, threshold in WHO_THRESHOLDS.items():
        if threshold is None:
            continue

        pol_df = df[
            (df["pollutant_code"] == pollutant_code) &
            (df["value"].notna()) &
            (df["borough"].isin(borough_filter))
        ]
        if pol_df.empty:
            continue

        for borough in borough_filter:
            b_df        = pol_df[pol_df["borough"] == borough]
            total_hours = len(b_df)
            exceeded    = len(b_df[b_df["value"] > threshold])
            pct         = round((exceeded / total_hours * 100), 1) if total_hours > 0 else 0
            exceedance_rows.append({
                "borough":        borough,
                "pollutant_code": pollutant_code,
                "total_hours":    total_hours,
                "exceeded_hours": exceeded,
                "pct_exceeded":   pct,
                "risk":           risk_level(pct),
            })

    exceedance_df = pd.DataFrame(exceedance_rows)

    if exceedance_df.empty:
        st.warning("⚠️ No exceedance data available for the selected borough.")
    else:
        colour_scale = alt.Scale(
            domain=BOROUGHS,
            range=list(BOROUGH_COLOURS.values()),
        )

        bar = alt.Chart(exceedance_df).mark_bar().encode(
            x=alt.X(
                "pollutant_code:N",
                title="Pollutant",
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y(
                "pct_exceeded:Q",
                title="% Hours Above WHO Limit",
            ),
            color=alt.Color(
                "borough:N",
                scale=colour_scale,
                legend=alt.Legend(title="Borough"),
            ),
            column=alt.Column(
                "borough:N",
                title="Borough",
            ),
            tooltip=[
                alt.Tooltip("borough:N",        title="Borough"),
                alt.Tooltip("pollutant_code:N", title="Pollutant"),
                alt.Tooltip("exceeded_hours:Q", title="Hours Exceeded"),
                alt.Tooltip("total_hours:Q",    title="Total Hours"),
                alt.Tooltip("pct_exceeded:Q",   title="% Exceeded", format=".1f"),
                alt.Tooltip("risk:N",           title="Risk Level"),
            ],
        ).properties(width=160, height=300)

        col_left, col_center, col_right = st.columns([0.1, 5, 0.1])
        with col_center:
            st.altair_chart(bar, use_container_width=False)

        with st.expander("ℹ️ About this chart", expanded=False):
            st.markdown("""
            **How to read this chart:**
            - Each **panel** represents a borough — bars within each panel show
            the exceedance rate per pollutant
            - **Taller bars** mean more hours of unsafe air quality recorded
            during the monitoring period
            - Borough colours are consistent across all panels for easy comparison

            **WHO thresholds applied:**
            | Pollutant | WHO Guideline |
            |---|---|
            | NO₂ | 25 µg/m³ |
            | PM2.5 | 15 µg/m³ |
            | PM10 | 45 µg/m³ |
            | O₃ | 100 µg/m³ |
            | SO₂ | 40 µg/m³ |

            **Interpretation guidance:**
            - High exceedance rates for **NO₂** and **PM2.5** are most directly linked
            to road traffic and diesel vehicle emissions
            - High **PM10** exceedance may reflect construction activity or road dust
            in addition to traffic
            - For a station-level breakdown, see the Most Affected Stations section below
            """)

    # ─────────────────────────── MOST AFFECTED STATIONS ───────────
    st.divider()
    st.subheader("📍 Most Affected Stations")
    st.caption(
        "Station-level health risk assessment based on WHO exceedance rates. "
        "The Overall Risk Ranking summarises each station's risk across all pollutants. "
        "The full breakdown shows which specific pollutant is driving the risk at each location."
    )

    station_rows = []
    for pollutant_code, threshold in WHO_THRESHOLDS.items():
        if threshold is None:
            continue

        pol_df = df[
            (df["pollutant_code"] == pollutant_code) &
            (df["value"].notna()) &
            (df["borough"].isin(borough_filter))
        ]
        if pol_df.empty:
            continue

        for station in pol_df["station_name"].unique():
            s_df     = pol_df[pol_df["station_name"] == station]
            borough  = s_df["borough"].iloc[0]
            total    = len(s_df)
            exceeded = len(s_df[s_df["value"] > threshold])
            pct      = round((exceeded / total * 100), 1) if total > 0 else 0
            station_rows.append({
                "Borough":        borough,
                "Station":        station,
                "Pollutant":      pollutant_code,
                "Total Hours":    total,
                "Hours Exceeded": exceeded,
                "% Exceeded":     pct,
                "Risk Level":     risk_level(pct),
            })

    station_df = pd.DataFrame(station_rows)

    if station_df.empty:
        st.warning("⚠️ No station data available for the selected borough.")
    else:
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
        st.dataframe(
            risk_score.drop(columns=["Borough"]),
            use_container_width=True,
        )

        st.markdown("#### 📋 Full Exceedance Breakdown by Station and Pollutant")
        st.dataframe(
            station_df
            .drop(columns=["Borough"])
            .sort_values(["% Exceeded"], ascending=False),
            use_container_width=True,
        )

        with st.expander("ℹ️ About these tables", expanded=False):
            st.markdown("""
            **Overall Risk Ranking** shows each station's average exceedance rate across
            all pollutants — a single score summarising its overall health risk to local residents.
            Stations at the top of this table are the most consistently polluted locations
            in the dataset.

            **Full Exceedance Breakdown** shows exceedance rates per station and pollutant
            individually, allowing you to identify which specific pollutant is driving the
            risk at each location — useful for understanding whether a station is problematic
            across the board or only for a specific pollutant.

            **Risk levels explained:**
            | Level | Threshold | Meaning |
            |---|---|---|
            | ✅ None | 0% | No readings exceeded the WHO guideline |
            | 🟡 Low | Up to 10% | Occasional exceedances — generally safe |
            | 🟠 Moderate | 10–30% | Frequent exceedances — sensitive groups at risk |
            | 🔴 High | 30–60% | Persistent exceedances — health risk for all residents |
            | 🚨 Very High | Above 60% | Severe exceedances — significant public health concern |

            > Stations with **🔴 High** or **🚨 Very High** risk ratings should be
            treated as priority locations for air quality intervention and further investigation.
            """)