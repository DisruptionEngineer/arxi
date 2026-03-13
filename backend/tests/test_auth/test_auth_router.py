import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from arxi.auth.models import Role
from arxi.auth.service import AuthService
from arxi.config import settings
from arxi.main import app
from arxi.database import get_db

# Re-use test DB from conftest (do NOT import setup_db — it's autouse via conftest)
from tests.conftest import test_session  # noqa: F401


def _make_token(username: str, role: str = "pharmacist") -> str:
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@pytest.fixture
async def seeded_db(db):
    """Create a test user in the DB."""
    svc = AuthService(db)
    await svc.create_user(
        username="testuser", password="testpass",
        full_name="Test User", role=Role.PHARMACIST,
    )
    return db


@pytest.fixture
async def raw_client(seeded_db):
    """Client WITHOUT auth overrides — tests real auth flow."""
    async def override_db():
        async with test_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    # Intentionally NOT overriding get_current_user
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)


async def test_me_with_cookie(raw_client):
    """GET /api/auth/me should work with cookie auth."""
    token = _make_token("testuser")
    raw_client.cookies.set("arxi_token", token)
    resp = await raw_client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "testuser"


async def test_me_with_bearer(raw_client):
    """GET /api/auth/me should work with Bearer auth."""
    token = _make_token("testuser")
    resp = await raw_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "testuser"


async def test_me_no_auth(raw_client):
    """GET /api/auth/me without auth should 401."""
    resp = await raw_client.get("/api/auth/me")
    assert resp.status_code == 401


async def test_login_success(raw_client):
    """POST /api/auth/login should set cookie and return user."""
    resp = await raw_client.post("/api/auth/login", json={
        "username": "testuser", "password": "testpass",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "testuser"
    assert data["role"] == "pharmacist"
    # Cookie should be set
    assert "arxi_token" in resp.cookies


async def test_login_bad_password(raw_client):
    """POST /api/auth/login with wrong password should 401."""
    resp = await raw_client.post("/api/auth/login", json={
        "username": "testuser", "password": "wrongpass",
    })
    assert resp.status_code == 401


async def test_login_nonexistent_user(raw_client):
    """POST /api/auth/login with unknown user should 401."""
    resp = await raw_client.post("/api/auth/login", json={
        "username": "nobody", "password": "testpass",
    })
    assert resp.status_code == 401


async def test_logout(raw_client):
    """POST /api/auth/logout should clear cookie."""
    resp = await raw_client.post("/api/auth/logout")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_login_then_me(raw_client):
    """Full flow: login -> me using cookie from login response."""
    login_resp = await raw_client.post("/api/auth/login", json={
        "username": "testuser", "password": "testpass",
    })
    assert login_resp.status_code == 200
    me_resp = await raw_client.get("/api/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "testuser"


async def test_change_password(raw_client):
    """PUT /api/auth/change-password should update password."""
    raw_client.cookies.set("arxi_token", _make_token("testuser"))
    resp = await raw_client.put("/api/auth/change-password", json={
        "old_password": "testpass",
        "new_password": "newpass123",
    })
    assert resp.status_code == 200

    raw_client.cookies.clear()
    resp = await raw_client.post("/api/auth/login", json={
        "username": "testuser", "password": "testpass",
    })
    assert resp.status_code == 401

    resp = await raw_client.post("/api/auth/login", json={
        "username": "testuser", "password": "newpass123",
    })
    assert resp.status_code == 200


async def test_change_password_wrong_old(raw_client):
    """PUT /api/auth/change-password with wrong old password should 400."""
    raw_client.cookies.set("arxi_token", _make_token("testuser"))
    resp = await raw_client.put("/api/auth/change-password", json={
        "old_password": "wrongpass",
        "new_password": "newpass123",
    })
    assert resp.status_code == 400
