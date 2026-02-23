# MVP Phase 1: Job Capture & Storage

## Overview
**Goal**: Capture job descriptions and populate the database without losing data during active job search.

**Priority**: CRITICAL - This is the foundation that enables all other features.

## Technology Stack

### Frontend
- **Framework**: Next.js 15+ (Server Components by default)
- **Package Manager**: pnpm
- **Linting/Formatting**: Biome
- **UI Scope**: Minimal - simple form to paste URLs and view saved jobs

### Backend
- **Framework**: FastAPI
- **Package Manager**: uv
- **Linting/Formatting**: Ruff
- **Database**: SQLite (file-based, single-user)
- **ORM**: SQLAlchemy (recommended for SQLite integration)

### AI/LLM Integration
- **Provider Strategy**: Configurable multi-provider support
- **Supported Providers**: 
  - OpenAI (GPT-4/GPT-4o)
  - Anthropic Claude (Sonnet/Opus)
  - Local models via Ollama
- **User Preference**: Allow users to select preferred provider and model via config file

### Data Storage Strategy
- **Job Descriptions**: Store both raw HTML and cleaned Markdown on disk
- **Database**: Metadata, relationships, and structured data only
- **File Organization**: 
  - `/data/jobs/raw/{company_slug}/{role_id}.html` - Original scraped HTML
  - `/data/jobs/cleaned/{company_slug}/{role_id}.md` - LLM-cleaned Markdown

## Core Features

### 1. Job URL Input
- **UI**: Simple web form with single text input field
- **Input**: User pastes job posting URL
- **Validation**: Basic URL format validation
- **Supported Sites**: LinkedIn, Indeed, Greenhouse, Lever (start with these)
- **Future**: Automated job board searching (not in MVP)

### 2. Web Scraping
- **Process**:
  1. Receive URL from frontend
  2. Scrape raw HTML content
  3. Save raw HTML to `/data/jobs/raw/{company_slug}/{role_id}.html`
  4. Return scraping status to frontend
- **Error Handling**: Handle rate limits, blocked requests, invalid URLs
- **Libraries**: BeautifulSoup4, Playwright (for JavaScript-heavy sites)

### 3. LLM De-noising
- **Input**: Raw HTML from scraping step
- **Process**: LLM extracts clean, structured content
- **Output**: Markdown file with:
  - Company name
  - Role title
  - Team/division (if available)
  - Salary range (if available)
  - Job description text
  - Required skills
  - Preferred skills
- **Save**: `/data/jobs/cleaned/{company_slug}/{role_id}.md`

### 4. Skill Extraction
- **Input**: Cleaned Markdown job description
- **LLM Task**: Identify and categorize skills as "Required" or "Preferred"
- **Deduplication**: Match against existing Skills table (fuzzy matching for similar skills)
- **Output**: List of skills with requirement level

### 5. Database Population
- **Tables to Populate**:
  - **Companies**: Insert if new company
  - **Roles**: Insert new role with metadata
  - **Skills**: Insert new skills (deduplicate existing)
  - **Role_Skills**: Link role to skills with requirement level

## Database Schema (Phase 1)

### Companies Table
```sql
CREATE TABLE companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    website TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Roles Table
```sql
CREATE TABLE roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    team_division TEXT,
    salary_min INTEGER,
    salary_max INTEGER,
    salary_currency TEXT DEFAULT 'USD',
    url TEXT NOT NULL UNIQUE,
    raw_html_path TEXT NOT NULL,
    cleaned_md_path TEXT NOT NULL,
    status TEXT DEFAULT 'active', -- active, applied, rejected, archived
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);
```

### Skills Table
```sql
CREATE TABLE skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    category TEXT, -- technical, soft, domain, tool, language
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Role_Skills Table
```sql
CREATE TABLE role_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    requirement_level TEXT NOT NULL, -- required, preferred
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id),
    FOREIGN KEY (skill_id) REFERENCES skills(id),
    UNIQUE(role_id, skill_id)
);
```

## API Endpoints

### POST /api/jobs/scrape
**Request**:
```json
{
  "url": "https://www.linkedin.com/jobs/view/123456"
}
```

