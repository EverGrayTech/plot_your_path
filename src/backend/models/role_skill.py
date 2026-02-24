"""RoleSkill database model (junction table)."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from src.backend.database import Base


class RoleSkill(Base):
    """
    RoleSkill model linking roles to skills with requirement level.
    
    Attributes:
        id: Primary key
        role_id: Foreign key to roles table
        skill_id: Foreign key to skills table
        requirement_level: Whether skill is 'required' or 'preferred'
        created_at: Timestamp when record was created
    """

    __tablename__ = "role_skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False, index=True)
    requirement_level = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Ensure unique combination of role_id and skill_id
    __table_args__ = (UniqueConstraint("role_id", "skill_id", name="_role_skill_uc"),)

    def __repr__(self) -> str:
        """String representation of RoleSkill."""
        return (
            f"<RoleSkill(id={self.id}, role_id={self.role_id}, "
            f"skill_id={self.skill_id}, level='{self.requirement_level}')>"
        )
