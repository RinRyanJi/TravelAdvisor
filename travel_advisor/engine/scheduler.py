"""Build a fresh itinerary from a request and a pool of candidate places."""

from __future__ import annotations

from datetime import date, timedelta

from ..models import (
    Coordinates,
    DayWeather,
    Itinerary,
    PointOfInterest,
    TripRequest,
)
from ..providers.base import RoutingProvider, TravelMode
from .timeline import layout_day


def _score(poi: PointOfInterest, request: TripRequest, anchor: Coordinates) -> float:
    """Rank a candidate: interest match dominates, rating breaks ties, distance
    gently penalises far-flung options."""
    score = 0.0
    if poi.category in request.wanted_categories:
        score += 5.0
    score += (poi.rating or 3.0)
    score -= anchor.distance_km(poi.coordinates) * 0.1
    return score


def _nearest_neighbour_order(
    anchor: Coordinates,
    pois: list[PointOfInterest],
) -> list[PointOfInterest]:
    """Greedy route starting from ``anchor`` so consecutive picks stay close,
    which keeps each day geographically coherent when the route is chunked."""
    remaining = list(pois)
    ordered: list[PointOfInterest] = []
    current = anchor
    while remaining:
        nxt = min(remaining, key=lambda p: current.distance_km(p.coordinates))
        ordered.append(nxt)
        remaining.remove(nxt)
        current = nxt.coordinates
    return ordered


class ItineraryScheduler:
    """Turn a :class:`TripRequest` plus candidate POIs into an itinerary.

    The scheduler is pure: given the same inputs it produces the same plan, and
    it never touches the network — all external data (places, weather, travel
    times) is injected. That makes the core logic fast and deterministic to test.
    """

    def __init__(self, routing: RoutingProvider, *, mode: TravelMode = TravelMode.WALK) -> None:
        self._routing = routing
        self._mode = mode

    def build(
        self,
        request: TripRequest,
        pois: list[PointOfInterest],
        *,
        anchor: Coordinates | None = None,
        weather: dict[date, DayWeather] | None = None,
    ) -> Itinerary:
        weather = weather or {}
        anchor = anchor or request.base_location or self._fallback_anchor(pois)
        max_per_day = request.pace.max_activities_per_day

        # Select the strongest candidates, then route them for locality.
        pool = sorted(pois, key=lambda p: _score(p, request, anchor), reverse=True)
        pool = pool[: max_per_day * request.num_days]
        route = _nearest_neighbour_order(anchor, pool)

        itinerary = Itinerary(request=request, days=[])
        remaining = route
        for offset in range(request.num_days):
            day = request.start_date + timedelta(days=offset)
            day_plan, remaining = layout_day(
                day=day,
                request=request,
                anchor=anchor,
                candidates=remaining,
                routing=self._routing,
                weather=weather.get(day),
                max_activities=max_per_day,
                mode=self._mode,
            )
            itinerary.days.append(day_plan)
        return itinerary

    @staticmethod
    def _fallback_anchor(pois: list[PointOfInterest]) -> Coordinates:
        if not pois:
            # No places and no base — default to (0,0); the plan will be empty.
            return Coordinates(lat=0.0, lon=0.0)
        lat = sum(p.coordinates.lat for p in pois) / len(pois)
        lon = sum(p.coordinates.lon for p in pois) / len(pois)
        return Coordinates(lat=lat, lon=lon)
