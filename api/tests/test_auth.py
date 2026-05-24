import pytest


async def _create_account_and_key(client, email="authtest@example.com"):
    acc_resp = await client.post("/v1/accounts", json={"email": email})
    assert acc_resp.status_code == 201

    # Create key — needs auth, but we need a bootstrap approach
    # In this test suite we directly insert via DB; here we test the unauthenticated path
    return acc_resp.json()


@pytest.mark.asyncio
async def test_unauthenticated_returns_401(client):
    resp = await client.get("/v1/runs")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_invalid_key_returns_401(client):
    resp = await client.get(
        "/v1/runs",
        headers={"Authorization": "Bearer lev_invalid_key_here"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_leaderboard_is_public(client):
    resp = await client.get("/v1/leaderboard")
    assert resp.status_code == 200
