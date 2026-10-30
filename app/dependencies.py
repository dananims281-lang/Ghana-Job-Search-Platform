"""FastAPI dependencies for authentication and company permissions."""

import uuid
from typing import Iterable, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.enums import CompanyRole
from app.security import decode_access_token

# auto_error=False so we return our own 401 (FastAPI's default is 403 for a missing header).
# Also adds the "Authorize" button to Swagger at /docs.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.AppUser:
    """The signed-in user. Raises 401 if the request has no valid access token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = decode_access_token(credentials.credentials)
    user = db.get(models.AppUser, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[models.AppUser]:
    """The signed-in user, or None. For public endpoints that show extra info when
    signed in (e.g. `has_applied` on GET /jobs/{id})."""
    if credentials is None:
        return None
    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None


def require_company_role(
    db: Session,
    user_id: uuid.UUID,
    company_id: uuid.UUID,
    roles: Iterable[CompanyRole],
) -> models.CompanyMember:
    """Return the user's membership in the company, or raise 403 if they have none
    or their role isn't one of `roles`.

    Example (in POST /jobs, after checking the company exists):
        require_company_role(db, current_user.user_id, payload.company_id,
                             {CompanyRole.owner, CompanyRole.admin, CompanyRole.recruiter})
    """
    member = db.get(models.CompanyMember, (company_id, user_id))
    if member is None or member.role not in set(roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to do this for this company",
        )
    return member
