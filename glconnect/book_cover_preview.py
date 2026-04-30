"""
Session-backed AI cover previews: generate to a temp file, user accepts or rejects before final save.
"""
from __future__ import annotations

import os
import shutil
import uuid
from typing import Any, Dict, Optional

from flask import current_app, session

SESSION_LISTING_AI_COVER = "pending_ai_cover_listing"
SESSION_EDIT_AI_COVER = "pending_ai_cover_edit"
PREVIEW_SUBDIR = "book_covers_previews"


def _preview_dir() -> str:
    root = current_app.root_path
    d = os.path.join(root, "static", PREVIEW_SUBDIR)
    os.makedirs(d, exist_ok=True)
    return d


def _covers_dir() -> str:
    root = current_app.root_path
    d = os.path.join(root, "static", "book_covers")
    os.makedirs(d, exist_ok=True)
    return d


def _abs_static_rel(rel: str) -> str:
    return os.path.join(current_app.root_path, "static", rel.replace("\\", "/"))


def _unlink_if_exists(rel: Optional[str]) -> None:
    if not rel:
        return
    path = _abs_static_rel(rel)
    if os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass


def clear_listing_preview() -> None:
    data = session.pop(SESSION_LISTING_AI_COVER, None)
    if data and data.get("rel"):
        _unlink_if_exists(data["rel"])
    session.modified = True


def save_listing_preview(image_bytes: bytes) -> str:
    """Write preview bytes; returns static-relative path (e.g. book_covers_previews/...)."""
    clear_listing_preview()
    _preview_dir()  # ensure glconnect/static/book_covers_previews exists (e.g. fresh deploy)
    fn = f"listing_{uuid.uuid4().hex[:12]}.png"
    rel = f"{PREVIEW_SUBDIR}/{fn}"
    path = _abs_static_rel(rel)
    with open(path, "wb") as out:
        out.write(image_bytes)
    session[SESSION_LISTING_AI_COVER] = {"rel": rel, "accepted": False}
    session.modified = True
    return rel


def set_listing_preview_accepted(accepted: bool) -> bool:
    data = session.get(SESSION_LISTING_AI_COVER)
    if not data or not data.get("rel"):
        return False
    if not os.path.isfile(_abs_static_rel(data["rel"])):
        return False
    data["accepted"] = bool(accepted)
    session[SESSION_LISTING_AI_COVER] = data
    session.modified = True
    return True


def promote_listing_preview_to_cover() -> Optional[str]:
    """Move accepted listing preview into book_covers/. Clears session. Returns cover rel or None."""
    data = session.get(SESSION_LISTING_AI_COVER)
    if not data or not data.get("accepted") or not data.get("rel"):
        return None
    src = _abs_static_rel(data["rel"])
    if not os.path.isfile(src):
        return None
    dest_name = f"ai_cover_{uuid.uuid4().hex[:10]}.png"
    dest_path = os.path.join(_covers_dir(), dest_name)
    shutil.move(src, dest_path)
    session.pop(SESSION_LISTING_AI_COVER, None)
    session.modified = True
    return f"book_covers/{dest_name}"


def listing_preview_image_rel() -> Optional[str]:
    data = session.get(SESSION_LISTING_AI_COVER)
    if not data or not data.get("rel"):
        return None
    if not os.path.isfile(_abs_static_rel(data["rel"])):
        return None
    return data["rel"]


def _edit_bucket() -> Dict[str, Any]:
    b = session.get(SESSION_EDIT_AI_COVER)
    if not isinstance(b, dict):
        b = {}
    return b


def _set_edit_bucket(bucket: Dict[str, Any]) -> None:
    session[SESSION_EDIT_AI_COVER] = bucket
    session.modified = True


def clear_edit_preview(book_id: int) -> None:
    key = str(int(book_id))
    bucket = _edit_bucket()
    prev = bucket.pop(key, None)
    if prev and prev.get("rel"):
        _unlink_if_exists(prev["rel"])
    _set_edit_bucket(bucket)


def save_edit_preview(book_id: int, image_bytes: bytes) -> str:
    clear_edit_preview(book_id)
    _preview_dir()
    fn = f"edit_{int(book_id)}_{uuid.uuid4().hex[:10]}.png"
    rel = f"{PREVIEW_SUBDIR}/{fn}"
    path = _abs_static_rel(rel)
    with open(path, "wb") as out:
        out.write(image_bytes)
    bucket = _edit_bucket()
    bucket[str(int(book_id))] = {"rel": rel}
    _set_edit_bucket(bucket)
    return rel


def edit_preview_image_rel(book_id: int) -> Optional[str]:
    key = str(int(book_id))
    data = _edit_bucket().get(key)
    if not data or not data.get("rel"):
        return None
    if not os.path.isfile(_abs_static_rel(data["rel"])):
        return None
    return data["rel"]


def promote_edit_preview_to_cover(book_id: int) -> Optional[str]:
    """Move pending edit preview to book_covers/. Clears edit preview session for book_id."""
    key = str(int(book_id))
    bucket = _edit_bucket()
    data = bucket.get(key)
    if not data or not data.get("rel"):
        return None
    src = _abs_static_rel(data["rel"])
    if not os.path.isfile(src):
        return None
    dest_name = f"ai_cover_{uuid.uuid4().hex[:10]}.png"
    dest_path = os.path.join(_covers_dir(), dest_name)
    shutil.move(src, dest_path)
    bucket.pop(key, None)
    _set_edit_bucket(bucket)
    return f"book_covers/{dest_name}"


def maybe_remove_local_cover_file(cover_image: Optional[str]) -> None:
    """Best-effort delete of a previously stored relative book_covers/* path."""
    if not cover_image:
        return
    c = str(cover_image).strip()
    if c.startswith("http://") or c.startswith("https://") or c.startswith("/"):
        return
    if not c.startswith("book_covers/"):
        return
    _unlink_if_exists(c)
