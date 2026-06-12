# Removing Accredited Reviewers

**Decision:** Retire the accredited reviewer marketplace entirely. Ink Studio focuses on **authors, book campaigns (patronage), and marketplace sales** — not a parallel freelancer review economy.

**Status:** Largely implemented in code (see checklist below).

---

## Why this fits Book Campaign v2

| With reviewers | Without reviewers |
|----------------|-------------------|
| Authors negotiate revenue share + fixed fees | Simpler trust: campaign + writing quality + author profile |
| 10% of every sale split among reviewers | More to author (and platform) |
| “Publishing house replacement” positioning | **Mission:** create & self-publish in Ink Studio → patron campaigns → marketplace → amplification tools & reviews |
| Extra admin (accreditation, payouts, guarantees) | Smaller operational surface |

Reader trust can come from **sample chapters**, **campaign transparency**, **author track record**, and **post-publish reviews** (future: simple star ratings from buyers — not accredited freelancers).

---

## What was removed vs kept

### Removed (accredited system)

- Reviewer registration and accreditation (`/reviewers/register`, admin approve/suspend)
- Reviewer marketplace browse (`/reviewers`)
- Author request review, submit review, publish review, pay task fee
- **10% reviewer pool** on book sales (`REVIEWER_POOL_PERCENTAGE = 0`)
- Reviewer guarantee payments in `accountability_service`
- Reviewer earnings on `/earnings` and payout requests
- Admin reviewer payout queue (redirects to admin books)
- Campaign page “Accredited Reviews” blocks

### Kept for now (legacy data & collab)

| Item | Notes |
|------|--------|
| DB tables `accredited_reviewers`, `book_reviews`, `review_requests`, `reviewer_earnings`, etc. | Historical records; no new flows |
| **Collaboration role `reviewer`** | In-draft commenter on a book — **not** the accredited program. Consider renaming to `beta_reader`. |
| `publish_review` / `pay_review_task` dead code after `410` | Can delete in a later cleanup PR |

### Optional later

- Drop DB tables via migration (after backup + confirming no legal need for payout history)
- Delete templates: `register_reviewer.html`, `reviewers.html`, `request_review.html`, etc.
- Remove models from `book_platform_models.py` and imports in routes

---

## Revenue split (current code)

After reviewer retirement, each sale:

```text
Platform:  15% (fixed)
Investors: 25% (legacy — remove in Campaign v2)
Author:    remainder (includes former 10% reviewer pool)
```

When Campaign v2 also removes investors:

```text
Platform: 15% | Author: 85%
```

---

## Implementation checklist

- [x] Public reviewer routes redirect / 410 (`book_platform_routes.py` ~6882+)
- [x] Admin reviewer management retired (~3503)
- [x] `REVIEWER_POOL_PERCENTAGE = 0` in `revenue_distribution_service.py`
- [x] No reviewer block in `accountability_service` guarantee loop
- [x] `publish_review`, `pay_review_task`, `request_reviewer_payout` → 410
- [x] `admin_reviewer_payout_requests` → redirect
- [x] `reviewer_earnings_by_book` → redirect
- [x] Earnings dashboard skips reviewer queries
- [x] Campaign details template: no accredited review section
- [ ] Remove nav links to `/reviewers` in global headers/menus (grep `reviewers`)
- [ ] Dashboard: hide “reviews awaiting publish” cards if any remain
- [ ] `sales_transparency.html`: reviewer-only sections
- [ ] Update `REVIEWER_INVESTMENT_SYSTEM_GUIDE.md` → archived pointer
- [ ] Book Campaign v2 Phase 2: zero investor pool

---

## Files reference

| Area | Files |
|------|--------|
| Models | `glconnect/book_platform_models.py` — `AccreditedReviewer`, `BookReview`, `ReviewRequest`, `ReviewerEarning`, `ReviewerPayoutRequest` |
| Routes | `glconnect/book_platform_routes.py` — reviewer section ~6878–7070, earnings, admin payouts |
| Revenue | `glconnect/revenue_distribution_service.py` |
| Accountability | `glconnect/accountability_service.py` — `process_reviewer_guarantee` (unused) |
| Templates | `register_reviewer.html`, `reviewers.html`, `request_review.html`, `reviewer_profile.html`, `books_seeking_review.html`, `admin_reviewers.html`, `admin_reviewer_payout_requests.html`, `submit_review.html` |
| Docs | `docs/BOOK_COLLABORATION_AND_REVIEWERS.md` (§2 accredited — superseded), `REVIEWER_INVESTMENT_SYSTEM_GUIDE.md` |

---

*Aligned with `docs/BOOK_CAMPAIGN_V2_SPEC.md`.*
