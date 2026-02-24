"""Jobs API router - scrape, list, detail, and status update endpoints."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import llm_config, scraping_config
from backend.database import get_db
from backend.models.company import Company
from backend.models.role import Role
from backend.models.role_skill import RoleSkill
from backend.schemas.company import Company as CompanySchema
from backend.schemas.job import (
    JobDetail,
    JobListItem,
    JobScrapeRequest,
    JobScrapeResponse,
    RoleStatus,
    SalaryInfo,
)
from backend.services.llm_service import LLMError, LLMService
from backend.services.scraper import ScraperError, ScraperService
from backend.services.skill_extractor import SkillExtractorService
from backend.utils.file_storage import file_exists, load_file, save_file
from backend.utils.slug import create_slug

router = APIRouter()


class StatusUpdate(BaseModel):
    """Schema for updating a job's status."""

    status: RoleStatus


def _build_salary_range(role: Role) -> str | None:
    """
    Build a human-readable salary range string from a Role record.

    Args:
        role: Role ORM instance

    Returns:
        Formatted salary string, or None if no salary info is present
    """
    if not role.salary_min and not role.salary_max:
        return None
    currency = role.salary_currency or "USD"
    symbol = "$" if currency == "USD" else ""
    if role.salary_min and role.salary_max:
        return f"{symbol}{role.salary_min:,} - {symbol}{role.salary_max:,} {currency}"
    elif role.salary_min:
        return f"{symbol}{role.salary_min:,}+ {currency}"
    else:
        return f"Up to {symbol}{role.salary_max:,} {currency}"


@router.get("/jobs", response_model=list[JobListItem])
def list_jobs(db: Session = Depends(get_db)) -> list[JobListItem]:
    """
    List all captured job postings.

    Returns:
        List of job summaries ordered by most recently captured.
    """
    rows = (
        db.query(Role, Company)
        .join(Company, Role.company_id == Company.id)
        .order_by(Role.created_at.desc())
        .all()
    )

    result: list[JobListItem] = []
    for role, company in rows:
        skills_count = db.query(RoleSkill).filter(RoleSkill.role_id == role.id).count()
        result.append(
            JobListItem(
                id=role.id,
                company=company.name,
                title=role.title,
                salary_range=_build_salary_range(role),
                created_at=role.created_at,
                skills_count=skills_count,
                status=RoleStatus(role.status),
            )
        )
    return result


@router.get("/jobs/{role_id}", response_model=JobDetail)
def get_job(role_id: int, db: Session = Depends(get_db)) -> JobDetail:
    """
    Get detailed information for a specific job posting.

    Args:
        role_id: The numeric ID of the role.

    Returns:
        Full job detail including skills and Markdown description.

    Raises:
        HTTPException 404: If the job is not found.
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Job not found")

    company = db.query(Company).filter(Company.id == role.company_id).first()

    # Load cleaned Markdown from disk (graceful fallback)
    description_md = ""
    if role.cleaned_md_path and file_exists(role.cleaned_md_path):
        description_md = load_file(role.cleaned_md_path)

    # Fetch associated skills
    extractor = SkillExtractorService(db)
    skills = extractor.get_skills_for_role(role_id)

    return JobDetail(
        id=role.id,
        company=CompanySchema.model_validate(company),
        title=role.title,
        team_division=role.team_division,
        salary=SalaryInfo(
            min=role.salary_min,
            max=role.salary_max,
            currency=role.salary_currency or "USD",
        ),
        url=role.url,
        skills=skills,
        description_md=description_md,
        created_at=role.created_at,
        status=RoleStatus(role.status),
    )


@router.patch("/jobs/{role_id}/status", response_model=JobListItem)
def update_job_status(
    role_id: int,
    status_update: StatusUpdate,
    db: Session = Depends(get_db),
) -> JobListItem:
    """
    Update the status of a job posting.

    Args:
        role_id: The numeric ID of the role.
        status_update: New status value.

    Returns:
        Updated job summary.

    Raises:
        HTTPException 404: If the job is not found.
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Job not found")

    role.status = status_update.status.value
    db.commit()
    db.refresh(role)

    company = db.query(Company).filter(Company.id == role.company_id).first()
    skills_count = db.query(RoleSkill).filter(RoleSkill.role_id == role.id).count()

    return JobListItem(
        id=role.id,
        company=company.name,
        title=role.title,
        salary_range=_build_salary_range(role),
        created_at=role.created_at,
        skills_count=skills_count,
        status=RoleStatus(role.status),
    )


