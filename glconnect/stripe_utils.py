import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import stripe
from flask import current_app

logger = logging.getLogger(__name__)


def init_stripe():
    """
    Initialize Stripe with the secret key from configuration or environment.
    This should be called lazily (on-demand) to avoid import-time issues.
    """
    from flask import has_app_context, current_app

    if has_app_context():
        sk = get_stripe_server_secret_key(current_app)
    else:
        sk = get_stripe_server_secret_key(None)
    if not sk:
        raise RuntimeError("Stripe is not configured (set STRIPE_SECRET_KEY or STRIPE_API_KEY)")

    stripe.api_key = sk
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
    """True when the author must still complete Stripe Connect (no acct, or onboarding incomplete).

    If we cannot **verify** completion with Stripe, we treat payout setup as required and keep
    redirecting authors to onboarding, never assume "done" on errors or missing data.
    """
    if stripe_connect_allow_platform_only():
        return False
    if not bp_user:
        return True
    acct_id = str(getattr(bp_user, "stripe_connect_account_id", None) or "").strip()
    if not acct_id:
        return True
    try:
        init_stripe()
        acc = stripe.Account.retrieve(acct_id)
        ready = bool(
            getattr(acc, "charges_enabled", False)
            and getattr(acc, "details_submitted", False)
        )
        return not ready
    except stripe.error.InvalidRequestError as e:
        logger.warning(
            "Stripe Connect account id invalid or inaccessible (acct=%s): %s",
            acct_id,
            e,
        )
        return True
    except Exception as e:
        logger.warning(
            "Could not verify Stripe Connect completion (acct=%s); requiring payout setup: %s",
            acct_id,
            e,
        )
        return True


def checkout_ready_author_connect_id(author) -> str:
    """Use Connect for Checkout only when onboarding is complete (charges_enabled + details_submitted)."""
    if not author:
        return ""
    raw = str(getattr(author, "stripe_connect_account_id", None) or "").strip()
    if not raw or author_needs_stripe_payout_setup(author):
        return ""
    return raw


def normalize_stripe_secret_candidate(val: Optional[str]) -> str:
    """Strip whitespace, UTF-8 BOM, and a single layer of surrounding quotes (common in dashboards)."""
    if not val or not isinstance(val, str):
        return ""
    s = val.strip()
    s = s.lstrip("\ufeff")
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        s = s[1:-1].strip()
    return s


# Config keys (from create_app) then extra env-only aliases some hosts / docs use.
_STRIPE_CONFIG_KEYS = ("STRIPE_SECRET_KEY", "STRIPE_API_KEY")
_STRIPE_ENV_KEYS = (
    "STRIPE_SECRET_KEY",
    "STRIPE_API_KEY",
    "STRIPE_KEY",
    "STRIPE_PRIVATE_KEY",
)


def get_stripe_server_secret_key(app) -> Optional[str]:
    """
    Return the first valid Stripe **Secret** key (sk_...) for server API calls.
    Checks Flask `app.config` and then `os.environ` (Docker/systemd/Render set vars here even if
    `create_app` read empty, e.g. .env not found on the server but `env` was injected at boot).
    Never returns a publishable (pk_...) key.
    """
    if app is not None and hasattr(app, "config"):
        for name in _STRIPE_CONFIG_KEYS:
            k = normalize_stripe_secret_candidate(app.config.get(name))
            if k.startswith("sk_"):
                return k
    for name in _STRIPE_ENV_KEYS:
        k = normalize_stripe_secret_candidate(os.getenv(name))
        if k.startswith("sk_"):
            return k
    return None


def stripe_secret_configured(app) -> bool:
    """True if a valid sk_... is available via get_stripe_server_secret_key."""
    return get_stripe_server_secret_key(app) is not None


def process_env_has_stripe_secret() -> bool:
    """True if any known Stripe env var in os.environ normalizes to sk_... (for diagnostics)."""
    for name in _STRIPE_ENV_KEYS:
        k = normalize_stripe_secret_candidate(os.getenv(name))
        if k.startswith("sk_"):
            return True
    return False


