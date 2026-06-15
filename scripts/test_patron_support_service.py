#!/usr/bin/env python3
"""Tests for patron supported-project tracking."""

import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class MockCampaign:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class MockBook:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class MockInvestment:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def main():
    from glconnect import create_app
    from glconnect.book_platform_models import BookStatus, CampaignStatus, InvestmentStatus
    from glconnect.patron_support_service import (
        PATRON_LISTING_NOTIFICATION_TYPE,
        group_patron_supported_projects,
    )

    result = create_app()
    app = result[0] if isinstance(result, tuple) else result

    failures = []

    if PATRON_LISTING_NOTIFICATION_TYPE != 'campaign_listed':
        failures.append('unexpected notification type')

    campaign = MockCampaign(id=5, status=CampaignStatus.FUNDED, funding_goal=1000, current_funding=1000)
    book = MockBook(id=9, title='Test Book', status=BookStatus.DRAFT)

    inv1 = MockInvestment(
        campaign_id=5,
        campaign=campaign,
        book_project=book,
        book_project_id=9,
        investor_id=99,
        amount=25.0,
        status=InvestmentStatus.ACTIVE,
        invested_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    inv2 = MockInvestment(
        campaign_id=5,
        campaign=campaign,
        book_project=book,
        book_project_id=9,
        investor_id=99,
        amount=10.0,
        status=InvestmentStatus.CONFIRMED,
        invested_at=datetime(2025, 2, 1, tzinfo=timezone.utc),
    )

    class FakeQuery:
        def options(self, *args, **kwargs):
            return self

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return [inv1, inv2]

    with app.app_context():
        import glconnect.book_platform_models as models

        original = models.BookInvestment.query
        models.BookInvestment.query = FakeQuery()
        try:
            groups = group_patron_supported_projects(99, None)
        finally:
            models.BookInvestment.query = original

    if len(groups) != 1:
        failures.append(f'expected 1 grouped project, got {len(groups)}')
    elif groups[0]['total_amount'] != 35.0:
        failures.append(f'expected total 35, got {groups[0]["total_amount"]}')
    elif groups[0]['contribution_count'] != 2:
        failures.append('expected 2 contributions in group')

    if failures:
        print('FAILURES:')
        for item in failures:
            print(' -', item)
        sys.exit(1)

    print('OK: patron support service tests passed')


if __name__ == '__main__':
    main()
