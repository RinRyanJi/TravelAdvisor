"""Provider protocols — the contract between the engine and the outside world."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Protocol, runtime_checkable

from ..models import Coordinates, DayWeather, PlaceCategory, PointOfInterest


class TravelMode(str, Enum):
    WALK = "walk"
    DRIVE = "drive"
    CYCLE = "cycle"


@runtime_checkable
class GeocodingProvider(Protocol):
    """Resolve a free-text place name to coordinates."""

    def geocode(self, query: str) -> Coordinates | None: ...


@runtime_checkable
class PoiProvider(Protocol):
    """Find candidate points of interest around a location."""

    def find_pois(
        self,
        center: Coordinates,
        *,
        categories: set[PlaceCategory],
        radius_m: int = 4000,
        limit: int = 60,
    ) -> list[PointOfInterest]: ...


@runtime_checkable
class WeatherProvider(Protocol):
    """Forecast weather for a place across a date range."""

    def forecast(
        self,
        coords: Coordinates,
        start: date,
        end: date,
    ) -> dict[date, DayWeather]: ...


@runtime_checkable
class RoutingProvider(Protocol):
    """Estimate travel time between two points."""

    def travel_minutes(
        self,
        origin: Coordinates,
        destination: Coordinates,
        mode: TravelMode = TravelMode.WALK,
    ) -> int: ...
