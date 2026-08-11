"""Disruptions: the events that force an itinerary to be re-planned."""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field

from .itinerary import Itinerary


class DisruptionType(str, Enum):
    """The kinds of change the rescheduler knows how to absorb."""

    # A place is unexpectedly closed (strike, maintenance, holiday).
    POI_CLOSED = "poi_closed"
    # Rain/snow now forecast for a day — steer that day indoors.
    WEATHER_RAIN = "weather_rain"
    # The traveller is running late; everything after a point shifts.
    DELAY = "delay"
    # An intercity transfer (flight/train) was cancelled — a day is lost/shifted.
    TRANSPORT_CANCELLED = "transport_cancelled"


class Disruption(BaseModel):
    """A description of what went wrong and where."""

    type: DisruptionType
    # The day affected. Required for weather/transport, used to scope others.
    date: date
    # The specific timeline item affected (for POI_CLOSED / DELAY).
    target_item_id: str | None = None
    # How many minutes late the traveller is (for DELAY).
    delay_minutes: int | None = None
    description: str = ""
    metadata: dict = Field(default_factory=dict)


class RescheduleResult(BaseModel):
    """The output of a re-plan: the new itinerary plus a human-readable log of
    exactly what changed, so the traveller can see how their day was adjusted."""

    itinerary: Itinerary
    changes: list[str] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.changes)
