# Merge Request Review Checklist

Use when reviewing or self-reviewing a PR. For a deep per-file review see the `app-code-review` skill; standards live in `fastapi-blueprint` chapter 14. Tick each item or mark N/A (state why). Block the PR on any ❗ item.

Severity: ❗ blocker — must be fixed before merge. Unmarked — standard item; fix or justify.

## 0. PR hygiene

- [ ] Branch follows `feature/<TICKET-ID>-...` / `bugfix/<TICKET-ID>-...`, targets the staging branch.
- [ ] Every commit matches `^[A-Z]+-[0-9]+ (feat|fix|refactor|chore|docs|test): .+` ❗
- [ ] PR is scoped to one ticket; no unrelated drive-by changes.
- [ ] No commented-out code, debug `print`, or leftover TODO without a ticket.
- [ ] No secrets, tokens, real customer data, or `.env` values committed. ❗

---

## 1. Architecture & layering

- [ ] New feature lives under `app/api/<feature>/` as `router.py` / `schemas.py` / `service.py`.
- [ ] Router is thin — validate + `@privileges` + delegate; no business logic or DB queries. ❗
- [ ] Business logic is in the service (`<Feature>Service`), not the router or schema.
- [ ] Router registered in the router registry in `app/api/__init__.py`.
- [ ] Shared primitives imported from the right place (`schemas_utils.py` / `common_utils.py` / `constants/annotations.py`) — not redefined locally. ❗
- [ ] Reuses existing `app/utils/...` helpers instead of re-implementing (crypto, file, cache, export, calc).
- [ ] No cross-layer leakage — no raw ORM rows or store documents returned to the client.

## 2. Routers

- [ ] Route returns `ApiResponse` / `ApiResponse[T]` and has a docstring. ❗
- [ ] Correct dependency alias: `COMMON_DEPS` (authed) vs `common_deps_half` (pre-auth).
- [ ] `request: Request` injected only when the service needs headers/IP/user-agent.
- [ ] Query/filter params grouped into a schema via `Annotated[…, Depends()]` — not loose query args.
- [ ] Endpoints grouped with `tags=[...]`; path/verb RESTful and consistent with the area prefix.
- [ ] Privileged routes document `### Business Rules` in the docstring.

## 3. Authorization & authentication ❗

- [ ] Every protected endpoint has `@privileges(<Menu>, <Access>)`.
- [ ] Correct access level — reads use `VIEW`, mutations use `EDIT` (or `VIEW_DOCUMENT` / `DOWNLOAD_DOCUMENT`).
- [ ] No endpoint silently exposes data without an auth/permission check.
- [ ] Identity read from `current_user` (`JWTPayloadSchema`), not the request body.
- [ ] Object-level checks present; constrained privileges honour the permission scope map.
- [ ] Pre-auth flows (login/forgot/reset/OTP/2FA) do their own checks inside the service.

## 4. Schemas / DTOs

- [ ] Request/response bodies are Pydantic schemas, not raw dict/JSON literals. ❗
- [ ] DTOs subclass `BaseSchema` (not bare `BaseModel`).
- [ ] Naming: `...Request` for inputs, `...Response` for outputs; closed choice sets use str-`Enum`.
- [ ] Fields fully typed; `default_factory` for list/dict defaults; validators where needed.
- [ ] Field transforms use the `Annotated` aliases (`DEC_VAL2`, `UI_ENCRYPT_STR`, `MASK_*_STR`, `LOCAL_DATETIME`, `DATE_STR`) — not hand-rolled serializers. ❗
- [ ] Python fields stay snake_case; camelCase comes from the alias generator.
- [ ] List endpoints take `GetAllQueryParams` via `Depends()`; response carries `total_count`.
- [ ] No sensitive field (raw PII, secrets, internal IDs) leaked in a response model.

## 5. Database & models

