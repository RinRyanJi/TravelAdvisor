"""Persistent trip itineraries owned by the authenticated user."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from ..db import ItineraryRepository
from ..db.models import UserRow
from ..deps import get_current_user, get_db, get_planner, get_sample_planner
from ..engine import Rescheduler, TripPlanner
from ..models import Disruption, RescheduleResult, TripRequest
from ..providers import HaversineRoutingProvider
from ..schemas import ItineraryOut, ItinerarySummary

router = APIRouter(prefix="/itineraries", tags=["itineraries"])


def _title_for(request: TripRequest) -> str:
    return f"{request.destination} · {request.start_date.isoformat()} → {request.end_date.isoformat()}"


@router.post("", response_model=ItineraryOut, status_code=status.HTTP_201_CREATED)
def create_itinerary(
    request: TripRequest,
    sample: bool = False,
    current: UserRow = Depends(get_current_user),
    db: Session = Depends(get_db),
    planner: TripPlanner = Depends(get_planner),
    sample_planner: TripPlanner = Depends(get_sample_planner),
) -> ItineraryOut:
    """Plan a trip and store it against the current user.

    By default the plan is built from live open data. Pass ``?sample=true`` to
    plan from the built-in offline dataset — useful for demos and for
    environments without outbound access to the open-data services.
    """
    active_planner = sample_planner if sample else planner
    try:
        planned = active_planner.plan(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:  # upstream provider/network failure
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Upstream data error: {exc}"
        ) from exc

    row = ItineraryRepository(db).create(
        owner_id=current.id,
        itinerary=planned.itinerary,
        candidates=planned.candidates,
        title=_title_for(request),
    )
    return ItineraryOut.from_row(row)


@router.get("", response_model=list[ItinerarySummary])
def list_itineraries(
    current: UserRow = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ItinerarySummary]:
    rows = ItineraryRepository(db).list_for_owner(current.id)
    return [ItinerarySummary.from_row(r) for r in rows]


@router.get("/{itinerary_id}", response_model=ItineraryOut)
def get_itinerary(
    itinerary_id: str,
    current: UserRow = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ItineraryOut:
    row = ItineraryRepository(db).get_for_owner(itinerary_id, current.id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    return ItineraryOut.from_row(row)


@router.post("/{itinerary_id}/reschedule", response_model=RescheduleResult)
def reschedule_itinerary(
    itinerary_id: str,
    disruption: Disruption,
    current: UserRow = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RescheduleResult:
    """Absorb a disruption and persist the updated plan as a new revision.

    Re-planning is deterministic and offline (haversine routing), so it never
    depends on an external service being reachable.
    """
    repo = ItineraryRepository(db)
    row = repo.get_for_owner(itinerary_id, current.id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")

    itinerary = repo.to_itinerary(row)
    candidates = repo.to_candidates(row)
    used = itinerary.scheduled_poi_ids()
    spares = [p for p in candidates if p.id not in used]

    result = Rescheduler(HaversineRoutingProvider()).reschedule(
        itinerary, disruption, spare_pois=spares
    )
    repo.save_itinerary(row, result.itinerary)
    return result


@router.delete("/{itinerary_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_itinerary(
    itinerary_id: str,
    current: UserRow = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    repo = ItineraryRepository(db)
    row = repo.get_for_owner(itinerary_id, current.id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    repo.delete(row)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
