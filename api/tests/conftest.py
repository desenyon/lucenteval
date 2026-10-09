"""Offline by default. PostgreSQL is opt-in via explicit TEST_DATABASE_URL variables."""

import base64
import os
from pathlib import Path

os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"0" * 32).decode())
os.environ.setdefault("ADMIN_TOKEN", "test-only-admin-token")
os.environ.setdefault("ARCHIVE_RESPONSES", "false")

import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app
from app.workers import tasks


@pytest.fixture
async def database(tmp_path, monkeypatch):
    async_url = os.environ.get("TEST_DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path}/test.db")
    sync_url = os.environ.get("TEST_DATABASE_URL_SYNC", f"sqlite:///{tmp_path}/test.db")
    if not async_url.startswith("sqlite"):
        assert make_url(async_url).database.endswith("_test"), "Refusing destructive tests outside a _test database"
        assert make_url(sync_url).database == make_url(async_url).database
    engine = create_async_engine(async_url)
    sync_engine = create_engine(sync_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    sync_factory = sessionmaker(sync_engine, expire_on_commit=False)
    monkeypatch.setattr(tasks, "_get_db_sync", sync_factory)
    queue = []
    monkeypatch.setattr(tasks, "_publish", lambda task, *args: queue.append((task, args)))
    yield factory, sync_factory, queue
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    sync_engine.dispose()


@pytest.fixture
async def db_session(database):
    async with database[0]() as session:
        yield session


@pytest.fixture
async def client(database, monkeypatch):
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.core.auth.get_redis", lambda: redis)
    monkeypatch.setattr("app.api.v1.health.get_redis", lambda: redis)

    async def override_get_db():
        async with database[0]() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    await redis.aclose()


@pytest.fixture
async def auth(client):
    response = await client.post("/v1/accounts", json={"email": "owner@example.com"})
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['raw_key']}"}
