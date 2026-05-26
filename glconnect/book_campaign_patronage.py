"""
Book campaign patronage mode (nonprofit-style funding).

Authors run campaigns to raise money for stories; funders contribute via Ink Studio.
Patrons do not receive financial returns or a share of marketplace sales.
"""

from __future__ import annotations

from typing import Any


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
