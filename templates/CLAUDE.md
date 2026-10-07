# {{PROJECT_NAME}}

## Application profile
Profile(s): {{fintech | assessment | interview | transport}}. See `fastapi-blueprint` chapter 17 (application profiles) for the extra rules of each.

## Stack
{{Python x.y, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, MySQL|PostgreSQL, Redis, queue/worker, object storage}}

## Run / test / migrate
- Run: `{{command}}`
- Test: `{{command}}`
- Lint: `{{command}}`
- Migrate: `alembic upgrade head` / new revision: `alembic revision --autogenerate -m "..."`

## Layout
{{Describe: app/<feature>/{router,schemas,service,repository,models}.py, core/, tests/ ... see fastapi-blueprint default layout}}

## Non-negotiables
- Money is `Decimal`/Numeric, never float.
- Commit once per request/use case, in the service layer.
- No secrets, tokens or PII in logs.
- User-facing messages use i18n keys.
- Permissions checked and data scoped (owner/tenant) on every endpoint, especially lists and exports.
- Never claim tests passed unless you ran them; state what was not run.

## Which skill when
- `task-plan`: before starting a non-trivial task.
- `impact-analysis`: describe API/DB/env impact of a change.
- `unit-testing`: derive test scenarios for the diff.
- `pr-review` / `app-code-review`: review a branch or PR.
- `fastapi-blueprint`: default standard for any endpoint/service/model work.
- `fastapi-auth`: login, tokens, roles, sessions.
- `fastapi-security-checklist`: before shipping anything touching auth, PII, files, money.
- `fastapi-deploy-ci`: Docker, CI/CD, environments.
- `fastapi-observability`: logging, metrics, tracing, alerts.
- `fastapi-background-and-realtime`: jobs, schedulers, uploads, exports, WebSockets/SSE, webhooks.

## Project-specific decisions
- Auth approach: {{}}
- Queue / scheduler choice: {{}}
- Storage and retention: {{}}
- Roles and privileges: {{}}
- Other: {{}}
