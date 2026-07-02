#!/usr/bin/env python3
"""Regression check for campaign translation abuse controls."""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    content = (ROOT / "glconnect" / "book_platform_routes.py").read_text(encoding="utf-8")
    route_index = content.find("@book_bp.route('/campaigns/<int:campaign_id>/translate', methods=['POST'])")
    func_index = content.find("def translate_campaign_page", route_index)
    block = content[route_index:func_index]

    failures = []
    if "from glconnect.book_platform_security import rate_limit" not in content:
        failures.append("book_platform_routes should import the existing rate_limit helper")
    if "@login_required" not in block:
        failures.append("translation route should remain login-required")
    if "@rate_limit(max_requests=20, window_minutes=60)" not in block:
        failures.append("translation route should rate-limit costly AI requests")

    if failures:
        print("FAILURES:")
        for failure in failures:
            print(" -", failure)
        sys.exit(1)

    print("OK: campaign translation route is login-protected and rate-limited")


if __name__ == "__main__":
    main()
