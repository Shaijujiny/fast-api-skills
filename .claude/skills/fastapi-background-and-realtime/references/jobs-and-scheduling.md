# Jobs and scheduling

## Idempotency
- Use a unique key (`job_type + business_id`) with a unique index; insert-or-skip.
- Side effects check state first ("already sent/paid?"). External calls carry an idempotency key.

## Retries and dead-letter
```python
# Arq-style
async def send_receipt(ctx, receipt_id: int):
    ...
class WorkerSettings:
    functions = [send_receipt]
    max_tries = 5
    retry_jobs = True   # raise arq.Retry(defer=2 ** ctx["job_try"]) on transient errors
```
- Retry only transient errors (timeouts, 5xx); fail fast on validation errors.
- After max attempts: set status `dead`, keep payload + error, alert, provide a manual replay command.

## Job status table
`job(id, type, key UNIQUE, status, attempts, progress, result_ref, error, created_by, created_at, updated_at)`.
API: `POST` returns 202 + job id; `GET /jobs/{id}` (owner/permission scoped) returns status.

## Scheduler
- Run APScheduler in a dedicated `scheduler` process (replicas=1), jobs only enqueue work.
- If it must live in the app, take a lock per run: Redis `SET lock:<job> <id> NX EX <ttl>` or DB advisory lock / `SELECT ... FOR UPDATE SKIP LOCKED` on a due-jobs table.
- Make each tick idempotent (query "due and not yet enqueued", mark enqueued in same transaction).
- Store times in UTC; convert at the edge. Handle missed runs (`misfire_grace_time`, `coalesce=True`).

## Workers
- Graceful shutdown, task time limits, bounded concurrency, one DB session per job.
- Separate queues for slow vs urgent work.
