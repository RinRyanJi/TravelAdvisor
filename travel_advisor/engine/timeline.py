"""Lay candidate places out onto a single day's clock.

This is the shared primitive used both when first building an itinerary and when
re-planning a disrupted day, so the two always produce consistent timelines.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from ..models import (
    Coordinates,
    DayPlan,
    DayWeather,
    ItemType,
    PointOfInterest,
    ScheduledItem,
    TripRequest,
)
from ..providers.base import RoutingProvider, TravelMode

MEAL_DURATION_MIN = 60
LUNCH_FROM = time(12, 0)
DINNER_FROM = time(18, 0)


def _item_id(day: date, seq: int) -> str:
    return f"{day.isoformat()}#{seq}"


def layout_day(
    *,
    day: date,
    request: TripRequest,
    anchor: Coordinates,
    candidates: list[PointOfInterest],
    routing: RoutingProvider,
    weather: DayWeather | None = None,
    max_activities: int,
    mode: TravelMode = TravelMode.WALK,
) -> tuple[DayPlan, list[PointOfInterest]]:
    """Place as many ``candidates`` as fit on ``day``.

    Candidates are consumed in priority order. A candidate that cannot fit the
    remaining time or is closed is returned in the leftover list (order
    preserved) so the caller can try it on another day.

    Returns ``(day_plan, leftover_candidates)``.
    """
    day_start = datetime.combine(day, request.day_start)
    day_end = datetime.combine(day, request.day_end)

    # On a wet day, pull sheltered options to the front so we steer indoors.
    ordered = candidates
    if weather is not None and weather.is_wet:
        ordered = sorted(candidates, key=lambda p: not p.indoor)

    queue = list(ordered)
    leftover: list[PointOfInterest] = []

    items: list[ScheduledItem] = []
    clock = day_start
    current = anchor
    placed = 0
    seq = 0
    had_lunch = False
    had_dinner = False

    def add_meal(title: str, at: datetime) -> datetime:
        nonlocal seq
        end = at + timedelta(minutes=MEAL_DURATION_MIN)
        items.append(
            ScheduledItem(
                id=_item_id(day, seq),
                type=ItemType.MEAL,
                title=title,
                start=at,
                end=end,
            )
        )
        seq += 1
        return end

    while queue and placed < max_activities:
        # Insert any meal that has come due at the current location/time.
        if not had_lunch and clock.time() >= LUNCH_FROM and clock + timedelta(minutes=MEAL_DURATION_MIN) <= day_end:
            clock = add_meal("Lunch", clock)
            had_lunch = True
        if not had_dinner and clock.time() >= DINNER_FROM and clock + timedelta(minutes=MEAL_DURATION_MIN) <= day_end:
            clock = add_meal("Dinner", clock)
            had_dinner = True

        poi = queue.pop(0)
        travel = routing.travel_minutes(current, poi.coordinates, mode)
        arrival = clock + timedelta(minutes=travel)
        visit_end = arrival + timedelta(minutes=poi.visit_duration_minutes)

        if visit_end > day_end:
            # Won't fit today; a later, shorter/closer candidate still might.
            leftover.append(poi)
            continue
        if poi.opening_hours is not None and not poi.opening_hours.opens_before_close_on(
            arrival, visit_end.time()
        ):
            leftover.append(poi)
            continue

        items.append(
            ScheduledItem(
                id=_item_id(day, seq),
                type=ItemType.ACTIVITY,
                title=poi.name,
                start=arrival,
                end=visit_end,
                poi=poi,
                travel_from_prev_minutes=travel,
                cost=poi.estimated_cost * request.party_size,
                notes="Indoor" if poi.indoor else "",
            )
        )
        seq += 1
        placed += 1
        clock = visit_end
        current = poi.coordinates

    # Everything still queued is unused by this day.
    leftover.extend(queue)

    # A final chance to seat meals that fit after the last activity.
    if not had_lunch and day_start.time() <= LUNCH_FROM and clock + timedelta(minutes=MEAL_DURATION_MIN) <= day_end and clock.time() >= LUNCH_FROM:
        clock = add_meal("Lunch", clock)
    if not had_dinner and clock.time() >= DINNER_FROM and clock + timedelta(minutes=MEAL_DURATION_MIN) <= day_end:
        add_meal("Dinner", clock)

    items.sort(key=lambda i: i.start)
    return DayPlan(date=day, items=items, weather=weather), leftover
