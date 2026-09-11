"""Shared purchase-format pricing for marketplace checkout and sales."""

from typing import Any, Iterable, List, Tuple

ALLOWED_PURCHASE_FORMATS = frozenset({"digital", "audiobook", "print", "bundle"})


def normalize_purchase_format(purchase_format: str) -> str:
    pt = (purchase_format or "digital").lower().strip()
    if pt.startswith("combo:"):
        return pt
    if pt in ALLOWED_PURCHASE_FORMATS:
        return pt
    return "digital"


def parse_selected_formats(
    raw_formats: Iterable[str] | None = None,
    purchase_type: str | None = None,
) -> List[str]:
    """Normalize client format selection to a sorted unique list."""
    allowed = {"digital", "audiobook", "print"}
    if raw_formats:
        out = sorted(
            {
                str(x).lower().strip()
                for x in raw_formats
                if str(x).lower().strip() in allowed
            }
        )
        if out:
            return out
    pt = (purchase_type or "digital").lower().strip()
    if pt == "bundle":
        return ["audiobook", "digital"]
    if pt.startswith("combo:"):
        tail = pt.split(":", 1)[1]
        return sorted({p for p in tail.split(",") if p in allowed})
    if pt in allowed:
        return [pt]
    return []


def purchase_format_key(formats: List[str]) -> str:
    """Persistable purchase_format value for the selected formats."""
    fmts = parse_selected_formats(formats)
    if not fmts:
        return "digital"
    if len(fmts) == 1:
        return fmts[0]
    if len(fmts) == 2 and "digital" in fmts and "audiobook" in fmts:
        return "bundle"
    return "combo:" + ",".join(fmts)


def formats_from_purchase_format(purchase_format: str | None) -> List[str]:
    key = normalize_purchase_format(purchase_format or "digital")
    if key == "bundle":
        return ["audiobook", "digital"]
    if key.startswith("combo:"):
        return parse_selected_formats(key.split(":", 1)[1].split(","))
    if key in {"digital", "audiobook", "print"}:
        return [key]
    return ["digital"]


def purchase_grants_format(purchase_format: str | None, fmt: str) -> bool:
    return fmt in formats_from_purchase_format(purchase_format)


def print_listed(book: Any) -> bool:
    return bool(
        book
        and getattr(book, "print_enabled", False)
        and (getattr(book, "print_price", None) or 0) > 0
    )


def _audiobook_listed(book: Any) -> bool:
    return bool(
        book
        and getattr(book, "audiobook_published", False)
        and getattr(book, "has_audiobook", False)
    )


def audiobook_listed(book: Any) -> bool:
    """Public alias for marketplace and purchase checks."""
    return _audiobook_listed(book)


def marketplace_listed_format_amounts(book: Any) -> List[float]:
    """
    Explicit list prices for each marketplace format (0.0 = author set free).
    Formats with unset price (None) are omitted — unset is not free.
    Print is included only when print_listed (price > 0).
    """
    amounts: List[float] = []
    if ebook_listed(book):
        digital_price = getattr(book, "price", None)
        if digital_price is not None:
            amounts.append(float(digital_price))
    if _audiobook_listed(book):
        audio_price = getattr(book, "audiobook_price", None)
        if audio_price is not None:
            amounts.append(float(audio_price))
    if print_listed(book):
        amounts.append(float(getattr(book, "print_price", None) or 0))
    return amounts


def marketplace_is_explicitly_free(book: Any) -> bool:
    """True only when every listed format with a set price is exactly 0."""
    amounts = marketplace_listed_format_amounts(book)
    return bool(amounts) and all(a == 0 for a in amounts)


def marketplace_min_paid_price(book: Any) -> float | None:
    paid = [a for a in marketplace_listed_format_amounts(book) if a > 0]
    return min(paid) if paid else None


def marketplace_card_price_label(book: Any) -> str:
    """
    Short label for marketplace cards.
    Never shows Free unless the author explicitly set all listed format prices to 0.
    """
    amounts = marketplace_listed_format_amounts(book)
    paid = [a for a in amounts if a > 0]
    if paid:
        low = min(paid)
        free_formats = [a for a in amounts if a == 0]
        if len(paid) > 1 or free_formats:
            return f"From ${low:.2f}"
        return f"${low:.2f}"
    if amounts and all(a == 0 for a in amounts):
        return "Free"
    return ""


def _marketplace_stats_row_as_book(row: Any) -> Any:
    """Adapt a slim SQLAlchemy row for marketplace pricing helpers."""

    class _RowBook:
        pass

    book = _RowBook()
    for attr in (
        "id",
        "price",
        "digital_book_published",
        "digital_file_path",
        "audiobook_published",
        "has_audiobook",
        "audiobook_price",
        "print_enabled",
        "print_price",
        "status",
    ):
        setattr(book, attr, getattr(row, attr, None))
    book.chapters = None
    return book


def ebook_listed(book: Any) -> bool:
    """True when digital ebook is offered on the marketplace (not merely price unset)."""
    if not book:
        return False
    if getattr(book, "digital_book_published", False) and getattr(book, "digital_file_path", None):
        return True
    from glconnect.book_platform_models import BookStatus

    if book.status == BookStatus.PUBLISHED and not getattr(book, "digital_file_path", None):
        chapters = getattr(book, "chapters", None)
        if chapters is not None:
            return len(chapters) > 0
        from glconnect.book_platform_models import BookChapter
        from glconnect import db

        return (
            db.session.query(BookChapter.id)
            .filter_by(book_project_id=book.id)
            .limit(1)
            .first()
            is not None
        )
    return False


