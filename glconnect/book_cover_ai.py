"""
Optional AI-generated ebook covers (Gemini image), for authors listing without a design file.
Uses GOOGLE_API_KEY — same credential family as other Gemini features in this project.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)


def generate_book_cover_bytes(
    title: str,
    description: str = "",
    genre: str = "",
    art_brief: str = "",
) -> Dict[str, Any]:
    """
    Return {success, image_bytes, error} — image_bytes is raw PNG/JPEG from the model when success.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {"success": False, "error": "GOOGLE_API_KEY is not configured.", "image_bytes": None}

    title = (title or "").strip()[:200]
    desc = (description or "").strip()[:1200]
    genre = (genre or "").strip()[:120]
    brief = (art_brief or "").strip()[:800]

    prompt = f"""Design a professional ebook cover illustration for online bookstore listings.

Book title (for mood and theme only—do not dominate the design with huge title text): "{title}"
Genre: {genre or "general"}
Summary for visual inspiration: {desc or "Not provided."}
Author art direction (optional): {brief or "None—use genre-appropriate professional design."}

Requirements:
- Vertical book-cover composition, aspect ratio approximately 2:3 (portrait), suitable for thumbnail and full display.
- Striking, commercially appropriate, genre-appropriate artwork; high quality; no cluttered collage.
- If you include the book title as text, make it clearly readable and well integrated; otherwise focus on strong imagery alone.
- No watermarks, no QR codes, no publisher logos, no price tags.
- Original illustrative style; avoid copying specific existing book covers or trademarked characters.
"""

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash-image-preview",
            contents=[prompt],
        )
        if not response.candidates:
            return {"success": False, "error": "Cover request was blocked or empty.", "image_bytes": None}
        image_bytes = None
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image_bytes = part.inline_data.data
                break
        if not image_bytes:
            return {"success": False, "error": "No image returned from the model.", "image_bytes": None}
        return {"success": True, "image_bytes": image_bytes, "error": None}
    except Exception as e:
        logger.exception("book cover AI generation failed: %s", e)
        return {"success": False, "error": str(e), "image_bytes": None}
