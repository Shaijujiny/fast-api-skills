# 10. Testing & Quality

## 10.1 Baseline expectations

- Every service has a `tests/` directory mirroring `app/`, with `pytest` and `httpx` in the dev requirements (not production).
- CI runs lint, type check, and tests on every pull request (see 11.10, 11.13). A project without this is missing a gate: add it as its own change.
- Beyond CI, quality is enforced by review and a per-change test checklist.

## 10.2 Static quality: Ruff

- Configure in `pyproject.toml`: a broad rule set (`select = ["ALL"]` with a short, justified ignore list, or an agreed subset), `target-version` matching the runtime, `line-length = 120`, one docstring convention. Per-file ignores for `tests/*.py` (assert, hard-coded test credentials, docstrings).
- Run before every commit:

```bash
ruff check app tests
ruff format --check app tests
```

- Don't add blanket `# noqa` or widen the ignore list. A targeted `# noqa: CODE` with a reason is acceptable.
- Don't reformat unrelated code in a feature PR; fix only the lines you touch.
- Full type annotations on every signature (the DI style relies on `Annotated[...]`). Public functions and classes carry docstrings:

```python
def get_by_id(self, payment_id: int, *, lock: bool = False) -> Payment | None:
    """Return one payment.

    Parameters
    ----------
    lock : bool
        Take ``SELECT ... FOR UPDATE`` so concurrent calls serialize.
    """
```

- Complexity cap 10 per function; split rather than ignore.

## 10.3 What to test for each change

| Area | Cases |
|---|---|
| Happy path | correct data, correct `ApiResponse[T]` envelope (status, code, localized message) |
| Validation | missing/invalid fields, out-of-range values, bad enum (expect 422 in the standard error shape) |
| AuthN | no token, expired token, wrong token type (refresh token on a normal route) |
| AuthZ | missing role/permission, read-only where write is needed, object-level scope (another user's or tenant's record), admin vs regular user |
| Not found / conflict | unknown id (404), invalid state transition (409/422), duplicate create |
| Transactions | commit happens; on failure nothing is persisted (`rollback`); no half-written rows |
| Concurrency | same request twice (idempotency), status re-check after lock |
| Money / precision | `Decimal` math, fixed-scale rounding, boundaries (0, max, negative), no float |
| Localization | every supported locale returns the right message; the key exists in all locales |
| Security | PII masked in the response, secrets absent from logs |
| Pagination | `offset`/`limit`, `total_count`, empty page, search term |
| External calls | success, timeout, non-2xx, malformed body; local state rolled back on failure |
| Scheduler | lock acquired vs skipped, rerun is idempotent |
| Regression | the bug that was fixed fails without the fix |

## 10.4 Test design rules

- **Arrange / Act / Assert**, one behaviour per test, descriptive names: `test_capture_payment_rejects_already_captured_payment`.
- Tests are independent and order-agnostic; no shared mutable state across tests.
- Deterministic: freeze time (`freezegun` or an injected clock), no sleeps, no real network.
- Assert on the **contract** (envelope, codes, field names, DB state), not on internal calls.
- Use realistic `Decimal` values and boundary values for money.
- Don't test the framework; test your rules.

## 10.5 Manual verification for risky changes

Some changes need a real run, not just automated tests:

- Money movement (payments, refunds, settlements): reconcile against a known dataset (for example captured total equals `SUM(line items)`), and run the SQL the change depends on against a dev database.
- Schema changes: run `alembic upgrade head` and `downgrade -1` on a copy first and confirm FK, index, and collation behaviour.
- Exports: open the file and confirm contents, access control, and filename.
- Scheduler jobs: trigger once, check the lock log lines, run twice to confirm idempotency.

## 10.6 Test checklist per change

For each PR, write a checklist of concrete scenarios derived from the diff (using 10.3) and record the result of each in the PR description. It is part of the review process (chapter 14).

## 10.7 Code quality checklist (before commit)

- [ ] `ruff check` and format clean on touched files
- [ ] Type hints and docstrings on new public functions/classes
- [ ] No dead code, commented-out blocks, debug prints, or TODOs without a ticket
- [ ] No duplicated formula or query; reused the existing helper
- [ ] Names say what things are (`captured_total`, not `tmp2`)
- [ ] Comments explain why, with the ticket id when it encodes a business rule

## 10.8 Testing levels

```
Unit tests          pure logic: calculations, validators, masking, helpers
  ↓
Integration tests   repositories and services against a real MySQL/PostgreSQL (locks, FKs, collation)
  ↓
API tests           TestClient against the router: contract, authz, envelope
  ↓
E2E tests           multi-step journeys across endpoints on a staging-like environment
```

Cover: business logic, validation, authentication, authorization, error handling, DB behaviour, transactions (commit and rollback), external integrations (mocked), edge cases, and regression.

> New behaviour needs automated test coverage appropriate to its risk. Money movement, auth, tenant/permission scope, and migrations are high risk; a display-only field is low risk.

## 10.9 Quality gates

| Gate | Standard |
|---|---|
| Ruff (lint) | required, blocking in CI |
| Formatting | `ruff format` (or the single formatter the project picks); don't reformat unrelated code |
| Type checking | mypy or pyright on `app/`; non-blocking at first, then blocking |
| Complexity | Ruff `C901`, max 10 |
| Coverage | `--cov-fail-under` set to an agreed baseline and raised gradually (see 11.10) |
| Documentation | docstrings on public code, route summaries and descriptions in OpenAPI |
| Dead code | Ruff (`F401`, `F841`); consider `vulture` in audits |

## 10.10 Dead-code detection

- Ruff `F401` (unused imports) and `F841` (unused variables) report most dead code. Remove unused imports by hand where an import may exist for re-export or side effects (for example in `__init__.py`).
- Remove code you orphan in your own change. Don't sweep unrelated dead code in a feature PR; raise a separate `chore:` change.
- Optional tool for audits: `vulture app/` (review the output; false positives are common with FastAPI route functions and Pydantic fields).
- Commented-out code and `TODO`s without a ticket id are removed in review.

## 10.11 Worked example: testing a service rule

```python
# tests/api/test_payment_service.py
import pytest
from fastapi import status

from app.core.exceptions import AppException, ErrorCode


@pytest.mark.parametrize("lang", SUPPORTED_LOCALES)
async def test_capture_payment_rejects_already_captured_payment(db_session, make_service, payment_factory, lang):
    payment = payment_factory(status="CAPTURED")
    service = make_service(PaymentService, lang=lang)

    with pytest.raises(AppException) as exc:
        await service.capture(CapturePaymentRequest(payment_id=payment.id))

    assert exc.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert exc.value.code == ErrorCode.PAYMENT_ALREADY_CAPTURED
    assert exc.value.message == translate("payment.already_captured", lang)
    db_session.refresh(payment)
    assert payment.status == "CAPTURED"          # nothing changed, nothing external called
```

What it demonstrates: every supported locale, the exact status and code, the localized message, and the state after a rejected call.
