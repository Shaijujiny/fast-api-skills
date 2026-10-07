# 6. Business Logic & Data Access

Class and module names are defaults (`Service`, repository classes in `app/repositories/`, `ApiResponse`, `AppException`, `ErrorCode`). Follow the project's own equivalents if they exist.

## 6.1 Anatomy of a service method

```python
async def cancel_booking(self, payload: BookingCancel) -> ApiResponse[None]:
    # 1. load + lock (repository), 404 if missing
    booking = self.bookings.get_by_id(payload.booking_id, lock=True)
    if booking is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.NOT_FOUND, message=self.message.booking_not_found,
        )
    # 2. authorize at object level (does this user own / may they act on this record?)
    # 3. validate business rules (status transition, limits) -> 4xx with localized message
    # 4. mutate through repositories
    # 5. commit explicitly (the service owns the transaction)
    self.db.commit()
    # 6. audit log, then build the response
    return ApiResponse(status_code=status.HTTP_200_OK, code=ErrorCode.SUCCESS,
                       message=self.message.success, data=None)
```

Order matters: load/lock, authorize, validate, mutate, commit, audit, respond. Keep each phase in a small private method so the public method stays under the complexity limit.

## 6.2 Complexity and structure

- Max cyclomatic complexity 10 (Ruff `C901`); split larger methods into `_private` helpers named for the step.
- One public method per use case; helpers are private and take explicit arguments.
- Prefer early `raise` (guard clauses) over deep nesting.
- Pure calculation (fees, pricing, scoring, due dates) goes in a shared utility or domain module and is called from every site. Never duplicate a formula; copied logic gets fixed in one place and missed in the others.

## 6.3 Data access rules

- **Session:** request scope uses the session injected by a dependency (`get_db`). Outside a request (scheduler, script, worker) use a context manager such as `with session_scope() as db:`. Follow the project's sync or async choice consistently; never mix.
- Queries live only inside repository classes. A service never builds queries or calls `session.execute` / `session.query` directly.
- All values go through bound parameters via the ORM; never build SQL with f-strings or concatenation. For rare raw SQL use `text()` with bind params.
- Select what you need. For large lists avoid loading full rows and use pagination plus a separate count.
- Avoid N+1: join or `selectinload` inside the repository instead of calling a method per row in a loop.
- Escape or parameterize `LIKE` search input.

## 6.4 Applying scope and filters

- Identity and scope come from the authenticated user (`current_user`) and their roles/permissions (tenant, owner, assigned group). Never trust an id supplied in the body to establish ownership.
- Reuse the shared scoping helpers rather than writing a new ownership check per endpoint.
- Permission-based default filters are applied by the shared permission dependency/decorator; do not re-implement defaulting in the service.

## 6.5 Caching and secondary stores (optional)

- Redis (if used) is for caches, rate limits, and distributed locks, not the source of truth. Every cached value needs a TTL and a rebuild path from the database.
- Use namespaced keys (`app:feature:id`) and never cache PII or secrets unencrypted.
- If a project uses a document store or other secondary store, keep that logic in its own repository, make writes idempotent upserts with a stable key, and remember there may be no multi-record transaction: design for safe re-runs.

## 6.6 External API calls

- Wrap each provider in a small client class in `app/integrations/` that owns the base URL, headers, endpoints, and Pydantic request building.
- Use one shared HTTP transport (for example `httpx.AsyncClient`) with explicit timeouts and response typing. Pass a short `timeout` when a DB row lock is held across the call.
- Base URLs and keys come from settings. Never hard-code a URL or key.
- Treat a non-2xx or timeout as a handled failure: roll back local state that depended on it, log without secrets, and raise `AppException`.
- Don't call a slow provider inline for something the user doesn't need to wait on; hand it to a background task, queue, or scheduler.

## 6.7 Files

