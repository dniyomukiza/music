"""Account signup Terms of Service and Privacy acknowledgment (all users)."""

from datetime import datetime, timezone
from typing import Any, Optional

ACCOUNT_TERMS_VERSION = "1.1"


def _as_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def validate_account_signup_terms(payload: Any) -> Optional[str]:
    """
    Validate signup / quick-register terms checkboxes.
    Returns an error message, or None if valid.
    """
    if payload is None:
        payload = {}

    # Keep these legally distinct. A client-controlled "accept all" flag must
    # not be able to bypass the separate privacy acknowledgment or age check.
    # This is intentionally fail-closed for crafted JSON/form submissions.
    compact = _as_bool(payload.get("account_signup_accept_all"))
    terms_ok = compact or _as_bool(payload.get("account_terms_accept"))
    privacy_ok = _as_bool(payload.get("account_privacy_ack"))
    age_ok = _as_bool(payload.get("account_age_confirm"))

    if not terms_ok:
        return "Please accept the Account Terms of Service to create an account."
    if not privacy_ok:
        return "Please acknowledge the Privacy Policy and data practices."
    if not age_ok:
        return "Please confirm you are at least 18 years old (or the age of majority where you live)."
    return None


def record_account_terms_acceptance(user: Any) -> None:
    """Persist account-level terms acceptance on User."""
    user.account_terms_version = ACCOUNT_TERMS_VERSION
    user.account_terms_accepted_at = datetime.now(timezone.utc)


def account_terms_context() -> dict:
    return {"account_terms_version": ACCOUNT_TERMS_VERSION}
