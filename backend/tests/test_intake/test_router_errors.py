import pytest
from httpx import ASGITransport, AsyncClient

from arxi.auth.middleware import get_current_user
from arxi.auth.models import Role
from arxi.database import get_db
from arxi.main import app
from tests.conftest import _FakeUser, test_session


@pytest.fixture
async def client(setup_db):
    async def override_db():
        async with test_session() as session:
            yield session

    fake_user = _FakeUser(
        user_id="test-user-001",
        username="testpharmacist",
        full_name="Test Pharmacist",
        role=Role.PHARMACIST,
    )

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: fake_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


async def test_approve_invalid_transition_returns_400(client):
    """Approving a non-existent rx should return 400 or 404, not 500."""
    resp = await client.post(
        "/api/intake/fake-id/approve",
        json={"pharmacist_id": "test-user-001", "notes": ""},
    )
    assert resp.status_code in (400, 404)
    assert "detail" in resp.json()


async def test_reject_invalid_transition_returns_400(client):
    """Rejecting a non-existent rx should return 400 or 404, not 500."""
    resp = await client.post(
        "/api/intake/fake-id/reject",
        json={"pharmacist_id": "test-user-001", "notes": ""},
    )
    assert resp.status_code in (400, 404)
    assert "detail" in resp.json()


async def test_newrx_invalid_xml_returns_400(client):
    """Posting invalid XML should return 400, not 500."""
    resp = await client.post(
        "/api/intake/newrx",
        content="not valid xml at all",
        headers={"Content-Type": "text/plain"},
    )
    assert resp.status_code == 400
    assert "detail" in resp.json()
