import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class JobListingCreate(BaseModel):
    """Body for POST /jobListings (employer input)."""
    company_id: uuid.UUID
    jobName: str
    location: str
    salary: Optional[Decimal] = None
    description: Optional[str] = None


class JobListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: uuid.UUID
    company_id: uuid.UUID
    title: str
    location: str
    salary: Optional[Decimal] = None
    description: Optional[str] = None
    status: str
    created_at: datetime
