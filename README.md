# fast-api-skills

Common engineering standard (a Claude Code skill) for every FastAPI service we build: **fintech apps, assessment portal, interview portal, transport portal**.

Stack: FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, MySQL or PostgreSQL, pytest.

## What is inside

```
fastapi-blueprint/
  SKILL.md        master file: non-negotiables, workflow, task-to-chapter map
  references/     17 chapters (architecture, API, schemas, DB, security,
                  testing, git, review, RBAC, lessons, application profiles)
```

Chapter 17 lists the extra rules for each application type.

## Install

Per project (shared with the team through git):

```bash
mkdir -p .claude/skills
cp -r path/to/fast-api-skills/fastapi-blueprint .claude/skills/
```

For all your projects:

```bash
cp -r path/to/fast-api-skills/fastapi-blueprint ~/.claude/skills/
```

Claude Code then loads the skill automatically when you work on endpoints, models, migrations, tests, PRs and reviews.

## Using it in a project

- Existing project: its own conventions win. The skill's names (`ApiResponse`, `BaseSchema`, `AppException`) are defaults.
- Record the project's application profile(s) from chapter 17 in its README or `CLAUDE.md`.

## Contributing

Keep the chapters project-neutral: no company, client or ticket names, no repo-specific paths. Open a PR with a short summary of what changed and why.
