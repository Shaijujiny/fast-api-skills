---
name: fastapi-security-checklist
description: "Practical security checklist for FastAPI services organized by OWASP API Security Top 10, plus input validation, file uploads, CORS, headers, secrets, dependencies, logging/PII, SQL injection, webhooks and per-portal notes (fintech, assessment, interview, transport). Use when reviewing a pull request, adding an endpoint, handling uploads/external calls/PII, or preparing a release."
---

# FastAPI Security Checklist

Use as a PR-review list: tick items that apply, comment on those that fail. Related: `../fastapi-blueprint` chapter 8 (security and external integrations), chapter 14 (code review and definition of done), chapter 15 (users, roles, privileges). Authentication details: `../fastapi-auth`.

## API1 - Broken Object Level Authorization (BOLA/IDOR)
- [ ] Every endpoint taking an id loads the object **scoped to the caller** (owner/tenant/assignment), not by id alone (chapter 15.5).
- [ ] Not-yours returns 404 (or 403 consistently), same as not-found.
- [ ] List endpoints filter by scope in the query, not after fetching.
- [ ] Nested ids (`/orgs/{o}/items/{i}`) verified to belong together.
- [ ] Prefer UUIDs for public ids, but never rely on unguessability as the control.

## API2 - Broken Authentication
- [ ] Follows `fastapi-auth`: hashed passwords, short access tokens, rotated refresh, pinned JWT algs.
- [ ] Login/OTP/reset rate-limited; generic error messages.
- [ ] No auth bypass via debug flags, default creds, or unauthenticated "internal" routes.
- [ ] Every router has an auth dependency by default (router-level `dependencies=[...]`); public routes are explicit.

## API3 - Broken Object Property Level Authorization
- [ ] Response schemas are explicit allowlists (no returning ORM objects or `model_dump()` of the table).
- [ ] Request schemas exclude server-owned fields (`role`, `status`, `is_admin`, `owner_id`, `balance`); `extra="forbid"` on BaseSchema.
- [ ] Never `Model(**payload.model_dump())` for privileged tables; map fields deliberately.
- [ ] Sensitive fields masked/omitted per role (chapter 15.6): PII, internal notes, hashes, tokens.

## API4 - Unrestricted Resource Consumption
- [ ] Rate limits per user/IP/API key on public, auth, OTP, search, export routes.
- [ ] Pagination mandatory with max `page_size` (e.g. 100); no unbounded lists/exports.
- [ ] Request body size limit (proxy and app); upload size limit; JSON depth/array length bounded in schemas (`max_length`).
- [ ] Timeouts on DB queries, outbound HTTP, background jobs; bounded concurrency.
- [ ] Expensive operations (reports, bulk, SMS/email sends) quota-capped and queued.
- [ ] No N+1 or unindexed filter on user-controlled sort/filter fields; sort/filter fields allowlisted.

## API5 - Broken Function Level Authorization
- [ ] Each route declares `require_permission(resource, action)` (chapter 15.4); admin routes under separate router.
- [ ] Deny by default; new routes not public by accident.
- [ ] HTTP method matters: GET allowed does not imply PUT/DELETE allowed.
- [ ] Authorization enforced server-side in service layer, not by hiding UI.

## API6 - Unrestricted Access to Sensitive Business Flows
- [ ] Identify abusable flows (signup, voucher/coupon, booking, payment, OTP send, referral, submission) and add per-user/device limits.
- [ ] Idempotency keys for payments/submissions; state-machine checks (cannot skip or repeat steps).
- [ ] Sequence/time checks server-side; CAPTCHA or step-up on public flows when abused.
- [ ] Money/quantity computed server-side from DB prices, never from client values.

## API7 - Server-Side Request Forgery
- [ ] User-supplied URLs (webhooks, image fetch, import) validated: scheme `https`, host allowlist, resolve DNS and block private/loopback/link-local/metadata IPs (169.254.169.254), re-check after redirects, or disable redirects.
- [ ] Short timeouts, response size cap, no raw response echoed to the user.
- [ ] Outbound calls go through one HTTP client wrapper (chapter 8).

## API8 - Security Misconfiguration
- [ ] `debug=False`, docs (`/docs`, `/openapi.json`) disabled or protected in production.
- [ ] CORS: explicit origin allowlist, no `*` with credentials; only needed methods/headers.
- [ ] Security headers set (at proxy or middleware): `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options`/CSP `frame-ancestors`, `Referrer-Policy`, `Cache-Control: no-store` on sensitive responses.
- [ ] TLS only; `TrustedHostMiddleware`; proxy headers trusted only from known proxies.
- [ ] Generic 500 messages; no stack traces, SQL, or paths in `ApiResponse` errors (`AppException`/`ErrorCode` only).
- [ ] Least-privilege DB user; no root; separate credentials per environment.

