# Logging

## Fields
Always: `ts, level, logger, msg, request_id`. Add when known: `trace_id, user_id (internal id), route, method, status, duration_ms, env, version`.
Use event-like messages (`"payment_captured"`) plus fields, not interpolated sentences.

```python
log.info("order_created", extra={"extra_fields": {"order_id": order.id, "amount_minor": order.amount}})
```

## Redaction
```python
SENSITIVE = {"password", "token", "access_token", "refresh_token", "authorization", "cookie",
             "secret", "api_key", "otp", "card_number", "cvv", "ssn", "national_id"}

def redact(obj):
    if isinstance(obj, dict):
        return {k: "***" if k.lower() in SENSITIVE else redact(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(i) for i in obj]
    return obj
```
Apply in the formatter to `extra_fields`. Also:
- Never log request bodies/headers wholesale. Log allow-listed fields.
- Mask PII when unavoidable (`a***@example.com`, last 4 digits) - prefer internal IDs.
- Pydantic: use `SecretStr` for secret fields; exclude with `Field(exclude=True)` in responses.
- SQLAlchemy `echo=True` logs parameters - never in prod. Set `sqlalchemy.engine` to WARNING.
- Third-party loggers (`httpx`, `uvicorn.access`, `sqlalchemy`) at WARNING/INFO as needed; httpx URLs may contain tokens in query strings - avoid putting secrets in URLs.
- Exception messages can embed data; review what is raised with user input.

## Uvicorn/gunicorn
Run with `--no-access-log` if app middleware emits the access line (avoids duplicates), or keep access log and skip the middleware line. Pick one.

## Retention
Short for debug-level app logs (days-weeks), longer for audit (see errors-alerts-audit.md). Sample noisy INFO in high-volume paths.

## Tests
```python
def test_no_secret_in_logs(caplog, client):
    client.post("/login", json={"email": "a@b.co", "password": "hunter2"})
    assert "hunter2" not in caplog.text
```
