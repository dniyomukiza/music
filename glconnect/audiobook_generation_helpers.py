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
from glconnect.book_utils import is_book_published
from glconnect.digital_book_processor import digital_book_processor

logger = logging.getLogger(__name__)


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
                "error": "Digital book file not found. Please re-upload the book.",
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
        chapters_for_audio = build_uploaded_book_audiobook_chapters(full_text)
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
                    'Mark each section you want in audio as "Chapter complete" before generating an audiobook.'
                )
                return {
                    "success": False,
                    "error": error_msg,
                    "full_text": "",
                    "chapters_for_audio": [],
                    "source_hash": "",
                }

        chapters_for_audio = []
        for chapter in chapters:
            chapter_text = ""
            chapter_text += f"Chapter {chapter.chapter_number}: {chapter.title}\n\n"
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
                        "title": f"Chapter {chapter.chapter_number}: {chapter.title}",
                        "text": chapter_text,
                        "chapter_number": chapter.chapter_number,
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
    for i, ch in enumerate(picked, start=1):
        ch["chapter_number"] = i
    return picked, None
