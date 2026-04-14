#!/usr/bin/env python3
"""
Delete ALL Ink Studio book projects and related DB rows (investments, sales, earnings, …).

Does NOT remove users, writers, or book_platform_users.

Requires BOTH:
  CONFIRM_CLEAR_ALL_BOOKS=YES
  ALLOW_DESTRUCTIVE_BOOK_PURGE=YES

Usage (from repo root):
  CONFIRM_CLEAR_ALL_BOOKS=YES ALLOW_DESTRUCTIVE_BOOK_PURGE=YES python scripts/clear_all_books.py
"""

import json
import os
import sys

# Repo root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    if os.getenv("CONFIRM_CLEAR_ALL_BOOKS") != "YES":
        print(
            "Refusing to run: set CONFIRM_CLEAR_ALL_BOOKS=YES",
            file=sys.stderr,
        )
        return 2
    if os.getenv("ALLOW_DESTRUCTIVE_BOOK_PURGE") != "YES":
        print(
            "Refusing to run: set ALLOW_DESTRUCTIVE_BOOK_PURGE=YES",
            file=sys.stderr,
        )
        return 2

    from glconnect import create_app, db
    from glconnect.book_platform_purge import purge_all_book_projects

    app, _ = create_app()
    with app.app_context():
        try:
            summary = purge_all_book_projects(db)
        except Exception:
            db.session.rollback()
            raise
        print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
