import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.dependencies import get_current_user, require_company_role
from app.enums import CompanyRole, JobStatus

# How long an invite can wait before the invited person signs in.
INVITE_DAYS = 14

router = APIRouter(tags=["Companies"])


def _open_jobs_count(db: Session, company_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count())
        .select_from(models.Job)
        .where(
            models.Job.company_id == company_id,
            models.Job.status == JobStatus.open,
        )
    )


@router.post(
    "/companies",
    response_model=schemas.CompanyDetailOut,
    status_code=status.HTTP_201_CREATED,
)
def create_company(
    payload: schemas.CompanyCreate,
    db: Session = Depends(get_db),
    # ---------------------------------------------------------------------------------
    # TODO (T4.1, step 1): require login.
    #   Add this parameter, exactly like GET /me in app/routers/me.py:
    #       current_user: models.AppUser = Depends(get_current_user),
    #   After that, calling this endpoint without a token returns 401 automatically.
    # ---------------------------------------------------------------------------------
):
    """Employer registers a company. It starts unverified.

    T4.1: the signed-in user who creates the company becomes its `owner`.
    """
    loc = payload.location

    company = models.Company(
        name=payload.name,
        website=str(payload.website) if payload.website else None,
        description=payload.description,
        country=loc.country if loc else None,
        region=loc.region if loc else None,
        city=loc.city if loc else None,
    )

    db.add(company)

    # ---------------------------------------------------------------------------------
    # TODO (T4.1, step 2): make the creator the owner.
    #   Add a CompanyMember row linking current_user to this company with role owner:
    #       db.add(models.CompanyMember(
    #           company=company,                 # the object above; no id needed yet
    #           user_id=current_user.user_id,
    #           role=CompanyRole.owner,
    #       ))
    #
    #   Why here, BEFORE db.commit(): the company and its owner are saved in the same
    #   commit (one transaction). If either insert fails, neither is saved, so a company
    #   can never exist without an owner.
    #
    # Done when:
    #   - POST /companies without a token                    -> 401
    #   - with a token (dev-login, then Authorize in /docs)  -> 201
    #   - GET /me afterwards lists the company with role "owner"
    # ---------------------------------------------------------------------------------

    db.commit()
    db.refresh(company)

    return schemas.CompanyDetailOut.from_model(company, open_jobs_count=0)


@router.get("/companies/{company_id}", response_model=schemas.CompanyDetailOut)
def get_company(company_id: uuid.UUID, db: Session = Depends(get_db)):
    """Public company profile, e.g. when a user clicks the company name on a job."""
    company = db.get(models.Company, company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found",
        )

    return schemas.CompanyDetailOut.from_model(
        company, open_jobs_count=_open_jobs_count(db, company_id)
    )


@router.post(
    "/companies/{company_id}/members",
    response_model=schemas.MemberAddOut,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    company_id: uuid.UUID,
    payload: schemas.MemberAddRequest,
    db: Session = Depends(get_db),
    current_user: models.AppUser = Depends(get_current_user),
):
    """Add a teammate to a company by email.

    - Someone with that email has already signed in -> they become a member right away
      (status "added").
    - Nobody has signed in with that email yet -> a pending invite is stored (status
      "invited"). It becomes a membership the first time they sign in with that email.

    Rules: only the company's owner or admins can add people, and only the owner can add
    admins. 401 not signed in, 404 unknown company, 403 not allowed, 409 already a member.
    """
    # 1. The company must exist.
    if db.get(models.Company, company_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found",
        )

    # 2. The caller must be this company's owner or an admin (403 otherwise).
    caller = require_company_role(
        db, current_user.user_id, company_id, {CompanyRole.owner, CompanyRole.admin}
    )
    # Admins can add recruiters, but making someone an admin is the owner's decision.
    if payload.role == CompanyRole.admin and caller.role != CompanyRole.owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the company owner can add admins",
        )

    # 3a. Already signed up? Add them directly; no invite needed.
    #     payload.email is lowercased by the schema, matching how app_user stores emails.
    user = db.scalar(select(models.AppUser).where(models.AppUser.email == payload.email))
    if user is not None:
        if db.get(models.CompanyMember, (company_id, user.user_id)) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{payload.email} is already a member of this company",
            )
        db.add(
            models.CompanyMember(company_id=company_id, user_id=user.user_id, role=payload.role)
        )
        db.commit()
        return schemas.MemberAddOut(status="added", email=payload.email, role=payload.role)

    # 3b. Not signed up yet: store (or refresh) a pending invite.
    expires_at = datetime.now(timezone.utc) + timedelta(days=INVITE_DAYS)
    invite = db.scalar(
        select(models.CompanyInvite).where(
            models.CompanyInvite.company_id == company_id,
            models.CompanyInvite.email == payload.email,
            models.CompanyInvite.accepted_at.is_(None),
        )
    )
    if invite is not None:
        # Invited again before they signed in: update the existing invite instead of
        # creating a second one. An expired invite becomes usable again here too.
        invite.role = payload.role
        invite.expires_at = expires_at
        invite.invited_by = current_user.user_id
    else:
        db.add(
            models.CompanyInvite(
                company_id=company_id,
                email=payload.email,
                role=payload.role,
                invited_by=current_user.user_id,  # from the token, never from the body
                expires_at=expires_at,
            )
        )
    db.commit()
    return schemas.MemberAddOut(
        status="invited", email=payload.email, role=payload.role, expires_at=expires_at
    )
