# 14. Code Review & Definition of Done

## 14.1 The review pipeline

Work moves through these stages:

| Stage | Who | Output |
|---|---|---|
| 0. Plan | author | layer-by-layer implementation plan |
| 1. Impact analysis | author | APIs, modules, DB, cache, env, testing, risks |
| 2. Testing | author | scenario checklist derived from the diff, plus test evidence |
| 3. Code review | reviewer | findings plus an Approved Yes/No decision |

Author self-review comes before requesting review; the reviewer checks that the impact analysis and the testing notes match the actual diff.

## 14.2 Author self-review (before opening the PR/MR)

- [ ] Read my own diff top to bottom; no debug code, commented blocks, stray files
- [ ] Lint and type check clean on touched files
- [ ] Tests added or updated, **and actually run**; the PR lists the exact command and result
- [ ] I exercised the endpoint with realistic data, including the failure path
- [ ] I know what is **not** verified and said so in the PR
- [ ] The PR description states what, why, risk, rollback, and DB/env changes
- [ ] A comment is posted on the ticket for this change

## 14.3 Review order

Review in this order so the expensive problems surface first. Stop and send back at the first Blocker.

```
1. Architecture
  ↓ 2. Business correctness
  ↓ 3. Security
  ↓ 4. Database / transactions
  ↓ 5. Validation
  ↓ 6. Concurrency
  ↓ 7. Performance
  ↓ 8. Testing
  ↓ 9. Code quality
```

## 14.4 Reviewer checklist (in review order)

### 1. Architecture
- [ ] Layers respected: router, service, repository, integration client
- [ ] Thin router: the route body is one line of real work
- [ ] Business logic is in the service; no raw queries in the service; repository methods used (with `lock` where needed)
- [ ] No duplicated logic; shared helper reused; a formula lives in one place
- [ ] No unnecessary new pattern, dependency, or abstraction
- [ ] Router registered with the right prefix and tags
- [ ] Function-local imports (or restructuring) where circularity is possible

### 2. Business correctness
- [ ] The change satisfies every acceptance criterion in the ticket, not only the happy path
- [ ] Business rules are right: status transitions, limits, fees, rounding, dates and timezones (stored in UTC, converted at the edge)
- [ ] Money math is `Decimal` and matches a worked example from the ticket
- [ ] Every call site of a changed rule is updated (a rule often lives in a request path, an export, and a scheduled job)
- [ ] Existing behaviour is preserved, or each intended change is stated in the PR and changelog
- [ ] Edge cases handled: empty, zero, max, already-processed, duplicate, deleted or inactive records
- [ ] Backwards compatible (no renamed or removed response fields), or the break is documented
- [ ] The scheduler/worker and the request path agree on the same rule

### 3. Security
- [ ] A permission dependency is present with the right resource and action
- [ ] Identity from the authenticated user; object-level scope enforced (tenant, ownership, assignment; no IDOR)
- [ ] PII masked in responses; no PII or secrets in logs or error messages
- [ ] One encryption scheme per field, no mixing
- [ ] Export policy followed (protection, filename, scope applied to exports too)
- [ ] File I/O through the storage abstraction; uploads validated; no client-controlled paths
- [ ] Security checks fail closed (2FA, risk/compliance checks, provider outage)
- [ ] No secrets or real `.env` values in the diff; no new CORS or header widening

### 4. Database and transactions
- [ ] Transaction boundary is correct and owned by the service
- [ ] `commit()` happens once, after the complete successful operation (no commit-per-operation)
- [ ] `rollback()` on failure before re-raising or continuing; no session reused after a failed flush
- [ ] `flush()` used where ids are needed before commit
- [ ] New table: collation/charset matches the referenced tables on the target server
- [ ] Alembic migration present, safe for existing data (nullable or backfilled), mirrors the model, reversible or documented as additive
- [ ] Existing column names untouched; indexes added for new access paths
- [ ] No string-built SQL; parameters bound

