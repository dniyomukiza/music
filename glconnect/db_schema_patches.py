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


def ensure_author_card_setup_schema(db) -> None:
    """Add author_card_setup_completed to book_platform_users; backfill for existing authors with books."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        dialect = db.engine.dialect.name
    except Exception as e:
        logger.warning("author_card_setup patch: dialect check failed: %s", e)
        return

    col = "author_card_setup_completed"

    try:
        if dialect == "postgresql":
            db.session.execute(
                text(
                    "ALTER TABLE book_platform_users ADD COLUMN IF NOT EXISTS "
                    "author_card_setup_completed BOOLEAN NOT NULL DEFAULT false"
                )
            )
            db.session.execute(
                text(
                    "UPDATE book_platform_users SET author_card_setup_completed = true "
                    "WHERE id IN (SELECT DISTINCT author_id FROM book_projects)"
                )
            )
            db.session.commit()
            logger.info("book_platform_users.%s ready (PostgreSQL).", col)
            return

        if dialect == "sqlite":
            rows = db.session.execute(text("PRAGMA table_info(book_platform_users)")).fetchall()
            db.session.rollback()
            names = {r[1] for r in rows}
            if col not in names:
                db.session.execute(
                    text(
                        "ALTER TABLE book_platform_users ADD COLUMN author_card_setup_completed "
                        "BOOLEAN NOT NULL DEFAULT 0"
                    )
                )
                db.session.commit()
                logger.info("book_platform_users.%s column added (SQLite).", col)
            db.session.execute(
                text(
                    "UPDATE book_platform_users SET author_card_setup_completed = 1 "
                    "WHERE id IN (SELECT DISTINCT author_id FROM book_projects)"
                )
            )
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(
            "Could not patch book_platform_users for author card setup: %s",
            e,
            exc_info=True,
        )


def ensure_book_platform_user_genres_removed(db) -> None:
    """Remove deprecated preferred-genres JSON column from author profiles."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        dialect = db.engine.dialect.name
    except Exception as e:
        logger.warning("drop book_platform_users.genres: dialect check failed: %s", e)
        return

    try:
        if dialect == "postgresql":
            db.session.execute(
                text("ALTER TABLE book_platform_users DROP COLUMN IF EXISTS genres")
            )
            db.session.commit()
            logger.info("book_platform_users.genres dropped if present (PostgreSQL).")
            return

        if dialect == "sqlite":
            rows = db.session.execute(text("PRAGMA table_info(book_platform_users)")).fetchall()
            db.session.rollback()
            names = {r[1] for r in rows}
            if "genres" not in names:
                return
            db.session.execute(text("ALTER TABLE book_platform_users DROP COLUMN genres"))
            db.session.commit()
            logger.info("book_platform_users.genres dropped (SQLite).")
    except Exception as e:
        db.session.rollback()
        logger.warning(
            "Could not drop book_platform_users.genres: %s",
            e,
            exc_info=True,
        )


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


def ensure_audiobook_segment_plan_schema(db) -> None:
    """Add audiobook_segment_plan JSON column to book_projects if missing."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        dialect = db.engine.dialect.name
    except Exception as e:
        logger.warning("audiobook_segment_plan patch: dialect check failed: %s", e)
        return

    col = "audiobook_segment_plan"
    try:
        if dialect == "postgresql":
            db.session.execute(
                text(
                    "ALTER TABLE book_projects ADD COLUMN IF NOT EXISTS audiobook_segment_plan JSONB"
                )
            )
            db.session.commit()
            logger.info("book_projects.%s verified (PostgreSQL).", col)
            return

        if dialect == "sqlite":
            rows = db.session.execute(text("PRAGMA table_info(book_projects)")).fetchall()
            db.session.rollback()
            names = {r[1] for r in rows}
            if col in names:
                return
            db.session.execute(
                text("ALTER TABLE book_projects ADD COLUMN audiobook_segment_plan JSON")
            )
            db.session.commit()
            logger.info("book_projects.%s column added (SQLite).", col)
    except Exception as e:
        db.session.rollback()
        logger.error(
            "Could not patch book_projects for audiobook_segment_plan: %s",
            e,
            exc_info=True,
        )


def ensure_reader_annotations_schema(db) -> None:
    """Persisted highlights / bookmarks / notes for the library ebook reader."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        dialect = db.engine.dialect.name
    except Exception as e:
        logger.warning("reader_annotations patch: dialect check failed: %s", e)
        return

    if dialect == "postgresql":
        stmts = [
            """
CREATE TABLE IF NOT EXISTS reader_annotations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    book_project_id INTEGER NOT NULL REFERENCES book_projects(id) ON DELETE CASCADE,
    section_index INTEGER NOT NULL,
    start_offset INTEGER NOT NULL DEFAULT 0,
    end_offset INTEGER NOT NULL DEFAULT 0,
    quote_text TEXT,
    note_text TEXT,
    kind VARCHAR(20) NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
""".strip(),
            "CREATE INDEX IF NOT EXISTS ix_reader_annotations_user_id ON reader_annotations(user_id)",
            "CREATE INDEX IF NOT EXISTS ix_reader_annotations_book_project_id ON reader_annotations(book_project_id)",
            "CREATE INDEX IF NOT EXISTS ix_reader_annotations_user_book ON reader_annotations(user_id, book_project_id)",
        ]
        try:
            for stmt in stmts:
                db.session.execute(text(stmt))
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Could not patch reader_annotations (PostgreSQL): %s", e, exc_info=True)
        return

    if dialect == "sqlite":
        try:
            exists = db.session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='reader_annotations'")
            ).fetchone()
            db.session.rollback()
            if not exists:
                db.session.execute(
                    text(
                        """
CREATE TABLE reader_annotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    book_project_id INTEGER NOT NULL,
    section_index INTEGER NOT NULL,
    start_offset INTEGER NOT NULL DEFAULT 0,
    end_offset INTEGER NOT NULL DEFAULT 0,
    quote_text TEXT,
    note_text TEXT,
    kind VARCHAR(20) NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY(book_project_id) REFERENCES book_projects(id) ON DELETE CASCADE
)
"""
                    )
                )
            db.session.execute(
                text("CREATE INDEX IF NOT EXISTS ix_reader_annotations_user_id ON reader_annotations(user_id)")
            )
            db.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_reader_annotations_book_project_id ON reader_annotations(book_project_id)"
                )
            )
            db.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_reader_annotations_user_book ON reader_annotations(user_id, book_project_id)"
                )
            )
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Could not patch reader_annotations (SQLite): %s", e, exc_info=True)


