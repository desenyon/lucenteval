import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "checks" in data
