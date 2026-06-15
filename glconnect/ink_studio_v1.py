"""Ink Studio Milestone 1 — marketplace entry, book campaigns + book sales."""

import os
from typing import Optional

from flask import current_app, redirect, url_for
from flask_login import current_user

# Roles that cannot list books or start campaigns in V1 (media / non-book personas).
_V1_EXCLUDED_AUTHOR_ROLES = frozenset({"artist", "podcaster", "freelancer", "blogger", "other"})


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def ink_v1_books_launch(app=None) -> bool:
    """True when INK_STUDIO_V1_BOOKS_LAUNCH is enabled."""
    target = app
    if target is None:
        try:
            target = current_app._get_current_object()
        except RuntimeError:
            target = None
    if target is not None:
        cfg = target.config.get("INK_STUDIO_V1_BOOKS_LAUNCH")
        if cfg is not None:
            if isinstance(cfg, bool):
                return cfg
            return str(cfg).strip().lower() in ("1", "true", "yes", "on")
    return _env_truthy("INK_STUDIO_V1_BOOKS_LAUNCH")


def ink_show_media_ecosystem(app=None) -> bool:
    """False in V1 — hide content hub, music, creators nav."""
    return not ink_v1_books_launch(app)


def ink_is_author_account(user_id: Optional[int] = None) -> bool:
    """
    True when the user has a completed author account: Ink Studio profile card,
    signed publishing agreement, and writer/book-platform profile.
    """
    uid = user_id
    if uid is None:
        if not getattr(current_user, "is_authenticated", False):
            return False
        uid = current_user.user_id
        if getattr(current_user, "role", None) in _V1_EXCLUDED_AUTHOR_ROLES:
            return False

    from glconnect.book_platform_routes import (
        _author_needs_publishing_agreement,
        _author_requires_setup_profile,
        get_profile_id,
        get_user_profile,
    )
    from glconnect.book_platform_models import BookProject

    if _author_requires_setup_profile(uid):
        return False
    if _author_needs_publishing_agreement(uid):
        return False

    if user_id is not None:
        from glconnect.models import User
        from glconnect.book_platform_models import BookPlatformUser, Writer

        user = User.query.get(uid)
        if not user or user.role in _V1_EXCLUDED_AUTHOR_ROLES:
            return False
        bp = BookPlatformUser.query.filter_by(user_id=uid).first()
        writer = Writer.query.filter_by(user_id=uid).first()
        if not bp and not writer:
            return False
        profile_type = "writer" if writer else "book_platform"
        user_profile = writer or bp
        author_id = get_profile_id(user_profile, profile_type)
        if not author_id:
            return False
        if user.role == "author":
            return True
        return BookProject.query.filter_by(author_id=author_id).count() > 0

    user_profile, profile_type = get_user_profile()
    if profile_type not in ("writer", "book_platform") or not user_profile:
        return False
    author_id = get_profile_id(user_profile, profile_type)
    if not author_id:
        return False
    if current_user.role == "author":
        return True
    return BookProject.query.filter_by(author_id=author_id).count() > 0


def ink_v1_role_redirect(user):
    """Post-login / ink-studio entry redirect when V1 launch flag is on."""
    from glconnect.book_platform_routes import _author_requires_setup_profile

    if user.role == "author" and _author_requires_setup_profile(user.user_id):
        return redirect(url_for("book_platform.setup_profile"))
    return redirect(url_for("book_platform.marketplace"))


def ink_account_capabilities(user_id: Optional[int] = None) -> dict:
    """
    Signed-in account capabilities for Ink Studio V1.

    Authors combine patron privileges (buy, fund others' campaigns) with author
    workspace tools (list books, launch campaigns). Own campaigns cannot be funded.
    """
    if user_id is None:
        authed = getattr(current_user, "is_authenticated", False)
        uid = current_user.user_id if authed else None
    else:
        authed = True
        uid = user_id

    is_author = ink_is_author_account(uid) if authed else False
    return {
        "authenticated": authed,
        "is_author": is_author,
        "can_browse_marketplace": authed,
        "can_buy_books": authed,
        "can_fund_campaigns": authed,
        "can_track_supported_projects": authed,
        "can_manage_author_workspace": is_author,
        "can_list_on_marketplace": is_author,
        "can_launch_campaigns": is_author,
    }
