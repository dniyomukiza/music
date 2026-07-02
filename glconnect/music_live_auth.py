"""Signed identity tokens for Music Live WebSocket sessions."""

from __future__ import annotations

import os
from typing import Any

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

MUSIC_LIVE_WS_SALT = "music-live-ws"
MUSIC_LIVE_WS_MAX_AGE_SECONDS = 60 * 60
_LOCAL_DEV_SECRET = "local-dev-secret-key-change-in-production"


def _jwt_secret() -> str | None:
    secret = (os.getenv("JWT_SECRET_KEY") or "").strip()
    if secret:
        return secret
    if os.getenv("FLASK_ENV") == "development" or not os.path.exists("/.dockerenv"):
        return _LOCAL_DEV_SECRET
    return None


def _serializer() -> URLSafeTimedSerializer | None:
    secret = _jwt_secret()
    if not secret:
        return None
    return URLSafeTimedSerializer(secret, salt=MUSIC_LIVE_WS_SALT)


def generate_music_live_ws_token(user_id: Any) -> str:
    """Return a signed token binding a Music Live socket to the current user id."""
    serializer = _serializer()
    if serializer is None:
        return ""
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return ""
    return serializer.dumps({"user_id": uid})


def validate_music_live_ws_token(
    token: str | None,
    expected_user_id: int,
    max_age: int = MUSIC_LIVE_WS_MAX_AGE_SECONDS,
) -> bool:
    """Validate that the token was issued for the requested Music Live user id."""
    if not token:
        return False
    serializer = _serializer()
    if serializer is None:
        return False
    try:
        data = serializer.loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return False
    try:
        token_user_id = int(data.get("user_id"))
    except (AttributeError, TypeError, ValueError):
        return False
    return token_user_id == expected_user_id
