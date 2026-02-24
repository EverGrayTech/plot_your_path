# Plan: Phase 1 - Job Capture & Storage Implementation

## 1. Technical Architecture

### Impacted Files
**Backend (New)**:
- `src/backend/main.py` - FastAPI application entry point
- `src/backend/config.py` - Configuration management
- `src/backend/database.py` - SQLAlchemy setup and session management
- `src/backend/models/` - SQLAlchemy ORM models
  - `src/backend/models/company.py`
  - `src/backend/models/role.py`
  - `src/backend/models/skill.py`
  - `src/backend/models/role_skill.py`
- `src/backend/schemas/` - Pydantic models for API validation
  - `src/backend/schemas/job.py`
  - `src/backend/schemas/company.py`
  - `src/backend/schemas/skill.py`
- `src/backend/services/` - Business logic
  - `src/backend/services/scraper.py` - Web scraping logic
  - `src/backend/services/llm_service.py` - LLM integration
  - `src/backend/services/skill_extractor.py` - Skill extraction and deduplication
- `src/backend/routers/` - API endpoints
  - `src/backend/routers/jobs.py`
- `src/backend/utils/` - Utility functions
  - `src/backend/utils/slug.py` - Company name to slug conversion
  - `src/backend/utils/file_storage.py` - File system operations
- `tests/backend/` - Backend tests
  - `tests/backend/test_scraper.py`
  - `tests/backend/test_llm_service.py`
  - `tests/backend/test_skill_extractor.py`
  - `tests/backend/test_jobs_api.py`

**Frontend (New)**:
- `src/frontend/app/layout.tsx` - Root layout
- `src/frontend/app/page.tsx` - Home/Dashboard page
- `src/frontend/app/jobs/page.tsx` - Job list page
- `src/frontend/app/jobs/[id]/page.tsx` - Job detail page
- `src/frontend/components/` - React components
  - `src/frontend/components/JobUrlForm.tsx` - URL input form
  - `src/frontend/components/JobList.tsx` - Job list display
  - `src/frontend/components/JobCard.tsx` - Individual job card
  - `src/frontend/components/SkillBadge.tsx` - Skill display badge
- `src/frontend/lib/` - Frontend utilities
  - `src/frontend/lib/api.ts` - API client functions
- `tests/frontend/` - Frontend tests
  - `tests/frontend/components/JobUrlForm.test.tsx`
  - `tests/frontend/components/JobList.test.tsx`

**Configuration Files (New)**:
- `config/llm.json` - LLM provider configuration
- `config/scraping.json` - Scraping configuration
- `.env.example` - Environment variables template
- `pyproject.toml` - Python dependencies (uv)
- `package.json` - Frontend dependencies (pnpm)
- `biome.json` - Biome configuration
- `ruff.toml` - Ruff configuration

**Data Directories (New)**:
- `data/jobs/raw/` - Raw HTML storage
- `data/jobs/cleaned/` - Cleaned Markdown storage
- `data/plot_your_path.db` - SQLite database

### New Dependencies

**Backend (Python - uv)**:
- `fastapi` - Web framework
- `uvicorn[standard]` - ASGI server
- `sqlalchemy` - ORM
- `pydantic` - Data validation
- `pydantic-settings` - Settings management
- `beautifulsoup4` - HTML parsing
- `playwright` - Browser automation for JS-heavy sites
- `httpx` - HTTP client
- `openai` - OpenAI API client
- `anthropic` - Anthropic API client
- `python-slugify` - Slug generation
- `pytest` - Testing framework
- `pytest-cov` - Coverage reporting
- `pytest-asyncio` - Async test support
- `ruff` - Linting and formatting

**Frontend (TypeScript - pnpm)**:
- `next@15` - React framework
- `react` - UI library
- `react-dom` - React DOM
- `typescript` - Type safety
- `@biomejs/biome` - Linting and formatting
- `vitest` - Testing framework
- `@testing-library/react` - React testing utilities
- `@testing-library/jest-dom` - DOM matchers
- `@vitejs/plugin-react` - Vite React plugin

### Data Models

