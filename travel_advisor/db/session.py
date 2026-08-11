"""Engine and session management.

Wrapped in a small :class:`Database` object rather than module globals so the
app can be handed a throwaway in-memory database in tests (and, later, a
Postgres URL in production) without touching import-time state.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .models import Base

DEFAULT_URL = "sqlite:///./traveladvisor.db"


class Database:
    def __init__(self, url: str) -> None:
        self.url = url
        connect_args: dict = {}
        kwargs: dict = {}
        if url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
            if ":memory:" in url:
                # Keep the one in-memory database alive across connections.
                kwargs["poolclass"] = StaticPool
        self.engine = create_engine(url, connect_args=connect_args, **kwargs)
        self.session_factory = sessionmaker(
            bind=self.engine, autoflush=False, autocommit=False, class_=Session
        )

    @classmethod
    def from_env(cls) -> "Database":
        return cls(os.getenv("TRAVELADVISOR_DATABASE_URL", DEFAULT_URL))

    def init(self) -> None:
        """Create tables if they do not exist."""
        Base.metadata.create_all(self.engine)
