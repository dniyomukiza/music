#!/usr/bin/env python3
"""Regression check that agent debug file logging is opt-in only."""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PY_FILES = [
    "glconnect/book_platform_routes.py",
    "glconnect/stripe_utils.py",
    "glconnect/ink_studio_v1.py",
    "glconnect/author_display.py",
    "glconnect/book_cover_ai.py",
]


def main():
    failures = []

    for relative in PY_FILES:
        content = (ROOT / relative).read_text(encoding="utf-8")
        if "debug-fe2ff6.log" in content and "DEBUG_AGENT_LOG" not in content:
            failures.append(f"{relative} writes debug-fe2ff6.log without DEBUG_AGENT_LOG gate")

    author_display = (ROOT / "glconnect" / "author_display.py").read_text(encoding="utf-8")
    if "/Applications/untitled folder" in author_display:
        failures.append("author_display.py should not contain a hardcoded local debug path")

    if failures:
        print("FAILURES:")
        for failure in failures:
            print(" -", failure)
        sys.exit(1)

    print("OK: agent debug file logging is gated behind DEBUG_AGENT_LOG")


if __name__ == "__main__":
    main()
