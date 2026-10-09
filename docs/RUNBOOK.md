# Operator runbook

This is an operational guide for the implemented self-hosted services, not evidence of uptime, load testing or an SLO. Setup and migration procedures are in the [README](../README.md).

## Readiness and startup

`GET /v1/health` checks PostgreSQL and Redis and returns `503` when either is unavailable. It does not prove that workers or Beat are running. Check `docker compose ps`, worker logs and whether `completed_count`/`failed_count` advance on the mock smoke. The platform has a separate `/api/health` route.

API startup applies Alembic migrations before serving; Compose workers wait for API readiness. Run one Beat scheduler and at least one worker for each `runner`, `scorer`, `webhook` queue. The local image includes both API and engine. Keep `CREDENTIAL_ENCRYPTION_KEY` consistent across them.

## Pending or stuck evaluations

1. Check DB and Redis readiness, broker URLs and worker queue subscriptions. `celery -A app.workers.celery_app inspect ping` can confirm worker responsiveness; it is not an evaluation health check.
2. Confirm Beat publishes `app.workers.tasks.reconcile_work` to `runner` every 30 seconds. Database rows are the source of truth, not Celery result state.
3. Inspect the ledger without exposing credentials or raw responses:

```sql
SELECT status, count(*) FROM runs GROUP BY status;
SELECT status, count(*), min(lease_expires_at), min(next_attempt_at)
FROM results WHERE status NOT IN ('scored','error') GROUP BY status;
SELECT status, count(*) FROM webhook_deliveries GROUP BY status;
```

4. Pending/captured rows and expired leases are republished on reconciliation. A one-off operator reconciliation can be run with `python -c 'from app.workers.tasks import reconcile_work; reconcile_work()'` in the API environment. This dispatches work and can repeat external requests when earlier outcomes were uncertain; agent idempotency is essential.
5. Do not reset attempt counts or terminal states to replay work. Fix the underlying endpoint/configuration issue and create a new run intentionally. Old claims are fenced; directly editing the ledger defeats those guarantees.

A stopped worker may leave a claim active until the ten-minute default lease expires. Repeated crashes consume the same bounded attempt budget as ordinary failures. Queue loss is recoverable while the database ledger remains intact and Beat/worker service resumes.

## Failed results or webhooks

Result `error` codes identify failure classes without copying sensitive exception messages. Inspect owner-authorized traces, response protocol, URL policy, token count validity and encryption configuration. Never paste provider headers into issue reports. Failed runs preserve successful results, but composite score is null and leaderboard excludes them.

Webhook rows remain in `webhook_deliveries` after exhaustion. Six total attempts are permitted by default, with backoff. Receivers verify the raw-byte HMAC and deduplicate stable event IDs. There is no replay API/UI yet; deliberately re-running an evaluation produces a new event. Deleting the webhook cancels pending delivery rows. Old webhook registrations from schema 0001 are disabled at migration and must be replaced.

## Storage, secrets and backup

PostgreSQL is authoritative for prompt snapshots, captured JSON, scores and the outbox. Back up it and the encryption key separately, and test restores. Keep API/workers stopped during an inconsistent restore. External effects from a restored snapshot may repeat; receiver idempotency must survive independently of the evaluation database.

Optional S3 storage is best effort and private by default in the updated local profile. If upgrading an existing MinIO bucket, run `docker compose --profile archive run --rm minio-setup` to remove the old public-read setting. Check existing bucket policies in nonlocal deployments separately. Enabling the profile alone does not enable archives; set `ARCHIVE_RESPONSES=true` as well. A database trace remains available when S3 is unavailable.

Terminal runs clear current encrypted header values, but historical backups or old schema-0001 archives may contain plaintext credentials. Plan retention and credential rotation accordingly. There is no automatic retention/deletion policy.

## Deployment configuration

The Compose file is a local development configuration: loopback-bound published ports and local database/MinIO passwords. For production use managed secrets, TLS at ingress, trusted `CORS_ORIGINS`, an appropriate `PLATFORM_URL`, registration/request/concurrency quotas, database backups and network egress restrictions. Remove the `mock-agent` private-host exception and do not deploy its unauthenticated diagnostic receiver publicly.

Weights, rates and prompt snapshots are frozen per run. Scorer code still comes from the deployed image; drain in-flight runs before deploying behavior changes and bump `scorer_version` when changing semantics. The historical price table is not a price feed. ClickHouse configuration/schema has no implemented writer and is optional.

## Rollback

Read the schema-0002 migration procedure first. Do not run old workers against new queues or old broker envelopes against new task signatures. Schema downgrade cannot recover cleared credentials or original webhook secrets; restore a tested backup for a full rollback. There are no automatic production deploy, rollback or release actions in CI.
