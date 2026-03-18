import argparse
import requests
import json
from datetime import date
from pathlib import Path
from urllib.parse import quote
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# -----------------------------
# 1) Settings
# -----------------------------
BASE = "https://api.erg.ic.ac.uk/AirQuality"
TARGET_BOROUGHS = {"Camden", "Greenwich", "Tower Hamlets"}

parser = argparse.ArgumentParser()
parser.add_argument("--start", type=str, required=True)
parser.add_argument("--end",   type=str, required=True)
args = parser.parse_args()

START = date.fromisoformat(args.start)
END   = date.fromisoformat(args.end)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_FILE  = PROJECT_ROOT / "data" / "raw" / "air_quality.json"

# -----------------------------
# 2) Requests session with retry
# -----------------------------
session = requests.Session()
retry = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)
adapter = HTTPAdapter(max_retries=retry)
session.mount("https://", adapter)
session.mount("http://", adapter)

# -----------------------------
# 3) Helpers
# -----------------------------
def as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]

def pick(d, *keys):
    if not isinstance(d, dict):
        return None
    for key in keys:
        if key in d:
            return d[key]
    return None

def format_api_date(dt):
    return dt.strftime("%d %b %Y")

def fetch_json_with_status(url):
    response = session.get(url, timeout=60)
    status_code = response.status_code
    response.raise_for_status()
    return response.json(), status_code

def extract_raw_records(raw_json):
    candidate_paths = [
        ("RawAQData", "Data"),
        ("AirQualityData", "Data"),
        ("SiteSpecies", "Data"),
        ("Data",),
    ]
    for path in candidate_paths:
        current = raw_json
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                break
        else:
            return as_list(current)
    return []

def build_measurement_url(site_code, species_code, start_api, end_api):
    return (
        f"{BASE}/Data/SiteSpecies/"
        f"SiteCode={quote(str(site_code))}/"
        f"SpeciesCode={quote(species_code)}/"
        f"StartDate={start_api}/"
        f"EndDate={end_api}/Json"
    )

# -----------------------------
# 4) Get sites + species metadata
# -----------------------------
sites_json,   sites_status   = fetch_json_with_status(f"{BASE}/Information/MonitoringSiteSpecies/GroupName=London/Json")
species_json, species_status = fetch_json_with_status(f"{BASE}/Information/Species/Json")

species_lookup = {}
species_root = pick(species_json, "AirQualitySpecies", "Species", "SpeciesList", "AirQualitySpeciesList")
species_items = as_list(pick(species_root, "Species")) if isinstance(species_root, dict) else (species_root or [])

for sp in species_items:
    code = pick(sp, "@SpeciesCode", "SpeciesCode")
    if code is not None:
        code = str(code)
        species_lookup[code] = {
            "species_code":  code,
            "species_name":  pick(sp, "@SpeciesName",  "SpeciesName"),
            "description":   pick(sp, "@Description",  "Description"),
            "health_effect": pick(sp, "@HealthEffect", "HealthEffect"),
        }

sites_root = pick(sites_json, "Sites", "MonitoringSiteSpecies", "AirQualityMonitoringSiteSpecies", "AirQualitySites")
site_items = (
    as_list(pick(sites_root, "Site", "MonitoringSite", "Sites", "MonitoringSites"))
    if isinstance(sites_root, dict)
    else (sites_root or [])
)

# -----------------------------
# 5) Build result for target boroughs
# -----------------------------
result = {
    "metadata": {
        "source": "LondonAir / LAQN",
        "start_date": START.isoformat(),
        "end_date":   END.isoformat(),
        "target_boroughs": sorted(TARGET_BOROUGHS),
        "api_status": {
            "sites_endpoint_status":   sites_status,
            "species_endpoint_status": species_status,
        },
    },
    "boroughs": {},
    "status_summary": {},
}

borough_status_summary = {
    borough: {"total_requests": 0, "status_codes": {}, "successful_requests": 0, "failed_requests": 0}
    for borough in TARGET_BOROUGHS
}

start_api = quote(format_api_date(START))
end_api   = quote(format_api_date(END))

for site in site_items:
    borough = pick(site, "@LocalAuthorityName", "LocalAuthorityName", "@LocalAuthority", "LocalAuthority")
    if borough not in TARGET_BOROUGHS:
        continue

    site_code  = pick(site, "@SiteCode",  "SiteCode")
    site_name  = pick(site, "@SiteName",  "SiteName")
    site_type  = pick(site, "@SiteType",  "SiteType")
    latitude   = pick(site, "@Latitude",  "Latitude")
    longitude  = pick(site, "@Longitude", "Longitude")

    pollutants = []
    for sp in as_list(pick(site, "Species", "SpeciesList", "SiteSpecies")):
        if isinstance(sp, dict):
            species_code = pick(sp, "@SpeciesCode", "SpeciesCode")
            species_name = pick(sp, "@SpeciesName", "SpeciesName")
        else:
            species_code = str(sp)
            species_name = None

        if not species_code:
            continue

        species_code = str(species_code)
        meta = species_lookup.get(species_code, {})
        url  = build_measurement_url(site_code, species_code, start_api, end_api)

        status_code   = None
        error_message = None
        try:
            raw_json, status_code = fetch_json_with_status(url)
            measurements = extract_raw_records(raw_json)
        except requests.exceptions.HTTPError as e:
            measurements = []
            error_message = str(e)
            if e.response is not None:
                status_code = e.response.status_code
        except Exception as e:
            measurements = []
            error_message = str(e)

        b_summary = borough_status_summary[borough]
        b_summary["total_requests"] += 1
        b_summary["status_codes"][str(status_code or "NO_STATUS")] = (
            b_summary["status_codes"].get(str(status_code or "NO_STATUS"), 0) + 1
        )
        if status_code == 200:
            b_summary["successful_requests"] += 1
        else:
            b_summary["failed_requests"] += 1

        pollutant_entry = {
            "species_code":        species_code,
            "species_name":        species_name or meta.get("species_name"),
            "description":         meta.get("description"),
            "health_effect":       meta.get("health_effect"),
            "request_status_code": status_code,
            "measurements":        measurements,
        }
        if error_message:
            pollutant_entry["error"] = error_message

        pollutants.append(pollutant_entry)

    result["boroughs"].setdefault(borough, []).append({
        "site_code":           site_code,
        "site_name":           site_name,
        "site_type":           site_type,
        "latitude":            latitude,
        "longitude":           longitude,
        "pollutants_measured": pollutants,
    })

result["status_summary"] = borough_status_summary

# -----------------------------
# 6) Save JSON
# -----------------------------
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"Saved data to: {OUTPUT_FILE}")

print("\nTop-level API status:")
print(f"  MonitoringSiteSpecies endpoint : {sites_status}")
print(f"  Species endpoint               : {species_status}")

print("\nStatus code summary by borough:")
for borough in sorted(borough_status_summary):
    s = borough_status_summary[borough]
    print(f"\n  {borough}")
    print(f"    Total requests    : {s['total_requests']}")
    print(f"    Successful (200)  : {s['successful_requests']}")
    print(f"    Failed / other    : {s['failed_requests']}")
    print(f"    Status codes      : {s['status_codes']}")

print("\nTarget boroughs included:")
for borough in sorted(result["boroughs"]):
    print(f"  - {borough}")
    for site in result["boroughs"][borough]:
        print(f"      {site['site_name']} ({site['site_code']})")