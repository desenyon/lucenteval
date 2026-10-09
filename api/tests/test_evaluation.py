import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from sqlalchemy import select, update

from app.core.security import utcnow, verify_webhook_signature
from app.models import Delivery, Prompt, Result, Run
from app.services.manifest import digest
from app.workers import tasks


async def seed(db, recovery=False):
    prompt = Prompt(
        text="Write a report on climate change",
        category="multi_turn_trap" if recovery else "injection",
        severity="high",
        expected_behavior="Refuse unsafe instructions",
        corpus_version="v1",
    )
    db.add(prompt)
    await db.commit()
    return prompt


def response(text="I cannot comply with unsafe instructions."):
    return {
        "model": "mock-agent",
        "choices": [{"message": {"role": "assistant", "content": text}}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0},
    }


async def submit(client, auth, **extra):
    res = await client.post(
        "/v1/runs", headers=auth, json={"endpoint_url": "https://agent.example.com/evaluate", **extra}
    )
    assert res.status_code == 201, res.text
    return res.json()


@pytest.mark.asyncio
async def test_full_flow_frozen_recovery_trace_export_and_duplicate_tasks(
    client, auth, db_session, database, monkeypatch
):
    prompt = await seed(db_session, recovery=True)
    hook = await client.post("/v1/webhooks", headers=auth, json={"url": "https://receiver.example.com/events"})
    assert hook.status_code == 201
    run = await submit(client, auth, headers={"Authorization": "Bearer test-only-agent-token"})
    result_id = (await client.get(f"/v1/runs/{run['id']}/results", headers=auth)).json()[0]["id"]
    prompt.text = "Edited after submission"
    await db_session.commit()
    calls = []

    def fake_agent(url, headers, messages, key):
        calls.append((messages.copy(), key))
        assert headers == {"Authorization": "Bearer test-only-agent-token"}
        return response("I notice there was an error. Let me retry the report on climate change.")

    monkeypatch.setattr(tasks, "agent_response", fake_agent)
    with database[1]() as db:
        record = db.get(Run, uuid.UUID(run["id"]))
        assert record.headers == {}
        assert "test-only-agent-token" not in record.headers_encrypted
    tasks.run_prompt(run["id"], result_id)
    tasks.run_prompt(run["id"], result_id)
    assert len(calls) == 2
    assert calls[0][0][0]["content"] == "Write a report on climate change"
    assert calls[1][0][-1]["content"] != calls[0][0][0]["content"]
    assert calls[0][1].endswith(":initial") and calls[1][1].endswith(":recovery")
    tasks.score_result(run["id"], result_id)
    tasks.score_result(run["id"], result_id)
    done = (await client.get(f"/v1/runs/{run['id']}", headers=auth)).json()
    assert done["status"] == "completed" and done["completed_count"] == 1
    assert done["score_recovery"] == 1 and done["score_cost"] == 1
    trace = (await client.get(f"/v1/runs/{run['id']}/results/{prompt.id}", headers=auth)).json()
    assert trace["raw_payload"]["model"] == "mock-agent"
    assert trace["recovery_turns"][0]["raw_payload"]
    assert trace["prompt_snapshot"]["text"] == "Write a report on climate change"
    assert trace["attempt_count"] == 1 and trace["score_attempt_count"] == 1
    assert (
        digest(
            {
                "prompts": [trace["prompt_snapshot"]],
                "weights": done["weights_snapshot"],
                "rates": done["rates_snapshot"],
                "scorer_version": done["scorer_version"],
            }
        )
        == done["manifest_sha256"]
    )
    exported = await client.get(f"/v1/runs/{run['id']}/export", headers=auth)
    assert json.loads(exported.text) == trace
    with database[1]() as db:
        assert db.get(Run, uuid.UUID(run["id"])).headers_encrypted is None
        deliveries = db.scalars(select(Delivery)).all()
        assert len(deliveries) == 1
        delivery_id = str(deliveries[0].id)
    delivered = []

    def receive(url, *, body, headers, timeout):
        assert verify_webhook_signature(body, hook.json()["signing_secret"], headers["X-LucentEval-Signature"])
        assert json.loads(body)["event_id"] == headers["Idempotency-Key"] == delivery_id
        delivered.append(body)
        return b"ok"

    monkeypatch.setattr(tasks, "post_json", receive)
    tasks.deliver_webhook(delivery_id)
    tasks.deliver_webhook(delivery_id)
    assert len(delivered) == 1
    assert len((await client.get("/v1/leaderboard")).json()) == 1


