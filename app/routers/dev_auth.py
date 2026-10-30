"""LOCAL DEVELOPMENT ONLY.

POST /auth/dev-login signs in as any email without Google, so you can test in Swagger or
Postman without a real Google token. main.py only registers this router when
ENABLE_DEV_LOGIN=true. Never turn that on anywhere real users can reach the API: anyone
could sign in as any account.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.enums import AuthProvider
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth (dev only)"])


@router.post("/dev-login", response_model=schemas.AuthResponse)
def dev_login(payload: schemas.DevLoginRequest, db: Session = Depends(get_db)):
    """Sign in as `email` without Google (creates the user the first time)."""
    return auth_service.sign_in(
        db,
        provider=AuthProvider.dev,
        subject=payload.email,
        email=payload.email,
        email_verified=True,
        full_name=payload.full_name,
        avatar_url=None,
    )