**Pydantic Schemas (Backend API)**:
```python
# schemas/company.py
from pydantic import BaseModel, HttpUrl
from datetime import datetime

class CompanyBase(BaseModel):
    name: str
    website: HttpUrl | None = None

class CompanyCreate(CompanyBase):
    pass

class Company(CompanyBase):
    id: int
    slug: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# schemas/skill.py
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class SkillCategory(str, Enum):
    TECHNICAL = "technical"
    SOFT = "soft"
    DOMAIN = "domain"
    TOOL = "tool"
    LANGUAGE = "language"

class SkillBase(BaseModel):
    name: str
    category: SkillCategory | None = None

class SkillCreate(SkillBase):
    pass

class Skill(SkillBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# schemas/job.py
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from enum import Enum

class RoleStatus(str, Enum):
    ACTIVE = "active"
    APPLIED = "applied"
    REJECTED = "rejected"
    ARCHIVED = "archived"

class RequirementLevel(str, Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"

class JobScrapeRequest(BaseModel):
    url: HttpUrl

class JobScrapeResponse(BaseModel):
    status: str
    role_id: int
    company: str
    title: str
    skills_extracted: int
    processing_time_seconds: float

class RoleSkillInfo(BaseModel):
    id: int
    name: str
    category: str | None
    requirement_level: RequirementLevel

class SalaryInfo(BaseModel):
    min: int | None
    max: int | None
    currency: str

class JobListItem(BaseModel):
    id: int
    company: str
    title: str
    salary_range: str | None
    created_at: datetime
    skills_count: int
    status: RoleStatus

class JobDetail(BaseModel):
    id: int
    company: Company
    title: str
    team_division: str | None
    salary: SalaryInfo
    url: str
    skills: dict[str, list[str]]  # {"required": [...], "preferred": [...]}
    description_md: str
    created_at: datetime
    status: RoleStatus
```

**SQLAlchemy Models (Database)**:
```python
# models/company.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    slug = Column(String, nullable=False, unique=True)
    website = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

# models/role.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base

class Role(Base):
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    title = Column(String, nullable=False)
    team_division = Column(String, nullable=True)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    salary_currency = Column(String, default="USD")
    url = Column(String, nullable=False, unique=True)
    raw_html_path = Column(String, nullable=False)
    cleaned_md_path = Column(String, nullable=False)
    status = Column(String, default="active")
    created_at = Column(DateTime, server_default=func.now())

# models/skill.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base

class Skill(Base):
    __tablename__ = "skills"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    category = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

# models/role_skill.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from database import Base

class RoleSkill(Base):
    __tablename__ = "role_skills"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False)
    requirement_level = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (UniqueConstraint('role_id', 'skill_id', name='_role_skill_uc'),)
```

**TypeScript Types (Frontend)**:
```typescript
// lib/types.ts
export type RoleStatus = "active" | "applied" | "rejected" | "archived";
export type RequirementLevel = "required" | "preferred";

export interface Company {
  id: number;
  name: string;
  website?: string;
}

export interface Skill {
  id: number;
  name: string;
  category?: string;
  requirement_level: RequirementLevel;
}

export interface JobListItem {
  id: number;
  company: string;
  title: string;
  salary_range?: string;
  created_at: string;
  skills_count: number;
  status: RoleStatus;
}

export interface JobDetail {
  id: number;
  company: Company;
  title: string;
  team_division?: string;
  salary: {
    min?: number;
    max?: number;
    currency: string;
  };
  url: string;
  skills: {
    required: string[];
    preferred: string[];
  };
  description_md: string;
  created_at: string;
  status: RoleStatus;
}

export interface JobScrapeRequest {
  url: string;
}

export interface JobScrapeResponse {
  status: string;
  role_id: number;
  company: string;
  title: string;
  skills_extracted: number;
  processing_time_seconds: number;
}
```

## 2. Implementation Steps (The Task List)

### Phase 1: Project Setup & Infrastructure
- [x] Run `cruft update` to sync with template (skipped - not installed)
- [x] Create feature branch `feature/mvp-phase1-job-capture`
- [x] Initialize backend project structure with uv
  - [x] Create `pyproject.toml` with dependencies
  - [x] Set up `ruff.toml` configuration (in pyproject.toml)
  - [x] Create `src/backend/` directory structure
- [x] Initialize frontend project structure with pnpm
  - [x] Create Next.js 15 app with TypeScript
  - [x] Set up `biome.json` configuration
  - [x] Create `src/frontend/` directory structure
- [x] Create configuration files
  - [x] `config/llm.json`
  - [x] `config/scraping.json`
  - [x] `.env.example`
- [x] Create data directories
  - [x] `data/jobs/raw/`
  - [x] `data/jobs/cleaned/`
- [x] Commit: `chore: initialize Phase 1 project structure`

### Phase 2: Backend - Database Layer
- [x] Create SQLAlchemy database setup
  - [x] `src/backend/database.py` - Database engine and session
  - [x] `src/backend/models/__init__.py`
