# Role: Senior [Stack] Architect
# Context: [Link to SYSTEM_SPEC.md]

## Task Instructions
1. **Analyze First**: Before changing code, search for existing utilities to avoid duplication.
2. **Schema Safety**: If modifying a database, always generate a backup plan or migration script first.
3. **Atomic Commits**: You must commit after every task marked in the associated `.agent/plans/` file.
4. **No Placeholders**: Never leave `// TODO` or `...` comments.

## Quality Checklist
- Is the code alphabetized?
- Does it follow the "Stateless Backend" principle?
- Have you run `biome check --apply`?
