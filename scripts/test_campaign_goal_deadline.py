#!/usr/bin/env python3
"""Tests for the 2-year campaign funding deadline and patron refund policy."""

import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class MockCampaign:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def main():
    from glconnect.book_platform_models import CampaignStatus
    from glconnect.book_campaign_patronage import (
        CAMPAIGN_GOAL_DEADLINE_DAYS,
        CAMPAIGN_GOAL_FAILURE_REASON,
        PATRON_GIFT_PAYMENT_MIN_USD,
        campaign_days_until_goal_deadline,
        campaign_goal_deadline,
        campaign_goal_reached,
        campaign_open_for_contributions,
        campaign_period_ended,
        validate_patron_gift_amount,
    )

    failures = []

    start = datetime.now(timezone.utc) - timedelta(days=100)
    campaign = MockCampaign(
        start_date=start,
        end_date=start + timedelta(days=30),
        status=CampaignStatus.ACTIVE,
        funding_goal=1000.0,
        current_funding=400.0,
    )
    deadline = campaign_goal_deadline(campaign)
    if not deadline or (deadline - start).days != CAMPAIGN_GOAL_DEADLINE_DAYS:
        failures.append('goal deadline should be 730 days after start')

    if campaign_period_ended(campaign):
        failures.append('100-day-old campaign should not be past deadline')

    days_left = campaign_days_until_goal_deadline(campaign)
    if days_left <= 0 or days_left > CAMPAIGN_GOAL_DEADLINE_DAYS:
        failures.append(f'unexpected days remaining: {days_left}')

    allowed, _ = campaign_open_for_contributions(campaign)
    if not allowed:
        failures.append('active in-window campaign should accept contributions')

    expired = MockCampaign(
        start_date=datetime.now(timezone.utc) - timedelta(days=CAMPAIGN_GOAL_DEADLINE_DAYS + 1),
        status=CampaignStatus.ACTIVE,
        funding_goal=1000.0,
        current_funding=400.0,
    )
    if not campaign_period_ended(expired):
        failures.append('campaign past 2 years should be expired')

    allowed, reason = campaign_open_for_contributions(expired)
    if allowed or not reason or 'refunded' not in reason.lower():
        failures.append('expired unfunded campaign should block contributions with refund message')

    failed = MockCampaign(
        start_date=start,
        status=CampaignStatus.FAILED,
        funding_goal=1000.0,
        current_funding=400.0,
    )
    allowed, reason = campaign_open_for_contributions(failed)
    if allowed or not reason or 'refunded' not in reason.lower():
        failures.append('FAILED campaign should explain patron refunds')

    funded = MockCampaign(
        start_date=start,
        status=CampaignStatus.FUNDED,
        funding_goal=1000.0,
        current_funding=1000.0,
    )
    if not campaign_goal_reached(funded):
        failures.append('funded campaign should report goal reached')

    allowed, reason = campaign_open_for_contributions(funded)
    if allowed or not reason or 'funding goal' not in reason.lower():
        failures.append('funded at-goal campaign should block new contributions before deadline')

    funded_over = MockCampaign(
        start_date=start,
        status=CampaignStatus.FUNDED,
        funding_goal=1000.0,
        current_funding=1500.0,
    )
    if not campaign_goal_reached(funded_over):
        failures.append('overfunded campaign should report goal reached')

    allowed, reason = campaign_open_for_contributions(funded_over)
    if allowed or not reason or 'funding goal' not in reason.lower():
        failures.append('overfunded campaign should block new contributions before deadline')

    if '2 years' not in CAMPAIGN_GOAL_FAILURE_REASON.lower():
        failures.append('failure reason should mention 2 years')

    ok, err = validate_patron_gift_amount(25.0)
    if not ok or err:
        failures.append('patron gift validation should accept 25.00')
    ok_low, _ = validate_patron_gift_amount(PATRON_GIFT_PAYMENT_MIN_USD - 0.01)
    if ok_low:
        failures.append('patron gift below payment minimum should be rejected')

    if failures:
        print('FAILURES:')
        for item in failures:
            print(' -', item)
        sys.exit(1)

    print('OK: campaign goal deadline tests passed')


if __name__ == '__main__':
    main()
