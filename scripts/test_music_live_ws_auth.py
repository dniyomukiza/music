#!/usr/bin/env python3
"""Regression checks for Music Live WebSocket user binding."""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    ws_content = (ROOT / "glconnect" / "music_live_ws.py").read_text(encoding="utf-8")
    template_content = (
        ROOT / "glconnect" / "templates" / "book_platform" / "music_dashboard.html"
    ).read_text(encoding="utf-8")
    app_content = (ROOT / "glconnect" / "__init__.py").read_text(encoding="utf-8")
    auth_content = (ROOT / "glconnect" / "music_live_auth.py").read_text(encoding="utf-8")

    failures = []

    if "validate_music_live_ws_token(token, uid)" not in ws_content:
        failures.append("WebSocket handler should validate signed tokens for non-guest users")
    runner_call_index = ws_content.find("= _get_runner()")
    if ws_content.find("validate_music_live_ws_token(token, uid)") > runner_call_index:
        failures.append("WebSocket auth should run before loading the ADK runner")
    if 'close(code=1008, reason="Unauthorized music session")' not in ws_content:
        failures.append("missing or mismatched tokens should close with policy violation")
    if "uid != 0" not in ws_content:
        failures.append("guest user_id=0 should remain the only unauthenticated socket context")
    if "music_live_ws_token(current_user.user_id)" not in template_content:
        failures.append("dashboard should generate a signed token for the logged-in user")
    if "encodeURIComponent(VOICE_WS_TOKEN)" not in template_content:
        failures.append("dashboard should send the signed token on the WebSocket URL")
    if "music_live_ws_token" not in app_content:
        failures.append("Flask app should expose the Music Live token helper to templates")
    if "URLSafeTimedSerializer" not in auth_content or "expected_user_id" not in auth_content:
        failures.append("token helper should bind a signed token to the requested user id")

    if failures:
        print("FAILURES:")
        for failure in failures:
            print(" -", failure)
        sys.exit(1)

    print("OK: Music Live WebSocket requires signed user binding")


if __name__ == "__main__":
    main()
