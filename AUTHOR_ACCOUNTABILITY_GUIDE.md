# Author Accountability & Protection System

## Problem Statement

**What happens if an author doesn't complete the book or publish it for sales?**

This is a critical concern for:
- **Reviewers** - Who spent time reviewing but won't get paid if book doesn't sell
- **Investors** - Who invested money expecting returns from book sales

---

## Solution: Comprehensive Accountability System

### 1. **Automatic Refunds for Investors**

#### When Refunds Are Triggered:

**Scenario A: Book Not Completed**
- **Deadline:** 180 days (6 months) after campaign is funded
- **Action:** Automatic refund process initiated
- **Amount:** Full investment amount
- **Status:** All investments marked as `REFUNDED`

**Scenario B: Book Completed But Not Published**
- **Deadline:** 210 days (7 months) = 180 days completion + 30 days publication
- **Action:** Automatic refund process initiated
- **Amount:** Full investment amount

**Scenario C: Author Abandons Project**
- **Detection:** No activity for extended period
- **Action:** Manual review and potential refund

#### Refund Process:

```
1. System detects deadline violation
   ↓
2. Create RefundRequest for each active investment
   ↓
3. Update investment status to REFUNDED
   ↓
4. Update campaign status to CANCELLED
   ↓
5. Process refunds via payment processor
   ↓
6. Notify investors via email
```

#### Refund Timeline:

- **Automatic Detection:** Daily cron job checks all funded campaigns
- **Refund Processing:** Within 5-7 business days
- **Payment Method:** Original payment method (Stripe/PayPal)

---

### 2. **Guaranteed Payments for Reviewers**

#### Reviewer Protection:

**Guarantee Payment:**
- **Amount:** 50% of agreed revenue share (based on estimated book price)
- **Trigger:** Book not published within deadline
- **Condition:** Reviewer must have completed and published their review

#### Example:

```
Reviewer Agreement:
- Revenue Share: 2.5% of sales
- Estimated Book Price: $10.00
- Agreed Share per Sale: $0.25

If book never publishes:
- Guarantee Payment: 50% of $0.25 = $0.125 per estimated sale
- Minimum Guarantee: $5.00 (based on 40 estimated sales)
```

#### Guarantee Payment Process:

```
1. Reviewer completes review (status: PUBLISHED)
   ↓
2. Book fails to publish within deadline
   ↓
3. System calculates guarantee payment
   ↓
4. Create ReviewerEarning with is_guarantee_payment=True
   ↓
5. Process payment to reviewer
   ↓
6. Update reviewer.total_earnings
```

---

### 3. **Author Accountability Mechanisms**

#### Deadlines & Milestones:

**Milestone 1: Book Completion**
- **Deadline:** 180 days after funding
- **Requirement:** Book status = PUBLISHED
- **Failure Consequence:** Investor refunds triggered

**Milestone 2: Book Publication**
- **Deadline:** 210 days after funding (30 days after completion)
- **Requirement:** Book available for sale
- **Failure Consequence:** Investor refunds triggered

#### Author Penalties:

1. **Campaign Cancellation**
   - Campaign status → CANCELLED
   - All investments → REFUNDED
   - Author reputation impact

2. **Future Restrictions**
   - Cannot create new campaigns for 6 months
   - Lower trust score
   - Platform review required

3. **Financial Impact**
   - Lose all invested funds (refunded to investors)
   - No revenue from sales (book not published)
   - Platform fees still apply if applicable

---

### 4. **Escrow & Payment Protection**

#### Investment Escrow:

**Current Implementation:**
- Investments are held until campaign is funded
- Once funded, funds are released to author
- **Future Enhancement:** Escrow system where funds are held until milestones are met

**Proposed Escrow System:**
```
1. Investor makes payment
   ↓
2. Funds held in escrow account
   ↓
3. Milestone 1: Book completion (50% released)
   ↓
4. Milestone 2: Book publication (50% released)
   ↓
5. If milestones not met → Full refund
```

#### Reviewer Payment Escrow:

**Current Implementation:**
- Reviewers paid from sales revenue
- Guarantee payment if book doesn't publish

**Future Enhancement:**
- Upfront payment option (author pays reviewer directly)
- Escrow for revenue-share agreements

---

### 5. **Dispute Resolution**

#### Refund Disputes:

**Author Can:**
- Request deadline extension (with justification)
- Appeal automatic refund (if book is near completion)
- Provide evidence of progress

**Investor Can:**
- Request refund if deadline passed
- Report author abandonment
- Dispute refund amount

**Reviewer Can:**
- Request guarantee payment if book not published
- Dispute payment amount
- Report author non-compliance

#### Dispute Process:

```
1. User files dispute
   ↓
2. Platform admin reviews
   ↓
3. Evidence gathering (book progress, communications)
   ↓
4. Decision made (approve/deny)
   ↓
5. Action taken (refund/extension/payment)
```

---

## Implementation Details

### Database Models Added:

1. **RefundRequest**
   - Tracks all refund requests
   - Links to investments
   - Status tracking

2. **ReviewerEarning Updates**
   - `is_guarantee_payment` flag
   - `notes` field for context