### 5. Validation
- [ ] Request schema extends `BaseSchema`; types, ranges, patterns, lengths enforced at the schema
- [ ] Business validation that needs DB or context is in the service, with localized messages
- [ ] Response schema is typed (`ApiResponse[T]`); no raw dicts for structured data
- [ ] Shared annotated types (decimal, masked, datetime) used correctly
- [ ] Errors are `AppException` with an HTTP status matching the `ErrorCode` category
- [ ] Every user-facing string uses an i18n message key; new keys exist in every locale
- [ ] External responses are parsed into Pydantic models, not trusted as raw JSON

### 6. Concurrency
- [ ] Money/status flows lock the row (`with_for_update` via `lock=True`) and re-check status after locking
- [ ] No read-modify-write on cached counters; recomputed from source rows or updated atomically
- [ ] Idempotent: a retry or double submit can't repeat a side effect (unique reference or status guard)
- [ ] No DB lock held across a slow external call, or the exception is justified with a short timeout and a rollback path
- [ ] Lock order consistent across flows; deadlock errors handled with retry
- [ ] Scheduled jobs: distributed lock, stable `id`, replace-on-restart, `max_instances=1` where long

### 7. Performance
- [ ] No N+1 queries; no DB calls inside loops
- [ ] Lists paginated with a capped `limit` and a `total_count`
- [ ] Only required columns loaded; no large datasets held in memory
- [ ] Indexes support the new filters, sorts, and joins
- [ ] No blocking sleeps, heavy CPU, or slow third-party calls inline in an `async` handler; long work in a worker/scheduler or `fire_and_forget`
- [ ] External calls have explicit timeouts
- [ ] Caching is keyed correctly (no cross-user or cross-tenant leakage) and degrades gracefully if the cache is down
- [ ] Any performance claim is backed by a measurement, not a guess

### 8. Testing
- [ ] Tests cover happy path, validation, authorization, failure, and (for money) concurrency and idempotency
- [ ] All supported locales checked for new messages
- [ ] A bug fix has a regression test that fails without the fix
- [ ] Automated tests updated where they exist; where they don't, the gap is stated and covered by manual verification
- [ ] **Test evidence is real:** the PR shows the command and output; "tests pass" without evidence is not accepted (section 14.7)
- [ ] The testing notes match the diff

### 9. Code quality
- [ ] Lint passes; complexity within the team limit; full type annotations; docstrings on public functions
- [ ] Naming is clear; comments explain why, with the ticket reference for business rules
- [ ] No dead code, debug output, commented-out blocks, or stray TODOs
- [ ] Changelog entry in the existing style, when the project keeps one
- [ ] New env vars added to `.env.example`; settings read through the settings object
- [ ] Logging uses the shared logger, correct levels, and no duplicate logging of re-raised errors
- [ ] Commits and branch names follow the team convention
- [ ] The diff contains only changes the ticket needs

## 14.5 Severity and how to give feedback

| Severity | Meaning | Merge? |
|---|---|---|
| Blocker | security hole, data loss or corruption, money error, race condition, broken migration, PII exposure, fabricated test evidence | No |
| Major | violates a MUST in this skill, missing authz or scope, missing test for a risky path, missing message key, wrong transaction boundary | No |
| Minor | style, naming, small simplification, missing docstring | Optional, fix preferably |
| Nit | taste | Author's call |

- Comment on the line, state the problem, the impact, and a concrete fix or example.
- Ask a question when intent is unclear; don't assume a bug.
- Separate "must change" from "suggestion".
- Praise good patterns; reviewers set the standard too.
- Re-review after changes: confirm each Blocker and Major is actually resolved, not just replied to.

## 14.6 Reviewer red flags (stop and look closer)

- Anything that moves money or changes a balance: payments, payouts, refunds, fares, fees, credits.
- Anything that grants, changes, or evaluates access: roles, permissions, data-scope rules, JWT handling, or results visible to the wrong user (for example a candidate seeing evaluator notes).
- A new external call, a new scheduled job, or a new export or file route.
- A migration that drops, renames, or retypes a column, or touches reference data.
- Code that "fixes" a symptom (retry, sleep, broader `except`) without a root cause.
- A large diff that mixes a refactor with a behaviour change.
- A lock held while calling out to a third party.
- New `# noqa`, `--no-verify`, or ignored lint rules.

