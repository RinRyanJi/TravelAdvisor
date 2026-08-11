"""FastAPI dependencies: database session, current user, and planner factory.

Everything the routes need is pulled from ``request.app.state``, which the app
factory populates. That indirection is what lets tests inject an in-memory
database and an offline planner without any global monkey-patching.
"""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .db import UserRepository
from .db.models import UserRow
from .engine import TripPlanner
from .security import decode_token

_bearer = HTTPBearer(auto_error=True)


def get_db(request: Request) -> Iterator[Session]:
    session = request.app.state.db.session_factory()
    try:
        yield session
    finally:
        session.close()


def get_planner(request: Request) -> TripPlanner:
    return request.app.state.planner_factory()


def get_sample_planner(request: Request) -> TripPlanner:
    """The offline, sample-data planner used when a request opts into demo mode."""
    return request.app.state.sample_planner_factory()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> UserRow:
    subject = decode_token(credentials.credentials)
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = int(subject)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    user = UserRepository(db).get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
    return user
