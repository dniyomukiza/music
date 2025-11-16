# Investment Campaign Workflow - Complete Guide

## Overview
This document explains the complete workflow for when a book is ready to receive potential investments, from book creation to investor returns.

---

## 📋 PHASE 1: BOOK PREPARATION

### Step 1: Author Creates a Book
- Author creates a new book project in Ink Studio
- **Required fields:**
  - Title (minimum 3 characters)
  - Description (minimum 50 characters)
  - Genre selection
  - **Language selection** (NEW - now required)
  - Target audience (optional)

### Step 2: Add Content
- Author writes and adds chapters to the book
- **Minimum requirements:**
  - At least 1 chapter
  - At least 1,000 words of content

### Step 3: Investment Readiness Check
The system automatically checks if the book meets all requirements:

✅ **Investment Readiness Requirements:**
1. ✅ Book has a title (at least 3 characters)
2. ✅ Book has a description (at least 50 characters)
3. ✅ Book has a genre selected
4. ✅ Book has a language selected
5. ✅ Book has at least one chapter
6. ✅ Book has at least 1,000 words of content

**Status Display:**
- Authors see an "Investment Readiness" card on their book page
- Shows progress: "X/6 requirements met"
- Lists any missing requirements
- When all requirements are met, shows "Ready for Investment!" with a button to create campaign

---

## 🚀 PHASE 2: CAMPAIGN CREATION

### Step 4: Create Investment Campaign
Once the book is ready, the author can create an investment campaign:

**Access:**
- Go to book page → Click "Create Investment Campaign" button
- Or navigate to: `/books/<book_id>/create-campaign`

**Campaign Details Required:**
1. **Campaign Title** - e.g., "Help publish my debut novel"
2. **Campaign Description** - Pitch to investors (why they should invest)
3. **Pitch Video URL** (optional) - YouTube/Vimeo link
4. **Funding Goal** - Total amount needed (e.g., $5,000)
5. **Minimum Investment** - Smallest investment allowed (e.g., $50)
6. **Maximum Investment** (optional) - Largest single investment allowed
7. **Revenue Share %** - Total % of sales shared with all investors (e.g., 25%)
8. **Return Multiplier Cap** - Maximum return (e.g., 3x = investor gets max 3x their investment)
9. **Campaign Duration** - Days to reach goal (e.g., 30 days)

**What Happens:**
- Campaign is created with status = `ACTIVE`
- Campaign appears in the Investment Marketplace
- Campaign start date = now
- Campaign end date = start date + duration
- Book's `has_investment_campaign` flag is set to `True`

---

## 💰 PHASE 3: INVESTMENT PERIOD

### Step 5: Campaign Goes Live
- Campaign appears in `/investments` marketplace
- Visible to all logged-in users
- Shows in "Active" campaigns filter by default
- Investors can browse and search campaigns

### Step 6: Investors Discover Campaign
**Ways to find campaigns:**
- Browse Investment Marketplace (`/investments`)
- Search by book title or campaign title
- Filter by status (Active, Funded, Draft, All)
- View campaign details page

**Campaign Details Page Shows:**
- Book information (title, description, genre, language)
- Author information
- Campaign progress (funding raised / goal)
- Investment terms (revenue share %, return cap)
- Minimum/maximum investment amounts
- Days remaining
- List of existing investors
- Accredited reviews (if any)

### Step 7: Investor Makes Investment
**Process:**
1. Investor clicks "Invest Now" on campaign page
2. Investor enters investment amount
3. System validates:
   - Amount >= minimum investment
   - Amount <= maximum investment (if set)
   - Amount doesn't exceed remaining funding needed
4. Investment record created with status = `PENDING`
5. Payment processed (via Stripe/Payment gateway)
6. Investment status changes to `CONFIRMED` → `ACTIVE`
7. Campaign's `current_funding` is updated

**Investment Record Created:**
- `BookInvestment` record with:
  - Investment amount
  - Investment percentage (% of total goal)
  - Revenue share percentage (from campaign)
  - Return multiplier cap (from campaign)
  - Status tracking

### Step 8: Campaign Funding Progress
**As investments come in:**
- Campaign's `current_funding` increases
- Progress bar updates on campaign page
- Investors can see how much is raised vs. goal

**Campaign Status Changes:**
- `ACTIVE` - Campaign is live, accepting investments
- `FUNDED` - Funding goal reached
- `FAILED` - Campaign ended without reaching goal
- `CANCELLED` - Author cancelled the campaign

---

## 📈 PHASE 4: POST-FUNDING (Book Publication)

### Step 9: Campaign Reaches Goal
When `current_funding >= funding_goal`:
- Campaign status changes to `FUNDED`
- Campaign's `funded_at` timestamp is set
- Book can now be published (if not already)
- Investment returns begin when book sales start

### Step 10: Book Sales Begin
**When a customer purchases the book:**
1. `BookPurchase` record created
2. Payment processed
3. `BookSale` record created
4. Revenue distribution is triggered automatically

---

## 💵 PHASE 5: REVENUE DISTRIBUTION

### Step 11: Revenue Distribution on Each Sale
**For each book sale, revenue is distributed:**

**Example: Book sells for $10.00**