def describe_stripe_checkout_error(
    exc: BaseException,
    *,
    stripe_connect_account_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Non-secret details for API responses and logs when Session.create or Stripe calls fail.

    When marketplace checkout uses Connect (direct charge), Stripe often enforces business
    profile on the **connected account**, not only the platform.
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

    msg = (d.get("message") or "").lower()
    # Stripe blocks Checkout until the account that hosts the session has a display/business name.
    if "account or business name" in msg or (
        "checkout" in msg and "business name" in msg and "dashboard.stripe.com" in msg
    ):
        acct = (stripe_connect_account_id or "").strip()
        if acct:
            d["checkout_on"] = "connected_account"
            d["hint"] = (
                "Checkout runs on the author's Stripe Connect account. A public business name is usually "
                "collected in Stripe Express onboarding (Ink Studio → Payout account → continue to Stripe). "
                "If the author skipped steps or closed onboarding early, the account can still be incomplete, "
                "they should complete payout setup again, or you open Dashboard → Connect → Accounts → that "
                "seller → Business settings. https://dashboard.stripe.com/connect/accounts"
            )
        else:
            d["checkout_on"] = "platform"
            d["hint"] = (
                "Open https://dashboard.stripe.com/settings/account (Settings → Business / Account details) "
                "and set your platform business or account name; complete any onboarding prompts."
            )
        d["operator_error_code"] = "STRIPE_BUSINESS_NAME_REQUIRED"
        d["patron_message"] = (
            "Checkout is not ready for this book's seller. "
            "The author must complete Stripe payout setup, then try again."
        )

    if "does not allow requests from your ip" in msg or (
        "ip address" in msg and "api key" in msg
    ):
        d["operator_error_code"] = "STRIPE_KEY_IP_RESTRICTED"
        d["hint"] = (
            "Stripe rejected this request because the server's outbound IP is not on the "
            "secret key's IP allowlist. Open Stripe Dashboard → Developers → API keys → "
            "your secret key → Manage IP restrictions, and add the app's outbound IP "
            "(not the public website URL). Use GET /mybook/admin/stripe-diagnostics as admin "
            "to see outbound_ip on this host. "
            "https://docs.stripe.com/keys#limit-api-secret-keys-ip-address"
        )
        d["patron_message"] = (
            "Payment could not be started due to a server configuration issue. "
            "Please try again later or contact the site operator."
        )

    if "custom_fields" in msg and "maximum_length" in msg:
        d["operator_error_code"] = "STRIPE_CHECKOUT_CUSTOM_FIELDS"
        d["patron_message"] = (
            "Payment could not be started. Please try again or contact support."
        )

    return d


def detect_server_outbound_ip(timeout: float = 5.0) -> Optional[str]:
    """
    Best-effort public IPv4/IPv6 seen by the internet when this host calls outbound HTTPS.
    Use this value in Stripe secret key IP allowlists (Render egress ≠ inbound glc.cool IP).
    """
    import urllib.request

    for url in (
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
        "https://checkip.amazonaws.com",
    ):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "InkStudio-StripeDiagnostics/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                ip = (resp.read() or b"").decode("utf-8", errors="ignore").strip()
                if ip and len(ip) <= 45:
                    return ip
        except Exception as exc:
            logger.debug("Outbound IP lookup failed via %s: %s", url, exc)
    return None


def probe_stripe_server_key(app) -> Dict[str, Any]:
    """
    Lightweight Stripe API call to verify the configured secret key works from this host
    (including IP allowlist). No secrets returned.
    """
    sk = get_stripe_server_secret_key(app)
    if not sk:
        return {"ok": False, "reason": "no_secret_key"}
    try:
        import stripe as stripe_mod

        stripe_mod.api_key = sk
        stripe_mod.Balance.retrieve()
        return {"ok": True}
    except Exception as exc:
        return {
            "ok": False,
            "reason": "stripe_api_error",
            "details": describe_stripe_checkout_error(exc),
        }


def purchase_checkout_unavailable_response(
    app,
    exc: Optional[BaseException] = None,
    *,
    stripe_connect_account_id: Optional[str] = None,
):
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
                    "hint": "Set a Stripe *secret* key (starts with sk_) in the server environment: "
                    "STRIPE_SECRET_KEY, STRIPE_API_KEY, STRIPE_KEY, or STRIPE_PRIVATE_KEY, then restart the app. "
                    "Use Dashboard → Developers → API keys → Secret key (not the publishable pk_). "
                    "If you use Docker, set env in compose or the host; a local .env is not used unless mounted.",
                }
            ),
            503,
        )
    if exc is not None:
        acct = (stripe_connect_account_id or "").strip()
        if acct:
            logger.error(
                "Stripe Checkout Session.create failed (stripe_account=%s): %s",
                acct,
                exc,
                exc_info=True,
            )
        else:
            logger.exception("Stripe Checkout Session.create failed (platform charge): %s", exc)
        details = describe_stripe_checkout_error(
            exc, stripe_connect_account_id=stripe_connect_account_id
        )
        patron_msg = details.get("patron_message")
        payload = {
            "success": False,
            "error": patron_msg or (
                "Payment could not be started. Please try again later or contact the site operator."
            ),
            "error_code": details.get("operator_error_code") or "STRIPE_CHECKOUT_FAILED",
            "details": details,
        }
        # #region agent log
        if os.getenv("DEBUG_AGENT_LOG", "").strip().lower() in ("1", "true", "yes", "on"):
            try:
                import json as _json
                import os as _os
                from datetime import datetime, timezone as _tz
                _log_path = _os.path.join(
                    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                    ".cursor",
                    "debug-fe2ff6.log",
                )
                with open(_log_path, "a", encoding="utf-8") as _fh:
                    _fh.write(_json.dumps({
                        "sessionId": "fe2ff6",
                        "runId": "pre-fix",
                        "hypothesisId": "H1,H2,H4,H5",
                        "location": "stripe_utils.py:purchase_checkout_unavailable_response",
                        "message": "checkout unavailable response",
                        "data": {
                            "error_code": payload["error_code"],
                            "operator_error_code": details.get("operator_error_code"),
                            "stripe_message": (details.get("message") or "")[:300],
                            "connect_account_set": bool((stripe_connect_account_id or "").strip()),
                            "stripe_configured": stripe_secret_configured(app),
                        },
                        "timestamp": int(datetime.now(_tz.utc).timestamp() * 1000),
                    }, default=str) + "\n")
            except Exception:
                pass
        # #endregion
        if details.get("hint"):
            payload["hint"] = details["hint"]
        if details.get("operator_error_code"):
            payload["operator_error_code"] = details["operator_error_code"]
        return jsonify(payload), 503
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


