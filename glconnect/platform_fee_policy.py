"""
Platform fee policy for Ink Studio book campaigns and marketplace sales.

Funded book campaigns (all projects):
  - Campaign pledges: 15% platform fee on collected funds (platform maintenance)
  - Author net: 85% of pledges (released at draft/publication milestones)

Marketplace sales:
  - 10% platform fee / 90% author royalty
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

MARKETPLACE_PLATFORM_FEE_PERCENT = 10.0
CAMPAIGN_PLATFORM_FEE_PERCENT = 15.0

# Legacy aliases (first vs subsequent no longer differ)
CAMPAIGN_PLATFORM_FEE_PERCENT_FIRST = CAMPAIGN_PLATFORM_FEE_PERCENT
CAMPAIGN_PLATFORM_FEE_PERCENT_SUBSEQUENT = CAMPAIGN_PLATFORM_FEE_PERCENT


def marketplace_author_royalty_percent() -> float:
    """Author share of marketplace list price (before extras like shipping)."""
    return 100.0 - MARKETPLACE_PLATFORM_FEE_PERCENT


def marketplace_author_royalty_fraction() -> float:
    return marketplace_author_royalty_percent() / 100.0


def is_author_first_funded_project(campaign: Any, db: Any) -> bool:
    """True when this is the author's earliest funded campaign (informational only)."""
    from glconnect.book_platform_models import BookProject, CampaignStatus, InvestmentCampaign

    book = getattr(campaign, 'book_project', None)
    author_id = getattr(book, 'author_id', None) if book else None
    if not author_id:
        return True

    earlier = (
        InvestmentCampaign.query
        .join(BookProject, InvestmentCampaign.book_project_id == BookProject.id)
        .filter(BookProject.author_id == author_id)
        .filter(InvestmentCampaign.status == CampaignStatus.FUNDED)
        .filter(InvestmentCampaign.id != campaign.id)
        .order_by(InvestmentCampaign.funded_at.asc(), InvestmentCampaign.id.asc())
        .first()
    )
    return earlier is None


def campaign_platform_fee_percent_for(campaign: Any, db: Any) -> float:
    if getattr(campaign, 'campaign_platform_fee_percent', None) is not None:
        return float(campaign.campaign_platform_fee_percent)
    return CAMPAIGN_PLATFORM_FEE_PERCENT


def apply_campaign_fee_terms(campaign: Any, db: Any) -> None:
    """Snapshot fee terms when a campaign becomes funded."""
    from glconnect.book_platform_models import CampaignStatus

    if getattr(campaign, 'status', None) != CampaignStatus.FUNDED:
        return

    if getattr(campaign, 'campaign_platform_fee_percent', None) is None:
        campaign.is_first_author_project = is_author_first_funded_project(campaign, db)
        campaign.campaign_platform_fee_percent = CAMPAIGN_PLATFORM_FEE_PERCENT

    update_campaign_fee_totals(campaign)


def update_campaign_fee_totals(campaign: Any) -> None:
    """Recalculate fee totals from current_funding (supports overfunding after goal met)."""
    fee_pct = float(getattr(campaign, 'campaign_platform_fee_percent', 0) or 0)
    gross = float(getattr(campaign, 'current_funding', 0) or 0)
    platform_fee = round(gross * fee_pct / 100.0, 2)
    author_net = round(gross - platform_fee, 2)

    campaign.campaign_platform_fee_amount = platform_fee
    campaign.author_net_funding = author_net

    logger.info(
        'Campaign %s fee totals: fee=%s%% gross=$%.2f author_net=$%.2f',
        getattr(campaign, 'id', None),
        fee_pct,
        gross,
        author_net,
    )


def ensure_campaign_fee_terms(campaign: Any, db: Any) -> None:
    """Backfill fee terms for funded campaigns created before this policy."""
    apply_campaign_fee_terms(campaign, db)


def campaign_author_pool(campaign: Any, db: Any | None = None) -> float:
    """Author's share of collected campaign pledges after platform fee."""
    if getattr(campaign, 'author_net_funding', None) is not None:
        return float(campaign.author_net_funding)
    if db is not None:
        ensure_campaign_fee_terms(campaign, db)
        if getattr(campaign, 'author_net_funding', None) is not None:
            return float(campaign.author_net_funding)
    gross = float(getattr(campaign, 'current_funding', 0) or 0)
    return round(gross * (100.0 - CAMPAIGN_PLATFORM_FEE_PERCENT) / 100.0, 2)


def campaign_milestone_release_amount(
    campaign: Any,
    db: Any | None = None,
    *,
    milestone_percent: float = 50.0,
) -> float:
    """Amount available for a milestone release (default 50% of author net pool)."""
    pool = campaign_author_pool(campaign, db)
    return round(pool * milestone_percent / 100.0, 2)


def campaign_fee_summary(campaign: Any, db: Any | None = None) -> dict[str, Any]:
    if db is not None:
        ensure_campaign_fee_terms(campaign, db)
    gross = float(getattr(campaign, 'current_funding', 0) or 0)
    fee_pct = float(getattr(campaign, 'campaign_platform_fee_percent', 0) or 0)
    platform_fee = float(getattr(campaign, 'campaign_platform_fee_amount', 0) or 0)
    author_net = campaign_author_pool(campaign, db)
    return {
        'is_first_author_project': bool(getattr(campaign, 'is_first_author_project', False)),
        'gross_funding': gross,
        'platform_fee_percent': fee_pct,
        'platform_fee_amount': platform_fee,
        'author_net_funding': author_net,
        'marketplace_platform_fee_percent': MARKETPLACE_PLATFORM_FEE_PERCENT,
    }
