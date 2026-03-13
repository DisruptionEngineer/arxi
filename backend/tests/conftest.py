import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from arxi.auth.middleware import get_current_user
from arxi.auth.models import Role, User
from arxi.database import Base, get_db
from arxi.main import app

# Import ALL model modules so their tables are registered on Base.metadata.
# Uncomment each import as the corresponding task creates the module.
import arxi.modules.compliance.models  # noqa: F401
import arxi.auth.models  # noqa: F401                -- uncomment in Task 4
import arxi.modules.intake.models  # noqa: F401
import arxi.modules.patient.models  # noqa: F401

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
test_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_db():
    # Save and strip schemas for SQLite compatibility
    saved = {t: t.schema for t in Base.metadata.sorted_tables}
    for table in Base.metadata.sorted_tables:
        table.schema = None
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    # Restore schemas so metadata isn't permanently mutated
    for table, schema in saved.items():
        table.schema = schema


@pytest.fixture
async def db():
    async with test_session() as session:
        yield session


class _FakeUser:
    """Lightweight stand-in for User that doesn't need SQLAlchemy state."""

    def __init__(self, *, user_id: str, username: str, full_name: str, role: Role, is_active: bool = True):
        self.id = user_id
        self.username = username
        self.full_name = full_name
        self.role = role
        self.is_active = is_active


@pytest.fixture
async def client():
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


@pytest.fixture
async def admin_client():
    async def override_db():
        async with test_session() as session:
            yield session

    fake_admin = _FakeUser(
        user_id="test-admin-001",
        username="testadmin",
        full_name="Test Admin",
        role=Role.ADMIN,
    )

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: fake_admin
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)
