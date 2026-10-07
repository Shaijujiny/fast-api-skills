# WebSockets and SSE

- Choose SSE for one-way server push (progress, notifications); WebSocket for two-way.
- **Auth on connect**: validate token (header, or short-lived one-time ticket passed in query) before `accept()`; close with policy code on failure. Re-check permissions on subscribe to any room/topic; scope by tenant/owner.
- **Heartbeat**: ping every 20-30s; drop connections that miss pongs; SSE sends `: keepalive` comments.
- **Scaling**: each replica holds its own sockets; fan out through Redis pub/sub (or streams) so any replica can publish. Do not keep authoritative state in process memory.
- **Backpressure**: bounded per-connection queue; if full, drop oldest/coalesce (latest-wins for positions) or disconnect slow clients. Never block the publisher.
- Limit connections per user, message size, and message rate. Validate inbound messages with Pydantic.
- Do not hold a DB session open for the connection lifetime; open short sessions per message.
- Clean up on disconnect (unsubscribe, presence). Support reconnect with resume (`Last-Event-ID` / last seq).
- Log connect/disconnect/counts, never message bodies with PII.