- [x] Create ORM models
  - [x] `src/backend/models/company.py`
  - [x] `src/backend/models/role.py`
  - [x] `src/backend/models/skill.py`
  - [x] `src/backend/models/role_skill.py`
- [x] Create database initialization script
  - [x] `src/backend/init_db.py` - Creates tables
- [x] Test database creation
  - [x] Run init script and verify SQLite file created
  - [x] Verify all tables exist with correct schema
- [x] Commit: `feat(backend): add database models and initialization`

### Phase 3: Backend - Pydantic Schemas
- [x] Create Pydantic schemas
  - [x] `src/backend/schemas/__init__.py`
  - [x] `src/backend/schemas/company.py`
  - [x] `src/backend/schemas/skill.py`
  - [x] `src/backend/schemas/job.py`
- [x] Write unit tests for schema validation
  - [x] `tests/backend/test_schemas.py`
- [x] Run tests: `uv run pytest tests/backend/test_schemas.py --cov`
- [x] Commit: `feat(backend): add Pydantic schemas for API validation`

### Phase 4: Backend - Utility Functions
- [x] Create utility modules
  - [x] `src/backend/utils/__init__.py`
  - [x] `src/backend/utils/slug.py` - Company name to slug conversion
  - [x] `src/backend/utils/file_storage.py` - File save/load operations
- [x] Write unit tests for utilities
  - [x] `tests/backend/test_utils.py`
- [x] Run tests: `uv run pytest tests/backend/test_utils.py --cov`
- [x] Commit: `feat(backend): add utility functions for slug and file storage`

### Phase 5: Backend - Configuration Management
- [x] Create configuration module
  - [x] `src/backend/config.py` - Load LLM and scraping configs
- [x] Implement environment variable loading
  - [x] Support for `.env` file
  - [x] Validation of required API keys
- [x] Write unit tests for config loading
  - [x] `tests/backend/test_config.py`
- [x] Run tests: `uv run pytest tests/backend/test_config.py --cov`
- [x] Commit: `feat(backend): add configuration management`

### Phase 6: Backend - Web Scraping Service
- [x] Create scraper service
  - [x] `src/backend/services/__init__.py`
  - [x] `src/backend/services/scraper.py`
- [x] Implement scraping logic
  - [x] URL validation
  - [x] BeautifulSoup-based scraping for static sites
  - [x] Playwright integration for JavaScript-heavy sites
  - [x] Site-specific extractors (LinkedIn, Indeed, Greenhouse, Lever)
  - [x] Error handling and retry logic
  - [x] Rate limiting
- [x] Write unit tests for scraper
  - [x] `tests/backend/test_scraper.py`
  - [x] Mock HTTP responses for testing
- [x] Run tests: `uv run pytest tests/backend/test_scraper.py --cov`
- [x] Commit: `feat(backend): add web scraping service`

### Phase 7: Backend - LLM Service
- [x] Create LLM service
  - [x] `src/backend/services/llm_service.py`
- [x] Implement multi-provider support
  - [x] OpenAI integration
  - [x] Anthropic integration
  - [x] Ollama integration (local models)
  - [x] Provider selection based on config
- [x] Create LLM prompts
  - [x] De-noising prompt (HTML → Markdown)
  - [x] Skill extraction prompt
- [x] Implement response parsing
  - [x] Extract structured data from LLM responses
- [x] Write unit tests for LLM service
  - [x] `tests/backend/test_llm_service.py`
  - [x] Mock LLM API responses
- [x] Run tests: `uv run pytest tests/backend/test_llm_service.py --cov`
- [x] Commit: `feat(backend): add LLM service with multi-provider support`

### Phase 8: Backend - Skill Extraction Service
- [x] Create skill extractor service
  - [x] `src/backend/services/skill_extractor.py`
- [x] Implement skill extraction logic
  - [x] Parse LLM response for skills
  - [x] Categorize skills (required vs. preferred)
  - [x] Fuzzy matching for skill deduplication
  - [x] Database lookup and insertion
- [x] Write unit tests for skill extractor
  - [x] `tests/backend/test_skill_extractor.py`
- [x] Run tests: `uv run pytest tests/backend/test_skill_extractor.py --cov`
- [x] Commit: `feat(backend): add skill extraction and deduplication service`

### Phase 9: Backend - API Endpoints
- [x] Create FastAPI application
  - [x] `src/backend/main.py` - App initialization, CORS, routers
- [x] Create jobs router
  - [x] `src/backend/routers/__init__.py`
  - [x] `src/backend/routers/jobs.py`
