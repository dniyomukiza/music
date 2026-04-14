"""
Optional AI-generated ebook covers for authors without a design file.
Credentials are read from the server environment (not exposed to end users).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Image-capable Gemini models (text+image / native image). Preview IDs change; override with BOOK_COVER_AI_MODEL.
_ENV_COVER_MODEL = "BOOK_COVER_AI_MODEL"
_DEFAULT_COVER_IMAGE_MODELS = (
    "gemini-2.0-flash-preview-image-generation",
    "gemini-2.5-flash-image",
    "gemini-2.0-flash-exp-image-generation",
)


def iter_book_cover_image_models():
    """Model names to try for cover (and similar) image generation, newest stable first."""
    env = (os.getenv(_ENV_COVER_MODEL) or "").strip()
    if env:
        yield env
        return
    for name in _DEFAULT_COVER_IMAGE_MODELS:
        yield name


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
        return {
            "success": False,
            "error": "AI cover isn’t available on this site right now. Please upload your own cover image.",
            "image_bytes": None,
        }

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
        from google.genai import errors as genai_errors

        client = genai.Client(api_key=api_key)
        response = None
        last_model_error = None
        for model_name in iter_book_cover_image_models():
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[prompt],
                )
                logger.info("book cover: used image model %s", model_name)
                break
            except genai_errors.ClientError as e:
                last_model_error = e
                msg = str(e)
                if "404" in msg or "NOT_FOUND" in msg:
                    logger.warning(
                        "book cover: model %s not available (%s), trying fallback",
                        model_name,
                        msg[:120],
                    )
                    continue
                raise
            except Exception as e:
                msg = str(e)
                if "404" in msg or "NOT_FOUND" in msg:
                    last_model_error = e
                    logger.warning(
                        "book cover: model %s not available (%s), trying fallback",
                        model_name,
                        msg[:120],
                    )
                    continue
                raise
        if response is None:
            raise last_model_error or RuntimeError("No image model responded")

        if not response.candidates:
            return {
                "success": False,
                "error": "We couldn’t create a cover from that information. Try again or upload your own image.",
                "image_bytes": None,
            }
        image_bytes = None
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image_bytes = part.inline_data.data
                break
        if not image_bytes:
            return {
                "success": False,
                "error": "We couldn’t produce a cover image. Try again or upload your own image.",
                "image_bytes": None,
            }
        return {"success": True, "image_bytes": image_bytes, "error": None}
    except Exception as e:
        logger.exception("book cover AI generation failed: %s", e)
        return {
            "success": False,
            "error": "Something went wrong while generating the cover. Try again or upload your own image.",
            "image_bytes": None,
        }
