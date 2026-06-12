#!/usr/bin/env python3
"""
Remove all data for manual test account(s) — default username: testuser.

Deletes every book authored by the user, purchases, library rows, posts,
playlists, Ink Studio profiles, and the users row itself.

Preview (no deletes):
  python scripts/cleanup_test_data.py

Preview for one user:
  python scripts/cleanup_test_data.py --username testuser

Execute cleanup for testuser (default):
  CONFIRM_CLEANUP_TEST_DATA=YES python scripts/cleanup_test_data.py --execute

Execute for a specific username:
  CONFIRM_CLEANUP_TEST_DATA=YES python scripts/cleanup_test_data.py --execute --username testuser

Env (optional):
  TEST_DATA_USERNAMES=testuser,testuser2
  TEST_DATA_EXTRA_USER_IDS=123
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Remove all DB data for test account(s); default username is testuser.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete (requires CONFIRM_CLEANUP_TEST_DATA=YES).",
    )
    parser.add_argument(
        "--username",
        metavar="NAME",
        help="Single username to clean (overrides TEST_DATA_USERNAMES for this run).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print summary as JSON only.",
    )
    args = parser.parse_args()

    dry_run = not args.execute
    if args.execute and os.getenv("CONFIRM_CLEANUP_TEST_DATA") != "YES":
        print(
            "Refusing to delete: set CONFIRM_CLEANUP_TEST_DATA=YES\n"
            "Tip: run without --execute first to preview matches.",
            file=sys.stderr,
        )
        return 2

    from glconnect import create_app, db
    from glconnect.test_data_cleanup import cleanup_test_data, cleanup_user_by_username

    app, _ = create_app()
    with app.app_context():
        try:
            if args.username:
                summary = cleanup_user_by_username(db, args.username, dry_run=dry_run)
            else:
                summary = cleanup_test_data(db, dry_run=dry_run)
        except Exception:
            return 1

    print(json.dumps(summary, indent=2, default=str))
    if not args.json:
        if dry_run:
            user_label = args.username or os.getenv("TEST_DATA_USERNAMES", "testuser")
            print(
                f"\nDry run complete for account(s) matching: {user_label}\n"
                "To delete everything for those users:\n"
                "  CONFIRM_CLEANUP_TEST_DATA=YES python scripts/cleanup_test_data.py --execute"
            )
        elif summary.get("success"):
            print("\nCleanup finished successfully.")
        else:
            print("\nCleanup finished with issues — see summary above.")

    return 0 if summary.get("success", dry_run) else 1


if __name__ == "__main__":
    raise SystemExit(main())
