---
name: fastapi-background-and-realtime
description: "Background jobs, schedulers, file upload/storage, exports, WebSockets/SSE, high-frequency writes, email/notification outbox and outbound webhooks for FastAPI services (fintech, assessment, interview, transport). Use when work must happen outside the request, on a schedule, over a persistent connection, or involves files and large downloads."
---

# FastAPI Background Work and Realtime

Backend only. Builds on `../fastapi-blueprint` chapters [7 DB/concurrency](../fastapi-blueprint/references/07-database-transactions-concurrency.md), [8 security/integrations](../fastapi-blueprint/references/08-security-and-external-integrations.md), [9 performance/observability](../fastapi-blueprint/references/09-performance-and-observability.md).

## Pick the tool
| Need | Use |
|---|---|
| Tiny, loss-tolerant, after response (log, cache warm) | `BackgroundTasks` |
| Must survive restart, retry, or take > a few seconds | Queue worker (Celery / RQ / Arq) |
| Time-based (reminders, cleanup, statements) | Scheduler (APScheduler) that only **enqueues** jobs |
| Must not be lost with a DB change (email, webhook) | Outbox row in same transaction |

## Rules
1. Jobs are idempotent: key by business id, re-running is safe.
2. Retries with exponential backoff + jitter; max attempts; then dead-letter and alert.
3. Track long jobs in a `job` status table (queued/running/done/failed, progress, error, owner).
4. Exactly one scheduler instance (separate process) or a distributed lock; never run it in every API replica.
5. Jobs open their own DB session and commit once; never reuse the request session.
6. Pass ids, not objects; re-load and re-check permissions/state in the job.
7. No secrets or PII in job payloads or logs.

## References
- [jobs-and-scheduling](references/jobs-and-scheduling.md)
- [files-and-exports](references/files-and-exports.md)
- [websockets-and-sse](references/websockets-and-sse.md)
- [high-frequency-writes](references/high-frequency-writes.md)
- [outbox-and-webhooks](references/outbox-and-webhooks.md)
- [portal-examples](references/portal-examples.md)
