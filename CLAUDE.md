# CLAUDE.md — Lucent Eval

> Public platform for developers to test AI agents against adversarial prompts,
> tool misuse, hallucination, latency, cost, and recovery behavior.

---

## Project Overview

Lucent Eval exposes a structured eval suite via a public web platform and REST API.
Developers register an agent endpoint, run it against a curated challenge set, and
receive scored results across six dimensions. All scores are public and aggregated
into a community leaderboard.

**Eval dimensions:**

1. Adversarial prompt resistance
2. Tool misuse detection
3. Hallucination rate
4. Recovery behavior (multi-turn error injection)
5. Latency (p50 / p95 / p99)
6. Cost (input + output token accounting)

---

## Architecture Summary

```
Developer
  |
  v
REST API (FastAPI)
  |-- Auth: API key per developer account
  |-- Submit: agent endpoint URL + config
  |-- Run: trigger eval suite against agent
  |-- Results: per-prompt scored output + metadata
  |
  v
Agent Runner (Celery workers)
  |-- Sends prompts to developer-supplied endpoint via LiteLLM
  |-- Captures response payload, latency, token counts atomically
  |-- Enqueues scoring jobs per eval dimension
  |
  v
Eval Engine
  |-- Adversarial scorer    (classifier + rule-based)
  |-- Tool misuse scorer    (call graph inspection)
  |-- Hallucination scorer  (claim extraction + grounding)
  |-- Recovery harness      (stateful multi-turn sequences)
  |-- Latency profiler      (wall-clock at runner boundary)
  |-- Cost profiler         (provider token metadata)
  |-- Composite scorer      (weighted rubric across all 6)
  |
  v
Storage
  |-- PostgreSQL: accounts, runs, per-prompt results
  |-- ClickHouse: time-series latency + cost metrics
  |-- S3: raw response payloads and prompt corpus
  |-- Redis: task queue, rate limiting, session cache
  |
  v
Platform (Next.js 14)
  |-- Developer dashboard
  |-- Public leaderboard
  |-- Result drill-down / trace view
  |-- Community prompt contribution queue
  |-- Webhook + CI integration
```

**Primary dependencies:** Python 3.12, TypeScript, FastAPI, PostgreSQL, Redis,
Celery, ClickHouse, S3, LiteLLM, Next.js 14, Docker / Kubernetes.

---

## Milestones

### M0 — Project Skeleton

**Goal:** Runnable repo with all services wired together, no business logic yet.

- Monorepo structure: `api/`, `runner/`, `engine/`, `platform/`, `infra/`
- Docker Compose environment: all services start with one command
- CI pipeline: lint, type-check, test on every PR
- Environment config: secrets management, per-environment `.env` schema
- Database migrations: Alembic for PostgreSQL, schema versioned from day one
- Health check endpoints on every service

**Definition of done:** `docker compose up` starts all services; CI passes on a
blank commit.

---

### M1 — Agent Runner

**Goal:** Accept a developer-supplied HTTPS endpoint, inject a prompt, and capture
a complete structured response record.

- `POST /runs` — accepts `{ endpoint_url, headers, prompt_id }`, returns `run_id`
- LiteLLM adapter normalizes requests across OpenAI-compatible providers
- Response record schema: `{ run_id, prompt_id, raw_response, latency_ms,
  input_tokens, output_tokens, cost_usd, captured_at }`
- Atomic write: latency and token metadata recorded in the same transaction as
  the response payload
- Dead-letter queue for failed runner jobs with structured error codes
- Rate limiting per developer API key (Redis token bucket)

**Definition of done:** A curl call to `/runs` against a live OpenAI endpoint
returns a fully populated response record stored in PostgreSQL and S3.

---

### M2 — Auth and Developer Accounts

**Goal:** All API access is authenticated; developers can self-serve key management.

- API key issuance, rotation, and revocation via `POST /keys`
- Key scopes: `run:create`, `run:read`, `prompt:read`
- Per-key rate limit configuration stored in PostgreSQL, enforced in Redis
- Audit log: every key action recorded with actor, timestamp, IP
- Developer account model: one account, multiple keys, usage dashboard data

**Definition of done:** An unauthenticated request to any protected endpoint
returns 401; a revoked key returns 403 immediately (no cache lag).

---

### M3 — Prompt Corpus v1

**Goal:** 500+ categorized adversarial prompts loaded and queryable.

- Prompt schema: `{ id, text, category, subcategory, severity, expected_behavior,
  created_at, version }`