def ensure_library_book_hides_schema(db) -> None:
    """Create library_book_hides for optional My Library row removal (UI hide only)."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        dialect = db.engine.dialect.name
    except Exception as e:
        logger.warning("library_book_hides patch: dialect check failed: %s", e)
        return

    if dialect == "postgresql":
        stmts = [
            """
CREATE TABLE IF NOT EXISTS library_book_hides (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    book_project_id INTEGER NOT NULL REFERENCES book_projects(id) ON DELETE CASCADE,
    hide_ebook BOOLEAN NOT NULL DEFAULT false,
    hide_audiobook BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP,
    CONSTRAINT uq_library_hide_user_book UNIQUE (user_id, book_project_id)
)
""".strip(),
            "CREATE INDEX IF NOT EXISTS ix_library_book_hides_user_id ON library_book_hides(user_id)",
            "CREATE INDEX IF NOT EXISTS ix_library_book_hides_book_project_id ON library_book_hides(book_project_id)",
        ]
        try:
            for stmt in stmts:
                db.session.execute(text(stmt))
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Could not patch library_book_hides (PostgreSQL): %s", e, exc_info=True)
        return

    if dialect == "sqlite":
        try:
            exists = db.session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='library_book_hides'")
            ).fetchone()
            db.session.rollback()
            if not exists:
                db.session.execute(
                    text(
                        """
CREATE TABLE library_book_hides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    book_project_id INTEGER NOT NULL,
    hide_ebook BOOLEAN NOT NULL DEFAULT 0,
    hide_audiobook BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP,
    UNIQUE (user_id, book_project_id),
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY(book_project_id) REFERENCES book_projects(id) ON DELETE CASCADE
)
"""
                    )
                )
            db.session.execute(
                text("CREATE INDEX IF NOT EXISTS ix_library_book_hides_user_id ON library_book_hides(user_id)")
            )
            db.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_library_book_hides_book_project_id ON library_book_hides(book_project_id)"
                )
            )
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Could not patch library_book_hides (SQLite): %s", e, exc_info=True)


def _library_book_hides_column_names_lowercase(db) -> set:
    try:
        dialect = db.engine.dialect.name
    except Exception:
        return set()
    if dialect == "postgresql":
        rows = db.session.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'library_book_hides'"
            )
        ).fetchall()
        db.session.rollback()
        return {r[0].lower() for r in rows}
    if dialect == "sqlite":
        rows = db.session.execute(text("PRAGMA table_info(library_book_hides)")).fetchall()
        db.session.rollback()
        return {r[1].lower() for r in rows} if rows else set()
    return set()


def ensure_library_book_hides_format_columns(db) -> None:
    """Add hide_ebook / hide_audiobook; legacy rows mean hide both formats."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        dialect = db.engine.dialect.name
    except Exception as e:
        logger.warning("library_book_hides format patch: dialect check failed: %s", e)
        return
    if dialect not in ("postgresql", "sqlite"):
        return

    exists = db.session.execute(
        text(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'library_book_hides'"
            if dialect == "postgresql"
            else "SELECT name FROM sqlite_master WHERE type='table' AND name='library_book_hides'"
        )
    ).fetchone()
    db.session.rollback()
    if not exists:
        return

    cols = _library_book_hides_column_names_lowercase(db)
    added_any = False
    try:
        if "hide_ebook" not in cols:
            if dialect == "postgresql":
                db.session.execute(
                    text(
                        "ALTER TABLE library_book_hides ADD COLUMN IF NOT EXISTS hide_ebook BOOLEAN NOT NULL DEFAULT false"
                    )
                )
            else:
                db.session.execute(
                    text("ALTER TABLE library_book_hides ADD COLUMN hide_ebook BOOLEAN NOT NULL DEFAULT 0")
                )
            added_any = True
        if "hide_audiobook" not in cols:
            if dialect == "postgresql":
                db.session.execute(
                    text(
                        "ALTER TABLE library_book_hides ADD COLUMN IF NOT EXISTS hide_audiobook BOOLEAN NOT NULL DEFAULT false"
                    )
                )
            else:
                db.session.execute(
                    text("ALTER TABLE library_book_hides ADD COLUMN hide_audiobook BOOLEAN NOT NULL DEFAULT 0")
                )
            added_any = True
        if added_any:
            db.session.execute(
                text(
                    "UPDATE library_book_hides SET hide_ebook = true, hide_audiobook = true"
                    if dialect == "postgresql"
                    else "UPDATE library_book_hides SET hide_ebook = 1, hide_audiobook = 1"
                )
            )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error("Could not patch library_book_hides format columns: %s", e, exc_info=True)


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


