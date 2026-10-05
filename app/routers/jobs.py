from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(tags=["Jobs"])


@router.post(
    "/jobs",
    response_model=schemas.JobOut,
    status_code=status.HTTP_201_CREATED,
)
def create_job(payload: schemas.JobCreate, db: Session = Depends(get_db)):
    """Employer creates a new job. The company must already exist."""
    company = db.get(models.Company, payload.company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {payload.company_id} not found",
        )

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
