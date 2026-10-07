# 17. Application Profiles

The blueprint is common to every FastAPI app we build. This chapter lists what changes per application type: the extra risks to design for and the extra tests to write. Read the profile that matches the app, then follow chapters 1 to 16 as usual.

## 17.1 Fintech applications

- **Money:** `Decimal` only, fixed scale per currency, one rounding helper. Ledger entries are append-only; corrections are reversing entries, not edits.
- **Concurrency:** balances, limits and quotas change under row locks or atomic conditional `UPDATE`s (see 7 and 16.1). Every money-moving endpoint takes an idempotency key.
- **Compliance:** KYC/AML/sanctions checks sit behind a service interface with an audit record of every decision (8.9). Keep an audit trail of who changed what and when.
- **Data:** PII and account numbers encrypted at rest, masked in responses and logs, restricted by role (15).
- **Integrations:** payment gateways, banks and KYC providers go through integration clients with timeouts, retries only for idempotent calls, and webhook signature verification.
- **Extra tests:** double-submit, concurrent withdrawals against one balance, rounding at boundaries, webhook replay, reversal of a reversed entry.

## 17.2 Assessment portal

- **Roles and scope:** candidate, evaluator, admin. A candidate sees only their own attempts; an evaluator sees only assigned submissions (15, data scoping).
- **Attempts:** one active attempt per candidate per assessment, enforced by a unique constraint plus a lock. The server owns the clock: start time, deadline and auto-submit are computed server-side, never trusted from the client.
- **Integrity:** correct answers and scoring keys never appear in candidate-facing responses. Answer saves are idempotent (the last write per question wins, with a version or timestamp check).
- **Scoring:** scoring is a pure, versioned function; re-scoring writes a new result and keeps the old one. Publishing results is a state transition with an audit entry.
- **Load:** exam start and submit windows spike. Keep those endpoints cheap, paginate everything else, and push report generation to background jobs (9).
- **Extra tests:** submit after deadline, double submit, two tabs saving the same answer, evaluator accessing an unassigned submission, answer key leak check on every candidate response schema.

## 17.3 Interview portal

- **Roles and scope:** candidate, interviewer, panel, recruiter, admin. Feedback written by one interviewer is hidden from the others until submitted if the process requires blind evaluation.
- **Scheduling:** slot booking is a concurrency problem. Lock the slot (or use a unique constraint on slot and interviewer) so a slot cannot be double-booked. Store times in UTC with the user's time zone kept separately.
- **Notifications and links:** calendar and meeting-link creation are external calls. Never hold a slot lock across them; create the booking first, then call out, and reconcile failures with a status (`pending_link`, `confirmed`).
- **Data:** resumes, recordings and feedback are PII. Use private storage with short-lived signed URLs and a retention policy.
- **Extra tests:** two recruiters booking the same slot, reschedule and cancel races, time zone and daylight-saving boundaries, feedback visibility per role.

## 17.4 Transport portal

- **Roles and scope:** rider or customer, driver, dispatcher, admin, often per operator or branch. Scope every list and export by tenant or branch (15).
- **Booking and capacity:** seat or vehicle allocation uses the same locking rules as slot booking (7). A trip is a state machine (`scheduled`, `boarding`, `in_transit`, `completed`, `cancelled`) and only the service layer moves it.
- **Location and real-time:** high-frequency location updates go to a cache or queue and are batched into the database; never one transaction per ping. Validate coordinates and rate-limit the writer.
- **Pricing and payments:** fares are computed server-side from versioned rules, stored with the booking, and never recalculated retroactively. Payments follow the fintech rules in 17.1.
- **Extra tests:** last seat taken concurrently, cancellation after departure, fare rule change after booking, out-of-order location updates, dispatcher scope by branch.

## 17.5 Choosing and combining profiles

An app can combine profiles (for example a transport portal with online payments uses 17.4 and 17.1). Record the chosen profiles in the project's README or `CLAUDE.md` so reviews check the right extras.
