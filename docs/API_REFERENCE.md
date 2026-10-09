# API reference

The running API's `/openapi.json` is the machine-readable source of truth; `/redoc` renders it. The [README route table](../README.md#api-and-authorization) describes access and usage. All routes use `/v1`, without an `/api` prefix.

Protected calls use `Authorization: Bearer lev_…`. `POST /v1/accounts` returns an initial `raw_key` only once. Public routes are registration, leaderboard, readiness and API documentation/metrics. Admin operations use a separate `X-Admin-Token` and are disabled when no operator token is configured.

## Run submission

`POST /v1/runs`, scope `run:create`, optional account-scoped `Idempotency-Key`:

```json
{
  "endpoint_url": "https://agent.example.com/v1/chat/completions",
  "headers": {},
  "system_prompt": null,
  "corpus_version": "v1"
}
```

`201` returns a run record. The same idempotency key/input returns the original run; different input with that key returns `409`. No active prompts returns `422`. Missing credential encryption when headers are nonempty returns `503`. URL syntax and header boundary violations return `422` with validation details. DNS policy is rechecked at connection time and failures become bounded result errors.

Runs: `pending`, `running`, `completed`, `failed`. Result states: `pending`, `running`, `captured`, `scoring`, `scored`, `error`. A run is terminal only when every expected result is terminal. `completed_count` counts scored results; `failed_count` counts errors. Failed runs expose no composite ranking score.

`GET /v1/runs/{id}` adds scorer version, frozen weights/rates and manifest hash. `GET /v1/runs/{id}/results/{prompt_id}` adds frozen prompt, database response, recovery conversation, rationale, attempts and safe error code. Legacy traces may have null snapshots/responses. These routes and NDJSON export are owner-only with `run:read`; other accounts get `404`.

List APIs use one-based `page`. Run summary page size defaults to 20 (max 100); result/prompt/leaderboard pages default to 50 (max 200). Results and prompts are ordered by prompt ID. Exports use the same trace schema, one JSON object per line.

## Leaderboard and webhooks

`GET /v1/leaderboard` is public. Sort by `composite_score`, `score_adversarial`, `score_tool_misuse`, `score_hallucination`, `score_recovery`, `score_latency` or `score_cost`. Filters: `corpus_version`, `scorer_version` (default `v2`) and `manifest_sha256`. Endpoint URLs are reduced to origins for public output; owner detail still includes the complete submitted URL.

`POST /v1/webhooks` accepts `{"url":"https://receiver.example.com/events","description":"CI"}`. The response includes `signing_secret` once. Verify `X-LucentEval-Signature` against the **raw request bytes** using that secret, then deduplicate `event_id`. All terminal runs, including failures, create a durable delivery event for active hooks. See [credential and delivery semantics](../README.md#credentials-destinations-and-webhooks).

The API has no login/password/session endpoints, run cancellation endpoint or public raw-trace endpoint. It does not accept `X-API-Key` authentication.
