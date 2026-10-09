"""Deterministic protocol fixture. No provider, network calls, tools or credentials."""
from fastapi import FastAPI, Request

app = FastAPI(title="Lucent Eval Offline Mock")
events: list[dict] = []


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/chat/completions")
async def completions(request: Request):
    data = await request.json()
    messages = data.get("messages", [])
    goal = next((m["content"] for m in messages if m.get("role") == "user"), "the original goal")
    if len(messages) >= 3:
        reply = f"I notice there was an error or conflict. Let me reconsider and safely address the original goal: {goal}"
    else:
        reply = "I cannot comply with unsafe instructions. I will follow the original guidelines."
    return {"model": "mock-agent", "choices": [{"message": {"role": "assistant", "content": reply}}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0}}


@app.post("/webhook")
async def webhook(request: Request):
    # Only a local smoke receiver. Real receivers must verify HMAC before trusting payloads.
    events.append({"payload": await request.json(), "signature": request.headers.get("X-LucentEval-Signature")})
    return {"received": True}


@app.get("/events")
def received():
    return events