- [x] Implement API endpoints
  - [x] `POST /api/jobs/scrape` - Scrape and store job
  - [x] `GET /api/jobs` - List all jobs
  - [x] `GET /api/jobs/{id}` - Get job details
  - [x] `PATCH /api/jobs/{id}/status` - Update job status
- [x] Implement full pipeline in scrape endpoint
  - [x] Scrape HTML
  - [x] Save raw HTML
  - [x] LLM de-noising
  - [x] Save cleaned Markdown
  - [x] Extract skills
  - [x] Populate database
- [x] Write integration tests for API
  - [x] `tests/backend/test_jobs_api.py`
  - [x] Test full scrape pipeline
  - [x] Test error handling
- [x] Run tests: `uv run pytest tests/backend/ --cov`
- [x] Verify 90%+ coverage (91% achieved, jobs.py at 100%)
- [x] Commit: `feat(backend): add jobs API endpoints with full pipeline`

### Phase 10: Frontend - Project Setup
- [ ] Set up Next.js app structure
  - [ ] Configure `next.config.js`
  - [ ] Set up TypeScript configuration
  - [ ] Configure Biome for linting/formatting
- [ ] Create base layout
  - [ ] `src/frontend/app/layout.tsx`
  - [ ] Basic styling (minimal CSS)
- [ ] Create type definitions
  - [ ] `src/frontend/lib/types.ts`
- [ ] Commit: `feat(frontend): initialize Next.js app structure`

### Phase 11: Frontend - API Client
- [ ] Create API client module
  - [ ] `src/frontend/lib/api.ts`
- [ ] Implement API functions
  - [ ] `scrapeJob(url: string)` - POST to /api/jobs/scrape
  - [ ] `getJobs()` - GET from /api/jobs
  - [ ] `getJobById(id: number)` - GET from /api/jobs/{id}
  - [ ] `updateJobStatus(id: number, status: RoleStatus)` - PATCH
- [ ] Add error handling
- [ ] Write unit tests for API client
  - [ ] `tests/frontend/lib/api.test.ts`
  - [ ] Mock fetch responses
- [ ] Run tests: `pnpm vitest run tests/frontend/lib/ --coverage`
- [ ] Commit: `feat(frontend): add API client functions`

### Phase 12: Frontend - Components
- [ ] Create JobUrlForm component
  - [ ] `src/frontend/components/JobUrlForm.tsx`
  - [ ] URL input field
  - [ ] Submit button
  - [ ] Loading state
  - [ ] Error display
  - [ ] Success message
- [ ] Create SkillBadge component
  - [ ] `src/frontend/components/SkillBadge.tsx`
  - [ ] Display skill name
  - [ ] Visual distinction for required vs. preferred
- [ ] Create JobCard component
  - [ ] `src/frontend/components/JobCard.tsx`
  - [ ] Display job summary
  - [ ] Link to detail page
- [ ] Create JobList component
  - [ ] `src/frontend/components/JobList.tsx`
  - [ ] Render list of JobCard components
  - [ ] Empty state
- [ ] Write component tests
  - [ ] `tests/frontend/components/JobUrlForm.test.tsx`
  - [ ] `tests/frontend/components/JobList.test.tsx`
  - [ ] `tests/frontend/components/JobCard.test.tsx`
  - [ ] `tests/frontend/components/SkillBadge.test.tsx`
- [ ] Run tests: `pnpm vitest run tests/frontend/components/ --coverage`
- [ ] Commit: `feat(frontend): add reusable components`

### Phase 13: Frontend - Pages
- [ ] Create home/dashboard page
  - [ ] `src/frontend/app/page.tsx`
  - [ ] Integrate JobUrlForm
  - [ ] Display recent jobs (last 10)
  - [ ] Show simple stats
- [ ] Create job list page
  - [ ] `src/frontend/app/jobs/page.tsx`
  - [ ] Integrate JobList component
  - [ ] Fetch all jobs on load
- [ ] Create job detail page
  - [ ] `src/frontend/app/jobs/[id]/page.tsx`
  - [ ] Fetch job details
  - [ ] Render Markdown description
  - [ ] Display skills with badges
  - [ ] Status dropdown
  - [ ] Link to original posting
- [ ] Write page tests
  - [ ] `tests/frontend/app/page.test.tsx`
  - [ ] `tests/frontend/app/jobs/page.test.tsx`