def ensure_page_analytics_slim_schema(db) -> None:
    """Drop removed PageAnalytics columns (method, browser, user_agent, referer) if still present."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    legacy = ("method", "browser", "user_agent", "referer")
    try:
        dialect = db.engine.dialect.name
    except Exception:
        return
    try:
        if dialect == "postgresql":
            for col in legacy:
                db.session.execute(
                    text(f"ALTER TABLE page_analytics DROP COLUMN IF EXISTS {col}")
                )
            db.session.commit()
            logger.info("page_analytics: legacy columns dropped if present (PostgreSQL).")
        elif dialect == "sqlite":
            for col in legacy:
                try:
                    db.session.execute(text(f"ALTER TABLE page_analytics DROP COLUMN {col}"))
                    db.session.commit()
                except Exception:
                    db.session.rollback()
    except Exception as e:
        db.session.rollback()
        logger.warning("page_analytics slim schema: %s", e)


def _chapter_versions_column_names(db, dialect: str) -> set:
    if dialect == "postgresql":
        rows = db.session.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'chapter_versions'"
            )
        ).fetchall()
        db.session.rollback()
        return {r[0].lower() for r in rows}
    if dialect == "sqlite":
        rows = db.session.execute(text("PRAGMA table_info(chapter_versions)")).fetchall()
        db.session.rollback()
        return {r[1].lower() for r in rows}
    return set()


def ensure_chapter_versions_metadata_columns(db) -> None:
    """Add summary + change_source for collaboration rollback history."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        dialect = db.engine.dialect.name
    except Exception as e:
        logger.warning("chapter_versions patch: dialect check failed: %s", e)
        return
    if dialect not in ("postgresql", "sqlite"):
        return

    exists = db.session.execute(
        text(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'chapter_versions'"
            if dialect == "postgresql"
            else "SELECT name FROM sqlite_master WHERE type='table' AND name='chapter_versions'"
        )
    ).fetchone()
    db.session.rollback()
    if not exists:
        return

    cols = _chapter_versions_column_names(db, dialect)
    try:
        if "summary" not in cols:
            if dialect == "postgresql":
                db.session.execute(
                    text("ALTER TABLE chapter_versions ADD COLUMN IF NOT EXISTS summary TEXT")
                )
            else:
                db.session.execute(text("ALTER TABLE chapter_versions ADD COLUMN summary TEXT"))
        if "change_source" not in cols:
            if dialect == "postgresql":
                db.session.execute(
                    text(
                        "ALTER TABLE chapter_versions ADD COLUMN IF NOT EXISTS change_source VARCHAR(40)"
                    )
                )
            else:
                db.session.execute(
                    text("ALTER TABLE chapter_versions ADD COLUMN change_source VARCHAR(40)")
                )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error("Could not patch chapter_versions metadata columns: %s", e, exc_info=True)


def ensure_book_chapter_section_kind_schema(db) -> None:
    """Add section_kind to book_chapters for manuscript vs audiobook boundaries."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        dialect = db.engine.dialect.name
    except Exception as e:
        logger.warning("book_chapters section_kind patch: dialect check failed: %s", e)
        return
    if dialect not in ("postgresql", "sqlite"):
        return

    col = "section_kind"
    try:
        if dialect == "postgresql":
            db.session.execute(
                text(
                    "ALTER TABLE book_chapters ADD COLUMN IF NOT EXISTS section_kind VARCHAR(20)"
                )
            )
            db.session.commit()
            return

        rows = db.session.execute(text("PRAGMA table_info(book_chapters)")).fetchall()
        db.session.rollback()
        names = {r[1] for r in rows}
        if col in names:
            return
        db.session.execute(text("ALTER TABLE book_chapters ADD COLUMN section_kind VARCHAR(20)"))
        db.session.commit()
        logger.info("book_chapters.%s column added (SQLite).", col)
    except Exception as e:
        db.session.rollback()
        logger.error("Could not patch book_chapters.section_kind: %s", e, exc_info=True)

