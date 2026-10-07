# FastAPI Guidelines (summary)

Short, generic rules used by the `task-plan` skill. The full standard is the
sibling skill `../fastapi-blueprint` — follow its chapters in `references/`;
this file only lists what a plan must not forget. A project's own guidelines
override paths and names here.

Stack: FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, MySQL/PostgreSQL.

## Default layout

```
app/
  api/<feature>/{router,schemas,service}.py
  repositories/     # all DB queries
  models/           # SQLAlchemy models
  integrations/     # external API clients
  core/             # settings, security, exceptions, responses, i18n
migrations/         # Alembic
tests/
```

## Layers (blueprint ch. 03, 04, 06)

- **Router**: thin. Validate via schemas, apply auth/permission dependency,
  call one service method, return `ApiResponse[T]`. No queries, no business
  logic.
- **Service** (`<Feature>Service`): business rules, transaction boundary,
  orchestration of repositories and integrations; raises `AppException`.
- **Repository** (`<Entity>Repository`): the only place with queries.
- **Model**: SQLAlchemy 2.x typed mappings; no business logic.

## Schemas (ch. 05)

- Pydantic v2, inherit `BaseSchema`; separate Request and Response schemas;
  never return ORM models or raw dicts.
- Validate at the edge (types, ranges, enums); never expose internal ids,
  hashes or secrets; mask/encrypt PII in responses.

## Responses and errors (ch. 04, 13)

- Success: `ApiResponse[T]`. Failure: `AppException(ErrorCode.X)` handled by
  one global handler. No bare `HTTPException`, no swallowed exceptions.
- User-facing text uses i18n message keys, never literals; add keys for every
  supported language.

## Database (ch. 07)

- Schema changes only through Alembic revisions with a working downgrade;
  consistent types/collation with referenced tables; indexes for new
  filters/joins.
- Transactions are explicit in the service; lock rows (`with_for_update`) or
  use idempotency keys for money, stock, seat/slot and attempt counters.
- Money is `Decimal` (never float); aggregates are recomputed, not blindly
  incremented. Timestamps are UTC from one clock helper.

## Security (ch. 08, 15)

- AuthN via dependency; authorization checks permission AND object ownership.
- Parameterized queries only; no secrets or PII in logs; config through
  settings, not `os.environ` scattered in code.
- External calls: timeout, bounded retry, error mapping, no blocking calls
  inside `async` routes.

## Style and quality (ch. 02, 10, 13, 14)

- Type hints everywhere, small single-purpose functions, no dead code, no
  magic strings (use enums/constants), reuse existing helpers first.
- Tests: unit tests for services, API tests for routes; cover happy, negative
  and edge paths.
- Git: branch/commit/PR format per ch. 12.

## Checklist for a new endpoint

1. Model/migration (if schema changes) with downgrade.
2. Repository method(s).
3. Request/Response schemas.
4. Service method with transaction and `AppException` errors.
5. Thin route with auth/permission dependency returning `ApiResponse[T]`.
6. Router registered.
7. i18n keys in all languages.
8. Tests (happy, negative, edge, permission).
9. PII, money and concurrency reviewed.