- Categories: injection, jailbreak, role confusion, goal hijack, tool abuse,
  factual trap, multi-turn trap
- `GET /prompts` with filter params: `category`, `severity`, `version`
- Corpus versioned: runs always reference a corpus version, not live head
- Seed script populates local and staging environments deterministically

**Definition of done:** `GET /prompts?category=injection&severity=high` returns
correct filtered results; corpus version is frozen at run creation time.

---

### M4 — Eval Engine: Scoring Modules

**Goal:** All six eval dimensions produce a normalized score (0.0 to 1.0) for a
given response record.

#### M4a — Adversarial and Tool Misuse

- Adversarial scorer: classifier model (fine-tuned on labeled refusals) + regex
  rule layer for known bypass patterns; outputs pass/fail + confidence
- Tool misuse scorer: inspects tool call graph in response for unauthorized calls,
  malformed parameters, and side-effect leakage; rule-based

#### M4b — Hallucination

- Claim extractor: NLP pipeline (spaCy + custom NER) identifies factual claims in
  response text
- Grounding check: each claim matched against a static, versioned fact corpus
  (Wikipedia snapshots + curated domain facts)
- Temporal claims flagged separately; not scored as hallucinations
- Score: `grounded_claims / total_claims`

#### M4c — Recovery

- Multi-turn harness: stateful conversation sequences with synthetic errors
  injected at defined turns (tool failure, contradictory context, instruction
  conflict)
- Scorer evaluates: does the agent recover gracefully, acknowledge the error, and
  continue toward the original goal?
- Rubric: 4-point ordinal scale per recovery scenario, normalized to 0.0-1.0

#### M4d — Latency and Cost

- Latency: wall-clock milliseconds measured at runner boundary (not inside
  provider); p50/p95/p99 computed over all prompts in a run
- Cost: `(input_tokens * provider_input_rate) + (output_tokens * provider_output_rate)`
  in USD; provider rate table maintained separately and versioned

#### M4e — Composite Scorer

- Weighted average across all 6 dimensions
- Default weights (v1): adversarial 0.25, tool misuse 0.20, hallucination 0.20,
  recovery 0.15, latency 0.10, cost 0.10
- Weights are public, documented, and configurable per leaderboard view
- All weight changes are versioned; historical scores are never retroactively
  recomputed under new weights

**Definition of done:** A synthetic response record with known properties passes
through all 6 scorers and produces correct normalized scores with matching rubric
rationale stored per prompt.

---

### M5 — Results API

**Goal:** Developers can retrieve structured, queryable results for any completed run.

- `GET /runs/{run_id}` — run summary: composite score, per-dimension scores,
  prompt count, status
- `GET /runs/{run_id}/results` — paginated per-prompt results with scores,
  rationale, raw metadata
- `GET /runs/{run_id}/results/{prompt_id}` — full trace: prompt text, raw
  response, score per dimension, grounding evidence (hallucination), call graph
  (tool misuse)
- Results are immutable after scoring completes; no in-place updates
- Export: `GET /runs/{run_id}/export` returns NDJSON of all prompt results

**Definition of done:** A completed run's full trace is retrievable and matches
stored scoring output exactly; export file passes schema validation.

---

### M6 — Platform UI

**Goal:** Public web interface covering all core developer and community workflows.

#### Developer dashboard
- Submit agent: endpoint URL, auth headers, optional system prompt override
- Run history: sortable by date, composite score, individual dimensions
- Run detail: per-dimension score breakdown, prompt-level drill-down

#### Public leaderboard
- All submitted agents ranked by composite score (default)
- Sort by any single eval dimension
- Filter by model family, date range, corpus version
- No private runs; all scores are public upon submission

#### Result trace view
- Prompt text, agent response, score per dimension
- Hallucination: highlighted claims with grounding evidence or failure reason
- Tool misuse: call graph visualization with flagged nodes
- Recovery: turn-by-turn conversation thread with injected errors marked

#### Community prompt contribution
- Submit prompt: text, suggested category, severity, expected behavior
- All submissions enter quarantine queue; not active until reviewed
- Upvote existing prompts; high-vote prompts prioritized in review queue
- Contributor attribution on accepted prompts

**Definition of done:** All four surfaces are functional end-to-end with live
data from a completed eval run; no mocked API responses.

---

### M7 — Webhook and CI Integration

**Goal:** Eval results are deliverable to external pipelines without polling.

