import pytest


@pytest.mark.asyncio
async def test_create_account(client):
    resp = await client.post("/v1/accounts", json={"email": "test@example.com", "display_name": "Test User"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert "id" in data


@pytest.mark.asyncio
async def test_duplicate_email_rejected(client):
    await client.post("/v1/accounts", json={"email": "dupe@example.com"})
    resp = await client.post("/v1/accounts", json={"email": "dupe@example.com"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_invalid_email_rejected(client):
    resp = await client.post("/v1/accounts", json={"email": "not-an-email"})
    assert resp.status_code == 422
