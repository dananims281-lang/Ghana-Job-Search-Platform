import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Numeric, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Company(Base):
    __tablename__ = "company"

    company_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    verified_at = Column(TIMESTAMP, nullable=True)

    job_listings = relationship(
        "JobListing", back_populates="company", cascade="all, delete-orphan"
    )


class JobListing(Base):
    __tablename__ = "job_listing"

    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True), ForeignKey("company.company_id"), nullable=False
    )
    title = Column(String, nullable=False)
    location = Column(String, nullable=False)
    salary = Column(Numeric(12, 2), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="open")
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)

    company = relationship("Company", back_populates="job_listings")
