"""Shared purchase-format pricing for marketplace checkout and sales."""

from typing import Any, Tuple


def normalize_purchase_format(purchase_format: str) -> str:
    pt = (purchase_format or "digital").lower().strip()
    if pt in ("digital", "audiobook", "bundle", "print"):
        return pt
    return "digital"


def print_listed(book: Any) -> bool:
    return bool(
        book
        and getattr(book, "print_enabled", False)
        and (getattr(book, "print_price", None) or 0) > 0
    )


def print_shipping_amount(book: Any) -> float:
    return max(0.0, float(getattr(book, "print_shipping_price", None) or 0))


def base_price_for_format(book: Any, purchase_format: str) -> float:
    """Book list price for the format (excludes shipping for print)."""
    pt = normalize_purchase_format(purchase_format)
    if pt == "audiobook":
        return float(getattr(book, "audiobook_price", None) or getattr(book, "price", None) or 0)
    if pt == "bundle":
        digital = float(getattr(book, "price", None) or 0)
        audio = float(getattr(book, "audiobook_price", None) or 0)
        return (digital + audio) * 0.8
    if pt == "print":
        return float(getattr(book, "print_price", None) or 0)
    return float(getattr(book, "price", None) or 0)


def total_checkout_amount(book: Any, purchase_format: str) -> float:
    """Total charged at checkout (print includes flat shipping)."""
    base = base_price_for_format(book, purchase_format)
    if normalize_purchase_format(purchase_format) == "print":
        return base + print_shipping_amount(book)
    return base


def revenue_split_for_purchase(
    book: Any, purchase_format: str, purchase_amount: float, royalty_percentage: float = 0.7
) -> Tuple[float, float, float, float]:
    """
    Returns (base_price, extra_amount, royalty_amount, platform_fee).
    Extra amount (e.g. shipping, tip) goes 100% to author; platform fee only on base list.
    """
    base_price = base_price_for_format(book, purchase_format)
    extra_amount = max(0.0, float(purchase_amount) - base_price)
    base_royalty = base_price * royalty_percentage
    base_platform_fee = base_price - base_royalty
    royalty_amount = base_royalty + extra_amount
    platform_fee = base_platform_fee
    return base_price, extra_amount, royalty_amount, platform_fee


# Stripe Checkout shipping_address_collection allowed_countries (common markets)
STRIPE_PRINT_SHIPPING_COUNTRIES = [
    "US", "CA", "GB", "AU", "NZ", "IE", "FR", "DE", "IT", "ES", "NL", "BE", "SE", "NO", "DK", "FI",
    "CH", "AT", "PT", "PL", "ZA", "IN", "SG", "HK", "JP", "MX", "BR",
]
