"""Role database model."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from backend.database import Base


class Role(Base):
    """
    Role model representing specific job openings.
    
    Attributes:
        id: Primary key
        company_id: Foreign key to companies table
        title: Job title
        team_division: Team or division within company
        salary_min: Minimum salary
        salary_max: Maximum salary
        salary_currency: Currency code (default: USD)
        url: Original job posting URL (unique)
        raw_html_path: Path to raw HTML file
        cleaned_md_path: Path to cleaned Markdown file
        status: Job status (active, applied, rejected, archived)
        created_at: Timestamp when record was created
    """

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    team_division = Column(String, nullable=True)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    salary_currency = Column(String, default="USD", nullable=False)
    url = Column(String, nullable=False, unique=True, index=True)
    raw_html_path = Column(String, nullable=False)
    cleaned_md_path = Column(String, nullable=False)
    status = Column(String, default="active", nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        """String representation of Role."""
        return f"<Role(id={self.id}, title='{self.title}', company_id={self.company_id})>"
