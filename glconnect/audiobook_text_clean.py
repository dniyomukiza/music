"""
Normalize and validate plain text before Google Cloud Text-to-Speech.

Conservative cleaning (Unicode, whitespace, common PDF quirks) plus lightweight
checks to avoid burning TTS on empty or clearly broken extractions.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)

# Zero-width / format characters that should not be spoken
_ZW_AND_BOM = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]")

# Lines that are often repeated headers/footers in PDFs (conservative)
_PAGE_NUMBER_LINE = re.compile(r"^\s*\d{1,4}\s*$")


@dataclass
class TtsTextValidation:
    ok: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def clean_for_tts(text: str | None) -> str:
    """
    Normalize text for speech synthesis without rewriting author content.

    - Unicode NFC, strip BOM and zero-width characters
    - Line endings → \\n; remove soft hyphens (common in PDFs)
    - Trim per-line; collapse horizontal whitespace; cap blank-line runs
    """
    if not text:
        return ""

    s = unicodedata.normalize("NFC", str(text))
    s = s.replace("\ufeff", "")
    s = _ZW_AND_BOM.sub("", s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\u00ad", "")

    raw_lines = s.split("\n")
    lines: List[str] = []
    for line in raw_lines:
        inner = re.sub(r"[ \t\xa0]+", " ", line.strip())
        lines.append(inner)

    # Drop isolated page-number-only lines (weak signal; keeps body intact)
    filtered: List[str] = []
    for i, line in enumerate(lines):
        if line and _PAGE_NUMBER_LINE.match(line):
            prev_empty = i == 0 or not lines[i - 1]
            next_empty = i + 1 >= len(lines) or not lines[i + 1]
            if prev_empty and next_empty:
                continue
        filtered.append(line)

    out: List[str] = []
    prev_blank = True
    for line in filtered:
        if not line:
            if not prev_blank:
                out.append("")
            prev_blank = True
        else:
            out.append(line)
            prev_blank = False

    s = "\n".join(out)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _letter_count(text: str) -> int:
    return sum(1 for c in text if unicodedata.category(c).startswith("L"))


def validate_for_tts(
    text: str,
    *,
    min_letters: int = 10,
    context: str = "",
) -> TtsTextValidation:
    """
    Validate cleaned text before calling TTS.

    ``min_letters`` uses Unicode letter categories so non-Latin voices are supported.
    """
    errors: List[str] = []
    warnings: List[str] = []
    prefix = f"{context}: " if context else ""

    if not (text or "").strip():
        errors.append(f"{prefix}Text is empty after cleaning.")
        return TtsTextValidation(ok=False, errors=errors, warnings=warnings)

    n = len(text)
    letters = _letter_count(text)
    if letters < min_letters:
        errors.append(
            f"{prefix}Too little readable text ({letters} letters); "
            "check extraction or chapter content."
        )

    digits = sum(1 for c in text if c.isdigit())
    if n and digits / n > 0.35:
        warnings.append(f"{prefix}High digit density; possible tables or page numbers.")

    url_n = len(re.findall(r"https?://", text, flags=re.I))
    if url_n > 10:
        warnings.append(f"{prefix}Many URLs ({url_n}); may not read well in audio.")

    if n > 450_000:
        warnings.append(f"{prefix}Very long section ({n} chars); verify extraction.")

    if re.search(r"\S{200,}", text):
        warnings.append(
            f"{prefix}Very long unbroken token(s); possible PDF extraction artifact."
        )

    return TtsTextValidation(ok=len(errors) == 0, errors=errors, warnings=warnings)


def clean_chapter_dict_for_tts(ch: dict, *, min_letters: int = 10) -> tuple[dict, TtsTextValidation]:
    """
    Return a shallow copy of chapter dict with cleaned ``text`` and validation result.
    """
    out = dict(ch)
    raw = ch.get("text") or ""
    cleaned = clean_for_tts(raw)
    out["text"] = cleaned
    title = ch.get("title", "")
    ctx = str(title)[:80] if title else f"chapter {ch.get('chapter_number', '')}"
    v = validate_for_tts(cleaned, min_letters=min_letters, context=ctx)
    return out, v
