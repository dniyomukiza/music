# Full Book Workflow Review & Proposed Refinements

End-to-end review: Writing → Funding → Editing/Review/Collab → Publishing (Digital/Audio) → Sales → Payouts.

---

## 1. Current Workflow (As Implemented)

### 1.1 Writing the Book

| Path | Flow | Status |
|------|------|--------|
| **Platform-created** | Create book → Add chapters (title, content, summary) → Publish chapters individually | ✅ |
| **Upload digital** | Upload PDF/EPUB/DOCX → Extract text → Create BookProject (no chapters) | ✅ |

**Investment readiness (platform only):** title 3+ chars, description 50+ chars, genre, language, 1+ chapter, 1,000+ words.

**Policy:** Uploaded books can never have campaigns—only selling (digital/audio) in the marketplace. Enforced server-side and in UI.

---

### 1.2 Collaboration & Review

| Feature | Flow | Status |
|---------|------|--------|
| **Collaboration** | Invite by email (co-author, editor, reviewer, viewer) → Accept → Access in Ink Studio | ✅ |
| **Accredited review** | Author requests → Reviewer submits → Author publishes → Review on marketplace | ✅ |
| **Reviewer earnings** | Fixed fee (author marks paid) + revenue share from 10% pool | ✅ |

**Gaps:** No "seeking review" visibility for reviewers. No reviewer-initiated offers.

---

### 1.3 Funding Campaign

| Step | Flow | Status |
|------|------|--------|
| Create campaign | Goal, min/max investment, revenue share %, return cap, duration | ✅ |
| Campaign ACTIVE | Appears in Investment Marketplace | ✅ |
| Investors invest | Stripe checkout → BookInvestment (PENDING → CONFIRMED via webhook) | ✅ |
| Campaign FUNDED | When current_funding >= goal | ✅ |
| Author fund release | 50% at first draft (25k+ words), 50% at publication | ✅ |

**Safeguards:** Author cannot withdraw until milestones. Accountability: 180 days to complete, 30 days to publish, else refunds.

---

### 1.4 Publishing (Digital & Audiobook)

| Format | Flow | Status |
|--------|------|--------|
| **Digital (platform)** | Set price → Publish → status = PUBLISHED | ✅ |
| **Digital (uploaded)** | Set price → Publish digital → digital_book_published = True | ✅ |
| **Audiobook** | Generate from chapters (TTS) → Set price → Publish → audiobook_published = True | ✅ |
| **Audiobook chapters** | Per-chapter audio for platform books; listeners pick any chapter | ✅ |

**Note:** Platform books use `status`; uploaded books use `digital_book_published` / `audiobook_published`. Marketplace shows books matching any of these.

---

### 1.5 Sales & Revenue Distribution

| Step | Flow | Status |
|------|------|--------|
| Purchase | Stripe → BookPurchase → BookSale | ✅ |
| Distribution | distribute_revenue(): 15% platform, 10% reviewers, 25% investors, 50% author | ✅ |
| Investor share | (investment / total) × investor_pool, capped by return multiplier | ✅ |

---

### 1.6 Payouts

| Recipient | Flow | Status |
|-----------|------|--------|
| **Investors** | Request payout (min $50) → PayoutRequest → Admin marks paid | ✅ |
| **Authors (campaign)** | Request first-draft/publication release → Admin approves → Manual transfer | ✅ |
| **Reviewers** | Earnings dashboard; fixed fee when author marks paid | ⚠️ No formal payout request flow |
| **Authors (sales)** | Revenue in earnings; no explicit payout flow (assumed external) | ⚠️ |

---

## 2. Identified Issues & Gaps

### 2.1 Accountability vs Uploaded Books

**Issue:** Accountability uses `book.status == PUBLISHED` for "completed." Uploaded books may stay `status = DRAFT` while `digital_book_published = True`. Refunds could trigger incorrectly.

**Fix:** Treat as published when `status == PUBLISHED` OR `digital_book_published` OR `audiobook_published`.

---

### 2.2 Author Payout for Sales Revenue

**Issue:** Author earnings from sales are tracked but there is no request/approval flow. Campaign funds have milestone release; sales revenue does not.

**Clarification:** If authors receive sales revenue via Stripe Connect or external payout, document it. If not, consider an author payout request flow similar to investors.

---

### 2.3 Reviewer Payout Flow

**Issue:** Reviewers see earnings but lack a formal "request payout" flow like investors. Fixed fee is marked paid by author; revenue-share earnings have no request mechanism.

**Fix:** Add reviewer payout request (min threshold) + admin approval, mirroring investor payouts.

---

### 2.4 Cron for Accountability

**Issue:** `check_all_books_accountability` exists but may not be scheduled. Refunds and reviewer guarantees depend on it running.

**Fix:** Ensure a daily cron (or similar) runs `check_all_books_accountability` and `check_author_accountability` for funded campaigns.

---

### 2.5 Refund Execution

**Issue:** `process_investor_refunds` creates RefundRequest records but has a TODO: "Integrate with payment processor to actually process refunds." Refunds are manual.

