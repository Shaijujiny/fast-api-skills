# Alembic migrations in deploy

See also blueprint ch.7.

## Order
1. CI builds image (SHA tag).
2. Deploy pipeline runs `alembic upgrade head` once, using the new image, as a one-off job
   (compose `migrate` service, k8s Job/pre-deploy hook, CI job). Fail the release if it fails.
3. Only then roll out new app replicas.
Take a DB backup/snapshot before prod migrations that alter or backfill data.

## Backward compatible (expand / contract)
Old code runs against the new schema during rollout, so every migration must be safe for N-1 code.

| Change | Release 1 (expand) | Release 2 (contract) |
|---|---|---|
| Add column | Add nullable / with server default; code writes it | Make NOT NULL after backfill |
| Rename column | Add new col, dual-write, backfill | Read new only; later drop old |
| Drop column | Stop reading/writing it in code | Drop in next release |
| Change type | Add new col, backfill, dual-write | Switch reads; drop old |
| Add index | `CREATE INDEX CONCURRENTLY` (Postgres) / online DDL (MySQL) | - |
| Add NOT NULL / FK | Add as NOT VALID / nullable, validate later | Validate / enforce |

- Large backfills: batch in a separate script/job, not inside the DDL migration; keep transactions short.
- Set `lock_timeout` (e.g. 5s) in migrations to avoid blocking traffic; retry rather than wait.
- Never edit a merged migration; add a new one. One head only (CI enforces).
- Data migrations must be idempotent.

## Rollback
- App rollback = redeploy previous image SHA. Works only if the schema is still compatible (hence expand/contract).
- `alembic downgrade -1` is for non-prod and emergencies; destructive downgrades lose data. Prefer
  roll-forward fix migration. CI checks that downgrade works, but prod rollback plan is "previous image".
- Contract (destructive) migrations ship only after the expand release has been stable for an agreed window.

## Env.py tips
Read URL from settings, not alembic.ini; set `compare_type=True`; import all models so `alembic check` is accurate.
