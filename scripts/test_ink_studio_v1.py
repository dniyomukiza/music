#!/usr/bin/env python3
"""Smoke tests for Ink Studio M1 (marketplace entry, campaigns + sales)."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def main():
    os.environ["INK_STUDIO_V1_BOOKS_LAUNCH"] = "1"
    from glconnect import create_app

    result = create_app()
    app = result[0] if isinstance(result, tuple) else result
    app.config["INK_STUDIO_V1_BOOKS_LAUNCH"] = True

    from glconnect.ink_studio_v1 import (
        ink_account_capabilities,
        ink_is_author_account,
        ink_show_author_workspace,
        ink_show_media_ecosystem,
        ink_v1_books_launch,
    )

    assert ink_v1_books_launch(app) is True
    assert ink_show_media_ecosystem(app) is False

    caps = ink_account_capabilities()
    assert caps["authenticated"] is False
    assert caps["can_fund_campaigns"] is False
    assert caps["can_manage_author_workspace"] is False

    failures = []
    with app.test_client() as c:
        redirects = [
            ("/mybook/investments", 301, "/mybook/campaigns"),
            ("/mybook/investments/1", 301, "/mybook/campaigns/1"),
            ("/mybook/investments/2/invest", 301, "/mybook/campaigns/2/contribute"),
        ]
        for path, code, target in redirects:
            r = c.get(path, follow_redirects=False)
            loc = r.headers.get("Location", "")
            if r.status_code != code or target not in loc:
                failures.append(f"{path}: expected {code}→{target}, got {r.status_code}→{loc}")

        r = c.get("/mybook/marketplace", follow_redirects=False)
        if r.status_code != 302:
            failures.append(f"marketplace unauthenticated: expected 302 login, got {r.status_code}")

        r = c.get("/mybook/campaigns/1", follow_redirects=False)
        if r.status_code != 302:
            failures.append(f"campaign detail unauthenticated: expected 302 login, got {r.status_code}")

        r = c.get("/marketplace", follow_redirects=False)
        if r.status_code != 302:
            failures.append(f"/marketplace unauthenticated: expected 302 login, got {r.status_code}")

        r = c.get("/mybook/", follow_redirects=False)
        if r.status_code != 302:
            failures.append(f"dashboard unauthenticated: expected 302, got {r.status_code}")

    with app.app_context():
        if ink_is_author_account():
            failures.append("ink_is_author_account should be False with no logged-in user")
        if ink_show_author_workspace():
            failures.append("ink_show_author_workspace should be False with no logged-in user")
        try:
            ink_is_author_account(1)
        except ImportError as exc:
            failures.append(f"ink_is_author_account(1) ImportError: {exc}")

    if failures:
        print("FAILURES:")
        for f in failures:
            print(" -", f)
        sys.exit(1)

    print("OK: Ink Studio V1 smoke tests passed")


if __name__ == "__main__":
    main()
