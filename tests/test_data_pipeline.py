import pytest
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIONS_FILE = PROJECT_ROOT / "data" / "processed" / "stations.csv"
MEASUREMENTS_FILE = PROJECT_ROOT / "data" / "processed" / "measurements.csv"


def test_stations_file_exists():
    assert STATIONS_FILE.exists(), "stations.csv does not exist"


def test_stations_has_required_columns():
    df = pd.read_csv(STATIONS_FILE)
    required = {"borough", "station_name", "station_code", "site_type", "latitude", "longitude"}
    assert required.issubset(set(df.columns)), f"Missing columns: {required - set(df.columns)}"


def test_stations_not_empty():
    df = pd.read_csv(STATIONS_FILE)
    assert len(df) > 0, "stations.csv is empty"