def marketplace_buyable(book: Any) -> bool:
    """True when at least one marketplace format can be purchased."""
    return bool(ebook_listed(book) or _audiobook_listed(book) or print_listed(book))


def print_shipping_amount(book: Any) -> float:
    return max(0.0, float(getattr(book, "print_shipping_price", None) or 0))


def base_price_for_format(book: Any, purchase_format: str) -> float:
    """Book list price for the format (excludes shipping for print)."""
    pt = normalize_purchase_format(purchase_format)
    if pt.startswith("combo:"):
        return combo_base_price(book, formats_from_purchase_format(pt))
    if pt == "audiobook":
        return float(getattr(book, "audiobook_price", None) or getattr(book, "price", None) or 0)
    if pt == "bundle":
        digital = float(getattr(book, "price", None) or 0)
        audio = float(getattr(book, "audiobook_price", None) or 0)
        return digital + audio
    if pt == "print":
        return float(getattr(book, "print_price", None) or 0)
    return float(getattr(book, "price", None) or 0)


def combo_base_price(book: Any, formats: Iterable[str]) -> float:
    """Subtotal for selected formats (ebook + audiobook use their combined prices)."""
    fmts = parse_selected_formats(formats)
    total = 0.0
    has_digital = "digital" in fmts
    has_audio = "audiobook" in fmts
    if has_digital and has_audio:
        total += base_price_for_format(book, "bundle")
    else:
        if has_digital:
            total += base_price_for_format(book, "digital")
        if has_audio:
            total += base_price_for_format(book, "audiobook")
    if "print" in fmts:
        total += base_price_for_format(book, "print")
    return total


def total_for_formats(book: Any, formats: Iterable[str]) -> float:
    """Checkout total for a format selection (includes print shipping when applicable)."""
    fmts = parse_selected_formats(formats)
    total = combo_base_price(book, fmts)
    if "print" in fmts:
        total += print_shipping_amount(book)
    return total


def total_checkout_amount(book: Any, purchase_format: str) -> float:
    """Total charged at checkout (print includes flat shipping)."""
    pt = normalize_purchase_format(purchase_format)
    if pt.startswith("combo:"):
        return total_for_formats(book, formats_from_purchase_format(pt))
    base = base_price_for_format(book, pt)
    if pt == "print":
        return base + print_shipping_amount(book)
    return base


def revenue_split_for_purchase(
    book: Any,
    purchase_format: str,
    purchase_amount: float,
    royalty_percentage: float | None = None,
) -> Tuple[float, float, float, float, float]:
    """
    Returns (base_price, extra_amount, royalty_amount, platform_fee, platform_fee_percent_applied).
    Extra amount (e.g. shipping, tip) goes 100% to author; platform fee only on base list portions.

    Author royalties (list price): ebook/print 90%, audiobook 70%, bundle of 2+ 80%.
    Remainder is platform maintenance. Coupon overrides may lower single-format fees.
    """
    from glconnect.author_listing_coupon_policy import (
        effective_platform_fee_percent,
        royalty_fraction_for_fee_percent,
    )

    pt = normalize_purchase_format(purchase_format)
    base_price = base_price_for_format(book, pt)
    extra_amount = max(0.0, float(purchase_amount) - base_price)

    if pt.startswith("combo:") or pt == "bundle":
        fmts = formats_from_purchase_format(pt)
        if len(fmts) >= 2:
            # Flat 20% platform / 80% author on the combo list-price base
            fee_pct_applied = effective_platform_fee_percent(book, pt)
            royalty_fraction = royalty_fraction_for_fee_percent(fee_pct_applied)
            base_royalty = base_price * royalty_fraction
            platform_fee = base_price - base_royalty
        elif len(fmts) == 1:
            fee_pct_applied = effective_platform_fee_percent(book, fmts[0])
            if royalty_percentage is None:
                royalty_fraction = royalty_fraction_for_fee_percent(fee_pct_applied)
            else:
                royalty_fraction = float(royalty_percentage)
            base_royalty = base_price * royalty_fraction
            platform_fee = base_price - base_royalty
        else:
            fee_pct_applied = effective_platform_fee_percent(book, "digital")
            base_royalty = 0.0
            platform_fee = 0.0
    else:
        fee_pct_applied = effective_platform_fee_percent(book, pt)
        if royalty_percentage is None:
            royalty_fraction = royalty_fraction_for_fee_percent(fee_pct_applied)
        else:
            royalty_fraction = float(royalty_percentage)
        base_royalty = base_price * royalty_fraction
        platform_fee = base_price - base_royalty

    royalty_amount = base_royalty + extra_amount
    return base_price, extra_amount, royalty_amount, platform_fee, fee_pct_applied


def revenue_split_legacy_tuple(
    book: Any, purchase_format: str, purchase_amount: float, royalty_percentage: float | None = None
) -> Tuple[float, float, float, float]:
    """Backward-compatible 4-tuple return (without fee percent)."""
    base, extra, royalty, platform, _ = revenue_split_for_purchase(
        book, purchase_format, purchase_amount, royalty_percentage
    )
    return base, extra, royalty, platform


# Stripe Checkout shipping_address_collection allowed_countries (print only).
# US-only at launch; expand STRIPE_PRINT_SHIPPING_COUNTRIES when demand warrants.
STRIPE_PRINT_SHIPPING_COUNTRIES = [
    "US",
]
