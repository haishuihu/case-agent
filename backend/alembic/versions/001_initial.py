"""initial schema: all core tables

Revision ID: 001_initial
Revises:
Create Date: 2026-04-22

This migration captures all existing tables for Alembic-managed schema evolution.
Subsequent schema changes should use separate migration files.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Generation Records ──────────────────────────────────────────────
    op.create_table(
        "generation_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("requirement_text", sa.Text()),
        sa.Column("result_markdown", sa.Text()),
        sa.Column("result_cases_json", sa.Text()),
        sa.Column("metadata_json", sa.Text()),
        sa.Column("model_name", sa.String()),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("attachment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_phase", sa.String(), nullable=False, server_default=""),
        sa.Column("progress_detail", sa.Text()),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("client_model_key", sa.String()),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_index("idx_gen_status", "generation_records", ["status"])
    op.create_index("idx_gen_created_at", "generation_records", ["created_at"])

    # ── Generation Attachments ─────────────────────────────────────────
    op.create_table(
        "generation_attachments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("generation_id", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("content_type", sa.String()),
        sa.Column("file_size", sa.Integer()),
        sa.Column("storage_path", sa.String()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_attach_gen", "generation_attachments", ["generation_id"])

    # ── Knowledge Documents ────────────────────────────────────────────
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("doc_type", sa.String()),
        sa.Column("module_tags", sa.Text()),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("content", sa.Text()),
        sa.Column("structured_payload", sa.Text()),
        sa.Column("summary", sa.Text()),
        sa.Column("source_type", sa.String()),
        sa.Column("source_filename", sa.String()),
        sa.Column("embedding_status", sa.String(), server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_index("idx_knowledge_doc_type", "knowledge_documents", ["doc_type"])
    op.create_index("idx_knowledge_status", "knowledge_documents", ["status"])

    # ── Knowledge Chunks ────────────────────────────────────────────────
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer()),
        sa.Column("has_embedding", sa.Boolean(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_chunk_doc", "knowledge_chunks", ["document_id"])

    # ── Submissions ────────────────────────────────────────────────────
    op.create_table(
        "submissions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("version", sa.String(100), nullable=False),
        sa.Column("submission_type", sa.String(50), nullable=False, server_default="feature"),
        sa.Column("requirement_id", sa.String(100)),
        sa.Column("requirement_link", sa.Text()),
        sa.Column("change_description", sa.Text(), nullable=False),
        sa.Column("affected_modules", sa.Text()),
        sa.Column("change_type", sa.String(20), nullable=False, server_default="modified"),
        sa.Column("self_test_passed", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("self_test_case_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("self_test_coverage", sa.Integer()),
        sa.Column("self_test_conclusion", sa.Text()),
        sa.Column("smoke_test_result", sa.String(20), nullable=False, server_default="not_executed"),
        sa.Column("blocking_issue_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("gate_result", sa.Text()),
        sa.Column("gate_reject_reason", sa.Text()),
        sa.Column("git_diff", sa.Text()),
        sa.Column("git_commit_hash", sa.String(100)),
        sa.Column("branch_name", sa.String(200)),
        sa.Column("submitter", sa.String(100)),
        sa.Column("reviewed_by", sa.String(100)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_index("idx_submissions_status", "submissions", ["status"])
    op.create_index("idx_submissions_created_at", "submissions", ["created_at"])

    # ── Submission Checklists ─────────────────────────────────────────
    op.create_table(
        "submission_checklists",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("submission_id", sa.String(), nullable=False),
        sa.Column("item", sa.Text(), nullable=False),
        sa.Column("check_method", sa.Text()),
        sa.Column("pass_criteria", sa.Text()),
        sa.Column("risk_level", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("category", sa.String(50), nullable=False, server_default="general"),
        sa.Column("is_checked", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("check_result", sa.Text()),
        sa.Column("checked_by", sa.String(100)),
        sa.Column("checked_at", sa.DateTime()),
        sa.Column("is_ai_generated", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_checklists_submission", "submission_checklists", ["submission_id"])

    # ── Impact Analyses ───────────────────────────────────────────────
    op.create_table(
        "impact_analyses",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("submission_id", sa.String()),
        sa.Column("git_diff", sa.Text()),
        sa.Column("changed_files", sa.Text()),
        sa.Column("added_lines", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_lines", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("modified_functions", sa.Text()),
        sa.Column("impact_summary", sa.Text()),
        sa.Column("confidence_level", sa.String(20), nullable=False, server_default="low"),
        sa.Column("status", sa.String(20), nullable=False, server_default="completed"),
        sa.Column("analyzed_by", sa.String(100)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_impact_submission", "impact_analyses", ["submission_id"])
    op.create_index("idx_impact_created_at", "impact_analyses", ["created_at"])

    # ── Impacted Modules ───────────────────────────────────────────────
    op.create_table(
        "impacted_modules",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("analysis_id", sa.String(), nullable=False),
        sa.Column("module_name", sa.String(100), nullable=False),
        sa.Column("module_type", sa.String(20), nullable=False, server_default="direct"),
        sa.Column("risk_level", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("impact_description", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_modules_analysis", "impacted_modules", ["analysis_id"])

    # ── Regression Recommendations ───────────────────────────────────
    op.create_table(
        "regression_recommendations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("analysis_id", sa.String(), nullable=False),
        sa.Column("case_id", sa.String(100)),
        sa.Column("case_title", sa.String(200)),
        sa.Column("priority", sa.String(20), nullable=False, server_default="should"),
        sa.Column("risk_level", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("reason", sa.Text()),
        sa.Column("estimated_minutes", sa.Integer()),
        sa.Column("category", sa.String(50)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_recommend_analysis", "regression_recommendations", ["analysis_id"])

    # ── Regression Executions ─────────────────────────────────────────
    op.create_table(
        "regression_executions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("recommendation_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="not_started"),
        sa.Column("executed_by", sa.String(100)),
        sa.Column("executed_at", sa.DateTime()),
        sa.Column("actual_result", sa.Text()),
        sa.Column("comment", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_exec_recommendation", "regression_executions", ["recommendation_id"])

    # ── Quick Generate Records ────────────────────────────────────────
    op.create_table(
        "quick_generate_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("requirement_text", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("output_content", sa.Text(), nullable=False),
        sa.Column("client_model_key", sa.String()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_quick_created_at", "quick_generate_records", ["created_at"])

    # ── Case Reviews ──────────────────────────────────────────────────
    op.create_table(
        "case_reviews",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("generation_id", sa.String(100)),
        sa.Column("case_title", sa.String(200)),
        sa.Column("requirement_text", sa.Text()),
        sa.Column("generated_cases", sa.Text()),
        sa.Column("review_status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("completeness_score", sa.Integer()),
        sa.Column("executability_score", sa.Integer()),
        sa.Column("consistency_score", sa.Integer()),
        sa.Column("redundancy_score", sa.Integer()),
        sa.Column("coverage_score", sa.Integer()),
        sa.Column("overall_score", sa.Integer()),
        sa.Column("ai_review_summary", sa.Text()),
        sa.Column("ai_review_details", sa.Text()),
        sa.Column("reviewer", sa.String(100)),
        sa.Column("reviewer_comment", sa.Text()),
        sa.Column("decision", sa.String(20)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_index("idx_reviews_status", "case_reviews", ["review_status"])
    op.create_index("idx_reviews_generation", "case_reviews", ["generation_id"])
    op.create_index("idx_reviews_created", "case_reviews", ["created_at"])

    # ── Review Comments ───────────────────────────────────────────────
    op.create_table(
        "review_comments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("review_id", sa.String(), nullable=False),
        sa.Column("author", sa.String(100)),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("case_id", sa.String(100)),
        sa.Column("case_title", sa.String(200)),
        sa.Column("parent_comment_id", sa.String(100)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_index("idx_comments_review", "review_comments", ["review_id"])

    # ── Append Generate Records ───────────────────────────────────────
    op.create_table(
        "append_generate_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("existing_cases", sa.Text(), nullable=False),
        sa.Column("requirement_text", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("appended_content", sa.Text(), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("client_model_key", sa.String()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_append_created_at", "append_generate_records", ["created_at"])

    # ── Defects ──────────────────────────────────────────────────────
    op.create_table(
        "defects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("submission_id", sa.String(100)),
        sa.Column("recommendation_id", sa.String(100)),
        sa.Column("execution_id", sa.String(100)),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("environment", sa.String(100)),
        sa.Column("browser", sa.String(50)),
        sa.Column("root_cause", sa.Text()),
        sa.Column("attachments", sa.Text()),
        sa.Column("creator", sa.String(100)),
        sa.Column("assignee", sa.String(100)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime()),
        sa.Column("resolved_at", sa.DateTime()),
    )
    op.create_index("idx_defects_submission", "defects", ["submission_id"])
    op.create_index("idx_defects_status", "defects", ["status"])
    op.create_index("idx_defects_created_at", "defects", ["created_at"])


def downgrade() -> None:
    op.drop_table("defects")
    op.drop_table("append_generate_records")
    op.drop_table("review_comments")
    op.drop_table("case_reviews")
    op.drop_table("quick_generate_records")
    op.drop_table("regression_executions")
    op.drop_table("regression_recommendations")
    op.drop_table("impacted_modules")
    op.drop_table("impact_analyses")
    op.drop_table("submission_checklists")
    op.drop_table("submissions")
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_documents")
    op.drop_table("generation_attachments")
    op.drop_table("generation_records")
