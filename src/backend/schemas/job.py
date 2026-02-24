"""Job-related Pydantic schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, HttpUrl

from backend.schemas.company import Company


class RoleStatus(str, Enum):
    """Role status enumeration."""

    ACTIVE = "active"
    APPLIED = "applied"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class RequirementLevel(str, Enum):
    """Skill requirement level enumeration."""

    REQUIRED = "required"
    PREFERRED = "preferred"


class JobScrapeRequest(BaseModel):
    """Schema for job scraping request."""

    url: HttpUrl


class JobScrapeResponse(BaseModel):
    """Schema for job scraping response."""

    status: str
    role_id: int
    company: str
    title: str
    skills_extracted: int
    processing_time_seconds: float


class SalaryInfo(BaseModel):
    """Salary information schema."""

    min: int | None
    max: int | None
    currency: str


class JobListItem(BaseModel):
    """Schema for job list item (summary view)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    company: str
    title: str
    salary_range: str | None
    created_at: datetime
    skills_count: int
    status: RoleStatus


class JobDetail(BaseModel):
    """Schema for detailed job view."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    company: Company
    title: str
    team_division: str | None
    salary: SalaryInfo
    url: str
    skills: dict[str, list[str]]  # {"required": [...], "preferred": [...]}
    description_md: str
    created_at: datetime
    status: RoleStatus
