# 8. Security & External Integrations

Names are defaults; follow the project's equivalents where they exist.

## 8.1 Authentication

- OAuth2 bearer plus JWT (or the project's identity provider). The resolved user is a typed `CurrentUser`/token payload schema (`user_id`, `uuid`, `role`, `permissions`, `exp`).
- Auth dependencies live in one module (for example `app/dependencies/auth.py`):
  - `get_current_user` for normal authenticated routes
  - `get_current_user_refresh` for refresh flows only
- Pre-auth endpoints (login, forgot/reset password, OTP, MFA) use a lighter dependency set and perform their own checks inside the service.
- Sensitive actions (payments, payouts, permission changes) additionally require step-up verification (MFA/OTP). Any amount threshold that skips it comes from settings, never hard-coded.

## 8.2 Authorization

- Function-level: a permission dependency or decorator (role/permission plus access level such as view, edit, export) on every non-public route (section 4.2).
- Object-level: even with the right permission, the user may only act on records they are entitled to (own records, tenant, assigned group). Check it in the service against `current_user`, not against a body field.
- Privileged roles may bypass scoping only through the shared scoping helpers; do not write one-off bypasses.
- Identity (who is acting, which entity is "mine") always comes from `current_user`.
- Fail closed: if the permission or scope cannot be resolved, deny.

## 8.3 Secrets and configuration

- Secrets and credentials come from typed settings (environment or a secret manager); never from source, never from the request.
- Never read `os.environ` in feature code. Add every new variable to `.env.example` (placeholders only).
- Never commit `.env` files with real values, keys, or tokens. Check env files at the repo root before committing near them.
- Passwords: a slow, salted hash (argon2/bcrypt) through shared `hash_password` / `verify_password` helpers only. Never store, log, or return a plaintext password, OTP, API key, or token.
- Third-party API keys sit in settings and travel only in request headers.

## 8.4 Data protection

- **At rest:** sensitive columns (government ids, bank details, health or personal documents) use column-level encryption (for example AES-GCM with a managed key) through one crypto helper. Keep keys outside the database.
- **In transit:** TLS everywhere; additional payload encryption only where a requirement says so, with its own keys (never share keys with the at-rest scheme; see 5.4).
- **Masking:** use masking aliases in responses; apply permission-aware masking through one shared helper so privileged roles see more only by design.
- **Logs and audit:** never print raw ids, bank/card numbers, phone, email, tokens, or full request bodies of sensitive endpoints. Log ids and outcomes.
- **Errors:** messages must not reveal SQL, stack traces, file paths, or whether a specific account exists on pre-auth endpoints (use a generic message for login and reset flows).

## 8.5 Exports and file delivery

- Export access needs an explicit export permission and applies the same filters/scope the user has in the UI, so an export can't exceed what they can see.
- Sensitive exports (XLSX, PDF, CSV with PII) are password-protected or delivered via short-lived signed links; deliver any password out-of-band, never in the same response as the file.
- Sanitize cell values against CSV/formula injection (prefix `=`, `+`, `-`, `@`).
- Use a consistent, non-guessable export filename format (user, report type, timestamp) via one helper; log who exported what.
- Follow the organization's data-loss-prevention rules for archive formats; where unspecified, ask the lead before adding a new export type.

## 8.6 File storage and serving

- Everything through the storage abstraction (local or object storage by config). Don't use `open()`, `os.path`, or a cloud SDK directly in features.
- Serving a stored file requires a per-module permission check and ownership check; never serve by raw path alone.
- Validate uploads (extension, MIME, size, structure) before storing; scan for malware where the data comes from untrusted users. Never trust the client filename: generate the stored name server-side and block path traversal (`..`, absolute paths).

## 8.7 Transport and headers

- Security headers (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, HSTS, CSP) are applied centrally in middleware. Don't set them per route.
- CORS origins and trusted hosts come from settings. Never widen them ad hoc to "make it work", and never combine `*` with credentials.
- API docs and debug routes are disabled or protected (basic auth/VPN) outside development.
- Cookies/sessions use `Secure`, `HttpOnly`, and `SameSite`, with the signing secret from settings.

## 8.8 External integrations

Integrations (payment gateways, email/SMS, identity verification, storage, partner APIs, accounting) each follow the same table:

| Practice | Detail |
|---|---|
| Client class | one class per provider in `app/integrations/` owning base URL, headers, endpoints |
| Transport | one shared async HTTP client with response typing and elapsed-time logging |
| Payload | Pydantic model, `model_dump(by_alias=True)` when the provider expects a different casing |
| Timeouts | explicit; short when a DB lock is held; never rely on library defaults for user-facing calls |
| Failures | catch provider errors, roll back dependent local state, log without secrets, raise `AppException` |
| Retries | only for idempotent calls or with a provider reference/idempotency key; never auto-retry a non-idempotent payment |
| Contract | confirm path, params, and auth with the provider docs; if a path is a best guess, say so in a code comment and the PR |
| Data minimization | send only the fields the provider needs |
| Diagnostics | record call start/elapsed, never request bodies containing PII |
| Callbacks/webhooks | verify the signature (HMAC over the raw body, constant-time compare, timestamp tolerance against replay) before trusting the payload; make the handler idempotent by event id |

## 8.9 Regulated and financial flows (fintech apps only)

Applies where the app handles money movement, onboarding of customers, or regulated data. Skip for apps without such flows.

- Identity (KYC) and screening (AML, sanctions, PEP) results gate onboarding and transactions. A failed or unavailable screening call must **block or hold** the action (fail closed), not pass silently.
- Scheduled re-screening runs under the distributed lock (7.8) and is idempotent.
- Document and ID data are PII: store through the storage abstraction/encrypted columns and mask on read.
- Keep an append-only audit trail of decisions (who, what, when, result) and retain it per the applicable regulation.
- Money movement uses `Decimal`, idempotency keys, and double-entry or ledger records; never mutate a balance without a ledger row.

## 8.10 Dependency and supply-chain hygiene

- Pin versions (lock file); add a dependency only when the standard library and existing utilities can't do the job, and say why in the PR.
- Don't add libraries that execute network calls at import time.
- Review security advisories when upgrading `fastapi`, `pydantic`, `sqlalchemy`, DB drivers, `cryptography`, and JWT libraries; run an audit tool (`pip-audit`) in CI.

## 8.11 Security coverage checklist

| Topic | Rule here |
|---|---|
| Authentication | JWT bearer via auth dependencies; step-up MFA on sensitive actions |
| Authorization / RBAC | permission dependency with role and access level |
| Object-level (IDOR) | check the record belongs to the caller's scope, never trust an id from the body alone |
| Password hashing | argon2/bcrypt via shared helpers |
| Secret management | typed settings / secret manager; never in code or logs |
| CORS / trusted hosts | central in `main.py`, settings-driven; never widened per route |
| Security headers | central middleware |
| Rate limiting | on login, OTP, and other abuse-prone routes |
| Input validation | Pydantic at the boundary; whitelist enums; bound sizes |
| SQL injection | ORM / bound parameters only |
| File upload | validate type, size, structure; server-generated names; storage abstraction; block path traversal |
| PII protection | masking, encryption at rest, no PII in logs |

## 8.12 Never log

Passwords, access or refresh tokens, OTPs, API keys and secrets, full payment/card/bank data, and sensitive PII (government id, full phone, email). Log ids and outcomes instead.

## 8.13 Integration shape and requirements

```
Service
  ↓
Integration client (adapter in app/integrations/, e.g. PaymentGatewayClient)
  ↓
HTTP client (httpx / aiohttp)
  ↓
External API
```

Every integration MUST have:

- **Timeout** explicit, short when a lock is held.
- **Response validation:** parse into a Pydantic model; a validation failure is an integration error.
- **Retry strategy:** only for idempotent calls or calls carrying an idempotency key; bounded attempts with backoff. Never auto-retry a non-idempotent payment.
- **Idempotency:** provider reference or local unique key.
- **Error mapping:** provider errors become `AppException` with the right `ErrorCode`; don't leak provider internals to the client.
- **Logging:** endpoint, status, elapsed time, no secrets or PII.
- **Circuit breaker** where a flaky provider could stall requests (screening, payments): after repeated failures, fail fast for a cool-down. Agree on it with the team before adding.
- **Connection pooling:** reuse one long-lived client/session per provider (created in lifespan) instead of one per request.

```python
# MUST NOT
data = (await client.get(...)).json()           # trust blindly

# MUST
class ProviderCustomer(BaseSchema):
    id: int
    name: str

try:
    customers = [ProviderCustomer.model_validate(c) for c in payload["customers"]]
except (ValidationError, KeyError, TypeError) as exc:
    raise AppException(status_code=502, code=ErrorCode.SYSTEM_EXTERNAL_SERVICE_ERROR,
                       message=self.message.external_service_error) from exc
```

## 8.14 Retry with backoff (idempotent calls only)

```python
RETRYABLE_STATUS = {502, 503, 504}

async def get_with_retry(self, endpoint: str, attempts: int = 3) -> httpx.Response:
    delay = 0.5
    for attempt in range(1, attempts + 1):
        try:
            response = await self.http.get(endpoint, headers=self.headers, timeout=10)
            if response.status_code not in RETRYABLE_STATUS:
                return response
        except (httpx.TransportError, asyncio.TimeoutError):
            if attempt == attempts:
                raise
        await asyncio.sleep(delay)          # awaited, never time.sleep in async code
        delay *= 2
    raise AppException(...)
```

- Retry only reads and writes that carry an idempotency key. Never loop a payment or refund.
- Cap attempts and total time so a request can't hang.
- Don't retry while holding a DB lock.
- Log each attempt with the endpoint and attempt number, never the payload.

## 8.15 JWT and OAuth2 specifics

- Access tokens are short-lived; refresh tokens only work on the refresh dependency. A refresh token on a normal route must be rejected.
- Validate signature, expiry, issuer/audience, and role claims; never trust permissions from the client, they come from the verified payload (or are reloaded server-side).
- On logout, password change, or account lock, tokens for that user must stop working (revocation list, token version, or short TTL; confirm the mechanism before relying on it).
- Never log or return a token; never put one in a URL.
