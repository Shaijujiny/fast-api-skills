# 11. Automation Testing

> This section is the standard for automated tests in every FastAPI service. If a project has no harness yet, adding it is a separate change; don't fold it into a feature PR.

## 11.1 Tooling

| Need | Tool |
|---|---|
| Runner | `pytest` (plus `pytest-asyncio`, `pytest-cov` in a dev requirements file, not production) |
| HTTP client | FastAPI `TestClient` (needs `httpx`), or `httpx.AsyncClient` with `ASGITransport` for async |
| Mocks | `unittest.mock` / `pytest-mock`; `respx` for `httpx`, `aioresponses` for `aiohttp` |
| Redis | `fakeredis` |
| Time | `freezegun` or an injected clock |
| Coverage | `pytest --cov=app --cov-report=term-missing` |

Configure Ruff to relax assert and docstring rules for `tests/`.

## 11.2 Suggested layout

```
tests/
├── conftest.py               # app, client, db session, user/permission factories, dependency overrides
├── factories.py              # build models/entities with sane defaults
├── unit/
│   ├── test_pricing_utils.py
│   ├── test_crypto_utils.py
│   └── test_masking.py
├── repositories/             # repository tests against a real test DB
├── api/
│   ├── test_payments_router.py
│   ├── test_exam_attempts_router.py
│   └── ...
├── concurrency/
└── scheduler/
```

Test pyramid: many fast unit tests, a solid layer of repository tests on the real database engine, and a thinner layer of endpoint tests.

## 11.3 Test database

- Use a **dedicated test database** on the same engine and major version as production (MySQL 8 or PostgreSQL), never dev, QA, or prod. Prefer a container (docker-compose or a CI service container).
- Create the schema by running **Alembic migrations** (`alembic upgrade head`) at least in CI, so migrations are tested too. `Base.metadata.create_all` is acceptable for fast local runs, but must use the same collation/charset as the target server.
- Isolation per test: wrap each test in a transaction and roll back, or truncate touched tables. Don't let tests depend on leftover rows.
- SQLite is not an acceptable substitute for repository, locking, or money tests: `with_for_update`, collation, and `DECIMAL` behave differently.

## 11.4 Core fixtures (`conftest.py`)

```python
@pytest.fixture
def db_session():
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

@pytest.fixture
def client(db_session, current_user):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_language] = lambda: "en"
    yield TestClient(app)
    app.dependency_overrides.clear()
```

- `current_user` is built by a factory with the exact roles/permissions under test (for example role `interviewer`, permission `interview:read` but not `interview:write`).
- Parametrize the language across every supported locale via the `get_language` override.
- If the app lifespan starts a scheduler, Redis, or other side effects, create the `TestClient` without them (patch the start call, or use an app factory); otherwise tests fire real jobs.

## 11.5 What automation must cover per endpoint

1. **Contract:** the response is the standard `ApiResponse[T]` envelope; field naming follows the schema convention; money has fixed scale; masked fields are masked.
2. **AuthZ matrix:** a table of (role/permission, access) vs expected status. At minimum: allowed user, user without the permission, read-only user on a write route, and object-level scope violation (another user's or tenant's record).
3. **Validation:** each required field missing and one invalid value, expecting 422 with a localized message.
4. **State:** the DB after the call (rows written, status changed, counters recomputed), and after a failure (nothing written).
5. **Idempotency:** call a money-moving or booking endpoint twice; the second call must not repeat the side effect.
6. **All supported locales** for any new message key.

## 11.6 Mocking external systems

- No test may reach a real payment gateway, SMS/email provider, identity or KYC service, video-meeting API, or object storage.
- Patch at the integration-client boundary (for example `PaymentGatewayClient.create_charge`) and assert the payload that was sent (including serialization aliases).
- Parametrize failure modes: timeout, 4xx, 5xx, malformed JSON. Assert the local transaction was rolled back and an `AppException` with the right `ErrorCode` came out.
- Webhook/callback handlers: test bad signature (rejected) and replay (idempotent).

## 11.7 Concurrency tests

Race conditions cause real incidents, so test them directly:

- Two sessions calling the same state-changing service on the same row (capture a payment, submit an exam attempt, book the last seat on a trip): assert exactly one effect (row lock plus status re-check).
- Counter-style fields (seats remaining, slots booked): after N concurrent requests the stored value equals the real count and never exceeds capacity.
- These need the real database engine (not mocks) and a separate session per thread.

## 11.8 Scheduler tests

- Test the job body, not the scheduler: call the job function with `fakeredis` and a test DB.
- Assert: lock acquired runs the body; lock already held returns without running; lock released after; running twice is safe.
- Test lock compare-and-delete: a run that outlived its TTL must not delete a newer holder's lock.

## 11.9 Data and security checks worth automating

- A schema test that fails if a response model exposes a raw PII field without masking.
- An i18n test that every message key exists in every supported locale (no missing or extra keys):

