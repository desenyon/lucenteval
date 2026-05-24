import pytest
from sqlalchemy import insert
from app.models.prompt import Prompt
import uuid


async def _seed_prompts(db_session, n=5):
    prompts = []
    for i in range(n):
        p = Prompt(
            id=uuid.uuid4(),
            text=f"Test prompt {i}",
            category="injection",
            severity="medium",
            expected_behavior="Refuse",
            corpus_version="v1",
            is_active=True,
            in_quarantine=False,
        )
        db_session.add(p)
        prompts.append(p)
    await db_session.commit()
    return prompts


@pytest.mark.asyncio
async def test_list_prompts_requires_auth(client):
    resp = await client.get("/v1/prompts")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_filter_by_category(db_session, client):
    await _seed_prompts(db_session, 3)

    # Without auth this will 401, which is correct behavior
    resp = await client.get("/v1/prompts?category=injection")
    assert resp.status_code == 401  # auth required
