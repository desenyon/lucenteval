"""Real loopback HTTP transport to the bundled mock, with disposable DB and ASGI API."""
import socket
import threading
import time

import pytest
import uvicorn
from examples.agents.mock_agent import app as mock_app
from examples.agents.mock_agent import events
from sqlalchemy import select

from app.core.config import get_settings
from app.models import Delivery
from app.workers import tasks
from tests.test_evaluation import seed


@pytest.mark.asyncio
async def test_real_http_mock_conversation_and_webhook(client, auth, db_session, database, monkeypatch):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(mock_app, log_level="critical", lifespan="off", ws="none"))
    thread = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
    events.clear()
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            assert time.monotonic() < deadline, "Mock server did not start"
            time.sleep(0.01)
        monkeypatch.setattr(get_settings(), "OUTBOUND_LOCAL_HOSTS", ["127.0.0.1"])
        await seed(db_session, recovery=True)
        hook = await client.post("/v1/webhooks", headers=auth, json={"url": f"http://127.0.0.1:{port}/webhook"})
        assert hook.status_code == 201
        created = await client.post("/v1/runs", headers=auth,
                                    json={"endpoint_url": f"http://127.0.0.1:{port}/v1/chat/completions"})
        assert created.status_code == 201
        run_id = created.json()["id"]
        # Drain the deterministic broker substitute, using real task/database/HTTP code.
        while database[2]:
            task, args = database[2].pop(0)
            task(*args)
        tasks.reconcile_work()
        while database[2]:
            task, args = database[2].pop(0)
            task(*args)
        done = (await client.get(f"/v1/runs/{run_id}", headers=auth)).json()
        assert done["status"] == "completed" and done["score_recovery"] == 1
        assert len(events) == 1 and events[0]["payload"]["run_id"] == run_id
        with database[1]() as db:
            assert db.scalar(select(Delivery)).status == "delivered"
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()
