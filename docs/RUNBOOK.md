# Operations Runbook

## On-Call Rotation

Weekly rotation. Primary on-call checks PagerDuty; escalation to secondary after 15 min.

---

## Incident Response

### P0 — Data loss, auth bypass
**SLA:** Patch within 4 hours  
**Steps:**
1. Page primary on-call immediately
2. Engage rollback plan if data is corrupted
3. For auth bypass: rotate all signing keys immediately, revoke affected API keys
4. Notify affected users within 2 hours of discovery
5. Post-mortem within 24 hours

### P1 — Wrong scores, broken UI
**SLA:** Fix within 48 hours  
**Steps:**
1. Identify scope (single run vs. all runs)
2. If scorer bug: halt new runs from affected scorer; mark affected runs with `score_flagged: true`
3. Do NOT retroactively recompute scores under fixed weights
4. Roll fix to staging, validate on 10 known-good runs
5. Deploy and monitor for 2h

### P2 — Performance degradation
**SLA:** Resolution within 7 days  
**Steps:**
1. Check Celery queue depth: `redis-cli LLEN celery`
2. Check DB connection pool utilization
3. Scale workers as needed

---

## Service Health Checks

```bash
# API
curl https://api.lucenteval.dev/v1/health

# Queue depth
redis-cli -h redis.internal LLEN runner
redis-cli -h redis.internal LLEN scorer

# DB connections
psql -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"

# Celery workers
celery -A app.workers.celery_app inspect ping
```

---

## Database Migrations

```bash
# Apply pending migrations
cd api && alembic upgrade head

# Rollback one
cd api && alembic downgrade -1

# Check current revision
cd api && alembic current
```

---

## Rollback Procedure

```bash
# API rollback
kubectl set image deployment/api api=lucenteval/api:<prev-tag>

# Database: migrations are additive only; downgrade if needed
cd api && alembic downgrade <revision>
```

---

## Monitoring

- **Latency SLO:** p95 run completion < 5 minutes for 100-prompt suite
- **Error rate:** < 0.1% of prompt runs should hit dead-letter queue
- **API p99:** < 500ms for read endpoints; < 2s for run creation

Key metrics (Prometheus):
- `lucenteval_run_completion_seconds_p95`
- `lucenteval_celery_queue_depth{queue}`
- `lucenteval_scorer_error_total{dimension}`
- `lucenteval_webhook_delivery_failures_total`
