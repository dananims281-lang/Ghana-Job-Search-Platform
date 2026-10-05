import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from app.enums import EmploymentType, ExperienceLevel, JobStatus, SalaryPeriod, WorkMode


# ---------- Request: POST /jobs ----------

class LocationIn(BaseModel):
    work_mode: WorkMode
    country: str = Field(min_length=2, max_length=2, description="ISO 3166-1 alpha-2, e.g. GH")
    region: Optional[str] = Field(default=None, max_length=100)
    city: Optional[str] = Field(default=None, max_length=100)

    @field_validator("country")
    @classmethod
    def upper_country(cls, v: str) -> str:
        return v.upper()

    @model_validator(mode="after")
    def city_required_unless_remote(self):
        if self.work_mode != WorkMode.remote and not self.city:
            raise ValueError("city is required for onsite and hybrid jobs")
        return self


class SalaryIn(BaseModel):
    min: Optional[int] = Field(default=None, ge=0)
    max: Optional[int] = Field(default=None, ge=0)
    currency: str = Field(min_length=3, max_length=3, description="ISO 4217, e.g. GHS")
    period: SalaryPeriod

    @field_validator("currency")
    @classmethod
    def upper_currency(cls, v: str) -> str:
        return v.upper()

    @model_validator(mode="after")
    def check_range(self):
        if self.min is None and self.max is None:
            raise ValueError("salary needs at least a min or a max")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("salary.min cannot be greater than salary.max")
        return self


class JobCreate(BaseModel):
    """Body for POST /jobs (employer input)."""

    company_id: uuid.UUID  # TODO: take from the logged-in employer once auth exists
    title: str = Field(min_length=1, max_length=150)
    description: str = Field(min_length=1)
    category: str = Field(min_length=1, max_length=50)
    employment_type: EmploymentType
    experience_level: Optional[ExperienceLevel] = None
    status: JobStatus = JobStatus.open
    location: LocationIn
    salary: Optional[SalaryIn] = None
    requirements: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None

    @field_validator("status")
    @classmethod
    def not_closed(cls, v: JobStatus) -> JobStatus:
        if v == JobStatus.closed:
            raise ValueError("a new job can only be 'open' or 'draft'")
        return v

    @field_validator("expires_at")
    @classmethod
    def expires_in_future(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is None:
            return v
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v <= datetime.now(timezone.utc):
            raise ValueError("expires_at must be in the future")
        return v


# ---------- Request: POST /companies ----------

class CompanyLocationIn(BaseModel):
    country: str = Field(min_length=2, max_length=2, description="ISO 3166-1 alpha-2, e.g. GH")
    region: Optional[str] = Field(default=None, max_length=100)
    city: Optional[str] = Field(default=None, max_length=100)

    @field_validator("country")
    @classmethod
    def upper_country(cls, v: str) -> str:
        return v.upper()


class CompanyCreate(BaseModel):
    """Body for POST /companies. `verified` is not accepted: it is set by an admin."""

    name: str = Field(min_length=1, max_length=200)
    website: Optional[HttpUrl] = None
    description: Optional[str] = None
    location: Optional[CompanyLocationIn] = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name cannot be blank")
        return v

    @field_validator("website")
    @classmethod
    def website_length(cls, v: Optional[HttpUrl]) -> Optional[HttpUrl]:
        if v is not None and len(str(v)) > 500:
            raise ValueError("website must be at most 500 characters")
        return v


# ---------- Response ----------

class CompanyOut(BaseModel):
    id: uuid.UUID
    name: str
    website: Optional[str]
    verified: bool


class CompanyLocationOut(BaseModel):
    country: Optional[str]
    region: Optional[str]
    city: Optional[str]


class CompanyDetailOut(BaseModel):
    """Full company profile, returned by GET/POST /companies."""

    id: uuid.UUID
    name: str
    website: Optional[str]
    description: Optional[str]
    verified: bool
    location: Optional[CompanyLocationOut]
    open_jobs_count: int
    created_at: datetime

    @classmethod
    def from_model(cls, company, open_jobs_count: int = 0) -> "CompanyDetailOut":
        has_location = any([company.country, company.region, company.city])
        return cls(
            id=company.company_id,
            name=company.name,
            website=company.website,
            description=company.description,
            verified=company.verified,
            location=CompanyLocationOut(
                country=company.country,
                region=company.region,
                city=company.city,
            )
            if has_location
            else None,
            open_jobs_count=open_jobs_count,
            created_at=company.created_at,
        )


class LocationOut(BaseModel):
    work_mode: WorkMode
    country: str
    region: Optional[str]
    city: Optional[str]


class SalaryOut(BaseModel):
    min: Optional[int]
    max: Optional[int]
    currency: Optional[str]
    period: Optional[SalaryPeriod]


class JobOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    category: str
    employment_type: EmploymentType
    experience_level: Optional[ExperienceLevel]
    status: JobStatus
    company: CompanyOut
    location: LocationOut
    salary: Optional[SalaryOut]
    requirements: list[str]
    benefits: list[str]
    posted_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]

    @classmethod
    def from_model(cls, job) -> "JobOut":
        has_salary = job.salary_min is not None or job.salary_max is not None
        return cls(
            id=job.job_id,
            title=job.title,
            description=job.description,
            category=job.category,
            employment_type=job.employment_type,
            experience_level=job.experience_level,
            status=job.status,
            company=CompanyOut(
                id=job.company.company_id,
                name=job.company.name,
                website=job.company.website,
                verified=job.company.verified,
            ),
            location=LocationOut(
                work_mode=job.work_mode,
                country=job.country,
                region=job.region,
                city=job.city,
            ),
            salary=SalaryOut(
                min=job.salary_min,
                max=job.salary_max,
                currency=job.salary_currency,
                period=job.salary_period,
            )
            if has_salary
            else None,
            requirements=job.requirements or [],
            benefits=job.benefits or [],
            posted_at=job.posted_at,
            updated_at=job.updated_at,
            expires_at=job.expires_at,
        )
