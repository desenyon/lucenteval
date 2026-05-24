"""
OpenAI Proxy Agent — wraps an OpenAI model as a LucentEval-compatible endpoint.

Passes prompts straight through to GPT-4o-mini (cheap, fast).
Good baseline for measuring a real model's adversarial/hallucination scores.

Run:
    pip install fastapi uvicorn openai
    OPENAI_API_KEY=sk-... uvicorn openai_proxy_agent:app --port 8081

Register with LucentEval:
    curl -X POST http://localhost:8000/api/v1/runs \
      -H "X-API-Key: lev_your_key" \
      -H "Content-Type: application/json" \
      -d '{
            "endpoint_url": "http://host.docker.internal:8081/v1/chat/completions",
            "headers": {},
            "system_prompt": "You are a helpful, harmless, and honest assistant."
          }'
"""

import os
import time
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI(title="OpenAI Proxy Agent")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


@app.post("/v1/chat/completions")
async def completions(request: Request):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not set")

    body = await request.json()
    body["model"] = MODEL
    body.setdefault("max_tokens", 512)

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            OPENAI_URL,
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json=body,
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return JSONResponse(resp.json())


@app.get("/health")
async def health():
    return {"status": "ok", "model": MODEL}
