"""Company Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl


class CompanyBase(BaseModel):
    """Base company schema with common fields."""

    name: str
    website: HttpUrl | None = None


class CompanyCreate(CompanyBase):
    """Schema for creating a new company."""

    pass


class Company(CompanyBase):
    """Complete company schema with database fields."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    created_at: datetime