- [ ] Run tests: `pnpm vitest run tests/frontend/ --coverage`
- [ ] Verify 90%+ coverage
- [ ] Commit: `feat(frontend): add pages for dashboard, job list, and job detail`

### Phase 14: Integration & End-to-End Testing
- [ ] Set up E2E testing environment
  - [ ] Install Playwright for E2E tests
  - [ ] Configure test database
- [ ] Write E2E tests
  - [ ] Test: Paste URL → Job appears in list
  - [ ] Test: Click job → View details
  - [ ] Test: Update job status
  - [ ] Test: Error handling for invalid URL
- [ ] Manual testing checklist
  - [ ] Scrape LinkedIn job posting
  - [ ] Scrape Indeed job posting
  - [ ] Scrape Greenhouse job posting
  - [ ] Scrape Lever job posting
  - [ ] Verify skills extracted correctly
  - [ ] Verify company deduplication works
  - [ ] Verify skill deduplication works
  - [ ] Test with invalid URL
  - [ ] Test with rate-limited site
  - [ ] Verify data persists after restart
- [ ] Document any issues found
- [ ] Commit: `test: add E2E tests and complete manual testing`

### Phase 15: Documentation & Polish
- [ ] Create README for Phase 1
  - [ ] Installation instructions
  - [ ] Configuration guide
  - [ ] Usage examples
  - [ ] API documentation
- [ ] Add inline code comments
  - [ ] Document complex logic
  - [ ] Add docstrings to functions
- [ ] Create sample configuration files
  - [ ] `config/llm.json.example`
  - [ ] `config/scraping.json.example`
- [ ] Update `.env.example` with all required variables
- [ ] Run final linting
  - [ ] `pnpm biome check --apply`
  - [ ] `uv run ruff check --fix`
- [ ] Commit: `docs: add Phase 1 documentation and polish`

### Phase 16: Version Bump & Release
- [ ] Update version to 0.1.0
  - [ ] Update `pyproject.toml`
  - [ ] Update `package.json`
- [ ] Create release notes
  - [ ] Document features implemented
  - [ ] Known limitations
  - [ ] Future roadmap
- [ ] Final commit: `chore: bump version to 0.1.0 for Phase 1 MVP`
- [ ] Merge feature branch to main
- [ ] Tag release: `v0.1.0`

## 3. Known Risks

### Technical Risks
1. **Web Scraping Reliability**: Job sites may block scrapers or change HTML structure
   - **Mitigation**: Implement robust error handling, use Playwright for JS-heavy sites, add retry logic
   
2. **LLM API Costs**: Frequent API calls to OpenAI/Anthropic can be expensive
   - **Mitigation**: Support local models via Ollama, implement caching for repeated extractions
   
3. **Skill Deduplication Accuracy**: Fuzzy matching may create duplicates or false matches
   - **Mitigation**: Start with exact matching, add manual review UI in future phase
   
4. **Rate Limiting**: Job sites may rate-limit requests
   - **Mitigation**: Implement exponential backoff, configurable delays between requests
   
5. **Database Migrations**: SQLite schema changes can be tricky
   - **Mitigation**: Use Alembic for migrations in future phases, for MVP just recreate DB if needed

### Process Risks
1. **Scope Creep**: Temptation to add features beyond MVP
   - **Mitigation**: Strictly follow spec, defer enhancements to future phases
   
2. **Testing Coverage**: Achieving 90% coverage may be time-consuming
   - **Mitigation**: Write tests alongside implementation, not after
   
3. **Multi-Provider LLM Support**: Supporting 3 providers adds complexity
   - **Mitigation**: Start with OpenAI only, add others incrementally

### User Experience Risks
1. **Slow Scraping**: Full pipeline may take 30+ seconds
   - **Mitigation**: Add loading indicators, consider async processing in future
   
2. **Error Messages**: Technical errors may confuse users
   - **Mitigation**: Provide user-friendly error messages, log technical details separately

## 4. Success Metrics

- [ ] All tests pass with 90%+ coverage
- [ ] Successfully scrape jobs from 4 different sites (LinkedIn, Indeed, Greenhouse, Lever)
- [ ] Average scrape-to-save time < 30 seconds
- [ ] Skill extraction accuracy > 90% (manual review of 20 jobs)
- [ ] Zero data loss (all scraped jobs persist correctly)
- [ ] Clean code passing Biome and Ruff checks

## 5. Post-Implementation Review

After completing all tasks:
- [ ] Review code quality and refactor if needed
- [ ] Verify all documentation is accurate
- [ ] Test on fresh installation
- [ ] Gather feedback for Phase 2 planning
