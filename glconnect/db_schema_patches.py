"""
Idempotent PostgreSQL patches for schema drift (model ahead of migrated DB).

Production was missing investment_campaigns milestone columns while SQLAlchemy
still mapped them, causing ProgrammingError on any query touching InvestmentCampaign.
See add_campaign_fund_release.sql (same DDL).
"""

import logging
import os

from sqlalchemy import text

logger = logging.getLogger(__name__)


def ensure_reader_book_discussion_schema(db) -> None:
    """Catch up the Book Café tables/columns on older PostgreSQL deployments."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        if db.engine.dialect.name != "postgresql":
            return
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS reader_book_posts (
                id SERIAL PRIMARY KEY,
                book_project_id INTEGER REFERENCES book_projects(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                external_book_title VARCHAR(300), external_book_author VARCHAR(200),
                external_book_cover_url VARCHAR(1000), content TEXT NOT NULL,
                quote TEXT, reading_status VARCHAR(20) DEFAULT 'reading',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.session.execute(text("ALTER TABLE reader_book_posts ADD COLUMN IF NOT EXISTS external_book_title VARCHAR(300)"))
        db.session.execute(text("ALTER TABLE reader_book_posts ADD COLUMN IF NOT EXISTS external_book_author VARCHAR(200)"))
        db.session.execute(text("ALTER TABLE reader_book_posts ADD COLUMN IF NOT EXISTS external_book_cover_url VARCHAR(1000)"))
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS reader_book_comments (
                id SERIAL PRIMARY KEY,
                post_id INTEGER NOT NULL REFERENCES reader_book_posts(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                content TEXT NOT NULL, image_url VARCHAR(1000),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.session.execute(text("ALTER TABLE reader_book_comments ADD COLUMN IF NOT EXISTS image_url VARCHAR(1000)"))
        db.session.commit()
        logger.info("Book Café discussion schema verified.")
    except Exception as e:
        db.session.rollback()
        logger.error("Could not patch Book Café schema: %s", e, exc_info=True)
        raise


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

    logger.info("Applying investment_campaign milestone columns (One time schema catch-up).")

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


def _book_projects_existing_columns(db, dialect: str) -> set:
    if dialect == "postgresql":
        rows = db.session.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'book_projects'"
            )
        ).fetchall()
        db.session.rollback()
        return {r[0].lower() for r in rows}
    if dialect == "sqlite":
        rows = db.session.execute(text("PRAGMA table_info(book_projects)")).fetchall()
        db.session.rollback()
        return {r[1].lower() for r in rows}
    return set()


def ensure_print_edition_schema(db) -> None:
    """Add print edition columns to book_projects."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        dialect = db.engine.dialect.name
    except Exception as e:
        logger.warning("print edition schema patch: dialect check failed: %s", e)
        return
    if dialect not in ("postgresql", "sqlite"):
        return
    try:
        names = _book_projects_existing_columns(db, dialect)
        if not names:
            return
        added = []
        patches = [
            ("print_enabled", "BOOLEAN DEFAULT FALSE NOT NULL"),
            ("print_price", "FLOAT"),
            ("print_shipping_price", "FLOAT DEFAULT 0"),
            ("print_handling_days", "INTEGER DEFAULT 7"),
            ("print_description", "TEXT"),
        ]
        for col, typedef in patches:
            if col in names:
                continue
            if dialect == "postgresql":
                db.session.execute(
                    text(f"ALTER TABLE book_projects ADD COLUMN IF NOT EXISTS {col} {typedef}")
                )
            else:
                db.session.execute(text(f"ALTER TABLE book_projects ADD COLUMN {col} {typedef}"))
            added.append(col)
        if added:
            db.session.commit()
            logger.info("book_projects print columns added (%s): %s", dialect, ", ".join(added))
    except Exception as e:
        db.session.rollback()
        logger.error("Could not patch print edition schema: %s", e, exc_info=True)