- All file reads and writes go through one storage abstraction (`app/core/storage.py`, local or cloud object storage selected by config). Never open storage paths directly.
- Validate uploads (type, MIME, size, structure) before saving.
- Generated documents (PDF, XLSX) live in one module; reuse it.

## 6.8 Localization

- `self.message.<key>` only. Add the key to **every** supported language catalog with identical key names; a missing translation falls back to the default language, never to a raw key.
- The language comes from the `Accept-Language` header (or the user's stored preference) through one shared dependency, with a default; the service already has `self.lang`.
- Notification and email text is localized too; keep templates in one place and use the shared notification helpers.

## 6.9 Audit logging

- State-changing actions (especially admin, money, and permission changes) are audit-logged through the audit log repository. Include the actor from `current_user`, never from the body.
- Never put raw PII or secrets in an audit payload; store ids and changed field names.

## 6.10 Time and configuration

- "Now": one shared clock helper returning timezone-aware UTC. Do not scatter `datetime.now()` or `utcnow()` in feature code.
- Settings: one typed settings object (`pydantic-settings`) from the environment. Never read `os.environ` in feature code. Add new env vars to `.env.example`.

## 6.11 Responsibilities by layer

**Service** handles: business rules, workflow orchestration, validation that needs DB or business context, repository calls, integration calls, transaction coordination, and domain errors (`AppException`).

**Repository** handles: queries, inserts, updates, deletes, query composition, row locks, and persistence operations. It returns rows or tuples. It does **not** commit (see 7.9), build `ApiResponse`, or call external APIs.

```
Router
  ↓
Service
  ↓
Repository
  ↓
Database
```

## 6.12 Avoid: the router doing everything

```
Router
  ↓ DB query
  ↓ business calculation
  ↓ external API call
  ↓ DB commit
```

All of that belongs in the service (and the query in a repository). A router that does this is the "fat router" anti-pattern.

## 6.13 Keeping layers honest

- **God service:** a service class that handles unrelated use cases. Split by responsibility (`BookingService`, `RefundService`).
- **God repository:** a repository accumulating unrelated reporting queries. Group methods by the entity's own concerns; put cross-entity reporting in a dedicated reporting repository or service.
- Don't call a service from a repository (wrong direction). Don't import a router anywhere.
- One workflow = one service method that orchestrates; the steps are private helpers, each doing one thing.
- Domain errors are raised in the service with `AppException`; repositories return `None`/empty and let the service decide the error.

## 6.14 Domain exceptions

The service speaks the domain through `AppException`. Pick the status and `ErrorCode` bucket together:

| Situation | `status_code` | `ErrorCode` bucket | Message |
|---|---|---|---|
| record not found | 404 | `NOT_FOUND_*` | `self.message.<entity>_not_found` |
| not allowed / out of scope | 403 | `FORBIDDEN_*` | `self.message.unauthorized` |
| not logged in / bad token | 401 | `AUTH_401_*` | handled by the auth dependency |
| business rule violated (wrong status, slot taken, limit exceeded) | 422 | `BUSINESS_*` | a specific localized key |
| malformed or invalid input outside the schema | 400 | `BAD_REQUEST_*` | `self.message.<key>` |
| provider or unexpected system failure | 500/502 | `SYSTEM_*` | a generic localized key, no internals |

```python
if attempt.status != AttemptStatus.IN_PROGRESS:
    raise AppException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code=ErrorCode.BUSINESS_RULE_VIOLATED,
        message=self.message.attempt_already_submitted,
    )
```

Rules:

- Raise at the point of detection, before any write.
- Use one precise message key per rule; don't reuse a vague one for several failures.
- Never catch `Exception` just to re-wrap it: catch the specific error (`IntegrityError`, `httpx.HTTPError`, `ValidationError`), `rollback()` if needed, and raise the matching domain error with `from exc`.
- Don't swallow errors to return a "success" envelope.
- Verify the `ErrorCode` member exists before using it; don't invent codes.
