from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(tags=["Job Listings"])


@router.post(
    "/jobListings",
    response_model=schemas.JobListingOut,
    status_code=status.HTTP_201_CREATED,
)
def create_job_listing(payload: schemas.JobListingCreate, db: Session = Depends(get_db)):
    """
    Employer creates a new job listing.

    Body:
        company_id: which company is posting (must already exist)
        jobName:    job title
        location:   job location
        salary:     optional salary
        description: optional job description
    """
    company = (
        db.query(models.Company)
        .filter(models.Company.company_id == payload.company_id)
        .first()
    )
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {payload.company_id} not found",
        )

    job_listing = models.JobListing(
        company_id=payload.company_id,
        title=payload.jobName,
        location=payload.location,
        salary=payload.salary,
        description=payload.description,
        status="open",
    )

    db.add(job_listing)
    db.commit()
    db.refresh(job_listing)

    return job_listing
