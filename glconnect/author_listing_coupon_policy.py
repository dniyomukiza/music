"""
Author cross format listing coupons, earn by publishing one format, redeem when listing another.

Coupons reduce the platform fee on sales of the redeemed format only (not buyer price).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

LISTING_FORMAT_EBOOK = "ebook"
LISTING_FORMAT_AUDIOBOOK = "audiobook"
LISTING_FORMAT_PRINT = "print"
LISTING_FORMATS = frozenset({LISTING_FORMAT_EBOOK, LISTING_FORMAT_AUDIOBOOK, LISTING_FORMAT_PRINT})

COUPON_STATUS_AVAILABLE = "available"
COUPON_STATUS_REDEEMED = "redeemed"
COUPON_STATUS_EXPIRED = "expired"

# Default ebook/print platform maintenance fee (overridable via env)
BASE_PLATFORM_FEE_PERCENT = float(os.getenv("INK_BASE_PLATFORM_FEE_PERCENT", "10"))
COUPON_PLATFORM_FEE_PERCENT = float(os.getenv("INK_COUPON_PLATFORM_FEE_PERCENT", "5"))
MIN_PLATFORM_FEE_PERCENT = float(os.getenv("INK_MIN_PLATFORM_FEE_PERCENT", "3"))
COUPON_TTL_DAYS = int(os.getenv("INK_LISTING_COUPON_TTL_DAYS", "365"))

# Map marketplace purchase/sale format keys to listing fee override columns
PURCHASE_FORMAT_TO_LISTING = {
    "digital": LISTING_FORMAT_EBOOK,
    "audiobook": LISTING_FORMAT_AUDIOBOOK,
    "print": LISTING_FORMAT_PRINT,
    "bundle": None,  # flat bundle fee when 2+ formats
}


class ListingCouponError(Exception):
    """Invalid earn/redeem operation."""


def _aware_utc(dt: datetime | None) -> datetime | None:
    """Normalize DB datetimes (often naive UTC) for safe comparison."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_naive() -> datetime:
    """Naive UTC for SQLAlchemy filters on timezone-less DateTime columns."""
    return _utc_now().replace(tzinfo=None)


def _base_fee_ceiling_for_listing(listing_format: str) -> float:
    """Default platform maintenance fee % for a listing format (coupon cannot raise above this)."""
    from glconnect.platform_fee_policy import marketplace_platform_fee_percent_for

    if listing_format == LISTING_FORMAT_AUDIOBOOK:
        return marketplace_platform_fee_percent_for("audiobook")
    if listing_format == LISTING_FORMAT_PRINT:
        return marketplace_platform_fee_percent_for("print")
    if listing_format == LISTING_FORMAT_EBOOK:
        return marketplace_platform_fee_percent_for("digital")
    return BASE_PLATFORM_FEE_PERCENT


def _clamp_fee_percent(percent: float, ceiling: float | None = None) -> float:
    ceil = BASE_PLATFORM_FEE_PERCENT if ceiling is None else float(ceiling)
    return max(MIN_PLATFORM_FEE_PERCENT, min(ceil, float(percent)))


def _fee_override_attr(listing_format: str) -> str:
    return {
        LISTING_FORMAT_EBOOK: "platform_fee_percent_ebook",
        LISTING_FORMAT_AUDIOBOOK: "platform_fee_percent_audiobook",
        LISTING_FORMAT_PRINT: "platform_fee_percent_print",
    }.get(listing_format, "")


def _format_label(fmt: str) -> str:
    return {
        LISTING_FORMAT_EBOOK: "ebook",
        LISTING_FORMAT_AUDIOBOOK: "audiobook",
        LISTING_FORMAT_PRINT: "print",
    }.get(fmt, fmt)


def effective_platform_fee_percent(book: Any, purchase_or_listing_format: str) -> float:
    """
    Resolve platform maintenance fee % for a purchase/sale format on this book.

    Defaults: ebook/print 10%, audiobook 30%, bundle of 2+ formats 20%.
    Per-format coupon overrides may lower a single-format fee (floor MIN_PLATFORM_FEE_PERCENT).
    """
    from glconnect.platform_fee_policy import (
        MARKETPLACE_PLATFORM_FEE_PERCENT_BUNDLE,
        marketplace_platform_fee_percent_for,
    )

    fmt = (purchase_or_listing_format or "digital").lower().strip()
    if fmt.startswith("combo:") or fmt == "bundle":
        from glconnect.book_purchase_format import formats_from_purchase_format

        fmts = formats_from_purchase_format(fmt if fmt.startswith("combo:") else "bundle")
        if len(fmts) >= 2:
            return MARKETPLACE_PLATFORM_FEE_PERCENT_BUNDLE
        if len(fmts) == 1:
            return _purchase_key_fee_percent(book, fmts[0])
        return marketplace_platform_fee_percent_for("digital")

    listing_fmt = PURCHASE_FORMAT_TO_LISTING.get(fmt)
    if listing_fmt:
        return _single_format_fee_percent(book, listing_fmt)
    return marketplace_platform_fee_percent_for(fmt)


