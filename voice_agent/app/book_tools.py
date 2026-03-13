"""
Book platform tools for the voice agent.
Queries the book platform database using SQLAlchemy.
"""

import os
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# DB connection from environment (same as main app)
_engine = None
_SessionLocal = None


def _get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        db_url = os.getenv("DB_URL") or os.getenv("DATABASE_URL")
        if not db_url:
            raise ValueError("DB_URL or DATABASE_URL must be set in environment")
        _engine = create_engine(db_url, pool_pre_ping=True)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine, _SessionLocal


def _get_session():
    """Get a database session."""
    _, SessionLocal = _get_engine()
    return SessionLocal()


def search_books(
    query: str,
    genre: Optional[str] = None,
    language: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """
    Search published books by title or description.

    Args:
        query: Search term for title/description.
        genre: Optional genre filter.
        language: Optional language filter.
        limit: Max results (default 10).

    Returns:
        List of books with id, title, author, genre, price.
    """
    session = _get_session()
    try:
        sql = """
            SELECT bp.id, bp.title, bp.genre, bp.language, bp.price,
                   bpu.pen_name as author
            FROM book_projects bp
            JOIN book_platform_users bpu ON bp.author_id = bpu.id
            WHERE (bp.status::text = 'published' OR bp.digital_book_published = true OR bp.audiobook_published = true)
              AND (bp.title ILIKE :query OR (bp.description IS NOT NULL AND bp.description ILIKE :query))
        """
        params = {"query": f"%{query}%", "limit": limit}
        if genre:
            sql += " AND bp.genre ILIKE :genre"
            params["genre"] = f"%{genre}%"
        if language:
            sql += " AND bp.language ILIKE :language"
            params["language"] = f"%{language}%"
        sql += " ORDER BY bp.published_at DESC NULLS LAST LIMIT :limit"

        result = session.execute(text(sql), params)
        rows = result.fetchall()
        return [
            {
                "id": r.id,
                "title": r.title,
                "author": r.author,
                "genre": r.genre,
                "language": r.language,
                "price": float(r.price) if r.price else None,
            }
            for r in rows
        ]
    finally:
        session.close()


def get_book_info(book_id: int) -> Optional[dict]:
    """
    Get book details by ID.

    Args:
        book_id: Book project ID.

    Returns:
        Book details: title, author, price, genre, description, chapters_count, has_audiobook.
    """
    session = _get_session()
    try:
        book = session.execute(
            text("""
                SELECT bp.id, bp.title, bp.description, bp.genre, bp.language,
                       bp.price, bp.audiobook_price, bp.audiobook_published,
                       bpu.pen_name as author
                FROM book_projects bp
                JOIN book_platform_users bpu ON bp.author_id = bpu.id
                WHERE bp.id = :book_id
            """),
            {"book_id": book_id},
        ).fetchone()

        if not book:
            return None

        chapters = session.execute(
            text(
                "SELECT COUNT(*) FROM book_chapters WHERE book_project_id = :book_id"
            ),
            {"book_id": book_id},
        ).scalar() or 0

        return {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "price": float(book.price) if book.price else None,
            "genre": book.genre,
            "description": book.description,
            "chapters_count": chapters,
            "has_audiobook": bool(book.audiobook_published),
            "audiobook_price": float(book.audiobook_price)
            if book.audiobook_price else None,
        }
    finally:
        session.close()


def list_authors(limit: int = 20) -> list[dict]:
    """
    List authors with published books.

    Args:
        limit: Max authors to return (default 20).

    Returns:
        List of authors with pen_name and books count.
    """
    session = _get_session()
    try:
        result = session.execute(
            text("""
                SELECT bpu.id, bpu.pen_name,
                       COUNT(bp.id) as books_count
                FROM book_platform_users bpu
                JOIN book_projects bp ON bp.author_id = bpu.id
                WHERE (bp.status::text = 'published' OR bp.digital_book_published = true OR bp.audiobook_published = true)
                GROUP BY bpu.id, bpu.pen_name
                ORDER BY books_count DESC
                LIMIT :limit
            """),
            {"limit": limit},
        )
        rows = result.fetchall()
        return [
            {
                "id": r.id,
                "pen_name": r.pen_name or "Unknown",
                "books_count": r.books_count,
            }
            for r in rows
        ]
    finally:
        session.close()


def get_author_books(author_name: str) -> list[dict]:
    """
    Get books by author name or pen_name.

    Args:
        author_name: Author pen name or partial match.

    Returns:
        List of books by that author.
    """
    session = _get_session()
    try:
        result = session.execute(
            text("""
                SELECT bp.id, bp.title, bp.genre, bp.price,
                       bp.audiobook_published as has_audiobook
                FROM book_projects bp
                JOIN book_platform_users bpu ON bp.author_id = bpu.id
                WHERE (bp.status::text = 'published' OR bp.digital_book_published = true OR bp.audiobook_published = true)
                  AND bpu.pen_name ILIKE :author_name
                ORDER BY bp.published_at DESC NULLS LAST
            """),
            {"author_name": f"%{author_name}%"},
        )
        rows = result.fetchall()
        return [
            {
                "id": r.id,
                "title": r.title,
                "genre": r.genre,
                "price": float(r.price) if r.price else None,
                "has_audiobook": bool(r.has_audiobook),
            }
            for r in rows
        ]
    finally:
        session.close()


def get_open_campaigns(limit: int = 10) -> list[dict]:
    """
    Get investment campaigns with status ACTIVE.

    Args:
        limit: Max campaigns to return (default 10).

    Returns:
        List of active campaigns with id, title, book, funding info.
    """
    session = _get_session()
    try:
        result = session.execute(
            text("""
                SELECT ic.id, ic.title, ic.funding_goal, ic.current_funding,
                       ic.minimum_investment, bp.title as book_title
                FROM investment_campaigns ic
                JOIN book_projects bp ON ic.book_project_id = bp.id
                WHERE ic.status = 'active'
                ORDER BY ic.created_at DESC
                LIMIT :limit
            """),
            {"limit": limit},
        )
        rows = result.fetchall()
        return [
            {
                "id": r.id,
                "title": r.title,
                "book_title": r.book_title,
                "funding_goal": float(r.funding_goal),
                "current_funding": float(r.current_funding),
                "minimum_investment": float(r.minimum_investment),
            }
            for r in rows
        ]
    finally:
        session.close()


def get_campaign_info(campaign_id: int) -> Optional[dict]:
    """
    Get campaign details by ID.

    Args:
        campaign_id: Investment campaign ID.

    Returns:
        Campaign details: title, book, funding_goal, current_funding, minimum_investment.
    """
    session = _get_session()
    try:
        row = session.execute(
            text("""
                SELECT ic.id, ic.title, ic.description,
                       ic.funding_goal, ic.current_funding, ic.minimum_investment,
                       bp.title as book_title, bp.id as book_id
                FROM investment_campaigns ic
                JOIN book_projects bp ON ic.book_project_id = bp.id
                WHERE ic.id = :campaign_id
            """),
            {"campaign_id": campaign_id},
        ).fetchone()

        if not row:
            return None

        return {
            "id": row.id,
            "title": row.title,
            "description": row.description,
            "book_title": row.book_title,
            "book_id": row.book_id,
            "funding_goal": float(row.funding_goal),
            "current_funding": float(row.current_funding),
            "minimum_investment": float(row.minimum_investment),
        }
    finally:
        session.close()


def get_catalog_stats() -> dict:
    """
    Get catalog statistics: total books, genres count, languages count.

    Returns:
        Dict with total_books, genres_count, languages_count.
    """
    session = _get_session()
    try:
        total = session.execute(
            text("""
                SELECT COUNT(*) FROM book_projects
                WHERE (status::text = 'published' OR digital_book_published = true OR audiobook_published = true)
            """)
        ).scalar() or 0

        genres = session.execute(
            text("""
                SELECT COUNT(DISTINCT genre) FROM book_projects
                WHERE (status::text = 'published' OR digital_book_published = true OR audiobook_published = true)
                  AND genre IS NOT NULL AND genre != ''
            """)
        ).scalar() or 0

        languages = session.execute(
            text("""
                SELECT COUNT(DISTINCT language) FROM book_projects
                WHERE (status::text = 'published' OR digital_book_published = true OR audiobook_published = true)
                  AND language IS NOT NULL AND language != ''
            """)
        ).scalar() or 0

        return {
            "total_books": total,
            "genres_count": genres,
            "languages_count": languages,
        }
    finally:
        session.close()
