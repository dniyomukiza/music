"""
AI translation of plain book text into additional ebook editions (UTF-8 .txt files).
Uses the same Gemini configuration as blog translation.
"""

import logging
import os

logger = logging.getLogger(__name__)

# Keep in sync with blog.LANGUAGE_NAMES for prompt quality
LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi",
    "nl": "Dutch",
    "pl": "Polish",
    "sv": "Swedish",
    "da": "Danish",
    "fi": "Finnish",
    "tr": "Turkish",
}

_CHUNK_CHARS = 12000


def _get_gemini_model():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        return genai.GenerativeModel("gemini-2.0-flash")
    except Exception as e:
        logger.warning("ebook_translation: could not init Gemini: %s", e)
        return None


def _split_for_translation(text: str) -> list:
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= _CHUNK_CHARS:
        return [text]
    parts = []
    start = 0
    while start < len(text):
        end = min(start + _CHUNK_CHARS, len(text))
        if end < len(text):
            break_at = text.rfind("\n\n", start, end)
            if break_at <= start:
                break_at = text.rfind("\n", start, end)
            if break_at <= start:
                break_at = end
            end = break_at
        parts.append(text[start:end].strip())
        start = end
    return [p for p in parts if p]


def translate_plain_text(text: str, source_code: str, target_code: str) -> str:
    """
    Translate full plain text (may be long). Returns UTF-8 string.
    Raises on missing API key or model errors.
    """
    model = _get_gemini_model()
    if not model:
        raise RuntimeError("Translation is not configured (set GOOGLE_API_KEY or GEMINI_API_KEY).")

    src = LANGUAGE_NAMES.get((source_code or "en").lower(), source_code or "English")
    tgt = LANGUAGE_NAMES.get((target_code or "").lower(), target_code or "")
    if not tgt:
        raise ValueError("Invalid target language")

    chunks = _split_for_translation(text)
    if not chunks:
        raise ValueError("No text to translate")

    import google.generativeai as genai

    out_parts = []
    for i, chunk in enumerate(chunks):
        prompt = f"""Translate the following book excerpt from {src} to {tgt}.
Preserve paragraph breaks. Output ONLY the translated text — no title, no quotes, no markdown fences, no commentary.

---BEGIN---
{chunk}
---END---"""

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=8192,
                temperature=0.25,
                top_p=0.85,
                top_k=40,
            ),
        )
        if not response.parts:
            raise RuntimeError(f"Empty translation response for chunk {i + 1}/{len(chunks)}")
        piece = (response.text or "").strip()
        if not piece:
            raise RuntimeError(f"Empty translation text for chunk {i + 1}/{len(chunks)}")
        out_parts.append(piece)

    return "\n\n".join(out_parts)