def _purchase_key_fee_percent(book: Any, purchase_key: str) -> float:
    listing_fmt = PURCHASE_FORMAT_TO_LISTING.get(purchase_key)
    if listing_fmt:
        return _single_format_fee_percent(book, listing_fmt)
    from glconnect.platform_fee_policy import marketplace_platform_fee_percent_for

    return marketplace_platform_fee_percent_for(purchase_key)


def _single_format_fee_percent(book: Any, listing_format: str) -> float:
    ceiling = _base_fee_ceiling_for_listing(listing_format)
    attr = _fee_override_attr(listing_format)
    if book and attr:
        override = getattr(book, attr, None)
        if override is not None:
            return _clamp_fee_percent(float(override), ceiling=ceiling)
    return ceiling


def _format_base_portions(book: Any, formats: List[str]) -> Dict[str, float]:
    """Base list-price portion per purchase format key (digital/audiobook/print)."""
    from glconnect.book_purchase_format import parse_selected_formats

    fmts = parse_selected_formats(formats)
    d = float(getattr(book, "price", None) or 0)
    a = float(getattr(book, "audiobook_price", None) or 0)
    p = float(getattr(book, "print_price", None) or 0)
    portions: Dict[str, float] = {}
    has_digital = "digital" in fmts
    has_audio = "audiobook" in fmts
    has_print = "print" in fmts

    if has_digital and has_audio:
        bundle_total = d + a
        if d + a > 0:
            portions["digital"] = bundle_total * (d / (d + a))
            portions["audiobook"] = bundle_total * (a / (d + a))
        else:
            portions["digital"] = 0.0
            portions["audiobook"] = 0.0
    else:
        if has_digital:
            portions["digital"] = d
        if has_audio:
            portions["audiobook"] = a
    if has_print:
        portions["print"] = p
    return portions


def royalty_fraction_for_fee_percent(platform_fee_percent: float) -> float:
    fee = max(0.0, min(100.0, float(platform_fee_percent)))
    return (100.0 - fee) / 100.0


def issue_coupon_on_format_publish(book: Any, earned_from_format: str) -> Optional[Any]:
    """
    Idempotently issue one coupon when a format is first published on a title.
    Returns the coupon row or None if already issued / invalid.
    """
    from glconnect import db
    from glconnect.book_platform_models import AuthorFormatListingCoupon

    fmt = (earned_from_format or "").lower().strip()
    if fmt not in LISTING_FORMATS or not book or not getattr(book, "id", None):
        return None

    existing = AuthorFormatListingCoupon.query.filter_by(
        book_project_id=book.id,
        earned_from_format=fmt,
    ).first()
    if existing:
        return existing

    now = _utc_now()
    coupon = AuthorFormatListingCoupon(
        author_id=book.author_id,
        book_project_id=book.id,
        earned_from_format=fmt,
        status=COUPON_STATUS_AVAILABLE,
        earned_at=now,
        expires_at=now + timedelta(days=COUPON_TTL_DAYS),
        platform_fee_percent_after=COUPON_PLATFORM_FEE_PERCENT,
    )
    db.session.add(coupon)
    db.session.flush()
    logger.info(
        "Issued listing coupon book=%s from=%s id=%s",
        book.id,
        fmt,
        coupon.id,
    )
    return coupon


def expire_stale_coupons_for_book(book_id: int) -> None:
    """Mark available coupons past expires_at as expired."""
    from glconnect import db
    from glconnect.book_platform_models import AuthorFormatListingCoupon

    now = _utc_now()
    rows = AuthorFormatListingCoupon.query.filter_by(
        book_project_id=book_id,
        status=COUPON_STATUS_AVAILABLE,
    ).all()
    for row in rows:
        if row.expires_at and _aware_utc(row.expires_at) < now:
            row.status = COUPON_STATUS_EXPIRED


def list_redeemable_coupons(book: Any, target_format: str) -> List[Any]:
    """Available cross format coupons for listing target_format on this book."""
    from glconnect.book_platform_models import AuthorFormatListingCoupon

    target = (target_format or "").lower().strip()
    if target not in LISTING_FORMATS or not book:
        return []

    expire_stale_coupons_for_book(book.id)
    now = _utc_now()
    rows = (
        AuthorFormatListingCoupon.query.filter_by(
            book_project_id=book.id,
            status=COUPON_STATUS_AVAILABLE,
        )
        .order_by(AuthorFormatListingCoupon.earned_at.asc())
        .all()
    )
    out = []
    for row in rows:
        if row.earned_from_format == target:
            continue
        if row.expires_at and _aware_utc(row.expires_at) < now:
            row.status = COUPON_STATUS_EXPIRED
            continue
        out.append(row)
    return out


