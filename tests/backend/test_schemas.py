"""Tests for Pydantic schemas."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from backend.schemas.company import Company, CompanyBase, CompanyCreate
from backend.schemas.job import (
    JobScrapeRequest,
    JobScrapeResponse,
    RequirementLevel,
    RoleStatus,
    SalaryInfo,
)
from backend.schemas.skill import Skill, SkillBase, SkillCategory, SkillCreate


class TestCompanySchemas:
    """Tests for company schemas."""

    def test_company_base_valid(self):
        """Test CompanyBase with valid data."""
        company = CompanyBase(name="Acme Corp", website="https://acme.com")
        assert company.name == "Acme Corp"
        assert str(company.website) == "https://acme.com/"

    def test_company_base_no_website(self):
        """Test CompanyBase without website."""
        company = CompanyBase(name="Acme Corp")
        assert company.name == "Acme Corp"
        assert company.website is None

    def test_company_base_invalid_url(self):
        """Test CompanyBase with invalid URL."""
        with pytest.raises(ValidationError):
            CompanyBase(name="Acme Corp", website="not-a-url")

    def test_company_create(self):
        """Test CompanyCreate schema."""
        company = CompanyCreate(name="Acme Corp", website="https://acme.com")
        assert company.name == "Acme Corp"

    def test_company_full(self):
        """Test full Company schema."""
        company = Company(
            id=1,
            name="Acme Corp",
            slug="acme-corp",
            website="https://acme.com",
            created_at=datetime.now(),
        )
        assert company.id == 1
        assert company.slug == "acme-corp"


class TestSkillSchemas:
    """Tests for skill schemas."""

    def test_skill_category_enum(self):
        """Test SkillCategory enum values."""
        assert SkillCategory.TECHNICAL == "technical"
        assert SkillCategory.SOFT == "soft"
        assert SkillCategory.DOMAIN == "domain"
        assert SkillCategory.TOOL == "tool"
        assert SkillCategory.LANGUAGE == "language"

    def test_skill_base_valid(self):
        """Test SkillBase with valid data."""
        skill = SkillBase(name="Python", category=SkillCategory.TECHNICAL)
        assert skill.name == "Python"
        assert skill.category == SkillCategory.TECHNICAL

    def test_skill_base_no_category(self):
        """Test SkillBase without category."""
        skill = SkillBase(name="Python")
        assert skill.name == "Python"
        assert skill.category is None

    def test_skill_create(self):
        """Test SkillCreate schema."""
        skill = SkillCreate(name="Python", category=SkillCategory.LANGUAGE)
        assert skill.name == "Python"
        assert skill.category == SkillCategory.LANGUAGE

    def test_skill_full(self):
        """Test full Skill schema."""
        skill = Skill(
            id=1,
            name="Python",
            category=SkillCategory.LANGUAGE,
            created_at=datetime.now(),
        )
        assert skill.id == 1
        assert skill.name == "Python"


class TestJobSchemas:
    """Tests for job-related schemas."""

    def test_role_status_enum(self):
        """Test RoleStatus enum values."""
        assert RoleStatus.ACTIVE == "active"
        assert RoleStatus.APPLIED == "applied"
        assert RoleStatus.REJECTED == "rejected"
        assert RoleStatus.ARCHIVED == "archived"

    def test_requirement_level_enum(self):
        """Test RequirementLevel enum values."""
        assert RequirementLevel.REQUIRED == "required"
        assert RequirementLevel.PREFERRED == "preferred"

    def test_job_scrape_request_valid(self):
        """Test JobScrapeRequest with valid URL."""
        request = JobScrapeRequest(url="https://linkedin.com/jobs/view/123")
        assert str(request.url) == "https://linkedin.com/jobs/view/123"

    def test_job_scrape_request_invalid_url(self):
        """Test JobScrapeRequest with invalid URL."""
        with pytest.raises(ValidationError):
            JobScrapeRequest(url="not-a-url")

    def test_job_scrape_response(self):
        """Test JobScrapeResponse schema."""
        response = JobScrapeResponse(
            status="success",
            role_id=42,
            company="Acme Corp",
            title="Senior Engineer",
            skills_extracted=15,
            processing_time_seconds=12.5,
        )
        assert response.status == "success"
        assert response.role_id == 42
        assert response.skills_extracted == 15

    def test_salary_info(self):
        """Test SalaryInfo schema."""
        salary = SalaryInfo(min=150000, max=200000, currency="USD")
        assert salary.min == 150000
        assert salary.max == 200000
        assert salary.currency == "USD"

    def test_salary_info_no_range(self):
        """Test SalaryInfo without min/max."""
        salary = SalaryInfo(min=None, max=None, currency="USD")
        assert salary.min is None
        assert salary.max is None
