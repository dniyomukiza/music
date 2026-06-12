"""
Book campaign patronage mode (nonprofit-style funding).

Authors run campaigns to raise money for stories; funders contribute via Ink Studio.
Patrons do not receive financial returns or a share of marketplace sales.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional, Tuple


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


def campaign_period_ended(campaign: Any, *, now: datetime | None = None) -> bool:
    """True when the campaign duration has passed (patron window closed)."""
    end = _aware_utc(getattr(campaign, 'end_date', None))
    if not end:
        return False
    now = now or datetime.now(timezone.utc)
    return now > end


def campaign_goal_reached(campaign: Any) -> bool:
    goal = float(getattr(campaign, 'funding_goal', 0) or 0)
    current = float(getattr(campaign, 'current_funding', 0) or 0)
    return goal > 0 and current >= goal


def campaign_open_for_contributions(
    campaign: Any,
    book: Any = None,
) -> Tuple[bool, Optional[str]]:
    """
    Patron campaigns accept gifts while ACTIVE, before end_date, before goal, book unpublished.
    Returns (allowed, user-facing reason if blocked).
    """
    from glconnect.book_platform_models import CampaignStatus
    from glconnect.book_utils import is_book_published

    if book and is_book_published(book):
        return False, 'This campaign is closed because the book is already published.'

    status = getattr(campaign, 'status', None)
    if status != CampaignStatus.ACTIVE:
        if status == CampaignStatus.FUNDED or campaign_goal_reached(campaign):
            return False, 'This campaign has reached its funding goal and is no longer accepting contributions.'
        if campaign_period_ended(campaign):
            return False, (
                'This campaign period has ended. Patrons can no longer contribute. '
                'Gifts already received stay with the author to help finish the book.'
            )
        return False, 'This campaign is not currently accepting contributions.'

    if campaign_goal_reached(campaign):
        return False, 'This campaign has reached its funding goal and is no longer accepting contributions.'

    if campaign_period_ended(campaign):
        return False, (
            'This campaign period has ended. Patrons can no longer contribute. '
            'Gifts already received stay with the author to help finish the book.'
        )

    return True, None

