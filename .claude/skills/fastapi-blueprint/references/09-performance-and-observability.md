# 9. Performance & Observability

## 9.1 Sync vs async

Know whether your DB layer is sync (`Session`) or async (`AsyncSession`). With a sync session inside `async def` handlers, every query **blocks the event loop**, so either declare those handlers as plain `def` (FastAPI runs them in a threadpool) or use the async engine consistently. Never mix the two in one request path. Keep each blocking section short and keep genuinely slow work off the request path.

| Situation | Do |
|---|---|
| Quick DB read/write | inline in the service, through a repository method |
| Slow third-party call the user must wait for | integration client with an explicit timeout and bounded retries |
| Slow work the user doesn't wait for | `BackgroundTasks` for small jobs; a task queue (Celery, ARQ, RQ) for anything that must survive a restart |
| Periodic / batch | scheduler or cron job guarded by a distributed lock (Redis or DB advisory lock) |
| Heavy CPU (large report/PDF/XLSX) | keep it out of hot endpoints; generate asynchronously and serve the file from object storage |
| `time.sleep` | never inside a handler or service; use `await asyncio.sleep` where needed |

Never call `asyncio.run` inside a handler, and never hold a DB row lock across a slow call without a short timeout.

## 9.2 Query performance

- Paginate every list (`offset`/`limit` or cursor), return `total_count`, and cap `limit` (no `limit=100000`).
- Select only the columns or entities you need.
- No N+1: use joins, `selectinload`/`joinedload`, or a subquery in the repository; don't query inside a loop over result rows.
- Batch inserts and updates (`session.execute(insert(Model), rows)`, one `UPDATE ... WHERE id IN (...)`) instead of per-row commits.
- Index every new filter/sort/join column on large tables (payments, audit log, exam attempts, bookings).
- Prefer aggregate SQL (`SUM`, `COUNT`, `GROUP BY`) over loading rows to sum in Python.
- Check slow endpoints with `EXPLAIN` before and after.
- Dashboards and summaries compute in SQL in one repository method, not by calling other endpoints' logic.

## 9.3 Caching

- Cache read-heavy, rarely changing **GET** data (reference data, dashboards, public listings) with Redis through one shared cache helper or decorator.
  - Key = `namespace:resource:<normalized params>`; use a distinct namespace per resource family so it can be invalidated as a group.
  - Always set a TTL.
  - Invalidate on write: a mutation of the resource deletes its namespace keys.
  - Optionally expose `X-Cache: HIT|MISS` to verify behaviour.
- Never cache per-user sensitive data under a shared key (include the user or tenant in the key, or don't cache it).
- Redis is optional: the app must start and serve when it is unreachable. Cache and rate-limiter init is wrapped, logged as disabled, and new code must not hard-fail on a cache error (fall through to the DB).

## 9.4 Rate limiting

- Rate-limit login, OTP, password reset, payment initiation, and other abuse-prone routes (for example `fastapi-limiter` on Redis, or a gateway/WAF rule).
- Keep one blocklist mechanism for IP or client blocking; reuse it rather than adding another.

## 9.5 Logging

- `logger = logging.getLogger(__name__)` (or the project's `get_logger`). Never `print`.
- Levels: `info` for lifecycle and business milestones (job started, lock acquired), `warning` for degraded-but-working (Redis unavailable), `exception`/`error` for failures (`logger.exception` keeps the traceback).
- Use `%s` lazy formatting for logger arguments.
- **Never log:** passwords, tokens, OTPs, API keys, card/bank numbers, full national id/phone/email, request bodies of sensitive endpoints.
- Emit one structured access log from middleware (method, path, status, duration, request id) and filter health-check paths. Don't duplicate it per route.
- Include the entity id in business-event logs so an issue can be traced, for example `"Payment %s captured (attempt=%s)"`.
- Errors that pass through the global exception handlers are already logged there with traceback. Don't log the same exception again in the service before re-raising.

## 9.6 Observability of integrations

- Integration clients record elapsed time and status per call so third-party latency is visible.
- For scheduled jobs log start, skipped (lock held elsewhere), and finished (with counts) so a missed or double run is diagnosable.
- Use clear, searchable messages; one fact per line.

## 9.7 Resource limits

- Bound everything user-controlled: page size, list lengths in request bodies, upload size, export row counts (and require filters for exports).
- Stream or chunk large files and exports instead of building them in memory.
- Close what you open: DB sessions are closed by the `get_db` dependency; short-lived Redis clients and HTTP clients are closed in `finally` or a context manager.

## 9.8 Startup and shutdown

- Everything started in the app `lifespan` (Redis, scheduler, connection pools, HTTP clients) must be shut down in its `finally`.
- Startup failures of optional dependencies (Redis) log a warning and continue; failures of required ones (DB, config) fail fast.

## 9.9 Performance review questions

Ask these for every change:

1. How many rows can this touch in production, and is it paginated and indexed?
2. Does it hold a lock or the event loop longer than a few hundred milliseconds?
3. Can this run twice at once (two requests, two instances, scheduler)? What happens?
4. If Redis or the third party is down, does it fail safely?
5. Does any log line contain PII or a secret?

## 9.10 Performance checklist

Avoid N+1 queries; index properly; paginate; select only needed columns; use bulk operations; use connection pooling (set `pool_size`, `pool_pre_ping`, `pool_recycle`); cache with Redis where the data allows; no DB calls inside loops; avoid unnecessary serialization (don't `model_dump` then re-validate); no blocking I/O in async handlers; don't load large datasets into memory (stream or chunk).

> Performance optimization is **measurement-driven**, not speculative. Measure (timing, `EXPLAIN`, a profiler, load test) before and after, and record the numbers in the PR.

## 9.11 Observability: baseline and target

| Capability | Baseline / target |
|---|---|
| Structured access logging | middleware emits JSON logs; health checks filtered |
| Application logging | module loggers, JSON formatter in non-local environments |
| External API latency | recorded per call by the integration client |
| Request / correlation id | one middleware sets an id (accepts an inbound header), returns it as a response header, and puts it on every log line |
| Metrics (latency, errors, cache hit rate) | Prometheus or OpenTelemetry metrics: request rate, error rate, p50/p95/p99, DB pool usage |
| Tracing | OpenTelemetry on the HTTP, DB, and integration-client layers |
| Error monitoring | an error tracker (for example Sentry) fed by the global handlers |
| DB latency | slow-query log review and SQLAlchemy event timing |
| Health | `/health/live` (process up) and `/health/ready` (DB and required dependencies reachable) |

Anything a project lacks is a target: raise it as its own ticket rather than adding it ad hoc inside a feature PR.

## 9.12 Cache metrics and how to measure

| Question | How to answer it |
|---|---|
| Is this endpoint cached? | call it twice and read `X-Cache` (`MISS` then `HIT`) |
| How long until expiry? | `TTL <key>` in Redis, or an `Expires` header |
| What is cached? | list keys with `SCAN` (never `KEYS` in production) |
| Hit ratio | `INFO stats`: `keyspace_hits` vs `keyspace_misses` (instance-wide) |
| Is invalidation correct? | do a write, then a read; expect `MISS` |

Target: expose hit, miss, and invalidation counts per namespace through the metrics stack.

## 9.13 Measure before optimizing

1. Reproduce with realistic data volume (production-sized tables for query work).
2. Record a baseline: response time (p50/p95), query count, and `EXPLAIN` for the main query.
3. Change one thing.
4. Re-measure and put the before/after numbers in the PR.
5. If the improvement is small, don't merge the added complexity.
