"""Company Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, HttpUrl


class CompanyBase(BaseModel):
    """Base company schema with common fields."""

    name: str
    website: HttpUrl | None = None


class CompanyCreate(CompanyBase):
    """Schema for creating a new company."""

    pass


class Company(CompanyBase):
    """Complete company schema with database fields."""

    id: int
    slug: str
    created_at: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True
