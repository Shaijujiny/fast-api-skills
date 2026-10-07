---
name: task-plan
description: "Stage 0 — Task Implementation Plan for FastAPI services: given a ticket/task description, produces a layer-by-layer implementation plan (router/schemas/service/repository/model/utils, DB migration, i18n, security) grounded in the fastapi-blueprint standard and the actual code."
---

# Stage 0 — Task Implementation Plan

Given a task (a ticket ID, a short summary, or a free-text requirement),
produce the implementation plan BEFORE any code is written. This is Stage 0
of the workflow — it feeds Stage 1 impact analysis, Stage 2 unit testing,
and Stage 3 PR review.

The plan must be grounded in two sources, in this order:

1. **The engineering standard** — the sibling skill `fastapi-blueprint`
   (`../fastapi-blueprint/SKILL.md` and its `references/` chapters), plus the
   short `PROJECT_GUIDELINES.md` next to this file. If the project has its own
   guidelines document, read it too; it wins on project-specific paths.
   Every plan step must comply.
2. **The actual code** — explore the modules the task touches. Never plan
   against assumed structure: open the real `router.py`/`schemas.py`/
   `service.py`, repository and model files, and find existing helpers in
   `app/core/` or `app/utils/` and existing schemas before proposing new ones.

## Process

1. Restate the requirement in 2–4 sentences. If a ticket ID is given, use
   branch/commit history and any matching docs for context. List open
   questions that change the design — but still produce the plan with your
   recommended answer marked as an assumption.
2. Locate the home for the change: which `app/api/<feature>/` module (or a
   new one), which repositories and models, which shared helpers. Grep for
   similar existing endpoints and name them as the pattern to copy.
3. Write the plan using the template below — file-by-file, in dependency
   order (model → migration → repository → schema → service → router →
   registration → i18n). Every planned file gets: exact path, create/modify,
   and what goes in it.
4. Check the plan against the new-endpoint checklist in
   `PROJECT_GUIDELINES.md` and the plan-review gates below.
5. Output the plan as markdown. If asked to save it, write to
   `docs/plans/<TICKET>-plan.md`.

## Plan template

```markdown
# Stage 0 — Implementation Plan

## Task
* Ticket ID:
* Feature Name:
* Requirement Summary:
* Assumptions / Open Questions:

## Approach
<3–6 sentences: the design in words — what happens on each request/flow,
which existing pattern it follows (name the module copied), what is NOT
being changed.>

## File Plan (in implementation order)
| # | File | Action | Contents |
|---|---|---|---|
| 1 | app/models/<entity>.py | modify | new column / relationship on <Entity> |
| 2 | migrations/versions/<rev>_<slug>.py | create | Alembic revision (only if schema change) |
| 3 | app/repositories/<entity>_repository.py | modify | <Entity>Repository.get_… / create_… |
| 4 | app/api/<feature>/schemas.py | modify | <X>Request, <X>Response (BaseSchema) |
| 5 | app/api/<feature>/service.py | modify | <Feature>Service.<method> — logic, transaction, errors |
| 6 | app/api/<feature>/router.py | modify | METHOD /path + auth/permission dependency |
| 7 | app/main.py (or router registry) | modify | include router (only if new router) |
| 8 | i18n messages (e.g. app/core/i18n/…) | modify | new message keys in every supported language |

## Database Plan
* Tables/columns/indexes/FKs/constraints (types and collation consistent with
  referenced tables — or "none"):
* Alembic revision: <yes + summary / not needed>; upgrade AND downgrade
  described; backfill/lock considerations for large tables.

## API Contract
* Endpoint(s): METHOD /path — request schema → ApiResponse[<Response>]
* Permissions: <role/permission required>
* Wire format notes: <aliases, pagination, filtering, idempotency key —
  as applicable>

## Reuse
* Existing helpers/schemas/repository methods to reuse (exact import paths):
* Similar endpoint used as the pattern:

## Security & Data
* PII / sensitive fields and how they are masked, encrypted or excluded:
* AuthN/AuthZ and ownership checks (object-level access):
* Money/aggregate fields touched (Decimal; recomputed, not incremented):
* External calls (timeouts, retries, idempotency):

## Risks & Rollback
* Known risks:
* Rollback plan (code revert + migration downgrade):

## Test Plan (feeds Stage 2)
* Happy path / negative / edge scenarios to verify:

## Estimated Steps to Done
1. <ordered work items, each small enough to verify independently>
```

## Neutral example (shape of a good File Plan row)

Task: "Reschedule an interview slot" — `PATCH /interviews/{id}/slot`:
`InterviewSlotRepository.get_for_update`, `RescheduleRequest`/`SlotResponse`
in schemas, `InterviewService.reschedule` (checks ownership, slot free,
raises `AppException(ErrorCode.SLOT_UNAVAILABLE)`), thin route returning
`ApiResponse[SlotResponse]`, message key `interview.slot_unavailable`.
Other typical tasks: capture a payment, submit an exam attempt, book a trip.

## Plan-review gates (check before presenting)

- Every new endpoint has: schema(s), service method, repository method(s),
  thin route with auth/permission dependency, registration, i18n keys for all
  supported languages, and — if DDL — an Alembic revision with downgrade.
  A plan missing any of these is incomplete.
- No step puts queries in a service/router, returns raw dicts instead of
  `ApiResponse[T]`, hardcodes user-facing strings, or raises bare
  `HTTPException` instead of `AppException`/`ErrorCode`.
- Functions planned stay small and single-purpose — if a service method's
  description sounds bigger, split it into helpers in the plan.
- Reuse checked: the plan names what it reuses; "write new util" is only
  allowed after stating that no existing helper fits.
- Money is `Decimal`; time comes from one injectable clock helper (UTC);
  config via the settings object, never raw `os.environ`; secrets never
  logged.
- Multi-step writes name their transaction boundary and any row locks or
  idempotency keys.
- Commit message and branch follow the team Git standard (see
  `fastapi-blueprint` chapter 12).

Keep plans concrete: exact paths, exact class/method names, exact
permission names. A plan a developer can execute top-to-bottom without
re-deciding anything is the goal.