def ensure_book_print_orders_schema(db) -> None:
    """Create book_print_orders table if missing."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        dialect = db.engine.dialect.name
    except Exception as e:
        logger.warning("book_print_orders schema patch: dialect check failed: %s", e)
        return
    if dialect not in ("postgresql", "sqlite"):
        return
    try:
        exists = db.session.execute(
            text(
                "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' "
                "AND table_name = 'book_print_orders'"
                if dialect == "postgresql"
                else "SELECT name FROM sqlite_master WHERE type='table' AND name='book_print_orders'"
            )
        ).fetchone()
        db.session.rollback()
        if exists:
            return
        if dialect == "postgresql":
            db.session.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS book_print_orders (
                        id SERIAL PRIMARY KEY,
                        uuid VARCHAR(36) NOT NULL UNIQUE,
                        book_purchase_id INTEGER NOT NULL UNIQUE REFERENCES book_purchases(id) ON DELETE CASCADE,
                        book_project_id INTEGER NOT NULL REFERENCES book_projects(id) ON DELETE CASCADE,
                        book_amount DOUBLE PRECISION NOT NULL DEFAULT 0,
                        shipping_amount DOUBLE PRECISION NOT NULL DEFAULT 0,
                        shipping_name VARCHAR(200),
                        shipping_line1 VARCHAR(200) NOT NULL,
                        shipping_line2 VARCHAR(200),
                        shipping_note VARCHAR(500),
                        shipping_city VARCHAR(100) NOT NULL,
                        shipping_state VARCHAR(100),
                        shipping_postal VARCHAR(30) NOT NULL,
                        shipping_country VARCHAR(2) NOT NULL DEFAULT 'US',
                        status VARCHAR(40) NOT NULL DEFAULT 'pending_fulfillment',
                        tracking_number VARCHAR(200),
                        shipping_carrier VARCHAR(100),
                        handling_days INTEGER,
                        expected_delivery_days INTEGER,
                        shipped_at TIMESTAMP,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP
                    )
                    """
                )
            )
            db.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_book_print_orders_book_project_id "
                    "ON book_print_orders(book_project_id)"
                )
            )
        else:
            db.session.execute(
                text(
                    """
                    CREATE TABLE book_print_orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        uuid VARCHAR(36) NOT NULL UNIQUE,
                        book_purchase_id INTEGER NOT NULL UNIQUE REFERENCES book_purchases(id) ON DELETE CASCADE,
                        book_project_id INTEGER NOT NULL REFERENCES book_projects(id) ON DELETE CASCADE,
                        book_amount FLOAT NOT NULL DEFAULT 0,
                        shipping_amount FLOAT NOT NULL DEFAULT 0,
                        shipping_name VARCHAR(200),
                        shipping_line1 VARCHAR(200) NOT NULL,
                        shipping_line2 VARCHAR(200),
                        shipping_note VARCHAR(500),
                        shipping_city VARCHAR(100) NOT NULL,
                        shipping_state VARCHAR(100),
                        shipping_postal VARCHAR(30) NOT NULL,
                        shipping_country VARCHAR(2) NOT NULL DEFAULT 'US',
                        status VARCHAR(40) NOT NULL DEFAULT 'pending_fulfillment',
                        tracking_number VARCHAR(200),
                        shipping_carrier VARCHAR(100),
                        handling_days INTEGER,
                        expected_delivery_days INTEGER,
                        shipped_at TIMESTAMP,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP
                    )
                    """
                )
            )
        db.session.commit()
        logger.info("book_print_orders table created (%s).", dialect)
    except Exception as e:
        db.session.rollback()
        logger.error("Could not create book_print_orders table: %s", e, exc_info=True)


