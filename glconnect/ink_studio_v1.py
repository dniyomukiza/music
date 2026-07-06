"""Ink Studio Milestone 1, marketplace entry, book campaigns + book sales."""

import json
import logging
import os
import time
from typing import Optional

from flask import current_app, redirect, url_for
from flask_login import current_user

logger = logging.getLogger(__name__)

# Roles that cannot list books or start campaigns in V1 (media / non-book personas).
_V1_EXCLUDED_AUTHOR_ROLES = frozenset({"artist", "podcaster", "freelancer", "blogger", "other"})

_DEBUG_LOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".cursor",
    "debug-fe2ff6.log",
)


def _agent_debug_log(hypothesis_id: str, message: str, data: dict | None = None) -> None:
    # #region agent log
    if not _env_truthy("DEBUG_AGENT_LOG"):
        return
    try:
        payload = {
            "sessionId": "fe2ff6",
            "hypothesisId": hypothesis_id,
            "location": "ink_studio_v1.py",
            "message": message,
            "data": data or {},
            "timestamp": int(time.time() * 1000),
        }
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, default=str) + "\n")
    except Exception:
        pass
    # #endregion


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
    """False in V1, hide content hub, music, creators nav."""
    return not ink_v1_books_launch(app)


def ink_is_author_account(user_id: Optional[int] = None) -> bool:
    """
    True when the user has a completed author account: Ink Studio profile card,
    signed publishing agreement, and writer/book-platform profile.
    """
    try:
        return _ink_is_author_account_impl(user_id)
    except Exception as exc:
        logger.warning("ink_is_author_account failed safely: %s", exc, exc_info=True)
        # #region agent log
        _agent_debug_log(
            "RESILIENCE",
            "ink_is_author_account_exception",
            {"error_type": type(exc).__name__, "error": str(exc)[:200]},
        )
        # #endregion
        return False


def _ink_is_author_account_impl(user_id: Optional[int] = None) -> bool:
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
        from glconnect.models import User, Writer
        from glconnect.book_platform_models import BookPlatformUser

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


def ink_show_author_workspace(user_id: Optional[int] = None) -> bool:
    """
    True when author nav/CTAs should appear (marketplace hero, My books, payouts).

    Signed-up authors (role=author) see workspace tools immediately; listing and
    uploads still require completed profile + publishing agreement via route guards.
    """
    try:
        if ink_is_author_account(user_id):
            return True
        if user_id is None:
            if not getattr(current_user, "is_authenticated", False):
                return False
            return getattr(current_user, "role", None) == "author"
        from glconnect.models import User

        user = User.query.get(user_id)
        return bool(user and user.role == "author")
    except Exception as exc:
        logger.warning("ink_show_author_workspace failed safely: %s", exc, exc_info=True)
        return False


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

    try:
        is_author = ink_is_author_account(uid) if authed else False
    except Exception as exc:
        logger.warning("ink_account_capabilities author check failed: %s", exc, exc_info=True)
        is_author = False

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


def ink_studio_v1_context_defaults(app=None):
    """Safe Jinja defaults when V1 context injection fails."""
    from flask_login import current_user

    authed = getattr(current_user, "is_authenticated", False)
    return {
        "ink_v1_books_launch": ink_v1_books_launch(app),
        "ink_is_author_account": False,
        "ink_show_author_workspace": False,
        "ink_show_media_ecosystem": ink_show_media_ecosystem(app),
        "ink_account_capabilities": {
            "authenticated": authed,
            "is_author": False,
            "can_browse_marketplace": authed,
            "can_buy_books": authed,
            "can_fund_campaigns": authed,
            "can_track_supported_projects": authed,
            "can_manage_author_workspace": False,
            "can_list_on_marketplace": False,
            "can_launch_campaigns": False,
        },
    }


def about_scroll_nav_urls():
    """
    Scrolling about-page nav destinations.

    Pitch / Fund → author campaigns (or author onboarding).
    Write / Publish → Ink Studio / My books (or onboarding).
    Promote → GLC Media (Content hub) for any signed-in user.
    Sell → Marketplace for any signed-in user.
    Guests → login with ``next`` preserved.
    """
    from flask import url_for

    from glconnect.book_platform_routes import _author_requires_setup_profile

    promote = url_for("book_platform.content_hub")
    sell = url_for("book_platform.marketplace")
    browse_campaigns = url_for("book_platform.campaigns")
    author_campaigns = url_for("book_platform.author_my_campaigns")
    my_books = url_for("book_platform.books")
    ink_studio = url_for("book_platform.ink_studio_access")

    def _setup(next_path: str) -> str:
        return url_for("book_platform.setup_profile", next=next_path)

    if not getattr(current_user, "is_authenticated", False):
        login = "routes1.login"
        campaign_entry = _setup(author_campaigns)
        books_entry = _setup(my_books)
        return {
            "pitch": url_for(login, next=campaign_entry),
            "fund": url_for(login, next=campaign_entry),
            "write": url_for(login, next=ink_studio),
            "publish": url_for(login, next=books_entry),
            "promote": url_for(login, next=promote),
            "sell": url_for(login, next=sell),
            "campaigns": url_for(login, next=browse_campaigns),
        }

    uid = current_user.user_id
    author_workspace = ink_show_author_workspace(uid)
    needs_setup = _author_requires_setup_profile(uid)

    if author_workspace and not needs_setup:
        campaign_url = author_campaigns
        write_url = ink_studio
        publish_url = my_books
    elif author_workspace or getattr(current_user, "role", None) == "author":
        campaign_url = _setup(author_campaigns)
        write_url = _setup(my_books)
        publish_url = _setup(my_books)
    else:
        campaign_url = _setup(author_campaigns)
        write_url = _setup(my_books)
        publish_url = _setup(my_books)

    return {
        "pitch": campaign_url,
        "fund": campaign_url,
        "write": write_url,
        "publish": publish_url,
        "promote": promote,
        "sell": sell,
        "campaigns": browse_campaigns,
    }


