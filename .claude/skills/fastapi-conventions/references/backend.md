# Backend — Python FastAPI + Pydantic

The standard backend setup: FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic. This file is the scaffolding shape (folders, primitives, naming). The full engineering rules — principles, API design, transactions, security, testing, Git, review — are in `fastapi-blueprint` (`../../fastapi-blueprint`); this file links there instead of repeating them.

## Contents

- [Stack](#stack)
- [Project layout](#project-layout)
- [Three-layer feature module](#three-layer-feature-module)
- [Shared primitives to build first](#shared-primitives-to-build-first)
- [Routers](#routers)
- [Services](#services)
- [Schemas](#schemas)
- [Models and migrations](#models-and-migrations)
- [Responses and errors](#responses-and-errors)
- [Auth](#auth)
- [Localization](#localization)
- [Security](#security)
- [Style and lint](#style-and-lint)
- [Cross-cutting](#cross-cutting)
- [New endpoint checklist](#new-endpoint-checklist)

## Stack

| Concern | Choice |
|---|---|
| Language | Python 3.11+ |
| Web framework | FastAPI |
| ORM | SQLAlchemy 2.0 typed mapping (`Mapped[...]` / `mapped_column`) |
| DB access style | Choose sync `Session` or async session once, project-wide, and don't mix |
| Validation / DTOs | Pydantic v2 on a shared `BaseSchema` |
| Database | MySQL or PostgreSQL, driver chosen in config |
| Migrations | Alembic |
| Cache / rate limit | Redis |
| Scheduling | APScheduler (or a worker queue) registered in the lifespan |
| File storage | Local FS or object storage, behind one storage abstraction |
| Lint / format | Ruff (line length 120) |
| Runtime | Docker |

**Async vs. blocking I/O.** With a synchronous DB session, handlers may still be `async` but DB calls block. Keep that consistent and don't add avoidable blocking work (sleeps, heavy CPU, slow third-party calls) inline; offload long work to a scheduler or worker. See blueprint chapters 3 and 9.

## Project layout

```txt
app/
├── api/<feature>/          # router.py / schemas.py / service.py per feature
│   └── __init__.py         # router registry — mounts every feature
├── repositories/           # all DB queries
├── models/                 # SQLAlchemy tables
├── integrations/           # external API clients
├── core/                   # config, security, exceptions, i18n, base schemas, logging
├── main.py                 # app: lifespan, middleware, scheduler, router mounting
migrations/                 # Alembic
scripts/                    # one-off / maintenance scripts
tests/
```

Keep `app/api/<feature>/` flat. Don't add sub-packages inside a feature unless it genuinely has sub-features.

## Three-layer feature module

- `router.py` — HTTP layer: routes, dependency wiring. No business logic.
- `schemas.py` — Pydantic request/response DTOs for this feature.
- `service.py` — business logic and orchestration; DB access goes through `app/repositories`.

Flow: request → router (validate, authn/authz, inject deps) → `Service(...).method(payload)` → repositories / integrations → `ApiResponse`. Routers are one line of real work; services own the logic. Details: blueprint chapters 3, 4 and 6.

## Shared primitives to build first

Build these once, import them everywhere, never redefine them locally.

| Primitive | Lives in |
|---|---|
| `BaseSchema`, `ApiResponse[T]`, `AppException`, `ErrorCode` | `app/core/` |
| Pagination params (`offset`, `limit`, `search_key`) | `app/core/` |
| Current-user schema, permission/resource enums, `require_permission` | `app/core/security` |
| Common dependency aliases (`db`, `lang`, `current_user`) | `app/core/deps` |
| `get_db` session dependency, context-managed session for jobs | `app/core/database` |
| Message bundle / i18n factory | `app/core/i18n` |
| Serializer aliases (decimal rounding, masking, local datetime) | `app/core/annotations` |
| Crypto helpers (encrypt/decrypt, hashing, masking) | `app/core/crypto` |
| Storage abstraction, cache and rate-limit helpers | `app/core/` |
| Settings object, logger | `app/core/config`, `app/core/logging` |

**Registration.** Every feature router is mounted in `app/api/__init__.py` with its prefix and tags; `main.py` includes that aggregate router.

## Routers

```python
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/summary", response_model=ApiResponse[DashboardSummaryResponse])
async def dashboard_summary(
    deps: CommonDeps,
    params: Annotated[DashboardSummaryRequest, Depends()],
) -> ApiResponse[DashboardSummaryResponse]:
    """
    Get dashboard summary analytics.

    ### Business Rules:
    - Requires `dashboard:read` permission.
    """
    return await DashboardService(deps).summary(params)
```

- Always annotate the return type and set `response_model`.
- Every route has a docstring; privileged routes document `### Business Rules`.
- Authorization goes on the route via a permission dependency; reads use read access, mutations write access.
- Inject dependencies through aliases, never construct them by hand; pre-auth flows (login, password reset) use a lighter alias without a current user.
- Group query/filter params into a schema injected with `Annotated[Schema, Depends()]`.
- Pass `Request` into the service only when it needs headers/IP/user-agent.

## Services

- Classes named `<Feature>Service`, constructed with the common deps; pull `db`, `lang`, `current_user` off them in `__init__` and resolve the message bundle for the request language.
- Methods return `ApiResponse` and resolve user-facing copy via message keys.
- Raise `AppException` for errors — never return bare dicts or raw `HTTPException`.
- **Transactions:** the service owns commit/rollback. Commit explicitly after a write; roll back before re-raising if a partial write could leak into a later query. See blueprint chapter 7.

## Schemas

- Always model data with Pydantic — never raw `dict`/JSON literals for bodies, responses, or payloads passed between layers.
- All DTOs subclass `BaseSchema` (`from_attributes=True`, `populate_by_name=True`, plus alias generator if the API is camelCase), not bare `BaseModel`.
- Naming: inputs end in `Request`, outputs in `Response`. Closed choice sets use str-valued `Enum`.
- Typed fields with `Field(...)`, `default_factory` for collections, validators where needed. Money uses `Decimal`.
- Field transforms (rounding, masking, decrypting, local-time rendering) are declarative `Annotated` aliases in one module, not hand-coded in services. Add a new alias there rather than scattering serializers.
- Lists: shared pagination params in, page plus `total_count` out.

More: blueprint chapter 5.

## Models and migrations

- SQLAlchemy 2.0 typing: `Mapped[...]` + `mapped_column(...)`; use `ForeignKey`, `CheckConstraint`, and `Enum` at the column level.
- Money is `DECIMAL(18, 2)` with a non-negative `CheckConstraint`.
- **Charset/collation:** declare it explicitly in `__table_args__` on every new table. A mismatch breaks foreign keys and JOINs against existing tables.
- Do not rename existing columns without a migration.
- Models hold mappings only; queries live in `app/repositories`. Parameterize through the ORM or bound params — never string-build SQL. Eager-load (`joinedload` / `selectinload`) to avoid N+1.
- Outside a request (schedulers, scripts) use a context-managed session, not the request dependency.
- **Migrations:** Alembic only. Every model change ships with its migration in the same PR; migrations are additive and safe on existing data. See blueprint chapter 7.

## Responses and errors

Success — always `ApiResponse`:

```python
return ApiResponse(
    status="1",
    status_code=status.HTTP_200_OK,
    code=ErrorCode.SUC_200_SUCCESS,
    message=self.message.some_success,   # resolved copy — never hard-coded
    data=payload,                        # Pydantic model or None — never a raw dict
)
```

Errors — raise `AppException` with a semantic `ErrorCode`:

```python
raise AppException(
    status="-1",
    status_code=status.HTTP_403_FORBIDDEN,
    code=ErrorCode.ACC_403_INSUFFICIENT_PERMISSIONS,
    message=self.message.unauthorized,
)
```

`ErrorCode` members are named by HTTP bucket: `SUC_2xx_*`, `AUTH_401_*`, `ACC_403_*`, `NF_404_*`, `BR_422_*`, `REQ_400_*`, `SYS_500_*`. Global handlers translate exceptions (`HTTPException`, DB errors, `RequestValidationError`, `AppException`, catch-all) into the standard envelope and log them. No bare `except:` and no silent swallow.

## Auth

- Protect endpoints with a permission dependency (resource + action). Reads use view-level access, mutations the edit-level.
- OAuth2 bearer + JWT; the current user is a typed schema resolved by a dependency.
- Identity comes from the current user, never the request body. Enforce object-level scope — a user may only act on records they're entitled to.
- Pre-auth endpoints (login, reset password, OTP) do their own checks in the service.

See blueprint chapters 8 and 15.

## Localization

- Never hard-code user-facing text at the call site; reference copy as `self.message.<snake_case_key>`.
- Language comes from `Accept-Language`, default `en`.
- Add every new key to **every** locale bundle with matching names.

## Security

- **Two cipher scopes — do not mix.** One cipher protects values at rest; a separate one protects values sent to clients. Moving an at-rest value into a client context is an explicit decrypt then re-encrypt (ideally via a single bridge alias).
- Passwords and secrets: hash/verify helpers; never log or return them.
- Mask emails, phone numbers, account numbers, and government IDs in responses and logs.
- Export policy: define once per project and follow it consistently; don't decide per endpoint.
- Files: all I/O through the storage abstraction; file-serving routes add an explicit permission check.
- Security headers, CORS origins and trusted hosts are applied centrally from config; don't duplicate per-route or widen ad hoc.

## Style and lint

- Ruff, clean build, no blanket ignores; per-rule ignores live in `pyproject.toml` with overrides for `__init__.py` and tests.
- Line length 120; docstrings on public functions and classes; max cyclomatic complexity 10.
- Full type annotations on signatures; `Decimal` for money.
- Reuse `app/core` helpers before re-implementing.

## Cross-cutting

- **Logging:** a shared `get_logger(__name__)`; structured access log; never log PII or secrets.
- **Time:** one helper returns "now" in the configured timezone. No naive `datetime.now()`.
- **Scheduling:** register jobs in the lifespan with a stable `id` and `replace_existing=True`; long jobs set `max_instances=1`; job bodies open their own session.
- **Config:** typed settings object. Never `os.environ` in feature code; add new vars to `.env.example`.
- **Cache / rate limit:** initialize in the lifespan; degrade gracefully if Redis is unreachable.

## New endpoint checklist

1. Request/response schemas in `schemas.py` on `BaseSchema`, with aliases for money, masking, encryption.
2. Repository method for any new query.
3. Service method returning `ApiResponse`; commit writes explicitly.
4. Thin route in `router.py` with docstring, permission dependency, and deps alias.
5. Register the router in `app/api/__init__.py`.
6. All user-facing text via message keys, added to every locale bundle.
7. New tables: charset/collation and an Alembic migration.
8. Encrypt/mask sensitive fields; honour export and file-storage policies.
9. Tests added (blueprint chapter 10); linter clean.
10. Commit as `<TICKET-ID> <type>: <description>`.
