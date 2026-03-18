import pandas as pd
import altair as alt
import streamlit as st
from src.analysis.constants import POLLUTANTS, WHO_THRESHOLDS, BOROUGH_COLOURS, BOROUGHS
from src.analysis.common import prepare_measurements, sidebar_borough_filter

# ─────────────────────────── HELPERS ───────────────────────────────
def pivot_pollutants(df, index_cols):
    return (
        df.pivot_table(
            index=index_cols,
            columns="pollutant_code",
            values="value",
            aggfunc="mean",
        )
        .reset_index()
    )

# ─────────────────────────── MAIN ──────────────────────────────────
def render_correlation(measurements_df: pd.DataFrame):

    st.title("📊 Correlation Analysis")
    st.markdown(
        """
        Explore relationships between pollutants across stations and boroughs.
        Strong correlations suggest pollutants share a common source —
        such as traffic emissions driving both **NO₂** and **PM2.5** simultaneously.
        Use the sidebar to filter by borough and the scatter plot selectors to compare any two pollutants.
        """
    )

    # ─────────────────────────── DATA PREP & SIDEBAR ───────────────
    df = prepare_measurements(measurements_df)

    st.sidebar.header("📊 Correlation Settings")
    borough_filter = sidebar_borough_filter()

    # ─────────────────────────── FILTER + PIVOT ────────────────────
    filtered      = df[df["borough"].isin(borough_filter)]
    wide          = pivot_pollutants(filtered, ["station_name", "measurement_date"])
    pollutant_cols = [c for c in wide.columns if c in POLLUTANTS.values()]
    wide          = wide[["station_name"] + pollutant_cols].dropna(how="all", subset=pollutant_cols)

    if wide.empty or len(pollutant_cols) < 2:
        st.warning("⚠️ Not enough data to compute correlations. Try selecting a different borough.")
        return

    # ─────────────────────────── CORRELATION HEATMAP ───────────────
    st.divider()
    st.subheader("🔥 Pollutant Correlation Heatmap")
    st.caption(
        "Pearson correlation coefficients between all pollutant pairs. "
        "Values range from -1 (perfect negative) to +1 (perfect positive). "
        "Strong positive correlations suggest a shared emission source."
    )

    corr      = wide[pollutant_cols].corr().round(2)
    corr_long = corr.reset_index().melt(
        id_vars="pollutant_code", var_name="pollutant_y", value_name="correlation"
    )

    heatmap = alt.Chart(corr_long).mark_rect().encode(
        x=alt.X("pollutant_code:N", title="Pollutant", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("pollutant_y:N",    title="Pollutant"),
        color=alt.Color(
            "correlation:Q",
            scale=alt.Scale(scheme="redblue", domain=[-1, 1]),
            title="Correlation",
        ),
        tooltip=[
            alt.Tooltip("pollutant_code:N", title="Pollutant X"),
            alt.Tooltip("pollutant_y:N",    title="Pollutant Y"),
            alt.Tooltip("correlation:Q",    title="Correlation", format=".2f"),
        ],
    ).properties(width=500, height=500)

    text = alt.Chart(corr_long).mark_text(fontSize=13, fontWeight="bold").encode(
        x=alt.X("pollutant_code:N", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("pollutant_y:N"),
        text=alt.Text("correlation:Q", format=".2f"),
        color=alt.condition(
            "datum.correlation > 0.5 || datum.correlation < -0.5",
            alt.value("white"),
            alt.value("black"),
        ),
    )

    col_left, col_center, col_right = st.columns([1, 3, 1])
    with col_center:
        st.altair_chart(heatmap + text, use_container_width=True)

    with st.expander("ℹ️ About this chart", expanded=False):
        st.markdown("""
        **How to read this heatmap:**
        - Each cell shows the **Pearson correlation coefficient** between two pollutants
        ranging from **-1** (perfect negative correlation) to **+1** (perfect positive correlation)
        - **Dark red cells** — strong positive correlation — both pollutants rise and fall together,
        suggesting they share a common emission source such as road traffic
        - **Dark blue cells** — strong negative correlation — one pollutant rises as the other falls
        - **White cells** — no meaningful relationship between the two pollutants

        **Interpretation guidance:**
        - A strong positive correlation between **NO₂ and PM2.5** is a strong indicator
        of traffic as the dominant pollution source — both are emitted by diesel vehicles
        - Correlations involving **O₃ (Ozone)** are often negative with NO₂ because ozone
        is consumed in chemical reactions with NO₂ near busy roads
        - **CO** readings are largely absent in this dataset and may show weak or unreliable
        correlations due to insufficient data coverage
        """)

    # ─────────────────────────── SCATTER PLOT ──────────────────────
    st.divider()
    st.subheader("🔵 Scatter Plot — Pollutant vs Pollutant")
    st.caption(
        "Compare any two pollutants directly. Each dot represents a single hourly reading "
        "where both pollutants were recorded at the same station at the same time. "
        "Colour indicates the borough."
    )

    available = [k for k, v in POLLUTANTS.items() if v in pollutant_cols]

    col1, col2 = st.columns(2)
    with col1:
        x_label = st.selectbox("X axis pollutant", available, index=0)
    with col2:
        y_label = st.selectbox("Y axis pollutant", available, index=1 if len(available) > 1 else 0)

    x_code = POLLUTANTS[x_label]
    y_code = POLLUTANTS[y_label]

    scatter_wide = (
        pivot_pollutants(
            filtered[filtered["pollutant_code"].isin([x_code, y_code])],
            ["station_name", "borough", "measurement_date"],
        )
        .dropna(subset=[x_code, y_code])
    )

    if scatter_wide.empty:
        st.warning(
            f"⚠️ Not enough overlapping data for **{x_label}** and **{y_label}**. "
            f"Try a different pollutant combination."
        )
    else:
        scatter = alt.Chart(scatter_wide).mark_circle(opacity=0.6, size=60).encode(
            x=alt.X(f"{x_code}:Q", title=f"{x_code} (µg/m³)"),
            y=alt.Y(f"{y_code}:Q", title=f"{y_code} (µg/m³)"),
            color=alt.Color(
                "borough:N",
                scale=alt.Scale(domain=BOROUGHS, range=list(BOROUGH_COLOURS.values())),
                legend=alt.Legend(title="Borough"),
            ),
            tooltip=[
                alt.Tooltip("station_name:N", title="Station"),
                alt.Tooltip("borough:N",       title="Borough"),
                alt.Tooltip(f"{x_code}:Q",     title=f"{x_code} (µg/m³)", format=".1f"),
                alt.Tooltip(f"{y_code}:Q",     title=f"{y_code} (µg/m³)", format=".1f"),
            ],
        ).properties(height=400).interactive()

        st.altair_chart(scatter, use_container_width=True)

        with st.expander("ℹ️ About this chart", expanded=False):
            st.markdown(f"""
            **How to read this scatter plot:**
            - Each **dot** represents a single hourly reading where both
            **{x_code}** and **{y_code}** were recorded at the same station at the same time
            - **Colour** indicates which borough the station belongs to
            - A **diagonal cluster** of dots from bottom-left to top-right suggests a
            strong positive correlation — both pollutants tend to be high or low together,
            pointing to a shared emission source such as road traffic
            - A **horizontal or vertical spread** with no clear pattern indicates
            little or no relationship between the two pollutants

            **Interpretation guidance:**
            - Hover over individual dots to see the station name, borough, and exact readings
            - Outlier dots far from the main cluster may reflect sensor spikes or
            localised pollution events — cross-reference with the **📉 Missing Data** page
            """)

    # ─────────────────────────── CORRELATION MATRIX TABLE ──────────
    st.divider()
    st.subheader("📋 Full Correlation Matrix")
    st.caption(
        "Complete Pearson correlation matrix for all pollutants with sufficient data. "
        "Values closer to 1.0 or -1.0 indicate stronger relationships."
    )
    st.dataframe(corr, use_container_width=True)

    with st.expander("ℹ️ About this table", expanded=False):
        st.markdown("""
        - Values range from **-1.0** to **+1.0**
        - **1.0** on the diagonal — every pollutant is perfectly correlated with itself
        - Values **above 0.7** indicate a strong positive relationship
        - Values **below -0.7** indicate a strong negative relationship
        - Values **between -0.3 and 0.3** suggest little to no meaningful correlation

        Pollutants with insufficient data (such as CO in this dataset) may show
        unreliable correlation values and should be interpreted with caution.
        """)