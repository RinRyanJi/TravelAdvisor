"""Geocoding via OpenStreetMap Nominatim (free, key-less)."""

from __future__ import annotations

from ..models import Coordinates
from .http import new_client


class NominatimGeocoder:
    """Resolve a place name to coordinates.

    Nominatim's usage policy asks for a valid User-Agent (set in ``http.py``)
    and at most ~1 request/second; for trip planning we geocode once per trip
    so that is comfortably within bounds.
    """

    BASE_URL = "https://nominatim.openstreetmap.org"

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or self.BASE_URL

    def geocode(self, query: str) -> Coordinates | None:
        params = {"q": query, "format": "jsonv2", "limit": 1}
        with new_client(self._base_url) as client:
            resp = client.get("/search", params=params)
            resp.raise_for_status()
            results = resp.json()
        if not results:
            return None
        top = results[0]
        return Coordinates(lat=float(top["lat"]), lon=float(top["lon"]))
