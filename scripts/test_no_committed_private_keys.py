#!/usr/bin/env python3
"""Regression check for committed private key material."""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache"}
SKIP_SUFFIXES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".mp3",
    ".mp4",
    ".pdf",
    ".pyc",
}
PRIVATE_KEY_MARKERS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r'"pem"\s*:\s*"-----BEGIN [A-Z ]*PRIVATE KEY-----'),
)


def main():
    failures = []

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        if path.name == "private_key.json" or any(marker.search(content) for marker in PRIVATE_KEY_MARKERS):
            failures.append(f"{relative} contains private key material")

    if failures:
        print("FAILURES:")
        for failure in failures:
            print(" -", failure)
        sys.exit(1)

    print("OK: no committed private key material found")


if __name__ == "__main__":
    main()
