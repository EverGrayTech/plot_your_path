"""Skill database model."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from backend.database import Base


class Skill(Base):
    """
    Skill model representing technical and soft skills.
    
    Attributes:
        id: Primary key
        name: Skill name (unique)
        category: Skill category (technical, soft, domain, tool, language)
        created_at: Timestamp when record was created
    """

    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True, index=True)
    category = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        """String representation of Skill."""
        return f"<Skill(id={self.id}, name='{self.name}', category='{self.category}')>"
