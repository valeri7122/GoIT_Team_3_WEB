import asyncio
from unittest import mock

import pytest
import pytest_asyncio
from fastapi import status
from fastapi.testclient import TestClient
from fastapi_limiter.depends import RateLimiter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.database.connect import get_db
from app.database.models import Base, User
from app.services.auth import AuthService
from config import settings
from main import app
from sqlalchemy.pool import NullPool


async_engine = create_async_engine(
    settings.db_url,
    future=True,
    echo=True,
    poolclass=NullPool
)

TestAsyncSession = sessionmaker(async_engine, autocommit=False, autoflush=False, class_=AsyncSession)  # noqa


@pytest.fixture(scope="session")
def event_loop():
    """Overrides pytest default function scoped event loop"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


def pytest_configure(config):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())


@pytest_asyncio.fixture(scope="module")
async def session():
    async with TestAsyncSession() as session:  # noqa
        yield session


@pytest.fixture(scope="session")
def client() -> TestClient:
    async def override_get_db():
        async with TestAsyncSession() as session:  # noqa
            yield session

    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)


@pytest.fixture(scope="session")
def user() -> dict:
    return {
        "email": "email@test.com",
        "username": "test_user",
        "password": "test_pwd",
        "first_name": "Stepan",
        "last_name": "Giga",
    }


@pytest.fixture(scope="function")
def mock_rate_limit(mocker):
    mock_rate_limit = mocker.patch.object(RateLimiter, '__call__', autospec=True)
    mock_rate_limit.return_value = False


@pytest_asyncio.fixture(autouse=True)
async def mock_auth_redis(mocker):
    mock_redis = mocker.patch.object(AuthService, 'redis', autospec=True)
    mock_redis.get.return_value = None


@pytest_asyncio.fixture(scope="class")
async def access_token(client, user, session) -> dict:
    mock.patch('app.routes.auth.send_email_confirmed')

    res = client.post("/api/auth/signup", json=user)
    if res.status_code == status.HTTP_201_CREATED:
        user['id'] = res.json()['user']['id']

    current_user: User = await session.scalar(select(User).filter(User.email == user['email']))
    current_user.email_verified = True
    await session.commit()

    response = client.post(
        "/api/auth/login",
        data={"username": user.get('email'), "password": user.get('password')},
    )
    assert response.status_code == status.HTTP_200_OK

    return response.json()['access_token']
