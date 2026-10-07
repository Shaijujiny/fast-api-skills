---
name: app-code-review
description: Deep code review for FastAPI services — per-file validation of router/service/schema/repository/model layers, response and exception conventions, and code-quality rules — on the current diff or a given target (branch/PR/path).
---

# FastAPI Code Review

A deep technical review for any FastAPI service (fintech, assessment,
interview, transport portals). The standards come from the sibling skill
`fastapi-blueprint` (`../fastapi-blueprint`): chapter 13 (code generation and
anti-patterns) defines what correct code looks like, and chapter 14 (code
review and definition of done) defines the review order, severity and
checklist. This skill is the per-file checklist plus the report format. If the
project already has an equivalent of a default name below, use theirs.

Review the changed code against these conventions. With no argument, review
the working tree + current branch diff against the default branch
(`git diff <default-branch>...HEAD` plus uncommitted changes). If an argument
is given, review that instead:

- **PR/MR number or URL**: get the diff via `gh pr diff <id>` / `glab mr diff
  <id>` (fall back to fetching the source branch and diffing it against its
  target). Review the full diff, not just the latest commit.
- **Branch name**: `git diff <target-base>...<branch>`.
- **Ticket ID**: find the matching branch (by ticket id in its name) and review it.
- **Path**: review the file/directory's uncommitted + branch changes.

Multiple targets may be given — review each independently and emit one
summary-table row per target.

## Process

1. Collect the diff and the list of changed files.
2. Read every changed file in full (not just hunks) — layering violations,
   missing dependencies, and duplicate blocks are invisible in a 3-line hunk.
3. Run the per-file checklist matching each file's role, then the
   cross-cutting rules.
4. For every candidate finding, re-read the code and confirm it is real
   before reporting; drop anything you cannot confirm.
5. Emit the **Code Review Summary report** (format below): the summary table
   first, then detailed findings ranked most-severe first as
   `file:line — [category] finding` with a one-line failure scenario each,
   then Attention Items. If nothing survives verification, say so plainly. Do
   not auto-fix unless the user asked for fixes.

## Architecture (what "correct" looks like)

```txt
app/
├── api/<feature>/{router,schemas,service}.py
├── repositories/     # all DB access
├── models/           # SQLAlchemy tables
├── integrations/     # external API clients
├── core/             # settings, security, exceptions, i18n, base schemas
migrations/           # Alembic
```

- `router.py` — thin endpoints. Declares the route, auth/permission
  dependency, typed request schema, `response_model=ApiResponse[T]`, and
  delegates to the service. No business logic, no DB access.
- `service.py` — business logic. Orchestrates repositories, integrations,
  caching, notifications. **Never queries the DB directly.**
- `schemas.py` — Pydantic request/response models for the feature. Shared ones
  live in `app/core`.
- `app/repositories/*` — queries, taking the session; no business decisions.

All endpoints return `ApiResponse[T]`; all errors are raised as
`AppException` carrying an `ErrorCode`.

## Deep per-file checklists

### router.py — route validation
- [ ] Path is kebab-case, has `tags=[...]` and a docstring (business rules
      listed for privileged routes).
- [ ] Auth/permission dependency present, with an access level matching the
      verb (read for GET; create/update/delete for mutations). A missing or
      commented-out permission check on an active endpoint is a finding.
- [ ] `response_model=ApiResponse[T]` and the return type annotated.
- [ ] Body/query params are typed Pydantic schemas — never `dict`, `Any`, or
      loose primitives for structured input. Pagination/filtering uses the
      shared pagination schema via `Depends()`, not ad-hoc query args.
- [ ] Dependencies injected via `Annotated[..., Depends(...)]` aliases — no
      manual session/user extraction.
- [ ] Body is one line of delegation to the service. Any `if`, loop,
      try/except, or computation in a router is a finding.

### service.py — service validation
- [ ] No `session.query(...)`, `execute(...)`, `select(...)`, or raw SQL —
      all DB access goes through repositories (blocker).
- [ ] Success: `ApiResponse(...)` with a code, a message resolved from i18n
      keys, and `data` as a schema instance.
- [ ] Errors: `raise AppException(code=ErrorCode.<X>, ...)`. Bare
      `HTTPException`, `JSONResponse`, or returned error dicts are findings.
- [ ] `code` comes from `ErrorCode` — no free-string codes; the ErrorCode
      bucket matches the HTTP status.
- [ ] User-facing messages come from i18n keys — no hardcoded strings.
- [ ] `None` returns from repository lookups are handled before use.
- [ ] Commit/rollback is owned by the service with matching exception
      handling; no commit inside loops when one at the end suffices.
- [ ] Read-then-write flows lock the row (`with_for_update()`) or use an
      atomic statement.

### schemas.py — schema validation
- [ ] Every request model validates strictly: explicit field types (no bare
      `dict`/`Any`), constraints via `Field(...)` where the DB/business rule
      implies one (lengths, ranges), `Annotated[...]` for reusable types.
- [ ] Models extend `BaseSchema`; response models are typed so they work as
      `ApiResponse[Model]`, not `dict`.
- [ ] Optional fields have explicit defaults (`| None = None`,
      `default_factory=list`); no mutable literal defaults.
- [ ] Money is `Decimal`, never float; datetimes are timezone-aware.
- [ ] Field names snake_case; aliases only where an external contract requires.
- [ ] No unused/duplicated schemas — check for an equivalent in the feature or
      `app/core` first.
