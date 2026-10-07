# High-frequency writes

Problem: many tiny writes (location pings, exam autosave, telemetry) overwhelm the DB.

- Write to Redis first (latest value per key, or a stream/list), flush to DB in batches by a worker every N seconds or M items (`executemany` / bulk insert).
- "Latest wins" data (current position, draft answers): keep a per-key hash with a version/timestamp; reject stale writes.
- Append-only history: buffer then bulk insert; partition large tables by time; set retention.
- Accept fast: validate, enqueue, return 202/204. Rate-limit per user/device.
- Durability: decide acceptable loss window; for must-not-lose data (final submission) write synchronously to DB and commit once.
- Idempotent flush (client sequence number or unique key) so retries do not duplicate.
- On shutdown, flush buffers; on Redis loss, degrade to direct DB write with tighter limits.
