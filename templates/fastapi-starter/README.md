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

`DB_TYPE` (`mysql` | `postgresql`) selects the SQL backend; its settings live in `app/database/<db>/config.py` (`MYSQL_*` / `POSTGRESQL_*` env vars).
`DATABASE_URL` overrides with a full URL (`sqlite:///./app.db` for dev/tests). Install the driver, see `requirements.txt`.
MongoDB (`app/database/mongodb/`) is opt-in and separate from the SQL stack.

`make migrate` also seeds the default roles (`super_admin`, `admin`, `staff`, `user`) and their permissions
(`python -m app.core.seed` does the same idempotently). Create the first super admin (no public signup):

```bash
python -c "from app.database import SessionLocal as S; from app.models import User; from app.core.security import hash_password as h; \
db=S(); db.add(User(email='admin@example.com', name='Admin', hashed_password=h('change-me-now'), role='super_admin')); db.commit()"
```

## What is where

| Path | Role |
|---|---|
| `app/api/<feature>/{router,schemas,service}.py` | HTTP layer / DTOs / business logic (service commits once) |
| `app/repositories/` | the only place that queries the DB; `base.py` has `Scope` and the `ScopedRepository` mixin (tenant filter) |
| `app/models/` | SQLAlchemy tables: users, organizations, roles/permissions/role_permissions, refresh_tokens |
| `app/database/` | one package per database: `mysql/`, `postgresql/` (config, base, session), `mongodb/` (client, config, models); `__init__` switches on `DB_TYPE` |
| `app/core/` | config, security (JWT, hashing, refresh-token hashing, cached RBAC resolver), `rate_limit.py` (pluggable memory/Redis limiter), `seed.py` (default roles/permissions), exceptions, deps, i18n, logging |
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
4. Add the resource to `Resource` in `app/core/security.py`, add its permissions to `DEFAULT_ROLES` in `app/core/seed.py` and to a new migration (roles are rows now, editable via `PUT /roles/{name}/permissions`); mount the router in `app/api/__init__.py`.
5. Add message keys to **every** file in `app/locales/`; add tests in `tests/`.

## Scope a new feature to the tenant

1. Give the table an `organization_id` FK (`organizations.id`, indexed, NOT NULL for tenant data) and set it on create from `deps.current_user.organization_id`.
2. Make the repository extend `ScopedRepository` with `scope_model = <Model>`, take a `Scope` in every `get_*`/`list`/count, and wrap the statement with `self.scoped(stmt, scope)`.
3. The service passes `deps.scope` (built by `get_scope`: the caller's org, or everything for `super_admin`) and answers **404, not 403**, when a row is outside the scope.
4. Add a cross-tenant test (org A cannot get/list org B; `super_admin` can). See `tests/test_rbac_tenancy.py`. Users with no organization only see other unassigned rows.

## Auth behaviour

- `POST /auth/login` returns `accessToken` + `refreshToken`; `POST /auth/refresh` rotates (reuse of a used token revokes the whole family); `POST /auth/logout` revokes the family; `POST /auth/change-password` and `PATCH /users/{id}/role` revoke all of the user's refresh tokens. Only a SHA-256 hash of a refresh token is stored. Access tokens already issued stay valid until they expire (`ACCESS_TOKEN_EXPIRE_MINUTES`).
- Login is rate limited per IP + email, refresh per IP (429 + `Retry-After`); repeated failures lock the account for `LOGIN_LOCKOUT_MINUTES`. Unknown email, wrong password and locked account return the identical 401.
- Permissions live in the `roles`/`permissions`/`role_permissions` tables, resolved through a per-process TTL cache (`PERMISSION_CACHE_TTL_SECONDS`) that is invalidated on role update.

## Blueprint chapters to read

`.claude/skills/fastapi-blueprint/references/`: 03 architecture, 04 API and routing, 05 schemas, 06 logic and data access,
07 database and transactions, 08 security and integrations, 10 testing, 15 users/roles/privileges (RBAC and data scoping), 18 error handling and responses.
Before opening a PR also read 14 (review and definition of done) and 12 (git).

## Known simplifications

- The default rate limiter is in-memory and single-process (counters are not shared between workers or hosts); set `REDIS_URL` (and `pip install redis`) for multi-worker deployments. If the limiter backend errors, requests are allowed and the error is logged.
- The permission cache is per process: a role edit is instant on the worker that served it and visible on others within the cache TTL.
- No MFA, password reset/OTP flows, or audit log; no organization management endpoints (create organizations via SQL or a seed).
- Lockout is per account, and a locked account is indistinguishable from a wrong password by design (no unlock endpoint; it expires).
- The client IP is `request.client.host`; behind a proxy run uvicorn with `--proxy-headers --forwarded-allow-ips`.
