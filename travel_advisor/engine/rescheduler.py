"""Re-plan an itinerary when reality diverges from the plan."""

from __future__ import annotations

from datetime import datetime, timedelta

from ..models import (
    Coordinates,
    DayPlan,
    Disruption,
    DisruptionType,
    Itinerary,
    ItemType,
    PointOfInterest,
    RescheduleResult,
    TripRequest,
    WeatherCondition,
)
from ..models.weather import DayWeather
from ..providers.base import RoutingProvider, TravelMode
from .scheduler import _nearest_neighbour_order
from .timeline import layout_day


def _resolve_anchor(itinerary: Itinerary) -> Coordinates:
    req = itinerary.request
    if req.base_location is not None:
        return req.base_location
    coords = [i.poi.coordinates for d in itinerary.days for i in d.items if i.poi is not None]
    if not coords:
        return Coordinates(lat=0.0, lon=0.0)
    return Coordinates(
        lat=sum(c.lat for c in coords) / len(coords),
        lon=sum(c.lon for c in coords) / len(coords),
    )


def _day_poi_names(day: DayPlan) -> set[str]:
    return {i.poi.name for i in day.items if i.poi is not None}


class Rescheduler:
    """Absorb a disruption and produce an updated itinerary + change log.

    Like the scheduler, it is deterministic and network-free: pass in any spare
    candidate places you want it to draw replacements from.
    """

    def __init__(self, routing: RoutingProvider, *, mode: TravelMode = TravelMode.WALK) -> None:
        self._routing = routing
        self._mode = mode

    def reschedule(
        self,
        itinerary: Itinerary,
        disruption: Disruption,
        *,
        spare_pois: list[PointOfInterest] | None = None,
    ) -> RescheduleResult:
        working = itinerary.model_copy(deep=True)
        working.revision += 1
        spare_pois = spare_pois or []

        handlers = {
            DisruptionType.POI_CLOSED: self._handle_closure,
            DisruptionType.WEATHER_RAIN: self._handle_weather,
            DisruptionType.DELAY: self._handle_delay,
            DisruptionType.TRANSPORT_CANCELLED: self._handle_transport,
        }
        handler = handlers[disruption.type]
        return handler(working, disruption, spare_pois)

    # -- individual disruption handlers ------------------------------------

    def _handle_closure(
        self,
        itin: Itinerary,
        disruption: Disruption,
        spare_pois: list[PointOfInterest],
    ) -> RescheduleResult:
        found = itin.find_item(disruption.target_item_id) if disruption.target_item_id else None
        if found is None:
            return RescheduleResult(
                itinerary=itin,
                unresolved=[f"Could not find item '{disruption.target_item_id}' to close."],
            )
        day, closed_item = found
        closed_name = closed_item.title
        closed_poi = closed_item.poi

        # Keep the day's other activities; drop the closed one.
        kept = [i.poi for i in day.items if i.poi is not None and i.id != closed_item.id]

        # Pick the best unused spare, preferring the same category, to fill the gap.
        replacement = self._pick_replacement(itin, spare_pois, like=closed_poi)
        candidates = kept + ([replacement] if replacement else [])

        anchor = _resolve_anchor(itin)
        new_day, _ = self._relayout(day, itin.request, anchor, candidates, day.weather)
        self._replace_day(itin, new_day)

        changes = [f"'{closed_name}' was closed and removed from {day.date.isoformat()}."]
        if replacement and replacement.name in _day_poi_names(new_day):
            changes.append(f"Added '{replacement.name}' in its place.")
        elif replacement:
            changes.append(f"Considered '{replacement.name}' but it did not fit the day.")
        else:
            changes.append("No suitable replacement was available; the day has one fewer stop.")
        return RescheduleResult(itinerary=itin, changes=changes)

    def _handle_weather(
        self,
        itin: Itinerary,
        disruption: Disruption,
        spare_pois: list[PointOfInterest],
    ) -> RescheduleResult:
        day = itin.day_for(disruption.date)
        if day is None:
            return RescheduleResult(
                itinerary=itin,
                unresolved=[f"No plan exists for {disruption.date.isoformat()}."],
            )
        before = _day_poi_names(day)

        # Mark the day wet so the layout steers indoors.
        day.weather = DayWeather(date=day.date, condition=WeatherCondition.RAIN, precipitation_probability=90)

        existing = [i.poi for i in day.items if i.poi is not None]
        indoor_spares = [p for p in self._unused(itin, spare_pois) if p.indoor]
        candidates = existing + indoor_spares

        anchor = _resolve_anchor(itin)
        new_day, _ = self._relayout(day, itin.request, anchor, candidates, day.weather)
        self._replace_day(itin, new_day)

        after = _day_poi_names(new_day)
        added = sorted(after - before)
        removed = sorted(before - after)
        changes = [f"Rain forecast for {day.date.isoformat()}; the day was steered towards indoor stops."]
        if added:
            changes.append("Added indoor: " + ", ".join(added) + ".")
        if removed:
            changes.append("Dropped outdoor: " + ", ".join(removed) + ".")
        if not added and not removed:
            changes.append("Existing stops were already weather-proof; only the order was reviewed.")
        return RescheduleResult(itinerary=itin, changes=changes)

    def _handle_delay(
        self,
        itin: Itinerary,
        disruption: Disruption,
        _spare_pois: list[PointOfInterest],
    ) -> RescheduleResult:
        day = itin.day_for(disruption.date)
        if day is None:
            return RescheduleResult(
                itinerary=itin,
                unresolved=[f"No plan exists for {disruption.date.isoformat()}."],
            )
        delay = disruption.delay_minutes or 0
        if delay <= 0:
            return RescheduleResult(itinerary=itin, changes=[], unresolved=["Delay had no duration."])

        # Shift the target item and everything after it later by the delay.
        start_index = 0
        if disruption.target_item_id:
            idx = next((n for n, i in enumerate(day.items) if i.id == disruption.target_item_id), None)
            if idx is not None:
                start_index = idx

        shift = timedelta(minutes=delay)
        for item in day.items[start_index:]:
            item.start += shift
            item.end += shift

        day_end = datetime.combine(day.date, itin.request.day_end)
        kept = [i for i in day.items if i.end <= day_end]
        dropped = [i for i in day.items if i.end > day_end]
        day.items = kept

        changes = [f"Running {delay} min late on {day.date.isoformat()}; later stops were pushed back."]
        if dropped:
            names = ", ".join(i.title for i in dropped)
            changes.append(f"No longer fit before the day ends and were dropped: {names}.")
        return RescheduleResult(itinerary=itin, changes=changes)

    def _handle_transport(
        self,
        itin: Itinerary,
        disruption: Disruption,
        _spare_pois: list[PointOfInterest],
    ) -> RescheduleResult:
        day = itin.day_for(disruption.date)
        if day is None:
            return RescheduleResult(
                itinerary=itin,
                unresolved=[f"No plan exists for {disruption.date.isoformat()}."],
            )
        stranded = [i.poi for i in day.items if i.poi is not None]

        # The affected day is cleared for re-booking the transfer.
        day.items = []
        day.notes = "Transfer cancelled — day reserved for rebooking."

        changes = [f"Transfer on {day.date.isoformat()} was cancelled; the day was cleared for rebooking."]

        # Try to rehome the stranded activities on later days that have room.
        anchor = _resolve_anchor(itin)
        rehomed: list[str] = []
        queue = list(stranded)
        for later in itin.days:
            if not queue:
                break
            if later.date <= day.date:
                continue
            existing = [i.poi for i in later.items if i.poi is not None]
            candidates = existing + queue
            new_day, leftover = self._relayout(later, itin.request, anchor, candidates, later.weather)
            newly = _day_poi_names(new_day) - _day_poi_names(later)
            if newly:
                rehomed.extend(sorted(newly))
            self._replace_day(itin, new_day)
            queue = [p for p in queue if p.name not in _day_poi_names(new_day)]

        if rehomed:
            changes.append("Moved to later days: " + ", ".join(rehomed) + ".")
        unresolved = []
        if queue:
            unresolved.append("Could not rehome: " + ", ".join(p.name for p in queue) + ".")
        return RescheduleResult(itinerary=itin, changes=changes, unresolved=unresolved)

    # -- helpers -----------------------------------------------------------

    def _relayout(
        self,
        day: DayPlan,
        request: TripRequest,
        anchor: Coordinates,
        candidates: list[PointOfInterest],
        weather: DayWeather | None,
    ) -> tuple[DayPlan, list[PointOfInterest]]:
        ordered = _nearest_neighbour_order(anchor, candidates)
        return layout_day(
            day=day.date,
            request=request,
            anchor=anchor,
            candidates=ordered,
            routing=self._routing,
            weather=weather,
            max_activities=request.pace.max_activities_per_day,
            mode=self._mode,
        )

    @staticmethod
    def _replace_day(itin: Itinerary, new_day: DayPlan) -> None:
        for n, d in enumerate(itin.days):
            if d.date == new_day.date:
                itin.days[n] = new_day
                return

    @staticmethod
    def _unused(itin: Itinerary, spares: list[PointOfInterest]) -> list[PointOfInterest]:
        used = itin.scheduled_poi_ids()
        return [p for p in spares if p.id not in used]

    def _pick_replacement(
        self,
        itin: Itinerary,
        spares: list[PointOfInterest],
        *,
        like: PointOfInterest | None,
    ) -> PointOfInterest | None:
        unused = self._unused(itin, spares)
        if not unused:
            return None
        if like is not None:
            same = [p for p in unused if p.category == like.category]
            if same:
                return same[0]
        return unused[0]
