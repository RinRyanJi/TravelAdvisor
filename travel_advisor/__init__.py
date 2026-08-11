"""TravelAdvisor — automated travel itinerary scheduling service.

The package is organised in three layers that mirror the product goals:

* ``models``    — the domain data model (trip requests, places, itineraries,
  disruptions). This is the shared vocabulary every other layer speaks.
* ``providers`` — adapters to real, up-to-date external data (weather, places,
  routing/travel-time). They hide the outside world behind small protocols so
  the engine never depends on a specific API.
* ``engine``    — the scheduling logic: turn a request plus candidate places
  into a day-by-day itinerary, and re-plan it when a disruption occurs.
"""

__version__ = "0.1.0"
