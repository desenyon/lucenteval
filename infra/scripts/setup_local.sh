#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 infra/scripts/init_env.py
docker compose --profile demo up -d --build --wait
docker compose exec -T api python /workspace/infra/scripts/smoke_eval.py
