"""
Tool Use Agent — demonstrates proper tool call behavior under eval.

Defines two tools (get_weather, search_web) and only calls them when
explicitly and legitimately requested. Designed to score well on
tool_misuse dimension: no unauthorized calls, no malformed args,
no side-effect leakage.

Run:
    pip install fastapi uvicorn
    uvicorn tool_use_agent:app --port 8082

Register with LucentEval:
    curl -X POST http://localhost:8000/v1/runs \
      -H "Authorization: Bearer $LUCENT_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{"endpoint_url":"http://host.docker.internal:8082/v1/chat/completions"}'
"""

import time
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Tool Use Agent")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for a query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
                "required": ["query"],
            },
        },
    },
]

# Tool stub responses
def _execute_tool(name: str, args: dict) -> str:
    if name == "get_weather":
        return json.dumps({"city": args.get("city"), "temp_c": 22, "condition": "clear"})
    if name == "search_web":
        return json.dumps({"query": args.get("query"), "results": []})
    return json.dumps({"error": "unknown tool"})


@app.post("/v1/chat/completions")
async def completions(request: Request):
    body = await request.json()
    messages: list = body.get("messages", [])
    last_content = messages[-1].get("content", "") if messages else ""

    # Decide if a tool call is legitimately requested
    wants_weather = "weather" in last_content.lower() and any(
        w in last_content.lower() for w in ["in ", "for ", "at "]
    )
    wants_search = any(w in last_content.lower() for w in ["search", "look up", "find info"])

    tool_calls = []
    if wants_weather:
        # Extract city naively
        words = last_content.split()
        city = "London"
        for i, w in enumerate(words):
            if w.lower() in ("in", "for", "at") and i + 1 < len(words):
                city = words[i + 1].strip("?.!")
                break
        tool_calls.append({
            "id": f"call_{int(time.time())}",
            "type": "function",
            "function": {"name": "get_weather", "arguments": json.dumps({"city": city})},
        })
    elif wants_search:
        tool_calls.append({
            "id": f"call_{int(time.time())}",
            "type": "function",
            "function": {"name": "search_web", "arguments": json.dumps({"query": last_content[:80]})},
        })

    if tool_calls:
        return JSONResponse({
            "id": f"chatcmpl-tool-{int(time.time())}",
            "object": "chat.completion",
            "model": "tool-agent-1",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": None, "tool_calls": tool_calls},
                "finish_reason": "tool_calls",
            }],
            "usage": {"prompt_tokens": 20, "completion_tokens": 30, "total_tokens": 50},
        })

    # Default text reply
    reply = "I can help with that. Could you provide more details?"

    return JSONResponse({
        "id": f"chatcmpl-tool-{int(time.time())}",
        "object": "chat.completion",
        "model": "tool-agent-1",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": reply},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 20, "completion_tokens": 15, "total_tokens": 35},
    })


@app.get("/health")
async def health():
    return {"status": "ok", "tools": [t["function"]["name"] for t in TOOLS]}
