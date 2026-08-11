"""The scheduling engine — turn requests into itineraries and re-plan them.

* :class:`ItineraryScheduler` builds a fresh day-by-day plan from a request and
  a set of candidate places, respecting opening hours, travel time, meal times,
  daily pace and the weather forecast.
* :class:`Rescheduler` absorbs a :class:`~travel_advisor.models.Disruption`
  (a closure, rain, a delay, a cancelled transfer) and returns an updated
  itinerary together with a log of exactly what changed.
* :class:`TripPlanner` wires the real data providers to the scheduler so a
  request becomes a plan end-to-end.
"""

from .planner import TripPlanner
from .rescheduler import Rescheduler
from .scheduler import ItineraryScheduler

__all__ = ["TripPlanner", "Rescheduler", "ItineraryScheduler"]
