import os

# Must be set before app modules read settings.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core import rate_limit  # noqa: E402
from app.core.deps import get_db  # noqa: E402
from app.core.security import hash_password, permission_resolver  # noqa: E402
from app.core.seed import seed_defaults  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, Organization, User  # noqa: E402

PASSWORD = "password123"


@pytest.fixture(autouse=True)
def _reset_process_state():
    """Rate-limit counters and the permission cache are process-global; isolate every test."""
    rate_limit.set_backend(None)
    permission_resolver.invalidate()
    yield
    rate_limit.set_backend(None)
    permission_resolver.invalidate()


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    seed_defaults(session)
    yield session
    session.close()
    engine.dispose()


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_org(db, name: str = "Org") -> Organization:
    org = Organization(name=name)
    db.add(org)
    db.commit()
    return org


def make_user(db, email: str, role: str = "user", status: str = "active", org: Organization | None = None) -> User:
    user = User(
        email=email,
        name=email.split("@")[0],
        hashed_password=hash_password(PASSWORD),
        role=role,
        status=status,
        organization_id=org.id if org else None,
    )
    db.add(user)
    db.commit()
    return user


def login(client, email: str, password: str = PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def auth_headers(client, email: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {login(client, email).json()['data']['accessToken']}"}


@pytest.fixture()
def admin_headers(client, db):
    make_user(db, "admin@example.com", role="admin")
    return auth_headers(client, "admin@example.com")
