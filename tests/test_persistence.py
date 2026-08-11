import pytest

from travel_advisor.db import Database, ItineraryRepository, UserRepository
from travel_advisor.engine import ItineraryScheduler
from travel_advisor.models import Disruption, DisruptionType
from travel_advisor.providers import HaversineRoutingProvider
from travel_advisor.samples import KYOTO_BASE, KYOTO_POIS, sample_kyoto_request
from travel_advisor.security import hash_password, verify_password


@pytest.fixture
def session():
    db = Database("sqlite+pysqlite:///:memory:")
    db.init()
    s = db.session_factory()
    try:
        yield s
    finally:
        s.close()


def _make_itinerary():
    request = sample_kyoto_request()
    itinerary = ItineraryScheduler(HaversineRoutingProvider()).build(
        request, KYOTO_POIS, anchor=KYOTO_BASE
    )
    used = itinerary.scheduled_poi_ids()
    spares = [p for p in KYOTO_POIS if p.id not in used]
    return itinerary, spares


def test_password_hashing_roundtrip():
    stored = hash_password("s3cret-passw0rd")
    assert stored != "s3cret-passw0rd"
    assert verify_password("s3cret-passw0rd", stored)
    assert not verify_password("wrong", stored)


def test_user_repository_create_and_lookup(session):
    users = UserRepository(session)
    user = users.create(email="a@example.com", password_hash=hash_password("password123"))
    assert user.id is not None
    assert users.get(user.id).email == "a@example.com"
    assert users.get_by_email("a@example.com").id == user.id
    assert users.get_by_email("missing@example.com") is None


def test_itinerary_repository_roundtrip_preserves_plan(session):
    user = UserRepository(session).create(email="b@example.com", password_hash="x")
    itinerary, spares = _make_itinerary()
    repo = ItineraryRepository(session)

    row = repo.create(owner_id=user.id, itinerary=itinerary, candidates=spares, title="Kyoto")
    loaded = repo.to_itinerary(repo.get(row.id))

    assert loaded.scheduled_poi_ids() == itinerary.scheduled_poi_ids()
    assert len(loaded.days) == len(itinerary.days)
    assert [c.id for c in repo.to_candidates(row)] == [p.id for p in spares]


def test_itinerary_ownership_is_enforced(session):
    users = UserRepository(session)
    owner = users.create(email="owner@example.com", password_hash="x")
    intruder = users.create(email="intruder@example.com", password_hash="x")
    itinerary, spares = _make_itinerary()
    repo = ItineraryRepository(session)
    row = repo.create(owner_id=owner.id, itinerary=itinerary, candidates=spares, title="Kyoto")

    assert repo.get_for_owner(row.id, owner.id) is not None
    assert repo.get_for_owner(row.id, intruder.id) is None


def test_saving_a_reschedule_bumps_the_stored_revision(session):
    from travel_advisor.engine import Rescheduler

    user = UserRepository(session).create(email="c@example.com", password_hash="x")
    itinerary, spares = _make_itinerary()
    repo = ItineraryRepository(session)
    row = repo.create(owner_id=user.id, itinerary=itinerary, candidates=spares, title="Kyoto")
    assert row.revision == 0

    result = Rescheduler(HaversineRoutingProvider()).reschedule(
        itinerary,
        Disruption(type=DisruptionType.WEATHER_RAIN, date=itinerary.request.start_date),
        spare_pois=spares,
    )
    repo.save_itinerary(row, result.itinerary)
    assert repo.get(row.id).revision == 1