**Fix:** Integrate Stripe refunds when RefundRequest is created, or add an admin "Process refund" action that calls Stripe.

---

### 2.6 ~~Campaign Fund Release for Uploaded Books~~ (N/A)

**Policy:** Uploaded books never have campaigns. No fund release logic applies.

---

### 2.7 Duplicate Purchase Checks

**Issue:** Purchase flow checks for existing purchases. Verify it correctly handles digital + audiobook + bundle as separate formats (user can buy digital and audiobook separately).

**Status:** Appears implemented; worth a quick audit.

---

### 2.8 Audiobook for Uploaded Books

**Issue:** Uploaded books can generate audiobooks from extracted text. They get a single file, not per-chapter. Acceptable, but document the difference.

---

## 3. Proposed Refinements (Prioritized)

### High Priority

| # | Refinement | Effort | Impact |
|---|------------|--------|--------|
| 1 | **Fix accountability for uploaded books** – Use `digital_book_published` / `audiobook_published` as "published" | Low | Prevents incorrect refunds |
| 2 | ~~Campaign fund release for uploaded books~~ | N/A | Uploaded books never have campaigns |
| 3 | **Stripe refund integration** – Auto-refund or admin-triggered refund when RefundRequest is created | Medium | Completes investor protection |
| 4 | **Scheduled accountability job** – Cron/celery to run `check_all_books_accountability` daily | Low | Enforces deadlines |

### Medium Priority

| # | Refinement | Effort | Impact |
|---|------------|--------|--------|
| 5 | **Reviewer payout request** – Min threshold, request flow, admin approval (like investors) | Medium | Fairness, clarity |
| 6 | **Author sales payout** – If no Stripe Connect, add request/approval flow for author earnings | Medium | Completes earnings flow |
| 7 | **"Seeking review" visibility** – Let reviewers see books marked seeking review | Medium | Better matching |
| 8 | **Unify "published" logic** – Single helper `is_book_published(book)` used everywhere | Low | Consistency |

### Lower Priority

| # | Refinement | Effort | Impact |
|---|------------|--------|--------|
| 9 | **Reviewer-initiated offers** – Reviewers can propose to review a book | High | More engagement |
| 10 | **Optional review before publish** – Campaign term: "Review required before publication" | Medium | Quality signal |
| 11 | **Campaign progress notifications** – Email investors when funded, when book published | Low | Engagement |
| 12 | **Investor Stripe Connect payout** – Auto-pay investors when they request (vs manual) | High | Scalability |

---

## 4. Workflow Diagram (Current + Ideal)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ WRITING                                                                      │
│ • Platform: Create book → Add chapters (min 1, 1000 words for campaign)    │
│ • Upload: PDF/EPUB/DOCX → Extract text (no campaigns)                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ COLLABORATION & REVIEW (optional, can overlap)                               │
│ • Invite co-authors, editors, reviewers                                      │
│ • Request accredited review → Submit → Publish                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ FUNDING (platform-created books only)                                        │
│ • Create campaign → ACTIVE → Investors invest (Stripe) → FUNDED              │
│ • Author: 50% at first draft (25k words), 50% at publication                 │
│ • Accountability: 180d complete, 30d publish, else refunds                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ PUBLISHING                                                                   │
│ • Digital: Set price → Publish (status or digital_book_published)            │
│ • Audiobook: Generate (chapters or single file) → Set price → Publish        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ SALES                                                                        │
│ • Customer buys (digital/audiobook/bundle) → Stripe → BookPurchase          │
│ • BookSale → distribute_revenue() → Platform 15%, Reviewers 10%,            │
│   Investors 25%, Author 50%                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ PAYOUTS                                                                      │
│ • Investors: Request (min $50) → Admin marks paid                             │
│ • Authors (campaign): Request milestone release → Admin approves              │
│ • Reviewers: Fixed fee (author marks paid); revenue share (no request yet)   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Key Files Reference

| Area | Files |
|------|-------|
| Writing | `book_platform_routes.py` (create_book, create_chapter, edit_chapter) |
| Upload | `book_platform_routes.py` (upload_digital_book), `digital_book_processor.py` |
| Campaign | `book_platform_routes.py` (create_campaign, make_investment) |
| Fund release | `accountability_service.py`, `book_platform_routes.py` (request_campaign_fund_release) |
| Audiobook | `audio_book_generator.py`, `book_platform_routes.py` (generate_audiobook) |
| Sales | `book_platform_routes.py` (purchase flow), `revenue_distribution_service.py` |
| Payouts | `book_platform_routes.py` (request_payout, admin_payout_requests, admin_author_payout_requests) |
| Accountability | `accountability_service.py` |

---

## 6. Summary

The workflow is largely implemented and coherent. Main refinements:

1. **Correctness:** Fix accountability for uploaded books; allow campaign fund release for uploaded books.
2. **Completeness:** Integrate Stripe refunds; add reviewer payout request; schedule accountability.
3. **Consistency:** Unify "published" logic; document author sales payout path.
4. **Enhancements:** Seeking-review visibility; notifications; optional review-before-publish.

Implementing the high-priority items will make the system more robust and complete.
