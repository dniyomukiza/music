#!/usr/bin/env python3
"""
Probe Gemini / Imagen model IDs used for book covers.

By default: calls the API models.get() for each ID (lightweight; checks the key
and that the model exists for your project).

With --generate: runs one real cover generation (uses quota).

Usage (from repo root):
  python3 scripts/test_gemini_cover_models.py
  python3 scripts/test_gemini_cover_models.py --generate
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser(description="Test book-cover AI model IDs")
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Run one full generate_book_cover_bytes() (consumes quota)",
    )
    args = parser.parse_args()

    from google.genai import errors as genai_errors

    # Load book_cover_ai without importing glconnect package (avoids Flask app init / debug noise).
    import importlib.util

    _bc_path = ROOT / "glconnect" / "book_cover_ai.py"
    _spec = importlib.util.spec_from_file_location("book_cover_ai", _bc_path)
    if _spec is None or _spec.loader is None:
        raise RuntimeError(f"Cannot load {_bc_path}")
    _bc = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_bc)
    iter_book_cover_image_models = _bc.iter_book_cover_image_models
    iter_imagen_cover_models = _bc.iter_imagen_cover_models
    make_cover_genai_client = _bc.make_cover_genai_client

    api_key = _bc.cover_image_api_key()
    if not api_key:
        print(
            "ERROR: Set GEMINI_API_KEY or GOOGLE_API_KEY (e.g. in .env at repo root).",
            file=sys.stderr,
        )
        sys.exit(1)

    client = make_cover_genai_client(api_key)

    print("models.get() — checks project can see each model (no image generation):\n")

    for name in iter_book_cover_image_models():
        try:
            m = client.models.get(model=name)
            disp = getattr(m, "display_name", None) or ""
            extra = f" ({disp})" if disp else ""
            print(f"  OK generateContent   {name}{extra}")
        except genai_errors.ClientError as e:
            print(f"  FAIL  generateContent   {name}\n        {str(e)[:300]}")
        except Exception as e:
            print(f"  FAIL  generateContent   {name}\n        {type(e).__name__}: {e!s}"[:400])

    print()
    for name in iter_imagen_cover_models():
        try:
            m = client.models.get(model=name)
            disp = getattr(m, "display_name", None) or ""
            extra = f" ({disp})" if disp else ""
            print(f"  OK    generate_images   {name}{extra}")
        except genai_errors.ClientError as e:
            print(f"  FAIL  generate_images   {name}\n        {str(e)[:300]}")
        except Exception as e:
            print(f"  FAIL  generate_images   {name}\n        {type(e).__name__}: {e!s}"[:400])

    if args.generate:
        print("\n--generate: full cover pipeline (Gemini image + Imagen fallbacks as configured)…\n")
        out = _bc.generate_book_cover_bytes(
            "Diagnostic Cover",
            "A minimal test book for API checks.",
            "fiction",
            "simple bold typography",
        )
        if out.get("success"):
            n = len(out.get("image_bytes") or b"")
            print(f"  OK    generate_book_cover_bytes — {n} bytes")
        else:
            print(f"  FAIL  {out.get('error')}")


if __name__ == "__main__":
    main()
