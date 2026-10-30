from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

# Used by T4.2 (remove this comment once it's done):
from app.dependencies import get_current_user, require_company_role  # noqa: F401
from app.enums import CompanyRole  # noqa: F401

router = APIRouter(tags=["Jobs"])


@router.post(
    "/jobs",
    response_model=schemas.JobOut,
    status_code=status.HTTP_201_CREATED,
)
def create_job(
    payload: schemas.JobCreate,
    db: Session = Depends(get_db),
    # ---------------------------------------------------------------------------------
    # TODO (T4.2, step 1): require login.
    #     current_user: models.AppUser = Depends(get_current_user),
    # ---------------------------------------------------------------------------------
):
    """Employer creates a new job. The company must already exist.

    T4.2: only members of that company (owner, admin or recruiter) may post its jobs.
    """
    company = db.get(models.Company, payload.company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {payload.company_id} not found",
        )

    # ---------------------------------------------------------------------------------
    # TODO (T4.2, step 2): check the caller works for this company.
    #     require_company_role(
    #         db,
    #         current_user.user_id,
    #         company.company_id,
    #         {CompanyRole.owner, CompanyRole.admin, CompanyRole.recruiter},
    #     )
    #   It raises 403 by itself when the caller isn't a member (or has another role), so
    #   nothing below runs. You don't need an if-statement here.
    #
    #   Why the company_id still comes from the body: one user can belong to several
    #   companies, so they must say which one. That is safe ONLY because of this check.
    #   Without it, anyone could post jobs for any company by changing company_id.
    #
    #   When done, also update the comment on JobCreate.company_id in app/schemas.py
    #   (it still says "take from the logged-in employer once auth exists").
    #
    # Done when:
    #   - no token                                                    -> 401
    #   - signed in, but not a member of payload.company_id           -> 403
    #   - signed in as the owner (create the company first, T4.1)     -> 201
    #   - unknown company_id                                          -> 404
    # ---------------------------------------------------------------------------------

    loc = payload.location
    sal = payload.salary

    job = models.Job(
        company_id=company.company_id,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        employment_type=payload.employment_type,
        experience_level=payload.experience_level,
        status=payload.status,
        work_mode=loc.work_mode,
        country=loc.country,
        region=loc.region,
        city=loc.city,
        salary_min=sal.min if sal else None,
        salary_max=sal.max if sal else None,
        salary_currency=sal.currency if sal else None,
        salary_period=sal.period if sal else None,
        requirements=payload.requirements,
        benefits=payload.benefits,
        expires_at=payload.expires_at,
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return schemas.JobOut.from_model(job)
