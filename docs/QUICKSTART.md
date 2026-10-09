# Quickstart

The maintained setup, account bootstrap, agent protocol and curl examples are in the [README](../README.md#quick-start-local-docker-demo).

```bash
python3 infra/scripts/init_env.py
docker compose --profile demo up -d --build --wait
docker compose exec -T api python /workspace/infra/scripts/smoke_eval.py
```

No model credentials are needed. Use `/v1` routes with `Authorization: Bearer lev_…`. The mock runs inside Docker at `http://mock-agent:8080/v1/chat/completions`; it is explicitly allowlisted by the demo configuration. Real destinations require public HTTPS unless an operator permits an exact private host.

Dashboard: http://localhost:3000. Live API reference: http://localhost:8000/redoc. Register through `POST /v1/accounts` to receive your own initial key once, then paste it in Dashboard → Settings. The automated smoke account's key is intentionally not printed.

See the README migration section before upgrading an existing installation. The setup script preserves existing `.env` files and existing Docker volumes.
