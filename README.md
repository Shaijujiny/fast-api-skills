# fast-api-skills

Common engineering skills (Claude Code) for every FastAPI backend we build: **fintech apps, assessment portal, interview portal, transport portal**.

Stack: FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, MySQL or PostgreSQL, pytest. Backend only, no frontend.

## What is inside

```
.claude/
  skills/
    fastapi-blueprint/                master standard, 18 chapters (ch. 17 app profiles:
                                      fintech, assessment, interview, transport;
                                      ch. 18 error handling and responses)
    fastapi-conventions/              new-project setup and backend coding conventions
    task-plan/ impact-analysis/       workflow: plan (0) -> impact (1) ->
    unit-testing/ pr-review/          tests (2) -> PR review (3, Approved Yes/No)
    app-code-review/                  deep per-file code review
    fastapi-auth/                     JWT, refresh, passwords, OTP, OAuth/SSO
    fastapi-security-checklist/       OWASP API Top 10 PR checklist, per-portal notes
    fastapi-deploy-ci/                Dockerfile, compose, GitHub/GitLab CI, pre-commit
    fastapi-observability/            logging, metrics, tracing, health, alerts
    fastapi-background-and-realtime/  jobs, files, exports, WebSocket/SSE, outbox, webhooks
  commands/                           /new-endpoint /new-migration /new-feature /pre-pr-check
templates/
  CLAUDE.md                           copy into a new project and fill in
  fastapi-starter/                    runnable starter app (auth, users, RBAC, Alembic, tests)
```

## Start a new project

1. Copy `templates/fastapi-starter/` as the new project, then follow its README (`make test`, `make run`).
2. Copy `templates/CLAUDE.md` to the project root and fill in the application profile(s).
3. Copy `.claude/` into the project (see Install).

The starter's tests pass (23 tests, run locally with Python 3.11). The Docker and CI templates in `fastapi-deploy-ci` have had their YAML syntax checked but have not been run.

## Install

Per project (shared with the team through git):

```bash
mkdir -p .claude/skills
cp -r path/to/fast-api-skills/.claude/skills/* .claude/skills/
cp -r path/to/fast-api-skills/.claude/commands .claude/
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
