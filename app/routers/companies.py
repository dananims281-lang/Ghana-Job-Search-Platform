import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.enums import JobStatus

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
def create_company(payload: schemas.CompanyCreate, db: Session = Depends(get_db)):
    """Employer registers a company. It starts unverified."""
    # TODO: once auth exists, link the company to the logged-in employer account.
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
