# Example Agents

Three reference agents for testing Lucent Eval locally.

| Agent | Port | Description | Expected strength |
|-------|------|-------------|-------------------|
| `echo_agent.py` | 8080 | Hardcoded refusals + echo | Adversarial ↑ |
| `openai_proxy_agent.py` | 8081 | GPT-4o-mini passthrough | Balanced |
| `tool_use_agent.py` | 8082 | Legitimate tool calls only | Tool Misuse ↑ |

## Quick start

```bash
pip install fastapi uvicorn httpx openai

# Terminal 1 — echo agent
uvicorn echo_agent:app --port 8080

# Terminal 2 — OpenAI proxy (needs key)
OPENAI_API_KEY=sk-... uvicorn openai_proxy_agent:app --port 8081

# Terminal 3 — tool use agent
uvicorn tool_use_agent:app --port 8082
```

Then register any of them with Lucent Eval:

```bash
# Get an API key from the dashboard → Settings
curl -X POST http://localhost:8000/api/v1/runs \
  -H "X-API-Key: lev_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"endpoint_url": "http://host.docker.internal:8080/v1/chat/completions"}'
```

> **Docker note:** from inside Docker Compose, use `host.docker.internal` to reach
> agents running on your host machine. If running everything on bare metal, use `localhost`.
