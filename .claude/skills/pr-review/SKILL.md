---
name: pr-review
description: "Stage 3 — Pull Request & Code Review for FastAPI services: runs the deep review on a PR/branch/ticket, verifies the Stage 1 and Stage 2 documents, and fills the reviewer sign-off document with an Approved Yes/No gate."
---

# Stage 3 — Pull Request & Code Review

Produce the reviewer's Pull Request & Code Review document. Stage 1 is
`/impact-analysis`, Stage 2 is `/unit-testing`. Review standards come from the
sibling skill `fastapi-blueprint` (`../fastapi-blueprint`): chapters 10/11
(testing), 12 (git/PR), 14 (review).

Target resolution: no argument = current branch vs the default branch plus
uncommitted changes; otherwise a PR id/URL (`gh pr diff` or equivalent), branch
name, ticket ID, or path.

## Process

1. Run the deep technical review following `fastapi-blueprint` chapter 14 (and
   any project code-review skill if present). If a review of the same target
   was already produced this session, reuse its confirmed findings.
2. Verify the earlier stage documents for this ticket:
   - Stage 1: `docs/impact-analysis/<TICKET-ID or branch>-impact-analysis.md`
   - Stage 2: `docs/unit-testing/<TICKET-ID or branch>-unit-testing.md`
   Check completeness and sign-off state.
3. Fill the document below. A checkbox means "reviewed AND passed": tick only
   when the area was checked with no confirmed findings; otherwise leave it
   unticked and cite `file:line` in Review Comments. An area absent from the
   diff is ticked with `(N/A — no changes in this area)`.
4. Output as markdown. If asked to save it, write to
   `docs/pr-review/<TICKET-ID or branch>-pr-review.md`.

## Output template

```markdown
# 🟦 Stage 3 — Pull Request & Code Review

## Basic Information
* PR Number:
* Ticket ID:
* Reviewer Name:

## Code Review
* [ ] Code Reviewed
* [ ] Coding Standards Followed
* [ ] Naming Standards Followed
* [ ] Reusability Verified

## Security Review
* [ ] Authorization Verified
* [ ] Authentication Verified
* [ ] No Sensitive Data Exposed
* [ ] SQL Injection Checked

## Performance Review
* [ ] Query Optimization Reviewed
* [ ] Pagination Reviewed
* [ ] Cache Reviewed

## Database Review
* [ ] Migration Reviewed
* [ ] Table Changes Reviewed

## API Review
* [ ] API Contract Reviewed
* [ ] Response Structure Reviewed

## Validation
* [ ] Unit Testing Verified
* [ ] Impact Analysis Verified

## Review Result
* Review Comments:
* Approved: Yes / No
* [ ] Reviewer Sign-Off
```

Keep headings and field order exactly as above.

## How each field is decided

**Basic Information**
- PR Number: the PR id when reviewing a PR, else `N/A (branch review)`.
- Ticket ID: from the branch name or PR; `N/A` if none.
- Reviewer Name: `git config user.name`.

**Code Review**
- Code Reviewed: tick once the full diff was read and all checks ran (the only
  box ticked unconditionally).
- Coding Standards Followed: no findings against the blueprint — layering
  (router thin, logic in services, queries in repositories/models), full type
  hints, Pydantic v2 schemas instead of raw dicts, small focused functions,
  consistent error handling.
- Naming Standards Followed: snake_case functions/fields, consistent route
  naming, clear `*Create`/`*Update`/`*Response` schema names.
- Reusability Verified: no duplicated logic; existing helpers/schemas reused.

**Security Review**
- Authorization Verified: every changed route enforces the correct
  role/permission and object-level ownership checks.
- Authentication Verified: routes use the shared auth dependency; none bypass it.
- No Sensitive Data Exposed: PII, tokens, and payment data masked or omitted
  from responses and logs; no secrets in code; no third-party error bodies leaked.
- SQL Injection Checked: no string interpolation into raw SQL or `text()`;
  ORM or bound parameters only.

**Performance Review**
- Query Optimization: no N+1, no load-all-then-filter in Python, indexed
  filters on large tables, async/sync not mixed incorrectly.
- Pagination: list endpoints paginated with bounded page size.
- Cache: Redis keys (if used) invalidated or updated on mutation; no stale path.

**Database Review**
- Migration / Table Changes: Alembic revision present, reversible, matches the
  model changes; column types/collation consistent with referenced tables; FKs,
  indexes, defaults and nullability sensible; safe on populated tables.

**API Review**
- API Contract: routes, methods, request/response schemas, and external
  payloads match the agreed contract; no breaking change for existing consumers
  without a note.
- Response Structure: responses follow the project's standard envelope and
  status codes; errors use the shared exception handlers.

**Validation**
- Unit Testing Verified: Stage 2 document exists, Result is PASS, sign-off
  ticked, and the PR's tests meet blueprint chapters 10/11. Otherwise leave
  unticked and state what is missing.
- Impact Analysis Verified: Stage 1 document exists, is developer-signed, and
  matches the actual diff. Otherwise leave unticked and state what is missing.

**Review Result**
- Review Comments: one line per unticked box with `file:line` findings, plus
  anything the next reviewer must know.
- Approved: `Yes` only when there are no High-severity findings, no unticked
  Security Review box, and both Validation boxes are ticked; otherwise `No`
  with blocking reasons in Review Comments.
- Reviewer Sign-Off: always left unticked; the human reviewer ticks it.
