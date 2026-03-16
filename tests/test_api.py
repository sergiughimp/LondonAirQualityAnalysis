import pytest
import requests


BASE = "https://api.erg.ic.ac.uk/AirQuality"


def test_api_species_endpoint_reachable():
    url = f"{BASE}/Information/Species/Json"
    response = requests.get(url, timeout=10)
    assert response.status_code == 200, f"Species endpoint returned {response.status_code}"


def test_api_sites_endpoint_reachable():
    url = f"{BASE}/Information/MonitoringSiteSpecies/GroupName=London/Json"
    response = requests.get(url, timeout=10)
    assert response.status_code == 200, f"Sites endpoint returned {response.status_code}"


def test_api_returns_json():
    url = f"{BASE}/Information/Species/Json"
    response = requests.get(url, timeout=10)
    data = response.json()
    assert isinstance(data, dict), "API response is not a JSON object"
