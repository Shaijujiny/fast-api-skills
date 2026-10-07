# Errors, alerts, SLOs, audit

## Error tracking (Sentry-style)
```python
import sentry_sdk
sentry_sdk.init(
    dsn=settings.sentry_dsn.get_secret_value(),
    environment=settings.app_env, release=settings.release,   # git SHA
    send_default_pii=False, traces_sample_rate=0.05,
    before_send=lambda event, hint: scrub(event),             # drop auth headers, bodies, emails
)
```
- Capture only unexpected exceptions (5xx); ignore `HTTPException` 4xx and validation errors.
- Tag with `request_id`: `sentry_sdk.set_tag("request_id", request_id_var.get())`; set user as internal id only.
- Upload release/SHA so errors map to deploys; alert on new issue in new release.
- Global handler returns generic body with request_id:
```python
@app.exception_handler(Exception)
async def unhandled(request, exc):
    log.exception("unhandled_error")
    return JSONResponse({"detail": "Internal error", "request_id": request_id_var.get()}, status_code=500)
```

## Health
Liveness = process only; readiness = DB/Redis. Add external uptime probe on a public-safe endpoint. Do not leak versions or dependency errors.

## SLOs and alerts
Example SLOs (tune per service): availability 99.9% of non-4xx requests per 30d; p95 latency < 500ms and p99 < 2s on critical endpoints.

| Alert | Condition (example) | Severity |
|---|---|---|
| High 5xx rate | 5xx / total > 2% for 5m | page |
| SLO burn | error budget burn > 14x over 1h and 5m | page |
| Latency | p95 > threshold for 10m | ticket/page |
| Readiness failing | any replica not ready > 2m | page |
| DB pool saturation | checked_out > 90% of max for 5m | warn |
| Slow queries | count > N / 10m | warn |
| Dependency errors | outbound failure rate > 10% for 5m | warn |
| Job/queue backlog | depth growing 15m or failures > N | warn |
| Restarts/OOM | restarts > 3 in 15m | warn |
| Auth anomalies | login failures spike | warn/security |
Each alert links a runbook: what it means, dashboards, first checks, rollback (see deploy skill). Avoid alerting on single errors or causes; alert on user-visible symptoms.

## Audit logs vs app logs
| | App logs | Audit logs |
|---|---|---|
| Purpose | Debug/operate | Accountability, compliance |
| Content | Technical events | Who did what to which resource, when, outcome, source IP, request_id |
| Storage | Stdout -> log platform | DB table or dedicated append-only sink |
| Mutability | Rotated | Append-only, tamper-evident, no update/delete |
| Retention | Days-weeks | Months-years per policy |
| Access | Engineers | Restricted, reviewed |

Audit: login/logout/failures, role/permission changes, money movement, PII read/export, config/admin actions, data deletion.
```python
class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(default=func.now(), index=True)
    actor_id: Mapped[int | None]
    action: Mapped[str] = mapped_column(String(64), index=True)   # "user.role_changed"
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(String(16))              # success | denied | failed
    ip: Mapped[str | None] = mapped_column(String(45))
    request_id: Mapped[str | None] = mapped_column(String(64))
    changes: Mapped[dict | None] = mapped_column(JSON)            # field names + before/after for non-sensitive fields only
```
Write the audit row in the same transaction as the change (so they commit or roll back together). Grant the app DB user INSERT/SELECT only on this table. Do not store secrets or full PII in `changes`.
