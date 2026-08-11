import pytest
from fastapi.testclient import TestClient

from travel_advisor.api import create_app
from travel_advisor.db import Database
from travel_advisor.engine import TripPlanner
from travel_advisor.models import Coordinates, Disruption, DisruptionType
from travel_advisor.providers import HaversineRoutingProvider
from travel_advisor.samples import KYOTO_BASE, KYOTO_POIS, sample_kyoto_request


# -- offline fakes so the API's live-planning path is testable without network --
class _FakeGeocoder:
    def geocode(self, query: str) -> Coordinates:
        return KYOTO_BASE


class _FakePoi:
    def find_pois(self, center, *, categories, radius_m=4000, limit=60):
        return list(KYOTO_POIS)


class _FakeWeather:
    def forecast(self, coords, start, end):
        return {}


def _fake_planner() -> TripPlanner:
    return TripPlanner(
        geocoder=_FakeGeocoder(),
        poi_provider=_FakePoi(),
        weather_provider=_FakeWeather(),
        routing=HaversineRoutingProvider(),
    )


@pytest.fixture
def client():
    app = create_app(db=Database("sqlite+pysqlite:///:memory:"), planner_factory=_fake_planner)
    return TestClient(app)


def _register_and_login(client, email="user@example.com", password="password123") -> str:
    client.post("/auth/register", json={"email": email, "password": password})
    resp = client.post("/auth/token", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_register_rejects_duplicate_email(client):
    body = {"email": "dupe@example.com", "password": "password123"}
    assert client.post("/auth/register", json=body).status_code == 201
    assert client.post("/auth/register", json=body).status_code == 409


def test_login_with_wrong_password_is_rejected(client):
    client.post("/auth/register", json={"email": "x@example.com", "password": "password123"})
    resp = client.post("/auth/token", json={"email": "x@example.com", "password": "nope"})
    assert resp.status_code == 401


def test_protected_route_requires_token(client):
    assert client.get("/itineraries").status_code in (401, 403)


def test_me_returns_current_user(client):
    token = _register_and_login(client)
    resp = client.get("/auth/me", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["email"] == "user@example.com"


def test_full_itinerary_lifecycle(client):
    token = _register_and_login(client)
    body = sample_kyoto_request().model_dump(mode="json")

    created = client.post("/itineraries", json=body, headers=_auth(token))
    assert created.status_code == 201
    data = created.json()
    assert data["revision"] == 0
    assert len(data["itinerary"]["days"]) == 3
    itinerary_id = data["id"]

    listing = client.get("/itineraries", headers=_auth(token)).json()
    assert len(listing) == 1 and listing[0]["id"] == itinerary_id

    fetched = client.get(f"/itineraries/{itinerary_id}", headers=_auth(token))
    assert fetched.status_code == 200
    assert fetched.json()["itinerary"]["days"][0]["items"]

    # Re-plan around rain on day one; the stored revision advances.
    disruption = Disruption(
        type=DisruptionType.WEATHER_RAIN, date=sample_kyoto_request().start_date
    ).model_dump(mode="json")
    resc = client.post(f"/itineraries/{itinerary_id}/reschedule", json=disruption, headers=_auth(token))
    assert resc.status_code == 200
    assert resc.json()["itinerary"]["revision"] == 1

    after = client.get(f"/itineraries/{itinerary_id}", headers=_auth(token)).json()
    assert after["revision"] == 1

    assert client.delete(f"/itineraries/{itinerary_id}", headers=_auth(token)).status_code == 204
    assert client.get(f"/itineraries/{itinerary_id}", headers=_auth(token)).status_code == 404


def test_users_cannot_see_each_others_itineraries(client):
    owner_token = _register_and_login(client, email="owner@example.com")
    body = sample_kyoto_request().model_dump(mode="json")
    itinerary_id = client.post("/itineraries", json=body, headers=_auth(owner_token)).json()["id"]

    intruder_token = _register_and_login(client, email="intruder@example.com")
    resp = client.get(f"/itineraries/{itinerary_id}", headers=_auth(intruder_token))
    assert resp.status_code == 404
    assert client.get("/itineraries", headers=_auth(intruder_token)).json() == []
