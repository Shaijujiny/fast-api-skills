# 16. Lessons Learned (general engineering rules from past incidents)

> Kept as general rules, stripped of business-domain detail. Check the current code before asserting a detail.

## 16.1 Concurrency and guards

1. **A validation that reads unlocked state protects nothing under concurrency.** Lock the row, or use an atomic conditional `UPDATE ... WHERE remaining >= :x` and check the affected row count.
2. **Never write a cached counter as an absolute value computed from a stale read.** Recompute from the source rows (`SUM(...)`) or increment atomically.
3. **A guard must compare against the original authoritative value**, not a figure that was adopted from the thing being checked. A guard that compares against the already-inflated number passes in exactly the scenario it is meant to catch.
4. **Two services writing the same tables need a shared locking convention.** "It is another app" is not isolation.
5. **Add database constraints as the last line of defence** (unique constraints, CHECKs) in addition to application checks.
6. **"That path is not used" is a claim to verify with production data**, not an assumption. Implicit transitions can run code nobody remembered.
7. **A new guard must not brick existing data.** Run it across the whole existing dataset before deploying, and scope it (new records only) if old rows would fail. Check that its query does not include rows (for example in-progress ones) that legitimately remain.
8. **Timestamp precision limits what you can prove.** Columns with zero fractional seconds cannot order sub-second events; don't build a policy on that ordering.
9. **Rehearse corrective scripts end to end on a clone** before production; rehearsal finds real defects (for example a preflight check that wrongly required cached counters to agree when they lag by definition).

## 16.2 Data and ORM pitfalls

1. **A scalar relationship that assumes one row breaks when several rows are legitimately pending.** It silently returns an arbitrary one. Resolve the row by the specific id instead of a relationship with no filter.
2. **A defensive early `return` can hide a silent no-op that is worse than a crash.** When a precondition fails, raise or log loudly rather than skipping work without a trace.
3. **A step may replace a row** (void the old one, insert a new one), leaving dependents pointing at the old id. Capture the id **before** the update when later logic needs it.
4. **Aggregates over a per-period or per-row relationship:** a "first row" relationship freezes the first row forever. Sum across all rows with a batched repository method (no N+1), and delete the dead relationship once unused.
5. **`FOUND_ROWS` is on** (MySQL), so an `UPDATE` with identical values reports the row as matched. Don't treat a zero row count as failure, and roll back the session before continuing after any error that may have poisoned it.
6. **Reverted or cancelled records must be excluded** from downstream queries (payout, schedule, reports) so no later flow picks them up.

## 16.3 Changing calculations

1. **List every call site before you edit**, and grep for both the new helper and the old function names to catch an unbranched copy. A hidden copy is often found only because two live responses disagree.
2. **One shared helper, all sites call it.** A helper may return a tuple; make sure every caller uses the right element (for example a period-prorated rate vs an annual rate).
3. **Read-only views can diverge from execution.** If one call site tolerates input another rejects, flag the asymmetry to QA.
4. **Memory of a past fix is not proof.** The code on disk is the source of truth; use `git diff` and `git log` before assuming something was implemented.

## 16.4 Seed data, reference data, and migrations

1. Reference/lookup rows (statuses, roles, permissions, categories) must be created by an **Alembic migration or an idempotent seed script**, never by manual SQL on one environment. Keep the migration and the seed file in sync.
2. Match the live row exactly (including empty or missing translations) rather than inventing values; if a translation is added later, update every artifact that carries it.
3. A hand-typed uuid can be malformed. If ids are 32 lowercase hex characters (or canonical 36-character UUIDs), validate the format in the seed loader or a test.
4. Reusing a value from another category can be a deliberate choice; record the decision where it is made.
5. **Collation is server-specific on MySQL.** A new table must match the referenced tables (for example `utf8mb4_0900_ai_ci` on MySQL 8 vs `utf8mb4_general_ci` or `utf8mb4_unicode_ci` elsewhere); a mismatch gives FK error 3780 or JOIN error 1267. Don't pin `COLLATE` in helper DDL that must run on both MariaDB and MySQL. PostgreSQL has its own collation rules; check them when joining across databases.
6. Before writing a migration for a schema redesign, confirm the old shape ever reached production; if it did not, no data migration is needed.
7. Make migrations additive and backwards compatible with the currently deployed code, so rollout order does not matter.

## 16.5 Security and integration lessons

1. **Provider contract assumptions:** confirm paths and body casing (some providers need camelCase, so dump with `by_alias=True`); when a path was a best guess, mark it as unconfirmed in code and in the PR, and verify against the provider docs.
2. **Locks and external calls:** hold a row lock across an external call only to prevent a duplicate side effect, with a short timeout and a status re-check. Otherwise commit or release before calling out.
3. **One cipher scheme per field.** Decide whether a field is encrypted at rest or encrypted for transport to the client, and use the matching helper; bridging between schemes must be an explicit, reviewed step.
4. **Fail closed** when a security or compliance check is unavailable, and make the failure visible in logs.
5. **Treat every external response as untrusted input:** parse it into a Pydantic model and handle missing or extra fields.
6. **Entity-level status changes do not silently cascade** to every related user; each person's status is managed by its own operation.

## 16.6 Environment and process

- A script that touches the models may need to import the app module first because of a circular import between models; fix the cycle with function-local imports when you can.
- Some environments (dev or QA databases) are reachable only over VPN; plan test data and CI access accordingly.
- Post a new comment on the ticket for every change; never edit an old one, so the history stays truthful.

## 16.7 How to use this chapter

- Changing a calculation: list every call site first and test each.
- Adding a guard: test it against existing production-shaped data, not only new data.
- Reviewing: ask "what happens when two of these run at once?" and "what happens when more than one row matches?".
