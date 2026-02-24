"""Skill Pydantic schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


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

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
