from datetime import datetime

from travel_advisor.engine import ItineraryScheduler
from travel_advisor.providers import HaversineRoutingProvider
from travel_advisor.samples import KYOTO_BASE, KYOTO_POIS, sample_kyoto_request

ROUTING = HaversineRoutingProvider()


def _build():
    request = sample_kyoto_request()
    scheduler = ItineraryScheduler(ROUTING)
    return request, scheduler.build(request, KYOTO_POIS, anchor=KYOTO_BASE)


def test_build_produces_one_plan_per_day():
    request, itinerary = _build()
    assert len(itinerary.days) == request.num_days
    for offset, day in enumerate(itinerary.days):
        assert day.date == request.start_date.fromordinal(request.start_date.toordinal() + offset)


def test_respects_pace_cap_and_schedules_something():
    request, itinerary = _build()
    total_activities = 0
    for day in itinerary.days:
        assert len(day.activities) <= request.pace.max_activities_per_day
        total_activities += len(day.activities)
    assert total_activities > 0


def test_no_poi_is_scheduled_twice():
    _, itinerary = _build()
    seen = [i.poi.id for d in itinerary.days for i in d.items if i.poi]
    assert len(seen) == len(set(seen))


def test_all_items_fall_within_the_daily_window():
    request, itinerary = _build()
    for day in itinerary.days:
        window_start = datetime.combine(day.date, request.day_start)
        window_end = datetime.combine(day.date, request.day_end)
        for item in day.items:
            assert window_start <= item.start <= item.end <= window_end


def test_costs_scale_with_party_size():
    request, itinerary = _build()
    # party_size is 2 in the sample; a paid activity should reflect that.
    paid = [i for d in itinerary.days for i in d.items if i.poi and i.poi.estimated_cost > 0]
    assert paid, "sample data should include at least one paid attraction"
    sample = paid[0]
    assert sample.cost == sample.poi.estimated_cost * request.party_size
