"""FastAPI surface for the planning engine.

Run locally with::

    uvicorn travel_advisor.api:app --reload

* ``POST /plan``       — plan a trip from a :class:`TripRequest` using the live
  open-data providers (needs outbound network).
* ``POST /reschedule`` — re-plan an existing itinerary around a disruption.
  Deterministic and offline (uses the haversine routing estimate), so it never
  depends on an external service being reachable.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .engine import Rescheduler, TripPlanner
from .models import (
    Disruption,
    Itinerary,
    PointOfInterest,
    RescheduleResult,
    TripRequest,
)
from .providers import HaversineRoutingProvider

app = FastAPI(
    title="TravelAdvisor",
    version="0.1.0",
    description="Automated travel itinerary scheduling and re-scheduling.",
)


class RescheduleRequest(BaseModel):
    itinerary: Itinerary
    disruption: Disruption
    spare_pois: list[PointOfInterest] = Field(default_factory=list)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/plan", response_model=Itinerary)
def plan(request: TripRequest) -> Itinerary:
    planner = TripPlanner()
    try:
        planned = planner.plan(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # upstream provider/network failure
        raise HTTPException(status_code=502, detail=f"Upstream data error: {exc}") from exc
    return planned.itinerary


@app.post("/reschedule", response_model=RescheduleResult)
def reschedule(body: RescheduleRequest) -> RescheduleResult:
    rescheduler = Rescheduler(HaversineRoutingProvider())
    return rescheduler.reschedule(
        body.itinerary,
        body.disruption,
        spare_pois=body.spare_pois,
    )
