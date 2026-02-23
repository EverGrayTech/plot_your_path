# Future Phases Roadmap

This document outlines the features and capabilities to be built after MVP Phase 1 (Job Capture & Storage) is complete.

## Phase 2: Company Scoring Engine

### Goal
Automatically research and score companies based on 8 desirability factors, weighted by user preferences.

### New Database Tables

#### Scoring_Config Table
```sql
CREATE TABLE scoring_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    factor_name TEXT NOT NULL UNIQUE, -- culture, notoriety, progressiveness, etc.
    user_weight REAL DEFAULT 1.0, -- 0.0 to 2.0, how much user cares
    agent_instructions TEXT NOT NULL, -- LLM prompt for researching this factor
    cache_duration_days INTEGER DEFAULT 90, -- how long to cache results
    is_volatile BOOLEAN DEFAULT 0, -- if true, refresh more frequently
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Company_Scores Table
```sql
CREATE TABLE company_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    culture_score INTEGER, -- 1-10
    notoriety_score INTEGER,
    progressiveness_score INTEGER,
    inventiveness_score INTEGER,
    social_impact_score INTEGER,
    wow_factor_score INTEGER,
    reputation_score INTEGER,
    comp_growth_score INTEGER,
    overall_desirability REAL, -- weighted average
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE(company_id)
);
```

#### Research_Cache Table
```sql
CREATE TABLE research_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    factor_name TEXT NOT NULL,
    data_source TEXT, -- glassdoor, crunchbase, etc.
    raw_data TEXT, -- JSON blob of research results
    score INTEGER, -- 1-10
    reasoning TEXT, -- LLM explanation
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE(company_id, factor_name)
);
```

### Features

1. **Default Scoring Instructions**: Pre-populate Scoring_Config with 8 factors
2. **Scoring Engine Agent**: Researches company data from external sources
3. **Smart Caching**: Cache stable data (90 days), refresh volatile data (7 days)
4. **User Weight Configuration**: UI to adjust how much each factor matters
5. **Instruction Customization**: Advanced users can edit research prompts
6. **Overall Desirability**: Calculate weighted score automatically

### Data Sources
- **Glassdoor API**: Culture ratings, reviews, salary data
- **Crunchbase/PitchBook**: Market cap, funding, company size
- **Company websites**: D&I reports, sustainability reports
- **Patent databases**: USPTO, Google Patents
- **News APIs**: Recent company news, product launches
- **Social media**: Public perception, "coolness" factor

### UI Components
- Company detail page with score breakdown
- Score configuration page (weights + instructions)
- Manual refresh button for cached data
- Score history/trends over time

---

## Phase 3: Skill Gap Analysis & Recommendations

### Goal
Compare role requirements against user's skills to provide AI-powered Go/No-Go recommendations.

### New Database Tables

#### Learnings Table
```sql
CREATE TABLE learnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id INTEGER NOT NULL,
    status TEXT DEFAULT 'to_do', -- to_do, learning, proficient, mastered
    ease_score REAL, -- 1-10, how easy for user to learn
    demand_score REAL, -- 1-10, market demand
    passion_score REAL, -- 1-10, user interest
    priority_score REAL, -- calculated from ease/demand/passion
    learning_time_hours INTEGER, -- estimated time to proficiency
    dependency_skill_id INTEGER, -- prerequisite skill
    notes TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (skill_id) REFERENCES skills(id),
    FOREIGN KEY (dependency_skill_id) REFERENCES skills(id),
    UNIQUE(skill_id)
);
```

#### Role_Recommendations Table
```sql
CREATE TABLE role_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id INTEGER NOT NULL,
    recommendation TEXT NOT NULL, -- go, maybe, no_go
    confidence REAL, -- 0.0 to 1.0
    skill_match_percentage REAL,
    required_skills_met INTEGER,
    required_skills_total INTEGER,
    preferred_skills_met INTEGER,
    preferred_skills_total INTEGER,
    learning_time_estimate_hours INTEGER,
    reasoning TEXT, -- LLM explanation
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id),
    UNIQUE(role_id)
);
```

#### Skill_Gaps Table
```sql
CREATE TABLE skill_gaps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    requirement_level TEXT, -- required, preferred
    gap_severity TEXT, -- critical, important, nice_to_have
    learning_path TEXT, -- suggested resources/steps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id),
    FOREIGN KEY (skill_id) REFERENCES skills(id),
    UNIQUE(role_id, skill_id)
);
```

### Features

1. **Onboarding Flow**: Upload resume/LinkedIn export
2. **AI Extraction**: LLM extracts skills and experiences from documents
3. **Learnings Population**: Auto-populate with extracted skills
4. **Skill Match Calculation**: Compare role requirements vs. user skills
5. **Gap Analysis**: Identify missing required/preferred skills
6. **AI Recommendation**: Holistic Go/No-Go with reasoning
7. **Learning Path**: Suggest resources to fill gaps

### Recommendation Algorithm Factors
- Skill match percentage (required vs. preferred)
- Skill gap difficulty (ease_score from Learnings)
- Learning time estimates
- Company overall_desirability score
- Salary alignment
- User's current learning capacity
- Skill dependencies (prerequisites)

### UI Components
- Onboarding wizard (upload resume)
- Skills inventory page (manage Learnings)
- Role detail page with recommendation badge
- Skill gap visualization
- Learning path suggestions

---

## Phase 4: Application Materials Generation

### Goal
Generate tailored resumes, cover letters, and interview prep materials using STAR stories.

### New Database Tables

#### Star_Stories Table
```sql
CREATE TABLE star_stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    situation TEXT NOT NULL,
    task TEXT NOT NULL,
    action TEXT NOT NULL,
    result TEXT NOT NULL,
    skills_demonstrated TEXT, -- JSON array of skill IDs
    impact_metrics TEXT, -- quantifiable results
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Application_Materials Table
```sql
CREATE TABLE application_materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id INTEGER NOT NULL,
    material_type TEXT NOT NULL, -- resume, cover_letter, linkedin_message, interview_prep, follow_up
    content TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    tone TEXT, -- professional, enthusiastic, technical
    star_stories_used TEXT, -- JSON array of story IDs
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);
```

