---
name: fastapi-observability
description: Logging, metrics, tracing, error tracking, health, alerting and audit logging for FastAPI services - JSON logs with request/correlation IDs, redaction of secrets/PII, Prometheus/OpenTelemetry, RED metrics, DB pool and slow-query metrics, Sentry-style error tracking, SLOs. Use when adding or reviewing logging, monitoring, tracing, alerts or audit trails in a FastAPI backend.
---

# FastAPI Observability

FastAPI backends only. Standard: [../fastapi-blueprint ch.9](../fastapi-blueprint/references/09-performance-and-observability.md).
Deploy/health wiring: [../fastapi-deploy-ci](../fastapi-deploy-ci/SKILL.md).
Details and longer snippets in `references/`.

## Rules
1. **Structured JSON logs to stdout** only; the platform ships them. One event per line, stable keys.
2. **Every request gets a request ID** (accept inbound `X-Request-ID`, else generate; validate length/charset),
   bound to a `contextvars` var, included in every log line, and echoed in the response header and error body.
3. **Never log** passwords, tokens, API keys, auth headers, cookies, full card/ID numbers, OTPs, or raw
   request/response bodies. Redact by key name; log IDs not personal data. See `references/logging.md`.
4. **Levels**: DEBUG (dev only), INFO (business/lifecycle events), WARNING (recoverable, 4xx anomalies),
   ERROR (failed request/operation, 5xx, needs attention), CRITICAL (service cannot function). No error
   logs for expected 4xx validation failures.
5. **Log once** at the boundary: raise typed exceptions in services; log in the exception handler with
   `logger.exception` for unexpected ones. Do not log-and-reraise at every layer.
6. **Metrics**: RED per route template (Rate, Errors, Duration histogram) + DB pool + dependency latency.
   Label by route template (`/users/{id}`), never raw path or user id (cardinality). See `references/metrics-and-tracing.md`.
7. **Tracing**: OpenTelemetry auto-instrumentation for FastAPI, SQLAlchemy, httpx, Redis; propagate W3C `traceparent`;
   put `trace_id` in logs.
8. **Errors**: send unhandled exceptions to Sentry-style tracker with release + environment, scrub PII
   (`send_default_pii=False`, `before_send` filter), sample traces. See `references/errors-alerts-audit.md`.
9. **Health**: `/health/live` and `/health/ready` (snippets in deploy skill); exclude from access logs/metrics noise.
10. **Audit logs differ from app logs**: separate, append-only, who/what/when/outcome records of security and
    money-relevant actions, retained longer, stored in DB or dedicated sink. See `references/errors-alerts-audit.md`.
11. **Alerts on symptoms** (SLO burn, 5xx rate, latency, saturation), not every error. Each alert has a runbook.

## Minimal setup

```python
import contextvars, json, logging, sys, time, uuid
from fastapi import FastAPI, Request

request_id_var = contextvars.ContextVar("request_id", default="-")

class JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {"ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"), "level": record.levelname,
                "logger": record.name, "msg": record.getMessage(), "request_id": request_id_var.get()}
        data.update(getattr(record, "extra_fields", {}))
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data, default=str)

def setup_logging(level="INFO"):
    h = logging.StreamHandler(sys.stdout); h.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[h], force=True)

app = FastAPI()

@app.middleware("http")
async def request_context(request: Request, call_next):
    rid = request.headers.get("x-request-id", "")
    rid = rid if 8 <= len(rid) <= 64 and rid.isascii() and rid.replace("-", "").isalnum() else uuid.uuid4().hex
    token = request_id_var.set(rid)
    start = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        ms = round((time.perf_counter() - start) * 1000, 1)
        logging.getLogger("access").info("request", extra={"extra_fields": {
            "method": request.method, "path": request.scope.get("route").path if request.scope.get("route") else "unmatched",
            "duration_ms": ms}})
        request_id_var.reset(token)
    response.headers["X-Request-ID"] = rid
    return response
```
Note: `BaseHTTPMiddleware` is fine for this; use a pure ASGI middleware if streaming/perf matters. Log `status` from `response` too.
Correlation ID across services: forward `X-Request-ID` (or `traceparent`) on outbound httpx calls.

## Checklist
- [ ] JSON logs, request_id in every line and response header
- [ ] Redaction tested (unit test asserts secrets absent)
- [ ] RED metrics + DB pool gauges exposed, `/metrics` not public
- [ ] Traces and error tracker wired with release/env tags
- [ ] Alerts + runbook links; SLO defined for critical endpoints
- [ ] Audit log for auth, permission, money and PII-access events