def ensure_book_print_order_shipping_note_column(db) -> None:
    """Add shipping_note to book_print_orders for delivery instructions from checkout."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        dialect = db.engine.dialect.name
    except Exception as e:
        logger.warning("book_print_orders shipping_note patch: dialect check failed: %s", e)
        return
    if dialect not in ("postgresql", "sqlite"):
        return
    try:
        exists = db.session.execute(
            text(
                "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' "
                "AND table_name = 'book_print_orders'"
                if dialect == "postgresql"
                else "SELECT name FROM sqlite_master WHERE type='table' AND name='book_print_orders'"
            )
        ).fetchone()
        db.session.rollback()
        if not exists:
            return
        if dialect == "postgresql":
            rows = db.session.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'book_print_orders'"
                )
            ).fetchall()
            cols = {r[0].lower() for r in rows}
        else:
            rows = db.session.execute(text("PRAGMA table_info(book_print_orders)")).fetchall()
            cols = {r[1].lower() for r in rows}
        db.session.rollback()
        if "shipping_note" in cols:
            return
        if dialect == "postgresql":
            db.session.execute(
                text(
                    "ALTER TABLE book_print_orders ADD COLUMN IF NOT EXISTS "
                    "shipping_note VARCHAR(500)"
                )
            )
        else:
            db.session.execute(text("ALTER TABLE book_print_orders ADD COLUMN shipping_note VARCHAR(500)"))
        db.session.commit()
        logger.info("book_print_orders.shipping_note column added (%s).", dialect)
    except Exception as e:
        db.session.rollback()
        logger.error("Could not add book_print_orders.shipping_note: %s", e, exc_info=True)


def ensure_book_print_order_fulfillment_columns(db) -> None:
    """Add shipment and handling-promise columns for author fulfillment."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        dialect = db.engine.dialect.name
    except Exception as e:
        logger.warning("book_print_orders fulfillment patch: dialect check failed: %s", e)
        return
    if dialect not in ("postgresql", "sqlite"):
        return
    try:
        exists = db.session.execute(
            text(
                "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' "
                "AND table_name = 'book_print_orders'"
                if dialect == "postgresql"
                else "SELECT name FROM sqlite_master WHERE type='table' AND name='book_print_orders'"
            )
        ).fetchone()
        db.session.rollback()
        if not exists:
            return
        if dialect == "postgresql":
            rows = db.session.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'book_print_orders'"
                )
            ).fetchall()
            cols = {r[0].lower() for r in rows}
        else:
            rows = db.session.execute(text("PRAGMA table_info(book_print_orders)")).fetchall()
            cols = {r[1].lower() for r in rows}
        db.session.rollback()
        changed = False
        if "shipping_carrier" not in cols:
            if dialect == "postgresql":
                db.session.execute(
                    text(
                        "ALTER TABLE book_print_orders ADD COLUMN IF NOT EXISTS "
                        "shipping_carrier VARCHAR(100)"
                    )
                )
            else:
                db.session.execute(
                    text("ALTER TABLE book_print_orders ADD COLUMN shipping_carrier VARCHAR(100)")
                )
            changed = True
        if "handling_days" not in cols:
            if dialect == "postgresql":
                db.session.execute(
                    text(
                        "ALTER TABLE book_print_orders ADD COLUMN IF NOT EXISTS "
                        "handling_days INTEGER"
                    )
                )
            else:
                db.session.execute(
                    text("ALTER TABLE book_print_orders ADD COLUMN handling_days INTEGER")
                )
            changed = True
        if "expected_delivery_days" not in cols:
            if dialect == "postgresql":
                db.session.execute(
                    text(
                        "ALTER TABLE book_print_orders ADD COLUMN IF NOT EXISTS "
                        "expected_delivery_days INTEGER"
                    )
                )
            else:
                db.session.execute(
                    text("ALTER TABLE book_print_orders ADD COLUMN expected_delivery_days INTEGER")
                )
            changed = True
        if changed:
            db.session.commit()
            logger.info("book_print_orders fulfillment columns added (%s).", dialect)
    except Exception as e:
        db.session.rollback()
        logger.error("Could not add book_print_orders fulfillment columns: %s", e, exc_info=True)


def _book_platform_users_existing_columns(db, dialect: str) -> set:
    if dialect == "postgresql":
        rows = db.session.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'book_platform_users'"
            )
        ).fetchall()
        db.session.rollback()
        return {r[0].lower() for r in rows}
    if dialect == "sqlite":
        rows = db.session.execute(text("PRAGMA table_info(book_platform_users)")).fetchall()
        db.session.rollback()
        return {r[1].lower() for r in rows}
    return set()


