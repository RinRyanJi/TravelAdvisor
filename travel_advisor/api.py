"""FastAPI application for TravelAdvisor.

Run locally with::

    uvicorn travel_advisor.api:app --reload

Endpoints:

* ``POST /auth/register``            — create an account
* ``POST /auth/token``               — log in, returns a bearer token
* ``GET  /auth/me``                  — the current user
* ``POST /itineraries``              — plan a trip (live data) and save it
* ``GET  /itineraries``              — list the user's trips
* ``GET  /itineraries/{id}``         — one trip, with its full plan
* ``POST /itineraries/{id}/reschedule`` — re-plan around a disruption, save a revision
* ``DELETE /itineraries/{id}``       — delete a trip
* ``POST /reschedule``               — stateless, offline re-plan utility
* ``GET  /health``

The app is built by :func:`create_app` so tests can inject an in-memory
database and an offline planner.
"""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .db import Database
from .engine import Rescheduler, TripPlanner
from .models import Disruption, Itinerary, PointOfInterest, RescheduleResult
from .providers import HaversineRoutingProvider
from .routers import auth, itineraries


class RescheduleRequest(BaseModel):
    itinerary: Itinerary
    disruption: Disruption
    spare_pois: list[PointOfInterest] = Field(default_factory=list)


def create_app(*, db: Database | None = None, planner_factory=None) -> FastAPI:
    database = db or Database.from_env()
    database.init()

    app = FastAPI(
        title="TravelAdvisor",
        version="0.2.0",
        description="Automated travel itinerary scheduling, re-scheduling, and storage.",
    )
    app.state.db = database
    app.state.planner_factory = planner_factory or (lambda: TripPlanner())

    app.include_router(auth.router)
    app.include_router(itineraries.router)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/reschedule", response_model=RescheduleResult, tags=["itineraries"])
    def reschedule(body: RescheduleRequest) -> RescheduleResult:
        """Stateless re-plan: pass an itinerary in, get the updated plan back.
        Deterministic and offline — handy for previews and integrations."""
        rescheduler = Rescheduler(HaversineRoutingProvider())
        return rescheduler.reschedule(body.itinerary, body.disruption, spare_pois=body.spare_pois)

    return app


app = create_app()
