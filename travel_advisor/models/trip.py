"""The traveller's request — the input to the scheduling engine."""

from __future__ import annotations

from datetime import date, time
from enum import Enum

from pydantic import BaseModel, Field, model_validator

from .place import Coordinates, PlaceCategory


class Interest(str, Enum):
    """High-level traveller interests, mapped to place categories."""

    HISTORY = "history"
    ART = "art"
    NATURE = "nature"
    FOOD = "food"
    SHOPPING = "shopping"
    NIGHTLIFE = "nightlife"
    FAMILY = "family"
    RELAXATION = "relaxation"

    @property
    def categories(self) -> set[PlaceCategory]:
        return _INTEREST_CATEGORIES[self]


_INTEREST_CATEGORIES: dict[Interest, set[PlaceCategory]] = {
    Interest.HISTORY: {PlaceCategory.SIGHT, PlaceCategory.LANDMARK, PlaceCategory.MUSEUM},
    Interest.ART: {PlaceCategory.GALLERY, PlaceCategory.MUSEUM},
    Interest.NATURE: {PlaceCategory.PARK, PlaceCategory.NATURE},
    Interest.FOOD: {PlaceCategory.RESTAURANT, PlaceCategory.CAFE},
    Interest.SHOPPING: {PlaceCategory.SHOPPING},
    Interest.NIGHTLIFE: {PlaceCategory.BAR, PlaceCategory.ENTERTAINMENT},
    Interest.FAMILY: {PlaceCategory.PARK, PlaceCategory.ENTERTAINMENT},
    Interest.RELAXATION: {PlaceCategory.PARK, PlaceCategory.CAFE},
}


class Pace(str, Enum):
    """How densely to pack each day."""

    RELAXED = "relaxed"
    BALANCED = "balanced"
    PACKED = "packed"

    @property
    def max_activities_per_day(self) -> int:
        return {Pace.RELAXED: 2, Pace.BALANCED: 4, Pace.PACKED: 6}[self]


class TripRequest(BaseModel):
    """Everything the engine needs to plan a trip."""

    destination: str
    start_date: date
    end_date: date
    party_size: int = Field(default=1, ge=1)
    interests: list[Interest] = Field(default_factory=list)
    pace: Pace = Pace.BALANCED
    # Optional per-person daily spending cap; None = unconstrained.
    daily_budget: float | None = None
    # Daily active window. Meals and activities are scheduled inside it.
    day_start: time = time(9, 0)
    day_end: time = time(19, 0)
    # Where each day begins/ends (hotel). If omitted the destination centre is
    # resolved by geocoding and used as the anchor.
    base_location: Coordinates | None = None

    @model_validator(mode="after")
    def _check_dates(self) -> "TripRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        if self.day_end <= self.day_start:
            raise ValueError("day_end must be after day_start")
        return self

    @property
    def num_days(self) -> int:
        return (self.end_date - self.start_date).days + 1

    @property
    def wanted_categories(self) -> set[PlaceCategory]:
        cats: set[PlaceCategory] = set()
        for interest in self.interests:
            cats |= interest.categories
        return cats
