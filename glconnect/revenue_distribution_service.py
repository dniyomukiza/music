"""
Revenue Distribution Service
Handles automatic distribution of revenue from book sales to:
- Authors
- Accredited Reviewers
- Investors
- Platform
"""

from datetime import datetime, timezone
from sqlalchemy.orm import joinedload
import logging

logger = logging.getLogger(__name__)

# Revenue distribution percentages (configurable)
PLATFORM_FEE_PERCENTAGE = 15.0  # 15% to platform
AUTHOR_BASE_PERCENTAGE = 50.0   # 50% base to author
REVIEWER_POOL_PERCENTAGE = 10.0  # 10% pool for reviewers
INVESTOR_POOL_PERCENTAGE = 25.0  # 25% pool for investors


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
            BookProject, BookReview, BookInvestment, InvestmentCampaign,
            RevenueDistribution, ReviewerEarning, InvestmentPayout,
            DistributionType, TransactionStatus, ReviewStatus, CampaignStatus
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
        
        # 1. Platform Fee (15%)
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
        
        # 2. Reviewer Distributions (from 10% pool)
        reviewer_total = 0.0
        published_reviews = [r for r in book.accredited_reviews 
                           if r.status == ReviewStatus.PUBLISHED]
        
        if published_reviews:
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
        
        # 3. Investor Distributions (from 25% pool)
        investor_total = 0.0
        campaign = book.investment_campaign
        
        # Handle case where investment_campaign might be a list (if relationship is misconfigured)
        if isinstance(campaign, list):
            campaign = campaign[0] if len(campaign) > 0 else None
        
        if not campaign:
            logger.info(f"No investment campaign found for book {book.id} - skipping investor distributions")
        elif campaign.status not in [CampaignStatus.FUNDED, CampaignStatus.ACTIVE]:
            logger.info(f"Campaign {campaign.id} for book {book.id} is not FUNDED or ACTIVE (status: {campaign.status.value}) - skipping investor distributions")
        else:
            # Allow distributions for both FUNDED and ACTIVE campaigns
            # Investors should get returns as soon as they invest and book sells, even if campaign isn't fully funded
            active_investments = [inv for inv in book.investments 
                                if inv.status.value in ['confirmed', 'active']]
            
            if not active_investments:
                logger.info(f"No active investments found for book {book.id} (campaign {campaign.id}) - skipping investor distributions")
            else:
                investor_pool = sale_amount * (INVESTOR_POOL_PERCENTAGE / 100)
                total_investment_amount = sum(inv.amount for inv in active_investments)
                
                for investment in active_investments:
                    # Calculate investor's share based on their investment percentage
                    investment_share = (investment.amount / total_investment_amount) if total_investment_amount > 0 else 0
                    investor_return = investor_pool * investment_share
                    
                    # Apply return multiplier cap - ensure returns increment until max is reached
                    max_return = investment.amount * investment.return_multiplier
                    current_returns = investment.total_returns
                    
                    # If investor has already reached max, skip distribution (share goes to author)
                    if current_returns >= max_return:
                        logger.info(f"Investor {investment.investor_id} (investment {investment.id}) has reached max return cap "
                                  f"(${current_returns:.2f} / ${max_return:.2f}) - skipping distribution")
                        continue
                    
                    # Cap the return if it would exceed the maximum
                    if current_returns + investor_return > max_return:
                        investor_return = max_return - current_returns
                        logger.info(f"Investor {investment.investor_id} (investment {investment.id}) return capped: "
                                  f"${investor_return:.2f} (would have been ${investor_pool * investment_share:.2f}, "
                                  f"but max is ${max_return:.2f}, current is ${current_returns:.2f})")
                    
                    if investor_return > 0:
                        # Create distribution
                        inv_dist = RevenueDistribution(
                            distribution_type=DistributionType.INVESTOR,
                            amount=investor_return,
                            percentage=(investor_return / sale_amount) * 100,
                            currency=book_sale.currency,
                            status=TransactionStatus.PENDING,  # Will be paid later
                            source_sale_id=book_sale.id,
                            recipient_id=investment.investor_id,
                            recipient_type='investor'
                        )
                        db.session.add(inv_dist)
                        db.session.flush()  # Get the ID
                        
                        # Create investment payout record
                        payout = InvestmentPayout(
                            investment_id=investment.id,
                            amount=investor_return,
                            currency=book_sale.currency,
                            status=TransactionStatus.PENDING,
                            distribution_id=inv_dist.id
                        )
                        db.session.add(payout)
                        
                        # Update investment returns - this increments on every sale until max is reached
                        investment.total_returns += investor_return
                        investment.last_payout_date = datetime.now(timezone.utc)
                        
                        logger.info(f"Investor {investment.investor_id} (investment {investment.id}): "
                                  f"Added ${investor_return:.2f}, Total returns now: ${investment.total_returns:.2f} / "
                                  f"Max: ${max_return:.2f} ({(investment.total_returns / max_return * 100) if max_return > 0 else 0:.1f}%)")
                        
                        investor_total += investor_return
                        distributions.append(('investor', investor_return))
        
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
                   f"Reviewers=${reviewer_total:.2f}, Investors=${investor_total:.2f}, Author=${author_amount:.2f}")
        
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


def calculate_investor_returns(investment, sale_amount, total_campaign_revenue_share, total_investment_amount):
    """
    Calculate investor returns from a book sale.
    
    Args:
        investment: BookInvestment object
        sale_amount: Total sale amount
        total_campaign_revenue_share: Total % of revenue shared with all investors
        total_investment_amount: Total amount invested in the campaign
    
    Returns:
        float: Amount to pay investor
    """
    # Calculate investor's share of the investor pool
    investor_share = investment.amount / total_investment_amount if total_investment_amount > 0 else 0
    
    # Calculate pool amount for this sale
    pool_amount = sale_amount * (total_campaign_revenue_share / 100)
    
    # Calculate investor's portion
    investor_return = pool_amount * investor_share
    
    # Apply return multiplier cap if applicable
    total_invested = investment.amount
    max_return = total_invested * investment.return_multiplier
    
    if investment.total_returns + investor_return > max_return:
        investor_return = max(0, max_return - investment.total_returns)
    
    return investor_return

