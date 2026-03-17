# Book Workflow Review – Core Platform Purpose

This document reviews the end-to-end book workflow: writing → funding → editing/review/collab → marketplace sales → investor earnings.

---

## 1. Writing the Book

**Flow:**
- Author creates book in Ink Studio (`/books/create`)
- Required: title (3+ chars), description (50+ chars), genre, language
- Author adds chapters with content
- Minimum for investment readiness: 1 chapter, 1,000 words

**Status:** Implemented. Authors create `BookProject`, add chapters via edit book flow.

---

## 2. Raise Funding (Investment Campaign)

**Flow:**
1. Book must meet **investment readiness** (6 checks: title, description, genre, language, 1+ chapter, 1,000+ words)
2. Author creates campaign (`/books/<id>/create-campaign`): goal, min/max investment, revenue share %, return multiplier cap, duration
3. Campaign goes **ACTIVE** and appears in Investment Marketplace
4. Investors browse, invest (Stripe payment)
5. When `current_funding >= funding_goal` → campaign status = **FUNDED**
6. New investments stop when book is **PUBLISHED** or campaign is **FUNDED**

**Status:** Implemented. Campaign creation, investment flow, author self-investment blocked.

---

## 3. Editing / Review / Collaboration

These can happen **before or after** the campaign, but typically before publishing to marketplace.

### 3a. Collaboration (Co-authors, Editors)

- Author invites by email with role: co-author, editor, reviewer (in-draft), viewer
- Invitee accepts → gets access in Ink Studio
- Co-authors can edit; editors suggest; reviewers give in-draft feedback

**Status:** Implemented per `BOOK_COLLABORATION_AND_REVIEWERS.md`.

### 3b. Accredited Review (Formal Reviews for Marketplace)

- Author requests review from accredited reviewer (optional fixed fee)
- Reviewer submits review (title, content, rating, revenue share %, min sales threshold)
- Author publishes review → review appears on marketplace
- Reviewer earns: **fixed fee** (when author marks paid) + **revenue share** from sales (10% pool)

**Status:** Implemented. Request review, submit, publish, task fee payment flow.

---

## 4. Publish to Marketplace

**Flow:**
- Author sets prices (digital, audiobook, bundle)
- Author publishes digital and/or audiobook via Edit Book
- Book appears in marketplace (`/marketplace`)
- Only **published** books are purchasable

**Note:** Author can publish before or after campaign is funded. If published before funding, campaign stops accepting new investments. Typical flow: fund first, then publish.

**Status:** Implemented. Digital, audiobook, bundle formats supported.

---

## 5. Sales in Marketplace

**Flow:**
1. Customer purchases (digital, audiobook, or bundle)
2. `BookPurchase` created, payment processed (Stripe)
3. `BookSale` created with `sale_format` (digital/audiobook/bundle)
4. `distribute_revenue(sale, db)` called automatically

**Status:** Implemented. Purchase flow, format-specific validation, duplicate purchase checks.

---

## 6. Investor Earnings per Share

**Revenue split (per sale):**
- Platform: 15%
- Reviewer pool: 10%
- Investor pool: 25%
- Author base: 50%

**Investor share:**
- Investor pool = 25% of sale amount
- Each investor’s share = `(investment.amount / total_investment_amount) × investor_pool`
- Return cap: `investment.amount × return_multiplier` (e.g. 3x)
- When `total_returns >= max_return`, that investor stops earning; remainder goes to author

**Tracking:**
- `BookInvestment.total_returns` updated on each sale
- `BookInvestment.paid_out_amount` tracks what’s been paid out
- Available balance = `total_returns - paid_out_amount`

**Status:** Implemented in `revenue_distribution_service.distribute_revenue()`.

---

## 7. Investor Payout

**Flow:**
1. Investor goes to Earnings → sees available balance per investment
2. Investor requests payout (min $25)
3. `PayoutRequest` created (status PENDING)
4. Admin sees payout requests in Admin → Payout Requests
5. Admin marks as paid → `paid_out_amount` updated, request status = PAID

**Status:** Implemented. `request_payout`, `admin_payout_requests`, `admin_mark_payout_paid`.

---

## Workflow Summary (Order of Operations)

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. WRITE BOOK                                                    │
│    Create book → Add chapters (min 1, 1000 words)               │
└─────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. EDIT / COLLAB / REVIEW (can overlap with 1 and 3)            │
│    • Invite collaborators (co-author, editor, reviewer)           │
│    • Request accredited review (optional fixed fee)             │
│    • Reviewer submits → Author publishes review                 │
└─────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. RAISE FUNDING                                                 │
│    Create campaign → Investors invest → Goal reached (FUNDED)   │
└─────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. PUBLISH TO MARKETPLACE                                        │
│    Set prices → Publish digital/audiobook → Book goes live       │
└─────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. SALES & REVENUE DISTRIBUTION                                  │
│    Customer buys → BookSale created → distribute_revenue()      │
│    → Platform, reviewers, investors, author get their share    │
└─────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. INVESTOR PAYOUT                                               │
│    Investor requests payout → Admin marks paid                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Gaps / Considerations

| Area | Status | Notes |
|------|--------|-------|
| **Enforce review before publish** | Optional | No hard rule that a book must have a review before publishing. Authors can publish without one. |
| **Campaign before vs after editing** | Flexible | Collaboration and review can happen before or after campaign. No enforced sequence. |
| **Publish before funded** | Allowed | Author can publish before goal is reached. Campaign then stops accepting investments. Investors who already invested still earn from sales. |
| **Investor payout method** | Manual | Admin marks paid; no automatic Stripe payout to investors. |
| **"Seeking review" visibility** | Not implemented | Per prior discussion: reviewers should only see books marked "seeking review" for review work. |
| **Reviewer-initiated flow** | Not implemented | Only authors can request reviews; reviewers cannot proactively offer to review. |

---

## Key Files

- **Models:** `glconnect/book_platform_models.py` (BookProject, InvestmentCampaign, BookInvestment, BookSale, PayoutRequest)
- **Revenue:** `glconnect/revenue_distribution_service.py` (`distribute_revenue`)
- **Routes:** `glconnect/book_platform_routes.py` (create book, campaign, invest, purchase, payout)
- **Docs:** `INVESTMENT_CAMPAIGN_WORKFLOW.md`, `docs/BOOK_COLLABORATION_AND_REVIEWERS.md`, `INVESTMENT_EARNINGS_WORKFLOW.md`
