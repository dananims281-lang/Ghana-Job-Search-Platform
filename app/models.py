import uuid

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    CheckConstraint,
    Column,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.enums import (
    AuthProvider,
    CompanyRole,
    EmploymentType,
    ExperienceLevel,
    JobStatus,
    SalaryPeriod,
    WorkMode,
)


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
    description = Column(Text, nullable=True)

    # Headquarters location
    country = Column(String(2), nullable=True)   # ISO 3166-1 alpha-2, e.g. "GH"
    region = Column(String(100), nullable=True)  # e.g. "Greater Accra"
    city = Column(String(100), nullable=True)

    # Set by an admin after checking the business is legit; never by the employer.
    verified_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    jobs = relationship(
        "Job", back_populates="company", cascade="all, delete-orphan"
    )
    members = relationship(
        "CompanyMember", back_populates="company", cascade="all, delete-orphan"
    )
    invites = relationship(
        "CompanyInvite", back_populates="company", cascade="all, delete-orphan"
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


# ---------- Users & auth ----------


class AppUser(Base):
    """A person who signs in. Job seeker vs employer is not stored here:
    company access comes from company_member rows."""

    __tablename__ = "app_user"
    __table_args__ = (
        CheckConstraint("email = lower(email)", name="ck_app_user_email_lowercase"),
    )

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(320), nullable=False, unique=True)  # always stored lowercase
    email_verified = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    full_name = Column(String(200), nullable=True)
    phone = Column(String(30), nullable=True, unique=True)  # Google doesn't provide it
    avatar_url = Column(String(1000), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    last_login_at = Column(TIMESTAMP(timezone=True), nullable=True)

    identities = relationship(
        "UserIdentity", back_populates="user", cascade="all, delete-orphan"
    )
    memberships = relationship(
        "CompanyMember", back_populates="user", cascade="all, delete-orphan"
    )


class UserIdentity(Base):
    """One sign-in method for a user, e.g. a Google account (provider_subject = Google's `sub`)."""

    __tablename__ = "user_identity"
    __table_args__ = (
        UniqueConstraint(
            "provider", "provider_subject", name="uq_user_identity_provider_subject"
        ),
    )

    identity_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("app_user.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider = Column(_enum(AuthProvider, "ck_user_identity_provider"), nullable=False)
    provider_subject = Column(String(255), nullable=False)
    email = Column(String(320), nullable=True)  # email the provider reported at last sign-in
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    user = relationship("AppUser", back_populates="identities")


class RefreshToken(Base):
    """Long-lived session token. Only a SHA-256 hash is stored, never the token itself."""

    __tablename__ = "refresh_token"

    token_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("app_user.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = Column(String(64), nullable=False, unique=True)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    revoked_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    user = relationship("AppUser")


class CompanyMember(Base):
    """Links a user to a company with a role. This is what makes someone an employer."""

    __tablename__ = "company_member"

    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("company.company_id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("app_user.user_id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    role = Column(_enum(CompanyRole, "ck_company_member_role"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    company = relationship("Company", back_populates="members")
    user = relationship("AppUser", back_populates="memberships")


class CompanyInvite(Base):
    """Invitation to join a company, for an email that has no account yet.

    Created by POST /companies/{company_id}/members when nobody has signed in with that
    email. The first time someone signs in with that (verified) email, sign_in() turns it
    into a CompanyMember and sets accepted_at (accept_pending_invites, T4.5).

    States: pending (accepted_at NULL, expires_at in the future), accepted (accepted_at set),
    expired (accepted_at NULL, expires_at in the past). Only pending invites are used.
    """

    __tablename__ = "company_invite"
    __table_args__ = (
        CheckConstraint("email = lower(email)", name="ck_company_invite_email_lowercase"),
    )

    invite_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("company.company_id", ondelete="CASCADE"),  # company deleted -> invites go too
        nullable=False,
        index=True,
    )
    email = Column(String(320), nullable=False, index=True)  # always stored lowercase
    role = Column(_enum(CompanyRole, "ck_company_invite_role"), nullable=False)
    invited_by = Column(
        UUID(as_uuid=True),
        ForeignKey("app_user.user_id", ondelete="SET NULL"),  # inviter deleted -> keep the invite
        nullable=True,
    )
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    accepted_at = Column(TIMESTAMP(timezone=True), nullable=True)  # NULL = not used yet
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    company = relationship("Company", back_populates="invites")