**Response**:
```json
{
  "status": "success",
  "role_id": 42,
  "company": "Acme Corp",
  "title": "Senior Software Engineer",
  "skills_extracted": 15,
  "processing_time_seconds": 12.5
}
```

### GET /api/jobs
**Response**:
```json
{
  "jobs": [
    {
      "id": 42,
      "company": "Acme Corp",
      "title": "Senior Software Engineer",
      "salary_range": "$150k - $200k",
      "created_at": "2026-02-22T23:00:00Z",
      "skills_count": 15,
      "status": "active"
    }
  ]
}
```

### GET /api/jobs/{id}
**Response**:
```json
{
  "id": 42,
  "company": {
    "id": 5,
    "name": "Acme Corp",
    "website": "https://acme.com"
  },
  "title": "Senior Software Engineer",
  "team_division": "Platform Engineering",
  "salary": {
    "min": 150000,
    "max": 200000,
    "currency": "USD"
  },
  "url": "https://www.linkedin.com/jobs/view/123456",
  "skills": {
    "required": ["Python", "FastAPI", "PostgreSQL", "Docker"],
    "preferred": ["Kubernetes", "AWS", "React"]
  },
  "description_md": "# Senior Software Engineer\n\n...",
  "created_at": "2026-02-22T23:00:00Z",
  "status": "active"
}
```

## Frontend Pages

### 1. Home/Dashboard (`/`)
- **Components**:
  - URL input form (prominent, center of page)
  - Recent jobs list (last 10 jobs added)
  - Simple stats (total jobs, total companies)

### 2. Job List (`/jobs`)
- **Components**:
  - Table/list of all saved jobs
  - Columns: Company, Title, Salary, Date Added, Status
  - Click row to view details

### 3. Job Detail (`/jobs/[id]`)
- **Components**:
  - Full job description (rendered Markdown)
  - Skills list (required vs. preferred)
  - Company info
  - Link to original posting
  - Status dropdown (active, applied, rejected, archived)

## Success Criteria

1. **Speed**: User can paste URL and see job saved within 30 seconds
2. **Accuracy**: Skills extracted with 90%+ accuracy (manual review of first 20 jobs)
3. **Persistence**: All data persists in SQLite + file system
4. **Reliability**: Handles common scraping errors gracefully
5. **Usability**: Non-technical user can add jobs without confusion

## Out of Scope (Future Phases)

- Company scoring/desirability calculation
- Skill gap analysis
- Go/No-Go recommendations
- Application materials generation
- Career path exploration
- Personal project recommendations
- User onboarding/resume import
- Advanced filtering/search
- Role comparison tools

## Configuration

### LLM Provider Config (`config/llm.json`)
```json
{
  "provider": "openai",
  "model": "gpt-4o",
  "api_key_env": "OPENAI_API_KEY",
  "temperature": 0.1,
  "max_tokens": 4000
}
```

### Scraping Config (`config/scraping.json`)
```json
{
  "timeout_seconds": 30,
  "retry_attempts": 3,
  "user_agent": "Mozilla/5.0 (compatible; PlotYourPath/1.0)",
  "rate_limit_delay_seconds": 2
}
```

## Development Workflow

1. **Branch**: Create `feature/mvp-phase1-job-capture`
2. **Backend First**:
   - Set up FastAPI project structure
   - Create SQLite database and models
   - Implement scraping endpoint
   - Implement LLM de-noising
   - Implement skill extraction
   - Write tests (90% coverage)
3. **Frontend**:
   - Set up Next.js project structure
   - Create URL input form
   - Create job list view
   - Create job detail view
   - Connect to backend API
4. **Integration Testing**:
   - Test with real job URLs from multiple sites
   - Verify data persistence
   - Check skill extraction accuracy
5. **Commit**: Use Conventional Commits
6. **Version**: Bump to 0.1.0 (first working MVP)

## Testing Strategy

### Backend Tests
- Unit tests for scraping logic
- Unit tests for LLM prompt/response parsing
- Unit tests for skill deduplication
- Integration tests for full scrape → store pipeline
- Database migration tests

### Frontend Tests
- Component tests for form validation
- Integration tests for API calls
- E2E test: paste URL → see job in list

### Manual Testing Checklist
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
