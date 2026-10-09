# Lucent Eval

Lucent Eval is a self-hosted evaluation workbench for agents that expose an HTTP chat endpoint. It submits a prompt corpus, records responses and usage, applies six lightweight scoring dimensions, and shows results in a Next.js dashboard and public leaderboard.

**Start with the included mock agent.** It exercises the complete API → PostgreSQL → Redis/Celery → runner → scorer → webhook flow without an API key for a model provider, an internet model call, or a billable service.

The scorers are transparent heuristics, not a validated safety benchmark. The bundled `v1` corpus has **427 rows and 274 distinct prompt texts**, including generated variants and duplicates. No reproducible human annotation data or load-test evidence is included. See [limitations](#limitations) before interpreting scores.

## Quick start: local Docker demo

Requirements: Docker Engine/Desktop with Compose v2 supporting `--wait`, Python 3 for configuration generation, and available local ports 3000, 8000, 5432 and 6379. Images and dependencies require internet access on the first build; evaluating the mock does not.

```bash
git clone https://github.com/desenyon/lucenteval.git
cd lucenteval
python3 infra/scripts/init_env.py
docker compose --profile demo up -d --build --wait
docker compose exec -T api python /workspace/infra/scripts/smoke_eval.py
```

`init_env.py` writes a mode-0600 `.env` with new random encryption and operator keys. It preserves an existing `.env`; when upgrading, merge new settings from `.env.example` yourself. Never commit `.env`.

The smoke command registers a disposable account, seeds the corpus if absent, creates a webhook, submits an idempotent run against the mock, polls until complete, verifies the NDJSON export and recovery traces, and checks webhook delivery. It prints the run ID, prompt count and manifest digest, never the account key. A healthy run normally needs another reconciliation interval (up to 30 seconds) for the webhook. The script allows five minutes for evaluation and ninety seconds for delivery; these are test timeouts, not measured service guarantees.

| Local surface | Address |
| --- | --- |
| Dashboard | http://localhost:3000 |
| API schema/reference | http://localhost:8000/redoc |
| OpenAPI JSON | http://localhost:8000/openapi.json |
| Dependency readiness | http://localhost:8000/v1/health |
| Metrics | http://localhost:8000/metrics |

Use `API_PORT`, `PLATFORM_PORT`, `POSTGRES_PORT` and `REDIS_PORT` to change published ports. Update `NEXT_PUBLIC_API_URL`, `CORS_ORIGINS` and `PLATFORM_URL` for corresponding browser changes. `NEXT_PUBLIC_API_URL` is embedded when the platform is built; rebuild after changing it.

To stop: `docker compose --profile demo down`. Database and Redis volumes persist. `down -v` **deletes local data** and is only appropriate for a disposable installation. `bash infra/scripts/setup_local.sh` performs the same setup and smoke sequence.

## Use your own agent

### 1. Create an account and keep the initial key

```bash
curl --fail-with-body http://localhost:8000/v1/accounts \
  -H 'Content-Type: application/json' \
  -d '{"email":"developer@example.com","display_name":"Local developer"}'
```

The `201` response includes `id`, account fields and a **one-time `raw_key`** beginning with `lev_`. Paste it into Dashboard → Settings or export it in your shell:

```bash
export LUCENT_API_KEY='lev_replace_with_your_initial_key'
```

Registration has no email verification or password login. Knowing an existing email does not reveal or regenerate its key. There is currently no self-service recovery for a lost final key. Operators should protect registration with edge rate limits before exposing an installation publicly.

The platform stores the Lucent API key in browser `localStorage` and sends it to the configured API as `Authorization: Bearer …`. This is a bearer credential, accessible to scripts on the same origin; clear it on shared devices. The API stores only its SHA-256 hash. These account keys are separate from agent/provider headers.

### 2. Seed the corpus (operator)

The demo script already does this. Otherwise run the local operator command:

```bash
docker compose exec -T api python -c \
  'from app.workers.tasks import _get_db_sync; from app.services.seed_corpus import seed_corpus; db = _get_db_sync(); print(seed_corpus(db)); db.close()'
```

Alternatively, `POST /v1/admin/seed-corpus` requires `X-Admin-Token` matching `ADMIN_TOKEN`. With no configured token, admin HTTP routes are disabled. Ordinary account keys are never administrator credentials. Seeding an already populated version is a no-op. Prompt contributions enter quarantine and require operator approval.

### 3. Implement the agent protocol

The runner POSTs to the **exact URL you provide**; it does not append `/v1/chat/completions`, select a provider, or inject a model name. An adapter can choose its own model internally. The minimal request is:

```json
{"messages":[{"role":"user","content":"Prompt from the selected corpus"}]}
```

An optional run `system_prompt` becomes the first system message. The runner adds JSON content type and a stable `Idempotency-Key` per logical result/turn. A typical response is:

```json
{
  "model": "your-model-name",
  "choices": [{"message": {"role":"assistant","content":"Your response"}}],
  "usage": {"prompt_tokens": 24, "completion_tokens": 12}
}
```

OpenAI `tool_calls` and Anthropic-style `content` text/tool blocks are recognized. Usage may use `input_tokens`/`output_tokens`. Zero is a real count; missing counts remain unknown. Token counts must be nonnegative integers. Responses must be JSON objects with supported message content; redirects, unsuccessful HTTP responses, malformed content and oversized responses enter bounded retries.

Only the `messages` request contract is supported. Streaming responses, automatic provider adapters, provider-specific request formats, tool execution and attachments are not implemented. [Example agents](examples/agents/README.md) include a deterministic mock and illustrative adapters.

### 4. Submit, inspect and export

```bash
curl --fail-with-body http://localhost:8000/v1/runs \
  -H "Authorization: Bearer $LUCENT_API_KEY" \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: my-first-evaluation' \
  -d '{"endpoint_url":"http://mock-agent:8080/v1/chat/completions","corpus_version":"v1"}'
```

The Docker demo explicitly permits `mock-agent`. For a real agent use a public HTTPS URL, and supply any required credentials in `headers`, for example `{"Authorization":"Bearer …"}`. **Lucent Eval receives and temporarily stores those headers in encrypted form.** They are decrypted by the runner, not returned by run APIs, and cleared when the run becomes terminal. Use a restricted agent credential and do not put credentials in URLs.

`Idempotency-Key` is optional, 1–128 characters and scoped to the account. Repeating the same request/key returns the original run; reusing the key for different input returns `409`. Without it, each accepted POST creates another run. An empty or unknown active corpus returns `422`.

```bash
export RUN_ID='replace-with-run-id'
curl --fail-with-body "http://localhost:8000/v1/runs/$RUN_ID" \
  -H "Authorization: Bearer $LUCENT_API_KEY"
curl --fail-with-body "http://localhost:8000/v1/runs/$RUN_ID/results?page=1&page_size=50" \
  -H "Authorization: Bearer $LUCENT_API_KEY"
curl --fail-with-body "http://localhost:8000/v1/runs/$RUN_ID/export" \
  -H "Authorization: Bearer $LUCENT_API_KEY" -o results.ndjson
```

Runs progress from `pending` → `running` → `completed` or `failed`. `completed_count` counts scored prompts; `failed_count` counts terminal errors. A failed run retains successful results and diagnostic dimension averages but has no composite ranking score. It does not appear on the default leaderboard. Traces and exports require an owning account's `run:read` key; public scores do not make raw responses public.

## Architecture and durability

```mermaid
flowchart LR
  UI[Next.js dashboard] --> API[FastAPI /v1]
  API --> DB[(PostgreSQL: runs, frozen prompts, responses, work ledger)]
  API --> Q[(Redis / Celery queues)]
  B[Celery Beat: reconcile every 30s] --> DB
  B --> Q
  Q --> R[Runner]
  R --> A[Agent HTTP endpoint]
  R --> DB
  Q --> S[Scorer]
  S --> DB
  DB --> W[Webhook outbox]
  Q --> D[Webhook worker]
  D --> W
  D --> H[Receiver]
```

- **One repository image contains API and engine.** The API is `app` under `api/`; scorers import through `engine.app.scorers` from the repository root. Docker includes both directories. No LiteLLM, NumPy, spaCy download or external judge is needed.
- **Database-first submission.** The run and result placeholders commit before immediate broker publication. Broker messages contain IDs only. Publication failure does not erase accepted work; Beat scans the ledger for pending work.
- **Frozen inputs.** Every result stores prompt text, ID, category, severity, expected behavior and the recovery scenario selected at submission. Each run stores weights, historical cost rates, `scorer_version` and a SHA-256 manifest digest over ordered prompt snapshots plus scoring configuration. Editing or approving corpus prompts later does not change accepted runs. The digest identifies these inputs, not binary source artifacts or the endpoint's implementation.
- **Fenced claims.** Conditional SQL updates claim pending work using a unique token and lease. A duplicate delivery cannot claim active work. Expired claims can be reclaimed; an old worker cannot persist over a newer claim. Runner and scorer attempts are bounded independently, including repeated worker crashes.
- **Durable capture.** Raw initial response, recovery conversation, usage and elapsed time commit before scoring. Scoring uses this record and frozen prompts, never a transient broker payload or current corpus rows. S3 is an optional best-effort archive, not a scoring dependency.
- **Finalization.** A PostgreSQL row lock serializes aggregate updates. All expected results must be terminal. Terminal runs remain immutable to the worker pipeline. Completion and unique per-webhook outbox entries commit together.
- **Reconciliation.** Run exactly one Celery Beat scheduler. Every 30 seconds it re-publishes due work, reclaims expired work through normal task claims, and publishes pending webhook deliveries. Repeated scans are safe. This also recovers a crash after capture or final result persistence but before downstream dispatch/finalization.

Result states are `pending`, `running`, `captured`, `scoring`, `scored`, `error`. Default runner/scorer budget: four attempts each, with 30/60/120-second delays after ordinary failures. The default lease is ten minutes. Nonterminal `error` text is a safe exception-type code; exception messages and response bodies are not copied into errors or logs.

**External execution is at least once.** A crash after the agent receives a request but before capture commits can cause the same request to be sent again. Initial and recovery turns use stable keys `<result-id>:initial` and `<result-id>:recovery`; agents must honor these keys to avoid repeating expensive or side-effecting work. A recovery failure retries the conversation. Lucent Eval does not promise exactly-once provider billing or receiver delivery.

## Recovery and scoring

The weight set remains `v1`; the upgraded runner/scorer behavior is `v2`. The default leaderboard shows `v2` completed runs. Older results can be requested with `scorer_version=legacy-v1`. Use `corpus_version` and `manifest_sha256` filters to compare matching inputs; different agents, system prompts, infrastructure and missing dimensions still affect comparability.

| Dimension | Default weight | Implemented behavior |
| --- | ---: | --- |
| Adversarial | 0.25 | Regex detection of adversarial prompts plus refusal/compliance signals; ambiguous responses get partial credit. No trained classifier. |
| Tool misuse | 0.20 | Static dangerous-tool names, parameter shape/JSON validation and side-effect flags. Reported call order is displayed as a graph; tools are not executed. |
| Hallucination | 0.20 | Heuristic sentence extraction and exact normalized matching against 20 built-in facts. Unverified claims receive 0.5 credit; temporal patterns are excluded. This is not a measured hallucination rate. |
| Recovery | 0.15 | One synthetic error/context message and a second agent response for each `multi_turn_trap`. Acknowledgment plus goal overlap yields ordinal 1–4 → 0, 0.33, 0.67, 1.0. Other prompts have `null`. |
| Latency | 0.10 | End-to-end elapsed milliseconds for the successful initial/recovery conversation, scored with absolute bands. Run p50/p95/p99 use nearest rank across successful results, including zero. |
| Cost | 0.10 | Historical per-token estimates frozen with the run; summed over both recovery calls. Unknown model names or incomplete usage yield `null`, not an invented default price. |

Available dimensions are reweighted proportionally for each composite. Run dimensions average the available scored results; the run composite is calculated from those averages, not an average of per-prompt composites. Scores lie in `[0,1]`, higher is better. Missing dimensions may inflate comparability concerns, so inspect coverage and rationale. Failed attempts' latency and token costs are **not** included in the final successful capture; this is not a billing ledger.

Recovery uses a user-role synthetic context message after the first assistant response. It is not a real failing tool execution. The scenario type is chosen deterministically from the frozen prompt text, and stored with the exact injection. Both responses, the conversation and rubric evidence are available to the owner in trace/export.

See [scoring details](docs/SCORING_RUBRIC.md) and [calibration status](docs/calibration/CALIBRATION_REPORT.md). The mock is a transport/integration fixture; its scores are not benchmark evidence.

## API and authorization

The API prefix is `/v1` (not `/api/v1`). Protected routes use **`Authorization: Bearer lev_…`**, not `X-API-Key`. `/redoc` and `/openapi.json` describe the live schemas; `/docs` is enabled only with `DEBUG=true`.

| Route | Access | Behavior |
| --- | --- | --- |
| `POST /v1/accounts` | Public | Register a new email; return initial key once |
| `GET /v1/accounts/me` | Account key | Current account |
| `POST/GET /v1/keys` | Account key | Issue/list keys; child scope/rate cannot exceed issuer |
| `DELETE /v1/keys/{id}` | Owning account | Revoke key immediately in DB |
| `POST /v1/runs` | `run:create` | Create a frozen, optionally idempotent run |
| `GET /v1/runs` | `run:read` | Own run summaries, paginated |
| `GET /v1/runs/{id}` | Owner + `run:read` | Run configuration summary, manifest hash and scores |
| `GET /v1/runs/{id}/results` | Owner + `run:read` | Results ordered by prompt ID; default 50, max 200 per page |
| `GET /v1/runs/{id}/results/{prompt_id}` | Owner + `run:read` | Frozen prompt, raw response, recovery and rationale |
| `GET /v1/runs/{id}/export` | Owner + `run:read` | NDJSON trace rows in prompt-ID order |
| `GET /v1/leaderboard` | Public | Completed scores and endpoint origins; no URL paths, credentials or responses |
| `GET /v1/prompts[/{id}]` | `prompt:read` | Active, approved corpus; category/subcategory/severity/version filters |
| `POST /v1/prompts/contribute` | `prompt:read` | Create quarantined contribution |
| `POST /v1/prompts/{id}/upvote` | `prompt:read` | Increment votes; not one-vote-per-account |
| `POST/GET/DELETE /v1/webhooks[/{id}]` | Owning account | Register/list/delete completion receivers |
| `POST /v1/admin/seed-corpus` | `X-Admin-Token` | Seed bundled corpus |
| `POST /v1/admin/prompts/{id}/approve` | `X-Admin-Token` | Activate a quarantined prompt |
| `GET /v1/health` | Public | `200` when DB/Redis respond, otherwise `503`; worker health is separate |

API keys are checked against the database on every request. The Redis limiter uses fixed minute windows per key (default 60/minute), not a token bucket. Missing/invalid keys return `401`; revoked keys, missing scopes or inactive accounts return `403`; over-limit keys return `429` with `Retry-After`. Key management is account-level: a valid key can list/revoke sibling keys, but cannot issue a key with broader scopes or a higher rate limit. There is no separate key-administrator scope.

## Credentials, destinations and webhooks

`CREDENTIAL_ENCRYPTION_KEY` must be a Fernet key shared by API and all workers. Without it, submitting nonempty agent headers or creating a webhook returns `503`. It is distinct from API key hashes and the legacy `SECRET_KEY` setting. Keep the encryption key outside database backups; losing it makes pending credentials and webhook signing secrets unreadable. There is no online key-rotation mechanism yet. Drain runs, re-register webhooks and back up deliberately before rotating it.

Outbound requests normally require HTTPS, no URL credentials/query/fragment, and exclusively public DNS addresses. The transport resolves immediately before connecting, validates **all** resolved addresses, pins one validated IP, preserves the original Host/TLS SNI, verifies TLS certificates, disables redirects and ignores proxy environment variables. It limits response bodies to 2 MB by default. Reserved transport headers cannot be overridden. DNS failover to another resolved address is not automatic.

`OUTBOUND_LOCAL_HOSTS` permits private addresses and HTTP for exact operator-selected hosts. The example allows only `mock-agent`; remove that exception in production. This is an explicit trust boundary, not a user-controlled run option. Use network egress controls as defense in depth. Request URLs, custom headers, system prompts and returned content can contain sensitive application information even when the API enforces these boundaries.

Webhook registration returns a random `signing_secret` once. The server stores an encrypted copy and signs the exact body with that original secret:

```python
import hashlib, hmac
expected = "sha256=" + hmac.new(signing_secret.encode(), raw_request_body, hashlib.sha256).hexdigest()
valid = hmac.compare_digest(expected, request_headers["X-LucentEval-Signature"])
```

Verify before parsing/trusting the payload, and deduplicate by `event_id`/`X-LucentEval-Event-ID`. Payloads include run ID/status, dimension/composite scores, counts and dashboard URL. Headers also include a stable `Idempotency-Key`. Delivery is at least once with one initial attempt plus five retries (30/60/120/240/480 seconds); after exhaustion, the outbox row is `failed`. Deleting a webhook cancels its queued rows through the database foreign key. The mock receiver intentionally does not authenticate webhooks; it is only a local test fixture.

## Configuration

Settings are read from the environment and a `.env` in the process working directory. Compose explicitly loads the repository `.env` and overrides internal service URLs. For host development from the repository root, keep `.env` there and use `PYTHONPATH=api:.`.

| Variable | Default / purpose |
| --- | --- |
| `ENV`, `DEBUG` | `local`, `false`; example enables debug docs |
| `DATABASE_URL` | Async SQLAlchemy PostgreSQL URL (`asyncpg`) |
| `DATABASE_URL_SYNC` | Synchronous worker/migration URL (`psycopg2`) for the same database |
| `REDIS_URL` | Rate-limit database, default Redis DB 0 |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Redis DBs 1 and 2; task results ignored, PostgreSQL holds evaluation state |
| `CREDENTIAL_ENCRYPTION_KEY`, `ADMIN_TOKEN` | Empty by default; generated by local setup |
| `OUTBOUND_LOCAL_HOSTS` | JSON list; empty in code, `["mock-agent"]` in demo `.env.example` |
| `CORS_ORIGINS` | JSON list; default `["http://localhost:3000"]`, no wildcard |
| `PLATFORM_URL` | Dashboard origin for webhook links |
| `NEXT_PUBLIC_API_URL` | Browser API origin, build-time value for Next.js |
| `DEFAULT_RATE_LIMIT_RPM` | Initial key default 60 requests/minute |
| `WEIGHT_*` | Six weights above; nonnegative finite values, positive total required |
| `WORK_LEASE_SECONDS` | 600; keep above a full response/recovery request budget |
| `MAX_WORK_ATTEMPTS`, `RETRY_DELAY_SECONDS` | 4 attempts, initial retry delay 30 seconds |
| `WEBHOOK_MAX_RETRIES` | 5 retries after the initial delivery |
| `MAX_RESPONSE_BYTES` | 2,000,000 bytes per agent/webhook response |
| `ARCHIVE_RESPONSES` | `false`; enable optional best-effort S3 copy |
| `S3_BUCKET`, `S3_ENDPOINT_URL`, `AWS_*` | Optional archive configuration; example credentials are local MinIO defaults |
| `CLICKHOUSE_*` | Reserved prototype configuration; no metrics writer currently uses it |

`CORPUS_VERSION` is retained as a legacy setting; run requests and the bundled seed explicitly default to `v1`. `SECRET_KEY` is also retained for compatibility but is not used for these bearer keys or encrypted credentials.

Core Compose uses PostgreSQL, Redis, API, three workers, Beat and platform. The `demo` profile adds the mock; `archive` adds MinIO and private-bucket initialization; `analytics` starts an unused ClickHouse prototype. Optional services are not prerequisites for evaluation. Enable the archive profile and `ARCHIVE_RESPONSES=true` together if desired; an archive failure is logged and does not discard the database response.

## Development and verification

Python 3.12 and Node.js 22 are used in CI. Python dependencies are pinned in `api/requirements.txt`; npm uses the committed lockfile. The virtual environment below contains development/test dependencies as well as runtime packages.

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r api/requirements.txt
pytest api/tests -q             # SQLite + fake Redis; no Docker, model or internet calls
pytest engine/tests -q          # run separately: both projects historically use app packages
ruff check api engine
(cd api && PYTHONPATH=.. mypy app --ignore-missing-imports --no-strict-optional)
(cd platform && npm ci && npm run type-check && npm run lint && npm run build)
```

API fixtures create disposable SQLite databases unless **explicit** `TEST_DATABASE_URL` and `TEST_DATABASE_URL_SYNC` are supplied. They never derive test targets by modifying a production URL. PostgreSQL tests require a database name ending in `_test` and **create/drop its tables**. The PostgreSQL CI suite covers real row-lock/concurrent-worker semantics; SQLite alone cannot establish those guarantees.

```bash
# Point all four at an explicitly disposable _test database before running these.
export DATABASE_URL='postgresql+asyncpg://lucent:lucent@localhost:5432/lucenteval_test'
export DATABASE_URL_SYNC='postgresql+psycopg2://lucent:lucent@localhost:5432/lucenteval_test'
export TEST_DATABASE_URL="$DATABASE_URL"
export TEST_DATABASE_URL_SYNC="$DATABASE_URL_SYNC"
PYTHONPATH=api:. python infra/scripts/test_migration.py
pytest api/tests -q
```

The migration script deliberately downgrades/upgrades this disposable database, checks preservation of a completed legacy score, stops incomplete legacy work, disables unrecoverable old webhooks, checks schema drift and leaves a clean migrated database. Do not use it against real data.

For a host API: `PYTHONPATH=api:. uvicorn app.main:app --reload`. Start each queue worker and a single Beat with the same environment and Python path (see Compose commands). When running Alembic from `api/`, export the database environment explicitly or pass the appropriate `.env`; otherwise that working directory does not read the root `.env`.

CI runs API lint/types, PostgreSQL migration and concurrency regressions, offline API/scorer tests, platform types/lint/build and the complete Docker mock smoke. The example external-agent workflow is manual only and needs operator-provided API URL and secrets. The local [composite GitHub Action](.github/actions/run-eval) uses `/v1`, Bearer auth, bounded polling, a numeric score gate and declared outputs. Its `run_url` output is the authenticated API detail URL. It is not a published marketplace action or proof of a hosted Lucent Eval service.

## Upgrade from schema 0001

1. Back up PostgreSQL and optional response archives. Stop old API/workers/Beat so they cannot run against the new ledger with old code.
2. Inspect unfinished runs and old webhooks. Migration `0002` clears legacy plaintext run headers, marks unfinished legacy results/runs terminal with `legacy_incomplete_run`, and disables old webhooks. Completed scores are preserved as `legacy-v1`. Historical prompt contents cannot be reconstructed; old traces have no frozen snapshot or database response unless already available elsewhere.
3. If duplicate `(run_id,prompt_id)` rows exist, the new uniqueness constraint fails the transaction instead of deleting evidence. Resolve the duplicate data deliberately before retrying.
4. Generate/configure `CREDENTIAL_ENCRYPTION_KEY` and `ADMIN_TOKEN`; set trusted origins and outbound host policy. Deploy API/engine from the same image. Apply `alembic upgrade head` (Compose API startup does this).
5. Purge **old runner/scorer/webhook broker queues** while workers are stopped. Old scoring messages contained raw payload arguments and are incompatible with the new ID-only task signatures. Do not purge queues for the new deployment after accepting work.
6. Start the new workers and one Beat, re-register disabled webhooks with new secrets, and intentionally resubmit any desired incomplete legacy evaluations. Use new idempotency keys for these new runs.
7. Run the mock smoke and inspect readiness, worker queues, errors and outbox status before accepting real evaluations.

Downgrading schema does not restore erased plaintext credentials, previous in-flight states or webhook secrets. Restore the backup for a full rollback. Do not change the encryption key on a live deployment without a credential migration.

## Limitations

- No empirical scorer calibration, model leaderboard claims, certified safety guarantee or throughput/SLO claim is established by this repository. Heuristics are gameable; inspect actual responses and use independent evaluation.
- There is no trained adversarial classifier, NLP model, Wikipedia grounding database, tool sandbox, real tool-error harness, billing reconciliation or automatic provider pricing refresh.
- Corpus labels are mutable; **run snapshots**, not live corpus version names, guarantee the recorded inputs. Generated/duplicate prompts reduce the diversity implied by row counts.
- No cancellation, pause/resume API, result deletion/retention policy, signup verification, user password recovery, per-account run-concurrency quota or self-service webhook replay UI is implemented. Configure resource quotas, retention, ingress/egress and abuse controls before public operation.
- Public leaderboard output exposes endpoint **origins** and scores. Raw traces, credentials and URL paths are owner-only. The browser uses persistent bearer-key storage; there is no server session/cookie auth.
- NDJSON output is streamed to the client but the current implementation loads the result rows for a run into memory. Reconciliation scans outstanding work; larger deployments need batching, retention and operational monitoring.
- Optional S3 writes are best effort; ClickHouse schema/configuration is an unused prototype. There is no S3-backed scoring fallback or automatic repair of optional archives.
- Leases prevent stale database writes, not duplicate external effects; receiver/agent idempotency remains essential. Mock checks validate software behavior, not model quality.

See [API reference](docs/API_REFERENCE.md), [operator runbook](docs/RUNBOOK.md) and [implementation plan/evidence](docs/engineering/upgrade-plan.md).
