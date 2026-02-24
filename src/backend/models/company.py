"""Company database model."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from src.backend.database import Base


class Company(Base):
    """
    Company model representing potential employers.
    
    Attributes:
        id: Primary key
        name: Company name (unique)
        slug: URL-friendly company identifier (unique)
        website: Company website URL
        created_at: Timestamp when record was created
    """

    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True, index=True)
    slug = Column(String, nullable=False, unique=True, index=True)
    website = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        """String representation of Company."""
        return f"<Company(id={self.id}, name='{self.name}', slug='{self.slug}')>"
