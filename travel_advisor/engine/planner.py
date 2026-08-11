"""End-to-end orchestration: real data providers wired to the scheduler."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ..models import (
    Coordinates,
    DayWeather,
    Itinerary,
    PlaceCategory,
    PointOfInterest,
    TripRequest,
)
from ..providers import (
    NominatimGeocoder,
    OpenMeteoWeatherProvider,
    OsrmRoutingProvider,
    OverpassPoiProvider,
)
from ..providers.base import (
    GeocodingProvider,
    PoiProvider,
    RoutingProvider,
    TravelMode,
    WeatherProvider,
)
from .scheduler import ItineraryScheduler

# When the traveller expresses no interests, plan a well-rounded sightseeing mix.
_DEFAULT_CATEGORIES: set[PlaceCategory] = {
    PlaceCategory.SIGHT,
    PlaceCategory.LANDMARK,
    PlaceCategory.MUSEUM,
    PlaceCategory.PARK,
    PlaceCategory.GALLERY,
}
_INDOOR_CATEGORIES = {PlaceCategory.MUSEUM, PlaceCategory.GALLERY}


@dataclass
class PlannedTrip:
    """A plan plus the context needed to re-plan it later."""

    itinerary: Itinerary
    candidates: list[PointOfInterest]
    anchor: Coordinates
    weather: dict[date, DayWeather] = field(default_factory=dict)

    @property
    def spare_pois(self) -> list[PointOfInterest]:
        """Candidates that were fetched but not placed — the pool the
        rescheduler draws replacements from."""
        used = self.itinerary.scheduled_poi_ids()
        return [p for p in self.candidates if p.id not in used]


class TripPlanner:
    """The service entry point: a :class:`TripRequest` in, a plan out.

    Providers are injected so the whole pipeline can be exercised with fakes in
    tests; the defaults are the real open-data services.
    """

    def __init__(
        self,
        *,
        geocoder: GeocodingProvider | None = None,
        poi_provider: PoiProvider | None = None,
        weather_provider: WeatherProvider | None = None,
        routing: RoutingProvider | None = None,
        mode: TravelMode = TravelMode.WALK,
        search_radius_m: int = 5000,
        candidate_limit: int = 80,
    ) -> None:
        self._geocoder = geocoder or NominatimGeocoder()
        self._poi = poi_provider or OverpassPoiProvider()
        self._weather = weather_provider or OpenMeteoWeatherProvider()
        self._routing = routing or OsrmRoutingProvider()
        self._scheduler = ItineraryScheduler(self._routing, mode=mode)
        self._radius = search_radius_m
        self._limit = candidate_limit

    def resolve_anchor(self, request: TripRequest) -> Coordinates:
        if request.base_location is not None:
            return request.base_location
        coords = self._geocoder.geocode(request.destination)
        if coords is None:
            raise ValueError(f"Could not geocode destination: {request.destination!r}")
        return coords

    def categories_for(self, request: TripRequest) -> set[PlaceCategory]:
        categories = set(request.wanted_categories) or set(_DEFAULT_CATEGORIES)
        # Guarantee at least one indoor category so wet-day re-planning has
        # something to fall back on.
        if not (categories & _INDOOR_CATEGORIES):
            categories.add(PlaceCategory.MUSEUM)
        return categories

    def find_candidates(
        self,
        request: TripRequest,
        anchor: Coordinates,
    ) -> list[PointOfInterest]:
        return self._poi.find_pois(
            anchor,
            categories=self.categories_for(request),
            radius_m=self._radius,
            limit=self._limit,
        )

    def plan(self, request: TripRequest) -> PlannedTrip:
        anchor = self.resolve_anchor(request)
        weather = self._weather.forecast(anchor, request.start_date, request.end_date)
        candidates = self.find_candidates(request, anchor)
        itinerary = self._scheduler.build(
            request, candidates, anchor=anchor, weather=weather
        )
        return PlannedTrip(
            itinerary=itinerary,
            candidates=candidates,
            anchor=anchor,
            weather=weather,
        )
