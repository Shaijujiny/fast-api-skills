---
description: Create and verify a reversible Alembic migration
---
Create a migration for: $ARGUMENTS

1. Change the SQLAlchemy model first; then `alembic revision --autogenerate -m "<short message>"`.
2. Review the generated file by hand: correct types (Numeric for money), nullability, defaults, indexes, constraints, naming; remove unrelated drift.
3. Make `downgrade()` truly reverse `upgrade()`. For data changes, backfill in batches and keep schema/data steps safe on large tables (add nullable -> backfill -> constrain).
4. Check chapter 7 of `fastapi-blueprint` for locking and long-running DDL risk.
5. Test on a scratch DB: `alembic upgrade head`, `alembic downgrade -1`, `alembic upgrade head`; confirm a single head (`alembic heads`).
6. Report the revision id, risks, and the commands actually run.
