# Earnings Workflow: How Reviewers & Investors Earn from Book Sales

## Overview

When a book is sold, revenue is automatically distributed to multiple parties based on pre-agreed percentages. This happens automatically with every sale.

---

## Revenue Distribution Breakdown

### Total Sale Amount: $10.00

```
┌─────────────────────────────────────────┐
│  Platform Fee:        15%  =  $1.50    │
│  Reviewer Pool:       10%  =  $1.00    │
│  Investor Pool:       25%  =  $2.50    │
│  Author (Remainder):  50%  =  $5.00    │
│                                         │
│  Total:              100%  = $10.00    │
└─────────────────────────────────────────┘
```

**Note:** The author gets 50% base + any unused portions from reviewer/investor pools if thresholds aren't met.

---

## 1. REVIEWER EARNINGS WORKFLOW

### How Reviewers Earn

**Step 1: Reviewer Submits Review**
- Reviewer reads the book
- Submits review with agreed revenue share (e.g., 2.5%)
- Sets minimum sales threshold (e.g., 0 = earn from first sale, or 100 = earn after 100 sales)

**Step 2: Book Sale Occurs**
- Customer purchases book for $10.00
- System triggers revenue distribution

**Step 3: Reviewer Earnings Calculation**
```python
# Example: Reviewer with 2.5% revenue share
Sale Amount = $10.00
Reviewer Share = $10.00 × 2.5% = $0.25 per sale

# If minimum sales threshold = 50, and book has sold 45 copies:
# Reviewer earns $0.00 (threshold not met)

# If book has sold 51 copies:
# Reviewer earns $0.25 per sale going forward
```

**Step 4: Earnings Accumulation**
- Each sale generates earnings
- Earnings accumulate in `ReviewerEarning` records
- Total tracked in `AccreditedReviewer.total_earnings`

**Step 5: Payout**
- Earnings are marked as `PENDING`
- Can be paid out via Stripe/PayPal (when integrated)
- Status changes to `COMPLETED` when paid

### Reviewer Earnings Example

**Scenario:**
- Book price: $10.00
- Reviewer revenue share: 2.5%
- Minimum sales threshold: 0 (earn from first sale)
- Book sells 100 copies

**Calculation:**
```
Total Sales Revenue = $10.00 × 100 = $1,000.00
Reviewer Earnings = $1,000.00 × 2.5% = $25.00
```

**Per Sale:**
- Sale #1: $0.25
- Sale #2: $0.25
- Sale #3: $0.25
- ...
- Sale #100: $0.25
- **Total: $25.00**

### Multiple Reviewers

If a book has 2 reviewers:
- Reviewer A: 2.5% share
- Reviewer B: 3.0% share
- Total reviewer pool: 10% of sales

**Sale of $10.00:**
```
Reviewer Pool = $10.00 × 10% = $1.00

Reviewer A gets: $10.00 × 2.5% = $0.25
Reviewer B gets: $10.00 × 3.0% = $0.30
Total distributed: $0.55

Remaining in pool: $0.45 (goes back to author)
```

---

## 2. INVESTOR EARNINGS WORKFLOW

### How Investors Earn

**Step 1: Investment Campaign Created**
- Author creates campaign with terms:
  - Funding goal: $5,000
  - Revenue share: 25% (total shared with all investors)
  - Return multiplier cap: 3x (max 3x investment)

**Step 2: Investors Contribute**
- Investor A: $2,500 (50% of goal)
- Investor B: $2,500 (50% of goal)
- Campaign reaches goal → Book published

**Step 3: Book Sale Occurs**
- Customer purchases book for $10.00
- System calculates investor returns

**Step 4: Investor Returns Calculation**
```python
# Step 1: Calculate investor pool
Investor Pool = $10.00 × 25% = $2.50

# Step 2: Calculate each investor's share based on investment %
Total Investment = $5,000
Investor A invested = $2,500 (50% of total)
Investor B invested = $2,500 (50% of total)

# Step 3: Distribute pool proportionally
Investor A's share = $2.50 × 50% = $1.25
Investor B's share = $2.50 × 50% = $1.25
```

**Step 5: Apply Return Multiplier Cap**
```python
# Investor A invested $2,500
# Max return = $2,500 × 3x = $7,500

# After 1,000 sales:
# Investor A earned: $1.25 × 1,000 = $1,250
# Still under cap, so continues earning

# After 6,000 sales:
# Investor A earned: $1.25 × 6,000 = $7,500
# Reached cap! No more earnings for Investor A
# Investor B continues earning until their cap
```

**Step 6: Payout**
- Returns accumulate in `InvestmentPayout` records
- Tracked in `BookInvestment.total_returns`
- Can be paid out periodically or when threshold reached

### Investor Earnings Example

**Scenario:**
- Book price: $10.00
- Campaign revenue share: 25%
- Investor A: Invested $1,000 (20% of $5,000 goal)
- Investor B: Invested $4,000 (80% of $5,000 goal)
- Return multiplier cap: 3x
- Book sells 500 copies

