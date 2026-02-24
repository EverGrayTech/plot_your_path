"""Skill Pydantic schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class SkillCategory(str, Enum):
    """Skill category enumeration."""

    TECHNICAL = "technical"
    SOFT = "soft"
    DOMAIN = "domain"
    TOOL = "tool"
    LANGUAGE = "language"


class SkillBase(BaseModel):
    """Base skill schema with common fields."""

    name: str
    category: SkillCategory | None = None


class SkillCreate(SkillBase):
    """Schema for creating a new skill."""

    pass


class Skill(SkillBase):
    """Complete skill schema with database fields."""

    id: int
    created_at: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True