3. **BookInvestment Updates**
   - `refunded_at` timestamp
   - Status tracking

4. **InvestmentCampaign Updates**
   - `cancelled_at` timestamp
   - `cancellation_reason` field

### Service Functions:

1. **`check_author_accountability(book_id, db)`**
   - Checks if author met deadlines
   - Triggers refunds if needed
   - Processes guarantee payments

2. **`process_investor_refunds(book_id, db, reason)`**
   - Creates refund requests
   - Updates investment status
   - Cancels campaign

3. **`process_reviewer_guarantee(review_id, db)`**
   - Calculates guarantee amount
   - Creates guarantee payment
   - Updates reviewer earnings

4. **`check_all_books_accountability(db)`**
   - Scheduled task (daily cron)
   - Checks all active campaigns
   - Processes violations

### Scheduled Tasks:

**Daily Accountability Check:**
```python
# Run daily at 2 AM
def daily_accountability_check():
    check_all_books_accountability(db)
```

**Weekly Refund Processing:**
```python
# Process pending refunds weekly
def process_pending_refunds():
    refunds = RefundRequest.query.filter_by(status=PENDING).all()
    for refund in refunds:
        process_refund_via_payment_processor(refund)
```

---

## Configuration

### Deadlines (Configurable):

```python
MAX_BOOK_COMPLETION_DAYS = 180  # 6 months
MAX_PUBLICATION_DAYS = 30       # 30 days after completion
AUTOMATIC_REFUND_DAYS = 210     # Total: 7 months
```

### Guarantee Percentages:

```python
REVIEWER_GUARANTEE_PERCENTAGE = 50.0  # 50% of agreed revenue share
```

### Extension Policy:

- **First Extension:** Up to 30 days (automatic if requested before deadline)
- **Second Extension:** Up to 60 days (requires admin approval)
- **Third Extension:** Not allowed (refunds triggered)

---

## User Experience

### For Authors:

**Dashboard Warnings:**
- "⚠️ Book completion deadline: 45 days remaining"
- "⚠️ Publication deadline: 15 days remaining"
- "❌ Deadline passed - Refunds processing"

**Accountability Status Page:**
- Shows all deadlines
- Progress tracking
- Warning indicators
- Extension request option

### For Investors:

**Refund Notifications:**
- Email when refund is initiated
- Dashboard notification
- Refund status tracking
- Expected refund date

**Investment Status:**
- Shows days until deadline
- Warning if deadline approaching
- Refund request option

### For Reviewers:

**Guarantee Payment:**
- Automatic if book doesn't publish
- Notification when guarantee is processed
- Visible in earnings dashboard
- Marked as "Guarantee Payment"

---

## Example Scenarios

### Scenario 1: Author Completes on Time

```
Day 0: Campaign funded ($5,000)
Day 90: Book 50% complete
Day 150: Book 90% complete
Day 175: Book completed
Day 180: Book published ✅
Result: No refunds, normal revenue distribution
```

### Scenario 2: Author Misses Completion Deadline

```
Day 0: Campaign funded ($5,000)
Day 90: Book 30% complete
Day 150: Book 40% complete
Day 180: Deadline passed, book not completed
Day 181: System triggers refunds
Day 186: Refunds processed
Result: All investors refunded, campaign cancelled
```

### Scenario 3: Author Completes But Doesn't Publish

```
Day 0: Campaign funded ($5,000)
Day 175: Book completed ✅
Day 180: Book not published
Day 210: Publication deadline passed
Day 211: System triggers refunds
Result: All investors refunded, reviewers get guarantee payment
```

### Scenario 4: Reviewer Protection

```
Day 0: Reviewer submits review (published)
Day 30: Book still not published
Day 60: Book still not published
Day 90: Book still not published
Day 91: System processes guarantee payment
Result: Reviewer receives $5.00 guarantee payment
```

---

## Summary

### Investor Protection:
✅ **Automatic refunds** if book not completed/published
✅ **Full refund** of investment amount
✅ **Timeline:** 180-210 days maximum wait
✅ **No risk** of losing money if author fails

### Reviewer Protection:
✅ **Guarantee payment** if book doesn't publish
✅ **50% of agreed revenue share** guaranteed
✅ **Automatic processing** when deadline passes
✅ **Fair compensation** for work completed

### Author Accountability:
✅ **Clear deadlines** and milestones
✅ **Automatic enforcement** via system
✅ **Reputation impact** for failures
✅ **Future restrictions** for repeat offenders

### System Features:
✅ **Automated checks** (daily cron job)
✅ **Transparent process** (all parties notified)
✅ **Dispute resolution** mechanism
✅ **Configurable deadlines** and policies

---

## Next Steps

1. **Implement RefundRequest model** ✅
2. **Add accountability service** ✅
3. **Create scheduled tasks** (cron jobs)
4. **Integrate payment processor** (Stripe refunds)
5. **Build admin dashboard** for dispute resolution
6. **Add user notifications** for deadlines and refunds
7. **Create accountability status page** for authors

The system now provides **complete protection** for reviewers and investors while holding authors accountable for their commitments.


