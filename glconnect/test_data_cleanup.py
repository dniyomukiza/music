"""
Remove manual-test rows from the database for specific test accounts.

Primary use: delete everything tied to username ``testuser`` (or ``TEST_DATA_USERNAMES``).

Match rules (env):
  TEST_DATA_USERNAMES          — exact usernames, comma-separated (default: testuser)
  TEST_DATA_USERNAME_PREFIXES  — optional extra prefix match (test_, e2e_, qa_)
  TEST_DATA_EMAIL_MARKERS      — optional email substrings
  TEST_DATA_EXTRA_USER_IDS     — optional explicit user_id values

Books: all ``book_projects`` authored by a matched user are removed (any title).
Also removes purchases, library rows, annotations, posts, playlists, etc. for that user_id.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from sqlalchemy import or_

logger = logging.getLogger(__name__)

DEFAULT_TEST_USERNAMES = ("testuser",)
# e2e- = Playwright suite (e2e/support/user_factory.py); test_/e2e_/qa_ = manual test accounts
DEFAULT_USERNAME_PREFIXES = ("test_", "e2e_", "e2e-", "qa_")
DEFAULT_EMAIL_MARKERS = ("+test@", "@test.", "test+", "e2e+")


def _csv_env(name: str, default: Sequence[str]) -> Tuple[str, ...]:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return tuple(default)
    return tuple(p.strip().lower() for p in raw.split(",") if p.strip())


def _extra_user_ids_from_env() -> Set[int]:
    raw = (os.getenv("TEST_DATA_EXTRA_USER_IDS") or "").strip()
    if not raw:
        return set()
    ids: Set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return ids


def is_test_account_marker(
    username: Optional[str],
    email: Optional[str],
    *,
    exact_usernames: Sequence[str] = DEFAULT_TEST_USERNAMES,
    username_prefixes: Sequence[str] = DEFAULT_USERNAME_PREFIXES,
    email_markers: Sequence[str] = DEFAULT_EMAIL_MARKERS,
) -> bool:
    """True when username/email match configured test-account rules."""
    uname = (username or "").strip().lower()
    mail = (email or "").strip().lower()

    if uname and uname in {u.lower() for u in exact_usernames}:
        return True
    if uname and any(uname.startswith(p) for p in username_prefixes):
        return True
    if uname and (uname.endswith("_test") or uname.endswith("-test")):
        return True
    if mail and any(m in mail for m in email_markers):
        return True
    return False


def find_test_users(
    db,
    *,
    exact_usernames: Optional[Sequence[str]] = None,
    username_prefixes: Optional[Sequence[str]] = None,
    email_markers: Optional[Sequence[str]] = None,
    extra_user_ids: Optional[Set[int]] = None,
) -> List[Any]:
    """Return User rows that match test rules (admins excluded)."""
    from glconnect.models import User

    names = (
        list(exact_usernames)
        if exact_usernames is not None
        else list(_csv_env("TEST_DATA_USERNAMES", DEFAULT_TEST_USERNAMES))
    )
    prefixes = (
        tuple(username_prefixes)
        if username_prefixes is not None
        else _csv_env("TEST_DATA_USERNAME_PREFIXES", DEFAULT_USERNAME_PREFIXES)
    )
    markers = (
        tuple(email_markers)
        if email_markers is not None
        else _csv_env("TEST_DATA_EMAIL_MARKERS", DEFAULT_EMAIL_MARKERS)
    )
    extra = extra_user_ids if extra_user_ids is not None else _extra_user_ids_from_env()

    users = User.query.all()
    matched = []
    for user in users:
        if (user.role or "").lower() == "admin":
            continue
        if user.user_id in extra:
            matched.append(user)
            continue
        if is_test_account_marker(
            user.username,
            user.email,
            exact_usernames=names,
            username_prefixes=prefixes,
            email_markers=markers,
        ):
            matched.append(user)
    return matched


def find_book_ids_for_users(db, test_user_ids: Sequence[int]) -> List[int]:
    """All Ink Studio books authored by any of the given users (any title)."""
    from glconnect.book_platform_models import BookPlatformUser, BookProject

    if not test_user_ids:
        return []

    author_bp_ids = [
        r[0]
        for r in db.session.query(BookPlatformUser.id)
        .filter(BookPlatformUser.user_id.in_(list(test_user_ids)))
        .all()
    ]
    if not author_bp_ids:
        return []

    return sorted(
        r[0]
        for r in db.session.query(BookProject.id)
        .filter(BookProject.author_id.in_(author_bp_ids))
        .all()
    )


def _delete_purchases_for_user(db, user_id: int, username: str) -> int:
    from glconnect.book_platform_models import BookPurchase, BookSale

    uname = (username or "").strip().lower()
    conditions = [BookPurchase.buyer_user_id == user_id]
    if uname:
        conditions.append(BookPurchase.buyer_username.ilike(uname))

    purchases = BookPurchase.query.filter(or_(*conditions)).all()
    count = 0
    for purchase in purchases:
        BookSale.query.filter_by(purchase_id=purchase.id).delete(synchronize_session=False)
        db.session.delete(purchase)
        count += 1
    return count


def _delete_investments_for_bp_user(db, bp_user_id: int) -> int:
    from glconnect.book_platform_models import (
        AuthorCampaignPayoutRequest,
        BookInvestment,
        InvestmentPayout,
        PayoutRequest,
        RefundRequest,
    )

    investments = BookInvestment.query.filter_by(investor_id=bp_user_id).all()
    if not investments:
        return 0

    inv_ids = [inv.id for inv in investments]
    camp_ids = {inv.campaign_id for inv in investments if inv.campaign_id}

    InvestmentPayout.query.filter(InvestmentPayout.investment_id.in_(inv_ids)).delete(
        synchronize_session=False
    )
    PayoutRequest.query.filter(PayoutRequest.investment_id.in_(inv_ids)).delete(
        synchronize_session=False
    )
    RefundRequest.query.filter(RefundRequest.investment_id.in_(inv_ids)).delete(
        synchronize_session=False
    )
    BookInvestment.query.filter(BookInvestment.id.in_(inv_ids)).delete(synchronize_session=False)

    if camp_ids:
        AuthorCampaignPayoutRequest.query.filter(
            AuthorCampaignPayoutRequest.campaign_id.in_(list(camp_ids))
        ).delete(synchronize_session=False)

    return len(inv_ids)


def _delete_user_scoped_app_rows(db, user_id: int, username: str) -> Dict[str, int]:
    """Delete rows in non–Ink Studio tables that reference users.user_id."""
    from glconnect.models import (
        Artist,
        PageAnalytics,
        Playlist,
        PodcastSubmission,
        Post,
        PostLike,
        PostView,
        WordContribution,
    )
    from glconnect.book_platform_models import AccreditedReviewer, LibraryBookHide, ReaderAnnotation

    counts: Dict[str, int] = {}
    uname = (username or "").strip()

    counts["post_likes"] = PostLike.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    counts["post_views"] = PostView.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    counts["posts"] = Post.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    counts["playlists"] = Playlist.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    counts["page_analytics"] = PageAnalytics.query.filter_by(user_id=user_id).delete(
        synchronize_session=False
    )
    counts["library_book_hides"] = LibraryBookHide.query.filter_by(user_id=user_id).delete(
        synchronize_session=False
    )
    counts["reader_annotations"] = ReaderAnnotation.query.filter_by(user_id=user_id).delete(
        synchronize_session=False
    )
    counts["podcast_submissions"] = PodcastSubmission.query.filter_by(user_id=user_id).delete(
        synchronize_session=False
    )
    counts["word_contributions_as_contributor"] = WordContribution.query.filter_by(
        contributor_id=user_id
    ).delete(synchronize_session=False)
    counts["word_contributions_as_reviewer"] = WordContribution.query.filter_by(
        reviewer_id=user_id
    ).delete(synchronize_session=False)

    artist = Artist.query.filter_by(user_id=user_id).first()
    if artist:
        if artist.profile_pic and artist.profile_pic != "static/uploads/default.jpg":
            _try_remove_static_file(artist.profile_pic)
        db.session.delete(artist)
        counts["artists"] = 1
    else:
        counts["artists"] = 0

    reviewer = AccreditedReviewer.query.filter_by(user_id=user_id).first()
    if reviewer:
        db.session.delete(reviewer)
        counts["accredited_reviewers"] = 1
    else:
        counts["accredited_reviewers"] = 0

    counts["book_purchases"] = _delete_purchases_for_user(db, user_id, uname)

    return counts


def _try_remove_static_file(relative_path: str) -> None:
    path = os.path.join(os.getcwd(), "glconnect", "static", relative_path.lstrip("/"))
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError as exc:
        logger.warning("Could not remove file %s: %s", path, exc)


def delete_test_user(db, user_id: int, *, username: Optional[str] = None) -> Dict[str, Any]:
    """
    Delete one test user and every row tied to their user_id / username.
    """
    from glconnect.models import User
    from glconnect.book_platform_models import BookPlatformUser
    from glconnect.user_deletion_handler import delete_user_and_all_data

    user = User.query.get(user_id)
    if not user:
        return {"success": False, "message": f"User {user_id} not found"}
    if (user.role or "").lower() == "admin":
        return {"success": False, "message": f"Refusing to delete admin user {user.username}"}

    uname = username or user.username
    detail: Dict[str, Any] = {"user_id": user_id, "username": uname}
    detail["app_rows_removed"] = _delete_user_scoped_app_rows(db, user_id, uname)

    bp_user = BookPlatformUser.query.filter_by(user_id=user_id).first()
    if bp_user:
        detail["investments_removed"] = _delete_investments_for_bp_user(db, bp_user.id)

    db.session.flush()
    result = delete_user_and_all_data(user_id, commit=False)
    detail.update(result)
    return detail


def cleanup_test_data(
    db,
    *,
    dry_run: bool = True,
    exact_usernames: Optional[Sequence[str]] = None,
    username_prefixes: Optional[Sequence[str]] = None,
    email_markers: Optional[Sequence[str]] = None,
    extra_user_ids: Optional[Set[int]] = None,
) -> Dict[str, Any]:
    """
    Remove all data for matched test users (default: username ``testuser``).
    """
    from glconnect.book_platform_models import BookPlatformUser, BookProject
    from glconnect.book_platform_purge import purge_book_projects_by_ids
    from glconnect.user_deletion_handler import cleanup_book_files

    names = (
        list(exact_usernames)
        if exact_usernames is not None
        else list(_csv_env("TEST_DATA_USERNAMES", DEFAULT_TEST_USERNAMES))
    )
    prefixes = (
        tuple(username_prefixes)
        if username_prefixes is not None
        else _csv_env("TEST_DATA_USERNAME_PREFIXES", DEFAULT_USERNAME_PREFIXES)
    )
    markers = (
        tuple(email_markers)
        if email_markers is not None
        else _csv_env("TEST_DATA_EMAIL_MARKERS", DEFAULT_EMAIL_MARKERS)
    )
    extra = extra_user_ids if extra_user_ids is not None else _extra_user_ids_from_env()

    test_users = find_test_users(
        db,
        exact_usernames=names,
        username_prefixes=prefixes,
        email_markers=markers,
        extra_user_ids=extra,
    )
    test_user_ids = [u.user_id for u in test_users]
    book_ids = find_book_ids_for_users(db, test_user_ids)

    books = BookProject.query.filter(BookProject.id.in_(book_ids)).all() if book_ids else []

    author_bp_ids: Set[int] = set()
    if test_user_ids:
        author_bp_ids = {
            r[0]
            for r in db.session.query(BookPlatformUser.id)
            .filter(BookPlatformUser.user_id.in_(test_user_ids))
            .all()
        }

    summary: Dict[str, Any] = {
        "dry_run": dry_run,
        "match_rules": {
            "usernames": list(names),
            "username_prefixes": list(prefixes),
            "email_markers": list(markers),
            "extra_user_ids": sorted(extra),
        },
        "test_users": [
            {"user_id": u.user_id, "username": u.username, "email": u.email, "role": u.role}
            for u in test_users
        ],
        "test_books": [{"id": b.id, "title": b.title, "author_id": b.author_id} for b in books],
        "test_user_count": len(test_users),
        "test_book_count": len(book_ids),
    }

    if dry_run:
        summary["message"] = (
            "Dry run — no rows deleted. Re-run with --execute and CONFIRM_CLEANUP_TEST_DATA=YES."
        )
        return summary

    if not test_users and not book_ids:
        summary["message"] = "No test data matched; nothing deleted."
        summary["success"] = True
        return summary

    try:
        for book in books:
            cleanup_book_files(book)

        if book_ids:
            purge_summary = purge_book_projects_by_ids(
                db,
                book_ids,
                commit=False,
                author_ids_for_sales_payouts=list(author_bp_ids) if author_bp_ids else None,
            )
            summary["book_purge"] = purge_summary

        user_results = []
        for user in test_users:
            user_results.append(delete_test_user(db, user.user_id, username=user.username))
        summary["users_deleted"] = user_results

        db.session.commit()
        summary["message"] = "Test data cleanup complete."
        summary["success"] = True
    except Exception as exc:
        db.session.rollback()
        logger.exception("Test data cleanup failed")
        summary["message"] = f"Cleanup failed: {exc}"
        summary["success"] = False
        raise

    return summary


def cleanup_user_by_username(db, username: str, *, dry_run: bool = True) -> Dict[str, Any]:
    """Convenience wrapper: purge everything for a single username (e.g. testuser)."""
    return cleanup_test_data(
        db,
        dry_run=dry_run,
        exact_usernames=(username.strip(),),
        username_prefixes=tuple(),
        email_markers=tuple(),
        extra_user_ids=set(),
    )
