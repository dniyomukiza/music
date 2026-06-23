"""
Chapter version snapshots for Ink Studio, track edits during collaboration and allow rollbacks.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CHANGE_SOURCES = frozenset(
    {"author_edit", "collaboration", "suggestion_approved", "rollback", "auto"}
)


def resolve_version_actor_id(book, user_id: int) -> Optional[int]:
    """BookPlatformUser.id for the acting user (author or collaborator)."""
    from glconnect.book_platform_models import BookPlatformUser

    bp = BookPlatformUser.query.filter_by(user_id=user_id).first()
    if bp:
        return bp.id
    if book.author and getattr(book.author, "user_id", None) == user_id:
        return book.author_id
    return None


def _get_or_create_current_book_version(book, created_by_id: int):
    from glconnect.book_platform_models import BookVersion

    book_version = BookVersion.query.filter_by(
        book_project_id=book.id, is_current=True
    ).first()
    if book_version:
        return book_version

    n = BookVersion.query.filter_by(book_project_id=book.id).count()
    book_version = BookVersion(
        book_project_id=book.id,
        version_number=f"{n + 1}.0",
        title=book.title,
        word_count=book.word_count or 0,
        is_current=True,
        created_by_id=created_by_id,
    )
    from glconnect import db

    db.session.add(book_version)
    db.session.flush()
    BookVersion.query.filter_by(book_project_id=book.id).filter(
        BookVersion.id != book_version.id
    ).update({"is_current": False})
    return book_version


def snapshot_chapter(
    chapter,
    created_by_id: int,
    change_source: str = "author_edit",
) -> Optional[Any]:
    """
    Persist the chapter's current state before applying new edits.
    Returns ChapterVersion or None if snapshot could not be saved.
    """
    from glconnect import db
    from glconnect.book_platform_models import BookVersion, ChapterVersion

    if not created_by_id:
        return None
    source = change_source if change_source in CHANGE_SOURCES else "author_edit"

    try:
        book = chapter.book_project
        book_version = _get_or_create_current_book_version(book, created_by_id)
        n = ChapterVersion.query.filter_by(chapter_id=chapter.id).count()
        ChapterVersion.query.filter_by(chapter_id=chapter.id).update(
            {"is_current": False}
        )
        version = ChapterVersion(
            chapter_id=chapter.id,
            book_version_id=book_version.id,
            version_number=f"{n + 1}.0",
            title=chapter.title or "",
            content=chapter.content,
            word_count=chapter.word_count or 0,
            is_current=False,
            created_by_id=created_by_id,
            summary=getattr(chapter, "summary", None),
            change_source=source,
        )
        db.session.add(version)
        db.session.flush()
        return version
    except Exception as exc:
        logger.error("Chapter snapshot failed for chapter %s: %s", chapter.id, exc, exc_info=True)
        return None


def chapter_version_to_dict(version) -> Dict[str, Any]:
    author_name = "Unknown"
    if version.created_by:
        author_name = (
            version.created_by.pen_name
            or (
                version.created_by.user.username
                if getattr(version.created_by, "user", None)
                else None
            )
            or "Collaborator"
        )
    return {
        "id": version.id,
        "version_number": version.version_number,
        "title": version.title,
        "word_count": version.word_count or 0,
        "change_source": getattr(version, "change_source", None) or "edit",
        "created_at": version.created_at.isoformat() if version.created_at else None,
        "created_by": author_name,
        "is_current_marker": bool(version.is_current),
        "preview": (version.content or "")[:240],
    }


def list_chapter_versions(chapter_id: int, limit: int = 40) -> List[Dict[str, Any]]:
    from glconnect.book_platform_models import ChapterVersion

    rows = (
        ChapterVersion.query.filter_by(chapter_id=chapter_id)
        .order_by(ChapterVersion.created_at.desc(), ChapterVersion.id.desc())
        .limit(limit)
        .all()
    )
    return [chapter_version_to_dict(v) for v in rows]


def restore_chapter_version(chapter, version_id: int, actor_id: int):
    """
    Roll back chapter to a saved version. Snapshots current state first.
    Returns (success, message, restored_version_dict|None).
    """
    from glconnect import db
    from glconnect.book_platform_models import ChapterVersion

    target = ChapterVersion.query.filter_by(
        id=version_id, chapter_id=chapter.id
    ).first()
    if not target:
        return False, "Version not found.", None

    snapshot_chapter(chapter, actor_id, change_source="rollback")

    chapter.title = target.title
    chapter.content = target.content
    chapter.word_count = target.word_count or 0
    if hasattr(chapter, "summary"):
        chapter.summary = getattr(target, "summary", None) or chapter.summary
    chapter.updated_at = datetime.now(timezone.utc)

    return True, f"Restored version {target.version_number}.", chapter_version_to_dict(target)
