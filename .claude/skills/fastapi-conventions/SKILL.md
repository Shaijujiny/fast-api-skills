---
name: fastapi-conventions
description: The standard project setup and backend coding conventions for Python FastAPI + Pydantic + SQLAlchemy services. Use this skill whenever scaffolding a new FastAPI project or building, refactoring, or reviewing backend code — routers, services, schemas, ORM models, migrations, or pull-request review — even if the user doesn't mention conventions, architecture, or a spec. Also use it for "where should this file go", "how should this be structured", or "set up a new FastAPI project" questions.
---

# FastAPI Conventions

The house standard for a FastAPI backend. It defines a base architecture that new projects start from and existing ones stay consistent with, so any developer (or AI-generated patch) lands in a predictable shape.

Everything here is project-agnostic. Where a name is prescribed (`BaseSchema`, `ApiResponse`, `AppException`), it is the convention to create in the project, not something that already exists elsewhere. If a project already has an equivalent, use theirs and keep the pattern.

This skill is the scaffolding and file-placement companion to `fastapi-blueprint` (`../fastapi-blueprint`), which holds the full engineering standard (principles, API design, security, testing, Git, review). Where the two overlap, the blueprint wins; this skill stays short and links to it.

## Pick the reference first

| Working on | Read |
|---|---|
| Bootstrapping a project from scratch | the bootstrap order below, then `references/backend.md` |
| Routers, services, schemas, ORM models, migrations, auth, localization | `references/backend.md` |
| Reviewing a PR, or self-checking before pushing | `references/review-checklist.md` (deep review: `app-code-review`) |

Read the file — don't work from this summary alone. The references carry the exact folder layout, base classes, and naming to generate.

## The spine

These account for most review comments:

1. **Nothing user-facing is hardcoded.** Backend copy comes from a message bundle resolved per request.
2. **Nothing configurable is hardcoded.** Use a typed settings object — never read the environment directly in feature code.
3. **Boundaries are schema-validated.** Every request/response body is a Pydantic model on a shared base.
4. **Full typing.** Full annotations on every Python signature.
5. **Money is `Decimal`.** Never float. `DECIMAL(18,2)` with a non-negative constraint in the DB.
6. **Sensitive data never travels or logs raw.** Mask PII declaratively at the schema layer; keep at-rest and in-transit ciphers separate.
7. **Layers stay thin.** Routers delegate to services; services use repositories/model helpers for DB access. Business logic lives in exactly one place.
8. **Commits:** `<TICKET-ID> <type>: <short description>`, type in `feat|fix|refactor|chore|docs|test`. Branches `feature/<TICKET-ID>-...` / `bugfix/<TICKET-ID>-...`, merged to a staging branch, promoted to main. Enforce with a hook or CI check (see blueprint chapter 12).

## The API contract

Agree these up front — mismatches here are the most common integration bug for API consumers:

- **Envelope.** Every REST response uses one shape: `status` (`"1"` ok / `"-1"` error), `status_code`, `code`, `message`, `data`.
- **Casing.** Python attributes are `snake_case`; the shared Pydantic base may apply an alias generator if the API contract is camelCase. Decide once per project.
- **Errors.** One exception type carries a semantic code (`AUTH_401_*`, `ACC_403_*`, `NF_404_*`, `BR_422_*`, `REQ_400_*`, `SYS_500_*`). Clients branch on `code`, never on message text.
- **Lists.** Query params `offset` / `limit` / `search_key`; responses carry the page plus `total_count`.
- **Language.** Resolve `Accept-Language` into the request's language (default `en`).
- **Auth.** Bearer JWT. Server-side identity always comes from the decoded token, never the request body.
- **Time.** Pick one app timezone in config. Store UTC and convert on the way out with a serializer alias; never emit naive datetimes.

## Bootstrap order for a new project

FastAPI app + settings module → shared primitives (`BaseSchema`, `ApiResponse`, `AppException`, `ErrorCode`, pagination params) → DB engine + session dependency → dependency aliases for common deps and auth → message bundle (`en` + second locale) → serializer/mask annotation aliases → `main.py` (middleware, exception handlers, lifespan, router mounting) → Alembic setup → first feature under `app/api/<feature>/` → Ruff config + hooks.

Do the shared layers before the first feature. Features written against a missing base layer end up inventing their own.

## Before saying a change is done

- Linter clean; explicit commit after writes; new tables declare their charset/collation; every schema change has a matching migration; new copy added to every locale bundle.
- Walk `references/review-checklist.md` and fix anything marked as a blocker.

## When the standard doesn't cover it

Match the surrounding code rather than inventing a new pattern, and say so in the reply ("the standard doesn't cover X; I followed the pattern in `<file>`"). If a genuinely new shared primitive is needed, add it to the shared layer — the annotation aliases, the utils package — instead of scattering one-off implementations across features.
