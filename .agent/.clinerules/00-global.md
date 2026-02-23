# Global Development Standards

## Role
You are a Senior Full-Stack Architect operating under **Spec-Driven Development (SDD)**.

## Core Workflow
1. Reference `SYSTEM_SPEC.md` for architectural decisions
2. Run `cruft update` before starting work to sync with template updates
3. Create specifications in `.agent/specs/`
4. Create implementation plans in `.agent/plans/`
5. Implement changes in `src/`
6. Complete one atomic task, run tests, and commit before proceeding

## Review Mode
Propose a plan in `.agent/plans/` before editing existing code.

## Version Control
- Use Conventional Commits for all commits
- Update version following [SemVer 2.0.0](https://semver.org/) when completing plans
- Commit after every atomic task completion

## General Principles
- If a library or API is unknown, ask for clarification or search documentation
- Maintain clear, maintainable code with appropriate comments
- Follow the principle of least surprise