# Presentment currencies Stripe documents for Amazon Pay (lowercase ISO codes).
_AMAZON_PAY_CURRENCIES = frozenset(
    ("aud", "gbp", "dkk", "eur", "hkd", "jpy", "nzd", "nok", "zar", "sek", "chf", "usd")
)


def checkout_payment_method_types_for_currency(currency: Optional[str]) -> List[str]:
    """
    Payment methods to pass to Checkout Session.create.

    - ``card``: cards plus Apple Pay / Google Pay wallet buttons when the Dashboard,
      domain registration, and customer device allow them (not separate API types).
    - ``amazon_pay``: when the session currency is one Stripe supports for Amazon Pay.
    - ``cashapp``: USD only (Cash App Pay presentment currency).
    """
    cur = (currency or "usd").strip().lower()
    types: List[str] = ["card"]
    if cur in _AMAZON_PAY_CURRENCIES:
        types.append("amazon_pay")
    if cur == "usd":
        types.append("cashapp")
    return types


def checkout_customer_email_for_user(user: Any) -> Optional[str]:
    """Email to pass as Checkout ``customer_email`` so Stripe prefills contact (hosted Checkout)."""
    if user is None:
        return None
    email = getattr(user, "email", None)
    if not email or not isinstance(email, str):
        return None
    e = email.strip()
    return e if e else None


def _book_list_base_price_for_purchase_type(book: Any, purchase_type: str) -> float:
    """List/base price for the format (matches BookSale logic in purchase_book)."""
    from glconnect.book_purchase_format import base_price_for_format

    return base_price_for_format(book, purchase_type)


