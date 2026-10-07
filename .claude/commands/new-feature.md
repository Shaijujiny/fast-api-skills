---
description: Build a full vertical slice (model, migration, schemas, service, router, permissions, tests)
---
Implement feature: $ARGUMENTS

Use the `fastapi-blueprint` skill (chapters 3-8, 10, 13, 15).

1. Clarify requirement and acceptance criteria; list endpoints, tables, roles. Use `task-plan` if the task is large.
2. Model + Alembic migration (see /new-migration).
3. Schemas, repository, service, router for each endpoint (see /new-endpoint).
4. Permissions: define privileges, enforce on every endpoint, apply data scoping to every list, export and file route.
5. Cross-cutting: Decimal for money, single commit, no secrets in logs, i18n keys for messages, audit log where needed; background/realtime parts via `fastapi-background-and-realtime`.
6. Tests: unit and API tests including permission and scoping cases.
7. Run lint/tests, then summarize what was built and what was verified.
