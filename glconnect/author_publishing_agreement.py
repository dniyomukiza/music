"""Author Publishing Agreement, version constants and acceptance helpers."""

from datetime import datetime, timezone
from typing import Any, Optional, Tuple


# Bump when account level agreement text changes materially; authors must re-accept.
AUTHOR_PUBLISHING_AGREEMENT_VERSION = "1.0"

# Bump when per-listing attestation text changes materially.
LISTING_ATTESTATION_VERSION = "1.0"


def _as_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def author_has_accepted_agreement(bp_user: Any) -> bool:
    """True if author accepted the current account level publishing agreement."""
    if not bp_user:
        return False
    version = getattr(bp_user, "author_agreement_version", None)
    accepted_at = getattr(bp_user, "author_agreement_accepted_at", None)
    return (
        version == AUTHOR_PUBLISHING_AGREEMENT_VERSION
        and accepted_at is not None
    )


def author_requires_publishing_agreement(user_id: int, bp_user: Any = None) -> bool:
    """True until the author accepts the current account level agreement."""
    if bp_user is None:
        from glconnect.book_platform_models import BookPlatformUser

        bp_user = BookPlatformUser.query.filter_by(user_id=user_id).first()
    return not author_has_accepted_agreement(bp_user)


def record_author_agreement_acceptance(bp_user: Any) -> None:
    """Persist account level agreement acceptance for the current version."""
    bp_user.author_agreement_version = AUTHOR_PUBLISHING_AGREEMENT_VERSION
    bp_user.author_agreement_accepted_at = datetime.now(timezone.utc)


def validate_listing_terms_payload(payload: Any) -> Optional[str]:
    """
    Validate per-listing attestation checkboxes from a form/JSON payload.
    Returns an error message string, or None if valid.
    """
    if payload is None:
        payload = {}
    rights_ok = _as_bool(payload.get("listing_terms_rights_warranty"))
    takedown_ok = _as_bool(payload.get("listing_terms_takedown_consent"))
    if not rights_ok:
        return "Please confirm you own (or licensed) rights to list and sell this work."
    if not takedown_ok:
        return "Please consent to immediate unlisting on credible infringement claims."
    return None


def record_listing_attestation(book: Any) -> None:
    """Persist per-title listing attestation for the current version."""
    book.listing_attestation_version = LISTING_ATTESTATION_VERSION
    book.listing_attestation_accepted_at = datetime.now(timezone.utc)


def book_has_listing_attestation(book: Any) -> bool:
    """
    True when the author already accepted per-title listing terms for this book.
    One attestation covers ebook, audiobook, and print on the same title.
    """
    if not book:
        return False
    if not getattr(book, "listing_attestation_accepted_at", None):
        return False
    version = getattr(book, "listing_attestation_version", None)
    return version == LISTING_ATTESTATION_VERSION


def ensure_listing_attestation(book: Any, payload: Any) -> Optional[str]:
    """
    Validate and record listing attestation if not yet accepted for this title.
    Returns an error message, or None when attestation is satisfied.
    """
    if book_has_listing_attestation(book):
        return None
    terms_error = validate_listing_terms_payload(payload)
    if terms_error:
        return terms_error
    record_listing_attestation(book)
    return None


def agreement_context_for_templates() -> dict:
    """Shared template context for agreement version labels."""
    return {
        "author_agreement_version": AUTHOR_PUBLISHING_AGREEMENT_VERSION,
        "listing_attestation_version": LISTING_ATTESTATION_VERSION,
    }
