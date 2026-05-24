"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # accounts
    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_accounts_email", "accounts", ["email"], unique=True)

    # api_keys
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("key_prefix", sa.String(16), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("scopes", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("rate_limit_rpm", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_keys_account_id", "api_keys", ["account_id"])
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)

    # prompts
    op.create_table(
        "prompts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("subcategory", sa.String(64), nullable=True),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("expected_behavior", sa.Text(), nullable=False),
        sa.Column("corpus_version", sa.String(32), nullable=False, server_default="v1"),
        sa.Column("contributor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("upvotes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("in_quarantine", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("severity IN ('low','medium','high','critical')", name="ck_prompt_severity"),
        sa.CheckConstraint(
            "category IN ('injection','jailbreak','role_confusion','goal_hijack','tool_abuse','factual_trap','multi_turn_trap')",
            name="ck_prompt_category",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prompts_category", "prompts", ["category"])
    op.create_index("ix_prompts_severity", "prompts", ["severity"])
    op.create_index("ix_prompts_corpus_version", "prompts", ["corpus_version"])

    # runs
    op.create_table(
        "runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("endpoint_url", sa.Text(), nullable=False),
        sa.Column("headers", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("corpus_version", sa.String(32), nullable=False, server_default="v1"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("composite_score", sa.Float(), nullable=True),
        sa.Column("score_adversarial", sa.Float(), nullable=True),
        sa.Column("score_tool_misuse", sa.Float(), nullable=True),
        sa.Column("score_hallucination", sa.Float(), nullable=True),
        sa.Column("score_recovery", sa.Float(), nullable=True),
        sa.Column("score_latency", sa.Float(), nullable=True),
        sa.Column("score_cost", sa.Float(), nullable=True),
        sa.Column("latency_p50", sa.Float(), nullable=True),
        sa.Column("latency_p95", sa.Float(), nullable=True),
        sa.Column("latency_p99", sa.Float(), nullable=True),
        sa.Column("prompt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("weights_version", sa.String(32), nullable=False, server_default="v1"),
        sa.Column("weights_snapshot", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_runs_account_id", "runs", ["account_id"])
    op.create_index("ix_runs_status", "runs", ["status"])

    # results
    op.create_table(
        "results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prompt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("s3_key", sa.String(512), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("score_adversarial", sa.Float(), nullable=True),
        sa.Column("score_tool_misuse", sa.Float(), nullable=True),
        sa.Column("score_hallucination", sa.Float(), nullable=True),
        sa.Column("score_recovery", sa.Float(), nullable=True),
        sa.Column("score_latency", sa.Float(), nullable=True),
        sa.Column("score_cost", sa.Float(), nullable=True),
        sa.Column("composite_score", sa.Float(), nullable=True),
        sa.Column("rationale_adversarial", postgresql.JSON(), nullable=True),
        sa.Column("rationale_tool_misuse", postgresql.JSON(), nullable=True),
        sa.Column("rationale_hallucination", postgresql.JSON(), nullable=True),
        sa.Column("rationale_recovery", postgresql.JSON(), nullable=True),
        sa.Column("tool_call_graph", postgresql.JSON(), nullable=True),
        sa.Column("recovery_turns", postgresql.JSON(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prompt_id"], ["prompts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_results_run_id", "results", ["run_id"])
    op.create_index("ix_results_prompt_id", "results", ["prompt_id"])
    op.create_index("ix_results_status", "results", ["status"])

    # webhooks
    op.create_table(
        "webhooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("secret_hash", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhooks_account_id", "webhooks", ["account_id"])

    # audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column("actor_ip", sa.String(64), nullable=True),
        sa.Column("metadata", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_account_id", "audit_logs", ["account_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("webhooks")
    op.drop_table("results")
    op.drop_table("runs")
    op.drop_table("prompts")
    op.drop_table("api_keys")
    op.drop_table("accounts")
