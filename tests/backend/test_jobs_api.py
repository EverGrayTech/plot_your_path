"""Integration tests for the Jobs API endpoints."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.main import app
from backend.models.company import Company
from backend.models.role import Role
from backend.models.role_skill import RoleSkill
from backend.models.skill import Skill

# ---------------------------------------------------------------------------
# In-memory SQLite test database (shared via StaticPool)
# ---------------------------------------------------------------------------
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Dependency override that uses the test in-memory database."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def setup_db():
    """Create and tear down tables around each test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """TestClient with the DB dependency overridden."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def db():
    """SQLAlchemy session for pre-populating test data."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_company(db):
    """Create a Company record in the test DB."""
    company = Company(name="Acme Corp", slug="acme-corp")
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@pytest.fixture
def sample_role(db, sample_company):
    """Create a Role record linked to sample_company."""
    role = Role(
        company_id=sample_company.id,
        title="Software Engineer",
        team_division="Platform",
        salary_min=120000,
        salary_max=180000,
        salary_currency="USD",
        url="https://greenhouse.io/jobs/12345",
        raw_html_path="data/jobs/raw/acme-corp/1.html",
        cleaned_md_path="data/jobs/cleaned/acme-corp/1.md",
        status="active",
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@pytest.fixture
def sample_skills(db, sample_role):
    """Create Skill and RoleSkill records linked to sample_role."""
    python_skill = Skill(name="Python", category="language")
    db.add(python_skill)
    db.flush()

    ts_skill = Skill(name="TypeScript", category="language")
    db.add(ts_skill)
    db.flush()

    db.add(RoleSkill(role_id=sample_role.id, skill_id=python_skill.id, requirement_level="required"))
    db.add(RoleSkill(role_id=sample_role.id, skill_id=ts_skill.id, requirement_level="preferred"))
    db.commit()
    return [python_skill, ts_skill]


# ---------------------------------------------------------------------------
# Helper: canonical LLM job data response
# ---------------------------------------------------------------------------

SAMPLE_JOB_DATA = {
    "title": "Backend Engineer",
    "company": "TechCo",
    "team_division": "Infrastructure",
    "salary_min": 130000,
    "salary_max": 170000,
    "salary_currency": "USD",
    "required_skills": ["Python", "FastAPI", "Docker"],
    "preferred_skills": ["Kubernetes", "Go"],
}


# ---------------------------------------------------------------------------
# Tests: GET /api/jobs
# ---------------------------------------------------------------------------


class TestListJobs:
    """Tests for GET /api/jobs."""

    def test_list_empty(self, client):
        """Empty list returned when no jobs have been captured."""
        response = client.get("/api/jobs")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_returns_jobs(self, client, sample_role, sample_company, sample_skills):
        """Jobs list includes captured roles with correct fields."""
        response = client.get("/api/jobs")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        job = data[0]
        assert job["id"] == sample_role.id
        assert job["company"] == "Acme Corp"
        assert job["title"] == "Software Engineer"
        assert job["skills_count"] == 2
        assert job["status"] == "active"
        assert "$120,000 - $180,000 USD" in job["salary_range"]

    def test_list_no_salary_returns_none(self, db, client, sample_company):
        """Jobs without salary info return null salary_range."""
        role = Role(
            company_id=sample_company.id,
            title="Intern",
            url="https://example.com/intern",
            raw_html_path="data/jobs/raw/acme-corp/2.html",
            cleaned_md_path="data/jobs/cleaned/acme-corp/2.md",
            status="active",
        )
        db.add(role)
        db.commit()

        response = client.get("/api/jobs")
        assert response.status_code == 200
        data = response.json()
        intern = next(j for j in data if j["title"] == "Intern")
        assert intern["salary_range"] is None

    def test_list_salary_min_only(self, db, client, sample_company):
        """Roles with only salary_min show a 'X+' range string."""
        role = Role(
            company_id=sample_company.id,
            title="Senior Dev",
            salary_min=150000,
            salary_currency="USD",
            url="https://example.com/senior",
            raw_html_path="data/jobs/raw/acme-corp/3.html",
            cleaned_md_path="data/jobs/cleaned/acme-corp/3.md",
            status="active",
        )
        db.add(role)
        db.commit()

        response = client.get("/api/jobs")
        data = response.json()
        senior = next(j for j in data if j["title"] == "Senior Dev")
        assert "$150,000+" in senior["salary_range"]

    def test_list_salary_max_only(self, db, client, sample_company):
        """Roles with only salary_max show an 'Up to X' range string."""
        role = Role(
            company_id=sample_company.id,
            title="Junior Dev",
            salary_max=90000,
            salary_currency="USD",
            url="https://example.com/junior",
            raw_html_path="data/jobs/raw/acme-corp/4.html",
            cleaned_md_path="data/jobs/cleaned/acme-corp/4.md",
            status="active",
        )
        db.add(role)
        db.commit()

        response = client.get("/api/jobs")
        data = response.json()
        junior = next(j for j in data if j["title"] == "Junior Dev")
        assert "Up to $90,000" in junior["salary_range"]

    def test_list_non_usd_currency(self, db, client, sample_company):
        """Non-USD currency shows currency code without dollar sign."""
        role = Role(
            company_id=sample_company.id,
            title="EU Engineer",
            salary_min=80000,
            salary_max=100000,
            salary_currency="EUR",
            url="https://example.com/eu",
            raw_html_path="data/jobs/raw/acme-corp/5.html",
            cleaned_md_path="data/jobs/cleaned/acme-corp/5.md",
            status="active",
        )
        db.add(role)
        db.commit()

        response = client.get("/api/jobs")
        data = response.json()
        eu = next(j for j in data if j["title"] == "EU Engineer")
        assert "EUR" in eu["salary_range"]
        assert "$" not in eu["salary_range"]


# ---------------------------------------------------------------------------
# Tests: GET /api/jobs/{id}
# ---------------------------------------------------------------------------


class TestGetJob:
    """Tests for GET /api/jobs/{role_id}."""

    def test_get_not_found(self, client):
        """Returns 404 when role does not exist."""
        response = client.get("/api/jobs/999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Job not found"

    def test_get_job_no_file(self, client, sample_role, sample_skills):
        """Returns 200 with empty description when Markdown file is missing."""
        response = client.get(f"/api/jobs/{sample_role.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_role.id
        assert data["title"] == "Software Engineer"
        assert data["company"]["name"] == "Acme Corp"
        assert data["description_md"] == ""
        assert "Python" in data["skills"]["required"]
        assert "TypeScript" in data["skills"]["preferred"]
        assert data["salary"]["min"] == 120000
        assert data["salary"]["max"] == 180000

    def test_get_job_with_file(self, client, db, sample_role, sample_skills):
        """Returns Markdown content when the cleaned file exists on disk."""
        with patch("backend.routers.jobs.file_exists", return_value=True), \
             patch("backend.routers.jobs.load_file", return_value="# Backend Engineer\n\nGreat role!"):
            response = client.get(f"/api/jobs/{sample_role.id}")

        assert response.status_code == 200
        assert response.json()["description_md"] == "# Backend Engineer\n\nGreat role!"

    def test_get_job_team_division(self, client, sample_role):
        """Team division is included in detail response."""
        response = client.get(f"/api/jobs/{sample_role.id}")
        assert response.status_code == 200
        assert response.json()["team_division"] == "Platform"


# ---------------------------------------------------------------------------
# Tests: PATCH /api/jobs/{id}/status
# ---------------------------------------------------------------------------


class TestUpdateJobStatus:
    """Tests for PATCH /api/jobs/{role_id}/status."""

    def test_update_status_not_found(self, client):
        """Returns 404 when role does not exist."""
        response = client.patch("/api/jobs/999/status", json={"status": "applied"})
        assert response.status_code == 404

    def test_update_status_success(self, client, sample_role):
        """Status is updated and new value returned in response."""
        response = client.patch(
            f"/api/jobs/{sample_role.id}/status", json={"status": "applied"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "applied"

    def test_update_status_invalid_value(self, client, sample_role):
        """Invalid status value returns 422 validation error."""
        response = client.patch(
            f"/api/jobs/{sample_role.id}/status", json={"status": "invalid_status"}
        )
        assert response.status_code == 422

    def test_update_status_all_valid_values(self, client, sample_role):
        """All valid status values are accepted."""
        for status in ("active", "applied", "rejected", "archived"):
            response = client.patch(
                f"/api/jobs/{sample_role.id}/status", json={"status": status}
            )
            assert response.status_code == 200
            assert response.json()["status"] == status


# ---------------------------------------------------------------------------
# Tests: POST /api/jobs/scrape
# ---------------------------------------------------------------------------


class TestScrapeJob:
    """Tests for POST /api/jobs/scrape."""

    def _mock_pipeline(self, html="<html><body>Job</body></html>", job_data=None):
        """Return a context manager that patches ScraperService and LLMService."""
        if job_data is None:
            job_data = SAMPLE_JOB_DATA

        mock_scraper_instance = MagicMock()
        mock_scraper_instance.scrape = AsyncMock(return_value=html)
        mock_scraper_instance.extract_text_from_html = MagicMock(return_value="Job text")

        mock_llm_instance = MagicMock()
        mock_llm_instance.denoise_job_posting = AsyncMock(return_value="# Backend Engineer")
        mock_llm_instance.extract_job_data = AsyncMock(return_value=job_data)

        return (mock_scraper_instance, mock_llm_instance)

    def test_scrape_successful(self, client):
        """Full pipeline creates role, company, and skills."""
        scraper_mock, llm_mock = self._mock_pipeline()

        with patch("backend.routers.jobs.ScraperService", return_value=scraper_mock), \
             patch("backend.routers.jobs.LLMService", return_value=llm_mock), \
             patch("backend.routers.jobs.save_file"):
            response = client.post(
                "/api/jobs/scrape",
                json={"url": "https://greenhouse.io/jobs/99999"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["company"] == "TechCo"
        assert data["title"] == "Backend Engineer"
        assert data["skills_extracted"] == 5  # 3 required + 2 preferred
        assert data["role_id"] >= 1
        assert data["processing_time_seconds"] >= 0

    def test_scrape_duplicate_url(self, client, sample_role):
        """Second scrape of the same URL returns already_exists status."""
        response = client.post(
            "/api/jobs/scrape",
            json={"url": "https://greenhouse.io/jobs/12345"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "already_exists"
        assert data["role_id"] == sample_role.id

    def test_scrape_invalid_url(self, client):
        """Pydantic rejects malformed URLs with 422."""
        response = client.post(
            "/api/jobs/scrape",
            json={"url": "not-a-valid-url"},
        )
        assert response.status_code == 422

    def test_scrape_scraper_error_returns_422(self, client):
        """ScraperError from the scraping service raises HTTP 422."""
        from backend.services.scraper import ScraperError

        mock_scraper = MagicMock()
        mock_scraper.scrape = AsyncMock(side_effect=ScraperError("blocked"))

        with patch("backend.routers.jobs.ScraperService", return_value=mock_scraper):
            response = client.post(
                "/api/jobs/scrape",
                json={"url": "https://blocked.example.com/job/1"},
            )

        assert response.status_code == 422
        assert "Scraping failed" in response.json()["detail"]

    def test_scrape_llm_denoise_error_returns_500(self, client):
        """LLMError during de-noising raises HTTP 500."""
        from backend.services.llm_service import LLMError

        mock_scraper = MagicMock()
        mock_scraper.scrape = AsyncMock(return_value="<html>Job</html>")
        mock_scraper.extract_text_from_html = MagicMock(return_value="Job text")

        mock_llm = MagicMock()
        mock_llm.denoise_job_posting = AsyncMock(side_effect=LLMError("timeout"))

        with patch("backend.routers.jobs.ScraperService", return_value=mock_scraper), \
             patch("backend.routers.jobs.LLMService", return_value=mock_llm):
            response = client.post(
                "/api/jobs/scrape",
                json={"url": "https://greenhouse.io/jobs/77777"},
            )

        assert response.status_code == 500
        assert "LLM de-noising failed" in response.json()["detail"]

    def test_scrape_llm_extraction_error_returns_500(self, client):
        """LLMError during skill extraction raises HTTP 500."""
        from backend.services.llm_service import LLMError

        mock_scraper = MagicMock()
        mock_scraper.scrape = AsyncMock(return_value="<html>Job</html>")
        mock_scraper.extract_text_from_html = MagicMock(return_value="Job text")

        mock_llm = MagicMock()
        mock_llm.denoise_job_posting = AsyncMock(return_value="# Good job")
        mock_llm.extract_job_data = AsyncMock(side_effect=LLMError("bad json"))

        with patch("backend.routers.jobs.ScraperService", return_value=mock_scraper), \
             patch("backend.routers.jobs.LLMService", return_value=mock_llm):
            response = client.post(
                "/api/jobs/scrape",
                json={"url": "https://greenhouse.io/jobs/88888"},
            )

        assert response.status_code == 500
        assert "LLM data extraction failed" in response.json()["detail"]

    def test_scrape_existing_company_deduplication(self, client, db, sample_company):
        """Scraping a job at an existing company reuses the Company record."""
        job_data = {**SAMPLE_JOB_DATA, "company": "Acme Corp"}  # matches fixture company
        scraper_mock, llm_mock = self._mock_pipeline(job_data=job_data)

        with patch("backend.routers.jobs.ScraperService", return_value=scraper_mock), \
             patch("backend.routers.jobs.LLMService", return_value=llm_mock), \
             patch("backend.routers.jobs.save_file"):
            response = client.post(
                "/api/jobs/scrape",
                json={"url": "https://greenhouse.io/jobs/new-acme-job"},
            )

        assert response.status_code == 200
        assert response.json()["company"] == "Acme Corp"
        # Only one company should exist
        assert db.query(Company).count() == 1

    def test_scrape_empty_skills(self, client):
        """Pipeline handles job postings with no extracted skills."""
        job_data = {**SAMPLE_JOB_DATA, "required_skills": [], "preferred_skills": []}
        scraper_mock, llm_mock = self._mock_pipeline(job_data=job_data)

        with patch("backend.routers.jobs.ScraperService", return_value=scraper_mock), \
             patch("backend.routers.jobs.LLMService", return_value=llm_mock), \
             patch("backend.routers.jobs.save_file"):
            response = client.post(
                "/api/jobs/scrape",
                json={"url": "https://greenhouse.io/jobs/no-skills"},
            )

        assert response.status_code == 200
        assert response.json()["skills_extracted"] == 0

    def test_scrape_slug_collision_resolved(self, client, db):
        """When a slug already exists, a suffix is added to avoid collision."""
        # Create a company whose slug would collide
        db.add(Company(name="NewCo", slug="newco"))
        db.commit()

        # A different company whose slug normalizes to the same value
        job_data = {**SAMPLE_JOB_DATA, "company": "NewCo"}
        scraper_mock, llm_mock = self._mock_pipeline(job_data=job_data)

        # This time the company name already exists, so it should reuse it
        with patch("backend.routers.jobs.ScraperService", return_value=scraper_mock), \
             patch("backend.routers.jobs.LLMService", return_value=llm_mock), \
             patch("backend.routers.jobs.save_file"):
            response = client.post(
                "/api/jobs/scrape",
                json={"url": "https://greenhouse.io/jobs/slug-test"},
            )

        assert response.status_code == 200
        assert db.query(Company).count() == 1

    def test_scrape_missing_company_defaults_to_unknown(self, client):
        """Empty/null company name from LLM defaults to 'Unknown Company'."""
        job_data = {**SAMPLE_JOB_DATA, "company": ""}
        scraper_mock, llm_mock = self._mock_pipeline(job_data=job_data)

        with patch("backend.routers.jobs.ScraperService", return_value=scraper_mock), \
             patch("backend.routers.jobs.LLMService", return_value=llm_mock), \
             patch("backend.routers.jobs.save_file"):
            response = client.post(
                "/api/jobs/scrape",
                json={"url": "https://greenhouse.io/jobs/unknown-co"},
            )

        assert response.status_code == 200
        assert response.json()["company"] == "Unknown Company"

    def test_scrape_saves_files(self, client):
        """save_file is called for both raw HTML and cleaned Markdown."""
        scraper_mock, llm_mock = self._mock_pipeline()

        with patch("backend.routers.jobs.ScraperService", return_value=scraper_mock), \
             patch("backend.routers.jobs.LLMService", return_value=llm_mock), \
             patch("backend.routers.jobs.save_file") as mock_save:
            response = client.post(
                "/api/jobs/scrape",
                json={"url": "https://greenhouse.io/jobs/file-test"},
            )

        assert response.status_code == 200
        assert mock_save.call_count == 2
        # First call: raw HTML
        assert mock_save.call_args_list[0][0][0] == "<html><body>Job</body></html>"
        # Second call: cleaned Markdown
        assert mock_save.call_args_list[1][0][0] == "# Backend Engineer"

    def test_scrape_no_salary_info(self, client):
        """Pipeline handles job postings without salary information."""
        job_data = {
            **SAMPLE_JOB_DATA,
            "salary_min": None,
            "salary_max": None,
            "salary_currency": "USD",
        }
        scraper_mock, llm_mock = self._mock_pipeline(job_data=job_data)

        with patch("backend.routers.jobs.ScraperService", return_value=scraper_mock), \
             patch("backend.routers.jobs.LLMService", return_value=llm_mock), \
             patch("backend.routers.jobs.save_file"):
            response = client.post(
                "/api/jobs/scrape",
                json={"url": "https://greenhouse.io/jobs/no-salary"},
            )

        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_scrape_true_slug_collision(self, client, db):
        """When slug exists for a different company name, a unique suffix is appended."""
        # Create a company whose slug would collide with the incoming job's company
        # "TechCo" → slug "techco"; "Tech Co" → slug also "tech-co"
        # To force a real slug collision: store "TechCo1" but slug="techco"
        db.add(Company(name="TechCo-Existing", slug="techco"))
        db.commit()

        # Now scrape a job for "TechCo" which would also slug to "techco"
        job_data = {**SAMPLE_JOB_DATA, "company": "TechCo"}
        scraper_mock, llm_mock = self._mock_pipeline(job_data=job_data)

        with patch("backend.routers.jobs.ScraperService", return_value=scraper_mock), \
             patch("backend.routers.jobs.LLMService", return_value=llm_mock), \
             patch("backend.routers.jobs.save_file"):
            response = client.post(
                "/api/jobs/scrape",
                json={"url": "https://greenhouse.io/jobs/slug-collision"},
            )

        assert response.status_code == 200
        assert response.json()["company"] == "TechCo"
        # Two companies should now exist, with different slugs
        companies = db.query(Company).all()
        assert len(companies) == 2
        slugs = {c.slug for c in companies}
        assert "techco" in slugs
        # New company should have a different slug
        assert any(s != "techco" for s in slugs)
