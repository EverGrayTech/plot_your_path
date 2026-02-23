# System Specification: Plot Your Path

## 1. Core Vision
- **Mission**: To holistically understand one's career history and goals, so that you're confident in each step of their journey.
- **User Stories**: 
  - As a job seeker, I want evaluate my fit for a role so that my search is both short and fruitful.
  - As a job applier, I want to present myself in the best possible manner to raise my chances.
  - As a ladder climber, I want to evaluate directions I could take my career so that I understand the pros, cons, and steps to get there.
  - As a life-long learner, I want to define interesting personal projects so that I grow and benefit from the fruits of my efforts.

## 2. Standards & Protocols
> **Rule of Truth**: This project follows the modular standards defined in the `.agent/.clinerules/` directory.
- **Workflow**: Follow the Spec-Driven Development (SDD) protocol in `.agent/.clinerules/00-global.md`.
- **Linting/Formatting**: See `.agent/.clinerules/10-frontend.md` and `20-backend.md`.
- **Quality**: See `.agent/.clinerules/30-testing.md`

## 3. Technology Stack

### Frontend
- **Framework**: Next.js 15+ (Server Components by default)
- **Package Manager**: pnpm
- **Linting/Formatting**: Biome

### Backend
- **Framework**: FastAPI
- **Package Manager**: uv
- **Linting/Formatting**: Ruff
- **Database**: SQLite (file-based, single-user)
- **Vector Store**: ChromaDB (for STAR stories and application history)
- **ORM**: SQLAlchemy

### AI/LLM Integration
- **Provider Strategy**: Configurable multi-provider support
- **Supported Providers**: OpenAI (GPT-4/GPT-4o), Anthropic Claude (Sonnet/Opus), Local models via Ollama

### Data Storage Strategy
- **Job Descriptions**: Store both raw HTML and cleaned Markdown on disk
- **Database**: Metadata, relationships, and structured data only
- **File Organization**: 
  - `/data/jobs/raw/{company_slug}/{role_id}.html` - Original scraped HTML
  - `/data/jobs/cleaned/{company_slug}/{role_id}.md` - LLM-cleaned Markdown
  - `/data/resumes/` - User's uploaded resume/LinkedIn exports
  - `/data/applications/{role_id}/` - Generated application materials

### Caching Strategy
- **Stable Data** (90+ day cache): Patents, R&D history, company founding info, historical D&I reports
- **Volatile Data** (7-day cache): Stock prices, Glassdoor ratings, recent news
- **User-Controlled**: Manual refresh option for any cached data
- **Rate Limiting**: Implement exponential backoff for external API calls

## 4. Architectural Overview

### Data Flow
- **Ingestion & Refinement**: The flow begins with a raw URL. The `Job Search Agent` scrapes the content, but crucially uses an LLM to "de-noise" the HTML, producing a clean, standardized Markdown version of the Job Description (JD) for the local archive.
- **Structured Mapping**: The cleaned JD is passed through an extraction prompt that populates the `Roles` and `Role_Skills` tables. This transforms unstructured text into a queryable relational format, linking the role to the broader `Skills` dictionary.
- **Dynamic Enrichment (The Scoring Engine)**: If the company is new, the agent triggers the `Scoring Engine`. It retrieves the data_source_query instructions from the `Scoring_Config` table for the Desirability Factors. It then performs external research to assign 1-10 scores, which are then weighted by your personal preferences to produce an overall_desirability score.
- **Actionable Synthesis**: Finally, the system intersects the `Role_Skills` with your Learnings table. This calculates a "Skill Match" percentage and identifies "Gaps," providing a "Go/No-Go" recommendation.

### The Role of AI Agents

In this architecture, the AI Agents act as Middleware and Reasoning Engines rather than simple scripts:

- **The Job Search Agent**: Acts as the primary orchestrator of the data flow, responsible for scraping, SQL insertion logic, and external research/scoring.
- **The Long-Term Context Agent**: Acts as the "Executive Assistant." It holds the vector memory (ChromaDB) of your STAR stories and past applications. When a role is flagged as a "GO," this agent synthesizes the company's "desirability" context with your personal "Learnings" to generate highly tailored application materials.
- **The Scoring Analyst (Sub-Agent)**: Specializes in interpreting messy, qualitative web data (like Glassdoor reviews or D&I reports) and quantifying them into the 1-10 integers required for the SQL core.

By separating the Instructions (stored in SQL) from the Execution (the Agents), the system remains "future-proof"—you can change how a factor is calculated simply by updating a row in the database without rewriting a single line of code.

## 5. Database Schema Overview

### Core Tables
- **Companies**: Master list of potential employers with desirability scores
- **Roles**: Specific job openings linked to companies
- **Skills**: Global dictionary of technical and soft skills
- **Role_Skills**: Junction table linking roles to required/preferred skills

### Scoring Architecture
- **Scoring_Config**: Stores user weights and AI instructions for 8 desirability factors:
  1. Culture (Glassdoor ratings)
  2. Notoriety (Market cap/influence)
  3. Progressiveness (D&I reports, parental leave)
  4. Inventiveness (Patents, R&D, innovation)
  5. Social Impact (UN SDG alignment)
  6. Wow-Factor (Cutting-edge tech, "coolness")
  7. Reputation (Ethics, trust scores)
  8. Comp/Growth (Salary, career development)

### Personal Progress
- **Learnings**: Personal skill tracker with status, ease/demand/passion scores, and dependencies
- **Star_Stories**: STAR format experiences stored in ChromaDB for application materials

### Key Relationships
- **Company → Roles**: One-to-many
- **Role ↔ Skills**: Many-to-many (via Role_Skills)
- **Skills → Learnings**: Links market demand to personal supply

> **Detailed schemas**: See `.agent/specs/01-job_capture.md` and `.agent/specs/future_phases_roadmap.md`

## 6. Development Phases

### Phase 1: MVP - Job Capture & Storage (PRIORITY)
**Goal**: Capture job descriptions without losing data during active job search

**Core Features**:
- URL-based job input (LinkedIn, Indeed, Greenhouse, Lever)
- Web scraping with LLM de-noising
- Skill extraction (required vs. preferred)
- SQLite database population
- Simple web UI for input and viewing

> **Full specification**: See `.agent/specs/01-job_capture.md`

### Phase 2: Company Scoring Engine
- Automated research and scoring of 8 desirability factors
- Smart caching (stable vs. volatile data)
- User-configurable weights and instructions

### Phase 3: Skill Gap Analysis & Recommendations
- Resume/LinkedIn import and AI extraction
- Skill match calculation
- AI-powered Go/No-Go recommendations

### Phase 4: Application Materials Generation
- ChromaDB integration for STAR stories
- Generate resumes, cover letters, interview prep, follow-ups
- Version history and regeneration

### Phase 5: Career Path Exploration
- Proactive career path suggestions
- "What-if" exploration tool
- Skill roadmaps and salary progression

### Phase 6: Personal Project Recommendations
- AI-suggested projects based on skill gaps
- Project templates library
- Progress tracking and portfolio integration

> **Detailed roadmap**: See `.agent/specs/future_phases_roadmap.md`

## 7. User Experience Principles
- **Single User Focus**: One profile per installation (no multi-user complexity)
- **Privacy First**: All data stored locally (SQLite + file system)
- **Iterative Enhancement**: Start simple, add sophistication in phases
- **AI Transparency**: Show reasoning behind recommendations
- **User Control**: Allow customization of AI instructions and weights
- **Data Ownership**: Easy export of all data in standard formats
