import json
import pandas as pd
from pathlib import Path

# -----------------------------
# Paths
# -----------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_FILE = PROJECT_ROOT / "data" / "raw" / "air_quality_3_days.json"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

STATIONS_FILE = PROCESSED_DIR / "stations.csv"
MEASUREMENTS_FILE = PROCESSED_DIR / "measurements.csv"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------
# Load JSON
# -----------------------------
with open(RAW_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

boroughs = data.get("boroughs", {})

# -----------------------------
# Extract stations
# -----------------------------
station_rows = []

for borough, sites in boroughs.items():
    for site in sites:
        station_rows.append({
            "borough": borough,
            "station_name": site.get("site_name"),
            "station_code": site.get("site_code"),
            "site_type": site.get("site_type"),
            "latitude": site.get("latitude"),
            "longitude": site.get("longitude"),
        })

stations_df = pd.DataFrame(station_rows)
stations_df.to_csv(STATIONS_FILE, index=False)

print(f"Saved stations data → {STATIONS_FILE}")

# -----------------------------
# Extract measurements
# -----------------------------
measurement_rows = []

for borough, sites in boroughs.items():
    for site in sites:

        station_name = site.get("site_name")
        station_code = site.get("site_code")
        site_type = site.get("site_type")

        pollutants = site.get("pollutants_measured", [])

        for pollutant in pollutants:

            pollutant_code = pollutant.get("species_code")
            pollutant_name = pollutant.get("species_name")
            measurements = pollutant.get("measurements", [])

            for m in measurements:

                date_value = (
                    m.get("@MeasurementDateGMT")
                    or m.get("MeasurementDateGMT")
                    or m.get("@Date")
                    or m.get("Date")
                )

                value = m.get("@Value") or m.get("Value")

                measurement_rows.append({
                    "borough": borough,
                    "station_name": station_name,
                    "station_code": station_code,
                    "site_type": site_type,
                    "pollutant_code": pollutant_code,
                    "pollutant_name": pollutant_name,
                    "measurement_date": date_value,
                    "value": value
                })

measurements_df = pd.DataFrame(measurement_rows)

measurements_df["measurement_date"] = pd.to_datetime(
    measurements_df["measurement_date"], errors="coerce"
)

measurements_df["value"] = pd.to_numeric(
    measurements_df["value"], errors="coerce"
)

measurements_df.to_csv(MEASUREMENTS_FILE, index=False)

print(f"Saved measurements data → {MEASUREMENTS_FILE}")