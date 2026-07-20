#!/usr/bin/env python3
"""Tests for platform fee policy on funded campaigns and marketplace sales."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class MockCampaign:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class MockBook:
    def __init__(self, author_id, **kwargs):
        self.author_id = author_id
        for key, value in kwargs.items():
            setattr(self, key, value)


def main():
    from glconnect.platform_fee_policy import (
        CAMPAIGN_PLATFORM_FEE_PERCENT,
        MARKETPLACE_PLATFORM_FEE_PERCENT,
        MARKETPLACE_PLATFORM_FEE_PERCENT_AUDIOBOOK,
        MARKETPLACE_PLATFORM_FEE_PERCENT_BUNDLE,
        apply_campaign_fee_terms,
        campaign_milestone_release_amount,
        marketplace_author_royalty_fraction,
        marketplace_author_royalty_percent,
        marketplace_platform_fee_percent_for,
    )
    from glconnect.book_platform_models import CampaignStatus
    from glconnect.book_purchase_format import revenue_split_for_purchase

    failures = []

    if CAMPAIGN_PLATFORM_FEE_PERCENT != 15.0:
        failures.append('campaign platform fee should be 15%')
    if MARKETPLACE_PLATFORM_FEE_PERCENT != 10.0:
        failures.append('ebook/print marketplace platform fee should be 10%')
    if MARKETPLACE_PLATFORM_FEE_PERCENT_AUDIOBOOK != 30.0:
        failures.append('audiobook platform fee should be 30%')
    if MARKETPLACE_PLATFORM_FEE_PERCENT_BUNDLE != 20.0:
        failures.append('bundle platform fee should be 20%')
    if marketplace_author_royalty_percent('digital') != 90.0:
        failures.append('ebook author share should be 90%')
    if marketplace_author_royalty_percent('audiobook') != 70.0:
        failures.append('audiobook author share should be 70%')
    if marketplace_author_royalty_percent('bundle') != 80.0:
        failures.append('bundle author share should be 80%')
    if marketplace_author_royalty_fraction('digital') != 0.9:
        failures.append('ebook author fraction should be 0.9')
    if marketplace_platform_fee_percent_for('print') != 10.0:
        failures.append('print platform fee should be 10%')

    book = MockBook(1, price=20.0, audiobook_price=15.0, print_price=25.0, print_shipping_price=5.0)
    base, extra, royalty, platform, fee_pct = revenue_split_for_purchase(book, 'digital', 20.0)
    if abs(royalty - 18.0) > 0.01 or abs(platform - 2.0) > 0.01 or abs(fee_pct - 10.0) > 0.01:
        failures.append(f'digital split wrong: royalty={royalty}, platform={platform}, fee={fee_pct}')

    base, extra, royalty, platform, fee_pct = revenue_split_for_purchase(book, 'audiobook', 15.0)
    if abs(royalty - 10.5) > 0.01 or abs(platform - 4.5) > 0.01 or abs(fee_pct - 30.0) > 0.01:
        failures.append(f'audiobook split wrong: royalty={royalty}, platform={platform}, fee={fee_pct}')

    base, extra, royalty, platform, fee_pct = revenue_split_for_purchase(book, 'print', 30.0)
    # base print 25 @ 90% = 22.5 royalty + 5 shipping; platform 2.5
    if abs(royalty - 27.5) > 0.01 or abs(platform - 2.5) > 0.01:
        failures.append(f'print+shipping split wrong: royalty={royalty}, platform={platform}')

    base, extra, royalty, platform, fee_pct = revenue_split_for_purchase(book, 'digital', 25.0)
    if abs(royalty - 23.0) > 0.01 or abs(platform - 2.0) > 0.01:
        failures.append(f'extra-to-author split wrong: royalty={royalty}, platform={platform}')

    # bundle ebook+audio base = (20+15)*0.8 = 28; 80% author / 20% platform
    base, extra, royalty, platform, fee_pct = revenue_split_for_purchase(book, 'bundle', 28.0)
    if abs(base - 28.0) > 0.01 or abs(royalty - 22.4) > 0.05 or abs(platform - 5.6) > 0.05:
        failures.append(f'bundle split wrong: base={base}, royalty={royalty}, platform={platform}, fee={fee_pct}')
    if abs(fee_pct - 20.0) > 0.01:
        failures.append(f'bundle fee pct should be 20, got {fee_pct}')

    first_campaign = MockCampaign(
        id=1,
        status=CampaignStatus.FUNDED,
        current_funding=1000.0,
        book_project=MockBook(42),
        author_net_funding=None,
    )

    import glconnect.platform_fee_policy as policy

    policy.is_author_first_funded_project = lambda campaign, db: True
    apply_campaign_fee_terms(first_campaign, None)

    if first_campaign.campaign_platform_fee_percent != 15.0:
        failures.append('first funded project campaign fee should be 15%')
    if first_campaign.author_net_funding != 850.0:
        failures.append(f'first project author net should be 850, got {first_campaign.author_net_funding}')

    subsequent = MockCampaign(
        id=2,
        status=CampaignStatus.FUNDED,
        current_funding=1000.0,
        book_project=MockBook(42),
        author_net_funding=None,
    )

    policy.is_author_first_funded_project = lambda campaign, db: False
    apply_campaign_fee_terms(subsequent, None)

    if subsequent.campaign_platform_fee_percent != 15.0:
        failures.append('subsequent funded project campaign fee should be 15%')
    if subsequent.author_net_funding != 850.0:
        failures.append(f'subsequent author net should be 850, got {subsequent.author_net_funding}')

    milestone = campaign_milestone_release_amount(subsequent, None, milestone_percent=50.0)
    if milestone != 425.0:
        failures.append(f'milestone release should be 425, got {milestone}')

    if failures:
        print('FAILURES:')
        for item in failures:
            print(' -', item)
        sys.exit(1)

    print('OK: platform fee policy tests passed')


if __name__ == '__main__':
    main()
