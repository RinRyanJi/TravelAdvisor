from datetime import date

from travel_advisor.models import Coordinates, PlaceCategory, WeatherCondition
from travel_advisor.providers import HaversineRoutingProvider
from travel_advisor.providers.base import TravelMode
from travel_advisor.providers.poi import OverpassPoiProvider
from travel_advisor.providers.weather import OpenMeteoWeatherProvider


def test_haversine_routing_grows_with_distance():
    routing = HaversineRoutingProvider()
    near = routing.travel_minutes(
        Coordinates(lat=35.0, lon=135.0), Coordinates(lat=35.01, lon=135.0)
    )
    far = routing.travel_minutes(
        Coordinates(lat=35.0, lon=135.0), Coordinates(lat=35.2, lon=135.0)
    )
    assert 0 < near < far


def test_driving_is_faster_than_walking():
    routing = HaversineRoutingProvider()
    a, b = Coordinates(lat=35.0, lon=135.0), Coordinates(lat=35.1, lon=135.1)
    walk = routing.travel_minutes(a, b, TravelMode.WALK)
    drive = routing.travel_minutes(a, b, TravelMode.DRIVE)
    assert drive < walk


def test_open_meteo_parse_maps_wmo_codes():
    payload = {
        "daily": {
            "time": ["2026-09-01", "2026-09-02"],
            "weathercode": [0, 65],  # clear, heavy rain
            "temperature_2m_max": [28.0, 24.0],
            "temperature_2m_min": [20.0, 19.0],
            "precipitation_probability_max": [5, 90],
        }
    }
    result = OpenMeteoWeatherProvider._parse(payload)
    assert result[date(2026, 9, 1)].condition == WeatherCondition.CLEAR
    rainy = result[date(2026, 9, 2)]
    assert rainy.condition == WeatherCondition.RAIN
    assert rainy.is_wet
    assert rainy.temp_max_c == 24.0


def test_overpass_parse_builds_points_of_interest():
    payload = {
        "elements": [
            {
                "type": "node", "id": 1, "lat": 35.01, "lon": 135.01,
                "tags": {"tourism": "museum", "name": "City Museum"},
            },
            {
                "type": "way", "id": 2, "center": {"lat": 35.02, "lon": 135.02},
                "tags": {"leisure": "park", "name": "Central Park"},
            },
            {  # no name -> skipped
                "type": "node", "id": 3, "lat": 35.0, "lon": 135.0,
                "tags": {"amenity": "cafe"},
            },
        ]
    }
    center = Coordinates(lat=35.0, lon=135.0)
    pois = OverpassPoiProvider._parse(payload, center, limit=10)
    by_name = {p.name: p for p in pois}
    assert set(by_name) == {"City Museum", "Central Park"}
    assert by_name["City Museum"].category == PlaceCategory.MUSEUM
    assert by_name["City Museum"].indoor is True
    assert by_name["Central Park"].category == PlaceCategory.PARK
    assert by_name["Central Park"].indoor is False
