# 7. Database, Transactions & Concurrency

Stack: SQLAlchemy 2.x with Alembic migrations on MySQL or PostgreSQL. Names are defaults; follow the project's equivalents.

## 7.1 Engine and session

Configure the engine and session factory in one module (for example `app/database/session.py`):

- Engine with `pool_pre_ping=True`, a sized pool, and `pool_recycle` below the DB/proxy idle timeout. Feature code never builds connections.
- Session factory with `autocommit=False` and `autoflush=False` (or know the consequence of autoflush). With autoflush off, pending changes are **not** visible to later queries until you `flush()` or `commit()`.
- MySQL reports "matched" vs "changed" rows depending on the `FOUND_ROWS` client flag; PostgreSQL reports matched. Do not rely on `rowcount == 0` to detect "nothing changed"; re-read or use a version column.
- `get_db()` yields a session per request and closes it in `finally`. A context-manager equivalent serves schedulers, workers, and scripts.

```python
with session_scope() as db:
    ...
    db.commit()
```

## 7.2 Transactions

- A write is not durable until `db.commit()`. Commit once at the end of the unit of work, not after every row, unless partial progress is intentional (batch jobs).
- If a handled failure can leave a half-applied session (external call failed after local changes), call `db.rollback()` **before** raising or continuing. A poisoned session breaks every later query in the same request.
- Never swallow a DB exception and carry on with the same session.
- Keep a transaction short: do validation and external calls before taking locks; mutate and commit quickly.
- Calling an external service while holding a row lock is allowed only with a short timeout and a clear rollback path (7.10).

## 7.3 Models

```python
class Booking(Base):
    __tablename__ = "bookings"
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    __table_args__ = (CheckConstraint("amount >= 0", name="ck_bookings_amount_nonneg"),)
```

- Use SQLAlchemy 2.0 typing: `Mapped[...]` plus `mapped_column(...)`.
- Follow the project's naming convention for tables and columns; set a `MetaData(naming_convention=...)` so constraint names are stable for Alembic. Never rename existing columns without a migration and a compatibility plan.
- Money columns: `Numeric(18, 2)` (or the precision the domain needs) with a non-negative `CheckConstraint` where the rule demands it. Never `Float`.
- Use `ForeignKey`, `CheckConstraint`, `UniqueConstraint`, and indexes at the model level.
- Identifiers exposed to clients are UUIDs/public ids, not auto-increment ids.
- Sensitive columns use an encrypted column type or application-level encryption (section 8.4).

## 7.4 Collation and charset (MySQL note)

On MySQL, a new table's collation must **match the tables it references**; a mismatch breaks foreign keys and JOINs (errors 3780, 1267).

