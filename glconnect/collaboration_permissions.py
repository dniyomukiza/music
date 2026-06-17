"""Collaboration role and permission helpers for Ink Studio books."""

from __future__ import annotations

from typing import Optional

from glconnect.book_platform_models import BookCollaboration, CollaborationRole

ROLE_ALIASES = {
    "co_author": "co_author",
    "coauthor": "co_author",
    "co-author": "co_author",
    "author": "author",
    "editor": "editor",
    "reviewer": "reviewer",
    "viewer": "viewer",
    "view": "reviewer",
    "edit": "editor",
}

MANAGEABLE_COLLAB_ROLES = frozenset(
    {
        CollaborationRole.EDITOR,
        CollaborationRole.REVIEWER,
        CollaborationRole.VIEWER,
        CollaborationRole.CO_AUTHOR,
    }
)


def normalize_collaboration_role(role_value: str) -> CollaborationRole:
    """Map client role strings to CollaborationRole enum values."""
    key = (role_value or "").lower().replace("-", "_").replace(" ", "_")
    normalized = ROLE_ALIASES.get(key, key)
    return CollaborationRole(normalized)


def permissions_for_role(role: CollaborationRole) -> dict:
    """Persisted permission flags derived from the collaboration role."""
    can_edit = role in {
        CollaborationRole.EDITOR,
        CollaborationRole.CO_AUTHOR,
        CollaborationRole.AUTHOR,
    }
    can_comment = role in {
        CollaborationRole.EDITOR,
        CollaborationRole.REVIEWER,
        CollaborationRole.CO_AUTHOR,
        CollaborationRole.AUTHOR,
    }
    return {
        "can_view": True,
        "can_edit": can_edit,
        "can_comment": can_comment,
    }


def collaboration_can_edit(collaboration: Optional[BookCollaboration]) -> bool:
    if not collaboration or not collaboration.is_active:
        return False
    perms = collaboration.permissions or {}
    if "can_edit" in perms:
        return bool(perms.get("can_edit"))
    return collaboration.role in {
        CollaborationRole.EDITOR,
        CollaborationRole.CO_AUTHOR,
        CollaborationRole.AUTHOR,
    }


def collaboration_can_view(collaboration: Optional[BookCollaboration]) -> bool:
    if not collaboration or not collaboration.is_active:
        return False
    perms = collaboration.permissions or {}
    if "can_view" in perms:
        return bool(perms.get("can_view"))
    return collaboration.role in MANAGEABLE_COLLAB_ROLES | {CollaborationRole.AUTHOR}


def apply_role_to_collaboration(collaboration: BookCollaboration, role: CollaborationRole) -> None:
    collaboration.role = role
    collaboration.permissions = permissions_for_role(role)
