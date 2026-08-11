"""Adapters to real, up-to-date external data.

Each provider is defined as a small ``typing.Protocol`` in :mod:`base` so the
engine depends only on the shape of the data, never on a concrete API. The
default implementations use free, key-less open services:

* Geocoding / places — OpenStreetMap (Nominatim + Overpass)
* Weather            — Open-Meteo
* Routing            — OSRM (with a haversine fallback baked in)

Swapping in a commercial API (Google Places, a GDS for flights, …) later means
writing one class that satisfies the same protocol — nothing in the engine
changes.
"""

from .base import (
    GeocodingProvider,
    PoiProvider,
    RoutingProvider,
    TravelMode,
    WeatherProvider,
)
from .geocoding import NominatimGeocoder
from .poi import OverpassPoiProvider
from .routing import HaversineRoutingProvider, OsrmRoutingProvider
from .weather import OpenMeteoWeatherProvider

__all__ = [
    "GeocodingProvider",
    "PoiProvider",
    "RoutingProvider",
    "TravelMode",
    "WeatherProvider",
    "NominatimGeocoder",
    "OverpassPoiProvider",
    "HaversineRoutingProvider",
    "OsrmRoutingProvider",
    "OpenMeteoWeatherProvider",
]
