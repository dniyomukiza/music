"""
Revenue Distribution Service
Handles automatic distribution of revenue from book sales to authors and platform.

Accredited reviewer and funder/investor revenue share from sales are retired.
Campaign backers receive no share of marketplace sales (patronage only).
"""

from datetime import datetime, timezone
from sqlalchemy.orm import joinedload
import logging

logger = logging.getLogger(__name__)

# Revenue distribution percentages (configurable)
PLATFORM_FEE_PERCENTAGE = 10.0  # 10% to platform on marketplace sales
AUTHOR_BASE_PERCENTAGE = 90.0   # 90% to author on marketplace sales
REVIEWER_POOL_PERCENTAGE = 0.0  # Accredited reviewers retired


def distribute_revenue(book_sale, db):
    """
    Distribute revenue from a book sale to all parties.
    Earnings (reviewers, investors, author, platform) are computed from every
    BookSale regardless of sale_format: digital copy, audiobook, or bundle.
    
    Args:
        book_sale: BookSale object (sale_format: 'digital', 'audiobook', or 'bundle')
        db: SQLAlchemy database session
    
    Returns:
        dict: Distribution summary
    """
    try:
        from glconnect.book_platform_models import (
            BookProject, BookReview,
            RevenueDistribution, ReviewerEarning,
            DistributionType, TransactionStatus,
        )
        
        # Get the book project with all related data
        book = BookProject.query.options(
            joinedload(BookProject.accredited_reviews),
            joinedload(BookProject.investments),
            joinedload(BookProject.investment_campaign)
        ).get(book_sale.book_project_id)
        
        if not book:
            logger.error(f"Book project {book_sale.book_project_id} not found for sale {book_sale.id}")
            return {'success': False, 'error': 'Book not found'}
        
        # Check if already distributed
        if book_sale.distribution_completed:
            logger.warning(f"Sale {book_sale.id} already distributed")
            return {'success': False, 'error': 'Already distributed'}
        
        sale_amount = book_sale.net_amount + book_sale.platform_fee  # Total sale amount
        distributions = []
        
        # 1. Platform Fee (10%)
        platform_amount = sale_amount * (PLATFORM_FEE_PERCENTAGE / 100)
        platform_dist = RevenueDistribution(
            distribution_type=DistributionType.PLATFORM,
            amount=platform_amount,
            percentage=PLATFORM_FEE_PERCENTAGE,
            currency=book_sale.currency,
            status=TransactionStatus.COMPLETED,
            paid_at=datetime.now(timezone.utc),
            source_sale_id=book_sale.id,
            recipient_id=0,  # Platform
            recipient_type='platform'
        )
        db.session.add(platform_dist)
        distributions.append(('platform', platform_amount))
        
        # 2. Reviewer Distributions, retired (no new payouts from sales)
        reviewer_total = 0.0
        published_reviews = []
        if REVIEWER_POOL_PERCENTAGE > 0 and published_reviews:
            reviewer_pool = sale_amount * (REVIEWER_POOL_PERCENTAGE / 100)
            
            for review in published_reviews:
                # Check minimum sales threshold
                if book.total_sales < review.minimum_sales_threshold:
                    continue
                
                # Calculate reviewer's share
                reviewer_share = sale_amount * (review.revenue_share_percentage / 100)
                
                # Don't exceed the pool
                if reviewer_total + reviewer_share > reviewer_pool:
                    reviewer_share = reviewer_pool - reviewer_total
                
                if reviewer_share > 0:
                    # Create distribution
                    review_dist = RevenueDistribution(
                        distribution_type=DistributionType.REVIEWER,
                        amount=reviewer_share,
                        percentage=review.revenue_share_percentage,
                        currency=book_sale.currency,
                        status=TransactionStatus.PENDING,  # Will be paid later
                        source_sale_id=book_sale.id,
                        recipient_id=review.reviewer_id,
                        recipient_type='reviewer'
                    )
                    db.session.add(review_dist)
                    db.session.flush()  # Get the ID
                    
                    # Create reviewer earning record
                    earning = ReviewerEarning(
                        reviewer_id=review.reviewer_id,
                        review_id=review.id,
                        amount=reviewer_share,
                        currency=book_sale.currency,
                        status=TransactionStatus.PENDING,
                        distribution_id=review_dist.id
                    )
                    db.session.add(earning)
                    
                    # Update reviewer total earnings
                    review.reviewer.total_earnings += reviewer_share
                    
                    reviewer_total += reviewer_share
                    distributions.append(('reviewer', reviewer_share))
        
        # 3. Funder pool retired, patrons do not receive sale revenue
        investor_total = 0.0

        # 4. Author gets the remainder
        author_amount = sale_amount - platform_amount - reviewer_total - investor_total
        author_dist = RevenueDistribution(
            distribution_type=DistributionType.AUTHOR,
            amount=author_amount,
            percentage=(author_amount / sale_amount) * 100,
            currency=book_sale.currency,
            status=TransactionStatus.COMPLETED,
            paid_at=datetime.now(timezone.utc),
            source_sale_id=book_sale.id,
            recipient_id=book.author_id,
            recipient_type='author'
        )
        db.session.add(author_dist)
        distributions.append(('author', author_amount))
        
        # Update book sale tracking
        book_sale.distributed_to_reviewers = reviewer_total
        book_sale.distributed_to_investors = investor_total
        book_sale.distribution_completed = True
        
        # Update book totals
        book.total_sales += 1
        book.total_revenue += sale_amount
        
        db.session.commit()
        
        logger.info(f"Revenue distributed for sale {book_sale.id}: Platform=${platform_amount:.2f}, "
                   f"Reviewers=${reviewer_total:.2f}, Author=${author_amount:.2f}")
        
        return {
            'success': True,
            'distributions': distributions,
            'summary': {
                'platform': platform_amount,
                'reviewers': reviewer_total,
                'investors': investor_total,
                'author': author_amount,
                'total': sale_amount
            }
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error distributing revenue for sale {book_sale.id}: {str(e)}", exc_info=True)
        return {'success': False, 'error': str(e)}


def calculate_reviewer_earnings(review, sale_amount):
    """
    Calculate reviewer earnings from a book sale.
    
    Args:
        review: BookReview object
        sale_amount: Total sale amount
    
    Returns:
        float: Amount to pay reviewer
    """
    if review.book_project.total_sales < review.minimum_sales_threshold:
        return 0.0
    
    return sale_amount * (review.revenue_share_percentage / 100)

