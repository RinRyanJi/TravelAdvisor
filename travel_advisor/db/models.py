"""SQLAlchemy ORM tables.

The rich, nested itinerary is stored as JSON (it is a Pydantic tree that evolves
with the engine), while the columns we query or list on — owner, destination,
dates, revision, timestamps — are promoted to real columns.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    itineraries: Mapped[list["ItineraryRow"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )


class ItineraryRow(Base):
    __tablename__ = "itineraries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    destination: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[date] = mapped_column(nullable=False)
    end_date: Mapped[date] = mapped_column(nullable=False)
    revision: Mapped[int] = mapped_column(default=0)
    # Full serialised Itinerary and the candidate POI pool (for re-planning).
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    candidates: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    owner: Mapped["UserRow"] = relationship(back_populates="itineraries")
