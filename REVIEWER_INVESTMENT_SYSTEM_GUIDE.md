# Reviewer & Investment System Implementation Guide

## Overview
This feature enables:
1. **Accredited Book Reviewers** - Professional reviewers who earn revenue share on book sales
2. **Pre-Publication Investment** - Users can invest in books before publication and earn returns
3. **Democratized Publishing** - Eliminates upfront costs for debut authors while maintaining quality

---

## Architecture Overview

### Core Components
1. **Reviewer Accreditation System** - Verification and rating system
2. **Investment Marketplace** - Pre-publication funding platform
3. **Revenue Distribution Engine** - Automated profit sharing
4. **Trust & Credibility Layer** - Ratings, reviews, transparency

---

## Database Models

### 1. Accredited Reviewer Model
```python
class AccreditedReviewer(db.Model):
    __tablename__ = 'accredited_reviewers'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, unique=True)
    reviewer_name = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.Text, nullable=True)
    profile_picture = db.Column(db.String(200), nullable=True)
    
    # Accreditation Details
    accreditation_status = db.Column(db.Enum(ReviewerStatus), default=ReviewerStatus.PENDING)
    accreditation_level = db.Column(db.Enum(ReviewerLevel), default=ReviewerLevel.BRONZE)
    accreditation_date = db.Column(db.DateTime, nullable=True)
    accreditation_expires_at = db.Column(db.DateTime, nullable=True)
    
    # Credentials
    credentials = db.Column(JSON, nullable=True)  # Education, certifications, publications
    specialties = db.Column(JSON, nullable=True)  # Genres they review
    portfolio_url = db.Column(db.String(500), nullable=True)
    
    # Performance Metrics
    total_reviews = db.Column(db.Integer, default=0)
    average_rating = db.Column(db.Float, default=0.0)
    total_earnings = db.Column(db.Float, default=0.0)
    books_reviewed = db.Column(db.Integer, default=0)
    
    # Financial
    payment_info = db.Column(JSON, nullable=True)
    revenue_share_percentage = db.Column(db.Float, default=0.0)  # Negotiated per book
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = db.relationship('User', backref='reviewer_profile')
    reviews = db.relationship('BookReview', backref='reviewer', lazy=True)
    earnings = db.relationship('ReviewerEarning', backref='reviewer', lazy=True)
```

### 2. Book Review Model
```python
class BookReview(db.Model):
    __tablename__ = 'book_reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    
    # Review Content
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    is_featured = db.Column(db.Boolean, default=False)
    is_public = db.Column(db.Boolean, default=True)
    
    # Review Status
    status = db.Column(db.Enum(ReviewStatus), default=ReviewStatus.DRAFT)
    submitted_at = db.Column(db.DateTime, nullable=True)
    published_at = db.Column(db.DateTime, nullable=True)
    
    # Revenue Share Agreement
    revenue_share_percentage = db.Column(db.Float, nullable=False)  # e.g., 2.5% of sales
    minimum_sales_threshold = db.Column(db.Integer, default=0)  # Minimum sales before earning
    
    # Foreign Keys
    book_project_id = db.Column(db.Integer, db.ForeignKey('book_projects.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('accredited_reviewers.id'), nullable=False)
    
    # Relationships
    book_project = db.relationship('BookProject', backref='accredited_reviews')
    earnings = db.relationship('ReviewerEarning', backref='review', lazy=True)
```