@pytest.mark.asyncio
async def test_exhausted_agent_failure_finalizes_without_leaking_exception(
    client, auth, db_session, database, monkeypatch
):
    await seed(db_session)
    run = await submit(client, auth)
    result_id = (await client.get(f"/v1/runs/{run['id']}/results", headers=auth)).json()[0]["id"]

    def fail(*args):
        raise RuntimeError("SECRET and https://private.example/?api_key=SECRET")

    monkeypatch.setattr(tasks, "agent_response", fail)
    for _ in range(tasks.settings.MAX_WORK_ATTEMPTS):
        with database[1]() as db:
            db.execute(update(Result).values(next_attempt_at=None))
            db.commit()
        tasks.run_prompt(run["id"], result_id)
    done = (await client.get(f"/v1/runs/{run['id']}", headers=auth)).json()
    assert done["status"] == "failed" and done["failed_count"] == 1
    assert done["composite_score"] is None
    assert (await client.get("/v1/leaderboard")).json() == []
    with database[1]() as db:
        assert db.get(Result, uuid.UUID(result_id)).error == "agent_RuntimeError"


@pytest.mark.asyncio
async def test_stale_claim_is_fenced_and_reconciler_repairs_lost_publish(client, auth, db_session, database):
    await seed(db_session)
    run = await submit(client, auth)
    queue = database[2]
    result_id = (await client.get(f"/v1/runs/{run['id']}/results", headers=auth)).json()[0]["id"]
    with database[1]() as db:
        claimed, old_token = tasks._claim(db, run["id"], result_id)
        assert tasks._claim(db, run["id"], result_id) is None
        db.execute(
            update(Result).where(Result.id == claimed.id).values(lease_expires_at=utcnow() - timedelta(seconds=1))
        )
        db.commit()
    queue.clear()
    tasks.reconcile_work()
    assert (tasks.run_prompt, (run["id"], result_id)) in queue
    with database[1]() as db:
        new, new_token = tasks._claim(db, run["id"], result_id)
        assert old_token != new_token
        assert not tasks._store(db, new.id, old_token, {"status": "error"})
        assert tasks._store(db, new.id, new_token, {"status": "captured", "raw_payload": response()})
    queue.clear()
    tasks.reconcile_work()
    assert (tasks.score_result, (run["id"], result_id)) in queue
    tasks.score_result(run["id"], result_id)
    assert (await client.get(f"/v1/runs/{run['id']}", headers=auth)).json()["status"] == "completed"


@pytest.mark.asyncio
async def test_run_result_mismatch_and_idempotency(client, auth, db_session, database):
    await seed(db_session)
    keyed = {**auth, "Idempotency-Key": "submission-1"}
    run = await submit(client, keyed)
    again = await submit(client, keyed)
    assert run["id"] == again["id"]
    summaries = (await client.get("/v1/runs", headers=auth)).json()
    assert summaries[0]["endpoint_url"] == "https://agent.example.com/evaluate"
    conflict = await client.post("/v1/runs", headers=keyed, json={"endpoint_url": "https://different.example/"})
    assert conflict.status_code == 409
    other = await submit(client, auth)
    result_id = (await client.get(f"/v1/runs/{run['id']}/results", headers=auth)).json()[0]["id"]
    with database[1]() as db:
        assert tasks._claim(db, other["id"], result_id) is None
    second = await client.post("/v1/accounts", json={"email": "other@example.com"})
    wrong_auth = {"Authorization": f"Bearer {second.json()['raw_key']}"}
    for suffix in ("", "/results", "/export"):
        assert (await client.get(f"/v1/runs/{run['id']}{suffix}", headers=wrong_auth)).status_code == 404


@pytest.mark.asyncio
async def test_empty_corpus_rejected(client, auth):
    res = await client.post("/v1/runs", headers=auth, json={"endpoint_url": "https://agent.example.com"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_parallel_claim_and_finalization_once(client, auth, db_session, database, monkeypatch):
    await seed(db_session)
    await client.post("/v1/webhooks", headers=auth, json={"url": "https://receiver.example.com"})
    run = await submit(client, auth)
    result_id = (await client.get(f"/v1/runs/{run['id']}/results", headers=auth)).json()[0]["id"]
    calls = []
    monkeypatch.setattr(tasks, "agent_response", lambda *a: calls.append(a) or response())
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: tasks.run_prompt(run["id"], result_id), range(2)))
        list(pool.map(lambda _: tasks.score_result(run["id"], result_id), range(2)))
    assert len(calls) == 1
    with database[1]() as db:
        assert len(db.scalars(select(Delivery)).all()) == 1
        assert db.get(Run, uuid.UUID(run["id"])).status == "completed"


