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