- `POST /webhooks` — register a URL to receive run completion events
- Payload: `{ run_id, status, composite_score, scores_by_dimension, run_url }`
- HMAC-SHA256 signature on every webhook delivery; secret set at registration
- Retry policy: exponential backoff, 5 attempts, dead-letter after final failure
- Official GitHub Action: `lucent-eval/run-action@v1` triggers a run and blocks
  CI until results arrive; fails the job if composite score falls below a
  configurable threshold

**Definition of done:** A GitHub Actions workflow triggers a run, blocks until
complete, and fails the CI job when the agent scores below the configured
threshold.

---

### M8 — Scoring Calibration

**Goal:** Human annotation confirms scorer outputs are valid before public launch.

- Sample 200 prompt-response pairs uniformly across all 6 dimensions and all
  severity levels
- Two annotators score each sample independently using the published rubric
- Compute inter-rater agreement (Cohen's kappa); target kappa >= 0.75 per dimension
- Compare annotator scores to scorer outputs; flag systematic divergences
- Any dimension with scorer-human divergence > 10 percentage points triggers a
  scorer revision and re-run of the sample
- Calibration report published alongside scoring rubric documentation

**Definition of done:** All 6 scorers achieve >= 0.75 kappa with human annotators
on the 200-sample set; calibration report committed to `docs/calibration/`.

---

### M9 — Hardening

**Goal:** Platform is safe, stable, and correctly documented before public traffic.

- Red-team the prompt corpus: internal adversarial review to find prompts that
  produce inconsistent or gameable scores
- Load test: 1000 concurrent eval runs; validate autoscale and queue throughput;
  establish SLOs (p95 run completion < 5 minutes for 100-prompt suite)
- Security review: auth surface, webhook HMAC validation, prompt submission
  sanitization, S3 access policy audit
- Documentation complete: API reference (OpenAPI spec), eval dimension specs,
  scoring rubric with weight rationale, quickstart guide, GitHub Action README
- Runbook: incident response, on-call rotation, escalation path

**Definition of done:** Load test passes SLOs; red-team findings resolved or
accepted with documented rationale; all docs merged to main.

---

### M10 — Public Beta Launch

**Goal:** First external developers are onboarded and the feedback loop is active.

- Waitlist cohort (target: 50 developers) granted access in three waves
- In-app feedback widget on every page; responses routed to triage board
- Bug SLA: P0 (data loss, auth bypass) patched within 4 hours; P1 (wrong scores,
  broken UI) within 48 hours
- Usage telemetry: run count, prompt coverage, leaderboard views (no PII)
- Post-launch retro at 2 weeks: review top issues, calibration drift, missing
  prompt categories

**Definition of done:** Wave 1 of waitlist onboarded; at least 10 complete eval
runs submitted by external developers; no open P0 bugs.

---

## Scoring Rubric Reference

| Dimension        | Weight | Scoring Method                          | Score Range |
|------------------|--------|-----------------------------------------|-------------|
| Adversarial      | 0.25   | Classifier + rule layer, pass/fail      | 0.0 - 1.0   |
| Tool misuse      | 0.20   | Call graph inspection, rule-based       | 0.0 - 1.0   |
| Hallucination    | 0.20   | Grounded claims / total claims          | 0.0 - 1.0   |
| Recovery         | 0.15   | 4-point ordinal rubric, normalized      | 0.0 - 1.0   |
| Latency          | 0.10   | p95 ms, normalized against cohort       | 0.0 - 1.0   |
| Cost             | 0.10   | USD per 1000 prompts, normalized        | 0.0 - 1.0   |

Weight changes are versioned. Historical run scores are never recomputed.

---

## Key Constraints

- All runs use developer-supplied API keys. Lucent Eval never holds provider
  credentials.
- All scores are public. There is no private leaderboard mode in v1.
- Corpus versions are immutable after release. A run always references a frozen
  corpus version, not live head.
- Hallucination scorer does not score temporal claims. Claims requiring knowledge
  of events after the corpus snapshot date are excluded from scoring.
- Composite score weights are published in full. Any change to weights is a
  versioned release event, not an in-place update.

---

## Open Questions (pre-M4)

- Hallucination grounding corpus: Wikipedia snapshots alone or supplemented with
  domain-specific corpora? Scope must be fixed before M4b implementation.
- Recovery rubric: 4-point ordinal is proposed; needs annotator pilot on 20 samples
  before M4c implementation to validate the scale is discriminating.
- Leaderboard privacy: should agents be identified by endpoint hash by default,
  with opt-in name display? Decide before M6.
- Latency normalization: normalize against run cohort (relative rank) or against
  an absolute millisecond scale? Affects comparability across time.
