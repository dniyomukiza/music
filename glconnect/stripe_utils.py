import os
from typing import Any, Dict, Optional, Tuple

import stripe
from flask import current_app


def init_stripe():
    """
    Initialize Stripe with the secret key from configuration or environment.
    This should be called lazily (on-demand) to avoid import-time issues.
    """
    secret_key = (
        getattr(current_app, "config", {}).get("STRIPE_SECRET_KEY")
        if hasattr(current_app, "config")
        else None
    ) or os.getenv("STRIPE_SECRET_KEY")

    if not secret_key:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")

    stripe.api_key = secret_key
    return stripe


def get_webhook_secret():
    """
    Get the Stripe webhook secret used to verify incoming webhook signatures.
    """
    return (
        getattr(current_app, "config", {}).get("STRIPE_WEBHOOK_SECRET")
        if hasattr(current_app, "config")
        else None
    ) or os.getenv("STRIPE_WEBHOOK_SECRET")


def stripe_connect_allow_platform_only() -> bool:
    """If true, book checkout proceeds without Connect (platform receives full charge). Dev-only."""
    return os.getenv("STRIPE_CONNECT_ALLOW_PLATFORM_ONLY", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def author_needs_stripe_payout_setup(bp_user) -> bool:
    """True when marketplace sales expect a Connect account but the author has none linked."""
    if stripe_connect_allow_platform_only():
        return False
    if not bp_user:
        return True
    acct = getattr(bp_user, "stripe_connect_account_id", None) or ""
    return not str(acct).strip()


def _book_list_base_price_for_purchase_type(book: Any, purchase_type: str) -> float:
    """List/base price for the format (matches BookSale logic in purchase_book)."""
    pt = (purchase_type or "digital").lower()
    if pt == "audiobook":
        return float(book.audiobook_price or book.price or 0)
    if pt == "bundle":
        return (float(book.price or 0) + float(book.audiobook_price or 0)) * 0.8
    return float(book.price or 0)


def marketplace_book_payment_intent_data(
    *,
    book: Any,
    purchase_type: str,
    payment_amount: float,
    stripe_connect_account_id: Optional[str],
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Build Stripe Checkout ``payment_intent_data`` for a marketplace book purchase
    (destination charge + application fee = platform share on list price only).

    Returns (payment_intent_data or None, user-facing error or None).
    """
    acct = (stripe_connect_account_id or "").strip()
    if not acct:
        if stripe_connect_allow_platform_only():
            return None, None
        return None, (
            "This title is not available for purchase yet because the author has not "
            "completed seller payout setup. Please try again later."
        )

    base = _book_list_base_price_for_purchase_type(book, purchase_type)
    platform_fee_usd = base * 0.3
    app_fee_cents = int(round(platform_fee_usd * 100))
    total_cents = int(round(float(payment_amount) * 100))
    if total_cents <= 0:
        return None, "Invalid payment amount."

    # Application fee must be strictly less than the PaymentIntent amount (Stripe).
    if app_fee_cents >= total_cents:
        app_fee_cents = max(0, total_cents - 1)

    data: Dict[str, Any] = {
        "application_fee_amount": app_fee_cents,
        "transfer_data": {"destination": acct},
        "metadata": {
            "book_id": str(book.id),
            "purchase_type": (purchase_type or "digital").lower(),
        },
    }
    return data, None

