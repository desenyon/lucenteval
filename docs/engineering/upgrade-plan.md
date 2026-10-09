# Durable evaluation upgrade

Base: `6bebf9b`. Work is isolated on `improve/durable-offline-evaluation`.

Baseline evidence: API requirements cannot resolve (unused LiteLLM requires httpx <0.28); 113 Ruff findings across API/engine; 28 scorer tests pass. Docker is unavailable locally; the Homebrew Node binary fails dynamic linking. Use an isolated Node runtime, offline SQLite tests, and PostgreSQL/Docker CI.

Design:
- PostgreSQL result rows are the durable work ledger. Conditional, leased claims fence stale workers; bounded retries and terminal errors allow finalization. Celery Beat reconciles missed publishes and expired claims. External calls are at least once, with stable idempotency headers.
- Freeze ordered prompt content, recovery scenario, weights and rate table at submission. Save response payloads transactionally before scoring. Score from the database, never broker payloads or live prompts.
- Encrypt run headers and webhook signing secrets with an operator-managed Fernet key. Clear run credentials at finalization. Enforce public HTTPS destinations with DNS address pinning; private HTTP requires exact operator allowlisting. No redirects or environment proxies.
- Add account bootstrap keys, authenticated admin operations, submission idempotency, trace manifests, real recovery conversations, deterministic pagination and an authenticated export.
- Keep v1 routes and score weights; explicitly version runner/scorer behavior. Legacy incomplete runs fail during migration rather than being silently re-executed. Legacy webhooks require re-registration because hashes cannot recover signing secrets.
- Run regression, type, lint, migration, build and mock end-to-end checks; publish only an improvement branch and draft PR.

## Verification before first push

- Baseline platform typecheck reproduced the unknown-to-ReactNode failure. Initial API import also exposed SQLAlchemy's reserved `metadata` attribute and missing email validation dependency.
- Offline regression suite now covers full capture/recovery/scoring/export/signature flow; encrypted credentials; owner/scope boundaries; frozen-input hashes; submission deduplication; duplicate and stale claims; bounded failures/crashes; concurrent finalization; URL/DNS pinning; body limits and malformed payloads; real loopback mock HTTP; composite-action credential quoting and score gates.
- A concurrent SQLite test exposed an aggregate overwrite because SQLite ignores SELECT FOR UPDATE. Finalization now acquires a write lock before reading aggregates; PostgreSQL CI exercises the same race on the production engine.
- Local scorer tests, API Ruff/mypy, platform types/lint/production build, Compose configuration, shell/YAML syntax and a browser navigation smoke have been exercised. The Inter font is bundled, removing build-time Google Fonts access.
- Local Docker daemon is unavailable. Full migrations, PostgreSQL concurrency and Docker image/worker smoke must be confirmed in remote CI before completion.

Fresh local verification before first push: **49 API tests passed, 34 scorer tests passed**; Ruff clean; mypy clean (41 API source files); platform TypeScript, ESLint and Next.js production build passed; Compose/YAML/shell validation passed. The browser loaded the built home and docs pages. No provider credentials or paid model calls were used.
