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

# Campaign fund release - safeguard for investors (author gets 50% at first draft, 50% at publication)
FIRST_DRAFT_RELEASE_PERCENT = 50.0
PUBLICATION_RELEASE_PERCENT = 50.0
FIRST_DRAFT_MIN_WORDS = 25000  # Full first draft = at least 25,000 words


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
        
        from glconnect.book_utils import is_book_published
        
        # Check investment campaign status
        campaign = book.investment_campaign
        if campaign and campaign.status == CampaignStatus.FUNDED:
            days_since_funding = (datetime.now(timezone.utc) - campaign.funded_at).days if campaign.funded_at else 0
            
            # Check if book is completed (platform: status; uploaded: digital_book_published/audiobook_published)
            is_completed = is_book_published(book)
            is_draft = not is_completed
            
            # Check completion deadline - first draft not out, so investors can get refunds
            if not is_completed and days_since_funding > MAX_BOOK_COMPLETION_DAYS:
                warnings.append(f"Book not completed after {days_since_funding} days (deadline: {MAX_BOOK_COMPLETION_DAYS} days)")
                refund_result = process_investor_refunds(book_id, db, reason="Book not completed within deadline")
                if refund_result.get('success'):
                    actions_taken.append(f"Created refund requests for {refund_result.get('refunded_count', 0)} investors")
            
            # Check publication deadline (first draft done but not published - no refunds, sales final)
            elif is_draft and days_since_funding > (MAX_BOOK_COMPLETION_DAYS + MAX_PUBLICATION_DAYS):
                warnings.append(f"Book completed but not published after {days_since_funding} days")
        
        # Accredited reviewer guarantees retired, no new reviewer payouts from accountability checks
        
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
    Create refund requests for investors when author fails to deliver first draft.
    Only applies before first draft (25k+ words) - investors can get refunds.
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
        for investment in investments:
            existing_refund = RefundRequest.query.filter_by(
                investment_id=investment.id,
                status=TransactionStatus.PENDING
            ).first()
            if existing_refund:
                continue
            
            refund = RefundRequest(
                investment_id=investment.id,
                amount=investment.amount,
                currency=investment.currency,
                reason=reason,
                status=TransactionStatus.PENDING
            )
            db.session.add(refund)
            refunded_count += 1
        
        db.session.commit()
        logger.info(f"Created {refunded_count} refund requests for book {book_id}")
        return {'success': True, 'refunded_count': refunded_count}
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating investor refunds for book {book_id}: {str(e)}", exc_info=True)
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
        from glconnect.book_utils import is_book_published
        if is_book_published(book):
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


def can_request_first_draft_release(book, campaign, db):
    """
    Check if author can request first-draft fund release (50% of campaign funds).
    Requires: full first draft = at least FIRST_DRAFT_MIN_WORDS and chapters with content.
    """
    from glconnect.book_platform_models import CampaignStatus
    if not campaign or campaign.status != CampaignStatus.FUNDED:
        return False, "Campaign not funded"
    if campaign.author_first_draft_released:
        return False, "First draft release already granted"
    if campaign.current_funding <= 0:
        return False, "No campaign funds"
    
    # Platform-created books: need chapters + word count
    try:
        from glconnect.book_platform_routes import update_book_word_count
        update_book_word_count(book)
    except Exception:
        pass
    
    word_count = book.word_count or 0
    if word_count < FIRST_DRAFT_MIN_WORDS:
        return False, f"Full first draft requires at least {FIRST_DRAFT_MIN_WORDS:,} words (you have {word_count:,})"
    
    # Check for pending request
    from glconnect.book_platform_models import AuthorCampaignPayoutRequest
    pending = AuthorCampaignPayoutRequest.query.filter_by(
        campaign_id=campaign.id, milestone='first_draft', status='pending'
    ).first()
    if pending:
        return False, "You already have a pending first draft release request"
    
    return True, None


def can_request_publication_release(book, campaign, db):
    """
    Check if author can request publication fund release (remaining 50%).
    Requires: book published to marketplace.
    """
    from glconnect.book_platform_models import CampaignStatus, BookStatus
    if not campaign or campaign.status != CampaignStatus.FUNDED:
        return False, "Campaign not funded"
    if not campaign.author_first_draft_released:
        return False, "First draft release must be granted before publication release"
    if campaign.author_publication_released:
        return False, "Publication release already granted"
    if campaign.current_funding <= 0:
        return False, "No campaign funds"
    
    if book.status != BookStatus.PUBLISHED:
        return False, "Book must be published to marketplace first"
    
    from glconnect.book_platform_models import AuthorCampaignPayoutRequest
    pending = AuthorCampaignPayoutRequest.query.filter_by(
        campaign_id=campaign.id, milestone='publication', status='pending'
    ).first()
    if pending:
        return False, "You already have a pending publication release request"
    
    return True, None


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


