from enum import Enum


class EmploymentType(str, Enum):
    full_time = "full_time"
    part_time = "part_time"
    contract = "contract"
    internship = "internship"
    temporary = "temporary"


class ExperienceLevel(str, Enum):
    entry = "entry"
    mid = "mid"
    senior = "senior"
    lead = "lead"


class JobStatus(str, Enum):
    draft = "draft"
    open = "open"
    closed = "closed"


class WorkMode(str, Enum):
    onsite = "onsite"
    hybrid = "hybrid"
    remote = "remote"


class SalaryPeriod(str, Enum):
    hourly = "hourly"
    monthly = "monthly"
    yearly = "yearly"


class CompanyRole(str, Enum):
    owner = "owner"
    admin = "admin"
    recruiter = "recruiter"


class AuthProvider(str, Enum):
    google = "google"
    dev = "dev"  # only created by POST /auth/dev-login when ENABLE_DEV_LOGIN=true
