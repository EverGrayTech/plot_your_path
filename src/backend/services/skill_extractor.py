"""Skill extraction and deduplication service."""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models.role_skill import RoleSkill
from backend.models.skill import Skill


class SkillExtractorService:
    """
    Service for extracting, deduplicating, and persisting skills.

    Handles:
    - Normalizing skill names (case-insensitive deduplication)
    - Upsert: find existing or create new Skill records
    - Link skills to roles via RoleSkill records
    """

    def __init__(self, db: Session) -> None:
        """
        Initialize the skill extractor.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    @staticmethod
    def normalize_skill_name(name: str) -> str:
        """
        Normalize a skill name for deduplication.

        Strips whitespace and applies consistent capitalization rules
        for common skills.

        Args:
            name: Raw skill name

        Returns:
            Normalized skill name

        Examples:
            >>> normalize_skill_name("  python  ")
            'Python'
            >>> normalize_skill_name("javascript")
            'JavaScript'
            >>> normalize_skill_name("REST APIs")
            'REST APIs'
        """
        # Strip whitespace
        name = name.strip()

        # Special case normalizations (common skills with known correct casing)
        KNOWN_CAPITALIZATIONS: dict[str, str] = {
            "python": "Python",
            "javascript": "JavaScript",
            "typescript": "TypeScript",
            "react": "React",
            "react.js": "React",
            "reactjs": "React",
            "vue": "Vue.js",
            "vue.js": "Vue.js",
            "angular": "Angular",
            "node.js": "Node.js",
            "nodejs": "Node.js",
            "fastapi": "FastAPI",
            "django": "Django",
            "flask": "Flask",
            "postgresql": "PostgreSQL",
            "mysql": "MySQL",
            "mongodb": "MongoDB",
            "redis": "Redis",
            "docker": "Docker",
            "kubernetes": "Kubernetes",
            "aws": "AWS",
            "gcp": "GCP",
            "azure": "Azure",
            "git": "Git",
            "graphql": "GraphQL",
            "rest": "REST",
            "sql": "SQL",
            "html": "HTML",
            "css": "CSS",
            "rust": "Rust",
            "go": "Go",
            "golang": "Go",
            "java": "Java",
            "c++": "C++",
            "c#": "C#",
            "ruby": "Ruby",
            "scala": "Scala",
            "kafka": "Apache Kafka",
            "apache kafka": "Apache Kafka",
            "spark": "Apache Spark",
            "apache spark": "Apache Spark",
        }

        lower_name = name.lower()
        if lower_name in KNOWN_CAPITALIZATIONS:
            return KNOWN_CAPITALIZATIONS[lower_name]

        # Default: title case for simple words, preserve for complex names
        return name

    def get_or_create_skill(self, name: str, category: str | None = None) -> Skill:
        """
        Get an existing skill or create a new one.

        Uses case-insensitive name matching for deduplication.

        Args:
            name: Raw skill name (will be normalized)
            category: Optional skill category

        Returns:
            Skill database record (existing or newly created)
        """
        normalized_name = self.normalize_skill_name(name)

        # Look up by exact normalized name (case-insensitive)
        existing = (
            self.db.query(Skill)
            .filter(Skill.name.ilike(normalized_name))
            .first()
        )

        if existing:
            return existing

        # Create new skill
        skill = Skill(name=normalized_name, category=category)
        self.db.add(skill)
        self.db.flush()  # Get the ID without committing
        return skill

    def link_skills_to_role(
        self,
        role_id: int,
        required_skills: list[str],
        preferred_skills: list[str],
    ) -> int:
        """
        Link extracted skills to a role in the database.

        Creates Skill records if they don't exist and links them
        to the role via RoleSkill junction records.

        Args:
            role_id: ID of the role to link skills to
            required_skills: List of required skill names
            preferred_skills: List of preferred skill names

        Returns:
            Total number of skills linked
        """
        total_linked = 0

        for skill_name in required_skills:
            if not skill_name.strip():
                continue
            skill = self.get_or_create_skill(skill_name)
            role_skill = RoleSkill(
                role_id=role_id,
                skill_id=skill.id,
                requirement_level="required",
            )
            self.db.add(role_skill)
            total_linked += 1

        for skill_name in preferred_skills:
            if not skill_name.strip():
                continue
            skill = self.get_or_create_skill(skill_name)
            role_skill = RoleSkill(
                role_id=role_id,
                skill_id=skill.id,
                requirement_level="preferred",
            )
            self.db.add(role_skill)
            total_linked += 1

        self.db.flush()
        return total_linked

    def get_skills_for_role(self, role_id: int) -> dict[str, list[str]]:
        """
        Get all skills associated with a role.

        Args:
            role_id: ID of the role

        Returns:
            Dictionary with 'required' and 'preferred' skill name lists
        """
        role_skills = (
            self.db.query(RoleSkill, Skill)
            .join(Skill, RoleSkill.skill_id == Skill.id)
            .filter(RoleSkill.role_id == role_id)
            .all()
        )

        required: list[str] = []
        preferred: list[str] = []

        for role_skill, skill in role_skills:
            if role_skill.requirement_level == "required":
                required.append(skill.name)
            else:
                preferred.append(skill.name)

        return {"required": required, "preferred": preferred}
