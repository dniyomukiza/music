"""
Shared utilities for book platform - avoids circular imports.
"""

import re

_FRONT_MATTER_PREFIXES = (
    'foreword', 'preface', 'introduction', 'prologue', 'acknowledgment',
    'acknowledgement', 'acknowledgments', 'acknowledgements', 'dedication',
)
_BACK_MATTER_PREFIXES = (
    'afterword', 'epilogue', 'appendix', 'appendices', 'index', 'bibliography',
    'glossary', 'endnotes', 'endnote', 'colophon', 'notes on',
)
_CHAPTER_TITLE = re.compile(r'(?i)^\s*(chapter|ch\.?|part)\b')


def manuscript_section_kind(title: str) -> str:
    """Classify a manuscript section: front, chapter, back, or other."""
    t = (title or '').strip().lower()
    if not t:
        return 'other'
    if any(t.startswith(p) for p in _FRONT_MATTER_PREFIXES):
        return 'front'
    if any(t.startswith(p) for p in _BACK_MATTER_PREFIXES):
        return 'back'
    if _CHAPTER_TITLE.match(t):
        return 'chapter'
    return 'other'


def manuscript_counts(chapters) -> dict:
    counts = {'chapter': 0, 'front': 0, 'back': 0, 'other': 0}
    for ch in chapters or []:
        counts[resolve_section_kind(
            getattr(ch, 'title', None),
            getattr(ch, 'section_kind', None),
        )] += 1
    return counts


def format_manuscript_summary(chapters) -> str:
    """Human summary, e.g. '1 chapter · 3 sections' for foreword + ch + afterword + appendix."""
    counts = manuscript_counts(chapters)
    parts = []
    n_ch = counts['chapter']
    if n_ch == 1:
        parts.append('1 chapter')
    elif n_ch > 1:
        parts.append(f'{n_ch} chapters')
    extras = counts['front'] + counts['back'] + counts['other']
    if extras == 1:
        parts.append('1 section')
    elif extras > 1:
        parts.append(f'{extras} sections')
    if not parts:
        return 'No sections yet'
    return ' · '.join(parts)


_KIND_LABELS = {
    'front': 'Front matter',
    'back': 'Back matter',
    'chapter': 'Content chapter',
    'other': 'Section',
}

VALID_SECTION_KINDS = frozenset(_KIND_LABELS.keys())


def section_kind_label(kind: str) -> str:
    return _KIND_LABELS.get(kind or '', 'Section')


def resolve_section_kind(title: str, stored_kind: str | None = None) -> str:
    """Prefer explicit section_kind from DB; fall back to title heuristics."""
    kind = (stored_kind or '').strip().lower()
    if kind in VALID_SECTION_KINDS:
        return kind
    return manuscript_section_kind(title)


def normalize_section_kind_input(raw: str | None, title: str) -> str:
    """Validate form/API section_kind or infer from title."""
    return resolve_section_kind(title, raw)


def audiobook_default_include(kind: str) -> bool:
    """Default audiobook narration toggle by section type."""
    if kind == 'chapter':
        return True
    if kind == 'back':
        return False
    if kind == 'front':
        return True
    return False


def manuscript_section_rows(chapters):
    """Ordered display metadata for manuscript list UIs."""
    rows = []
    narrative_index = 0
    for ch in chapters or []:
        kind = resolve_section_kind(
            getattr(ch, 'title', None),
            getattr(ch, 'section_kind', None),
        )
        if kind == 'chapter':
            narrative_index += 1
        rows.append({
            'chapter': ch,
            'kind': kind,
            'kind_label': section_kind_label(kind),
            'display_num': str(narrative_index) if kind == 'chapter' else '·',
            'narrative_index': narrative_index if kind == 'chapter' else None,
        })
    return rows


def manuscript_section_heading(title: str, chapter_number: int) -> str:
    """Subtitle for a section view, use the section title, not 'Chapter N' for foreword etc."""
    t = (title or '').strip()
    if t:
        return t
    kind = manuscript_section_kind(title)
    if kind == 'chapter':
        return f'Chapter {chapter_number}'
    return _KIND_LABELS.get(kind, 'Section')


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
    try:
        from glconnect.book_purchase_format import print_listed

        if print_listed(book):
            return True
    except Exception:
        pass
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