def count_available_coupons_for_author(author_id: int) -> int:
    from glconnect.book_platform_models import AuthorFormatListingCoupon

    now = _utc_now_naive()
    return (
        AuthorFormatListingCoupon.query.filter_by(
            author_id=author_id,
            status=COUPON_STATUS_AVAILABLE,
        )
        .filter(
            (AuthorFormatListingCoupon.expires_at.is_(None))
            | (AuthorFormatListingCoupon.expires_at >= now)
        )
        .count()
    )


def coupons_summary_for_books(books: List[Any]) -> Dict[int, Dict[str, Any]]:
    """Per book_id: available count and next redeem hint."""
    from glconnect.book_platform_models import AuthorFormatListingCoupon

    if not books:
        return {}
    book_ids = [b.id for b in books]
    now = _utc_now_naive()
    rows = (
        AuthorFormatListingCoupon.query.filter(
            AuthorFormatListingCoupon.book_project_id.in_(book_ids),
            AuthorFormatListingCoupon.status == COUPON_STATUS_AVAILABLE,
        )
        .filter(
            (AuthorFormatListingCoupon.expires_at.is_(None))
            | (AuthorFormatListingCoupon.expires_at >= now)
        )
        .all()
    )
    by_book: Dict[int, List[Any]] = {}
    for row in rows:
        by_book.setdefault(row.book_project_id, []).append(row)

    summary: Dict[int, Dict[str, Any]] = {}
    for book in books:
        available = by_book.get(book.id, [])
        missing_formats = []
        if not getattr(book, "print_enabled", False):
            missing_formats.append(LISTING_FORMAT_PRINT)
        if not getattr(book, "audiobook_published", False):
            missing_formats.append(LISTING_FORMAT_AUDIOBOOK)
        if not getattr(book, "digital_book_published", False) and not (
            book.status.value == "published" if hasattr(getattr(book, "status", None), "value") else False
        ):
            missing_formats.append(LISTING_FORMAT_EBOOK)

        redeemable_for = []
        for mf in missing_formats:
            if any(c.earned_from_format != mf for c in available):
                redeemable_for.append(mf)

        summary[book.id] = {
            "available_count": len(available),
            "redeemable_for": redeemable_for,
            "coupons": available,
        }
    return summary


def redeem_coupon(coupon_id: int, book: Any, target_format: str) -> Any:
    """
    Consume coupon and set per-format platform fee override on the book.
    """
    from glconnect import db
    from glconnect.book_platform_models import AuthorFormatListingCoupon

    target = (target_format or "").lower().strip()
    if target not in LISTING_FORMATS:
        raise ListingCouponError("Invalid target format for coupon redemption.")

    coupon = AuthorFormatListingCoupon.query.get(coupon_id)
    if not coupon or coupon.book_project_id != book.id:
        raise ListingCouponError("Coupon not found for this title.")
    if coupon.status != COUPON_STATUS_AVAILABLE:
        raise ListingCouponError("This coupon is no longer available.")
    if coupon.earned_from_format == target:
        raise ListingCouponError(
            f"Use a coupon earned from a different format (not {_format_label(target)})."
        )

    now = _utc_now()
    if coupon.expires_at and _aware_utc(coupon.expires_at) < now:
        coupon.status = COUPON_STATUS_EXPIRED
        db.session.flush()
        raise ListingCouponError("This coupon has expired.")

    fee_after = _clamp_fee_percent(
        float(coupon.platform_fee_percent_after or COUPON_PLATFORM_FEE_PERCENT),
        ceiling=_base_fee_ceiling_for_listing(target),
    )
    attr = _fee_override_attr(target)
    if not attr:
        raise ListingCouponError("Could not apply coupon to this format.")

    setattr(book, attr, fee_after)
    coupon.status = COUPON_STATUS_REDEEMED
    coupon.redeemed_at = now
    coupon.redeemed_for_format = target
    db.session.flush()
    logger.info(
        "Redeemed coupon %s for book=%s target=%s fee=%s%%",
        coupon.id,
        book.id,
        target,
        fee_after,
    )
    return coupon


def try_redeem_coupon_from_form(book: Any, target_format: str, form_data: Any) -> Optional[str]:
    """
    If listing_coupon_id present in form, redeem it. Returns error message or None.
    """
    raw = None
    if form_data is not None:
        if hasattr(form_data, "get"):
            raw = form_data.get("listing_coupon_id")
        else:
            raw = getattr(form_data, "listing_coupon_id", None)
    if raw in (None, "", "0", 0):
        return None
    try:
        coupon_id = int(raw)
    except (TypeError, ValueError):
        return "Invalid coupon selection."
    try:
        redeem_coupon(coupon_id, book, target_format)
    except ListingCouponError as exc:
        return str(exc)
    return None
