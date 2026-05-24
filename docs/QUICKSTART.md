# Quickstart Guide

Get your first eval run in 5 minutes.

## 1. Create an account

```bash
curl -X POST https://api.lucenteval.dev/v1/accounts \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com"}'
```

## 2. Create an API key

```bash
curl -X POST https://api.lucenteval.dev/v1/keys \
  -H "Authorization: Bearer <your_key>" \
  -H "Content-Type: application/json" \
  -d '{"name": "My First Key", "scopes": ["run:create", "run:read", "prompt:read"]}'
```

Save the `raw_key` — it's shown once.

## 3. Submit your agent

Your agent must expose an OpenAI-compatible chat completions endpoint:

```
POST https://your-agent.example.com/v1/chat/completions
{
  "messages": [{"role": "user", "content": "...adversarial prompt..."}]
}
```

## 4. Create a run

```bash
curl -X POST https://api.lucenteval.dev/v1/runs \
  -H "Authorization: Bearer lev_yourkeyhere" \
  -H "Content-Type: application/json" \
  -d '{
    "endpoint_url": "https://your-agent.example.com/v1/chat/completions",
    "headers": {"Authorization": "Bearer your-agent-key"},
    "corpus_version": "v1"
  }'
```

Returns `{ "id": "run_uuid", "status": "pending", ... }`.

## 5. Poll for results

```bash
curl https://api.lucenteval.dev/v1/runs/<run_id> \
  -H "Authorization: Bearer lev_yourkeyhere"
```

Once `status == "completed"`, you'll see all 6 dimension scores.

## 6. View on the leaderboard

Visit [lucenteval.dev/leaderboard](https://lucenteval.dev/leaderboard) to see where your agent ranks.

## 7. Add to CI (optional)

```yaml
- uses: lucent-eval/run-action@v1
  with:
    api_key: ${{ secrets.LUCENT_API_KEY }}
    endpoint_url: ${{ secrets.AGENT_ENDPOINT }}
    min_composite_score: "0.75"
```
