# FastAPI starter

Minimal FastAPI service following the `fastapi-blueprint` / `fastapi-conventions` standard:
FastAPI, Pydantic v2 + pydantic-settings, SQLAlchemy 2.x (sync), Alembic, pytest + httpx. Python 3.11+.

## Run

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # set SECRET_KEY; DATABASE_URL defaults to sqlite
make migrate                # alembic upgrade head
make run                    # http://127.0.0.1:8000/docs
make test                   # pytest -q
make lint                   # ruff
```

`DATABASE_URL` selects the database: `sqlite:///./app.db` (dev/tests), `mysql+pymysql://...` or
`postgresql+psycopg://...` (prod; install the driver, see `requirements.txt`).

Create the first admin (there is deliberately no public signup):

```bash
python -c "from app.core.database import SessionLocal as S; from app.models import User; from app.core.security import hash_password as h; \
db=S(); db.add(User(email='admin@example.com', name='Admin', hashed_password=h('change-me-now'), role='admin')); db.commit()"
```

## What is where

| Path | Role |
|---|---|
| `app/api/<feature>/{router,schemas,service}.py` | HTTP layer / DTOs / business logic (service commits once) |
| `app/repositories/` | the only place that queries the DB |
| `app/models/` | SQLAlchemy tables |
| `app/core/` | config, security (JWT, hashing, RBAC tables), exceptions, deps, i18n, logging |
| `app/schemas/common.py` | `BaseSchema` (camelCase wire), `ApiResponse[T]`, pagination |
| `app/integrations/` | one client per external provider (stub included) |
| `app/locales/*.json` | i18n message keys; every locale must have the same keys (tested) |
| `migrations/` | Alembic |

Conventions baked in: `ApiResponse[T]` envelope for success and errors, `AppException`/`ErrorCode` with global
handlers, request-id middleware (`X-Request-ID`), `require_permission(resource, action)`, CORS and all config from env,
no secrets in logs, money as `Decimal` / `Numeric(18, 2)` (never `float`).

## Add a feature

1. `app/models/<entity>.py` (+ export in `app/models/__init__.py`), then `make revision m="add <entity>"` and review the migration.
2. `app/repositories/<entity>.py`: all queries; `flush()` only, no commit.
3. `app/api/<feature>/schemas.py` (`BaseSchema`, `...Request`/`...Response`), `service.py` (`<Feature>Service(deps)`, raise `AppException`, commit once), `router.py` (one line per route, `require_permission(...)`, docstring with `### Business Rules:`).
4. Add the resource to `Resource` and `ROLE_PERMISSIONS` in `app/core/security.py`; mount the router in `app/api/__init__.py`.
5. Add message keys to **every** file in `app/locales/`; add tests in `tests/`.

## Blueprint chapters to read

`.claude/skills/fastapi-blueprint/references/`: 03 architecture, 04 API and routing, 05 schemas, 06 logic and data access,
07 database and transactions, 08 security and integrations, 10 testing, 15 users/roles/privileges (RBAC and data scoping).
Before opening a PR also read 14 (review and definition of done) and 12 (git).

## Known simplifications

Permissions are a code-level role map (chapter 15 recommends tables plus a cached resolver once roles must be editable);
no refresh tokens, rate limiting or tenant scoping yet.