### 3. Book Investment Model
```python
class BookInvestment(db.Model):
    __tablename__ = 'book_investments'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    
    # Investment Details
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    investment_percentage = db.Column(db.Float, nullable=False)  # % of total funding goal
    
    # Terms
    revenue_share_percentage = db.Column(db.Float, nullable=False)  # % of sales revenue
    return_multiplier = db.Column(db.Float, nullable=False)  # e.g., 1.5x return cap
    minimum_return = db.Column(db.Float, nullable=True)  # Guaranteed minimum return
    
    # Status
    status = db.Column(db.Enum(InvestmentStatus), default=InvestmentStatus.PENDING)
    payment_status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.PENDING)
    
    # Timeline
    invested_at = db.Column(db.DateTime, nullable=True)
    return_start_date = db.Column(db.DateTime, nullable=True)  # When returns begin
    return_end_date = db.Column(db.DateTime, nullable=True)  # When returns stop
    
    # Returns Tracking
    total_returns = db.Column(db.Float, default=0.0)
    last_payout_date = db.Column(db.DateTime, nullable=True)
    
    # Foreign Keys
    investor_id = db.Column(db.Integer, db.ForeignKey('book_platform_users.id'), nullable=False)
    book_project_id = db.Column(db.Integer, db.ForeignKey('book_projects.id'), nullable=False)
    
    # Relationships
    investor = db.relationship('BookPlatformUser', backref='investments')
    book_project = db.relationship('BookProject', backref='investments')
    payouts = db.relationship('InvestmentPayout', backref='investment', lazy=True)
```

### 4. Investment Campaign Model
```python
class InvestmentCampaign(db.Model):
    __tablename__ = 'investment_campaigns'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    
    # Campaign Details
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    pitch_video_url = db.Column(db.String(500), nullable=True)
    
    # Funding Goals
    funding_goal = db.Column(db.Float, nullable=False)
    minimum_investment = db.Column(db.Float, nullable=False)
    maximum_investment = db.Column(db.Float, nullable=True)
    current_funding = db.Column(db.Float, default=0.0)
    
    # Terms
    revenue_share_percentage = db.Column(db.Float, nullable=False)  # Total % shared with investors
    return_multiplier_cap = db.Column(db.Float, nullable=False)  # Max return (e.g., 3x)
    investment_period_days = db.Column(db.Integer, default=30)  # Days to reach goal
    
    # Status
    status = db.Column(db.Enum(CampaignStatus), default=CampaignStatus.DRAFT)
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    funded_at = db.Column(db.DateTime, nullable=True)
    
    # Foreign Keys
    book_project_id = db.Column(db.Integer, db.ForeignKey('book_projects.id'), nullable=False, unique=True)
    
    # Relationships
    book_project = db.relationship('BookProject', backref='investment_campaign', uselist=False)
    investments = db.relationship('BookInvestment', backref='campaign', lazy=True)
```

### 5. Revenue Distribution Model
```python
class RevenueDistribution(db.Model):
    __tablename__ = 'revenue_distributions'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    
    # Distribution Details
    distribution_type = db.Column(db.Enum(DistributionType), nullable=False)  # REVIEWER, INVESTOR, AUTHOR
    amount = db.Column(db.Float, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    
    # Status
    status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.PENDING)
    paid_at = db.Column(db.DateTime, nullable=True)
    payment_method = db.Column(db.String(50), nullable=True)
    transaction_id = db.Column(db.String(100), nullable=True)
    
    # Source
    source_sale_id = db.Column(db.Integer, db.ForeignKey('book_sales.id'), nullable=False)
    recipient_id = db.Column(db.Integer, nullable=False)  # Reviewer ID, Investor ID, or Author ID
    recipient_type = db.Column(db.String(50), nullable=False)  # 'reviewer', 'investor', 'author'
    
    # Relationships
    source_sale = db.relationship('BookSale', backref='distributions')
```

### 6. Enums
```python
class ReviewerStatus(PyEnum):
    PENDING = "pending"
    ACCREDITED = "accredited"
    SUSPENDED = "suspended"
    REVOKED = "revoked"

class ReviewerLevel(PyEnum):
    BRONZE = "bronze"  # New reviewers
    SILVER = "silver"  # Established reviewers
    GOLD = "gold"      # Expert reviewers
    PLATINUM = "platinum"  # Top-tier reviewers

class ReviewStatus(PyEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PUBLISHED = "published"
    REJECTED = "rejected"

class InvestmentStatus(PyEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class CampaignStatus(PyEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    FUNDED = "funded"
    FAILED = "failed"
    CANCELLED = "cancelled"

class DistributionType(PyEnum):
    REVIEWER = "reviewer"
    INVESTOR = "investor"
    AUTHOR = "author"
    PLATFORM = "platform"
```