def ensure_author_publishing_agreement_schema(db) -> None:
    """Add agreement acceptance columns to book_platform_users and book_projects."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        dialect = db.engine.dialect.name
    except Exception as e:
        logger.warning("author publishing agreement schema patch: dialect check failed: %s", e)
        return
    if dialect not in ("postgresql", "sqlite"):
        return
    try:
        user_cols = _book_platform_users_existing_columns(db, dialect)
        if user_cols:
            user_patches = [
                ("author_agreement_version", "VARCHAR(20)"),
                ("author_agreement_accepted_at", "TIMESTAMP"),
            ]
            added_user = []
            for col, typedef in user_patches:
                if col in user_cols:
                    continue
                if dialect == "postgresql":
                    db.session.execute(
                        text(f"ALTER TABLE book_platform_users ADD COLUMN IF NOT EXISTS {col} {typedef}")
                    )
                else:
                    db.session.execute(text(f"ALTER TABLE book_platform_users ADD COLUMN {col} {typedef}"))
                added_user.append(col)
            if added_user:
                db.session.commit()
                logger.info(
                    "book_platform_users agreement columns added (%s): %s",
                    dialect,
                    ", ".join(added_user),
                )

        project_cols = _book_projects_existing_columns(db, dialect)
        if project_cols:
            project_patches = [
                ("listing_attestation_version", "VARCHAR(20)"),
                ("listing_attestation_accepted_at", "TIMESTAMP"),
            ]
            added_proj = []
            for col, typedef in project_patches:
                if col in project_cols:
                    continue
                if dialect == "postgresql":
                    db.session.execute(
                        text(f"ALTER TABLE book_projects ADD COLUMN IF NOT EXISTS {col} {typedef}")
                    )
                else:
                    db.session.execute(text(f"ALTER TABLE book_projects ADD COLUMN {col} {typedef}"))
                added_proj.append(col)
            if added_proj:
                db.session.commit()
                logger.info(
                    "book_projects listing attestation columns added (%s): %s",
                    dialect,
                    ", ".join(added_proj),
                )
    except Exception as e:
        db.session.rollback()
        logger.error("Could not patch author publishing agreement schema: %s", e, exc_info=True)


def _users_existing_columns(db, dialect: str) -> set:
    if dialect == "postgresql":
        rows = db.session.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'users'"
            )
        ).fetchall()
        db.session.rollback()
        return {r[0].lower() for r in rows}
    if dialect == "sqlite":
        rows = db.session.execute(text("PRAGMA table_info(users)")).fetchall()
        db.session.rollback()
        return {r[1].lower() for r in rows}
    return set()


def ensure_user_account_terms_schema(db) -> None:
    """Add account signup terms acceptance columns to users."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        dialect = db.engine.dialect.name
    except Exception as e:
        logger.warning("user account terms schema patch: dialect check failed: %s", e)
        return
    if dialect not in ("postgresql", "sqlite"):
        return
    try:
        user_cols = _users_existing_columns(db, dialect)
        if not user_cols:
            return
        patches = [
            ("account_terms_version", "VARCHAR(20)"),
            ("account_terms_accepted_at", "TIMESTAMP"),
        ]
        added = []
        for col, typedef in patches:
            if col in user_cols:
                continue
            if dialect == "postgresql":
                db.session.execute(
                    text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {typedef}")
                )
            else:
                db.session.execute(text(f"ALTER TABLE users ADD COLUMN {col} {typedef}"))
            added.append(col)
        if added:
            db.session.commit()
            logger.info("users account terms columns added (%s): %s", dialect, ", ".join(added))
    except Exception as e:
        db.session.rollback()
        logger.error("Could not patch users account terms schema: %s", e, exc_info=True)


def _artists_existing_columns(db, dialect: str) -> set:
    if dialect == "postgresql":
        rows = db.session.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'artists'"
            )
        ).fetchall()
        db.session.rollback()
        return {r[0].lower() for r in rows}
    if dialect == "sqlite":
        rows = db.session.execute(text("PRAGMA table_info(artists)")).fetchall()
        db.session.rollback()
        return {r[1].lower() for r in rows}
    return set()


def _songs_existing_columns(db, dialect: str) -> set:
    if dialect == "postgresql":
        rows = db.session.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'songs'"
            )
        ).fetchall()
        db.session.rollback()
        return {r[0].lower() for r in rows}
    if dialect == "sqlite":
        rows = db.session.execute(text("PRAGMA table_info(songs)")).fetchall()
        db.session.rollback()
        return {r[1].lower() for r in rows}
    return set()


def _song_upload_existing_columns(db, dialect: str) -> set:
    if dialect == "postgresql":
        rows = db.session.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'song_upload'"
            )
        ).fetchall()
        db.session.rollback()
        return {r[0].lower() for r in rows}
    if dialect == "sqlite":
        rows = db.session.execute(text("PRAGMA table_info(song_upload)")).fetchall()
        db.session.rollback()
        return {r[1].lower() for r in rows}
    return set()


def _podcast_submissions_existing_columns(db, dialect: str) -> set:
    if dialect == "postgresql":
        rows = db.session.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'podcast_submissions'"
            )
        ).fetchall()
        db.session.rollback()
        return {r[0].lower() for r in rows}
    if dialect == "sqlite":
        rows = db.session.execute(text("PRAGMA table_info(podcast_submissions)")).fetchall()
        db.session.rollback()
        return {r[1].lower() for r in rows}
    return set()


