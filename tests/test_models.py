from datetime import date, datetime, time

import pytest
from pydantic import ValidationError

from travel_advisor.models import (
    Coordinates,
    Interest,
    OpeningHours,
    Pace,
    TripRequest,
)


def test_distance_km_is_symmetric_and_positive():
    a = Coordinates(lat=35.0, lon=135.0)
    b = Coordinates(lat=35.1, lon=135.1)
    assert a.distance_km(b) == pytest.approx(b.distance_km(a))
    assert a.distance_km(b) > 0
    assert a.distance_km(a) == pytest.approx(0.0, abs=1e-9)


def test_opening_hours_daily_window():
    hours = OpeningHours.daily(time(9, 0), time(17, 0))
    monday_10 = datetime(2026, 9, 7, 10, 0)  # a Monday
    monday_18 = datetime(2026, 9, 7, 18, 0)
    assert hours.is_open_at(monday_10)
    assert not hours.is_open_at(monday_18)
    # Can start at 10:00 and finish by 16:00, but not finish by 17:30 (past close).
    assert hours.opens_before_close_on(monday_10, time(16, 0))
    assert not hours.opens_before_close_on(monday_10, time(17, 30))


def test_always_open_hours():
    hours = OpeningHours.open_always()
    assert hours.is_open_at(datetime(2026, 1, 1, 3, 0))


def test_trip_request_num_days_and_categories():
    req = TripRequest(
        destination="Kyoto",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 3),
        interests=[Interest.HISTORY],
        pace=Pace.PACKED,
    )
    assert req.num_days == 3
    assert req.pace.max_activities_per_day == 6
    assert req.wanted_categories  # history maps to some categories


def test_trip_request_rejects_backwards_dates():
    with pytest.raises(ValidationError):
        TripRequest(
            destination="X",
            start_date=date(2026, 9, 3),
            end_date=date(2026, 9, 1),
        )
