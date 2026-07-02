#!/usr/bin/env python3
"""Regression check for campaign pitch video iframe URL normalization."""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    routes = (ROOT / "glconnect" / "book_platform_routes.py").read_text(encoding="utf-8")
    failures = []

    if "pitch_video_url=normalize_video_embed_url(form.pitch_video_url.data)" not in routes:
        failures.append("campaign creation should store only normalized pitch video embed URLs")
    if "campaign.pitch_video_url = normalize_video_embed_url(pitch_url) if pitch_url else None" not in routes:
        failures.append("campaign editing should store only normalized pitch video embed URLs")
    if "campaign.pitch_video_url = embed or pitch_url" in routes:
        failures.append("campaign editing should not fall back to raw pitch video URLs")

    if failures:
        print("FAILURES:")
        for failure in failures:
            print(" -", failure)
        sys.exit(1)

    print("OK: campaign pitch video URLs are normalized before iframe rendering")


if __name__ == "__main__":
    main()
