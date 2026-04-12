"""
Split plain extracted text into logical chapters for Audible-style per-chapter audio.

Used for uploaded digital books (PDF/EPUB/TXT) so TTS produces one file per segment
instead of a single multi-hour track.
"""

from __future__ import annotations

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Minimum words for a segment to stand alone (avoid tiny fragments)
_MIN_SEGMENT_WORDS = 80
# When no chapter headings are found, split by word count (~12–15 min of speech)
_DEFAULT_PART_WORDS = 4200
# Regex: start of line looks like a chapter / part heading
_CHAPTER_HEADING = re.compile(
    r'^\s*(?:'
    r'chapter|ch\.?|part|book|episode|section|act'
    r')\s+'
    r'(?:[0-9]{1,4}|[IVXLCDM]{1,8}|[A-Z]|[a-z]+)\b'
    r'(?:\s*[:\.\-–—]\s*|\s+)',
    re.IGNORECASE | re.MULTILINE,
)
# Simpler: "Chapter 1" on its own line
_SIMPLE_CHAPTER = re.compile(
    r'^\s*(?:chapter|ch\.?|part)\s+([0-9]{1,4}|[IVXLCDM]{1,8})\s*$',
    re.IGNORECASE | re.MULTILINE,
)


def _word_count(s: str) -> int:
    return len(s.split())


def _split_by_headings(text: str) -> List[tuple[str, str]]:
    """
    Returns list of (heading_or_title, body) using regex split on chapter-like lines.
    First segment may have empty heading if text starts without a heading.
    """
    text = text.strip()
    if not text:
        return []

    # Try heading-based splits: find all match positions
    matches = list(_CHAPTER_HEADING.finditer(text))
    if len(matches) < 2:
        matches = list(_SIMPLE_CHAPTER.finditer(text))

    if len(matches) < 2:
        return []

    segments: List[tuple[str, str]] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end].strip()
        line_end = block.find('\n')
        if line_end == -1:
            heading = block[:80].strip()
            body = ''
        else:
            heading = block[:line_end].strip()
            body = block[line_end + 1 :].strip()
        segments.append((heading, body))

    return segments


def _split_by_word_budget(text: str, words_per_part: int) -> List[str]:
    """Split long text into roughly equal word-count parts."""
    words = text.split()
    if not words:
        return []
    parts: List[str] = []
    i = 0
    while i < len(words):
        chunk = words[i : i + words_per_part]
        parts.append(' '.join(chunk))
        i += words_per_part
    return parts


def build_uploaded_book_audiobook_chapters(
    full_text: str,
    *,
    part_words: int = _DEFAULT_PART_WORDS,
) -> List[Dict[str, Any]]:
    """
    Build chapter dicts compatible with AudioBookGenerator.generate_audiobook_by_chapters:
    title, text, chapter_number, book_chapter_id (None for uploads).
    """
    cleaned = re.sub(r'\r\n?', '\n', (full_text or '').strip())
    if not cleaned:
        return []

    segments = _split_by_headings(cleaned)
    chapters: List[Dict[str, Any]] = []

    if segments:
        # Preamble before first heading (copyright, dedication) → merge into first chapter audio
        first_start = None
        for pat in (_CHAPTER_HEADING, _SIMPLE_CHAPTER):
            m = pat.search(cleaned)
            if m and (first_start is None or m.start() < first_start):
                first_start = m.start()
        if first_start and first_start > 40:
            pre = cleaned[:first_start].strip()
            if pre and _word_count(pre) >= 20:
                h0, b0 = segments[0]
                combined_open = (pre + '\n\n' + b0).strip() if b0 else pre
                segments[0] = (h0, combined_open)

        n = 0
        for heading, body in segments:
            combined = f"{heading}\n\n{body}".strip() if body else heading
            if _word_count(combined) < _MIN_SEGMENT_WORDS and chapters:
                # Merge tiny fragment into previous chapter
                prev = chapters[-1]
                prev['text'] = (prev['text'] + '\n\n' + combined).strip()
                continue
            n += 1
            title = heading if heading else f'Part {n}'
            chapters.append(
                {
                    'title': title[:300] if len(title) > 300 else title,
                    'text': combined,
                    'chapter_number': n,
                    'book_chapter_id': None,
                }
            )

    substantial = sum(1 for c in chapters if _word_count(c['text']) >= _MIN_SEGMENT_WORDS)
    use_heading_chapters = len(chapters) >= 2 or (
        len(chapters) == 1 and substantial >= 1 and _word_count(chapters[0]['text']) >= 1200
    )
    if not use_heading_chapters:
        # No reliable headings — split by word budget (Audible-style "parts")
        chapters = []
        for i, part_text in enumerate(_split_by_word_budget(cleaned, part_words), start=1):
            if not part_text.strip():
                continue
            chapters.append(
                {
                    'title': f'Part {i}',
                    'text': part_text.strip(),
                    'chapter_number': i,
                    'book_chapter_id': None,
                }
            )

    if not chapters:
        chapters.append(
            {
                'title': 'Full audiobook',
                'text': cleaned,
                'chapter_number': 1,
                'book_chapter_id': None,
            }
        )

    logger.info(
        'Segmented uploaded book text into %s audiobook chapter(s) (total words ~%s)',
        len(chapters),
        sum(_word_count(c['text']) for c in chapters),
    )
    return chapters
