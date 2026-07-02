"""
Optional AI generated ebook covers for authors without a design file.
Credentials are read from the server environment (not exposed to end users).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_DEBUG_COVER_LOG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".cursor",
    "debug-fe2ff6.log",
)


def _debug_cover_log(hypothesis_id: str, location: str, message: str, data: Optional[dict] = None) -> None:
    # #region agent log
    if os.getenv("DEBUG_AGENT_LOG", "").strip().lower() not in ("1", "true", "yes", "on"):
        return
    try:
        import json as _json
        from datetime import datetime, timezone as _tz

        with open(_DEBUG_COVER_LOG, "a", encoding="utf-8") as fh:
            fh.write(
                _json.dumps(
                    {
                        "sessionId": "fe2ff6",
                        "runId": "cover-gen",
                        "hypothesisId": hypothesis_id,
                        "location": location,
                        "message": message,
                        "data": data or {},
                        "timestamp": int(datetime.now(_tz.utc).timestamp() * 1000),
                    },
                    default=str,
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion


def cover_image_api_key() -> str:
    """
    API key for Gemini / Imagen image calls.

    Prefers GEMINI_API_KEY when set, then GOOGLE_API_KEY, so you can keep a general
    GOOGLE_API_KEY for other services while using a separate Gemini Studio key with
    image quota for covers.
    """
    return (
        (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    )


def cover_genai_http_timeout_ms() -> int:
    """
    HTTP timeout for Gemini / Imagen image calls (milliseconds), same idea as JS
    GoogleGenAI httpOptions.timeout. Override with BOOK_COVER_GENAI_TIMEOUT_MS.
    """
    raw = (os.getenv("BOOK_COVER_GENAI_TIMEOUT_MS") or "").strip()
    default_ms = 300_000  # 5 minutes, image generation is often slow
    if not raw:
        return default_ms
    try:
        n = int(raw)
    except ValueError:
        return default_ms
    return max(10_000, min(n, 900_000))  # clamp 10s … 15m


def make_cover_genai_client(api_key: str):
    """google.genai Client with extended timeout for cover / Imagen requests."""
    from google import genai
    from google.genai import types as genai_types

    return genai.Client(
        api_key=api_key,
        http_options=genai_types.HttpOptions(timeout=cover_genai_http_timeout_ms()),
    )


# Native image via generateContent (generativelanguage.googleapis.com v1beta).
_GEMINI_COVER_IMAGE_MODELS = ("gemini-2.5-flash-image",)
_ENV_IMAGEN_MODEL = "BOOK_COVER_IMAGEN_MODEL"
_DEFAULT_IMAGEN_MODELS = ("imagen-4.0-fast-generate-001",)


def iter_imagen_cover_models():
    """Imagen uses generate_images(), often a different quota than Gemini Flash Image."""
    env = (os.getenv(_ENV_IMAGEN_MODEL) or "").strip()
    if env:
        yield env
    for name in _DEFAULT_IMAGEN_MODELS:
        if env and name == env:
            continue
        yield name


def _prompt_for_imagen(full_prompt: str) -> str:
    t = (full_prompt or "").strip()
    if len(t) > 1800:
        return t[:1800] + " …"
    return t


def _try_imagen_book_cover(client: Any, prompt: str) -> Optional[bytes]:
    from google.genai import types

    short = _prompt_for_imagen(prompt)
    for imagen_id in iter_imagen_cover_models():
        try:
            resp = client.models.generate_images(
                model=imagen_id,
                prompt=short,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="3:4",
                    output_mime_type="image/png",
                ),
            )
            if not resp.generated_images:
                continue
            first = resp.generated_images[0]
            if getattr(first, "rai_filtered_reason", None):
                logger.warning(
                    "book cover: imagen %s RAI filtered: %s",
                    imagen_id,
                    first.rai_filtered_reason,
                )
                continue
            img = first.image
            if not img or not img.image_bytes:
                continue
            raw = img.image_bytes
            logger.info("book cover: used Imagen model %s", imagen_id)
            return raw if isinstance(raw, bytes) else bytes(raw)
        except Exception as e:
            logger.warning(
                "book cover: imagen %s failed: %s",
                imagen_id,
                str(e)[:220],
            )
            continue
    return None


def iter_book_cover_image_models():
    """Gemini image models for covers in preferred order."""
    for name in _GEMINI_COVER_IMAGE_MODELS:
        yield name


def _error_http_code(err: Exception) -> Optional[int]:
    code = getattr(err, "status_code", None)
    if isinstance(code, int):
        return code
    if isinstance(code, str) and code.isdigit():
        return int(code)
    return None


def _should_try_next_image_model(err: Exception) -> bool:
    """Try another model ID when this failure might be model-specific."""
    code = _error_http_code(err)
    if code == 401:
        return False
    if code in (400, 403, 404, 429, 408, 500, 502, 503, 504):
        return True
    msg_u = str(err).upper()
    for token in (
        "400",
        "403",
        "404",
        "NOT_FOUND",
        "429",
        "RESOURCE_EXHAUSTED",
        "UNAVAILABLE",
        "DEADLINE_EXCEEDED",
        "INTERNAL",
        "OVERLOADED",
        "503",
        "500",
        "TIMEOUT",
        "INVALID_ARGUMENT",
    ):
        if token in msg_u:
            return True
    return False


def _all_models_failed_message(last_err: Optional[Exception]) -> str:
    if not last_err:
        return (
            "No image model responded. Try again later or upload your own cover image."
        )
    msg = str(last_err)
    msg_u = msg.upper()
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg_u:
        return (
            "Google AI rate or quota limit was reached for cover generation (all tried models). "
            "Wait a minute and retry, review limits and billing for your API project "
            "(https://ai.google.dev/gemini-api/docs/rate-limits), or upload your own cover. "
            "If Imagen fallback also fails, enable billing or wait for quota reset, or upload your own cover."
        )
    code = _error_http_code(last_err)
    if code == 403 or "PERMISSION_DENIED" in msg_u or "FORBIDDEN" in msg_u:
        return (
            "Google AI refused access for image generation (permission). "
            "Confirm the API key’s project has the Generative Language API enabled and billing "
            "if required, or upload your own cover."
        )
    if code == 401 or "UNAUTHENTICATED" in msg_u or "API_KEY_INVALID" in msg_u:
        return (
            "The Google API key is missing or invalid for AI cover generation. "
            "Set GEMINI_API_KEY or GOOGLE_API_KEY in the server environment, or upload your own cover."
        )
    if "404" in msg or "NOT_FOUND" in msg_u:
        return (
            "Gemini image generation is not available for this API key (model not enabled or renamed). "
            "Check Google AI model access for your project, or upload your own cover."
        )
    if code == 400 or "INVALID_ARGUMENT" in msg_u or "FAILED_PRECONDITION" in msg_u:
        return (
            "Google AI rejected the cover request (invalid argument or model mismatch). "
            "Try again with a shorter description or upload your own cover."
        )
    if "SAFETY" in msg_u or "BLOCKED" in msg_u:
        return (
            "The cover request was blocked by content safety rules. "
            "Simplify the title or art direction and try again, or upload your own cover."
        )
    return (
        "We could not generate a cover with the AI service after trying every configured model. "
        "Check the server log for details, try again in a few minutes, or upload your own cover image."
    )


def generate_book_cover_bytes(
    title: str,
    description: str = "",
    genre: str = "",
    art_brief: str = "",
    author_name: str = "",
) -> Dict[str, Any]:
    """
    Return {success, image_bytes, error}, image_bytes is raw PNG/JPEG from the model when success.
    Title and author_name are rendered as legible cover typography (not just mood cues).
    """
    api_key = cover_image_api_key()
    if not api_key:
        return {
            "success": False,
            "error": "AI cover isn’t configured (set GEMINI_API_KEY or GOOGLE_API_KEY) or upload your own cover image.",
            "image_bytes": None,
        }

    title = (title or "").strip()[:200]
    author = (author_name or "").strip()[:120] or "Author"
    desc = (description or "").strip()[:1200]
    genre = (genre or "").strip()[:120]
    brief = (art_brief or "").strip()[:800]

    import time as _time
    _cover_t0 = _time.monotonic()
    _debug_cover_log(
        "H1,H3,H5",
        "book_cover_ai.py:generate_book_cover_bytes:start",
        "cover generation started",
        {
            "has_art_brief": bool(brief),
            "title_len": len(title),
            "desc_len": len(desc),
            "timeout_ms": cover_genai_http_timeout_ms(),
        },
    )

    prompt = f"""Design a professional ebook cover for online bookstore listings.