### Features

1. **ChromaDB Integration**: Store STAR stories as vectors
2. **Story Extraction**: Extract from resume during onboarding
3. **Manual Story Entry**: UI to add/edit STAR stories
4. **Relevant Story Retrieval**: Vector search for best-fit stories
5. **Material Generation**:
   - Tailored resume (highlight relevant skills/experiences)
   - Custom cover letter (company desirability + skill alignment)
   - LinkedIn outreach templates
   - Interview prep notes (anticipated questions + STAR suggestions)
   - Follow-up email templates
6. **Regeneration**: Different tones/emphasis on demand
7. **Version History**: Track iterations of materials

### LLM Prompts
- Resume tailoring: Emphasize relevant skills, reorder experiences
- Cover letter: Weave in company desirability factors + skill match
- Interview prep: Predict questions based on JD, suggest STAR stories
- Follow-up: Reference interview topics, reiterate fit

### UI Components
- STAR stories library (CRUD interface)
- Material generation page (select type, tone, generate)
- Material editor (review, edit, regenerate)
- Version history viewer
- Export to PDF/DOCX

---

## Phase 5: Career Path Exploration

### Goal
Suggest career paths and enable "what-if" exploration of different directions.

### New Database Tables

#### Career_Paths Table
```sql
CREATE TABLE career_paths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_role_title TEXT NOT NULL,
    to_role_title TEXT NOT NULL,
    typical_years INTEGER, -- time to transition
    difficulty TEXT, -- easy, moderate, hard
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Path_Suggestions Table
```sql
CREATE TABLE path_suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    suggested_role_title TEXT NOT NULL,
    current_skill_match REAL, -- 0.0 to 1.0
    skills_to_learn TEXT, -- JSON array of skill IDs
    learning_time_estimate_hours INTEGER,
    typical_companies TEXT, -- JSON array of company types
    salary_range_min INTEGER,
    salary_range_max INTEGER,
    desirability_estimate REAL, -- based on user's weights
    pros TEXT, -- JSON array
    cons TEXT, -- JSON array
    reasoning TEXT, -- LLM explanation
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Features