@router.post("/jobs/scrape", response_model=JobScrapeResponse)
async def scrape_job(
    request: JobScrapeRequest,
    db: Session = Depends(get_db),
) -> JobScrapeResponse:
    """
    Scrape a job posting URL and persist all extracted data.

    Pipeline:
        1. Validate URL and check for duplicates
        2. Scrape raw HTML
        3. LLM de-noise HTML → clean Markdown
        4. LLM extract structured job data + skills
        5. Upsert Company record
        6. Create Role record with file paths
        7. Save HTML and Markdown to disk
        8. Link extracted skills via Role_Skills

    Args:
        request: Scrape request containing the job posting URL.

    Returns:
        Scrape result including role ID, company, title, and skill count.

    Raises:
        HTTPException 422: If the URL cannot be scraped or data cannot be processed.
        HTTPException 500: If an unexpected internal error occurs.
    """
    start_time = time.time()
    url = str(request.url)

    # --- Deduplication: return existing record if URL was already captured ---
    existing_role = db.query(Role).filter(Role.url == url).first()
    if existing_role:
        company = db.query(Company).filter(Company.id == existing_role.company_id).first()
        skills_count = (
            db.query(RoleSkill).filter(RoleSkill.role_id == existing_role.id).count()
        )
        return JobScrapeResponse(
            status="already_exists",
            role_id=existing_role.id,
            company=company.name if company else "Unknown",
            title=existing_role.title,
            skills_extracted=skills_count,
            processing_time_seconds=round(time.time() - start_time, 3),
        )

    # --- Step 1: Scrape HTML ---
    scraper = ScraperService(config=scraping_config)
    try:
        html = await scraper.scrape(url)
    except ScraperError as exc:
        raise HTTPException(status_code=422, detail=f"Scraping failed: {exc}") from exc

    raw_text = scraper.extract_text_from_html(html)

    # --- Step 2: LLM de-noise ---
    llm = LLMService(config=llm_config)
    try:
        markdown = await llm.denoise_job_posting(raw_text)
    except LLMError as exc:
        raise HTTPException(
            status_code=500, detail=f"LLM de-noising failed: {exc}"
        ) from exc

    # --- Step 3: LLM skill / metadata extraction ---
    try:
        job_data = await llm.extract_job_data(markdown)
    except LLMError as exc:
        raise HTTPException(
            status_code=500, detail=f"LLM data extraction failed: {exc}"
        ) from exc

    # --- Step 4: Upsert Company ---
    company_name = (job_data.get("company") or "Unknown Company").strip() or "Unknown Company"
    company = db.query(Company).filter(Company.name.ilike(company_name)).first()
    if not company:
        slug = create_slug(company_name)
        # Resolve slug collisions
        if db.query(Company).filter(Company.slug == slug).first():
            slug = f"{slug}-{int(time.time())}"
        company = Company(name=company_name, slug=slug)
        db.add(company)
        db.flush()

    # --- Step 5: Create Role with placeholder paths (need ID first) ---
    title = (job_data.get("title") or "Unknown Title").strip() or "Unknown Title"
    role = Role(
        company_id=company.id,
        title=title,
        team_division=job_data.get("team_division"),
        salary_min=job_data.get("salary_min"),
        salary_max=job_data.get("salary_max"),
        salary_currency=job_data.get("salary_currency") or "USD",
        url=url,
        raw_html_path="pending",
        cleaned_md_path="pending",
        status="active",
    )
    db.add(role)
    db.flush()  # Obtain role.id before building file paths

    # --- Step 6: Persist files at canonical paths ---
    raw_path = f"data/jobs/raw/{company.slug}/{role.id}.html"
    cleaned_path = f"data/jobs/cleaned/{company.slug}/{role.id}.md"
    save_file(html, raw_path)
    save_file(markdown, cleaned_path)

    role.raw_html_path = raw_path
    role.cleaned_md_path = cleaned_path

    # --- Step 7: Extract and link skills ---
    extractor = SkillExtractorService(db)
    required_skills: list[str] = job_data.get("required_skills") or []
    preferred_skills: list[str] = job_data.get("preferred_skills") or []
    skills_count = extractor.link_skills_to_role(role.id, required_skills, preferred_skills)

    db.commit()

    return JobScrapeResponse(
        status="success",
        role_id=role.id,
        company=company.name,
        title=title,
        skills_extracted=skills_count,
        processing_time_seconds=round(time.time() - start_time, 3),
    )
