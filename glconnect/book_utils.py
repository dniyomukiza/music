"""
Shared utilities for book platform - avoids circular imports.
"""


def audiobook_ready_for_marketplace_publish(book):
    """
    Server-side guard: only allow audiobook publishing when generation finished
    and at least one audio asset path exists (single file or per-chapter files).
    Returns (ok: bool, error_message or None).
    """
    if not book or not getattr(book, 'has_audiobook', False):
        return False, 'Audiobook must be generated before it can be published.'

    from glconnect import db
    from glconnect.book_platform_models import AudioGenerationTask, AudiobookChapter

    task = (
        AudioGenerationTask.query.filter_by(book_project_id=book.id)
        .order_by(AudioGenerationTask.created_at.desc())
        .first()
    )
    if task and task.status in ('pending', 'processing'):
        return (
            False,
            'Audiobook generation is still in progress. Wait until it completes successfully before publishing.',
        )

    path = (getattr(book, 'audiobook_file_path', None) or '').strip()
    if path:
        return True, None

    n = (
        db.session.query(AudiobookChapter.id)
        .filter(AudiobookChapter.book_project_id == book.id)
        .count()
    )
    if n:
        return True, None

    return (
        False,
        'Audiobook audio files are missing. Regenerate the audiobook before publishing.',
    )


def is_book_published(book):
    """
    Unified check: book is published if:
    - status == PUBLISHED (platform-created books), or
    - digital_book_published == True (uploaded digital), or
    - audiobook_published == True (audiobook)
    """
    if not book:
        return False
    from glconnect.book_platform_models import BookStatus
    if book.status == BookStatus.PUBLISHED:
        return True
    if getattr(book, 'digital_book_published', False):
        return True
    if getattr(book, 'audiobook_published', False):
        return True
    return False


def delete_book_chapter_version_graph_for_project(book_project_id: int) -> None:
    """
    Remove chapter rows and version-control rows for one book in FK-safe order.

    SQLAlchemy relationship cascade does not run for Query.delete(); Postgres FKs on
    chapter_versions.chapter_id are not CASCADE, so bulk-deleting book_chapters alone fails.
    """
    from glconnect import db
    from glconnect.book_platform_models import (
        BookChapter,
        BookVersion,
        ChapterSuggestion,
        ChapterVersion,
    )

    chapter_ids = [
        r[0]
        for r in db.session.query(BookChapter.id)
        .filter(BookChapter.book_project_id == book_project_id)
        .all()
    ]
    if chapter_ids:
        ChapterSuggestion.query.filter(
            ChapterSuggestion.chapter_id.in_(chapter_ids)
        ).delete(synchronize_session=False)
        ChapterVersion.query.filter(
            ChapterVersion.chapter_id.in_(chapter_ids)
        ).delete(synchronize_session=False)

    BookChapter.query.filter(
        BookChapter.book_project_id == book_project_id
    ).delete(synchronize_session=False)

    version_ids = [
        r[0]
        for r in db.session.query(BookVersion.id)
        .filter(BookVersion.book_project_id == book_project_id)
        .all()
    ]
    if version_ids:
        ChapterVersion.query.filter(
            ChapterVersion.book_version_id.in_(version_ids)
        ).delete(synchronize_session=False)

    BookVersion.query.filter(
        BookVersion.book_project_id == book_project_id
    ).delete(synchronize_session=False)
