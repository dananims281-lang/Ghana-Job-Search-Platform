import uuid
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

""""@router.get("/jobs", response_model=list[schemas.JobOut])
def get_jobs(
    skip: int = 0,
    limit: int = 10,
    category: Optional[str] = None,
    employment_type: Optional[str] = None,
    work_mode: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    #Retrieve a list of jobs with optional filters and pagination.
    # Build the SQLAlchemy 2.0 select statement
    stmt = select(models.Job)

    # Apply filters dynamically if provided
    if category:
        stmt = stmt.where(models.Job.category == category)
    if employment_type:
        stmt = stmt.where(models.Job.employment_type == employment_type)
    if work_mode:
        stmt = stmt.where(models.Job.work_mode == work_mode)
    if status:
        stmt = stmt.where(models.Job.status == status)

    # Add pagination and execute using db.scalars()
    stmt = stmt.offset(skip).limit(limit)
    jobs = db.scalars(stmt).all()

    return [schemas.JobOut.from_model(job) for job in jobs]


@router.get("/jobs/{job_id}", response_model=schemas.JobOut)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    #Retrieve a single job by its ID (similar to get_company).
    job = db.get(models.Job, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    return schemas.JobOut.from_model(job)
"""

@router.get("/jobs/{job_id}", response_model=schemas.JobOut)
def get_jobs(job_id: uuid.UUID, db: Session = Depends(get_db)):
    job = db.get(models.Job, job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    return schemas.JobOut.from_model(job)