---

## Business Logic & Revenue Distribution

### Revenue Distribution Formula

When a book is sold, revenue is distributed as follows:

```
Total Sale Price = $10.00

Distribution:
1. Platform Fee: 15% = $1.50
2. Author Base Share: 50% = $5.00
3. Reviewer Pool: 10% = $1.00 (split among reviewers based on their agreements)
4. Investor Pool: 25% = $2.50 (split among investors based on investment %)

Remaining to Author: $5.00 + any reviewer/investor shares if they didn't meet thresholds
```

### Example Scenarios

**Scenario 1: Book with 1 Reviewer (2% share) and 2 Investors**
- Sale: $10.00
- Platform: $1.50 (15%)
- Reviewer: $0.20 (2% of $10)
- Investor 1 (50% of funding): $1.25 (50% of $2.50 pool)
- Investor 2 (50% of funding): $1.25 (50% of $2.50 pool)
- Author: $5.80 (remaining)

**Scenario 2: Book with No Reviewer/Investor**
- Sale: $10.00
- Platform: $1.50 (15%)
- Author: $8.50 (85%)

### Reviewer Earnings Calculation
```python
def calculate_reviewer_earnings(review, book_sale):
    """
    Calculate reviewer earnings from a book sale
    
    Args:
        review: BookReview object with revenue_share_percentage
        book_sale: BookSale object with sale amount
    
    Returns:
        float: Amount to pay reviewer
    """
    if book_sale.book_project.total_sales < review.minimum_sales_threshold:
        return 0.0
    
    return book_sale.amount * (review.revenue_share_percentage / 100)
```

### Investor Returns Calculation
```python
def calculate_investor_returns(investment, book_sale, total_campaign_revenue_share):
    """
    Calculate investor returns from a book sale
    
    Args:
        investment: BookInvestment object
        book_sale: BookSale object
        total_campaign_revenue_share: Total % of revenue shared with all investors
    
    Returns:
        float: Amount to pay investor
    """
    # Calculate investor's share of the investor pool
    investor_share = investment.investment_percentage / 100
    
    # Calculate pool amount for this sale
    pool_amount = book_sale.amount * (total_campaign_revenue_share / 100)
    
    # Calculate investor's portion
    investor_return = pool_amount * investor_share
    
    # Apply return multiplier cap if applicable
    total_invested = investment.amount
    max_return = total_invested * investment.return_multiplier
    
    if investment.total_returns + investor_return > max_return:
        investor_return = max(0, max_return - investment.total_returns)
    
    return investor_return
```

---

## Implementation Phases

### Phase 1: Reviewer Accreditation System (Week 1-2)
**Goals:**
- Create reviewer registration and accreditation workflow
- Build reviewer profile pages
- Implement reviewer marketplace/discovery

**Tasks:**
1. Create database models (`AccreditedReviewer`, `BookReview`)
2. Build reviewer registration form with credential upload
3. Create admin accreditation approval system
4. Build reviewer marketplace page (browse available reviewers)
5. Create reviewer profile pages with ratings and portfolio
6. Implement reviewer search and filtering

**Routes:**
- `/reviewers/register` - Reviewer registration
- `/reviewers` - Reviewer marketplace
- `/reviewers/<id>` - Reviewer profile
- `/admin/reviewers/pending` - Admin approval queue
- `/admin/reviewers/<id>/approve` - Approve reviewer
- `/admin/reviewers/<id>/reject` - Reject reviewer

### Phase 2: Book Review Assignment System (Week 3)
**Goals:**
- Allow authors to request reviews
- Match reviewers with books
- Track review submissions

**Tasks:**
1. Create review request system
2. Build reviewer application/acceptance flow
3. Create review submission interface
4. Implement review publishing workflow
5. Add review display on book pages

**Routes:**
- `/books/<id>/request-review` - Author requests review
- `/books/<id>/reviews/apply` - Reviewer applies to review
- `/books/<id>/reviews/<review_id>/submit` - Submit review
- `/books/<id>/reviews` - View all reviews

