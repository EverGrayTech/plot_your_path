# System Specification: Plot Your Path

## 1. Core Vision
- **Vision**: A 1-sentence "North Star" for the project.
- **Problem**: What specific pain point is this solving?
- **Core User**: Who is the primary persona?

## 2. Architectural Overview
- **Backend**: FastAPI (Python 3.12+)
- **Frontend**: Next.js 15+
- **Database**: [Name of DB]
- **State Management**: [e.g., Stateless JWT, Server Actions, or Zustand].
- **Key Integrations**: [e.g., Stripe, OpenAI, Clerk]

## 3. Standards & Protocols
> **Rule of Truth**: This project follows the modular standards defined in the `.agent/.clinerules/` directory.
- **Workflow**: Follow the Spec-Driven Development (SDD) protocol in `.agent/.clinerules/00-global.md`.
- **Linting/Formatting**: See `.agent/.clinerules/10-frontend.md` and `20-backend.md`.
- **Quality**: See `.agent/.clinerules/30-testing.md`

## 4. Unique Project Constraints
- [List only things NOT in global rules, e.g., "Must remain compatible with IE11"]
- [e.g., "All primary keys must be UUIDv7"]

## 5. Global Data Model
- **Core Entities**: [Briefly list User, Project, etc.]
- **Relationships**: [e.g., 1-to-many User to Projects]
- **Security**: Data must be isolated by `user_id` at the database level.
