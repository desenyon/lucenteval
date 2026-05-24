#!/usr/bin/env bash
# One-time local dev setup script

set -euo pipefail

echo "🚀 Setting up Lucent Eval local dev environment..."

# Copy env
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✓ Created .env from .env.example"
fi

# Start infrastructure
docker compose up -d postgres redis minio clickhouse
echo "⏳ Waiting for services..."
timeout 60 bash -c 'until docker compose exec -T postgres pg_isready -U lucent; do sleep 2; done'
timeout 30 bash -c 'until docker compose exec -T redis redis-cli ping | grep -q PONG; do sleep 2; done'
echo "✓ Services ready"

# Create MinIO bucket
docker compose run --rm minio-setup
echo "✓ S3 bucket created"

# Apply migrations
echo "Running Alembic migrations..."
cd api
pip install -r requirements.txt -q
alembic upgrade head
echo "✓ Migrations applied"

# Seed corpus
python3 -c "
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.seed_corpus import seed_corpus
from app.core.config import get_settings
settings = get_settings()
engine = create_engine(settings.DATABASE_URL_SYNC)
Session = sessionmaker(bind=engine)
with Session() as db:
    n = seed_corpus(db)
    print(f'Seeded {n} prompts')
"
cd ..

echo ""
echo "✅ Done! Start all services with: docker compose up"
echo "   API:      http://localhost:8000/redoc"
echo "   Platform: http://localhost:3000"
echo "   MinIO:    http://localhost:9001"
