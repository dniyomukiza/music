"""
Accountability Service
Handles author accountability, refunds, and payments when books aren't completed/published
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import joinedload
import logging

logger = logging.getLogger(__name__)

# Configuration
MAX_BOOK_COMPLETION_DAYS = 180  # 6 months to complete book after funding
MAX_PUBLICATION_DAYS = 30  # 30 days to publish after completion
REVIEWER_GUARANTEE_PERCENTAGE = 50.0  # 50% of agreed revenue share guaranteed
AUTOMATIC_REFUND_DAYS = 210  # 210 days (7 months) = funding + completion + publication


def check_author_accountability(book_id, db):
    """
    Check if author has met their obligations and trigger appropriate actions.
    
    Returns:
        dict: Status and actions taken
    """
    try:
        from glconnect.book_platform_models import (
            BookProject, InvestmentCampaign, BookInvestment, BookReview,
            BookStatus, CampaignStatus, InvestmentStatus, ReviewStatus,
            TransactionStatus, RefundRequest
        )
        
        book = BookProject.query.options(
            joinedload(BookProject.investment_campaign),
            joinedload(BookProject.accredited_reviews)
        ).get(book_id)
        
        if not book:
            return {'success': False, 'error': 'Book not found'}
        
        actions_taken = []
        warnings = []
        
        # Check investment campaign status
        campaign = book.investment_campaign
        if campaign and campaign.status == CampaignStatus.FUNDED:
            days_since_funding = (datetime.now(timezone.utc) - campaign.funded_at).days if campaign.funded_at else 0
            
            # Check if book is completed
            is_completed = book.status == BookStatus.PUBLISHED
            is_draft = book.status == BookStatus.DRAFT
            
            # Check completion deadline
            if not is_completed and days_since_funding > MAX_BOOK_COMPLETION_DAYS:
                warnings.append(f"Book not completed after {days_since_funding} days (deadline: {MAX_BOOK_COMPLETION_DAYS} days)")
                
                # Trigger refund process for investors
                refund_result = process_investor_refunds(book_id, db, reason="Book not completed within deadline")
                if refund_result.get('success'):
                    actions_taken.append(f"Initiated refunds for {refund_result.get('refunded_count', 0)} investors")
            
            # Check publication deadline (if book is completed but not published)
            elif is_draft and days_since_funding > (MAX_BOOK_COMPLETION_DAYS + MAX_PUBLICATION_DAYS):
                warnings.append(f"Book completed but not published after {days_since_funding} days")
                
                # Trigger refund process
                refund_result = process_investor_refunds(book_id, db, reason="Book not published within deadline")
                if refund_result.get('success'):
                    actions_taken.append(f"Initiated refunds for {refund_result.get('refunded_count', 0)} investors")
        
        # Check reviewer payments
        reviews = [r for r in book.accredited_reviews if r.status == ReviewStatus.PUBLISHED]
        if reviews:
            # Check if reviewers should be paid even if book isn't selling
            for review in reviews:
                if not book.status == BookStatus.PUBLISHED:
                    # Book not published - check if reviewer should get guaranteed payment
                    guarantee_result = process_reviewer_guarantee(review.id, db)
                    if guarantee_result.get('success'):
                        actions_taken.append(f"Processed guarantee payment for reviewer {review.reviewer_id}")
        
        return {
            'success': True,
            'actions_taken': actions_taken,
            'warnings': warnings,
            'book_status': book.status.value if book.status else None,
            'days_since_funding': days_since_funding if campaign and campaign.funded_at else None
        }
        
    except Exception as e:
        logger.error(f"Error checking author accountability for book {book_id}: {str(e)}", exc_info=True)
        return {'success': False, 'error': str(e)}


def process_investor_refunds(book_id, db, reason="Author failed to complete book"):
    """
    Process refunds for all investors when author fails to deliver.
    
    Args:
        book_id: Book project ID
        db: Database session
        reason: Reason for refund
    
    Returns:
        dict: Refund processing result
    """
    try:
        from glconnect.book_platform_models import (
            BookProject, InvestmentCampaign, BookInvestment,
            InvestmentStatus, TransactionStatus, RefundRequest
        )
        
        book = BookProject.query.get(book_id)
        if not book:
            return {'success': False, 'error': 'Book not found'}
        
        campaign = book.investment_campaign
        if not campaign or campaign.status != CampaignStatus.FUNDED:
            return {'success': False, 'error': 'No funded campaign found'}
        
        investments = BookInvestment.query.filter_by(
            campaign_id=campaign.id,
            status=InvestmentStatus.ACTIVE
        ).all()
        
        refunded_count = 0
        refunds_created = []
        
        for investment in investments:
            # Check if already refunded
            existing_refund = RefundRequest.query.filter_by(
                investment_id=investment.id,
                status=TransactionStatus.COMPLETED
            ).first()
            
            if existing_refund:
                continue
            
            # Create refund request
            refund = RefundRequest(
                investment_id=investment.id,
                amount=investment.amount,
                currency=investment.currency,
                reason=reason,
                status=TransactionStatus.PENDING,
                requested_at=datetime.now(timezone.utc)
            )
            db.session.add(refund)
            refunds_created.append(refund)
            
            # Update investment status
            investment.status = InvestmentStatus.REFUNDED
            investment.refunded_at = datetime.now(timezone.utc)
            
            refunded_count += 1
        
        # Update campaign status
        campaign.status = CampaignStatus.CANCELLED
        campaign.cancelled_at = datetime.now(timezone.utc)
        campaign.cancellation_reason = reason
        
        db.session.commit()
        
        logger.info(f"Processed {refunded_count} refund requests for book {book_id}")
        
        # TODO: Integrate with payment processor to actually process refunds
        # For now, refunds are marked as pending and need manual processing
        
        return {
            'success': True,
            'refunded_count': refunded_count,
            'refunds': refunds_created
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing investor refunds for book {book_id}: {str(e)}", exc_info=True)
        return {'success': False, 'error': str(e)}


def process_reviewer_guarantee(review_id, db):
    """
    Process guaranteed payment for reviewer when book isn't published.
    
    Reviewers get a guaranteed minimum payment (e.g., 50% of agreed revenue share)
    if they complete their review but the book never gets published.
    
    Args:
        review_id: Book review ID
        db: Database session
    
    Returns:
        dict: Payment processing result
    """
    try:
        from glconnect.book_platform_models import (
            BookReview, BookProject, ReviewerEarning,
            ReviewStatus, BookStatus, TransactionStatus
        )
        
        review = BookReview.query.get(review_id)
        if not review:
            return {'success': False, 'error': 'Review not found'}
        
        # Only process if review is published but book isn't
        if review.status != ReviewStatus.PUBLISHED:
            return {'success': False, 'error': 'Review not published'}
        
        book = review.book_project
        if book.status == BookStatus.PUBLISHED:
            return {'success': False, 'error': 'Book is published, no guarantee needed'}
        
        # Check if guarantee already paid
        existing_guarantee = ReviewerEarning.query.filter_by(
            review_id=review_id,
            is_guarantee_payment=True
        ).first()
        
        if existing_guarantee:
            return {'success': False, 'error': 'Guarantee already paid'}
        
        # Calculate guarantee amount
        # Use estimated book price or default
        estimated_book_price = book.price or 10.0  # Default $10
        agreed_revenue_share = review.revenue_share_percentage
        guarantee_amount = (estimated_book_price * (agreed_revenue_share / 100)) * (REVIEWER_GUARANTEE_PERCENTAGE / 100)
        
        # Create guarantee earning
        guarantee_earning = ReviewerEarning(
            reviewer_id=review.reviewer_id,
            review_id=review_id,
            amount=guarantee_amount,
            currency=book.currency or 'USD',
            status=TransactionStatus.PENDING,
            is_guarantee_payment=True,
            notes=f"Guarantee payment: Book not published within deadline"
        )
        db.session.add(guarantee_earning)
        
        # Update reviewer total earnings
        review.reviewer.total_earnings += guarantee_amount
        
        db.session.commit()
        
        logger.info(f"Processed guarantee payment of ${guarantee_amount} for reviewer {review.reviewer_id}")
        
        return {
            'success': True,
            'guarantee_amount': guarantee_amount,
            'earning_id': guarantee_earning.id
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing reviewer guarantee for review {review_id}: {str(e)}", exc_info=True)
        return {'success': False, 'error': str(e)}


def check_all_books_accountability(db):
    """
    Check accountability for all books with active campaigns or reviews.
    Run this as a scheduled task (daily cron job).
    """
    try:
        from glconnect.book_platform_models import (
            BookProject, InvestmentCampaign, CampaignStatus
        )
        
        # Get all books with funded campaigns
        funded_campaigns = InvestmentCampaign.query.filter_by(
            status=CampaignStatus.FUNDED
        ).all()
        
        results = []
        for campaign in funded_campaigns:
            result = check_author_accountability(campaign.book_project_id, db)
            results.append({
                'book_id': campaign.book_project_id,
                'result': result
            })
        
        return {
            'success': True,
            'books_checked': len(results),
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Error checking accountability for all books: {str(e)}", exc_info=True)
        return {'success': False, 'error': str(e)}


def get_accountability_status(book_id, db):
    """
    Get current accountability status for a book.
    
    Returns:
        dict: Status information including deadlines, warnings, etc.
    """
    try:
        from glconnect.book_platform_models import (
            BookProject, InvestmentCampaign, BookStatus, CampaignStatus
        )
        
        book = BookProject.query.get(book_id)
        if not book:
            return {'success': False, 'error': 'Book not found'}
        
        campaign = book.investment_campaign
        
        status = {
            'book_id': book_id,
            'book_status': book.status.value if book.status else None,
            'has_campaign': campaign is not None,
            'campaign_status': campaign.status.value if campaign else None,
            'deadlines': {},
            'warnings': [],
            'days_remaining': {}
        }
        
        if campaign and campaign.status == CampaignStatus.FUNDED:
            days_since_funding = (datetime.now(timezone.utc) - campaign.funded_at).days if campaign.funded_at else 0
            
            # Completion deadline
            completion_deadline = MAX_BOOK_COMPLETION_DAYS
            days_until_completion = completion_deadline - days_since_funding
            status['deadlines']['completion'] = {
                'deadline_days': completion_deadline,
                'days_remaining': max(0, days_until_completion),
                'days_elapsed': days_since_funding,
                'is_overdue': days_until_completion < 0
            }
            
            if days_until_completion < 0:
                status['warnings'].append(f"Completion deadline passed by {abs(days_until_completion)} days")
            
            # Publication deadline (if completed)
            if book.status == BookStatus.DRAFT:
                publication_deadline = MAX_BOOK_COMPLETION_DAYS + MAX_PUBLICATION_DAYS
                days_until_publication = publication_deadline - days_since_funding
                status['deadlines']['publication'] = {
                    'deadline_days': publication_deadline,
                    'days_remaining': max(0, days_until_publication),
                    'days_elapsed': days_since_funding,
                    'is_overdue': days_until_publication < 0
                }
                
                if days_until_publication < 0:
                    status['warnings'].append(f"Publication deadline passed by {abs(days_until_publication)} days")
        
        return {
            'success': True,
            'status': status
        }
        
    except Exception as e:
        logger.error(f"Error getting accountability status for book {book_id}: {str(e)}", exc_info=True)
        return {'success': False, 'error': str(e)}


