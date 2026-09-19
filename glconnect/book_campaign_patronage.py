"""
Book campaign patronage mode (nonprofit-style funding).

Authors run campaigns to raise money for stories; funders contribute via Ink Studio.
Patrons do not receive financial returns or a share of marketplace sales.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Authors must reach the full funding goal within this many days of campaign start.
CAMPAIGN_GOAL_DEADLINE_DAYS = 730  # 2 years

# Minimum manuscript words before launching a patron campaign (sample chapter for preview).
CAMPAIGN_READINESS_MIN_WORDS = 500

# Stripe USD minimum; not a campaign rule, patrons may give any amount at or above this.
PATRON_GIFT_PAYMENT_MIN_USD = 0.50

CAMPAIGN_GOAL_FAILURE_REASON = (
    'Funding goal not reached within 2 years of campaign start. '
    'Patrons will be refunded their pledges.'
)


def is_book_campaign_patronage_mode(app: Any = None) -> bool:
    """Campaigns are patronage-only (no sale-linked funder returns)."""
    return True


def patronage_campaign_terms() -> dict[str, float]:
    """Stored on campaigns/contributions."""
    return {
        "revenue_share_percentage": 0.0,
        "return_multiplier_cap": 1.0,
    }


def apply_patronage_terms_to_investment(investment: Any) -> None:
    """Ensure a contribution record does not accrue sale-based returns."""
    investment.revenue_share_percentage = 0.0
    investment.return_multiplier = 1.0


def _aware_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def campaign_goal_deadline(campaign: Any) -> datetime | None:
    """Hard deadline to reach the full funding goal (2 years from start)."""
    start = _aware_utc(getattr(campaign, 'start_date', None))
    if start:
        return start + timedelta(days=CAMPAIGN_GOAL_DEADLINE_DAYS)
    return _aware_utc(getattr(campaign, 'end_date', None))


def campaign_period_ended(campaign: Any, *, now: datetime | None = None) -> bool:
    """True when the 2-year goal deadline has passed."""
    deadline = campaign_goal_deadline(campaign)
    if not deadline:
        return False
    now = now or datetime.now(timezone.utc)
    return now > deadline


def campaign_days_until_goal_deadline(campaign: Any, *, now: datetime | None = None) -> int:
    deadline = campaign_goal_deadline(campaign)
    if not deadline:
        return 0
    now = now or datetime.now(timezone.utc)
    return max(0, (deadline - now).days)


def campaign_goal_reached(campaign: Any) -> bool:
    goal = float(getattr(campaign, 'funding_goal', 0) or 0)
    current = float(getattr(campaign, 'current_funding', 0) or 0)
    return goal > 0 and current >= goal


def validate_patron_gift_amount(amount: float) -> Tuple[bool, Optional[str]]:
    """Patrons choose any gift size; only enforce payment-processor minimum."""
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return False, 'Enter a valid contribution amount.'
    if value < PATRON_GIFT_PAYMENT_MIN_USD:
        return False, (
            f'Enter at least ${PATRON_GIFT_PAYMENT_MIN_USD:.2f} '
            '(payment processor minimum).'
        )
    return True, None


def process_campaign_goal_deadline_failure(campaign: Any, db: Any) -> dict[str, Any]:
    """
    If an ACTIVE campaign passes the 2-year deadline without full funding,
    mark it FAILED and queue patron refunds for paid contributions.
    """
    from glconnect.book_platform_models import (
        BookInvestment,
        CampaignStatus,
        InvestmentStatus,
        RefundRequest,
        TransactionStatus,
    )

    if getattr(campaign, 'status', None) != CampaignStatus.ACTIVE:
        return {'processed': False, 'reason': 'not_active'}
    if campaign_goal_reached(campaign):
        return {'processed': False, 'reason': 'goal_reached'}
    if not campaign_period_ended(campaign):
        return {'processed': False, 'reason': 'deadline_not_passed'}

    campaign.status = CampaignStatus.FAILED
    campaign.cancelled_at = datetime.now(timezone.utc)
    campaign.cancellation_reason = CAMPAIGN_GOAL_FAILURE_REASON

    refundable_statuses = (InvestmentStatus.CONFIRMED, InvestmentStatus.ACTIVE)
    investments = BookInvestment.query.filter_by(campaign_id=campaign.id).filter(
        BookInvestment.status.in_(refundable_statuses)
    ).all()

    refunded_count = 0
    for investment in investments:
        existing_refund = RefundRequest.query.filter_by(
            investment_id=investment.id,
            status=TransactionStatus.PENDING,
        ).first()
        if existing_refund:
            continue
        db.session.add(RefundRequest(
            investment_id=investment.id,
            amount=investment.amount,
            currency=investment.currency,
            reason=CAMPAIGN_GOAL_FAILURE_REASON,
            status=TransactionStatus.PENDING,
        ))
        refunded_count += 1

    db.session.commit()
    logger.info(
        'Campaign %s failed goal deadline; queued %s patron refund(s)',
        getattr(campaign, 'id', None),
        refunded_count,
    )
    return {'processed': True, 'refunded_count': refunded_count}


def ensure_campaign_goal_deadline_resolved(campaign: Any, db: Any) -> dict[str, Any]:
    """Resolve a single campaign when its goal deadline has passed without full funding."""
    from glconnect.book_platform_models import CampaignStatus

    if getattr(campaign, 'status', None) != CampaignStatus.ACTIVE:
        return {'processed': False}
    if campaign_goal_reached(campaign) or not campaign_period_ended(campaign):
        return {'processed': False}
    return process_campaign_goal_deadline_failure(campaign, db)


def resolve_expired_active_campaigns(db: Any) -> list[tuple[int, dict[str, Any]]]:
    """Batch-resolve ACTIVE campaigns past the 2-year goal deadline."""
    from glconnect.book_platform_models import CampaignStatus, InvestmentCampaign

    results: list[tuple[int, dict[str, Any]]] = []
    campaigns = InvestmentCampaign.query.filter_by(status=CampaignStatus.ACTIVE).all()
    for campaign in campaigns:
        if campaign_goal_reached(campaign) or not campaign_period_ended(campaign):
            continue
        outcome = process_campaign_goal_deadline_failure(campaign, db)
        if outcome.get('processed'):
            results.append((campaign.id, outcome))
    return results


def campaign_open_for_contributions(
    campaign: Any,
    book: Any = None,
) -> Tuple[bool, Optional[str]]:
    """
    Patron campaigns accept gifts while ACTIVE or FUNDED, before the 2-year deadline,
    and while the book is unpublished. Projects may raise above their stated goal.
    Returns (allowed, user-facing reason if blocked).
    """
    from glconnect.book_platform_models import CampaignStatus
    from glconnect.book_utils import is_book_published

    if book and is_book_published(book):
        return False, 'This campaign is closed because the book is already published.'

    status = getattr(campaign, 'status', None)
    if status == CampaignStatus.FAILED:
        return False, (
            'This campaign did not reach its funding goal within 2 years. '
            'Patrons are being refunded what they pledged.'
        )
    if status == CampaignStatus.CANCELLED:
        return False, 'This campaign is not currently accepting contributions.'

    if campaign_period_ended(campaign):
        if campaign_goal_reached(campaign):
            return False, (
                'The 2-year patron window has ended. '
                'This campaign reached its funding goal and is no longer accepting contributions.'
            )
        if status == CampaignStatus.ACTIVE:
            return False, (
                'The 2-year funding deadline has passed without reaching the goal. '
                'Patrons are being refunded what they pledged.'
            )
        return False, 'This campaign is no longer accepting contributions.'

    # The displayed funding goal is the cap. Do not silently accept
    # overfunding without a separately approved stretch-goal model.
    if status == CampaignStatus.ACTIVE and not campaign_goal_reached(campaign):
        return True, None
    if status == CampaignStatus.FUNDED or campaign_goal_reached(campaign):
        return False, 'This campaign has reached its funding goal and is no longer accepting contributions.'

    return False, 'This campaign is not currently accepting contributions.'
