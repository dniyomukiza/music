#!/usr/bin/env python3
"""Regression check for campaign pitch video iframe URL normalization."""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    routes = (ROOT / "glconnect" / "book_platform_routes.py").read_text(encoding="utf-8")
    media = (ROOT / "glconnect" / "project_description_media.py").read_text(encoding="utf-8")
    failures = []

    if "pitch_video_url=normalize_video_embed_url(form.pitch_video_url.data)" not in routes:
        failures.append("campaign creation should store only normalized pitch video embed URLs")
    if "campaign.pitch_video_url = normalize_video_embed_url(pitch_url) if pitch_url else None" not in routes:
        failures.append("campaign editing should store only normalized pitch video embed URLs")
    if "campaign.pitch_video_url = embed or pitch_url" in routes:
        failures.append("campaign editing should not fall back to raw pitch video URLs")
    if "def _is_safe_youtube_video_id" not in media:
        failures.append("shared video normalizer should validate YouTube video IDs")
    if 're.fullmatch(r"[A-Za-z0-9_-]{6,32}", video_id)' not in media:
        failures.append("YouTube video IDs should be limited to safe characters")
    if "safe_embed_url = escape(embed_url, quote=True)" not in media:
        failures.append("iframe src should escape normalized embed URLs")

    if failures:
        print("FAILURES:")
        for failure in failures:
            print(" -", failure)
        sys.exit(1)

    print("OK: campaign pitch video URLs are normalized before iframe rendering")


if __name__ == "__main__":
    main()