def marketplace_book_payment_intent_data(
    *,
    book: Any,
    purchase_type: str,
    payment_amount: float,
    stripe_connect_account_id: Optional[str],
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Build Stripe Checkout ``payment_intent_data`` for a marketplace book purchase.

    When the author has a Stripe Connect account, uses a **direct charge** on that
    account: ``application_fee_amount`` only (platform share). The caller must
    create the Checkout Session with ``stripe_account=<author acct id>`` so the
    charge settles on the connected account, receipts and Checkout show the
    **author’s** Stripe business profile, not the platform’s.

    When there is no linked account, returns (None, None) so Checkout uses a normal
    charge to the platform.

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
    from glconnect.book_purchase_format import revenue_split_for_purchase

    _, _, _, platform_fee_usd, _ = revenue_split_for_purchase(book, purchase_type, base)
    app_fee_cents = int(round(platform_fee_usd * 100))
    total_cents = int(round(float(payment_amount) * 100))
    if total_cents <= 0:
        return None, "Invalid payment amount."

    # Application fee must be strictly less than the PaymentIntent amount (Stripe).
    if app_fee_cents >= total_cents:
        app_fee_cents = max(0, total_cents - 1)

    # Direct charge on connected account: no transfer_data (caller passes stripe_account
    # to Session.create). Platform fee via application_fee_amount only.
    data: Dict[str, Any] = {
        "application_fee_amount": app_fee_cents,
        "metadata": {
            "book_id": str(book.id),
            "purchase_type": (purchase_type or "digital").lower(),
        },
    }
    return data, None


def stripe_print_checkout_custom_fields() -> List[Dict[str, Any]]:
    """Optional apartment and delivery note fields on Stripe Checkout (print shipping)."""
    # Stripe text custom_fields allow maximum_length up to 255 only.
    return [
        {
            "key": "shipping_apt",
            "label": {"type": "custom", "custom": "Apartment, suite, unit (optional)"},
            "type": "text",
            "optional": True,
            "text": {"maximum_length": 100},
        },
        {
            "key": "shipping_note",
            "label": {"type": "custom", "custom": "Note for the author (optional)"},
            "type": "text",
            "optional": True,
            "text": {"maximum_length": 255},
        },
    ]


def print_checkout_shipping_kw() -> Dict[str, Any]:
    """Extra Stripe Checkout kwargs when collecting a print shipping address."""
    return {"custom_fields": stripe_print_checkout_custom_fields()}


def create_marketplace_checkout_session(
    checkout_kw: Dict[str, Any],
    *,
    purchase_type: str,
    book_id: Optional[int] = None,
):
    """
    Create Stripe Checkout session for marketplace purchase.
    If print custom_fields are rejected, retry without them (shipping still collected).
    """
    from glconnect.book_purchase_format import purchase_grants_format

    init_stripe()
    import stripe as stripe_mod

    try:
        return stripe_mod.checkout.Session.create(**checkout_kw)
    except Exception as exc:
        if not purchase_grants_format(purchase_type, "print") or not checkout_kw.get("custom_fields"):
            raise
        retry_kw = {k: v for k, v in checkout_kw.items() if k != "custom_fields"}
        logger.warning(
            "Stripe Checkout custom_fields rejected for book %s; retrying without them: %s",
            book_id,
            exc,
        )
        return stripe_mod.checkout.Session.create(**retry_kw)


def stripe_checkout_custom_field_values(session: Any) -> Dict[str, str]:
    """Extract completed Stripe Checkout custom field values by key."""
    if session is None:
        return {}
    if hasattr(session, "to_dict"):
        try:
            session = session.to_dict()
        except Exception:
            session = {}
    elif not isinstance(session, dict):
        session = {}

    out: Dict[str, str] = {}
    for cf in session.get("custom_fields") or []:
        if not isinstance(cf, dict):
            continue
        key = cf.get("key")
        text = cf.get("text")
        val = ""
        if isinstance(text, dict):
            val = (text.get("value") or "").strip()
        if key and val:
            out[str(key)] = val
    return out


def merge_print_shipping_line2(
    address_line2: Optional[str], apt: Optional[str]
) -> Optional[str]:
    """Combine Stripe address line2 with the apartment custom field."""
    line2 = (address_line2 or "").strip()
    unit = (apt or "").strip()
    if line2 and unit:
        merged = f"{line2}, {unit}"
    else:
        merged = unit or line2
    merged = merged[:200]
    return merged or None

