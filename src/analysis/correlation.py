import pandas as pd
import altair as alt
import streamlit as st
import numpy as np

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
def render_correlation(measurements_df: pd.DataFrame):

    st.title("📊 Correlation Analysis")
    st.write(
        "Explore relationships between pollutants across stations and boroughs. "
        "Strong correlations suggest pollutants share a common source — "
        "such as traffic emissions driving both NO₂ and PM2.5 simultaneously."
    )

    # ─────────────────────────── PREPARE DATA ──────────────────────
    df = measurements_df.copy()
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["measurement_date"] = pd.to_datetime(df["measurement_date"], errors="coerce")

    # ─────────────────────────── SIDEBAR ───────────────────────────
    st.sidebar.header("📊 Correlation Settings")

    borough_options = ["All boroughs"] + BOROUGHS
    borough_selection = st.sidebar.selectbox(
        "Filter by borough", borough_options, index=0
    )
    borough_filter = BOROUGHS if borough_selection == "All boroughs" else [borough_selection]

    # pivot to wide format — one column per pollutant
    filtered = df[df["borough"].isin(borough_filter)]
    wide = filtered.pivot_table(
        index=["station_name", "measurement_date"],
        columns="pollutant_code",
        values="value",
        aggfunc="mean",
    ).reset_index()

    # keep only pollutants with enough data
    pollutant_cols = [c for c in wide.columns if c in POLLUTANTS.values()]
    wide = wide[["station_name"] + pollutant_cols].dropna(how="all", subset=pollutant_cols)

    if wide.empty or len(pollutant_cols) < 2:
        st.warning("Not enough data to compute correlations.")
        return

    # ─────────────────────────── SECTION 1 — CORRELATION HEATMAP ──
    st.divider()
    st.subheader("🔥 Pollutant Correlation Heatmap")

    corr = wide[pollutant_cols].corr().round(2)

    corr_long = (
        corr.reset_index()
        .melt(id_vars="pollutant_code", var_name="pollutant_y", value_name="correlation")
    )

    heatmap = alt.Chart(corr_long).mark_rect().encode(
        x=alt.X("pollutant_code:N", title="Pollutant"),
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
    ).properties(width=400, height=400)

    text = alt.Chart(corr_long).mark_text(fontSize=12).encode(
        x=alt.X("pollutant_code:N"),
        y=alt.Y("pollutant_y:N"),
        text=alt.Text("correlation:Q", format=".2f"),
        color=alt.condition(
            "datum.correlation > 0.5 || datum.correlation < -0.5",
            alt.value("white"),
            alt.value("black"),
        ),
    )

    st.altair_chart(heatmap + text, use_container_width=False)

    with st.expander("ℹ️ About this chart", expanded=False):
        st.markdown("""
        Each cell shows the **Pearson correlation coefficient** between two pollutants,
        ranging from **-1** (perfect negative) to **+1** (perfect positive).

        - **Dark red** — strong positive correlation — both pollutants rise and fall together
        - **Dark blue** — strong negative correlation — one rises as the other falls
        - **White** — no meaningful relationship

        A strong positive correlation between NO₂ and PM2.5 for example suggests
        both are being produced by the same source — most likely road traffic.
        """)

    # ─────────────────────────── SECTION 2 — SCATTER PLOT ──────────
    st.divider()
    st.subheader("🔵 Scatter Plot — Pollutant vs Pollutant")

    available = [k for k, v in POLLUTANTS.items() if v in pollutant_cols]

    col1, col2 = st.columns(2)
    with col1:
        x_label = st.selectbox("X axis pollutant", available, index=0)
    with col2:
        y_label = st.selectbox("Y axis pollutant", available, index=1 if len(available) > 1 else 0)

    x_code = POLLUTANTS[x_label]
    y_code = POLLUTANTS[y_label]

    scatter_df = filtered[filtered["pollutant_code"].isin([x_code, y_code])]
    scatter_wide = scatter_df.pivot_table(
        index=["station_name", "borough", "measurement_date"],
        columns="pollutant_code",
        values="value",
        aggfunc="mean",
    ).reset_index().dropna(subset=[x_code, y_code])

    if scatter_wide.empty:
        st.warning("Not enough overlapping data for these two pollutants.")
    else:
        colour_scale = alt.Scale(
            domain=BOROUGHS,
            range=list(BOROUGH_COLOURS.values()),
        )

        scatter = alt.Chart(scatter_wide).mark_circle(
            opacity=0.6, size=60
        ).encode(
            x=alt.X(f"{x_code}:Q", title=f"{x_code} (µg/m³)"),
            y=alt.Y(f"{y_code}:Q", title=f"{y_code} (µg/m³)"),
            color=alt.Color("borough:N", scale=colour_scale, legend=alt.Legend(title="Borough")),
            tooltip=[
                alt.Tooltip("station_name:N",   title="Station"),
                alt.Tooltip("borough:N",         title="Borough"),
                alt.Tooltip(f"{x_code}:Q",       title=x_code, format=".1f"),
                alt.Tooltip(f"{y_code}:Q",       title=y_code, format=".1f"),
            ],
        ).properties(height=400).interactive()

        st.altair_chart(scatter, use_container_width=True)

        with st.expander("ℹ️ About this chart", expanded=False):
            st.markdown(f"""
            Each dot represents a single hourly reading where both **{x_code}** and **{y_code}**
            were recorded at the same station at the same time.
            Colour indicates the borough.

            A diagonal cluster of dots suggests the two pollutants are correlated —
            they tend to be high or low at the same time, pointing to a shared emission source.
            """)

    # ─────────────────────────── SECTION 3 — CORRELATION TABLE ─────
    st.divider()
    st.subheader("📋 Correlation Matrix")
    st.dataframe(corr, use_container_width=True)