For these, require the impact analysis to describe the risk and rollback before approving.

## 14.7 Verifying claims (including AI-generated changes)

Review what was **actually done**, not what the description says.

- **Test evidence:** the PR must show the exact command and result. If a test run is claimed, the reviewer re-runs it or checks the pipeline. Never accept "tests pass" without evidence. If tests could not be run, the PR says so and lists what is unverified.
- **AI-generated code:** apply extra scrutiny. Check that every referenced name exists in the repo: column names, `ErrorCode` values, message keys, helper functions, endpoint paths, and imports. Assistants invent plausible ones. Check that it follows the existing layering rather than a generic FastAPI tutorial (no raw dict responses, no new path-versioning scheme unless the project uses one).
- **Scope creep:** compare the diff to the ticket. Flag reformatting, renamed symbols, or "while I was here" changes.
- **Behaviour preservation:** for refactors, confirm the outputs are unchanged on the same inputs.
- **Third-party assumptions:** an unconfirmed provider path or parameter must be marked as such in a comment and the PR, and verified against the provider docs before release.

## 14.8 Release readiness

Before approving a change that will be deployed:

- [ ] Order of rollout is stated: migration first, then the image, or the reverse, and what happens in between
- [ ] Rollback plan exists: how to revert code, and whether the migration is reversible or additive
- [ ] Config and env: new variables set in every target environment before deploy
- [ ] Data safety: backfills are idempotent and were tried on a copy; destructive statements are reviewed by the lead
- [ ] Scheduler, cache, and queue impact: new or changed jobs, cache keys to flush, locks that need a TTL review
- [ ] Clients: breaking or additive API changes communicated; changelog updated
- [ ] Monitoring: what to watch after deploy (error rate, logs for the new code path, scheduler lock messages)
- [ ] Smoke test list is written for the staging environment

## 14.9 Quick checklist (one-glance version)

```text
[ ] Correct architecture; thin router; logic in the service; queries in repositories
[ ] Business rules and acceptance criteria met; existing behaviour preserved
[ ] Permission dependency + object-level scope; no secrets/PII in logs
[ ] Pydantic request and typed response schemas; no unnecessary raw dict
[ ] Transaction boundary correct; single commit at the end; rollback handled
[ ] Race conditions considered (lock, re-check, idempotency)
[ ] External API: timeout, validated response, no lock held across a slow call
[ ] No N+1; paginated; indexed; no blocking work in async handlers
[ ] Tests added and actually run (evidence in the PR)
[ ] Lint and type annotations OK; complexity within limit
[ ] Alembic migration added if required, collation verified
[ ] API docs (docstring, tags, changelog) updated; env vars in .env.example
[ ] Git and PR standards followed; rollout and rollback described
```

## 14.10 Definition of Done

A feature is **not** complete because the code works locally. It is complete only when:

```
Implementation
+ Validation
+ Security
+ Transaction correctness
+ Tests
+ Documentation
+ Code review
+ Git standards
+ Quality checks
= DONE
```

In detail, a change is done only when all of these hold:

1. Behaviour matches the ticket's acceptance criteria and was exercised, including failure paths.
2. The checklist in 14.4 passes with no open Blocker or Major.
3. Lint is clean and the tests were run and pass; new behaviour has tests, and bug fixes have a regression test.
4. The impact analysis and testing notes exist and match the diff.
5. DB changes have an Alembic migration, collation verified, safe on existing data; env vars are in `.env.example`.
6. The changelog/docs are updated; the ticket has a new comment describing the change.
7. The PR is approved (Approved: Yes), the pipeline is green, and it is merged into the integration branch.
8. Release readiness (14.8) is satisfied.
9. After deploy to staging, the change was smoke-tested there; promotion to production follows the release process.

Where automated tests don't exist yet, the author records that gap in the PR and covers the risk with manual verification.

## 14.11 Final principle

> The skill guides an agent from requirement → design → implementation → testing → review → Git/PR, not just generation of endpoint code. A reviewer who only checks that the endpoint returns data has not reviewed the change.
