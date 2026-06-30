"""Chapter edit suggestions — review before merge for collaborator editors."""

from __future__ import annotations

import difflib
import html
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from glconnect import db


def html_to_plain(text: Optional[str]) -> str:
    if not text:
        return ""
    plain = re.sub(r"<[^>]+>", " ", text)
    plain = re.sub(r"&[a-zA-Z]+;", " ", plain)
    plain = plain.replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", plain).strip()


def build_unified_diff_html(original: Optional[str], proposed: Optional[str]) -> str:
    """Unified diff of plain text extracted from HTML content."""
    a = html_to_plain(original).splitlines()
    b = html_to_plain(proposed).splitlines()
    diff_lines = list(difflib.unified_diff(a, b, fromfile="Current (live)", tofile="Proposed", lineterm=""))
    if not diff_lines:
        return '<p class="text-muted mb-0">No textual changes detected.</p>'

    parts: List[str] = ['<pre class="ink-diff-pre mb-0">']
    for line in diff_lines:
        escaped = html.escape(line)
        if line.startswith("+") and not line.startswith("+++"):
            parts.append(f'<span class="ink-diff-add">{escaped}</span>\n')
        elif line.startswith("-") and not line.startswith("---"):
            parts.append(f'<span class="ink-diff-del">{escaped}</span>\n')
        elif line.startswith("@@"):
            parts.append(f'<span class="ink-diff-hunk">{escaped}</span>\n')
        else:
            parts.append(f"{escaped}\n")
    parts.append("</pre>")
    return "".join(parts)


def title_changed(original: str, proposed: str) -> bool:
    return (original or "").strip() != (proposed or "").strip()


def get_pending_suggestion(chapter_id: int, suggested_by_id: Optional[int] = None):
    from glconnect.book_platform_models import ChapterSuggestion

    q = ChapterSuggestion.query.filter_by(chapter_id=chapter_id, status="pending")
    if suggested_by_id is not None:
        q = q.filter_by(suggested_by_id=suggested_by_id)
    return q.order_by(ChapterSuggestion.created_at.desc()).first()


def pending_suggestions_for_chapter(chapter_id: int):
    from glconnect.book_platform_models import BookPlatformUser, ChapterSuggestion
    from sqlalchemy.orm import joinedload

    return (
        ChapterSuggestion.query.options(
            joinedload(ChapterSuggestion.suggested_by).joinedload(BookPlatformUser.user),
        )
        .filter_by(chapter_id=chapter_id, status="pending")
        .order_by(ChapterSuggestion.created_at.desc())
        .all()
    )


def count_pending_suggestions_for_book(book_id: int) -> int:
    from glconnect.book_platform_models import BookChapter, ChapterSuggestion

    return (
        ChapterSuggestion.query.join(BookChapter, ChapterSuggestion.chapter_id == BookChapter.id)
        .filter(BookChapter.book_project_id == book_id, ChapterSuggestion.status == "pending")
        .count()
    )


def pending_suggestions_for_book(book_id: int):
    from glconnect.book_platform_models import BookChapter, BookPlatformUser, ChapterSuggestion
    from sqlalchemy.orm import joinedload

    return (
        ChapterSuggestion.query.options(
            joinedload(ChapterSuggestion.suggested_by).joinedload(BookPlatformUser.user),
            joinedload(ChapterSuggestion.chapter),
        )
        .join(BookChapter, ChapterSuggestion.chapter_id == BookChapter.id)
        .filter(BookChapter.book_project_id == book_id, ChapterSuggestion.status == "pending")
        .order_by(ChapterSuggestion.created_at.desc())
        .all()
    )


def submit_chapter_suggestion(chapter, submitter, data: Dict[str, Any]):
    """Create or update a pending suggestion; does not mutate the live chapter."""
    from glconnect.book_platform_models import ChapterSuggestion

    suggested_title = data.get("title", chapter.title)
    suggested_content = data.get("content", chapter.content or "")
    suggested_summary = data.get("summary", chapter.summary or "")

    existing = ChapterSuggestion.query.filter_by(
        chapter_id=chapter.id,
        suggested_by_id=submitter.id,
        status="pending",
    ).first()

    if existing:
        existing.suggested_title = suggested_title
        existing.suggested_content = suggested_content
        existing.suggested_summary = suggested_summary
        existing.original_content = chapter.content
        suggestion = existing
    else:
        suggestion = ChapterSuggestion(
            chapter_id=chapter.id,
            suggested_by_id=submitter.id,
            suggested_title=suggested_title,
            suggested_content=suggested_content,
            suggested_summary=suggested_summary,
            original_content=chapter.content,
            status="pending",
        )
        db.session.add(suggestion)

    db.session.flush()
    return suggestion


def notify_author_suggestion_pending(book, suggestion, submitter) -> None:
    from glconnect.book_platform_models import BookNotification

    submitter_name = submitter.pen_name or (
        submitter.user.username if getattr(submitter, "user", None) else "A collaborator"
    )
    chapter_title = suggestion.suggested_title or (suggestion.chapter.title if suggestion.chapter else "Section")
    notification = BookNotification(
        user_id=book.author_id,
        book_project_id=book.id,
        title="Edits awaiting your review",
        message=f'{submitter_name} submitted changes to "{chapter_title}" for your approval.',
        notification_type="suggestion",
    )
    db.session.add(notification)


def mark_suggestion_reviewed(
    suggestion,
    *,
    status: str,
    reviewer_id: int,
    message: str = "",
) -> None:
    suggestion.status = status
    suggestion.reviewed_by_id = reviewer_id
    suggestion.reviewed_at = datetime.now(timezone.utc)
    suggestion.review_message = message or ""


def suggestion_to_review_dict(suggestion) -> Dict[str, Any]:
    chapter = suggestion.chapter
    submitter = suggestion.suggested_by
    submitter_name = "Collaborator"
    if submitter:
        submitter_name = submitter.pen_name or (
            submitter.user.username if getattr(submitter, "user", None) else submitter_name
        )
    live_content = chapter.content if chapter else suggestion.original_content
    live_title = chapter.title if chapter else (suggestion.suggested_title or "")
    return {
        "id": suggestion.id,
        "status": suggestion.status,
        "submitter": submitter_name,
        "created_at": suggestion.created_at.isoformat() if suggestion.created_at else None,
        "live_title": live_title,
        "live_content": live_content or "",
        "proposed_title": suggestion.suggested_title or "",
        "proposed_content": suggestion.suggested_content or "",
        "proposed_summary": suggestion.suggested_summary or "",
        "title_changed": title_changed(live_title, suggestion.suggested_title or ""),
        "diff_html": build_unified_diff_html(live_content, suggestion.suggested_content),
    }