**Calculation:**
```
Total Sales Revenue = $10.00 × 500 = $5,000.00
Investor Pool = $5,000.00 × 25% = $1,250.00

Investor A's share = $1,250.00 × 20% = $250.00
Investor B's share = $1,250.00 × 80% = $1,000.00

Investor A ROI = $250.00 / $1,000.00 = 25% return
Investor B ROI = $1,000.00 / $4,000.00 = 25% return

Max returns:
- Investor A max: $1,000 × 3x = $3,000 (not reached)
- Investor B max: $4,000 × 3x = $12,000 (not reached)
```

**Per Sale Breakdown:**
- Sale #1: Investor A gets $0.50, Investor B gets $2.00
- Sale #2: Investor A gets $0.50, Investor B gets $2.00
- ...
- Sale #500: Investor A gets $0.50, Investor B gets $2.00

---

## 3. COMPLETE EARNINGS WORKFLOW

### Step-by-Step Process

```
1. CUSTOMER PURCHASES BOOK
   └─> BookPurchase record created
   └─> Payment processed ($10.00)
   
2. BOOK SALE RECORDED
   └─> BookSale record created
   └─> Status: COMPLETED
   
3. REVENUE DISTRIBUTION TRIGGERED
   └─> distribute_revenue() function called
   
4. PLATFORM FEE DISTRIBUTED
   └─> $1.50 → Platform (15%)
   └─> RevenueDistribution record created
   └─> Status: COMPLETED (paid immediately)
   
5. REVIEWER EARNINGS CALCULATED
   └─> Check each published review
   └─> Check minimum sales threshold
   └─> Calculate: Sale Amount × Reviewer %
   └─> Create ReviewerEarning record
   └─> Update reviewer.total_earnings
   └─> Status: PENDING (paid later)
   
6. INVESTOR RETURNS CALCULATED
   └─> Check if campaign is FUNDED
   └─> Calculate investor pool (25% of sale)
   └─> Distribute proportionally by investment %
   └─> Apply return multiplier cap
   └─> Create InvestmentPayout record
   └─> Update investment.total_returns
   └─> Status: PENDING (paid later)
   
7. AUTHOR EARNINGS
   └─> Calculate remainder after all distributions
   └─> Author gets: Sale - Platform - Reviewers - Investors
   └─> Create RevenueDistribution record
   └─> Status: COMPLETED
   
8. UPDATE BOOK STATISTICS
   └─> book.total_sales += 1
   └─> book.total_revenue += sale_amount
   └─> book_sale.distribution_completed = True
```

---

## 4. REAL-WORLD EXAMPLE

### Book: "The Adventure Novel"
- **Price:** $12.99
- **Author:** Debut Author
- **Reviewers:** 2 accredited reviewers
- **Investors:** 3 investors

### Campaign Setup:
- Funding goal: $3,000
- Revenue share: 25%
- Return cap: 3x

### Investments:
- Investor 1: $1,000 (33.3%)
- Investor 2: $1,000 (33.3%)
- Investor 3: $1,000 (33.3%)

### Reviews:
- Reviewer A: 2.5% share, no threshold
- Reviewer B: 3.0% share, 50 sales threshold

### Sale #1 ($12.99):
```
Total Sale: $12.99

Platform Fee:     $1.95  (15%)
Reviewer Pool:    $1.30  (10%)
Investor Pool:    $3.25  (25%)
Author Base:      $6.49  (50%)

Reviewer A:       $0.32  (2.5% of $12.99)
Reviewer B:       $0.00  (threshold not met - 0 sales < 50)
Investor 1:       $1.08  (33.3% of $3.25)
Investor 2:       $1.08  (33.3% of $3.25)
Investor 3:       $1.08  (33.3% of $3.25)

Author gets:      $6.49 + $0.98 (unused reviewer B share) = $7.47
```

### Sale #51 ($12.99):
```
(Now Reviewer B threshold is met)

Total Sale: $12.99

Platform Fee:     $1.95
Reviewer Pool:    $1.30
Investor Pool:    $3.25
Author Base:      $6.49

Reviewer A:       $0.32  (2.5%)
Reviewer B:       $0.39  (3.0%) ✅ Now earning!
Investor 1:       $1.08
Investor 2:       $1.08
Investor 3:       $1.08

Author gets:      $6.49 + $0.59 (unused pool) = $7.08
```

### After 1,000 Sales:
```
Total Revenue: $12,990.00

Platform:      $1,948.50
Reviewers:     $1,300.00 (distributed to A & B)
Investors:     $3,250.00 (distributed to 1, 2, 3)
Author:        $6,491.50

Reviewer A Total:    $324.75 (2.5% × 1,000 sales)
Reviewer B Total:    $975.25 (3.0% × 950 sales, started at sale 51)

Investor 1 Total:    $1,083.33 (33.3% of pool)
Investor 2 Total:    $1,083.33
Investor 3 Total:    $1,083.33

ROI for Investors:
- Each invested $1,000
- Each earned $1,083.33
- ROI: 8.3% (and growing with more sales)
- Max possible: $3,000 each (3x cap)
```

