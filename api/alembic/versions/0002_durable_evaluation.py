"""Durable evaluation ledger, frozen manifests and encrypted credentials.

Legacy in-flight work is stopped, never replayed with changed inputs.
Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_prompts_subcategory", "prompts", ["subcategory"])
    for name, kind in [
        ("headers_encrypted", sa.Text()),
        ("idempotency_key", sa.String(128)),
        ("request_hash", sa.String(64)),
        ("manifest_sha256", sa.String(64)),
    ]:
        op.add_column("runs", sa.Column(name, kind, nullable=True))
    op.add_column("runs", sa.Column("scorer_version", sa.String(32), nullable=False, server_default="legacy-v1"))
    op.add_column("runs", sa.Column("rates_snapshot", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("runs", sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"))
    op.create_unique_constraint("uq_run_idempotency", "runs", ["account_id", "idempotency_key"])
    for name, kind in [
        ("prompt_snapshot", sa.JSON()),
        ("raw_payload", sa.JSON()),
        ("claim_token", sa.String(36)),
        ("lease_expires_at", sa.DateTime(timezone=True)),
        ("next_attempt_at", sa.DateTime(timezone=True)),
    ]:
        op.add_column("results", sa.Column(name, kind, nullable=True))
    for name in ("attempt_count", "score_attempt_count"):
        op.add_column("results", sa.Column(name, sa.Integer(), nullable=False, server_default="0"))
    # Fail explicitly if a legacy database already has duplicate logical results; do not delete evidence.
    op.create_unique_constraint("uq_result_prompt", "results", ["run_id", "prompt_id"])
    op.add_column("webhooks", sa.Column("secret_encrypted", sa.Text(), nullable=True))
    op.execute("UPDATE webhooks SET is_active = false")
    op.execute("UPDATE runs SET headers = '{}'::json")
    op.execute("""UPDATE results SET status = 'error', error = 'legacy_incomplete_run: resubmit after migration'
                  WHERE run_id IN (SELECT id FROM runs WHERE status NOT IN ('completed', 'failed'))
                  AND status != 'scored'""")
    op.execute("""UPDATE runs SET status = 'failed', completed_at = now(),
                  completed_count = (SELECT count(*) FROM results WHERE results.run_id = runs.id AND status = 'scored'),
                  failed_count = (SELECT count(*) FROM results WHERE results.run_id = runs.id AND status = 'error')
                  WHERE status NOT IN ('completed', 'failed')""")
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "webhook_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("webhooks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("claim_token", sa.String(36)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("run_id", "webhook_id", name="uq_delivery_run_webhook"),
    )
    op.create_index("ix_webhook_deliveries_status", "webhook_deliveries", ["status"])


def downgrade():
    op.drop_index("ix_prompts_subcategory", table_name="prompts")
    # Credential wiping, failed legacy work and disabled legacy hooks cannot be undone.
    op.drop_table("webhook_deliveries")
    op.drop_column("webhooks", "secret_encrypted")
    op.drop_constraint("uq_result_prompt", "results", type_="unique")
    for name in (
        "prompt_snapshot",
        "raw_payload",
        "claim_token",
        "lease_expires_at",
        "next_attempt_at",
        "attempt_count",
        "score_attempt_count",
    ):
        op.drop_column("results", name)
    op.drop_constraint("uq_run_idempotency", "runs", type_="unique")
    for name in (
        "headers_encrypted",
        "idempotency_key",
        "request_hash",
        "manifest_sha256",
        "scorer_version",
        "rates_snapshot",
        "failed_count",
    ):
        op.drop_column("runs", name)
