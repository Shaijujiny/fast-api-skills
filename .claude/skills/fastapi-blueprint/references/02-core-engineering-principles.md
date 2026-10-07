# 2. Core Engineering Principles

Each principle has a rule, the reason, and what it looks like in practice.

## 2.1 Follow the existing conventions

- **Rule:** write code that reads like the code around it: naming, comment density, docstring style, idiom.
- **Why:** a codebase with many modules stays maintainable only if modules are interchangeable to read.
- **How:** before writing, open the closest existing feature and mirror its router, service, and schema shape. Reuse helpers in `app/utils/` and `app/core/` before writing new ones.

## 2.2 Thin routers, services own logic

- **Rule:** a route validates input, applies authorization, and delegates in one line. Branching, orchestration, and external calls belong in the service.
- **Why:** routers can then be read as a table of endpoints, and logic is testable without HTTP.

## 2.3 Data access lives in repositories

- **Rule:** SQLAlchemy queries (`select(...)`, `session.execute(...)`) appear only in repository classes under `app/repositories/`. Services call repository methods and shape the response.
- **Why:** one place per entity for query logic, filters, joins, and row locks.
- **Example:** `PaymentRepository.get_by_id(db, payment_id, for_update=True)`.

## 2.4 Pydantic everywhere, never raw dicts

- **Rule:** request bodies, responses, and payloads passed between layers are `BaseSchema` subclasses.
- **Why:** validation, camelCase aliasing, masking, and rounding happen declaratively in one place.
- **Exception:** a payload whose shape is dictated by a third party can be built with `model_dump(by_alias=True)` from a Pydantic model; never hand-build the dict.

## 2.5 Localize all user-facing text

- **Rule:** messages come from i18n message keys (one catalogue per supported language, e.g. en, ar, hi), never hard-coded strings. A new key must exist in every supported language catalogue.
- **Repo reality:** hard-coded error strings in services or dependencies exist in some projects. Do not copy them.

## 2.6 Explicit transactions

- **Rule:** one transaction per request/use case, owned by the service. Commit once after the write succeeds; roll back when a handled failure could leave a half-written session.
- **Why:** a poisoned session breaks every later query in the same request.

## 2.7 Money is `Decimal`

- **Rule:** never `float` for amounts, fees, rates, prices, fares, or balances. Use `Decimal` in code and `NUMERIC`/`DECIMAL` in the DB; round at the response boundary with a shared annotated type.
- **Why:** float drift in totals is a reconciliation bug that surfaces months later.

## 2.8 Protect data by default

- **Rule:** mask PII in responses and logs, encrypt sensitive fields at rest, never log secrets or tokens.
- **Why:** our apps hold national IDs, phone numbers, bank data, candidate answers, interview recordings, and location data.

## 2.9 Don't block the event loop

- **Rule:** `async def` handlers must not call blocking code (sync DB driver, `time.sleep`, CPU-heavy work, slow third-party SDKs) directly. Use an async driver, or plain `def` routes / a thread pool for blocking work.
- **How:** put long jobs in a scheduler or task queue, and use background tasks for non-critical side effects. Set short timeouts on integration clients, especially while a DB lock is held across the call.

## 2.10 Assume concurrency

- **Rule:** two requests, two workers, or a request plus a background job can touch the same row at once. Design writes accordingly (section 7.5).
- **Example:** two users booking the last trip seat, two submits of the same exam attempt, or a double-clicked payment: use row locks, unique constraints, or optimistic versioning.

## 2.11 Smallest correct diff

- **Rule:** change only what the task needs. Don't reformat unrelated lines or reorder imports in files you only touch lightly.
- **Why:** small diffs review faster and merge cleanly across branches.

## 2.12 Prefer the boring solution

- No new dependency when `app/utils` already covers the need.
- No abstraction until a second caller exists.
- A comment explains **why** (a business rule, a ticket, a constraint), not what the code does.

## 2.13 Principle catalogue and how each applies

| Principle | Meaning in practice |
|---|---|
| SOLID | one reason to change per class (`PaymentService` vs `RefundService`); depend on abstractions you already have (shared deps, integration clients) |
| DRY | one formula and one query per rule (late fee, score total); call the shared helper |
| KISS | the straightforward query or method over a clever generic one |
| YAGNI | no abstraction, flag, or extension point without a second real use |
| Separation of concerns | HTTP in routers, rules in services, SQL in repositories, formatting in schema aliases |
| Single responsibility | a function does one step of the flow; split at complexity 10 |
| Explicit over implicit | explicit commit, explicit lock flag, explicit timeouts and status codes |
| Composition over inheritance | services compose repositories and clients; inherit only `BaseSchema`/ORM `Base` and existing bases |
| Type safety | full annotations, `Mapped[...]`, `Decimal`, `Enum`, Pydantic everywhere |
| Immutability | treat request schemas and constants as read-only; don't mutate inputs |
| Fail fast | validate at the schema, then guard clauses at the top of the service; raise before any write |
| Defensive programming | check object-level ownership (the caller may only touch their own attempt, slot, booking), status after locking, and external responses; fail closed on security checks |
| Backward compatibility | add fields, don't rename or remove; record changes in the changelog |

## 2.14 Mandatory layering

```
Router → Service → Repository → Database
           ↓
      Integration client (external APIs)
```

- Each layer has exactly one responsibility.
- No duplicated business logic; no giant functions or classes.
- No premature abstraction.
- Reuse existing utilities before writing new ones.