```
Total Sale: $10.00

1. Platform Fee:      $1.50  (15% - goes to platform)
2. Reviewer Pool:     $1.00  (10% - split among reviewers)
3. Investor Pool:     $2.50  (25% - split among investors)
4. Author Base:       $5.00  (50% - goes to author)
```

### Step 12: Investor Returns Calculation
**For each investor in the campaign:**

```
Investor Pool = $2.50 (25% of $10.00 sale)

Example Campaign:
- Funding Goal: $5,000
- Investor A: Invested $2,500 (50% of goal)
- Investor B: Invested $2,500 (50% of goal)

Distribution:
- Investor A gets: $2.50 × 50% = $1.25 per sale
- Investor B gets: $2.50 × 50% = $1.25 per sale
```

**Return Multiplier Cap Applied:**
- If return multiplier cap = 3x:
  - Investor A invested $2,500
  - Max return = $2,500 × 3 = $7,500
  - After 6,000 sales: $1.25 × 6,000 = $7,500 (cap reached)
  - Investor A stops earning after cap is reached

### Step 13: Returns Tracking
**For each sale:**
- `InvestmentPayout` record created for each investor
- `BookInvestment.total_returns` is updated
- Returns accumulate until payout
- Status: `PENDING` until paid out

**Investor Dashboard Shows:**
- Total investment amount
- Total returns earned
- Returns per sale
- Progress toward return cap
- Payout history

---

## 📊 COMPLETE WORKFLOW SUMMARY

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: BOOK PREPARATION                                   │
├─────────────────────────────────────────────────────────────┤
│ 1. Author creates book                                      │
│ 2. Author adds title, description, genre, language          │
│ 3. Author writes chapters (min 1 chapter, 1,000 words)      │
│ 4. System checks investment readiness                       │
│ 5. Book marked as "Ready for Investment"                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: CAMPAIGN CREATION                                  │
├─────────────────────────────────────────────────────────────┤
│ 6. Author creates investment campaign                       │
│ 7. Sets funding goal, terms, duration                       │
│ 8. Campaign goes LIVE (status = ACTIVE)                     │
│ 9. Campaign appears in marketplace                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: INVESTMENT PERIOD                                  │
├─────────────────────────────────────────────────────────────┤
│ 10. Investors browse marketplace                            │
│ 11. Investors view campaign details                         │
│ 12. Investors make investments                              │
│ 13. Campaign funding increases                              │
│ 14. Campaign reaches goal → Status = FUNDED                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4: BOOK PUBLICATION                                   │
├─────────────────────────────────────────────────────────────┤
│ 15. Book is published                                       │
│ 16. Book appears in marketplace                             │
│ 17. Customers can purchase the book                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ PHASE 5: REVENUE DISTRIBUTION                               │
├─────────────────────────────────────────────────────────────┤
│ 18. Customer purchases book                                 │
│ 19. Revenue distribution triggered                          │
│ 20. Platform fee deducted (15%)                             │
│ 21. Reviewer earnings calculated (10%)                      │
│ 22. Investor returns calculated (25%)                       │
│ 23. Author receives remainder (50%+)                        │
│ 24. Returns tracked and accumulated                         │
│ 25. Periodic payouts to investors                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 KEY REQUIREMENTS SUMMARY

### For a Book to Be Investment-Ready:
1. ✅ **Title** - At least 3 characters
2. ✅ **Description** - At least 50 characters  
3. ✅ **Genre** - Must be selected
4. ✅ **Language** - Must be selected (NEW)
5. ✅ **Chapters** - At least 1 chapter
6. ✅ **Content** - At least 1,000 words

### For a Campaign to Appear in Marketplace:
1. ✅ Campaign exists for the book
2. ✅ Campaign status = `ACTIVE` (or `FUNDED` if viewing funded campaigns)
3. ✅ Campaign is not cancelled or failed

### For Investors to Earn Returns:
1. ✅ Campaign reached funding goal (status = `FUNDED`)
2. ✅ Book is published and selling
3. ✅ Investor's return cap not yet reached
4. ✅ Revenue distribution is working

---

## 💡 EXAMPLE SCENARIO

**Book:** "The Mystery Novel"
- **Language:** English
- **Genre:** Mystery
- **Word Count:** 15,000 words
- **Chapters:** 5 chapters

**Campaign:**
- **Goal:** $3,000
- **Revenue Share:** 25%
- **Return Cap:** 3x
- **Duration:** 30 days

**Investments:**
- Investor 1: $1,000 (33.3%)
- Investor 2: $1,000 (33.3%)
- Investor 3: $1,000 (33.3%)

**Book Sales:**
- Price: $10.00
- Sales: 1,000 copies = $10,000 revenue

**Returns:**
- Investor Pool: $10,000 × 25% = $2,500
- Each investor gets: $2,500 × 33.3% = $833.33
- ROI: $833.33 / $1,000 = 83.3% return
- Max return: $1,000 × 3 = $3,000 (not reached yet)

---

## 🔍 WHERE TO CHECK STATUS

**For Authors:**
- Book page → "Investment Readiness" card
- Dashboard → "My Investment Campaigns" section
- Campaign details page

**For Investors:**
- Investment Marketplace (`/investments`)
- Campaign details page
- Dashboard → "My Investments" section

**For All Users:**
- Investment Marketplace shows all active campaigns
- Can filter by status, search by title
- View campaign progress and terms






