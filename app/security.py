"""Token handling: verifying Google ID tokens and issuing our own tokens.

Google's token only proves who the person is at sign-in. After that, the API uses its own
short-lived access token (a JWT) and a long-lived refresh token (random, stored hashed).
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status
from google.auth import exceptions as google_exceptions
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.config import settings

# Reused across calls; google-auth fetches Google's public signing keys with it.
_google_request = google_requests.Request()

_UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers=_UNAUTHORIZED_HEADERS,
    )


# ---------- Google ----------


def verify_google_token(token: str) -> dict:
    """Check a Google ID token and return its claims (sub, email, name, picture, ...).

    Verifies Google's signature, expiry, issuer, and that the token was issued for one of
    our client IDs (`aud`). Rejects accounts whose email Google hasn't verified.
    """
    if not settings.google_client_ids:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google sign-in is not configured (GOOGLE_CLIENT_IDS is empty)",
        )

    try:
        claims = google_id_token.verify_oauth2_token(
            token,
            _google_request,
            audience=list(settings.google_client_ids),
            clock_skew_in_seconds=10,
        )
    except google_exceptions.TransportError:
        # Couldn't download Google's keys: our problem, not the user's token.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not reach Google to verify the sign-in. Try again.",
        )
    except (ValueError, google_exceptions.GoogleAuthError):
        raise _unauthorized("Invalid or expired Google token")

    # verify_oauth2_token already checks these; checked again so a library change can't
    # silently let through a token issued for someone else's app.
    if claims.get("aud") not in settings.google_client_ids:
        raise _unauthorized("Google token was not issued for this app")
    if not claims.get("sub") or not claims.get("email"):
        raise _unauthorized("Google token is missing the account id or email")
    if claims.get("email_verified") is not True:
        raise _unauthorized("Google account email is not verified")

    return claims


# ---------- Access tokens (JWT) ----------


def create_access_token(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> uuid.UUID:
    """Return the user id inside a valid access token, or raise 401."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Access token expired")
    except jwt.PyJWTError:
        raise _unauthorized("Invalid access token")

    if payload.get("type") != "access":
        raise _unauthorized("Invalid access token")
    try:
        return uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        raise _unauthorized("Invalid access token")


# ---------- Refresh tokens ----------


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def new_refresh_token() -> tuple[str, str]:
    """Return (raw token for the client, SHA-256 hash to store)."""
    raw = secrets.token_urlsafe(48)
    return raw, hash_token(raw)
