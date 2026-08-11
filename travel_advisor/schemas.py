"""Request/response models for the HTTP API (distinct from domain models)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import Itinerary
from .db.models import ItineraryRow


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime


class ItinerarySummary(BaseModel):
    """Lightweight view for listing a user's trips."""

    id: str
    title: str
    destination: str
    start_date: date
    end_date: date
    revision: int
    updated_at: datetime

    @classmethod
    def from_row(cls, row: ItineraryRow) -> "ItinerarySummary":
        return cls(
            id=row.id,
            title=row.title,
            destination=row.destination,
            start_date=row.start_date,
            end_date=row.end_date,
            revision=row.revision,
            updated_at=row.updated_at,
        )


class ItineraryOut(ItinerarySummary):
    """Full view including the day-by-day plan."""

    itinerary: Itinerary

    @classmethod
    def from_row(cls, row: ItineraryRow) -> "ItineraryOut":
        return cls(
            id=row.id,
            title=row.title,
            destination=row.destination,
            start_date=row.start_date,
            end_date=row.end_date,
            revision=row.revision,
            updated_at=row.updated_at,
            itinerary=Itinerary.model_validate(row.payload),
        )
