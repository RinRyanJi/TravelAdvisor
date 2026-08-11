"""Password hashing and JWT access tokens.

Password hashing uses PBKDF2-HMAC-SHA256 from the standard library (no native
build step, constant-time verification). Tokens are signed JWTs.

The signing secret comes from ``TRAVELADVISOR_SECRET``. The built-in default is
for local development only — set a real secret in any shared deployment.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

_PBKDF2_ITERATIONS = 200_000
_ALGORITHM = "HS256"
_DEFAULT_TOKEN_MINUTES = 60 * 24  # 1 day


def _secret() -> str:
    # The default is for local development only (≥32 bytes to satisfy HS256);
    # set TRAVELADVISOR_SECRET to a real secret in any shared deployment.
    return os.getenv("TRAVELADVISOR_SECRET", "dev-insecure-secret-change-me-in-production")


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text.encode("ascii"))


def hash_password(password: str) -> str:
    """Return an encoded ``pbkdf2_sha256$iterations$salt$hash`` string."""
    salt = os.urandom(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${_b64(salt)}${_b64(derived)}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time check of ``password`` against an encoded hash."""
    try:
        algorithm, iterations, salt_b64, hash_b64 = stored.split("$")
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    salt = _unb64(salt_b64)
    expected = _unb64(hash_b64)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
    return hmac.compare_digest(derived, expected)


def create_access_token(subject: str | int, expires_minutes: int = _DEFAULT_TOKEN_MINUTES) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, _secret(), algorithm=_ALGORITHM)


def decode_token(token: str) -> str | None:
    """Return the token subject, or ``None`` if the token is invalid/expired."""
    try:
        payload = jwt.decode(token, _secret(), algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return None
    return payload.get("sub")
