import asyncio
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.db.base import Base
from app.main import app
from app.models.enums import RoleEnum, MembershipStatus
from app.models.organization import Organization, OrganizationMember
from app.models.user import User

# Configure Celery in eager mode for tests
celery_app.conf.update(
    task_always_eager=True,
    task_eager_propagates=True,
    broker_connection_retry=False,
    broker_connection_max_retries=0,
)

# Use in-memory SQLite for super-fast, isolated automated testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def create_test_user(db_session: AsyncSession):
    async def _create(email: str, password: str = "Password123!", full_name: str = "Test User"):
        user = User(
            email=email.lower().strip(),
            hashed_password=get_password_hash(password),
            full_name=full_name,
            is_active=True,
            is_verified=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        token = create_access_token(subject=user.id)
        return user, token

    return _create


@pytest_asyncio.fixture
async def create_test_org(db_session: AsyncSession):
    async def _create(name: str, owner_user: User):
        org = Organization(name=name, slug=name.lower().replace(" ", "-"))
        db_session.add(org)
        await db_session.flush()

        member = OrganizationMember(
            organization_id=org.id,
            user_id=owner_user.id,
            role=RoleEnum.OWNER,
            status=MembershipStatus.ACTIVE,
        )
        db_session.add(member)
        await db_session.commit()
        await db_session.refresh(org)
        return org

    return _create
