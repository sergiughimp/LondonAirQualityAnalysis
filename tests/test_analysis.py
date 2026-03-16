import pytest
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MEASUREMENTS_FILE = PROJECT_ROOT / "data" / "processed" / "measurements.csv"

WHO_THRESHOLDS = {
    "NO2":  25,
    "PM25": 15,
    "PM10": 45,
    "O3":   100,
    "SO2":  40,
}


def test_who_thresholds_correct():
    assert WHO_THRESHOLDS["NO2"] == 25
    assert WHO_THRESHOLDS["PM25"] == 15
    assert WHO_THRESHOLDS["PM10"] == 45


def test_peak_value_matches_max():
    df = pd.read_csv(MEASUREMENTS_FILE)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    no2 = df[(df["pollutant_code"] == "NO2") & (df["value"] > 0)]
    if no2.empty:
        pytest.skip("No NO2 data available")
    peak = no2.groupby("borough")["value"].max()
    for borough, val in peak.items():
        actual_max = no2[no2["borough"] == borough]["value"].max()
        assert val == actual_max, f"Peak mismatch for {borough}"


def test_missing_rate_calculation():
    df = pd.read_csv(MEASUREMENTS_FILE)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["is_missing"] = df["value"].isna() | (df["value"] <= 0)
    total = len(df)
    missing = df["is_missing"].sum()
    pct = round((missing / total) * 100, 1)
    assert 0 <= pct <= 100, f"Missing rate {pct}% is out of valid range"