def ensure_glc_media_terms_schema(db) -> None:
    """Add GLC Media terms columns to artists, songs, song_upload, users, and podcast_submissions."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        dialect = db.engine.dialect.name
    except Exception as e:
        logger.warning("glc media terms schema patch: dialect check failed: %s", e)
        return
    if dialect not in ("postgresql", "sqlite"):
        return
    patches = [
        ("artists", _artists_existing_columns, [
            ("glc_media_terms_version", "VARCHAR(20)"),
            ("glc_media_terms_accepted_at", "TIMESTAMP"),
        ]),
        ("songs", _songs_existing_columns, [
            ("glc_media_submission_version", "VARCHAR(20)"),
            ("glc_media_submission_accepted_at", "TIMESTAMP"),
        ]),
        ("song_upload", _song_upload_existing_columns, [
            ("glc_media_submission_version", "VARCHAR(20)"),
            ("glc_media_submission_accepted_at", "TIMESTAMP"),
        ]),
        ("users", _users_existing_columns, [
            ("glc_media_podcaster_terms_version", "VARCHAR(20)"),
            ("glc_media_podcaster_terms_accepted_at", "TIMESTAMP"),
        ]),
        ("podcast_submissions", _podcast_submissions_existing_columns, [
            ("glc_media_submission_version", "VARCHAR(20)"),
            ("glc_media_submission_accepted_at", "TIMESTAMP"),
        ]),
    ]
    try:
        for table, cols_fn, col_defs in patches:
            existing = cols_fn(db, dialect)
            if not existing:
                continue
            added = []
            for col, typedef in col_defs:
                if col in existing:
                    continue
                if dialect == "postgresql":
                    db.session.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {typedef}")
                    )
                else:
                    db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {typedef}"))
                added.append(col)
            if added:
                db.session.commit()
                logger.info("%s glc media columns added (%s): %s", table, dialect, ", ".join(added))
    except Exception as e:
        db.session.rollback()
        logger.error("Could not patch glc media terms schema: %s", e, exc_info=True)


def ensure_campaign_tentative_timeline_schema(db) -> None:
    """Add optional tentative_timeline on investment_campaigns."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        bind = db.engine
        if bind.dialect.name != "postgresql":
            return
    except Exception as e:
        logger.warning("Schema patch: could not inspect dialect: %s", e)
        return

    check = db.session.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'investment_campaigns' "
            "AND column_name = 'tentative_timeline'"
        )
    ).fetchone()
    if check:
        db.session.rollback()
        return

    try:
        db.session.execute(
            text(
                "ALTER TABLE investment_campaigns "
                "ADD COLUMN IF NOT EXISTS tentative_timeline VARCHAR(200)"
            )
        )
        db.session.commit()
        logger.info("Added investment_campaigns.tentative_timeline column")
    except Exception as e:
        db.session.rollback()
        logger.error("Could not add tentative_timeline column: %s", e, exc_info=True)


def ensure_saved_book_campaigns_schema(db) -> None:
    """Create saved_book_campaigns table for patron save-for-later."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        bind = db.engine
        if bind.dialect.name != "postgresql":
            return
    except Exception as e:
        logger.warning("Schema patch: could not inspect dialect: %s", e)
        return

    check = db.session.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'saved_book_campaigns'"
        )
    ).fetchone()
    if check:
        db.session.rollback()
        return

    create_sql = """
