# 3. Architecture & Design Patterns

## 3.1 Repository layout

```
app/
├── api/<feature>/            # one folder per feature
│   ├── router.py             # HTTP layer only
│   ├── schemas.py            # Pydantic request/response DTOs
│   └── service.py            # business logic (may be a package if it grows)
├── models/                   # SQLAlchemy ORM models (tables only)
├── repositories/             # data access: queries, locks, paging
├── integrations/             # one client per external provider
├── core/                     # config, security, exceptions, deps, logging
├── utils/                    # shared helpers
└── main.py                   # app, lifespan, middleware, router mounting
migrations/                   # Alembic
tests/
```

**Default names.** This skill uses default names for shared primitives: `ApiResponse[T]` (response envelope), `BaseSchema` (Pydantic v2 base), `AppException` / `ErrorCode` (errors), `<Entity>Repository` (data access), `<Feature>Service`, i18n message keys, and `<Provider>Client` (integrations). They are defaults: an existing project should keep and follow its own equivalents (same role, different name) rather than renaming or adding parallel ones.

## 3.2 The three-layer module

```
HTTP request
  -> router.py     validate, authn/authz, inject deps
    -> Service(deps).method(payload)
      -> repositories, integration clients, utils
    <- ApiResponse
```

| Layer | Owns | Must not |
|---|---|---|
| Router | routes, tags, docstring, authorization, dependency wiring | contain branching, queries, or messages |
| Schemas | DTO shape, validation, masking/rounding aliases | hold business logic |
| Service | orchestration, rules, transactions, calling externals | run raw queries, return dicts |
| Repository | queries, filters, joins, lock helpers | handle HTTP concerns or build `ApiResponse` |
| Model | table mapping, relationships, constraints | contain business logic or HTTP concerns |

## 3.3 Services

- Named `<Feature>Service`; a module may hold several by responsibility (`PaymentService`, `RefundService`).
- Constructed with the shared request dependencies. Standard `__init__`:

```python
class PaymentService:
    def __init__(self, deps: CommonDeps) -> None:
        self.db = deps.db
        self.lang = deps.lang
        self.current_user = deps.current_user
        self.repo = PaymentRepository()
```

- Methods return `ApiResponse` and raise `AppException` on error.
- A service used outside a request (scheduler, worker) is built from its own session context, not from request dependencies.

## 3.4 Repositories

- One `<Entity>Repository` per aggregate; methods take the session explicitly or hold it from construction, consistently within a project.
- Use SQLAlchemy 2.x style (`select(...)`, `session.execute`/`scalars`).
- Return ORM rows or tuples (`tuple[Sequence[Entity], int]` for paged lists), never `ApiResponse`.
- Offer a `for_update: bool = False` flag on read-then-write methods so callers opt into `SELECT ... FOR UPDATE`.
- Avoid circular imports by importing sibling models inside the method when needed.

## 3.5 Shared primitives (don't re-implement)

| Primitive | Location |
|---|---|
| `BaseSchema`, `ApiResponse[T]`, pagination params (`PageParams`) | `app/core/` or `app/utils/schemas.py` |
| `AppException`, `ErrorCode`, global exception handlers | `app/core/exceptions.py` |
| `get_db`, `get_current_user`, `CommonDeps` bundle, permission/role checks | `app/core/deps.py` |
| Settings (`Settings` via pydantic-settings), JWT, password hashing, encryption | `app/core/config.py`, `app/core/security.py` |
| i18n message catalogues and lookup | `app/utils/i18n.py` (or `app/core/`) |
| Annotated aliases (rounded decimal, masked string, timezone-aware datetime) | `app/utils/types.py` |
| File storage helper (local or object storage) | `app/utils/` |
| Cache, rate limit, distributed lock | `app/utils/` (Redis, optional) |
| HTTP client wrapper with timeout and elapsed-time logging | `app/integrations/base.py` |

## 3.6 Cross-feature calls

- A service may call another feature's service or repository; avoid importing routers.
- If two features need the same logic, move it to `app/utils/` (or a shared service) rather than importing sideways in a cycle.
- Shared DTOs live in `app/utils/schemas.py`, not inside one feature.

## 3.7 Design patterns commonly in use

- **Dependency injection** via `Annotated[..., Depends()]` aliases.
- **Decorator/dependency-based authorization** and caching.
- **Declarative serialization** with `Annotated` aliases instead of per-field serializer code.
- **Factory** for locale messages; **singleton** only for expensive shared clients (connection pools).
- **Distributed lock** for scheduled jobs (Redis `SET NX EX` plus compare-and-delete release) when running multiple workers.
- **Idempotent upsert / idempotency key** for retried writes.

## 3.8 Design patterns: use only when justified

> A design pattern must solve an actual problem. Do not introduce one merely because it exists.

| Pattern | When to use |
|---|---|
| Dependency injection | already everywhere (`Depends`); keep using it |
| Service layer | the standard; one `<Feature>Service` per responsibility |
| Repository | the standard for data access |
| DTO | `BaseSchema` request/response schemas |
| Factory | locale messages; add another only for a real family of variants |
| Adapter | one client class per provider (payment gateway, video provider, maps); mandatory for new integrations |
| Strategy | several interchangeable algorithms (payment channels, scoring rules, fare calculators); not for a single `if` |
| Unit of work | the per-request `Session` with one commit at the end |
| Observer / event-driven | background tasks for non-critical side effects (emails, notifications); a message bus needs a documented need |
| Singleton | connection pools and settings only |

Before adding a pattern, write down the concrete problem it solves and the second caller that needs it.

## 3.9 The dependency layer

Dependencies give a route its collaborators. They live in `app/core/deps.py`.

| Dependency | Provides | Notes |
|---|---|---|
| `get_db` | request-scoped session | closed in `finally`; one session per request |
| `get_language` | language code from `Accept-Language` | falls back to the project default |
| `get_current_user` | authenticated principal | 401 on missing/expired token |
| `CommonDeps` | `db`, `lang`, `current_user` bundled | the standard for authenticated routes |
| `CommonDepsPublic` | `db`, `lang` | pre-auth routes only (login, reset password, OTP) |

Rules:

- Add a new dependency only when two or more routes need it; otherwise resolve it inside the service.
- Dependencies must not hold business logic; they resolve and validate context (who, which language, which session).
- Never construct a session yourself in a route; request it through the shared dependencies.
- For tests, every dependency is overridable through `app.dependency_overrides` (section 11.4), so keep them as plain callables.
