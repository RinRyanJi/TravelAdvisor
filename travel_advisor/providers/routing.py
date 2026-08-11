"""Travel-time estimation: OSRM with a built-in offline fallback."""

from __future__ import annotations

import math

import httpx

from ..models import Coordinates
from .base import TravelMode
from .http import new_client

# Average door-to-door speeds (km/h) including the friction of real travel:
# waiting, parking, stairs, etc. Deliberately conservative.
_SPEED_KMH: dict[TravelMode, float] = {
    TravelMode.WALK: 4.5,
    TravelMode.CYCLE: 12.0,
    TravelMode.DRIVE: 22.0,
}

_OSRM_PROFILE: dict[TravelMode, str] = {
    TravelMode.WALK: "walking",
    TravelMode.CYCLE: "cycling",
    TravelMode.DRIVE: "driving",
}


def _haversine_minutes(a: Coordinates, b: Coordinates, mode: TravelMode) -> int:
    straight_km = a.distance_km(b)
    # Real routes are longer than the crow-flies distance; 1.3 is a common
    # detour factor for street networks.
    route_km = straight_km * 1.3
    minutes = route_km / _SPEED_KMH[mode] * 60
    return max(1, math.ceil(minutes))


class HaversineRoutingProvider:
    """Offline routing estimate from great-circle distance and a mode speed.

    Requires no network — used directly in tests and as the fallback inside
    :class:`OsrmRoutingProvider`.
    """

    def travel_minutes(
        self,
        origin: Coordinates,
        destination: Coordinates,
        mode: TravelMode = TravelMode.WALK,
    ) -> int:
        return _haversine_minutes(origin, destination, mode)


class OsrmRoutingProvider:
    """Travel time from the public OSRM router, falling back to haversine.

    If OSRM is unreachable or returns no route, we degrade gracefully to the
    haversine estimate rather than failing the whole plan — travel time is an
    input the engine can tolerate being approximate.
    """

    BASE_URL = "https://router.project-osrm.org"

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or self.BASE_URL
        self._fallback = HaversineRoutingProvider()

    def travel_minutes(
        self,
        origin: Coordinates,
        destination: Coordinates,
        mode: TravelMode = TravelMode.WALK,
    ) -> int:
        profile = _OSRM_PROFILE[mode]
        coords = f"{origin.lon},{origin.lat};{destination.lon},{destination.lat}"
        try:
            with new_client(self._base_url) as client:
                resp = client.get(f"/route/v1/{profile}/{coords}", params={"overview": "false"})
                resp.raise_for_status()
                data = resp.json()
            routes = data.get("routes") or []
            if not routes:
                return self._fallback.travel_minutes(origin, destination, mode)
            seconds = routes[0]["duration"]
            return max(1, math.ceil(seconds / 60))
        except (httpx.HTTPError, KeyError, ValueError):
            return self._fallback.travel_minutes(origin, destination, mode)
