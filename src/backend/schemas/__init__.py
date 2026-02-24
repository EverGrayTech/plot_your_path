"""Pydantic schemas package."""

from backend.schemas.company import Company, CompanyBase, CompanyCreate
from backend.schemas.job import (
    JobDetail,
    JobListItem,
    JobScrapeRequest,
    JobScrapeResponse,
    RequirementLevel,
    RoleStatus,
    SalaryInfo,
)
from backend.schemas.skill import Skill, SkillBase, SkillCategory, SkillCreate

__all__ = [
    "Company",
    "CompanyBase",
    "CompanyCreate",
    "JobDetail",
    "JobListItem",
    "JobScrapeRequest",
    "JobScrapeResponse",
    "RequirementLevel",
    "RoleStatus",
    "SalaryInfo",
    "Skill",
    "SkillBase",
    "SkillCategory",
    "SkillCreate",
]
