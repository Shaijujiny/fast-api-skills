---
name: unit-testing
description: "Stage 2 — Developer Unit Testing for FastAPI services: generates the unit-testing checklist document for the current branch or a given PR/branch/ticket, with concrete test scenarios derived from the diff for each section."
---

# Stage 2 — Developer Unit Testing

Generate the Developer Unit Testing document for a change set. Stage 1 is
`/impact-analysis`, Stage 3 is `/pr-review`. Testing standards (pytest,
fixtures, what to mock, coverage expectations) are in the sibling skill
`fastapi-blueprint` (`../fastapi-blueprint`), chapters 10/11.

Target resolution: no argument = current branch vs the default branch plus
uncommitted changes; otherwise a PR id/URL, branch name, ticket ID, or path.

The goal is to make each checkbox concrete: derive the exact scenarios from
what the diff changed, so "tested" is verifiable. Prefer automated pytest
tests; list manual steps (Swagger, curl) only where no automated test exists.

## Process

1. Collect the diff and read every changed file. If a Stage 1 document exists
   (`docs/impact-analysis/<TICKET-ID or branch>-impact-analysis.md`), reuse its
   affected-API/module/cache lists.
2. For each section below, derive concrete scenarios and list them as
   sub-bullets under the checkbox.
3. Tick a checkbox ONLY on evidence: the user said they executed it, or you
   ran it this session (test run, endpoint call, DB/Redis inspection).
4. Result: PASS only when every applicable checkbox is ticked; FAIL if any
   executed scenario failed (say which in Remarks); otherwise leave
   `PASS / FAIL` for the developer. Never tick Developer Sign-Off.
5. Output as markdown. If asked to save it, write to
   `docs/unit-testing/<TICKET-ID or branch>-unit-testing.md`.

## How to derive scenarios per section

**Functional Validation**
- Happy Path: one per new/changed endpoint or service method (e.g. successful
  payment, exam attempt submit, interview slot booking, trip booking).
- Negative: unknown ids, duplicates, wrong-state records (already paid,
  attempt already submitted, slot already taken, trip cancelled), missing
  related rows.
- Edge Cases: empty lists, boundary values (0, max, exactly at deadline),
  first/last page, Unicode input, concurrent repeat of the same mutation.
- Validation Rules: one per Pydantic `Field(...)`/validator in changed
  schemas; violate each and expect a 422, not a 500.

**API Validation**
- Request: wrong types, missing/unknown fields, malformed body give 4xx in the
  project's error shape, never a stack trace.
- Response: matches the response schema; sensitive fields are masked or omitted.
- Error Response: each raised HTTP/domain exception is reachable and returns
  its documented code and message.

**Database Validation**
- SQL Data: for each changed model/table, the `SELECT` to verify the row after
  each mutation; audit/log tables when written. For migrations: upgrade and
  downgrade both run cleanly.
- Data Integrity: FKs resolve; stored aggregates (balances, seat/slot counts)
  equal their source-of-truth after the operation; failure rolls back with no
  orphan rows.

**Cache Validation** (N/A if Redis unused or untouched)
- For each key/prefix: created on first read, updated or invalidated after
  mutation (mutate, re-read, expect new value), TTL as configured.

**Security Validation**
- Authentication: no/expired/invalid token gives 401.
- Authorization: user lacking the required role/permission gets 403; correct
  role succeeds; users cannot access other users' records. One per changed endpoint.

**Error Handling**
- Exceptions: force each external dependency to fail (timeout, non-200, DB
  error) and expect a clean error response, logged error, no third-party body leaked.
- Failure Scenarios: mid-flow failure leaves consistent state (fail after
  step 1 of 2; verify rollback or safe re-run).

**Existing Features**
- From Stage 1 regression areas (or grep callers of changed shared code), list
  endpoints/flows to re-verify. Never N/A when shared code changed.

**Result**
- Remarks: what could not be tested locally, known gaps, data prerequisites.

## Output template

```markdown
# 🟦 Stage 2 — Developer Unit Testing

## Basic Information
* Feature Name:
* Ticket ID:
* Developer Name:

## Functional Validation
* [ ] Happy Path Tested
* [ ] Negative Scenarios Tested
* [ ] Edge Cases Tested
* [ ] Validation Rules Tested

## API Validation
* [ ] Request Validation
* [ ] Response Validation
* [ ] Error Response Validation

## Database Validation
* [ ] SQL Data Verified
* [ ] Data Integrity Verified

## Cache Validation
* [ ] Redis Cache Created
* [ ] Redis Cache Updated
* [ ] Cache Expiry Verified

## Security Validation
* [ ] Authentication Tested
* [ ] Authorization Tested

## Error Handling
* [ ] Exception Handling Tested
* [ ] Failure Scenarios Tested

## Existing Features
* [ ] Existing APIs Verified
* [ ] Existing Features Verified

## Result
* Remarks:
* Result: PASS / FAIL
* [ ] Developer Sign-Off
```

Keep headings and field order exactly as above. List derived scenarios as
indented sub-bullets under each checkbox. Mark inapplicable items
`N/A — <reason>` (e.g. "Cache: N/A — Redis not used by this change") but keep
the checkbox line.
