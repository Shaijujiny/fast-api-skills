# 13. Code Generation & Anti-Patterns

Use this when you (or an AI assistant) generate new code. The goal is output that is indistinguishable from the surrounding code and passes review the first time.

## 13.1 Generation workflow

1. **Read first.** Open the closest existing feature and the model(s) involved. Copy its shape, not a generic FastAPI tutorial's.
2. **Plan layer by layer** (write the plan before any code): schemas, repository, service, router, registration, i18n messages, DB migration, security, tests.
3. **Write in dependency order:** schemas, repository method, service method, router, router registration, message keys, Alembic migration, changelog/docs.
4. **Verify:** lint, type check, run tests, exercise the endpoint, re-read the diff.
5. **Report honestly:** say what was verified and what wasn't.

## 13.2 Checklist for a new endpoint

1. **Schemas** (`schemas.py`): `...Request` / `...Response` subclassing `BaseSchema`; `Decimal` for money, timezone-aware datetimes, enums as `str` `Enum`, masking/encryption via `Annotated` aliases where relevant.
2. **Repository** (`repository.py`): query/lock helper taking the session; `lock: bool = False` (maps to `with_for_update()`) if read-then-write.
3. **Service** (`service.py`): `async` method, dependencies injected in `__init__`, i18n message keys, `AppException` on error, explicit `commit()` / `rollback()` owned by the service, audit log for state changes.
4. **Router** (`router.py`): tag, `Depends(require_permission(resource, action))`, docstring with business rules, `response_model=ApiResponse[T]`, one-line delegation to the service.
5. **Register** the router in the app's router aggregator with the right prefix and tags.
6. **Messages:** add the key to **every** supported locale file.
7. **DB:** new/changed table gets an Alembic migration (additive, safe for existing data, collation matching referenced tables).
8. **Security:** mask/encrypt sensitive fields; object-level scope check; export policy; storage access through the file-storage abstraction.
9. **Docs:** changelog/API docs entry; `.env.example` for new variables.
10. **Quality:** tests added, lint and type check clean.
11. **Commit:** follow the team's commit and branch convention (type, ticket reference, short description).

## 13.3 Reference skeleton

Schema (fintech example):

```python
class PayoutApproveRequest(BaseSchema):
    """Approve-payout request."""

    payout_id: UUID
    note: str | None = Field(None, max_length=500)


class PayoutApproveResponse(BaseSchema):
    """Approve-payout response."""

    status: PayoutStatus
    amount: Decimal
    processed_at: datetime
```

Router:

```python
@router.put("/payouts/{payout_id}/approve", tags=["Payouts"],
            response_model=ApiResponse[PayoutApproveResponse])
async def approve_payout(
    payout_id: UUID,
    payload: PayoutApproveRequest,
    user: CurrentUser = Depends(require_permission("payout", "edit")),
    service: PayoutService = Depends(get_payout_service),
) -> ApiResponse[PayoutApproveResponse]:
    """Approve a payout.

    ### Business Rules:
    - Requires `edit` on the `payout` resource.
    - Idempotent: an already processed payout returns its existing result.
    """
    return await service.approve(payout_id, payload, user)
```

Service (shape only): load with `lock=True`, 404 if missing, object-level scope check, status guard, external call with a short timeout, mutate, `commit()`, audit, return `ApiResponse(...)`.

## 13.4 Anti-patterns

### Structure

- Business logic, branching, or queries in a router.
- Raw `session.execute` / `session.query` in a service (it belongs in a repository).
- Returning a dict, list, ORM object, or `JSONResponse` from a service instead of `ApiResponse[T]`.
- A feature missing one of `router.py` / `schemas.py` / `service.py` / `repository.py`, or putting DTOs in the router.
- Importing a router from another feature, or circular imports at module top (use function-local imports or restructure).
- Duplicating a formula or query instead of calling the shared helper.

### Schemas and responses

- Bare `BaseModel` instead of the shared `BaseSchema`; raw `dict` / `Any` for structured payloads.
- Hand-written camelCase attribute names when the schema base already provides an alias generator.
- `float` for money; skipping decimal precision handling.
- Masking or encrypting inline in the service instead of a reusable `Annotated` type.
- Raising `HTTPException` directly or building ad-hoc error JSON instead of `AppException` with an `ErrorCode`.
- Mismatched HTTP status and `ErrorCode` category (a 404 carrying a validation code).
- Hard-coded user-facing strings, or a message key added to only some locales.

### Database

- Missing `commit()`, or `commit()` inside a loop for one logical unit.
- Continuing to use a session after a failed flush without `rollback()`.
- String-built SQL.
- Read-modify-write on money, status, or cached counters without `with_for_update()`; decrementing a cached counter; trusting a status read before the lock.
- Renaming or retyping a column in place without a migration plan; wrong collation on a new table; a model change without an Alembic migration.
- Relying on `rowcount == 0` to detect "no change" (on MySQL with `FOUND_ROWS`, identical-value updates count as matched).
- N+1 queries, unpaginated lists, `LIKE '%x%'` on huge tables without an index plan.

### Security

- Taking identity or the acting entity (user, tenant, owner) from the request body.
- A route without a permission dependency (unless on a deliberate public allowlist).
- Skipping the object-level scope check because the permission passed.
- Mixing encryption schemes on one field.
- Logging PII, secrets, tokens, or full request bodies; returning stack traces or SQL in `message`.
- Exports without the agreed protection policy; trusting a client-supplied filename or path.
- Reading `os.environ` in feature code instead of the settings object; widening CORS or duplicating security headers per route.
- Failing **open** when a risk, compliance, 2FA, or provider check is unavailable.