Exact text that MUST appear on the cover (spell exactly as shown):
- Book title: "{title}"
- Author name: "{author}"

Genre: {genre or "general"}
Summary for visual inspiration: {desc or "Not provided."}
Author art direction (optional): {brief or "None provided, the model will choose genre-appropriate style and imagery on its own. Title and author name on the cover are still mandatory."}

Requirements:
- Vertical book-cover composition, aspect ratio approximately 2:3 (portrait), suitable for thumbnail and full display.
- Render the book TITLE prominently in the upper half: large, legible, professionally typeset typography integrated with the artwork.
- Render the AUTHOR NAME clearly below the title (smaller than the title but still easily readable at thumbnail size).
- Both title and author text must be spelled exactly as given above, do not substitute, abbreviate, or omit either.
- Striking, commercially appropriate, genre-appropriate background artwork; high quality; no cluttered collage.
- No watermarks, no QR codes, no publisher logos, no price tags.
- Original illustrative style; avoid copying specific existing book covers or trademarked characters.
"""

    try:
        from google.genai import errors as genai_errors

        client = make_cover_genai_client(api_key)
        response = None
        last_model_error: Optional[Exception] = None
        _gemini_t0 = _time.monotonic()
        for model_name in iter_book_cover_image_models():
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[prompt],
                )
                logger.info("book cover: used image model %s", model_name)
                _debug_cover_log(
                    "H1,H2",
                    "book_cover_ai.py:generate_book_cover_bytes:gemini_ok",
                    "gemini model succeeded",
                    {
                        "model": model_name,
                        "elapsed_ms": int((_time.monotonic() - _gemini_t0) * 1000),
                    },
                )
                break
            except genai_errors.ClientError as e:
                last_model_error = e
                if _should_try_next_image_model(e):
                    logger.warning(
                        "book cover: model %s failed (%s), trying fallback",
                        model_name,
                        str(e)[:200],
                    )
                    continue
                raise
            except Exception as e:
                last_model_error = e
                if _should_try_next_image_model(e):
                    logger.warning(
                        "book cover: model %s failed (%s), trying fallback",
                        model_name,
                        str(e)[:200],
                    )
                    continue
                raise
        if response is None:
            _imagen_t0 = _time.monotonic()
            image_bytes_fb = _try_imagen_book_cover(client, prompt)
            _debug_cover_log(
                "H2",
                "book_cover_ai.py:generate_book_cover_bytes:imagen_fallback",
                "imagen fallback after gemini failure",
                {
                    "success": bool(image_bytes_fb),
                    "elapsed_ms": int((_time.monotonic() - _imagen_t0) * 1000),
                    "last_gemini_ms": int((_time.monotonic() - _gemini_t0) * 1000),
                },
            )
            if image_bytes_fb:
                _debug_cover_log(
                    "H1",
                    "book_cover_ai.py:generate_book_cover_bytes:done",
                    "cover generation finished",
                    {"path": "imagen", "total_ms": int((_time.monotonic() - _cover_t0) * 1000)},
                )
                return {"success": True, "image_bytes": image_bytes_fb, "error": None}
            logger.error(
                "book cover: all Gemini image models failed; last error: %r",
                last_model_error,
            )
            return {
                "success": False,
                "error": _all_models_failed_message(last_model_error),
                "image_bytes": None,
            }

        if not response.candidates:
            _imagen_t0 = _time.monotonic()
            image_bytes_fb = _try_imagen_book_cover(client, prompt)
            _debug_cover_log(
                "H2",
                "book_cover_ai.py:generate_book_cover_bytes:imagen_no_candidates",
                "imagen fallback, no gemini candidates",
                {
                    "success": bool(image_bytes_fb),
                    "elapsed_ms": int((_time.monotonic() - _imagen_t0) * 1000),
                },
            )
            if image_bytes_fb:
                _debug_cover_log(
                    "H1",
                    "book_cover_ai.py:generate_book_cover_bytes:done",
                    "cover generation finished",
                    {"path": "imagen_no_candidates", "total_ms": int((_time.monotonic() - _cover_t0) * 1000)},
                )
                return {"success": True, "image_bytes": image_bytes_fb, "error": None}
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
            _imagen_t0 = _time.monotonic()
            image_bytes_fb = _try_imagen_book_cover(client, prompt)
            _debug_cover_log(
                "H2",
                "book_cover_ai.py:generate_book_cover_bytes:imagen_no_inline",
                "imagen fallback, no inline image bytes",
                {
                    "success": bool(image_bytes_fb),
                    "elapsed_ms": int((_time.monotonic() - _imagen_t0) * 1000),
                },
            )
            if image_bytes_fb:
                _debug_cover_log(
                    "H1",
                    "book_cover_ai.py:generate_book_cover_bytes:done",
                    "cover generation finished",
                    {"path": "imagen_no_inline", "total_ms": int((_time.monotonic() - _cover_t0) * 1000)},
                )
                return {"success": True, "image_bytes": image_bytes_fb, "error": None}
            return {
                "success": False,
                "error": "We couldn’t produce a cover image. Try again or upload your own image.",
                "image_bytes": None,
            }
        _debug_cover_log(
            "H1",
            "book_cover_ai.py:generate_book_cover_bytes:done",
            "cover generation finished",
            {"path": "gemini", "total_ms": int((_time.monotonic() - _cover_t0) * 1000)},
        )
        return {"success": True, "image_bytes": image_bytes, "error": None}
    except Exception as e:
        logger.exception("book cover AI generation failed: %s", e)
        try:
            from google.genai import errors as genai_errors

            if isinstance(e, genai_errors.ClientError):
                err_out = _all_models_failed_message(e)
            else:
                err_out = (
                    "Something went wrong while generating the cover. Try again or upload your own image."
                )
        except Exception:
            err_out = (
                "Something went wrong while generating the cover. Try again or upload your own image."
            )
        return {
            "success": False,
            "error": err_out,
            "image_bytes": None,
        }
