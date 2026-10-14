#!/usr/bin/env python3
"""Smoke tests for collaboration role normalization."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from glconnect.book_platform_models import CollaborationRole
from glconnect.collaboration_permissions import normalize_collaboration_role, permissions_for_role


def main():
    for raw in ("viewer", "reviewer", "editor", "co_author", "coauthor", "Co author"):
        role = normalize_collaboration_role(raw)
        perms = permissions_for_role(role)
        assert role in CollaborationRole, raw
        assert perms["can_view"] is True
        print(f"OK {raw!r} -> {role.value} edit={perms['can_edit']}")

    co = normalize_collaboration_role("coauthor")
    assert co == CollaborationRole.CO_AUTHOR
    assert permissions_for_role(co)["can_edit"] is True
    print("OK: coauthor maps to co_author with edit rights")


if __name__ == "__main__":
    main()
