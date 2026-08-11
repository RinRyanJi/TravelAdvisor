from datetime import date, datetime, time

from travel_advisor.engine.timeline import layout_day
from travel_advisor.models import (
    Coordinates,
    DayWeather,
    ItemType,
    Pace,
    PlaceCategory,
    PointOfInterest,
    TripRequest,
    WeatherCondition,
)
from travel_advisor.providers import HaversineRoutingProvider

ANCHOR = Coordinates(lat=35.0, lon=135.0)
ROUTING = HaversineRoutingProvider()


def _poi(pid: str, *, indoor: bool, dur: int = 60, lat=35.0, lon=135.0):
    return PointOfInterest(
        id=pid, name=pid, category=PlaceCategory.MUSEUM if indoor else PlaceCategory.PARK,
        coordinates=Coordinates(lat=lat, lon=lon), indoor=indoor, visit_duration_minutes=dur,
    )


def _request() -> TripRequest:
    return TripRequest(
        destination="Test",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 1),
        pace=Pace.BALANCED,
        day_start=time(9, 0),
        day_end=time(19, 0),
    )


def test_activities_stay_within_the_day_window():
    pois = [_poi(f"p{i}", indoor=False, lat=35.0 + i * 0.001) for i in range(4)]
    day, _ = layout_day(
        day=date(2026, 9, 1), request=_request(), anchor=ANCHOR,
        candidates=pois, routing=ROUTING, max_activities=4,
    )
    start = datetime(2026, 9, 1, 9, 0)
    end = datetime(2026, 9, 1, 19, 0)
    for item in day.items:
        assert start <= item.start <= item.end <= end


def test_lunch_is_inserted_when_the_day_spans_midday():
    # Long visits guarantee the clock crosses noon.
    pois = [_poi(f"p{i}", indoor=False, dur=120, lat=35.0 + i * 0.001) for i in range(4)]
    day, _ = layout_day(
        day=date(2026, 9, 1), request=_request(), anchor=ANCHOR,
        candidates=pois, routing=ROUTING, max_activities=4,
    )
    meals = [i for i in day.items if i.type == ItemType.MEAL]
    assert any(m.title == "Lunch" for m in meals)


def test_wet_weather_puts_indoor_first():
    outdoor = _poi("outdoor", indoor=False, lat=35.0)
    indoor = _poi("indoor", indoor=True, lat=35.05)  # slightly farther
    wet = DayWeather(date=date(2026, 9, 1), condition=WeatherCondition.RAIN)
    day, _ = layout_day(
        day=date(2026, 9, 1), request=_request(), anchor=ANCHOR,
        candidates=[outdoor, indoor], routing=ROUTING, weather=wet, max_activities=2,
    )
    activities = [i for i in day.items if i.type == ItemType.ACTIVITY]
    assert activities[0].poi.indoor is True


def test_leftovers_returned_when_day_is_full():
    pois = [_poi(f"p{i}", indoor=False, dur=180, lat=35.0 + i * 0.001) for i in range(6)]
    day, leftover = layout_day(
        day=date(2026, 9, 1), request=_request(), anchor=ANCHOR,
        candidates=pois, routing=ROUTING, max_activities=6,
    )
    assert leftover  # a 10h day cannot hold six 3h visits + meals
