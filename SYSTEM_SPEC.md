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

## 3. Architechural Overview

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

## 4. Database
### Company & Scoring Architecture
- **Companies**: The master list of potential employers. It stores raw 1-10 scores for the desirability factorsand a calculated overall_desirability score.
- **Scoring_Config**: The "Brain" of the scoring engine. It stores the User Weights (how much you care about each factor) and the Agent Instructions (how the AI should find and rate that specific data point).
  1. **Culture**: Fetch Glassdoor "Culture & Values" rating (1-5) and scale it to 1-10.
  2. **Notoriety**: Use company Market Cap (Trillion/Billion/Million) to determine 1-10 influence score.
  3. **Progressiveness**: Analyze public Diversity & Inclusion reports and parental leave policy length for a 1-10 score.
  4. **Inventiveness**: Analyze Patent/R&D spend/recent product breakthroughs for a 1-10 score.
  5. **Social Impact**: Determine the company's mission alignment with the UN SDGs or social good, score 1-10.
  6. **Wow-Factor**: Rate based on the use of cutting-edge technology (e.g., Generative AI, Quantum) and public perception of "coolness", score 1-10.
  7. **Reputation**: Calculate average RepTrak/TrustPilot score and overall Glassdoor rating (excluding salary) for a 1-10 ethical score.
  8. **Comp/Growth**: Rate based on median salary and clarity/budget for internal career development/training, score 1-10.

### Role & Skill Mapping
- **Roles**: Specific job openings. Each role is linked to a Company and includes the team/division, salary range, and a file path to the original job description text stored on disk.
- **Skills**: A global dictionary of all technical and soft skills encountered across all job descriptions.
- **Role_Skills**: The junction table that connects Roles to Skills. It tracks whether a specific skill is "Required" or "Preferred" for that particular job.

### Personal Progress & Roadmap
- **Learnings**: Your personal skill tracker. It links to the Skills table and tracks your status (e.g., "To Do" vs. "Mastered").
- **Prioritization**: It uses internal scores (Ease, Demand, Passion) to help the agent decide which skills you should learn next to unlock the most "High Desirability" roles.
- **Dependencies**: Tracks if one skill (e.g., Kubernetes) requires another (e.g., Docker) to be learned first.

### Key Relationships
- **Company → Roles**: One company can have many different job roles.
- **Role ↔ Skills**: A many-to-many relationship. One role requires many skills, and one skill can appear in many different roles.
- **Skills → Learnings**: Connects the market demand (what the jobs want) to your personal supply (what you know).
