"""
Destructive: remove every Ink Studio book project and all related rows
(investments, campaigns, sales, purchases, distributions, reviews, chapters, …).

Does NOT delete users, writers, or book_platform_users.

Call only via scripts/clear_all_books.py with explicit env confirmations.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from sqlalchemy import or_

logger = logging.getLogger(__name__)


def purge_all_book_projects(db) -> Dict[str, Any]:
    """
    Delete all BookProject rows and dependent book-platform data.

    Returns a summary dict with counts (best-effort).
    """
    from glconnect.book_platform_models import (
        AudioGenerationTask,
        AudiobookChapter,
        AuthorCampaignPayoutRequest,
        BookAnalytics,
        BookChapter,
        BookCollaboration,
        BookComment,
        BookInvestment,
        BookNotification,
        BookProject,
        BookPurchase,
        BookReview,
        BookSale,
        BookVersion,
        ChapterSuggestion,
        ChapterVersion,
        CollaborationInvitation,
        DigitalBookEdition,
        InvestmentCampaign,
        InvestmentPayout,
        LibraryBookHide,
        PayoutRequest,
        ReaderAnnotation,
        RealtimeSession,
        RefundRequest,
        RevenueDistribution,
        ReviewerEarning,
        ReviewRequest,
    )

    book_ids: List[int] = [r[0] for r in db.session.query(BookProject.id).all()]
    summary: Dict[str, Any] = {"book_project_ids": len(book_ids)}
    if not book_ids:
        summary["message"] = "No book_projects rows; nothing to do."
        return summary

    # --- Investments & campaigns ---
    camp_ids = [
        r[0]
        for r in db.session.query(InvestmentCampaign.id)
        .filter(InvestmentCampaign.book_project_id.in_(book_ids))
        .all()
    ]

    inv_conds = [BookInvestment.book_project_id.in_(book_ids)]
    if camp_ids:
        inv_conds.append(BookInvestment.campaign_id.in_(camp_ids))
    inv_ids = [
        r[0]
        for r in BookInvestment.query.filter(or_(*inv_conds))
        .with_entities(BookInvestment.id)
        .all()
    ]

    if inv_ids:
        n = (
            InvestmentPayout.query.filter(InvestmentPayout.investment_id.in_(inv_ids))
            .delete(synchronize_session=False)
        )
        summary["investment_payouts_deleted"] = n
        n = (
            PayoutRequest.query.filter(PayoutRequest.investment_id.in_(inv_ids))
            .delete(synchronize_session=False)
        )
        summary["payout_requests_deleted"] = n
        n = (
            RefundRequest.query.filter(RefundRequest.investment_id.in_(inv_ids))
            .delete(synchronize_session=False)
        )
        summary["refund_requests_deleted"] = n

    if camp_ids:
        n = (
            AuthorCampaignPayoutRequest.query.filter(
                AuthorCampaignPayoutRequest.campaign_id.in_(camp_ids)
            ).delete(synchronize_session=False)
        )
        summary["author_campaign_payout_requests_deleted"] = n

    if inv_ids:
        n = (
            BookInvestment.query.filter(BookInvestment.id.in_(inv_ids))
            .delete(synchronize_session=False)
        )
        summary["book_investments_deleted"] = n

    n = (
        InvestmentCampaign.query.filter(InvestmentCampaign.book_project_id.in_(book_ids))
        .delete(synchronize_session=False)
    )
    summary["investment_campaigns_deleted"] = n

    # --- Sales & revenue ---
    sale_ids = [
        r[0]
        for r in db.session.query(BookSale.id)
        .filter(BookSale.book_project_id.in_(book_ids))
        .all()
    ]
    if sale_ids:
        dist_ids = [
            r[0]
            for r in db.session.query(RevenueDistribution.id)
            .filter(RevenueDistribution.source_sale_id.in_(sale_ids))
            .all()
        ]
        if dist_ids:
            n = (
                InvestmentPayout.query.filter(
                    InvestmentPayout.distribution_id.in_(dist_ids)
                ).delete(synchronize_session=False)
            )
            summary["investment_payouts_by_distribution_deleted"] = (
                summary.get("investment_payouts_by_distribution_deleted", 0) + n
            )
            n = (
                ReviewerEarning.query.filter(
                    ReviewerEarning.distribution_id.in_(dist_ids)
                ).delete(synchronize_session=False)
            )
            summary["reviewer_earnings_by_distribution_deleted"] = n
            n = (
                RevenueDistribution.query.filter(
                    RevenueDistribution.id.in_(dist_ids)
                ).delete(synchronize_session=False)
            )
            summary["revenue_distributions_deleted"] = n
        n = (
            BookSale.query.filter(BookSale.book_project_id.in_(book_ids))
            .delete(synchronize_session=False)
        )
        summary["book_sales_deleted"] = n

    n = (
        BookPurchase.query.filter(BookPurchase.book_project_id.in_(book_ids))
        .delete(synchronize_session=False)
    )
    summary["book_purchases_deleted"] = n

    # --- Reviews (earnings first) ---
    review_ids = [
        r[0]
        for r in db.session.query(BookReview.id)
        .filter(BookReview.book_project_id.in_(book_ids))
        .all()
    ]
    if review_ids:
        n = (
            ReviewerEarning.query.filter(ReviewerEarning.review_id.in_(review_ids))
            .delete(synchronize_session=False)
        )
        summary["reviewer_earnings_by_review_deleted"] = n
        n = (
            BookReview.query.filter(BookReview.book_project_id.in_(book_ids))
            .delete(synchronize_session=False)
        )
        summary["book_reviews_deleted"] = n

    n = (
        ReviewRequest.query.filter(ReviewRequest.book_project_id.in_(book_ids))
        .delete(synchronize_session=False)
    )
    summary["review_requests_deleted"] = n

    # --- Misc per-book ---
    for model, key in (
        (ReaderAnnotation, "reader_annotations_deleted"),
        (LibraryBookHide, "library_book_hides_deleted"),
        (AudioGenerationTask, "audio_generation_tasks_deleted"),
        (RealtimeSession, "realtime_sessions_deleted"),
        (BookComment, "book_comments_deleted"),
        (BookAnalytics, "book_analytics_deleted"),
        (BookNotification, "book_notifications_deleted"),
        (DigitalBookEdition, "digital_book_editions_deleted"),
        (AudiobookChapter, "audiobook_chapters_deleted"),
    ):
        n = (
            model.query.filter(model.book_project_id.in_(book_ids))  # type: ignore[attr-defined]
            .delete(synchronize_session=False)
        )
        summary[key] = n

    collab_ids = [
        r[0]
        for r in db.session.query(BookCollaboration.id)
        .filter(BookCollaboration.book_project_id.in_(book_ids))
        .all()
    ]
    if collab_ids:
        n = (
            CollaborationInvitation.query.filter(
                CollaborationInvitation.collaboration_id.in_(collab_ids)
            ).delete(synchronize_session=False)
        )
        summary["collaboration_invitations_deleted"] = n
    n = (
        BookCollaboration.query.filter(BookCollaboration.book_project_id.in_(book_ids))
        .delete(synchronize_session=False)
    )
    summary["book_collaborations_deleted"] = n

    # --- Chapters & versions ---
    chapter_ids = [
        r[0]
        for r in db.session.query(BookChapter.id)
        .filter(BookChapter.book_project_id.in_(book_ids))
        .all()
    ]
    if chapter_ids:
        n = (
            ChapterSuggestion.query.filter(ChapterSuggestion.chapter_id.in_(chapter_ids))
            .delete(synchronize_session=False)
        )
        summary["chapter_suggestions_deleted"] = n
        n = (
            ChapterVersion.query.filter(ChapterVersion.chapter_id.in_(chapter_ids))
            .delete(synchronize_session=False)
        )
        summary["chapter_versions_deleted"] = n

    n = (
        BookChapter.query.filter(BookChapter.book_project_id.in_(book_ids))
        .delete(synchronize_session=False)
    )
    summary["book_chapters_deleted"] = n

    version_ids = [
        r[0]
        for r in db.session.query(BookVersion.id)
        .filter(BookVersion.book_project_id.in_(book_ids))
        .all()
    ]
    if version_ids:
        n = (
            ChapterVersion.query.filter(ChapterVersion.book_version_id.in_(version_ids))
            .delete(synchronize_session=False)
        )
        summary["chapter_versions_by_book_version_deleted"] = n
    n = (
        BookVersion.query.filter(BookVersion.book_project_id.in_(book_ids))
        .delete(synchronize_session=False)
    )
    summary["book_versions_deleted"] = n

    # --- Stale author withdrawal rows (sales are gone) ---
    try:
        from glconnect.book_platform_models import AuthorSalesPayoutRequest

        n = db.session.query(AuthorSalesPayoutRequest).delete(synchronize_session=False)
        summary["author_sales_payout_requests_deleted"] = n
    except Exception as exc:
        logger.warning("Could not clear author_sales_payout_requests: %s", exc)
        summary["author_sales_payout_requests_deleted"] = "skipped"

    # --- Books ---
    n = (
        BookProject.query.filter(BookProject.id.in_(book_ids))
        .delete(synchronize_session=False)
    )
    summary["book_projects_deleted"] = n
    db.session.commit()
    summary["message"] = "Purge complete."
    return summary