### Phase 3: Investment Campaign System (Week 4-5)
**Goals:**
- Allow authors to create investment campaigns
- Enable users to invest in books
- Track funding progress

**Tasks:**
1. Create investment campaign models
2. Build campaign creation interface
3. Create investment marketplace
4. Implement investment flow (payment integration)
5. Build campaign progress tracking
6. Add investment terms calculator

**Routes:**
- `/books/<id>/create-campaign` - Create investment campaign
- `/investments` - Investment marketplace
- `/investments/<id>` - Campaign details
- `/investments/<id>/invest` - Make investment
- `/investments/my-investments` - User's investments

### Phase 4: Revenue Distribution Engine (Week 6)
**Goals:**
- Automatically calculate and distribute revenue
- Track all payouts
- Generate financial reports

**Tasks:**
1. Create revenue distribution service
2. Build automated payout system
3. Create distribution tracking
4. Implement payout notifications
5. Build financial dashboard for all parties

**Routes:**
- `/earnings` - View earnings (reviewers/investors/authors)
- `/earnings/payouts` - Payout history
- `/admin/revenue/distribute` - Manual distribution trigger
- `/admin/revenue/reports` - Financial reports

### Phase 5: Trust & Credibility Features (Week 7)
**Goals:**
- Build rating and review system
- Add transparency features
- Implement verification badges

**Tasks:**
1. Create reviewer rating system
2. Build investor rating/trust score
3. Add transparency dashboard (show revenue distribution)
4. Implement verification badges
5. Create dispute resolution system

**Routes:**
- `/reviewers/<id>/rate` - Rate reviewer
- `/transparency/<book_id>` - Revenue transparency
- `/disputes/create` - Create dispute
- `/admin/disputes` - Dispute management

---

## Key Features & User Flows

### Author Flow: Getting Reviewed & Funded
1. Author creates book project
2. Author requests review from accredited reviewers
3. Reviewers apply or are matched
4. Reviewer submits review (with revenue share agreement)
5. Author creates investment campaign
6. Investors browse and invest
7. Campaign reaches funding goal → book published
8. Sales generate revenue → automatic distribution

### Reviewer Flow: Earning from Reviews
1. User applies to become accredited reviewer
2. Admin reviews credentials and approves
3. Reviewer browses available books needing reviews
4. Reviewer applies to review specific books
5. Author accepts reviewer
6. Reviewer reads and submits review
7. Review published → reviewer earns % of sales
8. Reviewer receives automatic payouts as book sells

### Investor Flow: Investing in Books
1. User browses investment marketplace
2. User views campaign details (pitch, terms, progress)
3. User calculates potential returns
4. User invests (payment processed)
5. Campaign reaches goal → book published
6. Book sells → investor receives returns
7. Investor tracks returns in dashboard

---

## Security & Trust Considerations

### 1. Accreditation Verification
- Require credentials (education, publications, portfolio)
- Manual admin review process
- Background checks for high-level reviewers
- Ongoing performance monitoring

### 2. Investment Protection
- Escrow system for investments (hold funds until goal reached)
- Refund policy if campaign fails
- Clear terms and conditions
- Legal documentation for investments

### 3. Revenue Distribution Security
- Automated, transparent calculations
- Immutable transaction records
- Regular audits
- Dispute resolution mechanism

### 4. Fraud Prevention
- Rate limiting on investments
- Identity verification for large investments
- Review authenticity checks
- Anti-manipulation measures

---

## Payment Integration

### Required Payment Processors
1. **Stripe** - Primary payment processor
   - Handle investments
   - Process book purchases
   - Automated payouts to reviewers/investors

2. **PayPal** - Alternative payment method
   - For international users
   - Backup payment option

### Payment Flow
```python
# Investment Payment
1. User clicks "Invest"
2. Create payment intent with Stripe
3. Process payment
4. Create BookInvestment record
5. Update campaign funding
6. If goal reached → trigger book publication

# Revenue Distribution
1. Book sale occurs
2. Calculate all distributions
3. Create RevenueDistribution records
4. Queue payouts (Stripe Connect transfers)
5. Update recipient balances
6. Send notifications
```

