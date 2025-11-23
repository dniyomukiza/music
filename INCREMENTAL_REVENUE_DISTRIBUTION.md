# Incremental Revenue Distribution - How It Works

## Overview
Revenue distributions increment automatically on **every book sale** until each investor reaches their maximum return cap. This document explains how the system ensures continuous, incremental distributions.

## How It Works

### 1. Distribution Trigger
**Every time a book is sold:**
- `BookPurchase` is created
- `BookSale` is created
- `distribute_revenue(sale, db)` is **automatically called**
- Distribution runs **immediately** (not batched or delayed)

### 2. Distribution Process for Each Sale

For each book sale, the system:

1. **Calculates Investor Pool**
   - 25% of sale amount goes to investors
   - Example: $20 sale → $5.00 investor pool

2. **Distributes to Each Active Investor**
   - Calculates each investor's share based on their investment percentage
   - Example: Investor with 50% of total funding gets 50% of the pool
   - $5.00 pool × 50% = $2.50 per sale

3. **Applies Return Cap**
   - Checks if `total_returns + new_return > max_return`
   - Max return = `investment.amount × return_multiplier`
   - Example: $100 investment × 3x multiplier = $300 max return

4. **Increments Returns**
   - Updates `investment.total_returns += investor_return`
   - Creates `InvestmentPayout` record
   - Creates `RevenueDistribution` record
   - Logs the increment

5. **Continues Until Cap Reached**
   - Distribution continues for every sale
   - Each sale increments `total_returns`
   - Once `total_returns >= max_return`, that investor stops receiving distributions
   - Their share goes to the author instead

### 3. Example: Incremental Distribution

**Scenario:**
- Investment: $100
- Return multiplier: 3x (max return = $300)
- Investor share: 50% of investor pool
- Book price: $20
- Investor pool per sale: $5.00 (25% of $20)
- Investor return per sale: $2.50 (50% of $5.00)

**Sale-by-Sale Distribution:**

| Sale # | Sale Amount | Investor Pool | Investor Return | Total Returns | Status |
|--------|-------------|---------------|-----------------|---------------|--------|
| 1     | $20.00      | $5.00         | $2.50           | $2.50         | ✅ Active |
| 2     | $20.00      | $5.00         | $2.50           | $5.00         | ✅ Active |
| 3     | $20.00      | $5.00         | $2.50           | $7.50         | ✅ Active |
| ...   | ...         | ...           | ...              | ...           | ... |
| 120   | $20.00      | $5.00         | $2.50           | $300.00       | ✅ **CAP REACHED** |
| 121   | $20.00      | $5.00         | $0.00           | $300.00       | ⏹️ Stopped (share goes to author) |

**Key Points:**
- Returns increment on **every sale** (Sale 1, 2, 3, ... 120)
- Each sale adds $2.50 to `total_returns`
- After 120 sales, investor reaches $300 cap
- Sale 121 and beyond: Investor gets $0 (their share goes to author)

## Code Flow

### Distribution Trigger (purchase_book route)
```python
# Every purchase triggers distribution
sale = BookSale(...)
db.session.add(sale)
db.session.commit()

# Automatic distribution
distribute_revenue(sale, db)  # ← Called immediately
```

### Distribution Logic (distribute_revenue function)
```python
for investment in active_investments:
    # Calculate return for this sale
    investor_return = investor_pool * investment_share
    
    # Check cap
    max_return = investment.amount * investment.return_multiplier
    if investment.total_returns >= max_return:
        continue  # Skip - already at cap
    
    # Cap if would exceed
    if investment.total_returns + investor_return > max_return:
        investor_return = max_return - investment.total_returns
    
    # Increment returns
    investment.total_returns += investor_return  # ← Increments on every sale
    
    # Create records
    create_payout(investment, investor_return)
    create_distribution(investor_return)
```

## Guarantees

✅ **Distributions run on every sale**
- No batching or delays
- Immediate execution after purchase

✅ **Returns increment continuously**
- Each sale adds to `total_returns`
- No gaps or missed distributions

✅ **Cap is respected**
- Returns stop when `total_returns >= max_return`
- No over-distribution

✅ **Multiple investors supported**
- Each investor's returns tracked independently
- One investor reaching cap doesn't affect others

✅ **Automatic and transparent**
- No manual intervention needed
- All distributions logged and tracked

## Database Updates

**On each sale, these are updated:**
- `investment.total_returns` ← Incremented
- `investment.last_payout_date` ← Updated
- `book_sale.distribution_completed` ← Set to True
- `book_sale.distributed_to_investors` ← Updated

**Records created:**
- `InvestmentPayout` record (one per investor per sale)
- `RevenueDistribution` record (one per investor per sale)

## Monitoring & Logging

The system logs:
- Each distribution amount
- Total returns after each sale
- Progress toward cap (percentage)
- When cap is reached
- When investor is skipped (already at cap)

**Example log output:**
```
Investor 123 (investment 456): Added $2.50, Total returns now: $150.00 / Max: $300.00 (50.0%)
```

## Verification

To verify distributions are incrementing:

1. **Check investment returns:**
   ```sql
   SELECT id, amount, total_returns, return_multiplier,
          (amount * return_multiplier) as max_return,
          (total_returns / (amount * return_multiplier) * 100) as progress_pct
   FROM book_investments
   WHERE investor_id = <investor_id>;
   ```

2. **Check payouts:**
   ```sql
   SELECT ip.*, bs.created_at as sale_date
   FROM investment_payouts ip
   JOIN revenue_distributions rd ON ip.distribution_id = rd.id
   JOIN book_sales bs ON rd.source_sale_id = bs.id
   WHERE ip.investment_id = <investment_id>
   ORDER BY bs.created_at;
   ```

3. **Check distribution completion:**
   ```sql
   SELECT id, created_at, distributed_to_investors, distribution_completed
   FROM book_sales
   WHERE book_project_id = <book_id>
   ORDER BY created_at;
   ```

## Troubleshooting

**If returns aren't incrementing:**

1. ✅ Check campaign status is `ACTIVE` or `FUNDED`
2. ✅ Check investment status is `'confirmed'` or `'active'`
3. ✅ Check `book_sale.distribution_completed = False` (not already distributed)
4. ✅ Check server logs for distribution errors
5. ✅ Verify `distribute_revenue()` is being called on purchase

**If returns stop before cap:**
- Check if `total_returns >= max_return` (cap reached)
- This is expected behavior - returns stop at cap

**If returns exceed cap:**
- This should never happen (logic prevents it)
- Report as a bug if this occurs

