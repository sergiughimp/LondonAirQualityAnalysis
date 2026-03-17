# ─────────────────────────── SHARED CONSTANTS ──────────────────────────────

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