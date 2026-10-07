---
description: Add a new API endpoint following fastapi-blueprint (schemas -> repository -> service -> router -> register -> tests)
---
Add an endpoint: $ARGUMENTS

Follow the `fastapi-blueprint` skill. Read first: chapters 3, 4, 5, 6, 13 (and 7/8/15 if money, locks, auth or permissions are involved).

1. Pick the feature module (or create one); check for an existing similar endpoint to match conventions.
2. Schemas: request/response models (Pydantic v2), no ORM objects returned, validation and PII masking.
3. Repository: query/persist methods only; scope by owner/tenant; no commit here.
4. Service: business rules, permission checks, transaction, single commit.
5. Router: thin handler, correct verb/status/path, dependencies for auth + permission, response_model, i18n error keys.
6. Register the router in the app/router index.
7. Tests: success, validation error, unauthenticated, forbidden, out-of-scope data, edge cases.
8. Run lint and tests; report only what was actually run.
