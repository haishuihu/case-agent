"""Lightweight SQLite column migration for existing deployments (create_all does not ALTER)."""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_generation_record_columns(engine: Engine) -> None:
    insp = inspect(engine)
    if not insp.has_table("generation_records"):
        return
    existing = {c["name"] for c in insp.get_columns("generation_records")}
    alters: list[str] = []
    if "progress_phase" not in existing:
        alters.append("ALTER TABLE generation_records ADD COLUMN progress_phase VARCHAR NOT NULL DEFAULT ''")
    if "progress_detail" not in existing:
        alters.append("ALTER TABLE generation_records ADD COLUMN progress_detail TEXT")
    if "started_at" not in existing:
        alters.append(
            "ALTER TABLE generation_records ADD COLUMN started_at DATETIME"
        )
    if "client_model_key" not in existing:
        alters.append("ALTER TABLE generation_records ADD COLUMN client_model_key VARCHAR")
    if "cancel_requested" not in existing:
        alters.append(
            "ALTER TABLE generation_records ADD COLUMN cancel_requested BOOLEAN NOT NULL DEFAULT 0"
        )
    if not alters:
        return
    with engine.begin() as conn:
        for stmt in alters:
            conn.execute(text(stmt))


def ensure_submission_tables(engine: Engine) -> None:
    """Create submission-related tables if they don't exist."""
    insp = inspect(engine)

    # submissions table
    if not insp.has_table("submissions"):
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE submissions (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    version VARCHAR(100) NOT NULL,
                    submission_type VARCHAR(50) NOT NULL DEFAULT 'feature',
                    requirement_id VARCHAR(100),
                    requirement_link TEXT,
                    change_description TEXT NOT NULL,
                    affected_modules TEXT,
                    change_type VARCHAR(20) NOT NULL DEFAULT 'modified',
                    self_test_passed BOOLEAN NOT NULL DEFAULT 0,
                    self_test_case_count INTEGER NOT NULL DEFAULT 0,
                    self_test_coverage INTEGER,
                    self_test_conclusion TEXT,
                    smoke_test_result VARCHAR(20) NOT NULL DEFAULT 'not_executed',
                    blocking_issue_count INTEGER NOT NULL DEFAULT 0,
                    status VARCHAR(30) NOT NULL DEFAULT 'pending',
                    gate_result TEXT,
                    gate_reject_reason TEXT,
                    git_diff TEXT,
                    git_commit_hash VARCHAR(100),
                    branch_name VARCHAR(200),
                    submitter VARCHAR(100),
                    reviewed_by VARCHAR(100),
                    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                    updated_at DATETIME
                )
            """))
            conn.execute(text("CREATE INDEX idx_submissions_status ON submissions(status)"))
            conn.execute(text("CREATE INDEX idx_submissions_created_at ON submissions(created_at)"))

    # submission_checklists table
    if not insp.has_table("submission_checklists"):
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE submission_checklists (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    submission_id VARCHAR NOT NULL,
                    item TEXT NOT NULL,
                    check_method TEXT,
                    pass_criteria TEXT,
                    risk_level VARCHAR(10) NOT NULL DEFAULT 'medium',
                    category VARCHAR(50) NOT NULL DEFAULT 'general',
                    is_checked BOOLEAN NOT NULL DEFAULT 0,
                    check_result TEXT,
                    checked_by VARCHAR(100),
                    checked_at DATETIME,
                    is_ai_generated BOOLEAN NOT NULL DEFAULT 1,
                    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE
                )
            """))
            conn.execute(text("CREATE INDEX idx_checklists_submission ON submission_checklists(submission_id)"))


