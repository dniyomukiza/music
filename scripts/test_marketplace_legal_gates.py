#!/usr/bin/env python3
"""Regression checks for marketplace legal safety gates."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    os.environ["FLASK_ENV"] = "production"
    os.environ.pop("STRIPE_CONNECT_ALLOW_PLATFORM_ONLY", None)
    os.environ.pop("STRIPE_TAX_ENABLED", None)

    from glconnect.stripe_utils import (
        apply_stripe_tax_to_checkout_kw,
        is_production_runtime,
        marketplace_requires_author_connect,
        stripe_connect_allow_platform_only,
        stripe_tax_enabled,
    )
    from glconnect.author_publishing_agreement import (
        AUTHOR_PUBLISHING_AGREEMENT_VERSION,
        LISTING_ATTESTATION_VERSION,
    )
    from glconnect.account_terms import ACCOUNT_TERMS_VERSION

    assert is_production_runtime() is True
    assert stripe_connect_allow_platform_only() is False
    assert marketplace_requires_author_connect() is True
    assert stripe_tax_enabled() is False
    assert apply_stripe_tax_to_checkout_kw({"mode": "payment"}) == {"mode": "payment"}

    os.environ["FLASK_ENV"] = "development"
    os.environ["STRIPE_CONNECT_ALLOW_PLATFORM_ONLY"] = "true"
    assert stripe_connect_allow_platform_only() is True
    assert marketplace_requires_author_connect() is False

    os.environ["STRIPE_TAX_ENABLED"] = "1"
    taxed = apply_stripe_tax_to_checkout_kw(
        {"line_items": [{"price_data": {"unit_amount": 500}}]}
    )
    assert taxed["automatic_tax"] == {"enabled": True}
    assert taxed["billing_address_collection"] == "required"
    assert taxed["line_items"][0]["price_data"]["tax_behavior"] == "exclusive"

    assert AUTHOR_PUBLISHING_AGREEMENT_VERSION == "1.2"
    assert LISTING_ATTESTATION_VERSION == "1.2"
    assert ACCOUNT_TERMS_VERSION == "1.1"
    print("test_marketplace_legal_gates: OK")


if __name__ == "__main__":
    main()
