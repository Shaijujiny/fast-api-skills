# 18. Error Handling & Responses

One contract for every response, success or error. Reference implementation: `templates/fastapi-starter/app/core/exceptions.py`, tests in `tests/test_errors.py`. Related: 4.6 and 5.6 (envelope), 6.14 (domain exceptions), 13.11 (anti-patterns).

## 18.1 The response contract

Every endpoint returns the same envelope, including errors and framework errors (404, 405, 422).

```json
{ "status": "0", "statusCode": 409, "code": "CONFLICT_409", "message": "...localized...", "data": null, "requestId": "9f2c..." }
```

- `status`: `"1"` success, `"0"` error. `statusCode` repeats the HTTP status. `code` is the machine-readable reason clients branch on. `message` is for humans and is localized (i18n key, never hard-coded text).
- `requestId` is on every error and also in the `X-Request-ID` response header, so support can find the log line from a screenshot.
- `data` on errors is optional structured detail (for example which field), never internals.
- Never return a bare `{"detail": ...}`; the global handlers translate every framework error into the envelope.

## 18.2 Status code guide

| Status | Use | `code` |
|---|---|---|
| 200 / 201 / 204 | OK / created / no content | `SUCCESS` |
| 400 | Malformed request the schema cannot express | `BAD_REQUEST_400` |
| 401 | Missing, expired or invalid credentials (send `WWW-Authenticate`) | `AUTH_401_*` |
| 403 | Authenticated but not allowed (role, scope, inactive account) | `FORBIDDEN_403*` |
| 404 | Resource does not exist **or the caller may not know it exists** (avoid leaking IDs) | `NOT_FOUND_404` |
| 405 | Wrong HTTP method (keep the `Allow` header) | `METHOD_NOT_ALLOWED_405` |
| 409 | State conflict: duplicate, stale version, wrong state transition, DB integrity violation | `CONFLICT_409` |
| 413 | Body or upload too large | `PAYLOAD_TOO_LARGE_413` |
| 422 | Valid JSON but fails validation or a business rule | `VALIDATION_422`, `BUSINESS_422_*` |
| 429 | Rate limited (always send `Retry-After`) | `RATE_LIMITED_429` |
| 500 | Our bug; generic message only | `SYSTEM_500` |
| 502 / 503 / 504 | Upstream failed / we are shedding load / upstream timed out | `SERVICE_UNAVAILABLE_503` |

Pick one status for one situation and keep it. Do not return 200 with an error body.

## 18.3 Error code naming and catalog

- Format `<AREA>_<HTTP>[_<REASON>]`, upper snake case: `AUTH_401_INVALID_CREDENTIALS`, `BUSINESS_422_EMAIL_EXISTS`, `FORBIDDEN_403_USER_INACTIVE`.
- Codes live in one `ErrorCode` enum. Add a code only when a client needs to behave differently for it; otherwise reuse the generic code for that status.
- Codes are part of the public API: never rename or reuse one. Add a new code and deprecate the old.
- Keep a short catalog (code, status, when it happens, client action) in the project docs and update it in the same PR as the enum change.
- Domain flavors: fintech `BUSINESS_422_INSUFFICIENT_FUNDS`, `CONFLICT_409_DUPLICATE_PAYMENT`; assessment `CONFLICT_409_ATTEMPT_ALREADY_SUBMITTED`, `FORBIDDEN_403_ATTEMPT_CLOSED`; interview `CONFLICT_409_SLOT_TAKEN`; transport `CONFLICT_409_SEAT_TAKEN`, `BUSINESS_422_TRIP_DEPARTED`.

## 18.4 Where errors are raised and handled

| Layer | Does |
|---|---|
| Router | Nothing for errors; it only calls the service. |
| Service | Raises `AppException(status, ErrorCode, message)` for business failures, with the localized message. |
| Repository | Lets DB errors propagate; never swallows them and never returns `None` for "failed". |
| Global handlers | The only place that builds an error response (see 18.5). |

Rules: raise, do not return error objects; raise the most specific exception once, at the point you know the reason; do not catch `Exception` in routers or services unless you re-raise after cleanup.

## 18.5 Global handlers (all required)

| Exception | Response |
|---|---|
| `AppException` | its own status, code, message, data, headers |
| `RequestValidationError` | 422 `VALIDATION_422`, first validator message resolved through i18n |
| `HTTPException` (401, 403, 404, 405, 413, 429, 503, other) | mapped to the matching code; keeps framework headers (`Allow`, `Retry-After`, `WWW-Authenticate`) |
| `IntegrityError` | 409 `CONFLICT_409`; log the DB message, never send SQL or constraint names. This catches the race the service check missed. |
| `SQLAlchemyError` | 500 `SYSTEM_500` |
| `Exception` | 500 `SYSTEM_500`; traceback to logs only |

- A 500 never contains an exception message, SQL, file path, stack trace or any user data.
- The unhandled-error response is produced outside the request middleware, so the handler must set `X-Request-ID` itself (the starter does).
- The session dependency rolls back on any exception before the handler runs.
- Validators raise `ValueError("<message_key>")` so the client gets a localized message, not Pydantic internals.

## 18.6 Client contract

- Clients branch on `code`, not on `message` text.
- Retry only idempotent requests, and only on 429, 502, 503, 504 and network errors, with backoff and jitter; honor `Retry-After`. Never blindly retry 4xx.
- Payment or booking POSTs carry an idempotency key so a retry cannot double-charge or double-book (chapter 7 and 17.1).
- Show `message` to users; log `requestId` and include it in support requests.

## 18.7 External failures

- Wrap provider errors in the integration client and map them to your own codes (provider down 503, provider rejected 422/409). Never forward provider messages, bodies or credentials.
- Timeouts are set on every outbound call; a timeout is a 504/503 for the caller, logged with the provider name and request id.
- Partial failure (some items of a batch failed) returns 200 with per-item results, or 207-style data in the envelope, never a single misleading status.

## 18.8 Logging errors

- 4xx: log at INFO/WARNING without a traceback (expected). 5xx: log at ERROR with traceback and `request_id`.
- Never log passwords, tokens, OTPs, full card or ID numbers, or request bodies of auth and payment routes (9, 8).
- Alert on 5xx rate and on spikes of 401/403/429 (auth probing).

## 18.9 Tests (required)

One test per handler, asserting the envelope keys, status, `code`, `requestId` equal to `X-Request-ID`, and that a 500 leaks nothing. See `tests/test_errors.py` in the starter. Also test one localized error per supported locale and that `AppException` with `data` serializes.

## 18.10 Review checklist

- [ ] New failure has a status from 18.2 and a code per 18.3 (reused if no client needs a new one)
- [ ] Message is an i18n key present in every locale
- [ ] No error path returns 200 or a bare `detail`
- [ ] No internals, SQL, provider text or PII in any response
- [ ] Race on a unique/state check also ends in 409, not 500
- [ ] 429 sends `Retry-After`; 401 sends `WWW-Authenticate`
- [ ] Handler test added or updated
