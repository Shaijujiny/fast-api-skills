"""Engine and session factory (blueprint ch. 7.1). Feature code never builds connections."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

_url = get_settings().database_url
_kwargs = {"connect_args": {"check_same_thread": False}} if _url.startswith("sqlite") else {"pool_recycle": 1800}
engine = create_engine(_url, pool_pre_ping=True, **_kwargs)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
