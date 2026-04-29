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


def ensure_book_platform_stripe_connect_schema(db) -> None:
    """Add stripe_connect_account_id to book_platform_users if missing."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        dialect = db.engine.dialect.name
    except Exception as e:
        logger.warning("stripe_connect patch: dialect check failed: %s", e)
        return

    col = "stripe_connect_account_id"

    try:
        if dialect == "postgresql":
            db.session.execute(
                text(
                    "ALTER TABLE book_platform_users ADD COLUMN IF NOT EXISTS "
                    "stripe_connect_account_id VARCHAR(255)"
                )
            )
            db.session.commit()
            return

        if dialect == "sqlite":
            rows = db.session.execute(text("PRAGMA table_info(book_platform_users)")).fetchall()
            db.session.rollback()
            names = {r[1] for r in rows}  # (cid, name, type, ...)
            if col in names:
                return
            db.session.execute(
                text(
                    "ALTER TABLE book_platform_users ADD COLUMN stripe_connect_account_id VARCHAR(255)"
                )
            )
            db.session.commit()
            logger.info("book_platform_users.%s column added (SQLite).", col)
    except Exception as e:
        db.session.rollback()
        logger.error(
            "Could not patch book_platform_users for Stripe Connect: %s",
            e,
            exc_info=True,
        )


def ensure_book_cart_schema(db) -> None:
    """Create marketplace cart table if missing."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        dialect = db.engine.dialect.name
    except Exception as e:
        logger.warning("book_cart patch: dialect check failed: %s", e)
        return

    if dialect == "postgresql":
        stmts = [
            """
CREATE TABLE IF NOT EXISTS book_cart_items (
    id SERIAL PRIMARY KEY,
    buyer_user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    book_project_id INTEGER NOT NULL REFERENCES book_projects(id) ON DELETE CASCADE,
    purchase_format VARCHAR(20) NOT NULL DEFAULT 'digital',
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    CONSTRAINT uq_cart_buyer_book_format UNIQUE (buyer_user_id, book_project_id, purchase_format)
)
""".strip(),
            "CREATE INDEX IF NOT EXISTS ix_book_cart_items_buyer_user_id ON book_cart_items(buyer_user_id)",
            "CREATE INDEX IF NOT EXISTS ix_book_cart_items_book_project_id ON book_cart_items(book_project_id)",
        ]
        try:
            for stmt in stmts:
                db.session.execute(text(stmt))
            db.session.commit()
            return
        except Exception as e:
            db.session.rollback()
            logger.error("Could not patch book_cart_items (PostgreSQL): %s", e, exc_info=True)
            return

    if dialect == "sqlite":
        try:
            exists = db.session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='book_cart_items'")
            ).fetchone()
            db.session.rollback()
            if not exists:
                db.session.execute(
                    text(
                        """
CREATE TABLE book_cart_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_user_id INTEGER NOT NULL,
    book_project_id INTEGER NOT NULL,
    purchase_format VARCHAR(20) NOT NULL DEFAULT 'digital',
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE (buyer_user_id, book_project_id, purchase_format),
    FOREIGN KEY(buyer_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY(book_project_id) REFERENCES book_projects(id) ON DELETE CASCADE
)
"""
                    )
                )
            db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_book_cart_items_buyer_user_id ON book_cart_items(buyer_user_id)"))
            db.session.execute(text("CREATE INDEX IF NOT EXISTS ix_book_cart_items_book_project_id ON book_cart_items(book_project_id)"))
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Could not patch book_cart_items (SQLite): %s", e, exc_info=True)


def _book_purchases_existing_columns(db, dialect: str) -> set:
    """Return lowercase column names for book_purchases."""
    if dialect == "postgresql":
        rows = db.session.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'book_purchases'"
            )
        ).fetchall()
        db.session.rollback()
        return {r[0].lower() for r in rows}
    if dialect == "sqlite":
        rows = db.session.execute(text("PRAGMA table_info(book_purchases)")).fetchall()
        db.session.rollback()
        return {r[1].lower() for r in rows}
    return set()


def ensure_book_purchases_schema(db) -> None:
    """
    Align book_purchases with the BookPurchase ORM on older databases.

    Adds any of: buyer_user_id, purchase_format, buyer_username, buyer_full_name.
    Backfills buyer_user_id from book_platform_users when buyer_id is set.
    """
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        dialect = db.engine.dialect.name
    except Exception as e:
        logger.warning("book_purchases schema patch: dialect check failed: %s", e)
        return

    if dialect not in ("postgresql", "sqlite"):
        return

    try:
        names = _book_purchases_existing_columns(db, dialect)
        if not names:
            logger.warning("book_purchases table missing; skip schema patch.")
            return

        added = []
        stmts = []

        if "buyer_user_id" not in names:
            stmts.append(
                "ALTER TABLE book_purchases ADD COLUMN buyer_user_id INTEGER "
                "REFERENCES users(user_id)"
            )
            added.append("buyer_user_id")
        if "purchase_format" not in names:
            stmts.append(
                "ALTER TABLE book_purchases ADD COLUMN purchase_format VARCHAR(20) DEFAULT 'digital'"
            )
            added.append("purchase_format")
        if "buyer_username" not in names:
            stmts.append(
                "ALTER TABLE book_purchases ADD COLUMN buyer_username VARCHAR(80)"
            )
            added.append("buyer_username")
        if "buyer_full_name" not in names:
            stmts.append(
                "ALTER TABLE book_purchases ADD COLUMN buyer_full_name VARCHAR(200)"
            )
            added.append("buyer_full_name")

        for stmt in stmts:
            db.session.execute(text(stmt))

        # Backfill users.user_id for rows that only have BookPlatformUser id
        if "buyer_user_id" in names or "buyer_user_id" in added:
            if dialect == "postgresql":
                db.session.execute(
                    text(
                        "UPDATE book_purchases bp SET buyer_user_id = bpu.user_id "
                        "FROM book_platform_users bpu "
                        "WHERE bp.buyer_id IS NOT NULL AND bp.buyer_user_id IS NULL "
                        "AND bp.buyer_id = bpu.id"
                    )
                )
            else:
                db.session.execute(
                    text(
                        "UPDATE book_purchases SET buyer_user_id = "
                        "(SELECT user_id FROM book_platform_users "
                        "WHERE book_platform_users.id = book_purchases.buyer_id) "
                        "WHERE buyer_id IS NOT NULL AND buyer_user_id IS NULL"
                    )
                )

        db.session.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_book_purchases_buyer_user_id "
                "ON book_purchases(buyer_user_id)"
            )
        )

        db.session.commit()
        if added:
            logger.info(
                "book_purchases schema patched (%s): added columns %s",
                dialect,
                ", ".join(added),
            )
    except Exception as e:
        db.session.rollback()
        logger.error(
            "Could not patch book_purchases schema: %s",
            e,
            exc_info=True,
        )
