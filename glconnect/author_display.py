"""Resolve public author names for marketplace, covers, and author cards."""

from __future__ import annotations

import json
import time
from typing import Any, Optional

_DEBUG_LOG_PATH = "/Applications/untitled folder/music-1/.cursor/debug-fe2ff6.log"


def looks_like_auto_author_name(name: Optional[str], username: Optional[str] = None) -> bool:
    """True when a stored name is likely a placeholder, not an intentional pen name."""
    if not name or not str(name).strip():
        return True
    normalized = str(name).strip().lower()
    if username and normalized == str(username).strip().lower():
        return True
    if normalized.startswith("debug"):
        return True
    if normalized in ("author", "user", "test", "test writer", "test author", "unknown"):
        return True
    return False


def _user_full_name(user: Any) -> Optional[str]:
    if not user:
        return None
    first = (getattr(user, "first_name", None) or "").strip()
    last = (getattr(user, "last_name", None) or "").strip()
    if first and last:
        return f"{first} {last}"
    if first:
        return first
    return None


def marketplace_author_display_name(
    author: Any,
    *,
    writer: Any = None,
    user: Any = None,
    log_context: Optional[str] = None,
) -> str:
    """
    Public author name shown on listings and marketplace modals.

    Prefers an intentional Ink Studio pen name, then Writer profile name,
    then account first/last name, then legacy pen name / username.
    """
    if not author:
        return "Author"

    user = user or getattr(author, "user", None)
    username = (getattr(user, "username", None) or "").strip() or None
    pen = (getattr(author, "pen_name", None) or "").strip()
    setup_completed = bool(getattr(author, "author_card_setup_completed", False))

    if writer is None and getattr(author, "user_id", None):
        from glconnect.models import Writer

        writer = Writer.query.filter_by(user_id=author.user_id).first()

    writer_name = (getattr(writer, "writer_name", None) or "").strip() if writer else ""
    full_name = _user_full_name(user)
    source = "fallback"

    if pen and setup_completed and not looks_like_auto_author_name(pen, username):
        result = pen
        source = "pen_name_setup"
    elif writer_name and not looks_like_auto_author_name(writer_name, username):
        result = writer_name
        source = "writer_name"
    elif full_name and not looks_like_auto_author_name(full_name, username):
        result = full_name
        source = "user_full_name"
    elif pen:
        result = pen
        source = "pen_name_legacy"
    elif username:
        result = username
        source = "username"
    else:
        result = "Author"
        source = "default"

    if log_context:
        # #region agent log
        try:
            payload = {
                "sessionId": "fe2ff6",
                "runId": "author-name",
                "hypothesisId": "H-author-pen-stale",
                "location": "author_display:marketplace_author_display_name",
                "message": "author display name resolved",
                "data": {
                    "context": log_context,
                    "source": source,
                    "pen_name": pen or None,
                    "writer_name": writer_name or None,
                    "has_full_name": bool(full_name),
                    "username": username,
                    "setup_completed": setup_completed,
                    "result_len": len(result),
                },
                "timestamp": int(time.time() * 1000),
            }
            with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload) + "\n")
        except Exception:
            pass
        # #endregion

    return result


def sync_stale_book_platform_pen_name(author: Any) -> bool:
    """Persist a better pen name when the stored value is an obvious placeholder."""
    if not author:
        return False
    current = (getattr(author, "pen_name", None) or "").strip()
    user = getattr(author, "user", None)
    username = (getattr(user, "username", None) or "").strip() or None
    if current and not looks_like_auto_author_name(current, username):
        return False
    resolved = marketplace_author_display_name(author, user=user)
    if not resolved or resolved == "Author" or resolved == current:
        return False
    author.pen_name = resolved
    return True
