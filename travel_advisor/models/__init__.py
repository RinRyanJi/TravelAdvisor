"""Domain data model for TravelAdvisor.

Everything here is a plain, serialisable Pydantic model with no knowledge of
HTTP, external APIs, or scheduling algorithms. Keeping the vocabulary isolated
lets the providers and the engine evolve independently.
"""

from .place import (
    Coordinates,
    OpeningHours,
    PlaceCategory,
    PointOfInterest,
    TimeInterval,
)
from .trip import Interest, Pace, TripRequest
from .weather import DayWeather, WeatherCondition
from .itinerary import DayPlan, Itinerary, ItemType, ScheduledItem
from .disruption import Disruption, DisruptionType, RescheduleResult

__all__ = [
    # place
    "Coordinates",
    "OpeningHours",
    "PlaceCategory",
    "PointOfInterest",
    "TimeInterval",
    # trip
    "Interest",
    "Pace",
    "TripRequest",
    # weather
    "DayWeather",
    "WeatherCondition",
    # itinerary
    "DayPlan",
    "Itinerary",
    "ItemType",
    "ScheduledItem",
    # disruption
    "Disruption",
    "DisruptionType",
    "RescheduleResult",
]
