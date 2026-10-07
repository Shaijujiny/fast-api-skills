"""Engine and session factory (blueprint ch. 7.1). Feature code never builds connections."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.postgresql.config import PostgresqlSettings, get_url

_url = get_url()
if _url.startswith("sqlite"):
    _kwargs = {"connect_args": {"check_same_thread": False}}
else:
    _s = PostgresqlSettings()
    _kwargs = {"pool_recycle": 1800, "pool_size": _s.pool_size, "max_overflow": _s.max_overflow}
engine = create_engine(_url, pool_pre_ping=True, **_kwargs)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
