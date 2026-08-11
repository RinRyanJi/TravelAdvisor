"""Places: geographic points and the points of interest built on top of them."""

from __future__ import annotations

import math
from datetime import datetime, time
from enum import Enum

from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    """A WGS-84 latitude/longitude pair."""

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)

    def distance_km(self, other: "Coordinates") -> float:
        """Great-circle distance to ``other`` in kilometres (haversine).

        Used as an offline fallback when a routing provider is unavailable,
        and to rank/cluster candidate places before routing is consulted.
        """
        r = 6371.0088  # mean Earth radius, km
        p1, p2 = math.radians(self.lat), math.radians(other.lat)
        dphi = math.radians(other.lat - self.lat)
        dlmb = math.radians(other.lon - self.lon)
        a = (
            math.sin(dphi / 2) ** 2
            + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
        )
        return 2 * r * math.asin(math.sqrt(a))


class PlaceCategory(str, Enum):
    """Coarse category used for interest matching and weather substitution."""

    SIGHT = "sight"
    MUSEUM = "museum"
    GALLERY = "gallery"
    PARK = "park"
    NATURE = "nature"
    LANDMARK = "landmark"
    RESTAURANT = "restaurant"
    CAFE = "cafe"
    BAR = "bar"
    SHOPPING = "shopping"
    ENTERTAINMENT = "entertainment"
    ACCOMMODATION = "accommodation"
    TRANSPORT = "transport"
    OTHER = "other"

    @property
    def is_food(self) -> bool:
        return self in {PlaceCategory.RESTAURANT, PlaceCategory.CAFE, PlaceCategory.BAR}


class TimeInterval(BaseModel):
    """A half-open [opens, closes) window within a single day."""

    opens: time
    closes: time

    def contains(self, t: time) -> bool:
        return self.opens <= t < self.closes


class OpeningHours(BaseModel):
    """A weekly opening schedule.

    ``by_weekday`` maps ``datetime.weekday()`` (Mon=0 .. Sun=6) to the list of
    open intervals for that day. A weekday absent from the mapping means the
    place is closed that day. ``None``/``always_open`` means hours are unknown
    and the place is assumed available (common for open-air landmarks).
    """

    by_weekday: dict[int, list[TimeInterval]] = Field(default_factory=dict)
    always_open: bool = False

    @classmethod
    def open_always(cls) -> "OpeningHours":
        return cls(always_open=True)

    @classmethod
    def daily(cls, opens: time, closes: time) -> "OpeningHours":
        """Same window every day of the week."""
        interval = TimeInterval(opens=opens, closes=closes)
        return cls(by_weekday={d: [interval] for d in range(7)})

    def is_open_at(self, when: datetime) -> bool:
        if self.always_open:
            return True
        intervals = self.by_weekday.get(when.weekday())
        if not intervals:
            return False
        t = when.time()
        return any(iv.contains(t) for iv in intervals)

    def opens_before_close_on(self, when: datetime, needed_end: time) -> bool:
        """True if there is a window on ``when``'s weekday that is still open at
        ``when`` and stays open until at least ``needed_end`` — i.e. a visit
        starting now can finish before closing."""
        if self.always_open:
            return True
        for iv in self.by_weekday.get(when.weekday(), []):
            if iv.contains(when.time()) and needed_end <= iv.closes:
                return True
        return False


class PointOfInterest(BaseModel):
    """Something a traveller can spend time at: a sight, a museum, a meal, etc."""

    id: str
    name: str
    category: PlaceCategory
    coordinates: Coordinates
    # Whether the activity is sheltered from weather — drives rain substitution.
    indoor: bool = False
    opening_hours: OpeningHours | None = None
    # Typical time a visitor spends here, in minutes.
    visit_duration_minutes: int = 60
    # Rough per-person cost in the trip's currency (0 = free).
    estimated_cost: float = 0.0
    rating: float | None = None
    interests: set[str] = Field(default_factory=set)
    source: str = "manual"
    raw: dict = Field(default_factory=dict)

    def is_available_at(self, when: datetime) -> bool:
        if self.opening_hours is None:
            return True
        return self.opening_hours.is_open_at(when)
