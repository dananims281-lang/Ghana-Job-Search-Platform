import uuid

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    Column,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.enums import EmploymentType, ExperienceLevel, JobStatus, SalaryPeriod, WorkMode


def _enum(enum_cls, name):
    """Store enums as VARCHAR(20) + CHECK constraint (easier to change than native PG enums)."""
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=20,
        values_callable=lambda e: [m.value for m in e],
    )


class Company(Base):
    __tablename__ = "company"

    company_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    website = Column(String(500), nullable=True)
    verified_at = Column(TIMESTAMP, nullable=True)

    jobs = relationship(
        "Job", back_populates="company", cascade="all, delete-orphan"
    )

    @property
    def verified(self) -> bool:
        return self.verified_at is not None


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max",
            name="ck_jobs_salary_range",
        ),
    )

    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True), ForeignKey("company.company_id"), nullable=False, index=True
    )

    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, index=True)
    employment_type = Column(_enum(EmploymentType, "ck_jobs_employment_type"), nullable=False)
    experience_level = Column(_enum(ExperienceLevel, "ck_jobs_experience_level"), nullable=True)
    status = Column(
        _enum(JobStatus, "ck_jobs_status"), nullable=False, default=JobStatus.open, index=True
    )

    # Location
    work_mode = Column(_enum(WorkMode, "ck_jobs_work_mode"), nullable=False)
    country = Column(String(2), nullable=False, index=True)  # ISO 3166-1 alpha-2, e.g. "GH"
    region = Column(String(100), nullable=True)               # e.g. "Greater Accra"
    city = Column(String(100), nullable=True, index=True)     # NULL for fully remote jobs

    # Salary (whole currency units)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    salary_currency = Column(String(3), nullable=True)        # ISO 4217, e.g. "GHS"
    salary_period = Column(_enum(SalaryPeriod, "ck_jobs_salary_period"), nullable=True)

    requirements = Column(ARRAY(Text), nullable=False, server_default=text("'{}'"))
    benefits = Column(ARRAY(Text), nullable=False, server_default=text("'{}'"))

    posted_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)

    company = relationship("Company", back_populates="jobs")