- Pick one charset/collation per project (for example `utf8mb4` with the server's default collation) and use it everywhere.
- Before writing DDL for a FK to an existing table, check it: `SHOW FULL COLUMNS FROM <table>;` or `SHOW TABLE STATUS WHERE Name = '<table>';`.
- Declare it explicitly when it differs from the DB default:

```python
__table_args__ = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_general_ci"}
```

PostgreSQL has no equivalent FK problem, but state the database collation up front if text sorting or case-insensitive matching matters (consider `citext` or a functional index).

## 7.5 Concurrency (read this before touching balances, counters, seats, or status)

There is no global locking. Two requests, two pods, or a request and a scheduler can read the same row and both write. Lost updates on cached counters cause overselling, double booking, and over-credit.

Rules:

1. **Lock then check then write.** For any "read a row, decide, update it" flow on money, capacity, or status, load with `with_for_update()` (use the repository's `lock=True` flag). Examples: payment capture, exam attempt submit, interview slot booking, trip seat booking.
2. **Re-check status after locking.** The status you read before the lock may be stale. Validate the transition against the locked row, and return the existing result on a repeat call (idempotency).
3. **Never decrement or increment a cached counter from memory.** Recompute absolutely from the source rows (for example `COUNT` of confirmed bookings for seats taken) or update atomically in SQL (`col = col + :delta` under a lock).
4. **Lock order.** When a flow locks several tables or rows, always lock in the same order everywhere (for example order by id, or account then ledger) to avoid deadlocks.
5. **Scheduler vs request.** A scheduled job that touches the same rows must use the same locking; do not assume the job runs when nobody else is writing.
6. **Idempotent side effects.** External refunds, invoices, payments, and emails need a guard (status flag or unique reference) so a retry can't execute twice.
7. **Deadlock handling.** A deadlock (MySQL 1213, PostgreSQL 40P01) rolls back the transaction; surface a retryable error or retry once after `rollback()`, never continue on the dead session.

## 7.6 Migrations (Alembic)

Schema and data changes ship only as Alembic revisions, in the same PR as the ORM change.

- Generate with `alembic revision --autogenerate -m "<what>"`, then **read and edit** the result; autogenerate misses renames, server defaults, and data changes.
- **Reversible:** every revision has a working `downgrade()`. If a step truly cannot be reversed (dropped data), say so in the revision docstring and the PR.
- **Reviewed:** a second person reads the generated SQL (`alembic upgrade --sql`) for every revision; destructive changes (`DROP COLUMN`, `DROP TABLE`, type narrowing) need a stated reason and lead/DBA sign-off.
- **Safe on existing data:** add columns as nullable or with a `server_default`, **backfill**, then tighten to `NOT NULL` (in a later revision for large tables). Backfill in batches; keep data migrations separate from schema revisions where practical.
- **Large tables:** avoid long locks; add indexes online where the engine supports it (`CREATE INDEX CONCURRENTLY` on PostgreSQL, `ALGORITHM=INPLACE` on MySQL) and test the migration on production-sized data.
- **Single head:** one linear history; resolve multiple heads with a merge revision before merging the PR.
- **MySQL:** DDL is not transactional (a failed revision can leave partial changes), so keep each revision small. Set charset/collation explicitly (7.4).
- **PostgreSQL:** DDL is transactional; prefer one transaction per revision, except for `CONCURRENTLY` operations.
- Seed or reference data goes in revisions or an idempotent seed script, with a stable key and all supported languages for display text.
- Migrations run as a deploy step before the new app version starts, never at import time or on every app boot in multi-pod setups. Make them backward compatible with the previous app version (expand, then contract).
- User-facing change notes go in the changelog (section 12).

## 7.7 Indexing and performance of schema

- Add an index for every column used in new `WHERE`, `JOIN`, or `ORDER BY` paths on large tables (ledgers, logs, attempts, bookings, audit).
- Prefer composite indexes that match the filter plus sort.
- Don't add `LIKE '%term%'` search over big text columns without a plan (it cannot use a normal index; consider full-text or trigram indexes).

## 7.8 Scheduler jobs and data

- Job bodies live in one module (for example `app/jobs/`) and use the context-manager session.
- If every pod runs the scheduler, each job body must take a distributed lock first (Redis, or a DB advisory lock):

```python
async with job_lock("daily_settlement", ttl_seconds=1800) as acquired:
    if not acquired:
        return None
    with session_scope() as db:
        ...
```

- The lock uses an atomic `SET NX EX` and a compare-and-delete release so a run that outlives its TTL cannot delete a newer pod's lock. Choose a TTL longer than a normal run but short enough to recover from a crash.
- Register jobs with a stable `id` and `replace_existing=True`; add `max_instances=1` for long jobs and `misfire_grace_time` where a missed run should still fire.
- Jobs must be idempotent and safe to re-run. Prefer a dedicated worker or queue over in-process schedulers for heavy work.

## 7.9 Transaction lifecycle (commit-last rule)

```
Request
  ↓ Validate (schema, scope, status)
  ↓ Business logic
  ↓ DB mutations (add / update / flush)
  ↓ Final validation (invariants still hold)
  ↓ COMMIT   ← once, at the end of the successful operation
```

Mandatory rules:

- Transaction ownership is explicit: **the service owns commit and rollback**. Repositories do not commit.
- Commit **after the complete successful business operation**, not after each DB operation.
- Don't hide commits inside unrelated repository methods. A method that must commit is named and documented as such, and is the exception.
- Roll back on failure before re-raising or continuing.
- Keep related mutations in one transaction where atomicity is required (debit and credit, order status and line items, seat hold and booking).
- Use `db.flush()` when you need a generated id or DB state before the end (autoflush may be off, so flush explicitly); it does not commit.
- Don't commit between an external call and the local state that depends on it; decide the order (7.10).

```python
# MUST NOT: commit per operation
self.db.add(a); self.db.commit()
self.db.add(b); self.db.commit()     # a is durable even if b fails

# MUST
self.db.add(a)
self.db.add(b)
self.db.flush()                      # ids available
...final validation...
self.db.commit()
```

## 7.10 Critical rule: locks and slow external APIs

> Never hold a database lock while waiting for a slow external API unless there is a very specific transactional requirement.

A valid exception: locking a payment or refund record across the provider call so two operators can't trigger a duplicate refund. In that case:

1. Pass a short `timeout` to the client.
2. Re-check status after locking.
3. Record the provider reference so a retry is idempotent.
4. On failure `rollback()` and surface a retryable error.

Otherwise: do the external call first (or after commit) and use a status field plus a unique reference to make the step idempotent, instead of holding a lock open.

## 7.11 Concurrency toolbox

| Tool | Use |
|---|---|
| `SELECT ... FOR UPDATE` | `with_for_update()` via `lock=True` on a repository method, for read-decide-write on money/capacity/status; `skip_locked=True` for work queues |
| Atomic update | `UPDATE t SET c = c + :d WHERE id = :id AND c + :d <= :cap`; the affected-row count is only meaningful if you know the driver's semantics (7.1); prefer re-reading under lock |
| Optimistic locking | a version column compared in the `WHERE`; use when contention is low and a retry is acceptable |
| Unique constraints | the last line of defence for duplicates (references, idempotency keys, one booking per slot); catch `IntegrityError`, `rollback()`, return the existing result |
| Idempotency | a client-supplied `Idempotency-Key` or generated reference stored with a unique index |
| Isolation | MySQL default `REPEATABLE READ`, PostgreSQL default `READ COMMITTED`; know which applies, and lock or re-query when correctness depends on freshness |
| Duplicate requests | double-click or retry must produce one effect |

## 7.12 SQLAlchemy 2.x checklist

- `Mapped[...]` and `mapped_column(...)` throughout; `select()` style queries.
- Relationships only where they are used; avoid lazy-load loops (N+1); use joins/`selectinload` in the repository.
- Foreign keys, `CheckConstraint`s, and indexes defined on the model and mirrored in the Alembic revision.
- Optimize queries by reading the `EXPLAIN` plan, not by guessing.
