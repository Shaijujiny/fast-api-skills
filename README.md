# fast-api-skills

Common engineering skills (Claude Code) for every FastAPI backend we build: **fintech apps, assessment portal, interview portal, transport portal**.

Stack: FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, MySQL or PostgreSQL, pytest. Backend only, no frontend.

## What is inside

```
.claude/skills/
  fastapi-blueprint/     master standard: 17 chapters (architecture, API, schemas, DB,
                         security, testing, git, review, RBAC, lessons, app profiles)
  fastapi-conventions/   new-project setup and backend coding conventions
  task-plan/             Stage 0: task implementation plan
  impact-analysis/       Stage 1: developer impact analysis
  unit-testing/          Stage 2: unit testing checklist
  pr-review/             Stage 3: pull request review with Approved Yes/No gate
  app-code-review/       deep per-file code review
```

The four stage skills form a workflow: plan, build, test, review. `fastapi-blueprint` is the standard they all point to, and its chapter 17 lists the extra rules for each application type.

## Install

Per project (shared with the team through git):

```bash
mkdir -p .claude/skills
cp -r path/to/fast-api-skills/.claude/skills/* .claude/skills/
```

For all your projects:

```bash
cp -r path/to/fast-api-skills/.claude/skills/* ~/.claude/skills/
```

Claude Code then loads the skills automatically when you work on endpoints, models, migrations, tests, PRs and reviews.

## Using it in a project

- Existing project: its own conventions win. The skills' names (`ApiResponse`, `BaseSchema`, `AppException`) are defaults.
- Record the project's application profile(s) from blueprint chapter 17 in its README or `CLAUDE.md`.

## Contributing

Keep the skills project-neutral: no company, client or ticket names, no repo-specific paths. Open a PR with a short summary of what changed and why.