CREATE TABLE IF NOT EXISTS saved_book_campaigns (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    campaign_id INTEGER NOT NULL REFERENCES investment_campaigns(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_saved_campaign_user UNIQUE (user_id, campaign_id)
)
"""
    index_stmts = [
        "CREATE INDEX IF NOT EXISTS ix_saved_book_campaigns_user_id ON saved_book_campaigns(user_id)",
        "CREATE INDEX IF NOT EXISTS ix_saved_book_campaigns_campaign_id ON saved_book_campaigns(campaign_id)",
    ]
    try:
        db.session.execute(text(create_sql))
        for stmt in index_stmts:
            db.session.execute(text(stmt))
        db.session.commit()
        logger.info("Created saved_book_campaigns table")
    except Exception as e:
        db.session.rollback()
        logger.error("Could not create saved_book_campaigns table: %s", e, exc_info=True)


def ensure_campaign_platform_fee_schema(db) -> None:
    """Add platform fee snapshot columns on investment_campaigns."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        bind = db.engine
        if bind.dialect.name != "postgresql":
            return
    except Exception as e:
        logger.warning("Schema patch: could not inspect dialect: %s", e)
        return

    stmts = [
        "ALTER TABLE investment_campaigns ADD COLUMN IF NOT EXISTS is_first_author_project BOOLEAN DEFAULT FALSE",
        "ALTER TABLE investment_campaigns ADD COLUMN IF NOT EXISTS campaign_platform_fee_percent DOUBLE PRECISION",
        "ALTER TABLE investment_campaigns ADD COLUMN IF NOT EXISTS campaign_platform_fee_amount DOUBLE PRECISION",
        "ALTER TABLE investment_campaigns ADD COLUMN IF NOT EXISTS author_net_funding DOUBLE PRECISION",
    ]
    try:
        for stmt in stmts:
            db.session.execute(text(stmt))
        db.session.commit()
        logger.info("Ensured investment_campaigns platform fee columns")
    except Exception as e:
        db.session.rollback()
        logger.error("Could not patch campaign platform fee schema: %s", e, exc_info=True)


def ensure_campaign_translations_schema(db) -> None:
    """Create campaign_translations table for AI patron-facing translations."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        bind = db.engine
        if bind.dialect.name != "postgresql":
            return
    except Exception as e:
        logger.warning("Schema patch: could not inspect dialect: %s", e)
        return

    check = db.session.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'campaign_translations'"
        )
    ).fetchone()
    if check:
        db.session.rollback()
        return

    create_sql = """
CREATE TABLE IF NOT EXISTS campaign_translations (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES investment_campaigns(id) ON DELETE CASCADE,
    language VARCHAR(10) NOT NULL,
    translated_title VARCHAR(200),
    translated_book_title VARCHAR(200),
    translated_author_bio TEXT,
    translated_book_description TEXT,
    translated_campaign_description TEXT,
    translated_tentative_timeline VARCHAR(200),
    translation_method VARCHAR(50) DEFAULT 'gemini',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_campaign_translation_lang UNIQUE (campaign_id, language)
)
"""
    index_sql = "CREATE INDEX IF NOT EXISTS ix_campaign_translations_campaign_id ON campaign_translations(campaign_id)"
    try:
        db.session.execute(text(create_sql))
        db.session.execute(text(index_sql))
        db.session.commit()
        logger.info("Created campaign_translations table")
    except Exception as e:
        db.session.rollback()
        logger.error("Could not create campaign_translations table: %s", e, exc_info=True)


def _book_sales_existing_columns(db, dialect: str) -> set:
    if dialect == "postgresql":
        rows = db.session.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'book_sales'"
            )
        ).fetchall()
        db.session.rollback()
        return {r[0].lower() for r in rows}
    if dialect == "sqlite":
        rows = db.session.execute(text("PRAGMA table_info(book_sales)")).fetchall()
        db.session.rollback()
        return {r[1].lower() for r in rows}
    return set()


def ensure_author_format_listing_coupons_schema(db) -> None:
    """Per-format fee overrides, sale audit column, and author_format_listing_coupons table."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        dialect = db.engine.dialect.name
    except Exception as e:
        logger.warning("author format listing coupons schema patch: dialect check failed: %s", e)
        return
    if dialect not in ("postgresql", "sqlite"):
        return
    try:
        book_cols = _book_projects_existing_columns(db, dialect)
        if book_cols:
            fee_patches = [
                ("platform_fee_percent_ebook", "FLOAT"),
                ("platform_fee_percent_audiobook", "FLOAT"),
                ("platform_fee_percent_print", "FLOAT"),
            ]
            added = []
            for col, typedef in fee_patches:
                if col in book_cols:
                    continue
                if dialect == "postgresql":
                    db.session.execute(
                        text(f"ALTER TABLE book_projects ADD COLUMN IF NOT EXISTS {col} {typedef}")
                    )
                else:
                    db.session.execute(text(f"ALTER TABLE book_projects ADD COLUMN {col} {typedef}"))
                added.append(col)
            if added:
                db.session.commit()
                logger.info(
                    "book_projects fee override columns added (%s): %s",
                    dialect,
                    ", ".join(added),
                )

        sale_cols = _book_sales_existing_columns(db, dialect)
        if sale_cols and "platform_fee_percent_applied" not in sale_cols:
            if dialect == "postgresql":
                db.session.execute(
                    text(
                        "ALTER TABLE book_sales ADD COLUMN IF NOT EXISTS "
                        "platform_fee_percent_applied FLOAT"
                    )
                )
            else:
                db.session.execute(
                    text("ALTER TABLE book_sales ADD COLUMN platform_fee_percent_applied FLOAT")
                )
            db.session.commit()
            logger.info("book_sales.platform_fee_percent_applied added (%s)", dialect)

        exists = db.session.execute(
            text(
                "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' "
                "AND table_name = 'author_format_listing_coupons'"
                if dialect == "postgresql"
                else "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='author_format_listing_coupons'"
            )
        ).fetchone()
        db.session.rollback()
        if exists:
            return

        if dialect == "postgresql":
            create_sql = """
CREATE TABLE IF NOT EXISTS author_format_listing_coupons (
    id SERIAL PRIMARY KEY,
    author_id INTEGER NOT NULL REFERENCES book_platform_users(id) ON DELETE CASCADE,
    book_project_id INTEGER NOT NULL REFERENCES book_projects(id) ON DELETE CASCADE,
    earned_from_format VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'available',
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    redeemed_at TIMESTAMP,
    redeemed_for_format VARCHAR(20),
    platform_fee_percent_after FLOAT,
    CONSTRAINT uq_author_format_coupon_book_earned UNIQUE (book_project_id, earned_from_format)
)
"""
        else:
            create_sql = """
CREATE TABLE IF NOT EXISTS author_format_listing_coupons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id INTEGER NOT NULL REFERENCES book_platform_users(id) ON DELETE CASCADE,
    book_project_id INTEGER NOT NULL REFERENCES book_projects(id) ON DELETE CASCADE,
    earned_from_format VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'available',
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    redeemed_at TIMESTAMP,
    redeemed_for_format VARCHAR(20),
    platform_fee_percent_after FLOAT,
    UNIQUE (book_project_id, earned_from_format)
)
"""
        db.session.execute(text(create_sql))
        db.session.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_author_format_coupons_author "
                "ON author_format_listing_coupons(author_id)"
            )
        )
        db.session.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_author_format_coupons_book "
                "ON author_format_listing_coupons(book_project_id)"
            )
        )
        db.session.commit()
        logger.info("author_format_listing_coupons table created (%s).", dialect)
    except Exception as e:
        db.session.rollback()
        logger.error("Could not patch author format listing coupons schema: %s", e, exc_info=True)