- [ ] Response models do not leak secrets, raw PII, or internal-only fields.

### repositories and models — query validation
- [ ] Queries live in repositories, take the session, and have type-hinted
      returns (`| None` when using `.first()` / `scalar_one_or_none()`).
- [ ] Queries filter/return only what the caller needs — no `.all()` then
      Python-side filtering; no N+1 loops where one `IN`/join works.
- [ ] Updates validate through a Pydantic schema rather than raw dict keys.
- [ ] Every new/changed table has an Alembic migration (additive, safe on
      existing data); DDL charset/collation matches referenced tables.
- [ ] Money columns are `DECIMAL`/`Numeric` with a non-negative constraint.
- [ ] No business logic in models/repositories — decisions stay in services.

## Cross-cutting rules

Standards detail: `fastapi-blueprint` chapters 13 and 14.

### 1. No raw dict/JSON payloads (blocker)
Requests, responses, and structured payloads are Pydantic models everywhere:
- Never build a response as a dict literal — construct `ApiResponse`/schemas.
- Never `json.loads`/hand-parse a request body — declare a schema parameter.
- External API bodies are schemas dumped via `model_dump(...)`, not inline dicts.
- Internal data passed between service methods should be schema instances
  when the shape is fixed.

### 2. Function size and type hints
- Function bodies stay short and single-purpose; split long ones into helpers
  (target ≤ 20 lines excluding signature/docstring unless the project sets a
  stricter limit).
- Every function has complete type hints: all parameters AND the return type
  (including `-> None`).
- Cyclomatic complexity ≤ 10 and lines ≤ 120 chars per the project's ruff config.

### 3. Duplicate code
Flag copy-pasted blocks (≥ ~4 similar lines appearing twice or more, in the
diff or between the diff and existing code). The fix is a shared helper in the
service, `app/core`, or a repository method — name the existing location when
one already exists.

### 4. Endpoint authorization (blocker)
Any unprotected mutation route is top severity unless intentionally public —
ask, don't assume. Identity comes from the authenticated user, never the
request body; object-level access (a user only touches records they are
entitled to) is enforced.

### 5. Secrets, encryption and PII (blocker)
No hardcoded secrets/API keys. Keep at-rest and in-transit ciphers separate
and never mix them. PII is masked in responses and logs; passwords are hashed
and never returned or logged.

### 6. Counters and money fields (blocker)
Money uses `Decimal`. Cached aggregates (totals, balances) must be rewritten
from source-of-truth aggregation or updated atomically / under a row lock —
never `x.total += amount` read-modify-write without locking (lost updates).

### 7. External API calls
Timeouts set; non-2xx handled; retries bounded; third-party error bodies never
leaked into `ApiResponse.message` (log them, return an i18n message).

### 8. Exports and files
Follow the project's single export policy (e.g. which formats must be
password-protected); file I/O goes through the storage abstraction with a
permission check on file-serving routes.

### 9. Diff hygiene
Only real changes: no serializer round-trips of data files, no mass
reformatting of untouched lines, no newly added commented-out code, debug
prints, test values, or leftover TODOs.

### 10. General correctness
Mutable default arguments; swallowed exceptions in broad `except Exception`;
magic strings/numbers that belong in constants; logging via the project logger
not `print`; cache invalidation when master/config data changes; tests added
for new logic.

## Severity order for reporting

1. **High** — security/auth (rules 4, 5), data integrity (rule 6, migrations),
   hardcoded secrets, and direct DB access in a service or router (layering
   blocker — always name the repository method the query must move to)
2. **Medium** — other layering/contract violations (router/schema checklists,
   rules 1, 7, 8), correctness (rule 10, `None` handling, commit/rollback),
   missing tests for new logic
3. **Low** — quality (rules 2, 3) and hygiene (rule 9)

## Report format — Code Review Summary

Output the review in this exact structure:

```
## Code Review Summary — <DD Mon YYYY>

| PR / Ticket | Developer | Status | Findings | Severity |
|---|---|---|---|---|
| <ticket> (#PR) | <name> | Reviewed | No issues found | — |
| <ticket> (#PR) | <name> | Reviewed with findings | <short list, e.g. "Direct query in service.py, hardcoded API key"> | High |
| <ticket> | <name> | Not Reviewed | <reason, e.g. "diff unavailable"> | — |

### Detailed findings
<per target: `file:line — [category] finding` + one-line failure scenario,
ranked High → Low>

### Attention Items — Recurring Issues
<one bullet per developer/rule that violates the same rule 2+ times — within
this review, across the targets reviewed, or versus earlier review reports if
available. State the rule, the count, and the required action.>
```

Filling the table:
- **PR / Ticket**: extract the ticket id from the branch name; append the PR
  number when reviewing a PR.
- **Developer**: `git log --format='%an'` on the reviewed commits (the most
  frequent author). Use they/them in prose.
- **Status**: Reviewed = no confirmed findings; Reviewed with findings =
  confirmed findings listed; Not Reviewed = review could not run — always give
  the reason.
- **Severity**: the highest severity among that target's confirmed findings;
  `—` when none.
- Omit the Attention Items section only when there are no recurring issues.

If no review was conducted (no reviewable diff, all targets inaccessible),
state explicitly: `No code review was conducted. Reason: [reason].`
