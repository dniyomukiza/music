"""
Idempotent PostgreSQL patches for schema drift (model ahead of migrated DB).

Production was missing investment_campaigns milestone columns while SQLAlchemy
still mapped them — causing ProgrammingError on any query touching InvestmentCampaign.
See add_campaign_fund_release.sql (same DDL).
"""

import logging
import os

from sqlalchemy import text

logger = logging.getLogger(__name__)


def ensure_investment_campaign_milestone_schema(db) -> None:
    """Add missing milestone columns / payout_requests table if not present."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        logger.info("Skipping investment_campaign schema patch (INK_STUDIO_SKIP_SCHEMA_PATCH=1)")
        return

    try:
        bind = db.engine
        if bind.dialect.name != "postgresql":
            return
    except Exception as e:
        logger.warning("Schema patch: could not inspect dialect: %s", e)
        return

    # Fast path: column exists after add_campaign_fund_release.sql or a prior boot patch
    check = db.session.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'investment_campaigns' "
            "AND column_name = 'author_first_draft_released_at'"
        )
    ).fetchone()
    if check:
        db.session.rollback()
        return

    logger.info("Applying investment_campaign milestone columns (one-time schema catch-up).")

    statements = [
        "ALTER TABLE investment_campaigns ADD COLUMN IF NOT EXISTS author_first_draft_released BOOLEAN DEFAULT FALSE",
        "ALTER TABLE investment_campaigns ADD COLUMN IF NOT EXISTS author_first_draft_released_at TIMESTAMP",
        "ALTER TABLE investment_campaigns ADD COLUMN IF NOT EXISTS author_first_draft_amount DOUBLE PRECISION",
        "ALTER TABLE investment_campaigns ADD COLUMN IF NOT EXISTS author_publication_released BOOLEAN DEFAULT FALSE",
        "ALTER TABLE investment_campaigns ADD COLUMN IF NOT EXISTS author_publication_released_at TIMESTAMP",
        "ALTER TABLE investment_campaigns ADD COLUMN IF NOT EXISTS author_publication_amount DOUBLE PRECISION",
    ]

    create_payout_table = """
CREATE TABLE IF NOT EXISTS author_campaign_payout_requests (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(36) UNIQUE NOT NULL,
    campaign_id INTEGER NOT NULL REFERENCES investment_campaigns(id) ON DELETE CASCADE,
    milestone VARCHAR(30) NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(20) DEFAULT 'pending',
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    approved_by_id INTEGER REFERENCES book_platform_users(id) ON DELETE SET NULL,
    paid_at TIMESTAMP,
    admin_notes TEXT,
    rejection_reason TEXT
)
"""

    index_stmts = [
        "CREATE INDEX IF NOT EXISTS ix_author_campaign_payout_requests_campaign_id ON author_campaign_payout_requests(campaign_id)",
        "CREATE INDEX IF NOT EXISTS ix_author_campaign_payout_requests_status ON author_campaign_payout_requests(status)",
    ]

    try:
        for stmt in statements:
            db.session.execute(text(stmt))
        db.session.execute(text(create_payout_table))
        for stmt in index_stmts:
            db.session.execute(text(stmt))
        db.session.commit()
        logger.info("Investment campaign milestone schema verified/patched (PostgreSQL).")
    except Exception as e:
        db.session.rollback()
        logger.error(
            "Could not apply investment_campaign milestone schema patch: %s. "
            "Run: python run_campaign_milestone_migration.py with DATABASE_URL set.",
            e,
            exc_info=True,
        )
        raise


def ensure_digital_book_editions_schema(db) -> None:
    """Create digital_book_editions if missing (PostgreSQL). SQLite uses metadata create_all."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        bind = db.engine
        if bind.dialect.name != "postgresql":
            return
    except Exception as e:
        logger.warning("digital_book_editions patch: dialect check failed: %s", e)
        return

    check = db.session.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'digital_book_editions'"
        )
    ).fetchone()
    db.session.rollback()
    if check:
        return

    logger.info("Creating digital_book_editions table (PostgreSQL catch-up).")
    stmts = [
        """
CREATE TABLE digital_book_editions (
    id SERIAL PRIMARY KEY,
    book_project_id INTEGER NOT NULL REFERENCES book_projects(id) ON DELETE CASCADE,
    language_code VARCHAR(10) NOT NULL,
    digital_file_path VARCHAR(500),
    file_format VARCHAR(10) DEFAULT 'txt' NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    CONSTRAINT uq_digital_edition_book_lang UNIQUE (book_project_id, language_code)
)
""".strip(),
        "CREATE INDEX IF NOT EXISTS ix_digital_book_editions_book_project_id ON digital_book_editions(book_project_id)",
    ]
    try:
        for stmt in stmts:
            db.session.execute(text(stmt))
        db.session.commit()
        logger.info("digital_book_editions table ready.")
    except Exception as e:
        db.session.rollback()
        logger.error("Could not create digital_book_editions: %s", e, exc_info=True)
