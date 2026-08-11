"""The itinerary: the engine's output and the thing that gets re-planned."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, computed_field

from .place import PointOfInterest
from .trip import TripRequest
from .weather import DayWeather


class ItemType(str, Enum):
    ACTIVITY = "activity"
    MEAL = "meal"
    TRANSFER = "transfer"
    FREE = "free"


class ScheduledItem(BaseModel):
    """One time-boxed entry on a day's timeline."""

    id: str
    type: ItemType
    title: str
    start: datetime
    end: datetime
    poi: PointOfInterest | None = None
    # Minutes spent travelling from the previous item's location to this one.
    travel_from_prev_minutes: int = 0
    cost: float = 0.0
    notes: str = ""

    @property
    def duration_minutes(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)


class DayPlan(BaseModel):
    """A single day of the trip."""

    date: date
    items: list[ScheduledItem] = Field(default_factory=list)
    weather: DayWeather | None = None
    notes: str = ""

    @computed_field  # serialised into API responses
    @property
    def total_cost(self) -> float:
        return sum(item.cost for item in self.items)

    @property
    def activities(self) -> list[ScheduledItem]:
        return [i for i in self.items if i.type == ItemType.ACTIVITY]

    def item_by_id(self, item_id: str) -> ScheduledItem | None:
        return next((i for i in self.items if i.id == item_id), None)


class Itinerary(BaseModel):
    """A full trip plan: the request plus a plan for every day."""

    request: TripRequest
    days: list[DayPlan] = Field(default_factory=list)
    # Bumped every time the rescheduler produces a new version.
    revision: int = 0

    @computed_field  # serialised into API responses
    @property
    def total_cost(self) -> float:
        return sum(day.total_cost for day in self.days)

    def day_for(self, on: date) -> DayPlan | None:
        return next((d for d in self.days if d.date == on), None)

    def find_item(self, item_id: str) -> tuple[DayPlan, ScheduledItem] | None:
        for day in self.days:
            item = day.item_by_id(item_id)
            if item is not None:
                return day, item
        return None

    def scheduled_poi_ids(self) -> set[str]:
        return {i.poi.id for d in self.days for i in d.items if i.poi is not None}
