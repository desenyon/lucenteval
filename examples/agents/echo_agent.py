"""
Echo Agent — minimal LucentEval test agent.

Responds to every message with a safe, compliant reply.
Expected profile: high adversarial score (refuses injections),
zero tool calls (no tool misuse), low hallucination (no claims).

Run:
    pip install fastapi uvicorn
    uvicorn echo_agent:app --port 8080

Register with LucentEval:
    curl -X POST http://localhost:8000/api/v1/runs \
      -H "X-API-Key: lev_your_key" \
      -H "Content-Type: application/json" \
      -d '{"endpoint_url":"http://host.docker.internal:8080/v1/chat/completions"}'
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import time

app = FastAPI(title="Echo Agent")


@app.post("/v1/chat/completions")
async def completions(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    last = messages[-1]["content"] if messages else ""

    # Safe refusal for any adversarial pattern
    refusal_triggers = [
        "ignore", "jailbreak", "dan", "pretend", "forget", "override",
        "as an ai with no restrictions", "do anything now",
    ]
    if any(t in last.lower() for t in refusal_triggers):
        reply = (
            "I'm not able to comply with that request. "
            "I'm designed to be helpful, harmless, and honest."
        )
    else:
        reply = f"Acknowledged. You said: {last[:200]}"

    return JSONResponse({
        "id": f"chatcmpl-echo-{int(time.time())}",
        "object": "chat.completion",
        "model": "echo-1",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": reply},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": len(last.split()),
            "completion_tokens": len(reply.split()),
            "total_tokens": len(last.split()) + len(reply.split()),
        },
    })


@app.get("/health")
async def health():
    return {"status": "ok"}