def _about_href(endpoint: str, *, protected: bool = False, **url_kwargs: str) -> str:
    """Resolve a platform link; guests are sent to login with ``next`` when protected."""
    from flask import url_for

    target = url_for(endpoint, **url_kwargs)
    if protected and not getattr(current_user, "is_authenticated", False):
        return url_for("routes1.login", next=target)
    return target


def _about_link(label: str, endpoint: str, *, protected: bool = False, description: str = "", **url_kwargs: str) -> dict:
    return {
        "label": label,
        "description": description,
        "href": _about_href(endpoint, protected=protected, **url_kwargs),
        "protected": protected,
        "requires_auth": protected and not getattr(current_user, "is_authenticated", False),
    }


def about_site_link_groups():
    """
    Active platform destinations for the /about link directory.

    Public links resolve directly; proprietary areas redirect guests to sign in first.
    """
    groups = [
        {
            "id": "discover",
            "title": "Discover",
            "description": "Public entry points and company pages.",
            "links": [
                _about_link("Home", "routes.index", description="Marketing landing and creator overview."),
                _about_link("Platform directory", "routes.platform", description="All active links (internal reference)."),
                _about_link("Blogs", "blog.blogs", description="Stories and journalism."),
                _about_link("Music", "book_platform.music_dashboard", description="GLC Media music and playlists."),
                _about_link("News", "news_bp.index", description="AI news broadcasts and audio."),
                _about_link("Language", "routes1.findwords", description="Word game and language tools."),
                _about_link("Community dictionary", "routes1.community_dictionary_public", description="Crowdsourced word definitions."),
                _about_link("Careers", "routes.careers", description="Join our mission."),
                _about_link("Support", "blog.contact", description="Questions about Ink Studio, print orders, and partnerships."),
                _about_link("Pitch deck", "routes.pitch_deck", protected=True, description="Investor overview."),
            ],
        },
        {
            "id": "ink-studio",
            "title": "Ink Studio",
            "description": "Author tools, marketplace, and patron campaigns.",
            "links": [
                _about_link("Ink Studio", "book_platform.ink_studio_access", protected=True, description="Write, publish, and manage projects."),
                _about_link("Marketplace", "book_platform.marketplace", protected=True, description="Browse and buy ebooks and audiobooks."),
                _about_link("Book campaigns", "book_platform.campaigns", protected=True, description="Fund books before publication."),
                _about_link("Supported projects", "book_platform.supported_projects", protected=True, description="Track campaigns you backed."),
                _about_link("My library", "book_platform.my_library", protected=True, description="Purchased ebooks and audiobooks."),
                _about_link("My books", "book_platform.books", protected=True, description="Author workspace and listings."),
                _about_link("My campaigns", "book_platform.author_my_campaigns", protected=True, description="Author funding campaigns."),
                _about_link("Become an author", "book_platform.setup_profile", protected=True, description="Complete your Ink Studio author profile."),
                _about_link("Earnings", "book_platform.earnings_dashboard", protected=True, description="Reviewer, investor, and author payouts."),
                _about_link("Payout account", "book_platform.author_payout_setup", protected=True, description="Stripe Connect for author sales."),
            ],
        },
        {
            "id": "account",
            "title": "Account",
            "description": "Sign in to access proprietary platform areas.",
            "links": [
                _about_link("Sign in", "routes1.login", description="Access protected tools and content."),
                _about_link("Sign up", "routes1.register", description="Create a free Ndotonic account."),
                _about_link("My profile", "prof.profile", protected=True, description="Account settings and profile."),
                _about_link("Write a story", "blog.blogpost", protected=True, description="Publish from the blog editor."),
                _about_link("Apply for a role", "routes.careers_apply", description="Submit a careers application."),
            ],
        },
    ]

    if ink_show_media_ecosystem():
        groups.insert(
            2,
            {
                "id": "creators",
                "title": "Creators & media",
                "description": "Content hub, podcasts, and creator workflows.",
                "links": [
                    _about_link("Creators hub", "book_platform.content_hub", protected=True, description="Blogs, news, freelancing, and music."),
                    _about_link("Podcast library", "book_platform.podcast_library", protected=True, description="Approved podcast episodes."),
                ],
            },
        )

    if getattr(current_user, "is_authenticated", False) and getattr(current_user, "role", None) == "admin":
        groups.append(
            {
                "id": "admin",
                "title": "Admin",
                "description": "Internal moderation and operations.",
                "links": [
                    _about_link("Admin panel", "book_platform.admin_hub", protected=True, description="Books, podcasts, songs, and reviewers."),
                    _about_link("Platform analytics", "analytics.analytics_dashboard", protected=True, description="Traffic and usage dashboard."),
                    _about_link("News analytics", "news_bp.analytics", protected=True, description="Topic and category trends."),
                ],
            },
        )

    groups.append(
        {
            "id": "legacy",
            "title": "Legacy previews",
            "description": "Archived layouts kept for easy restore — not linked from public nav.",
            "links": [
                _about_link("Legacy home", "routes.home_legacy", description="Former hero landing page."),
                _about_link("Legacy careers", "routes.careers_legacy", description="Former multi-role careers listings."),
            ],
        },
    )

    return groups
