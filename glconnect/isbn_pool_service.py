"""
Platform ISBN pool for self-publishing: assign one ISBN per listed title (ebook + audiobook share it).
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import text

logger = logging.getLogger(__name__)

DEFAULT_PUBLISHER_NAME = "GLC.COOL"


class IsbnPoolError(Exception):
    """Raised when an ISBN cannot be assigned (e.g. pool exhausted)."""


class IsbnValidationError(Exception):
    """Raised when an author-supplied ISBN is invalid or already in use."""


def platform_publisher_name() -> str:
    return (os.getenv("INK_STUDIO_PUBLISHER_NAME") or DEFAULT_PUBLISHER_NAME).strip() or DEFAULT_PUBLISHER_NAME


def validate_isbn13(raw: str) -> str:
    """Validate ISBN-13 (or ISBN-10 converted to ISBN-13). Returns 13 digits."""
    cleaned = re.sub(r"[^0-9Xx]", "", (raw or "").strip()).upper()
    if len(cleaned) == 10:
        core12 = f"978{cleaned[:9]}"
        cleaned = core12 + isbn13_check_digit(core12)
    if len(cleaned) != 13 or not cleaned.isdigit():
        raise IsbnValidationError("Enter a valid 13-digit ISBN (hyphens optional).")
    if cleaned[-1] != isbn13_check_digit(cleaned[:12]):
        raise IsbnValidationError("That ISBN check digit is invalid — double-check the number.")
    return cleaned


def count_available_pool_isbns(db) -> int:
    from glconnect.book_platform_models import IsbnPoolEntry, IsbnPoolStatus

    try:
        return (
            db.session.query(IsbnPoolEntry.id)
            .filter_by(status=IsbnPoolStatus.AVAILABLE)
            .count()
        )
    except Exception:
        return 0


def normalize_isbn(raw: str) -> str:
    """Digits only (ISBN-13)."""
    return re.sub(r"[^0-9Xx]", "", (raw or "").strip()).upper().replace("X", "10")[:13]


def format_isbn_display(isbn: str) -> str:
    """Human-readable ISBN-13 grouping."""
    d = normalize_isbn(isbn)
    if len(d) != 13:
        return isbn or ""
    return f"{d[0:3]}-{d[3:10]}-{d[10:12]}-{d[12]}"


def isbn13_check_digit(core12: str) -> str:
    total = 0
    for i, ch in enumerate(core12):
        n = int(ch)
        total += n * (1 if i % 2 == 0 else 3)
    return str((10 - (total % 10)) % 10)


def build_dummy_isbn13(serial: int) -> str:
    """Dummy pool ISBNs: 9781999990XXX + valid check digit (dev / staging)."""
    serial = max(0, min(serial, 999))
    core12 = f"9781999990{serial:03d}"[:12]
    if len(core12) != 12:
        core12 = (core12 + "0" * 12)[:12]
    return core12 + isbn13_check_digit(core12)


def ensure_isbn_pool_schema(db) -> None:
    """Create isbn_pool + book_projects.publisher_name if missing."""
    if os.getenv("INK_STUDIO_SKIP_SCHEMA_PATCH") == "1":
        return
    try:
        dialect = db.engine.dialect.name
    except Exception as e:
        logger.warning("ISBN pool schema: dialect check failed: %s", e)
        return

    if dialect == "postgresql":
        stmts = [
            """
            CREATE TABLE IF NOT EXISTS isbn_pool (
                id SERIAL PRIMARY KEY,
                isbn VARCHAR(20) UNIQUE NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'available',
                book_project_id INTEGER REFERENCES book_projects(id) ON DELETE SET NULL,
                assigned_at TIMESTAMP,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            "CREATE INDEX IF NOT EXISTS ix_isbn_pool_status ON isbn_pool(status)",
            "CREATE INDEX IF NOT EXISTS ix_isbn_pool_book_project_id ON isbn_pool(book_project_id)",
            "ALTER TABLE book_projects ADD COLUMN IF NOT EXISTS publisher_name VARCHAR(200)",
            "ALTER TABLE book_projects ADD COLUMN IF NOT EXISTS isbn_assigned_at TIMESTAMP",
            "ALTER TABLE book_projects ADD COLUMN IF NOT EXISTS isbn_source VARCHAR(20)",
        ]
        try:
            for stmt in stmts:
                db.session.execute(text(stmt))
            db.session.commit()
            logger.info("ISBN pool schema verified (PostgreSQL).")
        except Exception as e:
            db.session.rollback()
            logger.error("ISBN pool schema patch failed: %s", e, exc_info=True)
    elif dialect == "sqlite":
        try:
            db.session.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS isbn_pool (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        isbn VARCHAR(20) UNIQUE NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'available',
                        book_project_id INTEGER REFERENCES book_projects(id),
                        assigned_at TIMESTAMP,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.warning("ISBN pool sqlite table: %s", e)


def seed_dummy_isbn_pool(db, count: int = 100, force: bool = False) -> int:
    """Insert dummy ISBNs when pool is empty (or force re-seed only if force and empty)."""
    from glconnect.book_platform_models import IsbnPoolEntry, IsbnPoolStatus

    existing = db.session.query(IsbnPoolEntry.id).limit(1).first()
    if existing and not force:
        return 0

    if force and existing:
        db.session.query(IsbnPoolEntry).filter(
            IsbnPoolEntry.status == IsbnPoolStatus.AVAILABLE
        ).delete(synchronize_session=False)
        db.session.commit()

    added = 0
    seen = set()
    for i in range(count * 2):
        if added >= count:
            break
        isbn = build_dummy_isbn13(added + i)
        if isbn in seen:
            continue
        seen.add(isbn)
        if db.session.query(IsbnPoolEntry.id).filter_by(isbn=isbn).first():
            continue
        db.session.add(
            IsbnPoolEntry(
                isbn=isbn,
                status=IsbnPoolStatus.AVAILABLE,
                notes="Dummy ISBN for platform pool (replace with purchased blocks in production).",
            )
        )
        added += 1
    if added:
        db.session.commit()
        logger.info("Seeded %s dummy ISBN(s) into pool.", added)
    return added


def assign_marketplace_isbn_if_needed(book) -> Tuple[Optional[str], str]:
    """
    When a book is listed on the marketplace, assign the next pool ISBN once.
    Same ISBN applies to ebook, print, and audiobook formats on that title.
    Returns (isbn, publisher_name). Raises IsbnPoolError if pool empty and ISBN required.
    """
    from glconnect.book_utils import is_book_published
    from glconnect.book_platform_models import IsbnPoolEntry, IsbnPoolStatus

    publisher = platform_publisher_name()

    if not book or not is_book_published(book):
        return book.isbn if book else None, publisher

    if book.isbn:
        if not getattr(book, "publisher_name", None):
            book.publisher_name = publisher
        return book.isbn, book.publisher_name or publisher

    q = (
        IsbnPoolEntry.query.filter_by(status=IsbnPoolStatus.AVAILABLE)
        .order_by(IsbnPoolEntry.id.asc())
    )
    try:
        entry = q.with_for_update(skip_locked=True).first()
    except Exception:
        entry = q.first()
    if not entry:
        raise IsbnPoolError(
            "No ISBN is available in the platform pool. Please contact support before listing on the marketplace."
        )

    now = datetime.now(timezone.utc)
    isbn = normalize_isbn(entry.isbn)
    entry.status = IsbnPoolStatus.ASSIGNED
    entry.book_project_id = book.id
    entry.assigned_at = now
    book.isbn = isbn
    book.publisher_name = publisher
    if hasattr(book, "isbn_source"):
        book.isbn_source = "pool"
    if hasattr(book, "isbn_assigned_at"):
        book.isbn_assigned_at = now

    logger.info(
        "Assigned pool ISBN %s to book %s (%s); publisher=%s",
        isbn,
        book.id,
        book.title,
        publisher,
    )
    return isbn, publisher


def apply_listing_isbn(book, source: Optional[str] = None, manual_raw: Optional[str] = None) -> Tuple[str, str]:
    """
    Assign ISBN when listing a title (ebook, print, or audiobook share one ISBN per book).
    source: 'pool' (next available platform ISBN) or 'manual' (author-supplied).
    """
    from glconnect.book_utils import is_book_published
    from glconnect.book_platform_models import BookProject

    publisher = platform_publisher_name()

    if not book or not is_book_published(book):
        return (book.isbn if book else None), publisher

    if book.isbn:
        if not getattr(book, "publisher_name", None):
            book.publisher_name = publisher
        return book.isbn, book.publisher_name or publisher

    mode = (source or "pool").strip().lower()
    if mode in ("manual", "author", "own"):
        if not manual_raw or not str(manual_raw).strip():
            raise IsbnValidationError(
                "Enter your ISBN or choose “Assign from platform pool”."
            )
        isbn = validate_isbn13(manual_raw)
        clash = BookProject.query.filter(
            BookProject.isbn == isbn,
            BookProject.id != book.id,
        ).first()
        if clash:
            raise IsbnValidationError(
                "That ISBN is already used on another title in the marketplace."
            )
        now = datetime.now(timezone.utc)
        book.isbn = isbn
        book.publisher_name = publisher
        if hasattr(book, "isbn_source"):
            book.isbn_source = "author"
        if hasattr(book, "isbn_assigned_at"):
            book.isbn_assigned_at = now
        logger.info(
            "Author-supplied ISBN %s on book %s (%s); publisher=%s",
            isbn,
            book.id,
            book.title,
            publisher,
        )
        return isbn, publisher

    isbn, pub = assign_marketplace_isbn_if_needed(book)
    return isbn, pub


def bootstrap_isbn_pool(db) -> None:
    """Schema + seed on app startup."""
    ensure_isbn_pool_schema(db)
    try:
        seed_dummy_isbn_pool(db, count=int(os.getenv("ISBN_POOL_SEED_COUNT", "100")))
    except Exception as e:
        db.session.rollback()
        logger.warning("ISBN pool seed skipped: %s", e)
