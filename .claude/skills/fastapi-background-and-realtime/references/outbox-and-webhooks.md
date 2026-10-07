# Outbox, email/notifications, outbound webhooks

## Outbox pattern
- In the same transaction as the business change, insert `outbox(id, type, payload, status, attempts, next_attempt_at)`.
- A worker polls with `FOR UPDATE SKIP LOCKED`, sends, marks `sent`; on failure increments attempts with backoff; after max -> `dead` + alert.
- Guarantees no message for a rolled-back change and none lost on crash. Consumers must tolerate duplicates.
- Email/SMS/push: store template key + params (not rendered secrets), respect user preferences and quiet hours, localise via i18n keys.

## Outbound webhooks
- Subscriptions table: url, secret, events, active. HTTPS only; block private/internal IPs (SSRF) and limit redirects.
- Sign: `HMAC-SHA256(secret, f"{timestamp}.{body}")` in `X-Signature` with `X-Timestamp`; receivers reject old timestamps. Support secret rotation.
- Include event id (idempotency) and type; small payload, receiver fetches detail.
- Short timeouts (5-10s); retry on non-2xx/timeouts with exponential backoff over hours; auto-disable after sustained failure; delivery log per attempt (status, latency, no secrets).
- Inbound webhooks (e.g. payment providers): verify signature on raw body, dedupe by event id, respond fast, process in a job.
