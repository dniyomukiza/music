import logging
import os
from typing import Any, Dict, Optional, Tuple

import stripe
from flask import current_app

logger = logging.getLogger(__name__)


def init_stripe():
    """
    Initialize Stripe with the secret key from configuration or environment.
    This should be called lazily (on-demand) to avoid import-time issues.
    """
    secret_key = (
        (
            getattr(current_app, "config", {}).get("STRIPE_SECRET_KEY")
            if hasattr(current_app, "config")
            else None
        )
        or (
            getattr(current_app, "config", {}).get("STRIPE_API_KEY")
            if hasattr(current_app, "config")
            else None
        )
        or os.getenv("STRIPE_SECRET_KEY")
        or os.getenv("STRIPE_API_KEY")
    )

    if not secret_key:
        raise RuntimeError("Stripe is not configured (set STRIPE_SECRET_KEY or STRIPE_API_KEY)")

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


def stripe_secret_configured(app) -> bool:
    """
    True if a server-side Secret key (sk_...) is in config. Publishable (pk_...) does not count.
    """
    for key in (
        (app.config.get("STRIPE_SECRET_KEY") or "").strip(),
        (app.config.get("STRIPE_API_KEY") or "").strip(),
    ):
        if key.startswith("sk_"):
            return True
    return False


def describe_stripe_checkout_error(exc: BaseException) -> Dict[str, Any]:
    """
    Non-secret details for API responses and logs when Session.create or Stripe calls fail.
    """
    d: Dict[str, Any] = {"exception": type(exc).__name__}
    try:
        import stripe as stripe_mod

        if isinstance(exc, stripe_mod.error.StripeError):
            if getattr(exc, "http_status", None):
                d["http_status"] = exc.http_status
            if getattr(exc, "code", None):
                d["code"] = str(exc.code)
        jb = getattr(exc, "json_body", None) or {}
        if isinstance(jb, dict):
            err = jb.get("error") or {}
            if err.get("message"):
                d["message"] = str(err["message"])[:600]
            if err.get("type"):
                d["type"] = err["type"]
            if err.get("code") and "code" not in d:
                d["code"] = err["code"]
    except Exception:
        pass
    if "message" not in d:
        d["message"] = str(exc)[:600]
    return d


def purchase_checkout_unavailable_response(app, exc: Optional[BaseException] = None):
    """
    503 JSON when Stripe Checkout URL could not be created.
    Distinguishes missing/invalid key vs real Stripe API errors.
    """
    from flask import jsonify

    if not stripe_secret_configured(app):
        return (
            jsonify(
                {
                    "success": False,
                    "error": "No valid Stripe secret key (sk_...) in server configuration.",
                    "error_code": "STRIPE_KEY_MISSING",
                    "hint": "Set STRIPE_SECRET_KEY in the environment the app process actually loads, then restart. "
                    "If you use Docker, set env in compose or the host; .env on your laptop is not used by the server unless mounted.",
                }
            ),
            503,
        )
    if exc is not None:
        logger.exception("Stripe Checkout Session.create failed: %s", exc)
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Stripe did not create a checkout session. See 'details' and server logs.",
                    "error_code": "STRIPE_CHECKOUT_FAILED",
                    "details": describe_stripe_checkout_error(exc),
                }
            ),
            503,
        )
    return (
        jsonify(
            {
                "success": False,
                "error": "Checkout URL not available. Check server logs.",
                "error_code": "STRIPE_CHECKOUT_UNKNOWN",
            }
        ),
        503,
    )


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
    Build Stripe Checkout ``payment_intent_data`` for a marketplace book purchase.

    When the author has a Stripe Connect account id, uses a destination charge with
    ``application_fee_amount`` (platform share) and ``transfer_data.destination``.

    When there is no linked account, returns (None, None) so Checkout uses a normal
    charge to the platform; the buyer can complete payment and in-app sale records
    still attribute revenue to the author for later payout / Connect linking.

    Returns (payment_intent_data or None, user-facing error or None).
    """
    acct = (stripe_connect_account_id or "").strip()
    if not acct:
        logger.info(
            "Marketplace book checkout without Connect account (book_id=%s); "
            "using platform charge (no destination transfer).",
            getattr(book, "id", "?"),
        )
        return None, None

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