## API9 - Improper Inventory Management
- [ ] Routes are versioned (`/api/v1`); old versions have a retirement plan.
- [ ] No orphaned debug/test/internal endpoints; OpenAPI is the single source and reviewed on diff.
- [ ] Environments listed; staging does not hold real production data (or is equally protected).
- [ ] Third-party integrations and data flows documented.

## API10 - Unsafe Consumption of APIs
- [ ] Responses from third parties validated with Pydantic models before use; treat as untrusted input.
- [ ] TLS verification on; timeouts and retries with backoff; circuit breaker for critical paths.
- [ ] Do not follow redirects to untrusted hosts; no secrets in URLs.
- [ ] Failures degrade safely (no fail-open on payment/auth checks).

## Cross-cutting
**Input validation**
- [ ] All input through Pydantic v2 schemas with types, `min/max_length`, `ge/le`, `Literal`/Enum, regex where needed.
- [ ] Path/query/header params validated too (`Query(..., max_length=...)`).
- [ ] Output encoding when generating HTML/CSV (CSV formula injection: prefix `= + - @` cells with `'`).

**SQL injection**
- [ ] Only SQLAlchemy expressions/bound params; no f-string/`%` SQL; `text()` always with `:params`.
- [ ] Dynamic `ORDER BY`/column names come from an allowlist.

**File uploads**
- [ ] Size cap, extension allowlist AND content sniffing (magic bytes), not just client `Content-Type`.
- [ ] Generated filename (UUID); never use the client path; no path traversal.
- [ ] Stored outside web root / in object storage, private by default, served via short-lived signed URLs.
- [ ] Virus scan for user-shared files; strip image metadata (EXIF/GPS) when not needed.
- [ ] Download endpoints check ownership (BOLA) and set `Content-Disposition`, `nosniff`.

**Secrets**
- [ ] Loaded via settings from env/secret manager; none in repo, logs, images, or `.env` committed.
- [ ] Secret scanning in CI; rotation procedure exists; separate per environment.

**Dependencies**
- [ ] Pinned/locked versions; `pip-audit` (or equivalent) and Dependabot/Renovate in CI; minimal base image.

**Logging / PII**
- [ ] No passwords, tokens, OTPs, full card/ID numbers, or full request bodies in logs.
- [ ] PII masked in logs; request id on every log line; audit trail for sensitive reads/writes (chapter 8/9).
- [ ] Retention and deletion policy for PII; encryption at rest for highly sensitive columns.

**Webhooks (inbound)**
- [ ] Signature verified over raw body with HMAC + constant-time compare; timestamp tolerance; replay protection (event id stored).
- [ ] Respond fast (2xx) and process async; idempotent handlers; unknown event types ignored safely.
- [ ] Source IP allowlist only as an extra layer.

## Per-portal notes
**Fintech**
- [ ] Amounts as `Decimal`/integer minor units, computed server-side; idempotency keys; row locks on balance updates (chapter 7).
- [ ] Step-up auth (OTP/MFA) for payouts and bank/beneficiary changes; maker-checker for high value.
- [ ] Immutable ledger/audit entries; mask account/card numbers; reconcile with provider webhooks.

**Assessment**
- [ ] Answer keys, correct options, scoring rubrics never in candidate-facing schemas or pre-submission responses.
- [ ] Server-side timer and attempt count; start time and deadline stored by server; ignore client-reported time.
- [ ] Attempt tampering: lock answers after submit, enforce one active attempt, verify question belongs to the attempt, no re-fetch of graded results before release.
- [ ] Randomized order/question sets seeded server-side; rate-limit answer saves.

**Interview**
- [ ] Resumes and recordings are private objects, signed short-lived URLs, access limited to authorized reviewers (BOLA) and logged.
- [ ] Consent captured before recording; retention/deletion schedule honored; strip file metadata.
- [ ] Candidate notes/scores hidden from candidates; field-level masking of contact data by role.
- [ ] Meeting links unguessable and expiring.

**Transport**
- [ ] Location data is personal data: collect minimum, coarse for non-owners, restrict live location to the assigned trip/guardian/dispatcher.
- [ ] Driver/rider home addresses and phone numbers masked in shared views; contact via relay where possible.
- [ ] Location history retention limit; no raw coordinates in logs; rate-limit location updates and validate plausibility (speed/jump) to stop spoofing.
- [ ] Trip/booking ids checked for ownership on every read (BOLA).