- [ ] New tables declare charset/collation in `__table_args__`. ❗
- [ ] ORM classes use `Mapped[...]` + `mapped_column(...)`.
- [ ] Existing physical column names preserved unless a migration renames them.
- [ ] FKs / `CheckConstraint` / `Enum` declared where appropriate.
- [ ] Money uses `Decimal` (`DECIMAL(18,2)`, non-negative check) — never float. ❗
- [ ] Model query helpers take the sync `db: Session`, keep orchestration in the service, use function-local imports.
- [ ] Queries parameterized through the ORM — no string-built SQL. ❗
- [ ] No N+1; eager-load where it matters.
- [ ] Writes `commit()` explicitly; `rollback()` on handled error; no partial-state leaks. ❗
- [ ] Jobs/scripts use the context-managed session (`get_ctx_db()`), not the request dependency.
- [ ] Schema change has a matching migration entry (Alembic or the project's SQL changelog). ❗

## 6. Document store (if used)

- [ ] Documents modelled as Pydantic subclassing `BaseSchema` — no raw dicts. ❗
- [ ] Collections obtained via `DocumentStoreSingleton().get_collection(name[, index])`.
- [ ] Writes idempotent — stable key + `UpdateOne(..., upsert=True)` / `bulk_write(ordered=False)`.
- [ ] Timestamps stored UTC, surfaced in the app timezone (`LOCAL_DATETIME`).
- [ ] No reliance on multi-document transactions.

## 7. Responses & error handling

- [ ] Success returns `ApiResponse` with correct `status` / `status_code` / `code` / `message` / `data`.
- [ ] `data` is a Pydantic model or `None` — never a raw dict.
- [ ] Errors raise `AppException` with a semantic `ErrorCode` — no ad-hoc JSON errors. ❗
- [ ] `ErrorCode` bucket matches the HTTP status.
- [ ] No bare `except:` / silent swallow.
- [ ] Edge cases handled: empty result, not-found, duplicate, unauthorized, validation failure.

## 8. Localization

- [ ] User-facing text resolved via `self.message.<key>` — no hard-coded strings. ❗
- [ ] New copy added to every locale bundle with matching attribute names.
- [ ] `self.lang` threaded through; no English-only assumptions.

## 9. Security & data protection ❗

- [ ] Correct cipher: the at-rest cipher for stored values; the UI cipher / `UI_ENCRYPT_STR` for values sent to the UI.
- [ ] at-rest→UI moves go through `UI_ENCRYPT_STR` (or manual decrypt → re-encrypt) — ciphers never mixed.
- [ ] Passwords/secrets hashed, never logged or returned.
- [ ] PII masked via `MASK_*_STR` in responses and logs.
- [ ] Export policy followed as defined for the project (protected vs. unprotected formats).
- [ ] File I/O through `FileManager`; serving adds a per-module check.
- [ ] No CORS origin / trusted host widened outside config/DB settings.
- [ ] Security headers not duplicated per-route.

## 10. Code quality

- [ ] `ruff check` passes clean — no new blanket ignores. ❗
- [ ] Line length ≤ 120; numpy-style docstrings on public functions/classes.
- [ ] Cyclomatic complexity ≤ 10.
- [ ] Full type annotations on signatures.
- [ ] Names clear and consistent; no dead or duplicated code.

## 11. Concurrency, performance, cross-cutting

- [ ] `async` used correctly — DB calls are sync by design, but no avoidable blocking stalls the event loop; external async calls awaited.
- [ ] Logging via `get_logger(__name__)`; no PII/secrets in messages.
- [ ] "Now" comes from `Constants.current_time()`; no naive `datetime.now()`.
- [ ] Scheduler jobs in lifespan with stable `id` + `replace_existing=True` (`max_instances=1` for long jobs); body uses `get_ctx_db()`.
- [ ] Config from the typed settings object; no direct `os.environ`; new vars in `.env.example`. ❗
- [ ] Cache/rate-limit degrades gracefully if Redis is down.

---

## 12. Correctness & verification

- [ ] Change does what the ticket asks; acceptance criteria met.
- [ ] Backward compatible — no breaking change to an existing response shape/contract without coordination. ❗
- [ ] Tested (or covered) for the happy path and key failure paths.
- [ ] No regression in adjacent flows touched by the change.
