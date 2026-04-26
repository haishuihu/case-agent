"""add llm_config and embedding_config tables

Revision ID: 002_add_llm_config
Revises: 001_initial
Create Date: 2026-04-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002_add_llm_config"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── LLM Config ─────────────────────────────────────────────────────
    op.create_table(
        "llm_configs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(length=100), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("api_format", sa.String(length=20), nullable=False, server_default="openai_compatible"),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("api_key", sa.String(length=500), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=False),
        sa.Column("max_output_tokens", sa.Integer(), nullable=False, server_default="131072"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="120"),
        sa.Column("supports_vision", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("supports_structured_output", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("extra_config", sa.JSON(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_llm_configs_user_id", "llm_configs", ["user_id"])

    # ── Embedding Config ────────────────────────────────────────────────
    op.create_table(
        "embedding_configs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(length=100), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("api_format", sa.String(length=20), nullable=False, server_default="openai_compatible"),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("api_key", sa.String(length=500), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("extra_config", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_embedding_configs_user_id", "embedding_configs", ["user_id"])


def downgrade() -> None:
    op.drop_index("idx_embedding_configs_user_id", table_name="embedding_configs")
    op.drop_table("embedding_configs")
    op.drop_index("idx_llm_configs_user_id", table_name="llm_configs")
    op.drop_table("llm_configs")
