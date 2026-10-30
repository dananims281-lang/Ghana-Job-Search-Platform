from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.enums import AuthProvider
from app.security import verify_google_token
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/google", response_model=schemas.AuthResponse)
def google_sign_in(payload: schemas.GoogleAuthRequest, db: Session = Depends(get_db)):
    """Sign in (or sign up) with a Google ID token from the frontend's Google button.

    Same call for job seekers and company users. `is_new_user` tells the frontend to show
    onboarding; `memberships` lists the companies the user can act for (empty = job seeker).
    """
    claims = verify_google_token(payload.id_token)
    return auth_service.sign_in(
        db,
        provider=AuthProvider.google,
        subject=claims["sub"],
        email=claims["email"],
        email_verified=True,  # verify_google_token rejects unverified emails
        full_name=claims.get("name"),
        avatar_url=claims.get("picture"),
    )


@router.post("/refresh", response_model=schemas.TokenResponse)
def refresh(payload: schemas.RefreshRequest, db: Session = Depends(get_db)):
    """Swap a refresh token for a new access token and refresh token.

    The refresh token sent is revoked; store the new one. Reusing an old one signs the user
    out everywhere.
    """
    return auth_service.refresh_session(db, payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: schemas.RefreshRequest, db: Session = Depends(get_db)):
    """Revoke this session's refresh token. The frontend should also delete both tokens."""
    auth_service.revoke_refresh_token(db, payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
