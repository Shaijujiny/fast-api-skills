# Per-portal examples

## Assessment
- Exam autosave: client sends answers every few seconds; write latest to Redis hash (`exam:{attempt}:answers`) with version, flush to DB in batch; final submit writes synchronously and commits once.
- Timers: server is the clock. Store `started_at`/`ends_at` in UTC, send remaining time via SSE/WebSocket; auto-submit via a scheduled job at `ends_at` (idempotent: skip if already submitted).
- Result exports and certificates: async job + signed URL.

## Interview
- Scheduling reminders: scheduler enqueues "due reminders" query results; outbox sends email/SMS at T-24h and T-1h; idempotent per (interview, channel, offset). Reschedule cancels pending outbox rows.
- Recordings: direct-to-storage presigned upload, virus/format check job, private bucket, short-lived playback URLs, retention policy then purge job.

## Transport
- Live location: drivers post pings -> Redis (latest per vehicle) + stream; batch history inserts; riders/dispatch get updates via WebSocket/SSE through Redis pub/sub, latest-wins with backpressure; scope subscriptions to the user's own trips/fleet.
- Trip reports: async export job.

## Fintech
- Payment webhooks (inbound): verify signature on raw body, dedupe by provider event id, enqueue job, update ledger in one transaction with `Decimal`; never trust client-reported status.
- Statements: scheduled monthly job per account (idempotent key `account+period`), generated to private storage, delivered via signed URL and notification outbox; PII masked, access audited.
- Outbound webhooks to merchants: signed, retried, delivery log.