def ensure_impact_tables(engine: Engine) -> None:
    """Create impact-analysis tables if they don't exist."""
    insp = inspect(engine)

    # impact_analyses table
    if not insp.has_table("impact_analyses"):
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE impact_analyses (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    submission_id VARCHAR,
                    git_diff TEXT,
                    changed_files TEXT,
                    added_lines INTEGER NOT NULL DEFAULT 0,
                    deleted_lines INTEGER NOT NULL DEFAULT 0,
                    modified_functions TEXT,
                    impact_summary TEXT,
                    confidence_level VARCHAR(20) NOT NULL DEFAULT 'low',
                    status VARCHAR(20) NOT NULL DEFAULT 'completed',
                    analyzed_by VARCHAR(100),
                    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE SET NULL
                )
            """))
            conn.execute(text("CREATE INDEX idx_impact_submission ON impact_analyses(submission_id)"))
            conn.execute(text("CREATE INDEX idx_impact_created_at ON impact_analyses(created_at)"))

    # impacted_modules table
    if not insp.has_table("impacted_modules"):
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE impacted_modules (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    analysis_id VARCHAR NOT NULL,
                    module_name VARCHAR(100) NOT NULL,
                    module_type VARCHAR(20) NOT NULL DEFAULT 'direct',
                    risk_level VARCHAR(10) NOT NULL DEFAULT 'medium',
                    impact_description TEXT,
                    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (analysis_id) REFERENCES impact_analyses(id) ON DELETE CASCADE
                )
            """))
            conn.execute(text("CREATE INDEX idx_modules_analysis ON impacted_modules(analysis_id)"))

    # regression_recommendations table
    if not insp.has_table("regression_recommendations"):
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE regression_recommendations (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    analysis_id VARCHAR NOT NULL,
                    case_id VARCHAR(100),
                    case_title VARCHAR(200),
                    priority VARCHAR(20) NOT NULL DEFAULT 'should',
                    risk_level VARCHAR(10) NOT NULL DEFAULT 'medium',
                    reason TEXT,
                    estimated_minutes INTEGER,
                    category VARCHAR(50),
                    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (analysis_id) REFERENCES impact_analyses(id) ON DELETE CASCADE
                )
            """))
            conn.execute(text("CREATE INDEX idx_recommend_analysis ON regression_recommendations(analysis_id)"))


def ensure_regression_execution_table(engine: Engine) -> None:
    """Create regression execution table if it doesn't exist."""
    insp = inspect(engine)
    if not insp.has_table("regression_executions"):
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE regression_executions (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    recommendation_id VARCHAR NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'not_started',
                    executed_by VARCHAR(100),
                    executed_at DATETIME,
                    actual_result TEXT,
                    comment TEXT,
                    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (recommendation_id) REFERENCES regression_recommendations(id) ON DELETE CASCADE
                )
            """))
            conn.execute(text("CREATE INDEX idx_exec_recommendation ON regression_executions(recommendation_id)"))


def ensure_quick_generate_table(engine: Engine) -> None:
    """Create quick generate records table if it doesn't exist."""
    insp = inspect(engine)
    if not insp.has_table("quick_generate_records"):
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE quick_generate_records (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    requirement_text TEXT NOT NULL,
                    model_name VARCHAR NOT NULL,
                    output_content TEXT NOT NULL,
                    client_model_key VARCHAR,
                    created_at DATETIME NOT NULL DEFAULT (datetime('now'))
                )
            """))
            conn.execute(text("CREATE INDEX idx_quick_created_at ON quick_generate_records(created_at)"))


def ensure_case_review_tables(engine: Engine) -> None:
    """Create case review tables if they don't exist."""
    insp = inspect(engine)

    if not insp.has_table("case_reviews"):
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE case_reviews (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    generation_id VARCHAR(100),
                    case_title VARCHAR(200),
                    requirement_text TEXT,
                    generated_cases TEXT,
                    review_status VARCHAR(30) NOT NULL DEFAULT 'pending',
                    completeness_score INTEGER,
                    executability_score INTEGER,
                    consistency_score INTEGER,
                    redundancy_score INTEGER,
                    coverage_score INTEGER,
                    overall_score INTEGER,
                    ai_review_summary TEXT,
                    ai_review_details TEXT,
                    reviewer VARCHAR(100),
                    reviewer_comment TEXT,
                    decision VARCHAR(20),
                    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                    updated_at DATETIME
                )
            """))
            conn.execute(text("CREATE INDEX idx_reviews_status ON case_reviews(review_status)"))
            conn.execute(text("CREATE INDEX idx_reviews_generation ON case_reviews(generation_id)"))
            conn.execute(text("CREATE INDEX idx_reviews_created ON case_reviews(created_at)"))

    if not insp.has_table("review_comments"):
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE review_comments (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    review_id VARCHAR NOT NULL,
                    author VARCHAR(100),
                    content TEXT NOT NULL,
                    case_id VARCHAR(100),
                    case_title VARCHAR(200),
                    parent_comment_id VARCHAR(100),
                    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                    updated_at DATETIME,
                    FOREIGN KEY (review_id) REFERENCES case_reviews(id) ON DELETE CASCADE
                )
            """))
            conn.execute(text("CREATE INDEX idx_comments_review ON review_comments(review_id)"))


def ensure_auto_test_soft_delete_columns(engine: Engine) -> None:
    """Add is_deleted and deleted_at columns to auto test tables."""
    insp = inspect(engine)
    tables = ["test_suites", "test_cases", "test_plans", "test_executions"]
    with engine.begin() as conn:
        for table in tables:
            if not insp.has_table(table):
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            if "is_deleted" not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT 0"))
            if "deleted_at" not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN deleted_at DATETIME"))


def ensure_append_generate_table(engine: Engine) -> None:
    """Create append generate records table if it doesn't exist."""
    insp = inspect(engine)
    if not insp.has_table("append_generate_records"):
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE append_generate_records (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    existing_cases TEXT NOT NULL,
                    requirement_text TEXT NOT NULL,
                    model_name VARCHAR NOT NULL,
                    appended_content TEXT NOT NULL,
                    total_count INTEGER NOT NULL DEFAULT 0,
                    client_model_key VARCHAR,
                    created_at DATETIME NOT NULL DEFAULT (datetime('now'))
                )
            """))
            conn.execute(text("CREATE INDEX idx_append_created_at ON append_generate_records(created_at)"))


def ensure_defect_table(engine: Engine) -> None:
    """Create defects table if it doesn't exist."""
    insp = inspect(engine)
    if not insp.has_table("defects"):
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE defects (
                    id VARCHAR(36) PRIMARY KEY,
                    submission_id VARCHAR(100),
                    recommendation_id VARCHAR(100),
                    execution_id VARCHAR(100),
                    title VARCHAR(300) NOT NULL,
                    description TEXT,
                    severity VARCHAR(20) NOT NULL DEFAULT 'medium',
                    priority VARCHAR(20) NOT NULL DEFAULT 'medium',
                    status VARCHAR(30) NOT NULL DEFAULT 'open',
                    environment VARCHAR(100),
                    browser VARCHAR(50),
                    root_cause TEXT,
                    attachments TEXT,
                    creator VARCHAR(100),
                    assignee VARCHAR(100),
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE,
                    resolved_at TIMESTAMP WITH TIME ZONE
                )
            """))
            conn.execute(text("CREATE INDEX idx_defects_submission ON defects(submission_id)"))
            conn.execute(text("CREATE INDEX idx_defects_status ON defects(status)"))
            conn.execute(text("CREATE INDEX idx_defects_created_at ON defects(created_at)"))
