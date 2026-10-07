# Files, storage, exports

## Upload validation
- Enforce max size while streaming (reject at limit, also set proxy limit); never `await file.read()` unbounded.
- Allow-list extensions and content types; verify **magic bytes** (e.g. `filetype`/`python-magic`), do not trust client type.
- Generate server-side object keys (uuid); never use the client filename in paths. Keep original name as metadata only.
- Virus-scan hook: store as `pending`, scan (ClamAV or provider) in a job, flip to `clean`/`rejected`; block download until clean.

## Storage
- S3-compatible (S3, MinIO, R2) via `boto3`/`aioboto3`. Buckets private; no public ACLs.
- Serve via short-lived presigned URLs (1-15 min) after a permission and data-scope check. Prefer direct-to-storage presigned PUT for large uploads, then a confirm endpoint that re-validates size/type.
- Stream large downloads (`StreamingResponse` over chunks) instead of loading into memory.
- DB stores key, size, content type, checksum, owner, status; not the bytes.
- Retention: lifecycle rules for temp/export files; delete or anonymise per policy; soft-delete DB row, purge object in a job.

## Exports and reports
- Large or slow: create a job, return 202, generate to storage, notify; download by signed URL.
- Small: stream rows with server-side cursor/chunks (`yield_per`), write CSV incrementally.
- Apply the same permission + data scoping as the list endpoint; mask PII per role; audit-log who exported what.
- Cap row counts / date ranges; guard against CSV formula injection (prefix `= + - @` cells).
