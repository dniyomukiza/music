"""
Build extracted text and per-chapter segments for audiobook generation.

Shared by prepare-audiobook-segments and generate-audiobook routes.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from glconnect.audiobook_text_segments import build_uploaded_book_audiobook_chapters
from glconnect.book_platform_models import BookChapter, BookProject
from glconnect.book_utils import is_book_published, resolve_section_kind, section_kind_label
from glconnect.digital_book_processor import digital_book_processor

logger = logging.getLogger(__name__)

_CHAPTER_TITLE = re.compile(r'(?i)^\s*(chapter|ch\.?|part)\b')


def _audiobook_display_title(title: str, kind: str, narrative_index: int | None) -> str:
    t = (title or '').strip()
    if kind == 'chapter':
        if _CHAPTER_TITLE.match(t):
            return t
        if narrative_index:
            return f'Chapter {narrative_index}: {t}' if t else f'Chapter {narrative_index}'
        return t or 'Chapter'
    return t or section_kind_label(kind)


def _attach_section_kind_to_uploaded_chapters(chapters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    narrative_index = 0
    out: List[Dict[str, Any]] = []
    for ch in chapters:
        kind = resolve_section_kind(ch.get('title'))
        if kind == 'chapter':
            narrative_index += 1
            n_idx = narrative_index
        else:
            n_idx = None
        row = dict(ch)
        row['section_kind'] = kind
        row['kind_label'] = section_kind_label(kind)
        row['is_narrative_chapter'] = kind == 'chapter'
        row['narrative_chapter_index'] = n_idx
        row['reading_order'] = ch.get('chapter_number')
        row['title'] = _audiobook_display_title(ch.get('title') or '', kind, n_idx)
        out.append(row)
    return out


def build_audiobook_source(
    book: BookProject,
    app_root_path: str,
) -> Dict[str, Any]:
    """
    Returns:
        success, error?, full_text, chapters_for_audio, source_hash
    """
    book_id = book.id
    full_text = ""

    if book.digital_file_path:
        digital_file_path = os.path.join(app_root_path, "static", book.digital_file_path)
        if not os.path.exists(digital_file_path):
            return {
                "success": False,
                "error": "Digital book file not found. Please re upload the book.",
                "full_text": "",
                "chapters_for_audio": [],
                "source_hash": "",
            }
        file_type = book.digital_file_type or os.path.splitext(digital_file_path)[1].lstrip(".")
        extraction_result = digital_book_processor.extract_text(digital_file_path, file_type)
        if not extraction_result["success"]:
            return {
                "success": False,
                "error": f'Failed to extract text from digital book: {extraction_result.get("error", "Unknown error")}',
                "full_text": "",
                "chapters_for_audio": [],
                "source_hash": "",
            }
        full_text = extraction_result.get("text", "")
        if not full_text.strip():
            return {
                "success": False,
                "error": "No text content found in the uploaded digital book file.",
                "full_text": "",
                "chapters_for_audio": [],
                "source_hash": "",
            }
        chapters_for_audio = _attach_section_kind_to_uploaded_chapters(
            build_uploaded_book_audiobook_chapters(full_text)
        )
    else:
        all_chapters = (
            BookChapter.query.filter_by(book_project_id=book_id)
            .order_by(BookChapter.chapter_number)
            .all()
        )
        if not all_chapters:
            return {
                "success": False,
                "error": "No chapters found. Please create at least one chapter before generating an audiobook.",
                "full_text": "",
                "chapters_for_audio": [],
                "source_hash": "",
            }
        chapters = [ch for ch in all_chapters if ch.is_published]
        if not chapters:
            chapters_with_content = [ch for ch in all_chapters if (ch.content or ch.summary)]
            if is_book_published(book) and chapters_with_content:
                logger.info(
                    "Book %s is published but chapters not individually marked. Using chapters with content.",
                    book_id,
                )
                chapters = chapters_with_content
            else:
                unpublished_with_content = [
                    ch for ch in all_chapters if not ch.is_published and (ch.content or ch.summary)
                ]
                unpublished_count = len(unpublished_with_content)
                error_msg = (
                    f"No complete sections found. You have {len(all_chapters)} section(s) total, "
                    "but none are marked complete. "
                )
                if unpublished_with_content:
                    error_msg += (
                        f"You have {unpublished_count} in-progress section(s) with content. "
                    )
                error_msg += (
                    'Mark each section you want in audio as "Section complete" before generating an audiobook.'
                )
                return {
                    "success": False,
                    "error": error_msg,
                    "full_text": "",
                    "chapters_for_audio": [],
                    "source_hash": "",
                }

        chapters_for_audio = []
        narrative_index = 0
        for chapter in chapters:
            kind = resolve_section_kind(chapter.title, getattr(chapter, 'section_kind', None))
            if kind == 'chapter':
                narrative_index += 1
                n_idx = narrative_index
            else:
                n_idx = None
            display_title = _audiobook_display_title(chapter.title, kind, n_idx)

            chapter_text = f"{display_title}\n\n"
            if chapter.summary:
                clean_summary = re.sub(r"<[^>]+>", "", chapter.summary)
                clean_summary = re.sub(r"\s+", " ", clean_summary).strip()
                if clean_summary:
                    chapter_text += f"Summary: {clean_summary}\n\n"
            if chapter.content:
                clean_content = re.sub(r"<[^>]+>", "", chapter.content)
                clean_content = re.sub(r"\s+", " ", clean_content).strip()
                if clean_content:
                    chapter_text += f"{clean_content}\n\n"
            if chapter_text.strip():
                chapters_for_audio.append(
                    {
                        "title": display_title,
                        "text": chapter_text,
                        "chapter_number": chapter.chapter_number,
                        "reading_order": chapter.chapter_number,
                        "narrative_chapter_index": n_idx,
                        "section_kind": kind,
                        "kind_label": section_kind_label(kind),
                        "is_narrative_chapter": kind == 'chapter',
                        "book_chapter_id": chapter.id,
                    }
                )
                full_text += chapter_text

        if not full_text.strip():
            return {
                "success": False,
                "error": (
                    "Published chapters found but they contain no text content. "
                    "Please add content to your chapters before generating an audiobook."
                ),
                "full_text": "",
                "chapters_for_audio": [],
                "source_hash": "",
            }

    raw = full_text.encode("utf-8", errors="replace")
    source_hash = hashlib.sha256(raw).hexdigest()

    return {
        "success": True,
        "error": None,
        "full_text": full_text,
        "chapters_for_audio": chapters_for_audio,
        "source_hash": source_hash,
    }


def filter_and_renumber_chapters(
    chapters_for_audio: List[Dict[str, Any]],
    segment_includes: List[bool],
) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """
    Filter chapters by parallel segment_includes flags; renumber chapter_number 1..N.
    """
    if len(segment_includes) != len(chapters_for_audio):
        return None, (
            f"segment_includes length ({len(segment_includes)}) must match "
            f"number of sections ({len(chapters_for_audio)})."
        )
    picked: List[Dict[str, Any]] = []
    for inc, ch in zip(segment_includes, chapters_for_audio):
        if inc:
            picked.append(dict(ch))
    if not picked:
        return None, "At least one section must be included for the audiobook."
    if not any(ch.get('section_kind') == 'chapter' or ch.get('is_narrative_chapter') for ch in picked):
        return None, (
            "Include at least one content chapter for the audiobook. "
            "Front matter and back matter alone cannot define the narrative."
        )
    audio_track = 0
    narrative_track = 0
    for ch in picked:
        audio_track += 1
        ch['audio_track_number'] = audio_track
        if ch.get('section_kind') == 'chapter' or ch.get('is_narrative_chapter'):
            narrative_track += 1
            ch['narrative_chapter_index'] = narrative_track
            ch['chapter_number'] = narrative_track
        else:
            ch['chapter_number'] = audio_track
    return picked, None
