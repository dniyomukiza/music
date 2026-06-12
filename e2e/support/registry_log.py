"""Persist tracked E2E user IDs when auto-cleanup is disabled."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

E2E_ROOT = Path(__file__).resolve().parent.parent
CREATED_IDS_PATH = E2E_ROOT / ".e2e-created-ids.json"


def append_created_user_ids(user_ids: list[int]) -> None:
    if not user_ids:
        return
    existing: list[dict] = []
    if CREATED_IDS_PATH.is_file():
        try:
            existing = json.loads(CREATED_IDS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = []
    known = {entry.get("user_id") for entry in existing if isinstance(entry, dict)}
    stamp = datetime.now(timezone.utc).isoformat()
    for uid in user_ids:
        if uid not in known:
            existing.append({"user_id": uid, "logged_at": stamp})
    CREATED_IDS_PATH.write_text(json.dumps(existing, indent=2), encoding="utf-8")
