"""Tests for the skill extraction service."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models.company import Company
from backend.models.role import Role
from backend.models.role_skill import RoleSkill
from backend.models.skill import Skill
from backend.services.skill_extractor import SkillExtractorService


@pytest.fixture
def db():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # Create a company and role for testing
    company = Company(name="Test Corp", slug="test-corp")
    session.add(company)
    session.flush()

    role = Role(
        company_id=company.id,
        title="Software Engineer",
        url="https://example.com/jobs/1",
        raw_html_path="data/jobs/raw/test-corp/1.html",
        cleaned_md_path="data/jobs/cleaned/test-corp/1.md",
    )
    session.add(role)
    session.flush()

    yield session, role.id

    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


class TestNormalizeSkillName:
    """Tests for skill name normalization."""

    def test_normalize_python(self):
        """Test Python normalization."""
        assert SkillExtractorService.normalize_skill_name("python") == "Python"
        assert SkillExtractorService.normalize_skill_name("PYTHON") == "Python"

    def test_normalize_javascript(self):
        """Test JavaScript normalization."""
        assert SkillExtractorService.normalize_skill_name("javascript") == "JavaScript"
        assert SkillExtractorService.normalize_skill_name("Javascript") == "JavaScript"

    def test_normalize_react_variants(self):
        """Test React normalization for multiple variants."""
        assert SkillExtractorService.normalize_skill_name("react") == "React"
        assert SkillExtractorService.normalize_skill_name("react.js") == "React"
        assert SkillExtractorService.normalize_skill_name("reactjs") == "React"

    def test_normalize_nodejs_variants(self):
        """Test Node.js normalization."""
        assert SkillExtractorService.normalize_skill_name("node.js") == "Node.js"
        assert SkillExtractorService.normalize_skill_name("nodejs") == "Node.js"

    def test_normalize_go_golang(self):
        """Test Go/Golang normalization."""
        assert SkillExtractorService.normalize_skill_name("golang") == "Go"
        assert SkillExtractorService.normalize_skill_name("go") == "Go"

    def test_normalize_strips_whitespace(self):
        """Test that whitespace is stripped."""
        assert SkillExtractorService.normalize_skill_name("  Python  ") == "Python"

    def test_normalize_unknown_skill(self):
        """Test that unknown skills are returned as-is."""
        assert SkillExtractorService.normalize_skill_name("MyCustomSkill") == "MyCustomSkill"
        assert SkillExtractorService.normalize_skill_name("Terraform") == "Terraform"


class TestGetOrCreateSkill:
    """Tests for skill get-or-create logic."""

    def test_creates_new_skill(self, db):
        """Test creating a new skill."""
        session, role_id = db
        extractor = SkillExtractorService(db=session)

        skill = extractor.get_or_create_skill("Python")
        assert skill.id is not None
        assert skill.name == "Python"

    def test_returns_existing_skill(self, db):
        """Test that existing skill is returned, not duplicated."""
        session, role_id = db
        extractor = SkillExtractorService(db=session)

        skill1 = extractor.get_or_create_skill("Python")
        skill2 = extractor.get_or_create_skill("Python")
        assert skill1.id == skill2.id

    def test_case_insensitive_deduplication(self, db):
        """Test case-insensitive skill deduplication."""
        session, role_id = db
        extractor = SkillExtractorService(db=session)

        skill1 = extractor.get_or_create_skill("python")  # normalizes to "Python"
        skill2 = extractor.get_or_create_skill("Python")
        assert skill1.id == skill2.id

    def test_normalizes_skill_name(self, db):
        """Test that skill name is normalized on creation."""
        session, role_id = db
        extractor = SkillExtractorService(db=session)

        skill = extractor.get_or_create_skill("javascript")
        assert skill.name == "JavaScript"

    def test_stores_category(self, db):
        """Test that category is stored with skill."""
        session, role_id = db
        extractor = SkillExtractorService(db=session)

        skill = extractor.get_or_create_skill("Python", category="language")
        assert skill.category == "language"


class TestLinkSkillsToRole:
    """Tests for linking skills to a role."""

    def test_links_required_skills(self, db):
        """Test linking required skills."""
        session, role_id = db
        extractor = SkillExtractorService(db=session)

        count = extractor.link_skills_to_role(
            role_id=role_id,
            required_skills=["Python", "FastAPI"],
            preferred_skills=[],
        )
        assert count == 2

        role_skills = session.query(RoleSkill).filter_by(role_id=role_id).all()
        assert len(role_skills) == 2
        assert all(rs.requirement_level == "required" for rs in role_skills)

    def test_links_preferred_skills(self, db):
        """Test linking preferred skills."""
        session, role_id = db
        extractor = SkillExtractorService(db=session)

        count = extractor.link_skills_to_role(
            role_id=role_id,
            required_skills=[],
            preferred_skills=["Kubernetes", "Rust"],
        )
        assert count == 2

        role_skills = session.query(RoleSkill).filter_by(role_id=role_id).all()
        assert all(rs.requirement_level == "preferred" for rs in role_skills)

    def test_links_mixed_skills(self, db):
        """Test linking both required and preferred skills."""
        session, role_id = db
        extractor = SkillExtractorService(db=session)

        count = extractor.link_skills_to_role(
            role_id=role_id,
            required_skills=["Python", "SQL"],
            preferred_skills=["Docker"],
        )
        assert count == 3

    def test_ignores_empty_skill_names(self, db):
        """Test that empty skill names are ignored."""
        session, role_id = db
        extractor = SkillExtractorService(db=session)

        count = extractor.link_skills_to_role(
            role_id=role_id,
            required_skills=["Python", "", "  "],
            preferred_skills=[],
        )
        assert count == 1

    def test_deduplicates_skills_across_roles(self, db):
        """Test that same skill used in multiple roles shares a single record."""
        session, role_id = db
        extractor = SkillExtractorService(db=session)

        # Create a second role
        company = session.query(Company).first()
        role2 = Role(
            company_id=company.id,
            title="Senior Engineer",
            url="https://example.com/jobs/2",
            raw_html_path="data/jobs/raw/test-corp/2.html",
            cleaned_md_path="data/jobs/cleaned/test-corp/2.md",
        )
        session.add(role2)
        session.flush()

        extractor.link_skills_to_role(role_id, ["Python"], [])
        extractor.link_skills_to_role(role2.id, ["Python"], [])

        # Should only have one Skill record for Python
        python_skills = session.query(Skill).filter_by(name="Python").all()
        assert len(python_skills) == 1


class TestGetSkillsForRole:
    """Tests for retrieving skills for a role."""

    def test_get_skills_empty(self, db):
        """Test getting skills for role with no skills."""
        session, role_id = db
        extractor = SkillExtractorService(db=session)

        skills = extractor.get_skills_for_role(role_id)
        assert skills == {"required": [], "preferred": []}

    def test_get_skills_with_data(self, db):
        """Test getting skills after linking them."""
        session, role_id = db
        extractor = SkillExtractorService(db=session)

        extractor.link_skills_to_role(
            role_id=role_id,
            required_skills=["Python", "FastAPI"],
            preferred_skills=["Docker"],
        )
        session.flush()

        skills = extractor.get_skills_for_role(role_id)
        assert "Python" in skills["required"]
        assert "FastAPI" in skills["required"]
        assert "Docker" in skills["preferred"]
        assert len(skills["required"]) == 2
        assert len(skills["preferred"]) == 1
