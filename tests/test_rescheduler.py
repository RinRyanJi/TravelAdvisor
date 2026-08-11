from datetime import datetime, timedelta

import pytest

from travel_advisor.engine import ItineraryScheduler, Rescheduler
from travel_advisor.models import Disruption, DisruptionType
from travel_advisor.providers import HaversineRoutingProvider
from travel_advisor.samples import KYOTO_BASE, KYOTO_POIS, sample_kyoto_request

ROUTING = HaversineRoutingProvider()


@pytest.fixture
def planned():
    request = sample_kyoto_request()
    itinerary = ItineraryScheduler(ROUTING).build(request, KYOTO_POIS, anchor=KYOTO_BASE)
    used = itinerary.scheduled_poi_ids()
    spares = [p for p in KYOTO_POIS if p.id not in used]
    return request, itinerary, spares


def _first_activity(itinerary):
    for day in itinerary.days:
        for item in day.activities:
            return day, item
    raise AssertionError("itinerary has no activities")


def test_closure_removes_the_poi_and_bumps_revision(planned):
    _, itinerary, spares = planned
    _, item = _first_activity(itinerary)
    closed_poi_id = item.poi.id
    result = Rescheduler(ROUTING).reschedule(
        itinerary,
        Disruption(type=DisruptionType.POI_CLOSED, date=item.start.date(), target_item_id=item.id),
        spare_pois=spares,
    )
    assert result.itinerary.revision == itinerary.revision + 1
    # The closed POI is gone from the whole plan.
    assert closed_poi_id not in result.itinerary.scheduled_poi_ids()
    assert result.changed


def test_weather_steers_a_day_indoors(planned):
    request, itinerary, spares = planned
    target_date = request.start_date
    result = Rescheduler(ROUTING).reschedule(
        itinerary,
        Disruption(type=DisruptionType.WEATHER_RAIN, date=target_date),
        spare_pois=spares,
    )
    day = result.itinerary.day_for(target_date)
    assert day.weather is not None and day.weather.is_wet
    activities = day.activities
    if activities:
        # First stop of a rainy day should be sheltered.
        assert activities[0].poi.indoor is True


def test_delay_drops_overflow_and_keeps_window(planned):
    request, itinerary, _ = planned
    target_date = request.start_date
    before = len(itinerary.day_for(target_date).items)
    result = Rescheduler(ROUTING).reschedule(
        itinerary,
        Disruption(type=DisruptionType.DELAY, date=target_date, delay_minutes=300),
    )
    day = result.itinerary.day_for(target_date)
    window_end = datetime.combine(target_date, request.day_end)
    for item in day.items:
        assert item.end <= window_end
    assert len(day.items) <= before


def test_transport_cancellation_clears_the_day(planned):
    request, itinerary, _ = planned
    target_date = request.start_date
    result = Rescheduler(ROUTING).reschedule(
        itinerary,
        Disruption(type=DisruptionType.TRANSPORT_CANCELLED, date=target_date),
    )
    day = result.itinerary.day_for(target_date)
    assert day.items == []
    assert "rebooking" in day.notes.lower()


def test_reschedule_does_not_mutate_the_original(planned):
    _, itinerary, spares = planned
    _, item = _first_activity(itinerary)
    original_ids = itinerary.scheduled_poi_ids()
    Rescheduler(ROUTING).reschedule(
        itinerary,
        Disruption(type=DisruptionType.POI_CLOSED, date=item.start.date(), target_item_id=item.id),
        spare_pois=spares,
    )
    assert itinerary.scheduled_poi_ids() == original_ids
    assert itinerary.revision == 0
