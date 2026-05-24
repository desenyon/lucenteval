# Lucent Eval API Reference

Base URL: `https://api.lucenteval.dev/v1`

All requests require `Authorization: Bearer <api_key>` unless noted.

---

## Authentication

### Create Account
```
POST /accounts
```
Body: `{ "email": "you@example.com", "display_name": "Optional" }`

Returns: Account object with `id`.

### Create API Key
```
POST /keys
```
Requires auth. Body: `{ "name": "CI Key", "scopes": ["run:create", "run:read", "prompt:read"], "rate_limit_rpm": 60 }`

Returns: Key object + `raw_key` (shown once only). Store it securely.

### Revoke API Key
```
DELETE /keys/{key_id}
```

---

## Runs (M1, M5)

### Create Run
```
POST /runs
```
Body:
```json
{
  "endpoint_url": "https://your-agent.example.com/v1/chat/completions",
  "headers": { "Authorization": "Bearer sk-..." },
  "system_prompt": "optional",
  "corpus_version": "v1"
}
```
Returns: Run object with `id` and `status: "pending"`.

### Get Run
```
GET /runs/{run_id}
```
Returns full run with composite score, per-dimension scores, and latency percentiles.

### List Runs
```
GET /runs?page=1&page_size=20
```

### Get Per-Prompt Results
```
GET /runs/{run_id}/results?page=1&page_size=50
```

### Get Result Trace
```
GET /runs/{run_id}/results/{prompt_id}
```
Returns full trace: scores, rationale blobs, call graph, recovery turns.

### Export Run
```
GET /runs/{run_id}/export
```
Returns NDJSON stream of all prompt results.

---

## Prompts (M3)

### List Prompts
```
GET /prompts?category=injection&severity=high&version=v1&page=1&page_size=50
```

**Categories:** `injection` | `jailbreak` | `role_confusion` | `goal_hijack` | `tool_abuse` | `factual_trap` | `multi_turn_trap`  
**Severities:** `low` | `medium` | `high` | `critical`

### Contribute Prompt
```
POST /prompts/contribute
```
Body: `{ "text": "...", "category": "injection", "severity": "high", "expected_behavior": "..." }`

Prompt enters quarantine; not active until reviewed.

### Upvote Prompt
```
POST /prompts/{prompt_id}/upvote
```

---

## Leaderboard (M6) — public, no auth

```
GET /leaderboard?sort_by=composite_score&corpus_version=v1&page=1
```

Sort by any dimension: `composite_score`, `score_adversarial`, `score_tool_misuse`, `score_hallucination`, `score_recovery`, `score_latency`, `score_cost`.

---

## Webhooks (M7)

### Register Webhook
```
POST /webhooks
```
Body: `{ "url": "https://yourserver.com/hooks/lucent", "description": "optional" }`

Returns: Webhook object + `signing_secret` (shown once). Use it to verify `X-LucentEval-Signature` headers.

### Verify Signature
```python
import hmac, hashlib
expected = "sha256=" + hmac.new(signing_secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
assert hmac.compare_digest(expected, request.headers["X-LucentEval-Signature"])
```

### Webhook Payload
```json
{
  "run_id": "uuid",
  "status": "completed",
  "composite_score": 0.82,
  "scores_by_dimension": {
    "adversarial": 0.91,
    "tool_misuse": 0.88,
    "hallucination": 0.74,
    "recovery": 0.65,
    "latency": 0.80,
    "cost": 0.92
  },
  "run_url": "https://lucenteval.dev/runs/uuid"
}
```

Delivery: exponential backoff, 5 attempts, dead-letter after final failure.

---

## Health

```
GET /v1/health
```
No auth required. Returns: `{ "status": "ok" | "degraded", "checks": { "postgres": "ok", "redis": "ok" } }`

---

## Rate Limits

Default: 60 requests/minute per API key. Configure per-key at creation.

429 response includes `Retry-After: 60`.

---

## Scoring Weights (v1)

| Dimension     | Weight |
|---------------|--------|
| Adversarial   | 0.25   |
| Tool Misuse   | 0.20   |
| Hallucination | 0.20   |
| Recovery      | 0.15   |
| Latency       | 0.10   |
| Cost          | 0.10   |

Weight changes are versioned. Historical scores are never recomputed.
