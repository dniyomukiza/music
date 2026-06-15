#!/usr/bin/env python3
"""Tests for first-project vs subsequent platform fee policy."""

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
        CAMPAIGN_PLATFORM_FEE_PERCENT_FIRST,
        CAMPAIGN_PLATFORM_FEE_PERCENT_SUBSEQUENT,
        MARKETPLACE_PLATFORM_FEE_PERCENT,
        apply_campaign_fee_terms,
        campaign_milestone_release_amount,
        marketplace_author_royalty_fraction,
        marketplace_author_royalty_percent,
    )
    from glconnect.book_platform_models import CampaignStatus
    from glconnect.book_purchase_format import revenue_split_for_purchase

    failures = []

    if MARKETPLACE_PLATFORM_FEE_PERCENT != 10.0:
        failures.append('marketplace platform fee should be 10%')
    if marketplace_author_royalty_percent() != 90.0:
        failures.append('author marketplace share should be 90%')
    if marketplace_author_royalty_fraction() != 0.9:
        failures.append('author marketplace fraction should be 0.9')

    book = MockBook(1, price=20.0, audiobook_price=15.0, print_price=25.0, print_shipping_price=5.0)
    base, extra, royalty, platform = revenue_split_for_purchase(book, 'digital', 20.0)
    if abs(royalty - 18.0) > 0.01 or abs(platform - 2.0) > 0.01:
        failures.append(f'digital split wrong: royalty={royalty}, platform={platform}')

    base, extra, royalty, platform = revenue_split_for_purchase(book, 'digital', 25.0)
    if abs(royalty - 23.0) > 0.01 or abs(platform - 2.0) > 0.01:
        failures.append(f'extra-to-author split wrong: royalty={royalty}, platform={platform}')

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

    if not first_campaign.is_first_author_project:
        failures.append('expected first funded project flag')
    if first_campaign.campaign_platform_fee_percent != CAMPAIGN_PLATFORM_FEE_PERCENT_FIRST:
        failures.append('first project campaign fee should be 0%')
    if first_campaign.author_net_funding != 1000.0:
        failures.append(f'first project author net should be 1000, got {first_campaign.author_net_funding}')

    subsequent = MockCampaign(
        id=2,
        status=CampaignStatus.FUNDED,
        current_funding=1000.0,
        book_project=MockBook(42),
        author_net_funding=None,
    )

    policy.is_author_first_funded_project = lambda campaign, db: False
    apply_campaign_fee_terms(subsequent, None)

    if subsequent.is_first_author_project:
        failures.append('second project should not be first')
    if subsequent.campaign_platform_fee_percent != CAMPAIGN_PLATFORM_FEE_PERCENT_SUBSEQUENT:
        failures.append('subsequent project campaign fee should be 3%')
    if subsequent.author_net_funding != 970.0:
        failures.append(f'subsequent author net should be 970, got {subsequent.author_net_funding}')

    milestone = campaign_milestone_release_amount(subsequent, None, milestone_percent=50.0)
    if milestone != 485.0:
        failures.append(f'milestone release should be 485, got {milestone}')

    if failures:
        print('FAILURES:')
        for item in failures:
            print(' -', item)
        sys.exit(1)

    print('OK: platform fee policy tests passed')


if __name__ == '__main__':
    main()