1. **Proactive Suggestions**: Analyze current skills, suggest next roles
2. **What-If Tool**: User enters target role, see gap analysis
3. **Path Visualization**: Show progression from current → target
4. **Skill Roadmap**: Ordered list of skills to learn
5. **Company Matching**: Find companies hiring for target role
6. **Salary Progression**: Estimate earning potential
7. **Pros/Cons Analysis**: Based on user's desirability preferences

### UI Components
- Career path dashboard (suggested paths)
- Path explorer (search/filter roles)
- Path detail view (skills, timeline, companies)
- Skill roadmap visualization
- Comparison tool (compare multiple paths side-by-side)

---

## Phase 6: Personal Project Recommendations

### Goal
Suggest and track personal projects that develop skills for target roles.

### New Database Tables

#### Projects Table
```sql
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    source TEXT, -- ai_suggested, user_defined, template
    template_id INTEGER, -- if from template
    skills_developed TEXT, -- JSON array of skill IDs
    difficulty TEXT, -- beginner, intermediate, advanced
    estimated_hours INTEGER,
    status TEXT DEFAULT 'planned', -- planned, in_progress, completed, abandoned
    progress_percentage INTEGER DEFAULT 0,
    github_url TEXT,
    demo_url TEXT,
    notes TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (template_id) REFERENCES project_templates(id)
);
```

#### Project_Templates Table
```sql
CREATE TABLE project_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT, -- web_dev, data_science, devops, mobile, etc.
    skills_developed TEXT, -- JSON array of skill IDs
    difficulty TEXT,
    estimated_hours INTEGER,
    instructions TEXT, -- step-by-step guide
    resources TEXT, -- JSON array of helpful links
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Project_Milestones Table
```sql
CREATE TABLE project_milestones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending', -- pending, completed
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
```

### Features

1. **AI Project Suggestions**: Based on skill gaps for target roles
2. **Template Library**: Pre-built project ideas with instructions
3. **Custom Projects**: User-defined projects
4. **Skill Mapping**: Link projects to skills they develop
5. **Progress Tracking**: Milestones, percentage complete
6. **Portfolio Integration**: GitHub/demo links
7. **Learning Update**: Mark skills as learned upon completion

### Project Suggestion Algorithm
- Identify skill gaps from target roles
- Find projects that teach multiple gap skills
- Prioritize by: user passion, skill demand, project difficulty
- Suggest projects with clear learning outcomes

### UI Components
- Project dashboard (active, planned, completed)
- Project suggestion page (AI recommendations)
- Template browser (filter by skill, difficulty)
- Project detail/editor (milestones, progress)
- Portfolio view (showcase completed projects)

---

## Implementation Priority

Based on user feedback, the recommended order is:

1. **Phase 1: Job Capture** (CRITICAL - in progress)
2. **Phase 3: Skill Gap Analysis** (High value for job search)
3. **Phase 2: Company Scoring** (Helps prioritize applications)
4. **Phase 4: Application Materials** (Streamlines application process)
5. **Phase 5: Career Path Exploration** (Long-term planning)
6. **Phase 6: Personal Projects** (Skill development)

Each phase should be:
- Fully tested (90% coverage)
- Documented in `.agent/specs/`
- Planned in `.agent/plans/`
- Committed with Conventional Commits
- Version bumped per SemVer

---

## Cross-Phase Considerations

### Authentication & Security
- Single-user app, no auth needed initially
- API keys stored in environment variables
- Sensitive data (STAR stories) stays local

### Data Export
- Export all data to JSON/CSV
- Backup/restore functionality
- Data portability (move between machines)

### Performance
- Lazy loading for large job lists
- Pagination for API endpoints
- Background jobs for LLM processing
- Cache LLM responses aggressively

### Error Handling
- Graceful degradation when LLM unavailable
- Retry logic for external APIs
- User-friendly error messages
- Logging for debugging

### Extensibility
- Plugin system for new data sources
- Custom scoring factors
- Custom project templates
- API for third-party integrations
