#!/usr/bin/env python3
"""Tests for author cross-format listing coupons and per-format platform fees."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class MockBook:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def main():
    from glconnect.author_listing_coupon_policy import (
        BASE_PLATFORM_FEE_PERCENT,
        COUPON_PLATFORM_FEE_PERCENT,
        MIN_PLATFORM_FEE_PERCENT,
        effective_platform_fee_percent,
        _format_base_portions,
    )
    from glconnect.book_purchase_format import revenue_split_for_purchase

    failures = []

    book_std = MockBook(
        id=1,
        author_id=1,
        price=20.0,
        audiobook_price=15.0,
        print_price=25.0,
        print_shipping_price=5.0,
    )
    base, extra, royalty, platform, fee_pct = revenue_split_for_purchase(book_std, "digital", 20.0)
    if abs(platform - 2.0) > 0.01 or abs(fee_pct - 10.0) > 0.01:
        failures.append(f"standard digital: platform={platform}, fee_pct={fee_pct}")

    fee_audio_default = effective_platform_fee_percent(book_std, "audiobook")
    if abs(fee_audio_default - 30.0) > 0.01:
        failures.append(f"default audiobook fee should be 30%, got {fee_audio_default}")

    book_disc = MockBook(
        id=2,
        author_id=1,
        price=20.0,
        audiobook_price=15.0,
        platform_fee_percent_audiobook=COUPON_PLATFORM_FEE_PERCENT,
    )
    fee_audio = effective_platform_fee_percent(book_disc, "audiobook")
    if abs(fee_audio - 5.0) > 0.01:
        failures.append(f"audiobook override fee should be 5%, got {fee_audio}")

    base, extra, royalty, platform, fee_pct = revenue_split_for_purchase(book_disc, "audiobook", 15.0)
    if abs(platform - 0.75) > 0.01:
        failures.append(f"discounted audiobook platform fee should be 0.75, got {platform}")

    # Bundle of 2+: flat 20% platform / 80% author on combined base (35)
    base, extra, royalty, platform, fee_pct = revenue_split_for_purchase(book_disc, "bundle", 35.0)
    expected_platform = 35.0 * 0.20
    if abs(platform - expected_platform) > 0.05 or abs(fee_pct - 20.0) > 0.01:
        failures.append(f"bundle platform fee wrong: {platform} (fee={fee_pct}) vs {expected_platform}")

    portions = _format_base_portions(book_std, ["digital", "audiobook"])
    if abs(sum(portions.values()) - 35.0) > 0.01:
        failures.append(f"bundle portions should sum to 35, got {portions}")

    if MIN_PLATFORM_FEE_PERCENT >= COUPON_PLATFORM_FEE_PERCENT:
        failures.append("min fee should be below coupon fee")
    if COUPON_PLATFORM_FEE_PERCENT >= BASE_PLATFORM_FEE_PERCENT:
        failures.append("coupon fee should be below base ebook fee")

    if failures:
        print("FAILURES:")
        for item in failures:
            print(" -", item)
        sys.exit(1)

    print("OK: author listing coupon policy tests passed")


if __name__ == "__main__":
    main()