---

## Database Schema Updates

### Add to BookProject Model
```python
# Add to existing BookProject
has_investment_campaign = db.Column(db.Boolean, default=False)
funding_goal = db.Column(db.Float, nullable=True)
current_funding = db.Column(db.Float, default=0.0)
total_sales = db.Column(db.Integer, default=0)
total_revenue = db.Column(db.Float, default=0.0)
```

### Add to BookSale Model
```python
# Add to existing BookSale
distributed_to_reviewers = db.Column(db.Float, default=0.0)
distributed_to_investors = db.Column(db.Float, default=0.0)
distribution_completed = db.Column(db.Boolean, default=False)
```

---

## API Endpoints

### Reviewer APIs
- `GET /api/reviewers` - List reviewers
- `GET /api/reviewers/<id>` - Get reviewer details
- `POST /api/reviewers/register` - Register as reviewer
- `POST /api/books/<id>/reviews/request` - Request review
- `POST /api/books/<id>/reviews/apply` - Apply to review
- `POST /api/reviews/<id>/submit` - Submit review

### Investment APIs
- `GET /api/investments` - List campaigns
- `GET /api/investments/<id>` - Get campaign details
- `POST /api/investments/<id>/invest` - Make investment
- `GET /api/investments/my-investments` - User's investments
- `GET /api/investments/<id>/returns` - Calculate returns

### Revenue APIs
- `GET /api/earnings` - Get user earnings
- `GET /api/earnings/payouts` - Payout history
- `POST /api/admin/revenue/distribute` - Trigger distribution

---

## UI/UX Considerations

### Reviewer Marketplace
- Filter by genre, rating, availability
- Show reviewer stats (reviews, earnings, rating)
- Display portfolio samples
- Easy application process

### Investment Marketplace
- Visual campaign progress bars
- ROI calculator
- Risk indicators
- Success stories
- Investment terms clearly displayed

### Transparency Dashboard
- Real-time revenue distribution
- Historical payout data
- Performance metrics
- Trust indicators

---

## Testing Strategy

### Unit Tests
- Revenue calculation formulas
- Investment return calculations
- Reviewer earnings calculations
- Distribution logic

### Integration Tests
- Payment processing flow
- Campaign funding flow
- Review submission flow
- Payout automation

### E2E Tests
- Complete author → reviewer → investor → sale flow
- Investment campaign lifecycle
- Revenue distribution cycle

---

## Monitoring & Analytics

### Key Metrics
- Reviewer application approval rate
- Average reviewer earnings
- Investment campaign success rate
- Average ROI for investors
- Revenue distribution accuracy
- Payout processing time

### Dashboards
- Admin dashboard (overview of all metrics)
- Reviewer dashboard (earnings, reviews, ratings)
- Investor dashboard (investments, returns, ROI)
- Author dashboard (funding, reviews, sales)

---

## Legal Considerations

1. **Investment Regulations**
   - May need SEC compliance (if treating as securities)
   - Consider crowdfunding regulations
   - Terms of service for investments

2. **Revenue Sharing Agreements**
   - Clear contracts for reviewers
   - Investment terms documentation
   - Tax implications documentation

3. **Dispute Resolution**
   - Clear policies
   - Mediation process
   - Arbitration clauses

---

## Next Steps

1. **Review this guide** with stakeholders
2. **Prioritize phases** based on business needs
3. **Design database schema** in detail
4. **Create wireframes** for key user flows
5. **Set up payment processing** (Stripe account)
6. **Begin Phase 1 implementation**

---

## Estimated Timeline

- **Phase 1**: 2 weeks
- **Phase 2**: 1 week
- **Phase 3**: 2 weeks
- **Phase 4**: 1 week
- **Phase 5**: 1 week

**Total: ~7 weeks** for full implementation

---

## Success Metrics

- Number of accredited reviewers
- Number of investment campaigns
- Campaign funding success rate
- Average reviewer earnings
- Average investor ROI
- Author satisfaction
- Platform revenue growth


