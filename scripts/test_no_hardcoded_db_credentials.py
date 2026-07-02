#!/usr/bin/env python3
"""Regression check for committed PostgreSQL credentials."""

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
PLACEHOLDERS = (
    "postgresql://user:password@",
    "postgresql://user:pass@",
    "postgresql://...'",
    'postgresql://..."',
)
CREDENTIAL_URL = re.compile(r"postgresql://[^\s\"'`]+:[^\s\"'`]+@[^\s\"'`]+")


def main():
    failures = []

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for match in CREDENTIAL_URL.finditer(content):
            value = match.group(0)
            if any(value.startswith(placeholder) for placeholder in PLACEHOLDERS):
                continue
            failures.append(f"{path.relative_to(ROOT)} contains a credentialed PostgreSQL URL")

    if failures:
        print("FAILURES:")
        for failure in failures:
            print(" -", failure)
        sys.exit(1)

    print("OK: no hardcoded PostgreSQL credentials found")


if __name__ == "__main__":
    main()
