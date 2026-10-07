---
name: fastapi-blueprint
description: "Common engineering standard for FastAPI services (Pydantic v2, SQLAlchemy 2.x, Alembic, MySQL/PostgreSQL) used across our fintech, assessment, interview and transport portals. Use when adding or changing an endpoint, router, service, schema, model, DB table or migration, background job, external API integration, export or file route; when touching money, payments, permissions or PII; when writing tests; when preparing a commit or pull request; or when reviewing code. Guides requirement to design, implementation, testing, review and Git/PR."
---

# FastAPI Blueprint (common engineering skill)

Goal: guide an AI agent or developer from **requirement → design → implementation → testing → review → Git/PR**, not just generate endpoint code.

This file is the master. Start here. Use the task map below to pick which files in `references/` to read, then read only those.

## Read this first: which chapters for which task

| If you are... | Read |
|---|---|
| Adding or changing an endpoint | [architecture](references/03-architecture-and-design-patterns.md), [API & routing](references/04-api-design-and-routing.md), [schemas](references/05-schemas-validation-serialization.md), [logic & data access](references/06-business-logic-and-data-access.md), [code generation](references/13-code-generation-and-anti-patterns.md) |
| Changing a table, column, query, or lock | [logic & data access](references/06-business-logic-and-data-access.md), [DB & concurrency](references/07-database-transactions-concurrency.md) |
| Touching money, payments or balances | [DB & concurrency](references/07-database-transactions-concurrency.md) (concurrency), [security & integrations](references/08-security-and-external-integrations.md), [review & DoD](references/14-code-review-and-definition-of-done.md) (red flags), [lessons learned](references/16-lessons-learned.md) |
| Roles, permissions, data scoping, user or entity status | [users & privileges](references/15-domain-users-roles-privileges.md) |
| Adding auth, privileges, masking, exports, files | [security & integrations](references/08-security-and-external-integrations.md), [schemas](references/05-schemas-validation-serialization.md) |
| Calling a third-party API | [security & integrations](references/08-security-and-external-integrations.md) (integrations), [logic & data access](references/06-business-logic-and-data-access.md), [DB & concurrency](references/07-database-transactions-concurrency.md) (locks) |
| Adding a scheduled job or background work | [DB & concurrency](references/07-database-transactions-concurrency.md) (7.8), [performance](references/09-performance-and-observability.md) |
| Slow endpoint or heavy query | [performance](references/09-performance-and-observability.md), [DB & concurrency](references/07-database-transactions-concurrency.md) |
| Writing or running tests | [testing & quality](references/10-testing-and-quality.md), [automation testing](references/11-automation-testing.md) |
| Committing, branching, opening a merge request | [git](references/12-git-standard.md) |
| Generating code with an AI assistant | [code generation](references/13-code-generation-and-anti-patterns.md), [review & DoD](references/14-code-review-and-definition-of-done.md) (14.7) |
| Reviewing a change | [review & DoD](references/14-code-review-and-definition-of-done.md) |
| Unsure where something belongs | [scope](references/01-purpose-and-scope.md), [principles](references/02-core-engineering-principles.md), [architecture](references/03-architecture-and-design-patterns.md) |
| Changing a calculation, adding a guard, or fixing a race | [lessons learned](references/16-lessons-learned.md) |
| Starting work on a specific app type (fintech, assessment, interview, transport) | [application profiles](references/17-application-profiles.md) |

Open only the files the task needs; they are long. Chapter 17 lists the extra rules per application type; read the profile that matches the app.

## The non-negotiables

1. Follow the project's existing conventions before introducing new ones. Inspect existing code first.
2. Layering: `Router → Service → Model helpers (the repository role) → Database`, with external APIs reached through an integration client from the service. Each layer has one job.
3. Pydantic schemas (`BaseSchema`) for every request, response, and structured payload. No raw dicts for structured data.
4. Transactions: mutate, validate, then **commit once at the end**; roll back on failure; `flush()` when you need generated ids before commit.
5. Money is `Decimal`. Never `float`.
6. Never hold a DB lock while waiting on a slow external API unless a specific transactional requirement demands it, and then with a short timeout.
7. Secrets, tokens, passwords, and PII never reach logs or error messages.
8. Every user-facing message goes through i18n message keys, with every supported locale filled.
9. Preserve existing business behaviour; no unintended changes.
10. **Never claim tests, lint, or a run passed unless it was actually executed.** Say what was verified and what was not.

## Workflow