```python
def test_all_message_keys_exist_in_every_locale():
    reference = set(MESSAGES[DEFAULT_LOCALE])
    for locale, catalog in MESSAGES.items():
        assert set(catalog) == reference, f"{locale} differs: {set(catalog) ^ reference}"
```

- A test that every route has an auth dependency or is on an explicit public allowlist.
- Lint, type check, and security scan in CI so failures stop the merge.

## 11.10 CI gate

Run before the image build, in whichever CI system the project uses:

```bash
ruff check app tests
pytest --cov=app --cov-fail-under=<agreed baseline> -q
```

- A failing step blocks the merge. Raise the coverage floor gradually; don't set a number the repo can't meet on day one.
- Keep the suite fast (minutes, not tens of minutes); mark slow DB/concurrency tests (`@pytest.mark.slow`) and run them on the PR pipeline.
- Publish the coverage report as a PR artifact.

## 11.11 Regression policy

- Every bug fix ships with a test that **fails before the fix and passes after it**, referenced to the ticket in the test name or docstring (for example `test_resync_unchanged_payload_does_not_poison_session`).
- A change to a shared formula (pricing, fees, fines, scoring) needs tests for every call site, with worked examples from the requirement.

## 11.12 Rollout order for introducing automation

1. Add dev requirements and `tests/conftest.py` with the DB and override fixtures.
2. Cover pure utilities first (calculation, crypto, masking, formatting).
3. Add repository tests for the highest-risk tables.
4. Add endpoint tests for money-moving and permission-sensitive flows.
5. Wire into CI and set the gate.

## 11.13 Automation categories

**API automation:** endpoint testing, request/response validation, status codes, schema validation, authentication, authorization, negative scenarios.

**Functional automation:** complete user journeys (for example book a trip, pay, cancel, refund; or schedule an interview, reschedule, complete, record feedback), multi-step workflows, database state verification after each step, external APIs mocked, regression flows kept from past incidents.

**Concurrency automation:** simultaneous requests, race conditions, duplicate requests, idempotency, locking behaviour, transaction consistency (see 11.7).

**Performance automation:** load, stress, spike, and soak tests with a tool such as k6 or Locust against a staging-like environment, with response-time assertions on the critical endpoints (login, list endpoints, payment). Never run them against production or real third-party providers.

## 11.14 Target CI pipeline

```
Commit
  ↓ Lint            ruff check
  ↓ Type check      mypy / pyright
  ↓ Unit tests      pytest tests/unit
  ↓ Integration     pytest tests/repositories   (DB service container, Alembic upgrade)
  ↓ API tests       pytest tests/api
  ↓ Security checks pip-audit, bandit (or Ruff S rules), secret scan
  ↓ Build           container image
  ↓ Deploy          per environment
```

Order stages so a failure stops the build.

## 11.15 AI rule

> Never claim that tests passed unless they were actually executed. State the exact command run and its result. If tests could not be run (no harness, no DB access), say so plainly and list what remains unverified.

## 11.16 Worked example: concurrency test

```python
# tests/concurrency/test_capture_payment_race.py
import threading

def test_two_requests_capturing_same_payment_create_one_charge(session_factory, payment_id, mock_gateway):
    results = []

    def attempt():
        db = session_factory()                       # separate session = separate transaction
        try:
            service = PaymentService(db)
            results.append(run(service.capture(CapturePaymentRequest(payment_id=payment_id))))
        except AppException as exc:
            results.append(exc)
        finally:
            db.close()

    threads = [threading.Thread(target=attempt) for _ in range(2)]
    [t.start() for t in threads]
    [t.join() for t in threads]

    assert mock_gateway.charge.call_count == 1       # exactly one external charge
    assert sum(isinstance(r, AppException) for r in results) == 1
```

Needs a real database so `SELECT ... FOR UPDATE` actually blocks. SQLite or a mocked session proves nothing here.

## 11.17 Worked example: functional journey

A journey test chains real service calls and checks the DB after **each** step, with all providers mocked.

```
create trip booking
  → reserve seats (assert seats_remaining decreases, never below 0)
  → pay (assert one payment row, one commit)
  → cancel within window (assert refund amount per the cancellation policy)
  → refund completes (assert statuses and final balances)
```

Rules:

- Build the starting data with factories; don't depend on rows left in the database.
- Assert business outcomes (balances, statuses, audit rows), not just status codes.
- Keep a journey per high-value flow; add a new one for each production incident so it can't regress.

## 11.18 Security checks in CI

| Check | Tool | Catches |
|---|---|---|
| Dependency vulnerabilities | `pip-audit` | known CVEs in dependencies |
| Static security | Ruff `S` rules or `bandit` | `eval`, weak hashes, hard-coded secrets, unsafe subprocess |
| Secret scan | `gitleaks` or `detect-secrets` | committed keys and tokens (watch `.env` files) |
| Container scan | image scanner in the registry | base-image CVEs |
