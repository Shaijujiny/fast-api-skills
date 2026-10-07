# 1. Purpose & Scope

## 1.1 Purpose

This skill is the single reference for how code is written, reviewed, tested, and shipped in our FastAPI services. It applies to every FastAPI app we build (fintech apps, assessment portal, interview portal, transport portal, and future ones). Its goals:

- **Consistency:** every feature looks like every other feature, so anyone can navigate any module in any app.
- **Safety:** our apps handle payments, personal data, exam and interview records, and bookings. Money, PII, and concurrency rules are strict.
- **Predictable review:** reviewers and authors check against the same list (section 14).

Use it when you plan a task, write code, review a merge request, or generate code with an AI assistant. Where an existing codebase deviates from a rule, it is called out as **Repo reality**: don't copy the bad example, and don't "fix" it inside an unrelated change.

## 1.2 Stack at a glance

| Concern | Choice |
|---|---|
| Language | Python 3.11+ |
| Web framework | FastAPI |
| ORM | SQLAlchemy 2.x typed mapping (`Mapped[...]`, `mapped_column`) |
| Migrations | Alembic |
| DTOs | Pydantic v2 through a shared `BaseSchema` |
| Database | Relational: MySQL 8 or PostgreSQL |
| Cache / rate limit / locks | Redis (optional; the app must degrade gracefully without it) |
| Lint / format | Ruff, line length 120 |
| Tests | pytest with FastAPI `TestClient` / `httpx` |
| Deploy | Docker; CI/CD per project |

DB access may be sync `Session` or async `AsyncSession`; pick one per project and don't mix. Async handlers must never run blocking calls on the event loop (section 2.9).

## 1.3 In scope

- REST features under `app/api/<feature>/` (router, schemas, service).
- ORM models in `app/models/`, data access in `app/repositories/`, external clients in `app/integrations/`.
- Core wiring in `app/core/` (config, security, exceptions, deps) and shared helpers in `app/utils/`.
- Alembic migrations, scheduled/background jobs, export/file generation.
- Tests, lint, commits, branches, and merge requests.

## 1.4 Out of scope

- Introducing new frameworks without a concrete need and lead approval.
- Front-end code and infrastructure beyond what a feature needs.

## 1.5 How to use this skill

1. Planning a task: read sections 3, 4, 5, 6 and use the checklist in section 13.
2. Touching the DB: read section 7 first (migrations, locking, transactions).
3. Touching money, PII, files, or external APIs: read section 8.
4. Before opening a merge request: run the self-review and checklist in section 14.

## 1.6 Rule strength

- **MUST / NEVER**: a violation blocks the merge request.
- **SHOULD**: follow unless there is a documented reason.
- **Repo reality**: an observed deviation in existing code. Don't copy it.

## 1.7 What this skill controls

Production-grade FastAPI development end to end: API design standards, architecture and folder structure, coding conventions, validation, database practices, security, testing, Git workflow, code generation, code review, maintainability, and performance.

## 1.8 Baseline rules

- Follow existing project conventions before introducing new ones.
- Prefer simple, maintainable solutions.
- Do not add libraries or design patterns without a concrete need.
- Existing business behaviour must not change unintentionally; if a change is intended, say so in the MR and the project's changelog.
- New code is production-ready: typed, tested, documented, and handles errors.

## 1.9 The skill's end-to-end goal

Guide work from **requirement → design → implementation → testing → review → Git/PR**. Applying only the "write the endpoint" part is a misuse of this skill.
