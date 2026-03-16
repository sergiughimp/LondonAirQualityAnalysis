import pytest
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MEASUREMENTS_FILE = PROJECT_ROOT / "data" / "processed" / "measurements.csv"

VALID_BOROUGHS = {"Camden", "Greenwich", "Tower Hamlets"}
VALID_POLLUTANTS = {"NO2", "PM25", "PM10", "O3", "SO2", "CO"}


def test_borough_names_valid():
    df = pd.read_csv(MEASUREMENTS_FILE)
    invalid = set(df["borough"].dropna().unique()) - VALID_BOROUGHS
    assert len(invalid) == 0, f"Invalid boroughs found: {invalid}"


def test_pollutant_codes_valid():
    df = pd.read_csv(MEASUREMENTS_FILE)
    invalid = set(df["pollutant_code"].dropna().unique()) - VALID_POLLUTANTS
    assert len(invalid) == 0, f"Invalid pollutant codes found: {invalid}"


def test_measurement_dates_parseable():
    df = pd.read_csv(MEASUREMENTS_FILE)
    parsed = pd.to_datetime(df["measurement_date"], errors="coerce")
    null_count = parsed.isna().sum()
    assert null_count == 0, f"{null_count} measurement dates could not be parsed"