"""
Destructive: remove Ink Studio book projects and related DB rows
(investments, campaigns, sales, purchases, distributions, reviews, chapters, …).

Does NOT delete users, writers, or book_platform_users.

Call only via scripts/clear_all_books.py or glconnect/test_data_cleanup.py with explicit confirmations.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import or_, text

logger = logging.getLogger(__name__)


def _delete_legacy_book_cart_rows(db, book_id: int) -> None:
    """Best-effort cleanup of legacy book_cart_items rows if the table still exists."""
    try:
        with db.session.begin_nested():
            db.session.execute(
                text("DELETE FROM book_cart_items WHERE book_project_id = :bid"),
                {"bid": int(book_id)},
            )
    except Exception:
        pass


def purge_book_projects_by_ids(
    db,
    book_ids: Sequence[int],
    *,
    commit: bool = True,
    clear_all_author_sales_payout_requests: bool = False,
    author_ids_for_sales_payouts: Optional[Sequence[int]] = None,
) -> Dict[str, Any]:
    """
    Delete BookProject rows (by id) and all dependent book-platform data.

    :param clear_all_author_sales_payout_requests: Only for full-table purge (legacy behaviour).
    :param author_ids_for_sales_payout_requests: Scope sales payout cleanup to these authors.
    """
    from glconnect.book_utils import delete_book_chapter_version_graph_for_project
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

    book_ids = sorted({int(b) for b in book_ids})
    summary: Dict[str, Any] = {"book_project_ids": len(book_ids)}
    if not book_ids:
        summary["message"] = "No book_projects ids; nothing to do."
        return summary

    for bid in book_ids:
        _delete_legacy_book_cart_rows(db, bid)

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

    for bid in book_ids:
        delete_book_chapter_version_graph_for_project(bid)

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

    try:
        from glconnect.book_platform_models import AuthorSalesPayoutRequest

        if clear_all_author_sales_payout_requests:
            n = db.session.query(AuthorSalesPayoutRequest).delete(synchronize_session=False)
            summary["author_sales_payout_requests_deleted"] = n
        elif author_ids_for_sales_payouts:
            n = (
                AuthorSalesPayoutRequest.query.filter(
                    AuthorSalesPayoutRequest.author_id.in_(list(author_ids_for_sales_payouts))
                ).delete(synchronize_session=False)
            )
            summary["author_sales_payout_requests_deleted"] = n
    except Exception as exc:
        logger.warning("Could not clear author_sales_payout_requests: %s", exc)
        summary["author_sales_payout_requests_deleted"] = "skipped"

    n = (
        BookProject.query.filter(BookProject.id.in_(book_ids))
        .delete(synchronize_session=False)
    )
    summary["book_projects_deleted"] = n

    if commit:
        db.session.commit()
    summary["message"] = "Book purge complete."
    return summary


def purge_all_book_projects(db) -> Dict[str, Any]:
    """Delete all BookProject rows and dependent book-platform data."""
    from glconnect.book_platform_models import BookProject

    book_ids: List[int] = [r[0] for r in db.session.query(BookProject.id).all()]
    if not book_ids:
        return {"book_project_ids": 0, "message": "No book_projects rows; nothing to do."}
    return purge_book_projects_by_ids(
        db,
        book_ids,
        commit=True,
        clear_all_author_sales_payout_requests=True,
    )
