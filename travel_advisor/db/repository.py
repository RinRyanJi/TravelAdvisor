"""Repositories: the only place that translates between ORM rows and the domain
Pydantic models. Routers depend on these, never on raw SQLAlchemy queries."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Itinerary, PointOfInterest
from .models import ItineraryRow, UserRow


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def create(self, email: str, password_hash: str) -> UserRow:
        user = UserRow(email=email, password_hash=password_hash)
        self._s.add(user)
        self._s.commit()
        self._s.refresh(user)
        return user

    def get(self, user_id: int) -> UserRow | None:
        return self._s.get(UserRow, user_id)

    def get_by_email(self, email: str) -> UserRow | None:
        return self._s.scalar(select(UserRow).where(UserRow.email == email))


class ItineraryRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def create(
        self,
        *,
        owner_id: int,
        itinerary: Itinerary,
        candidates: list[PointOfInterest],
        title: str,
    ) -> ItineraryRow:
        req = itinerary.request
        row = ItineraryRow(
            id=uuid.uuid4().hex,
            owner_id=owner_id,
            title=title,
            destination=req.destination,
            start_date=req.start_date,
            end_date=req.end_date,
            revision=itinerary.revision,
            payload=itinerary.model_dump(mode="json"),
            candidates=[p.model_dump(mode="json") for p in candidates],
        )
        self._s.add(row)
        self._s.commit()
        self._s.refresh(row)
        return row

    def get(self, itinerary_id: str) -> ItineraryRow | None:
        return self._s.get(ItineraryRow, itinerary_id)

    def get_for_owner(self, itinerary_id: str, owner_id: int) -> ItineraryRow | None:
        row = self.get(itinerary_id)
        if row is None or row.owner_id != owner_id:
            return None
        return row

    def list_for_owner(self, owner_id: int) -> list[ItineraryRow]:
        stmt = (
            select(ItineraryRow)
            .where(ItineraryRow.owner_id == owner_id)
            .order_by(ItineraryRow.updated_at.desc())
        )
        return list(self._s.scalars(stmt))

    def save_itinerary(self, row: ItineraryRow, itinerary: Itinerary) -> ItineraryRow:
        row.payload = itinerary.model_dump(mode="json")
        row.revision = itinerary.revision
        self._s.commit()
        self._s.refresh(row)
        return row

    def delete(self, row: ItineraryRow) -> None:
        self._s.delete(row)
        self._s.commit()

    # -- row -> domain reconstruction --------------------------------------

    @staticmethod
    def to_itinerary(row: ItineraryRow) -> Itinerary:
        return Itinerary.model_validate(row.payload)

    @staticmethod
    def to_candidates(row: ItineraryRow) -> list[PointOfInterest]:
        return [PointOfInterest.model_validate(c) for c in (row.candidates or [])]