| Phase | Do | Reference |
|---|---|---|
| Requirement | clarify scope, actors, money/PII, DB change, failure cases; write a plan | [scope](references/01-purpose-and-scope.md), [code generation](references/13-code-generation-and-anti-patterns.md), [users & privileges](references/15-domain-users-roles-privileges.md) |
| Design | pick layers and files; mirror the closest existing feature | [architecture](references/03-architecture-and-design-patterns.md), [API & routing](references/04-api-design-and-routing.md), [logic & data access](references/06-business-logic-and-data-access.md) |
| Implement | schemas → model helper → service → router → registration → locale → SQL | [schemas](references/05-schemas-validation-serialization.md), [logic & data access](references/06-business-logic-and-data-access.md), [DB & concurrency](references/07-database-transactions-concurrency.md), [security & integrations](references/08-security-and-external-integrations.md) |
| Test | unit, integration, API, concurrency; run them | [testing & quality](references/10-testing-and-quality.md), [automation testing](references/11-automation-testing.md), [lessons learned](references/16-lessons-learned.md) |
| Review | self-review, impact analysis, test notes, then reviewer checklist | [review & DoD](references/14-code-review-and-definition-of-done.md) |
| Git / PR | commit format, branch, PR content, Alembic migration | [git](references/12-git-standard.md) |

## Reference files (`references/`)

| # | File | Topic |
|---|------|-------|
| 1 | [references/01-purpose-and-scope.md](references/01-purpose-and-scope.md) | Purpose and scope |
| 2 | [references/02-core-engineering-principles.md](references/02-core-engineering-principles.md) | Core engineering principles |
| 3 | [references/03-architecture-and-design-patterns.md](references/03-architecture-and-design-patterns.md) | Architecture and design patterns |
| 4 | [references/04-api-design-and-routing.md](references/04-api-design-and-routing.md) | API design and routing |
| 5 | [references/05-schemas-validation-serialization.md](references/05-schemas-validation-serialization.md) | Schemas, validation, serialization |
| 6 | [references/06-business-logic-and-data-access.md](references/06-business-logic-and-data-access.md) | Business logic and data access |
| 7 | [references/07-database-transactions-concurrency.md](references/07-database-transactions-concurrency.md) | Database, transactions, concurrency |
| 8 | [references/08-security-and-external-integrations.md](references/08-security-and-external-integrations.md) | Security and external integrations |
| 9 | [references/09-performance-and-observability.md](references/09-performance-and-observability.md) | Performance and observability |
| 10 | [references/10-testing-and-quality.md](references/10-testing-and-quality.md) | Testing and quality |
| 11 | [references/11-automation-testing.md](references/11-automation-testing.md) | Automation testing |
| 12 | [references/12-git-standard.md](references/12-git-standard.md) | Git standard |
| 13 | [references/13-code-generation-and-anti-patterns.md](references/13-code-generation-and-anti-patterns.md) | Code generation and anti-patterns |
| 14 | [references/14-code-review-and-definition-of-done.md](references/14-code-review-and-definition-of-done.md) | Code review and definition of done |
| 15 | [references/15-domain-users-roles-privileges.md](references/15-domain-users-roles-privileges.md) | Users, roles, privileges (RBAC) |
| 16 | [references/16-lessons-learned.md](references/16-lessons-learned.md) | Lessons learned (general rules) |
| 17 | [references/17-application-profiles.md](references/17-application-profiles.md) | Application profiles (fintech, assessment, interview, transport) |

## Default project layout

New projects use this layout. For an existing project, follow its own equivalents and do **not** introduce a second structure.

| Layer | Default location |
|---|---|
| Router | `app/api/<feature>/router.py` |
| Schemas | `app/api/<feature>/schemas.py` (shared DTOs in `app/schemas/`) |
| Service | `app/api/<feature>/service.py` |
| Repository (only place that queries the DB) | `app/repositories/` |
| ORM models | `app/models/` |
| Integration clients | `app/integrations/` |
| Config, security, exceptions, dependencies | `app/core/` |
| Migrations | `migrations/` (Alembic) |
| Tests | `tests/` |

Default names used in the chapters: `ApiResponse[T]` (response envelope), `BaseSchema` (Pydantic base), `AppException` / `ErrorCode`, i18n message keys.

## Definition of Done

```
Implementation + Validation + Security + Transaction correctness
+ Tests + Automation tests + Documentation + Code review
+ Git standards + Quality checks  = DONE
```

Working locally is not done. See [review & DoD](references/14-code-review-and-definition-of-done.md).
