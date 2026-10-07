# 4. API Design & Routing

## 4.1 Router file rules

- One module-level router per feature: `router = APIRouter(prefix="/<feature>", tags=["<Feature>"])`.
- Mount it in `app/main.py` (or `app/api/__init__.py`). Group related endpoints under one Swagger tag.
- Every route has:
  - `tags=[...]`
  - an authorization dependency unless the endpoint is deliberately public or pre-auth
  - a return annotation: `ApiResponse` or `ApiResponse[T]`
  - a docstring (`### Business Rules:` section on protected routes)
  - a one-line body delegating to a service

```python
@router.get("/dashboard/summary", tags=["Dashboard"])
async def dashboard_summary(
    deps: CommonDeps,
    query: Annotated[DashboardQuery, Depends()],
    _: Annotated[None, Depends(require_permission("dashboard:view"))],
) -> ApiResponse[DashboardSummary]:
    """Get dashboard summary data.

    ### Business Rules:
    - Only users with the `dashboard:view` permission can view it.
    """
    return await DashboardService(deps).summary(query)
```

## 4.2 Authorization contract

- Authentication (who is the caller) and authorization (what may they do) are enforced by dependencies in `app/core/deps.py`, such as `get_current_user` and `require_permission(...)` / `require_role(...)`. Never inline token parsing or role checks in a route body.
- Fail closed: missing or unknown permission means 403, missing or expired token means 401.
- Object-level checks (the caller owns this payment, attempt, interview slot, or booking) belong in the service, after loading the object.
- Scope limits (for example a list restricted to the caller's own records, or to their organisation) are applied in the service/repository from `current_user`, never from a client-supplied value.
- Client-supplied filters override configured defaults only when explicitly sent; defaults apply when the client sends nothing.
- If caching is combined with authorization, authorization runs first and the cache key includes the caller's scope.

## 4.3 Dependency aliases

| Alias | Use | Provides |
|---|---|---|
| `CommonDeps` | authenticated endpoints | `db`, `lang`, `current_user` |
| `CommonDepsPublic` | pre-auth: login, forgot/reset password, OTP | `db`, `lang` |

Never build `Depends(...)` by hand for these. Pass `request: Request` into the service only when headers, IP, or user-agent are needed (audit logging, 2FA, login activity, integration clients).

## 4.4 Parameters

- Group query/filter params in a request schema: `Annotated[SomeQuery, Depends()]`. Do not add a long list of loose query args.
- Lists use shared `PageParams` (`offset: int = 0`, `limit: int = 10` with a maximum, `search: str | None = None`).
- Body requests use a `...Request` schema directly. Identity (user id, tenant/organisation id of the caller) never comes from the body; take it from `current_user`.

## 4.5 Naming and URL conventions

- Resource-style paths, kebab-case for multiword (`/payments/{id}/refund`, `/exam-attempts/{id}/submit`, `/interview-slots`, `/trip-bookings`).
- HTTP verbs: `GET` read, `POST` create/action, `PUT`/`PATCH` update, `DELETE` remove. Follow the verb convention the project already uses for state changes.
- JSON is camelCase on the wire (alias generator in `BaseSchema`); Python stays snake_case.
- Function names are verbs in snake_case (`list_trip_bookings`, `submit_exam_attempt`).

## 4.6 Response envelope

Every endpoint returns `ApiResponse`:

```json
{ "status": "1", "statusCode": 200, "code": "SUCCESS", "message": "...", "data": { } }
```

Errors use the same envelope through global handlers in `app/core/exceptions.py` (see section 5.6). Never return a bare dict, list, or `JSONResponse` from a service. The one framework-level exception is a cache layer, which may return a `JSONResponse` carrying the same envelope.

## 4.7 Versioning and compatibility

- Don't rename or remove response fields on a live endpoint; add new fields.
- Breaking changes need a new version prefix (`/api/v2/...`) agreed with the lead; the old version stays until clients migrate.
- Record request/response changes clients must adopt in the project changelog (Added / Changed / Fix) with the ticket reference.

## 4.8 File and export endpoints

- File responses are served through the shared file helper; every file-serving route performs a per-resource permission check (owner, role, or signed URL). Never serve a path taken straight from the client.
- Export endpoints follow section 8.5 (password policy and safe filename).

## 4.9 Idempotency and safe retries

- Endpoints that move money, finalise an attempt, or call a third party must be safe to retry: guard with a status check under a row lock (section 7.5), accept an idempotency key where clients may retry, and return the existing result for a repeat call rather than executing twice.
- Document the idempotency behaviour in the route docstring's `### Business Rules:`.

## 4.10 Rate limiting and caching

- Apply rate limiting to abuse-prone public or pre-auth endpoints (login, OTP, registration).
- Cache **GET** responses only, with an explicit TTL and a distinct key prefix per resource family so a write invalidates only its own cache. Never cache per-user data under a shared key.
- Both must degrade gracefully when Redis is unreachable; don't make a request fail because a cache is down.

## 4.11 Router responsibilities (exhaustive)

A router does only: HTTP method, path, dependency injection, authentication/authorization, request schema, response type, HTTP status, and delegation to the service.

## 4.12 Router MUST NOT

- Contain business logic.
- Perform DB queries (simple or complex).
- Build large response dictionaries.
- Call more than one service/repository method to assemble a workflow.
- Hold long `if/else` business flows.

```python
# MUST NOT
@router.get("/bookings/{booking_id}")
async def get_booking(booking_id: int, deps: CommonDeps):
    booking = deps.db.execute(select(Booking).where(Booking.id == booking_id)).scalar()
    if booking.status == "x" and booking.total > 100:
        ...
    return {"id": booking.id, "status": booking.status}

# MUST
@router.get("/bookings/{booking_id}", tags=["Bookings"])
async def get_booking(deps: CommonDeps, booking_id: int) -> ApiResponse[BookingResponse]:
    """Get a booking."""
    return await BookingService(deps).get_booking(booking_id)
```

## 4.13 API standards checklist

| Standard | Rule |
|---|---|
| Naming | resource paths, kebab-case; verbs only for action endpoints (`/submit`, `/refund`) |
| Methods | `GET` read, `POST` create/action, `PUT`/`PATCH` update, `DELETE` remove; no state change on `GET` |
| Status codes | the envelope `statusCode` matches the HTTP status (200/201 success, 400, 401, 403, 404, 409 conflict, 422 validation, 500) and the `ErrorCode` bucket |
| Versioning | additive changes by default; a new version prefix only for breaking changes, agreed with the lead |
| Pagination | `PageParams`, `total_count`, capped `limit` |
| Filtering / sorting / search | typed fields on the request schema; whitelist sortable columns; escape search terms |
| Idempotency | money/status endpoints safe to retry (lock, re-check status, return existing result) |
| Request IDs | a request-id/correlation middleware should set and log an ID per request; don't invent per-route ids |
| OpenAPI | `tags`, docstring with `### Business Rules:`, typed request/response so Swagger is accurate |