### Runtime

- `time.sleep`, heavy CPU, or slow third-party calls inline in a handler.
- An external call with a long or default timeout while holding a DB lock.
- A scheduled job without a distributed lock, a stable `id`, and replace-on-restart semantics.
- Starting background tasks without keeping a reference (the task can be garbage-collected mid-run).
- Hard failure when the cache (Redis) is down.

### Process

- Reformatting or reordering unrelated code in a feature change; round-tripping a data file through a serializer.
- Committing `.env` values, dumps, caches, or generated files.
- Commit messages without the agreed type/ticket format; force-push to shared branches; `--no-verify`.
- A changelog entry that describes the implementation instead of the effect.
- Copying a known deviation from the codebase into new code.

## 13.5 Good patterns to copy

- Repository query helper with an opt-in row lock: `OrderRepository.get_by_id(session, order_id, lock=True)`.
- Scheduled-job lock: acquire (`SET NX EX`), run, release by compare-and-delete.
- One integration client class per provider, Pydantic payloads dumped `by_alias=True`, explicit timeouts.
- A shared helper to apply default scope filters, reused in flows outside the dependency (exports, reports).
- A `fire_and_forget(coro)` helper that keeps a reference to background tasks.

## 13.6 Prompting an AI assistant well

Include in the request: the ticket reference, the endpoint and verb, the entities/tables involved, who may call it (resource and action permission), the money/PII fields, the DB change, expected errors, and "follow the `fastapi-blueprint` skill and mirror the closest existing feature". Review the output against section 14 before accepting it; an assistant will happily invent column names, error codes, or message keys that don't exist, so verify each against the code.

## 13.7 Code generation MUST

- Inspect existing code first (closest feature, the model, the schemas).
- Follow the existing architecture and reuse existing utilities.
- Use Pydantic schemas and full type annotations.
- Add tests appropriate to the risk.
- Preserve existing behaviour.
- Handle errors with `AppException`, not silent passes.
- Follow the transaction rules (commit once at the end, rollback on failure) and the security rules.
- Run lint and tests where possible, and report exactly what was run.

## 13.8 Code generation MUST NOT

- Return raw dict responses when a schema exists or should.
- Put business logic in routers.
- Commit midway through a workflow.
- Use floats for money.
- Hard-code secrets, URLs, or thresholds.
- Duplicate an existing utility.
- Add a dependency or a design pattern without a concrete need.
- Suppress lint errors blindly (`# noqa` without a code and reason).
- Catch bare `Exception` without proper handling (log, roll back, re-raise or map to `AppException`).
- Invent column names, error codes, message keys, or endpoint paths; verify each in the code.
- Claim tests passed unless they were executed.

## 13.9 Anti-pattern gallery

**Fat router**

```python
@router.post("/repay")
async def repay(payload: RepayRequest, session: Session = Depends(get_session)):
    row = session.query(Loan).filter_by(id=payload.id).first()
    row.paid = row.paid + payload.amount           # float-ish math, no lock
    await accounting_client.create_invoice(...)    # external call in router
    session.commit()
    return {"ok": True}                            # raw dict
```

Fix: thin route; service loads with `lock=True`, validates, mutates, commits once; response is `ApiResponse[RepayResponse]`.

**God service / god repository:** one class with dozens of unrelated methods. Split by use case.

**Raw dictionary response:** `return {"id": ..., "name": ...}`. Use a response schema.

**N+1 query**

```python
for booking in bookings:
    driver = session.get(Driver, booking.driver_id)   # one query per row
```

Fix: join or batch-load in the repository.

**Commit-per-operation:** several `commit()` calls inside one workflow, leaving partial state on failure.

**Blocking async code:** `time.sleep(5)` or a slow third-party call inline in an `async def`. Use a scheduler/worker or `fire_and_forget`.

**Unvalidated external API response:** using `response.json()` fields directly. Parse into a Pydantic model.

**Hard-coded configuration:** URLs, keys, thresholds, or limits as literals. Use the settings object or configuration tables.

**Duplicate business logic:** the same formula (for example early-settlement or late-fee calculation) pasted into three call sites. One helper, all sites call it.

**Over-engineering:** a strategy hierarchy or an event bus for one query or one `if`. Use the plain version until a second use exists.

**Lock held across a slow call:** `with_for_update()` then an HTTP call with a long default timeout.

**Lost update:** read a cached counter, add in Python, write back. Recompute from source rows or update atomically under a lock.

## 13.10 God repository and how to spot it

A repository (or model class) can grow into a dumping ground:

- dozens of unrelated methods in one class
- reporting and dashboard aggregates mixed with the entity's own CRUD
- helpers that call other services, send notifications, or commit
- 1,000+ line files where each query is a one-off

Fix: keep a repository's methods to that entity's persistence and lock/query needs; move cross-entity reporting into a named summary/reporting repository or service; keep notifications and external calls in the service.

## 13.11 Exception handling anti-patterns

```python
# MUST NOT: swallows everything, session may be poisoned, caller thinks it worked
try:
    do_work()
    self.session.commit()
except Exception:
    pass

# MUST NOT: re-wraps blindly and loses the cause
except Exception as e:
    raise AppException(..., message=str(e))     # leaks internals

# MUST
try:
    do_work()
    self.session.commit()
except IntegrityError as exc:
    self.session.rollback()
    raise AppException(
        status_code=status.HTTP_409_CONFLICT,
        code=ErrorCode.DUPLICATE_RECORD,
        message_key="errors.duplicate_record",
    ) from exc
```