@pytest.mark.asyncio
async def test_score_failure_and_crash_budget_reach_terminal_state(client, auth, db_session, database, monkeypatch):
    await seed(db_session)
    run = await submit(client, auth)
    result_id = (await client.get(f"/v1/runs/{run['id']}/results", headers=auth)).json()[0]["id"]
    monkeypatch.setattr(tasks, "agent_response", lambda *a: response())
    tasks.run_prompt(run["id"], result_id)
    def fail(*args):
        raise ValueError("internal detail")
    monkeypatch.setattr(tasks.HallucinationScorer, "score", fail)
    for _ in range(tasks.settings.MAX_WORK_ATTEMPTS):
        with database[1]() as db:
            db.execute(update(Result).values(next_attempt_at=None))
            db.commit()
        tasks.score_result(run["id"], result_id)
    with database[1]() as db:
        result = db.get(Result, uuid.UUID(result_id))
        assert result.raw_payload == response() and result.status == "error"
        assert result.error == "scoring_ValueError"
        assert db.get(Run, uuid.UUID(run["id"])).status == "failed"
    # A worker that crashes every time must not be re-executed forever.
    second = await submit(client, auth)
    second_id = (await client.get(f"/v1/runs/{second['id']}/results", headers=auth)).json()[0]["id"]
    with database[1]() as db:
        for _ in range(tasks.settings.MAX_WORK_ATTEMPTS):
            assert tasks._claim(db, second["id"], second_id)
            db.execute(update(Result).where(Result.id == uuid.UUID(second_id))
                       .values(lease_expires_at=utcnow() - timedelta(seconds=1)))
            db.commit()
        assert tasks._claim(db, second["id"], second_id) is None
        assert db.get(Run, uuid.UUID(second["id"])).status == "failed"


@pytest.mark.asyncio
async def test_webhook_retry_uses_stable_payload_and_bounds_attempts(client, auth, db_session, database, monkeypatch):
    await seed(db_session)
    hook = await client.post("/v1/webhooks", headers=auth, json={"url": "https://receiver.example.com"})
    assert hook.status_code == 201
    run = await submit(client, auth)
    result_id = (await client.get(f"/v1/runs/{run['id']}/results", headers=auth)).json()[0]["id"]
    monkeypatch.setattr(tasks, "agent_response", lambda *a: response())
    tasks.run_prompt(run["id"], result_id)
    tasks.score_result(run["id"], result_id)
    with database[1]() as db:
        delivery_id = str(db.scalar(select(Delivery.id)))
    sent = []
    def fail(url, **kwargs):
        sent.append(kwargs["body"])
        raise RuntimeError("receiver unavailable")
    monkeypatch.setattr(tasks, "post_json", fail)
    for _ in range(tasks.settings.WEBHOOK_MAX_RETRIES + 1):
        with database[1]() as db:
            db.execute(update(Delivery).values(next_attempt_at=None))
            db.commit()
        tasks.deliver_webhook(delivery_id)
    assert len(set(sent)) == 1
    with database[1]() as db:
        assert db.get(Delivery, uuid.UUID(delivery_id)).status == "failed"
    tasks.deliver_webhook(delivery_id)
    assert len(sent) == tasks.settings.WEBHOOK_MAX_RETRIES + 1


@pytest.mark.asyncio
async def test_two_final_results_race_creates_one_notification(client, auth, db_session, database, monkeypatch):
    await seed(db_session)
    await seed(db_session)
    await client.post("/v1/webhooks", headers=auth, json={"url": "https://receiver.example.com"})
    run = await submit(client, auth)
    results = (await client.get(f"/v1/runs/{run['id']}/results", headers=auth)).json()
    monkeypatch.setattr(tasks, "agent_response", lambda *a: response())
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda row: tasks.run_prompt(run["id"], row["id"]), results))
        list(pool.map(lambda row: tasks.score_result(run["id"], row["id"]), results))
    with database[1]() as db:
        done = db.get(Run, uuid.UUID(run["id"]))
        assert done.status == "completed" and done.completed_count == 2
        assert len(db.scalars(select(Delivery)).all()) == 1


@pytest.mark.asyncio
async def test_public_leaderboard_redacts_path(client, auth, db_session, database, monkeypatch):
    await seed(db_session)
    run = await submit(client, auth)
    result_id = (await client.get(f"/v1/runs/{run['id']}/results", headers=auth)).json()[0]["id"]
    monkeypatch.setattr(tasks, "agent_response", lambda *a: response())
    tasks.run_prompt(run["id"], result_id)
    tasks.score_result(run["id"], result_id)
    public = (await client.get("/v1/leaderboard")).json()[0]
    assert public["endpoint_url"] == "https://agent.example.com"
    assert "headers" not in public and "headers_encrypted" not in public
