"""Exercise the real API, broker, workers, database, recovery and webhook outbox with a local mock."""
import json
import os
import time
import uuid

import httpx

api_url = os.environ.get("SMOKE_API_URL", "http://api:8000")
agent_url = os.environ.get("SMOKE_AGENT_URL", "http://mock-agent:8080")
with httpx.Client(base_url=api_url, timeout=30, trust_env=False) as client:
    account = client.post("/v1/accounts", json={"email": f"smoke-{uuid.uuid4().hex}@example.com"})
    account.raise_for_status()
    client.headers["Authorization"] = f"Bearer {account.json()['raw_key']}"
    seeded = client.post("/v1/admin/seed-corpus", headers={"X-Admin-Token": os.environ["ADMIN_TOKEN"]})
    seeded.raise_for_status()
    hook = client.post("/v1/webhooks", json={"url": f"{agent_url}/webhook"})
    hook.raise_for_status()
    body = {"endpoint_url": f"{agent_url}/v1/chat/completions"}
    key = uuid.uuid4().hex
    created = client.post("/v1/runs", json=body, headers={"Idempotency-Key": key})
    created.raise_for_status()
    run_id = created.json()["id"]
    repeated = client.post("/v1/runs", json=body, headers={"Idempotency-Key": key})
    assert repeated.json()["id"] == run_id
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        status = client.get(f"/v1/runs/{run_id}")
        status.raise_for_status()
        run = status.json()
        if run["status"] in ("completed", "failed"):
            break
        time.sleep(2)
    else:
        raise RuntimeError("Mock evaluation timed out")
    assert run["status"] == "completed", run
    assert run["completed_count"] == run["prompt_count"] > 0 and run["failed_count"] == 0
    exported = client.get(f"/v1/runs/{run_id}/export")
    exported.raise_for_status()
    rows = [json.loads(line) for line in exported.text.splitlines()]
    assert len(rows) == run["prompt_count"]
    assert all(row["raw_payload"] and row["prompt_snapshot"] and row["status"] == "scored" for row in rows)
    assert any(row["recovery_turns"] and row["score_recovery"] is not None for row in rows)
    # Beat must publish the durable outbox event, even after finalization has committed.
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        events = httpx.get(f"{agent_url}/events", trust_env=False).json()
        if any(event["payload"]["run_id"] == run_id for event in events):
            break
        time.sleep(2)
    else:
        raise RuntimeError("Webhook outbox was not delivered")
    print(json.dumps({"run_id": run_id, "status": run["status"], "prompts": len(rows),
                      "manifest_sha256": run["manifest_sha256"], "webhook": "delivered"}))