---

## 5. EARNINGS TRACKING

### Database Records Created Per Sale:

1. **BookPurchase** - Customer purchase record
2. **BookSale** - Author sale record
3. **RevenueDistribution** (Platform) - Platform fee
4. **RevenueDistribution** (Reviewer) - For each reviewer
5. **ReviewerEarning** - Tracks reviewer earnings
6. **RevenueDistribution** (Investor) - For each investor
7. **InvestmentPayout** - Tracks investor returns
8. **RevenueDistribution** (Author) - Author remainder

### Earnings Dashboard Shows:

**For Reviewers:**
- Total earnings across all books
- Earnings per book/review
- Payout history
- Pending earnings

**For Investors:**
- Total returns across all investments
- Returns per investment
- ROI percentage
- Progress toward return cap
- Payout history

**For Authors:**
- Total sales revenue
- Net earnings after distributions
- Sales per book
- Revenue trends

---

## 6. PAYOUT PROCESS

### Current Implementation:
- Earnings are calculated and recorded immediately
- Status: `PENDING` (awaiting payment)
- Can be paid manually or via automated system

### Future Integration (Recommended):
1. **Stripe Connect** - Automated payouts
2. **PayPal Payouts** - Batch payments
3. **Minimum Payout Threshold** - e.g., $50 minimum
4. **Payout Schedule** - Weekly/Monthly batches
5. **Tax Documentation** - 1099 forms for US

### Payout Flow:
```
1. Earnings accumulate in database
2. Reach minimum threshold ($50)
3. Payout request created
4. Payment processed (Stripe/PayPal)
5. Status: COMPLETED
6. Transaction ID recorded
7. Email notification sent
```

---

## 7. KEY FEATURES

### For Reviewers:
✅ **Revenue Share Agreement** - Set at review submission
✅ **Minimum Sales Threshold** - Earn after X sales
✅ **Automatic Calculation** - No manual tracking needed
✅ **Earnings Dashboard** - View all earnings
✅ **Per-Sale Tracking** - See earnings from each sale

### For Investors:
✅ **Proportional Distribution** - Based on investment %
✅ **Return Cap Protection** - Max 3x prevents unlimited liability
✅ **Transparent Calculations** - See exactly how returns work
✅ **Investment Dashboard** - Track all investments
✅ **ROI Tracking** - See return on investment percentage

### For Authors:
✅ **Automatic Distribution** - No manual work
✅ **Transparent System** - See where revenue goes
✅ **Remainder Protection** - Get unused pool amounts
✅ **Sales Tracking** - Monitor book performance

---

## 8. EXAMPLE SCENARIOS

### Scenario A: Successful Book (High Sales)
- Book sells 10,000 copies at $10.00
- Total revenue: $100,000

**Distribution:**
- Platform: $15,000
- Reviewers: $10,000 (split among reviewers)
- Investors: $25,000 (split proportionally, capped at 3x)
- Author: $50,000 + any unused portions

**Investor Returns:**
- If investor put in $1,000
- Max return: $3,000 (3x cap)
- After 1,200 sales, investor hits cap
- No more earnings after cap reached

### Scenario B: Slow Start (Low Sales)
- Book sells 50 copies at $10.00
- Total revenue: $500

**Distribution:**
- Platform: $75
- Reviewers: $50 (if thresholds met)
- Investors: $125 (if campaign funded)
- Author: $250

**Note:** Small sales still generate earnings, just smaller amounts.

### Scenario C: No Reviewers/Investors
- Book has no reviewers or investors
- Book sells for $10.00

**Distribution:**
- Platform: $1.50 (15%)
- Author: $8.50 (85%)

**Simple case:** Author gets most of the revenue.

---

## 9. IMPORTANT NOTES

### Reviewer Thresholds:
- If threshold not met, reviewer earns $0
- Threshold is checked per sale
- Once met, reviewer earns on all future sales

### Investor Return Caps:
- Protects authors from unlimited liability
- Once cap reached, investor stops earning
- Different investors can have different caps
- Cap is per investment, not per campaign

### Platform Fee:
- Always 15% (configurable)
- Paid immediately
- Used for platform maintenance

### Author Protection:
- Author always gets at least 50% base
- Gets unused portions from pools
- Protected from excessive distributions

---

## 10. AUTOMATION

The system is **fully automated**:
- ✅ Triggers on every sale
- ✅ Calculates all distributions
- ✅ Creates tracking records
- ✅ Updates statistics
- ✅ No manual intervention needed

**Manual Steps (Future):**
- Payout processing (can be automated with Stripe)
- Tax documentation
- Dispute resolution

---

## Summary

**Reviewers earn:** Percentage of each sale (after threshold met)
**Investors earn:** Proportional share of investor pool (capped at multiplier)
**Authors earn:** Base 50% + remainder from unused pools
**Platform earns:** Fixed 15% fee

All calculations are automatic, transparent, and tracked in the database.


