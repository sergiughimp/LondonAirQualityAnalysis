import pandas as pd
import streamlit as st
from src.analysis.constants import POLLUTANTS, WHO_THRESHOLDS, BOROUGHS

def prepare_measurements(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns             = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df["value"]            = pd.to_numeric(df["value"], errors="coerce")
    df["measurement_date"] = pd.to_datetime(df["measurement_date"], errors="coerce")
    return df[df["value"] > 0]

def load_and_normalise_csv(filepath) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    return df

def sidebar_borough_filter() -> list[str]:
    selection = st.sidebar.selectbox("Filter by borough", ["All boroughs"] + BOROUGHS, index=0)
    return BOROUGHS if selection == "All boroughs" else [selection]

def sidebar_pollutant_selector() -> tuple[str, str, int | None]:
    label     = st.sidebar.selectbox("Pollutant", list(POLLUTANTS.keys()), index=0)
    code      = POLLUTANTS[label]
    threshold = WHO_THRESHOLDS.get(code)
    return label, code, threshold