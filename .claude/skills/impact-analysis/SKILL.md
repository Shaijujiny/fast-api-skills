---
name: impact-analysis
description: "Stage 1 — Developer Impact Analysis for FastAPI services: generates the impact-analysis document for the current branch or a given PR/branch/ticket, auto-filled from the diff (APIs, modules, DB/migrations, Redis, env/config, testing, risks)."
---

# Stage 1 — Developer Impact Analysis

Generate the Developer Impact Analysis document for a change set. Stage 1 of
the review workflow; Stage 2 is `/unit-testing`, Stage 3 is `/pr-review`.
Standards live in the sibling skill `fastapi-blueprint` (`../fastapi-blueprint`).

Target resolution: no argument = current branch vs the default branch
(`main`/`master`/`develop`, whichever the repo uses) plus uncommitted changes;
otherwise a PR id/URL (`gh pr diff` or the host's equivalent), branch name,
ticket ID (found in the branch name), or path.

## Process

1. Collect the diff, changed files with statuses (`git diff --name-status`),
   and the commit log.
2. Read every changed file, and its callers where impact is unclear (grep for
   imports/usages of changed services, models, schemas, utils).
3. Fill EVERY field below from evidence in the code. Never guess: a field you
   cannot determine gets `_<to be filled by developer>_`. Tick a checkbox only
   when the diff proves it.
4. Output the document as markdown. If asked to save it, write to
   `docs/impact-analysis/<TICKET-ID or branch>-impact-analysis.md`.

## How to fill each section

**Basic Information**
- Feature Name: from the branch slug and commit/PR titles.
- Ticket ID: the identifier in the branch name or PR (whatever tracker the
  team uses); `N/A` if none.
- Developer Name: most frequent `git log --format='%an'`. Date: today.
  Sprint/Release: from the PR milestone if available, else leave for developer.

**Change Details**
- Requirement Summary: 2-4 sentences on what the change does (behavior, not
  file names), e.g. "payment refund now supports partial amounts".
- Changed Files: total count; New (`A`), Deleted (`D`), Modified (`M`/`R`) listed separately.

**Impact Analysis** — trace, don't guess
- Affected APIs: every route in changed routers plus routes whose
  service/schema/model dependencies changed. List as `METHOD /path`.
- Affected Modules: packages touched directly or via shared code they import.
- Affected Workflows: business flows a changed function is demonstrably part
  of (e.g. payment capture, exam attempt submission, interview slot booking,
  trip booking and cancellation).
- Affected Reports: changed reports, exports, or file generation.
- Affected Dashboards: consumers of any changed response schema (list the
  schema names; any changed response model is potential client impact).
- Affected Notifications: changed email/SMS/push senders, templates, or queues.

**Database Impact**
- SQL Changes: tick if any SQLAlchemy model changed or DDL appears. List each
  table with the kind of change (new table / new column / index / query-only).
  Query changes alone need no migration.
- Migration Required: tick only for schema changes (tables, columns, indexes,
  FKs). Check an Alembic revision exists, is reversible, and column
  type/collation matches referenced tables. Note data backfill needs.
- Other data stores: if any non-SQL store is touched, list it under Notes.

**Infrastructure Impact**
- Redis (if used): tick if cache/session/rate-limit code changed; list keys or
  prefixes, TTLs, and whether invalidation on mutation is handled.
- Environment Changes: tick if settings/config classes, `.env.example`, or
  deploy files gained or changed variables; list new variables per environment.
- External Service Impact: tick if integrations changed (payment gateway,
  email/SMS provider, identity/KYC, video provider, maps); name the service
  and the contract change.

**Testing Impact**
- Unit Tested: tick only if the diff contains tests covering the new logic
  (see blueprint chapters 10/11); otherwise leave unticked and say so.
- Regression Areas: existing behavior sharing code with the change.
- Modules / APIs To Be Tested: concrete list QA can run, from Affected APIs
  plus regression areas.

**Risk Assessment** — cite only risks the diff exposes
- Known Risks: race conditions on balances/counters/slots, lost updates,
  missing transaction boundaries, unvalidated `None` from lookups, type or
  collation mismatches, breaking schema changes.
- Performance Impact: N+1 queries, unindexed filters, unbounded lists, large
  exports, new external calls in request paths.
- Security Impact: new/changed endpoints and their auth/permission coverage,
  PII or money data in responses/logs, secrets in code or env.
- Rollback Risk: Low = code-only revert; Medium = config/cache changes; High =
  irreversible migration or external state (e.g. a payment already captured).
  State what rollback requires.

**Sign-Off** — always leave unticked; the developer ticks it.

## Output template

```markdown
# 🟦 Stage 1 — Developer Impact Analysis

## Basic Information
* Feature Name:
* Ticket ID:
* Developer Name:
* Date:
* Sprint / Release Version:

## Change Details
* Requirement Summary:
* Changed Files:
* New Files Added:
* Deleted Files:
* Modified Files:

## Impact Analysis
* Affected APIs:
* Affected Modules:
* Affected Workflows:
* Affected Reports:
* Affected Dashboards:
* Affected Notifications:

## Database Impact
* [ ] SQL Changes
* Tables:
* [ ] Migration Required
* Notes:

## Infrastructure Impact
* [ ] Redis Changes
* Cache Keys:
* [ ] Environment Changes
* [ ] External Service Impact

## Testing Impact
* [ ] Unit Tested
* Regression Areas:
* Modules To Be Tested:
* APIs To Be Tested:

## Risk Assessment
* Known Risks:
* Performance Impact:
* Security Impact:
* Rollback Risk:

## Sign-Off
* [ ] Developer Sign-Off
```

Keep headings and field order exactly as above. Use `N/A` for untouched
sections; never leave a field blank.