def _pg_enum_labels(db, type_name: str) -> list[str]:
    rows = db.session.execute(
        text(
            "SELECT e.enumlabel FROM pg_enum e "
            "JOIN pg_type t ON e.enumtypid = t.oid "
            "WHERE t.typname = :type_name "
            "ORDER BY e.enumsortorder"
        ),
        {"type_name": type_name},
    ).fetchall()
    return [row[0] for row in rows]


def ensure_collaboration_role_enum_schema(db) -> None:
    """Ensure PostgreSQL CollaborationRole enum includes every value defined in the app."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        if db.engine.dialect.name != "postgresql":
            return
    except Exception as e:
        logger.warning("Collaboration role enum patch: dialect check failed: %s", e)
        return

    try:
        from glconnect.book_platform_models import CollaborationRole

        required_values = [role.value for role in CollaborationRole]
    except Exception as e:
        logger.warning("Collaboration role enum patch: could not load roles: %s", e)
        return

    candidate_types = ("collaborationrole", "collaboration_role")

    try:
        patched = False
        for type_name in candidate_types:
            labels = set(_pg_enum_labels(db, type_name))
            if not labels:
                continue
            for value in required_values:
                if value in labels:
                    continue
                logger.info(
                    "Adding missing CollaborationRole enum value %r to PostgreSQL type %s",
                    value,
                    type_name,
                )
                db.session.execute(
                    text(f"ALTER TYPE {type_name} ADD VALUE IF NOT EXISTS '{value}'")
                )
                patched = True
        if patched:
            db.session.commit()
            logger.info("Collaboration role enum patch applied.")
        else:
            db.session.rollback()
    except Exception as e:
        db.session.rollback()
        logger.error("Could not patch CollaborationRole enum: %s", e, exc_info=True)
