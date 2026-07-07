"""
Model-assisted + heuristic classification of book sections for audiobook inclusion.

Uses Gemini (same stack as news: GEMINI_API_KEY / GOOGLE_API_KEY + google.generativeai)
when configured; otherwise title heuristics only.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from glconnect.book_utils import (
    audiobook_default_include,
    manuscript_section_kind,
    resolve_section_kind,
    section_kind_label,
)

logger = logging.getLogger(__name__)

# Match news / book_cover: routes2._get_google_api_key()
DEFAULT_GEMINI_MODEL = os.getenv("AUDIOBOOK_SECTION_GEMINI_MODEL", "gemini-2.0-flash")

BACK_MATTER_TITLE = re.compile(
    r"(?i)^\s*(index|appendix|appendices|endnotes?|notes on|works cited|"
    r"references?|bibliography|citations?|further reading|"
    r"acknowledgements?|acknowledgments?|about the author|copyright|"
    r"contents|table of contents)\b"
)


def _gemini_api_key() -> Optional[str]:
    return (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip() or None


def heuristic_section_include(
    title: str,
    preview: str,
    section_kind: str | None = None,
) -> Tuple[bool, str]:
    """Fast rule-based suggestion when Gemini is unavailable."""
    kind = section_kind or manuscript_section_kind(title)
    if kind == 'chapter':
        return True, "Content chapter, each included chapter becomes its own audio track"
    if kind == 'back':
        return False, "Back matter, usually skipped for audio (appendix, index, etc.)"
    if kind == 'front':
        return True, "Front matter, included by default; uncheck if you do not want it narrated"
    t = (title or "").strip()
    if BACK_MATTER_TITLE.search(t):
        return False, "Title matches common back-matter / reference pattern"
    if re.search(r"(?i)\b(index|appendix|endnotes?|bibliography)\b", t) and len(t) < 100:
        return False, "Short heading suggests reference / back matter"
    return audiobook_default_include(kind), "Non-chapter section, review whether it should be spoken"


def _parse_sections_json(content: str, expected_indices: List[int]) -> Optional[Dict[int, Dict[str, Any]]]:
    text = (content or "").strip()
    if not text:
        return None
    # Strip markdown fence if Gemini adds it
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    sections = data.get("sections")
    if not isinstance(sections, list):
        return None
    out: Dict[int, Dict[str, Any]] = {}
    for item in sections:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("index"))
        except (TypeError, ValueError):
            continue
        inc = item.get("include")
        if not isinstance(inc, bool):
            inc = str(inc).lower() in ("1", "true", "yes")
        reason = item.get("reason")
        if not isinstance(reason, str):
            reason = ""
        out[idx] = {"include": inc, "reason": reason.strip()[:300]}
    for i in expected_indices:
        if i not in out:
            return None
    return out


def _generation_config():
    """Align with news pipeline (routes2 / news_agent): Flash + moderate caps."""
    import google.generativeai as genai

    kwargs: Dict[str, Any] = {
        "max_output_tokens": 8192,
        "temperature": 0.2,
        "top_p": 0.8,
        "top_k": 40,
    }
    try:
        return genai.types.GenerationConfig(**kwargs, response_mime_type="application/json")
    except TypeError:
        return genai.types.GenerationConfig(**kwargs)


def classify_sections_gemini(
    segments: List[Dict[str, Any]],
    *,
    model: Optional[str] = None,
) -> Optional[Tuple[str, List[Dict[str, Any]]]]:
    """
    Call Gemini (batched) to label sections.

    segments: items with keys index, title, preview (short text).

    Returns ("gemini", list of {index, include, reason}) or None on failure.
    """
    key = _gemini_api_key()
    if not key:
        return None
    model_name = (model or DEFAULT_GEMINI_MODEL).strip()
    try:
        import google.generativeai as genai

        genai.configure(api_key=key)
    except Exception as exc:
        logger.warning("Gemini configure failed for audiobook sections: %s", exc)
        return None

    batch_size = 24
    all_results: List[Dict[str, Any]] = []
    gen_cfg = _generation_config()

    try:
        gemini_model = genai.GenerativeModel(model_name, generation_config=gen_cfg)
    except Exception as exc:
        logger.warning("Gemini GenerativeModel failed (%s): %s", model_name, exc)
        return None

    instruction = (
        "You label sections of a book for audiobook narration only. "
        "The print/ebook edition may keep index, footnotes, tables, and appendix; this task is only what should be spoken.\n"
        "Each section has section_kind: chapter (main narrative, defines audio start/stop tracks), "
        "front (foreword/preface), back (afterword/appendix/index), or other.\n"
        "For section_kind=chapter, strongly prefer include=true, these are the story boundaries.\n"
        "For section_kind=back, prefer include=false unless the preview is short and narrative.\n"
        "For section_kind=front, include=true is common but optional.\n"
        "Set include=false for index, appendix, endnotes, footnote collections, long data tables, "
        "bibliography, references, copyright pages, tables of contents, and long citation lists.\n"
        "When unsure on non-chapter sections, prefer include=false.\n"
        "Respond with ONLY valid JSON (no markdown): "
        '{"sections": [{"index": number, "include": boolean, "reason": string}]}\n'
    )

    for start in range(0, len(segments), batch_size):
        batch = segments[start : start + batch_size]
        payload_lines = []
        for s in batch:
            payload_lines.append(
                {
                    "index": s["index"],
                    "title": (s.get("title") or "")[:400],
                    "section_kind": s.get("section_kind") or manuscript_section_kind(s.get("title")),
                    "preview": (s.get("preview") or "")[:450],
                }
            )
        user = json.dumps({"sections": payload_lines}, ensure_ascii=False)
        full_prompt = instruction + "\nInput JSON:\n" + user

        try:
            response = gemini_model.generate_content(full_prompt)
        except Exception as exc:
            logger.warning("Gemini section classify generate_content failed: %s", exc)
            return None

        raw_text = ""
        try:
            raw_text = (response.text or "").strip()
        except Exception as exc:
            logger.warning("Gemini audiobook section response has no text: %s", exc)
            return None
        if not raw_text:
            logger.warning("Gemini audiobook section empty response")
            return None

        expected = [s["index"] for s in batch]
        parsed = _parse_sections_json(raw_text, expected)
        if not parsed:
            logger.warning("Could not parse Gemini section JSON (batch starting %s)", start)
            return None
        for idx in expected:
            all_results.append(
                {
                    "index": idx,
                    "include": parsed[idx]["include"],
                    "reason": parsed[idx]["reason"],
                }
            )

    all_results.sort(key=lambda x: x["index"])
    return ("gemini", all_results)


def suggest_includes_for_chapters(
    chapters_for_audio: List[Dict[str, Any]],
    *,
    preview_chars: int = 500,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Build segment list with AI suggestions, falling back to heuristics.

    Returns (classifier_name, list of dicts: index, title, preview, ai_include, ai_reason, include)
    """
    from glconnect.audiobook_text_clean import clean_for_tts

    segments_for_api: List[Dict[str, Any]] = []

    for i, ch in enumerate(chapters_for_audio):
        title = ch.get("title") or f"Part {i + 1}"
        kind = ch.get("section_kind") or resolve_section_kind(title)
        body = clean_for_tts(ch.get("text") or "")
        preview = body[:preview_chars] if body else ""
        segments_for_api.append({
            "index": i,
            "title": title,
            "section_kind": kind,
            "preview": preview,
        })

    ai_out = classify_sections_gemini(segments_for_api)
    ai_by_index: Dict[int, Tuple[bool, str]] = {}
    classifier = "heuristic"

    if ai_out:
        classifier, rows = ai_out
        for row in rows:
            ai_by_index[row["index"]] = (row["include"], row.get("reason") or "")

    built: List[Dict[str, Any]] = []
    for i, ch in enumerate(chapters_for_audio):
        title = ch.get("title") or f"Part {i + 1}"
        kind = ch.get("section_kind") or resolve_section_kind(title)
        body = clean_for_tts(ch.get("text") or "")
        preview = body[:preview_chars] if body else ""
        if i in ai_by_index:
            ai_inc, ai_reas = ai_by_index[i]
        else:
            ai_inc, ai_reas = heuristic_section_include(title, preview, kind)
        built.append(
            {
                "index": i,
                "title": title[:300],
                "preview": preview,
                "section_kind": kind,
                "kind_label": section_kind_label(kind),
                "is_narrative_chapter": kind == 'chapter',
                "narrative_chapter_index": ch.get("narrative_chapter_index"),
                "reading_order": ch.get("reading_order", ch.get("chapter_number")),
                "ai_include": ai_inc,
                "ai_reason": ai_reas,
                "include": False,
                "is_section_complete": ch.get("is_section_complete"),
            }
        )

    return classifier, built
