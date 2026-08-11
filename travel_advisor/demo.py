"""An offline planner backed by the built-in sample dataset.

The live planner needs outbound access to open-data services. For demos, tests,
and any environment where that access is unavailable, this planner wires the
same :class:`~travel_advisor.engine.TripPlanner` to in-process sample data so a
request still yields a real, fully-scheduled plan (respecting the request's
dates, pace, interests and party size).
"""

from __future__ import annotations

from datetime import date

from .engine import TripPlanner
from .models import Coordinates, DayWeather, PlaceCategory, PointOfInterest
from .providers import HaversineRoutingProvider
from .samples import KYOTO_BASE, KYOTO_POIS


class _SampleGeocoder:
    def geocode(self, query: str) -> Coordinates:
        return KYOTO_BASE


class _SamplePoiProvider:
    def find_pois(
        self,
        center: Coordinates,
        *,
        categories: set[PlaceCategory],
        radius_m: int = 4000,
        limit: int = 60,
    ) -> list[PointOfInterest]:
        return list(KYOTO_POIS)


class _SampleWeatherProvider:
    def forecast(self, coords: Coordinates, start: date, end: date) -> dict[date, DayWeather]:
        # No forecast in offline mode; the engine treats this as "no signal".
        return {}


def build_sample_planner() -> TripPlanner:
    """A :class:`TripPlanner` that plans entirely from built-in sample data."""
    return TripPlanner(
        geocoder=_SampleGeocoder(),
        poi_provider=_SamplePoiProvider(),
        weather_provider=_SampleWeatherProvider(),
        routing=HaversineRoutingProvider(),
    )
