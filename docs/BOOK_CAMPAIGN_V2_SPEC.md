# Book Campaign v2 — Patronage & Mission Spec

**Status:** Patronage mode implemented in backend (`glconnect/book_campaign_patronage.py`, default on)  
**Replaces (conceptually):** Investment campaigns with revenue-share returns  
**Mission:** Help authors meet their audience through storytelling — the right books funded by people who care, then sold on the marketplace.

---

## 1. Mission & principles

| Principle | Meaning |
|-----------|---------|
| **Patronage, not securities** | Supporters give money to help a book exist. They do not buy a share of future sales. |
| **Story first** | Campaign copy, curation, and marketplace placement emphasize the book and author voice, not ROI. |
| **Trust through transparency** | Clear funding goal, use of funds, progress, and accountability if the book stalls. |
| **Author meets audience** | Campaign = discovery + community; marketplace = ongoing relationship via purchases and reader discovery. |
| **Platform sustainability** | Revenue after publish: **author + platform** only (accredited reviewers retired). No standing obligation to pay backers from every sale. |

**Required disclaimer (campaign + checkout):**  
*“This is a contribution to help publish this book. It is not an investment and does not entitle you to financial returns.”*

---

## 2. Terminology map (UX & code)

| v1 (investment) | v2 (patronage) |
|-----------------|----------------|
| Investment campaign | **Book campaign** |
| Investor | **Supporter** / **Backer** |
| Invest / Invest Now | **Back this book** / **Contribute** |
| Investment Marketplace (`/investments`) | **Discover campaigns** (`/campaigns` or keep URL with redirect) |
| Investment amount | **Contribution amount** |
| Revenue share % for investors | **Remove** (not shown) |
| Return multiplier cap | **Remove** |
| Investor returns / earnings (investor slice) | **Remove** from sale splits; optional **thank-you perks** only |
| `BookInvestment` | **`BookContribution`** (table rename in Phase 2) |
| `InvestmentCampaign` | **`BookCampaign`** (alias or rename in Phase 2) |

Internal code may keep old table names temporarily with deprecated columns; public UI and API use v2 language only.

---

## 3. User journeys (unchanged skeleton, new economics)

### 3.1 Author

1. Write book in Ink Studio (same **readiness** checks: title, description, genre, language, ≥1 chapter, ≥1,000 words; no uploaded-only books).
2. Create **book campaign**: pitch, optional video, funding goal, min/max contribution, duration, **use of funds** (new text field).
3. Campaign goes **ACTIVE** → listed in Discover (authors still cannot back their own book).
4. When `current_funding >= funding_goal` → **FUNDED**; no new contributions; author works toward draft + publish (milestones unchanged in spirit).
5. Publish on marketplace → sales revenue to **author + platform** only.

### 3.2 Supporter

1. Browse Discover → open campaign → read story + transparency block.
2. Choose amount (within min/max and remaining goal) → Stripe Checkout (same webhook pattern).
3. See confirmation + optional perks (tier-based, see §5).
4. After publish: buy book on marketplace if desired; no “returns dashboard” for backers.

### 3.3 Accountability (keep, reword)

Keep `accountability_service.py` behavior, adapted for backers:

- Funded campaign + no completed draft by **180 days** → refund **contributions** (Stripe PI), not “investor refunds.”
- **50% / 50%** author fund release at first draft (25k words) and publication stays as **safeguard** (money held until milestones).
- Language: “If this book isn’t finished on time, supporters can request a refund.”

---

## 4. Data model v2

### 4.1 `BookCampaign` (evolve `investment_campaigns`)

| Field | v1 | v2 |
|-------|----|----|
| `title`, `description`, `pitch_video_url` | ✓ | ✓ |
| `funding_goal`, `minimum_investment`, `maximum_investment` | ✓ | Rename conceptually to `minimum_contribution`, `maximum_contribution` (DB column rename optional Phase 2) |
| `current_funding` | ✓ | ✓ (or `current_raised`) |
| `revenue_share_percentage` | ✓ | **Deprecate** — stop writing; hide in UI |
| `return_multiplier_cap` | ✓ | **Deprecate** |
| `investment_period_days` | ✓ | `campaign_duration_days` |
| `status`, `start_date`, `end_date`, `funded_at` | ✓ | ✓ |
| Author milestone release flags | ✓ | ✓ |
| `use_of_funds` | — | **New** `Text` — e.g. editing, cover, audiobook |
| `mission_tagline` | — | **Optional** short line for cards |
| `curation_status` | — | **Optional** `draft \| submitted \| featured` for staff/community pick |
| `book_project_id` | ✓ unique | ✓ |

**Statuses (unchanged enum values):** `DRAFT`, `ACTIVE`, `FUNDED`, `FAILED`, `CANCELLED`

### 4.2 `BookContribution` (evolve `book_investments`)

| Field | v1 | v2 |
|-------|----|----|
| `amount`, `currency`, `campaign_id`, `book_project_id`, `supporter_id` (was `investor_id`) | ✓ | ✓ |
| `investment_percentage` | ✓ | **Optional** keep as `contribution_percentage` for display only (“you helped 12% of the goal”) |
| `revenue_share_percentage`, `return_multiplier` | ✓ | **Remove** from new rows |
| `status` | `InvestmentStatus` | Rename enum → `ContributionStatus` (same values: pending → confirmed → active; completed when campaign fully delivered; refunded) |
| `total_returns`, `paid_out_amount`, `return_start_date`, `return_end_date` | ✓ | **Deprecate** — no sale-based payouts to backers |
| `stripe_payment_intent_id` | ✓ | ✓ (refunds) |
| `perk_tier_id` | — | **Optional** FK |
| `display_name_on_page` | — | **Optional** bool (public thank-you list) |
| `message_to_author` | — | **Optional** text (moderated) |

### 4.3 New: `CampaignPerkTier` (optional Phase 2)

```text
id, campaign_id, name, min_amount, description, max_claims, sort_order
```

Examples: “Name in thank-you page ($25)”, “Early digital copy ($50)”, “Signed paperback ($100)” — fulfilled by author/platform operationally, not automatic % of sales.

### 4.4 `BookProject` flags

| Field | v2 |
|-------|-----|
| `has_investment_campaign` | Rename to `has_book_campaign` (or keep column, alias in code) |

---

## 5. Revenue distribution v2

**Current (after reviewer retirement):**

```text
Platform 15% | Author remainder | Reviewers 0% | Investors 25% (legacy)
```

**Target v2 (patronage + no investors):**

```text
Platform 15% | Author 85% | Supporters 0%
```

- **Accredited reviewers:** removed — see `docs/REMOVING_ACCREDITED_REVIEWERS.md`. Former 10% pool flows to author via remainder on each sale.
- Reallocate former **INVESTOR_POOL (25%)** to **author** (or split 20% author / 5% platform if platform needs margin — product decision).
- Remove all `DistributionType.INVESTOR` / `InvestmentPayout` creation on new sales after cutover date.
- **Grandfathering (choose one):**
  - **A. Hard cutover:** From launch date, no investor distributions even for old campaigns (simplest; may need comms).
  - **B. Legacy only:** Campaigns funded before `v2_launch_at` keep investor pool until return cap reached; new campaigns never create investor rows (complex but fair).

Recommendation: **B** if any live funded campaigns exist; **A** if pre-production only.

### 5.1 Earnings dashboard

| Role | v2 dashboard |
|------|----------------|
| Author | Sales, campaign raised, milestone payouts |
| Supporter | **My backing** — list of contributions, campaign status, refund status; **no** “returns from sales” |

Remove or hide: `investor_returns_book.html`, investor sections in `earnings.html`.

---

## 6. Routes & templates (rename map)

| v1 route | v2 route (suggested) |
|----------|----------------------|
| `POST/GET .../create-campaign` | same path, template copy only |
| `/investments` | `/campaigns` (+ 301 from `/investments`) |
| `/investments/<id>` | `/campaigns/<id>` |
| `/investments/<id>/invest` | `/campaigns/<id>/contribute` |
| `make_investment.html` | `contribute.html` |
| `investments.html` | `discover_campaigns.html` |
| `campaign_details.html` | Update: remove ROI terms; add use of funds, supporter wall |
| `investment_refund_status.html` | `contribution_refund_status.html` |

**Stripe metadata:** `contribution_id`, `campaign_id` (keep `investment_id` in webhook handler until migration).

**Forms:** `InvestmentCampaignForm` → `BookCampaignForm` (drop revenue share + return cap fields). `InvestmentForm` → `ContributionForm`.

---

## 7. Curation (“the right book”)

v2 mission implies light **curation** so Discover isn’t a raw firehose.

| Level | Mechanism |
|-------|-----------|
| **MVP** | Readiness gate only + author completes profile (`author_card_setup_completed`) |
| **Phase 2** | `curation_status`: staff can mark **featured**; Discover default sort: featured → % funded → recent |
| **Phase 3** | Community nominate / vote (separate spec) |

Featured badge copy: *“Editor’s pick — stories we believe deserve an audience.”*

---

## 8. Legal & nonprofit structure (non-blocking)

- **Product mission** can ship before a 501(c)(3) or local equivalent exists.
- Contributions are **donations/patronage** for a creative project, not equity.
- If pursuing tax-deductible donations later: separate entity, gift acknowledgment, and restrictions on author payments — legal review required.
- Terms of Service + campaign page disclaimer (§1) are required at launch.

---

## 9. Implementation phases

### Phase 1 — Language & UI (no DB migration)

- [ ] Replace user-facing strings: invest → back, investor → supporter, marketplace title.
- [ ] Remove revenue share & return cap from `create_campaign.html` and `InvestmentCampaignForm` (ignore on submit if old campaigns exist).
- [ ] Add `use_of_funds` to form + `create_investment_campaign` handler (new column + migration).
- [ ] Campaign detail: disclaimer + “How your contribution helps” section.
- [ ] Discover page hero: mission statement.

**Files:** `forms.py`, `create_campaign.html`, `campaign_details.html`, `investments.html`, `make_investment.html`, `view_book.html`, `books.html`, `dashboard.html`, `marketplace.html`

### Phase 2 — Economics off

- [ ] `distribute_revenue`: set `INVESTOR_POOL_PERCENTAGE = 0`, add 25% to `AUTHOR_BASE_PERCENTAGE` (or chosen split).
- [ ] Skip investor loop for campaigns created after `v2_launch_at` (if grandfathering).
- [ ] Earnings dashboard: supporter view only; hide investor returns routes.
- [ ] Stop setting `return_start_date` / `ACTIVE` for “returns”; `ACTIVE` = confirmed contribution only.

**Files:** `revenue_distribution_service.py`, `book_platform_routes.py` (webhook ~5717), `earnings.html`, `investor_returns_book.html`

### Phase 3 — Schema aliases & perks

- [ ] DB migration: `use_of_funds`, optional `campaign_perk_tiers`, `perk_tier_id` on contributions.
- [ ] SQLAlchemy model aliases: `BookCampaign = InvestmentCampaign` module-level until table rename.
- [ ] Optional table renames + data backfill script.

**Files:** `book_platform_models.py`, `db_schema_patches.py`, new Alembic/SQL patch

### Phase 4 — Routes & cleanup

- [ ] Add `/campaigns` routes; redirects from `/investments`.
- [ ] Delete deprecated docs: point `INVESTMENT_CAMPAIGN_WORKFLOW.md` → this spec.
- [ ] Update `INVESTMENT_EARNINGS_WORKFLOW.md`, `EARNINGS_WORKFLOW_EXPLAINED.md`.
- [ ] Purge/update tests referencing investor returns.

---

## 10. Deprecation checklist (v1 concepts to remove)

| Item | Action |
|------|--------|
| `revenue_share_percentage` on campaign form | Remove UI + stop persisting on create |
| `return_multiplier_cap` | Remove UI + stop persisting |
| `revenue_share_percentage`, `return_multiplier` on `BookInvestment` | No new writes |
| `total_returns`, `paid_out_amount`, investor payout cron/UI | Deprecate |
| `InvestmentPayout` model usage on new sales | Stop creating |
| `DistributionType.INVESTOR` | Legacy only or remove |
| Investor pool 25% constant | 0% (v2) |
| Copy: “3x return”, “revenue share”, “Invest for returns” | Delete |
| `investor_returns_by_book` route | Remove or redirect to contribution history |
| Self-investment block | Keep (author cannot back own book) |

**Keep without change (initially):**

- `check_investment_readiness()` → rename function only
- Stripe Checkout + `checkout.session.completed` webhook
- `current_funding` / FUNDED transition
- Author milestone 50%/50% release
- `accountability_service` refund flow (wording + same PI refund)
- One campaign per book; uploaded books blocked
- Accredited reviewer system — **removed** (routes disabled; sale splits no longer pay reviewers)

**Keep (separate from accredited reviewers):**

- **Collaboration role `reviewer`** on invites = in-draft feedback in Ink Studio, not marketplace accreditation. Optional later rename to “beta reader.”

---

## 11. Example supporter-facing copy

**Discover hero:**  
*“Back stories that deserve readers. Your contribution helps authors finish and publish — then find their audience on the marketplace.”*

**Campaign card:**  
*“$2,400 raised of $5,000 · 12 days left · Historical fiction”*

**Contribute CTA:**  
*“Back this book — from $50”*

**After payment:**  
*“Thank you. You’re helping [Author] bring [Title] to readers.”*

---

## 12. Success metrics (v2)

| Metric | Why |
|--------|-----|
| Campaigns funded / month | Patronage works |
| Median time to FUNDED | Community engagement |
| % funded campaigns that publish within 210 days | Accountability |
| Marketplace sales per funded book | Mission outcome (audience) |
| Repeat backers (same user, multiple books) | Community, not one-off speculators |
| Refund rate | Trust / quality signal |

---

## 13. Open product decisions (resolve before Phase 2)

1. **Grandfathering** investor returns on existing funded campaigns? (§5.1 A vs B)
2. **Author share after cutover:** 65% or 50% + 10% to platform from former 25% pool?
3. **Perks:** MVP thank-you list only, or tier picker at checkout?
4. **Featured curation:** MVP manual flag in admin, or wait for Phase 3?
5. **Public supporter names:** opt-in default on or off?

---

## 14. Reference: current touchpoints (for implementers)

| Area | Primary files |
|------|----------------|
| Models | `glconnect/book_platform_models.py` — `InvestmentCampaign`, `BookInvestment`, enums |
| Routes | `glconnect/book_platform_routes.py` — create campaign, investments, make_investment, earnings, webhooks |
| Revenue | `glconnect/revenue_distribution_service.py` |
| Accountability | `glconnect/accountability_service.py` |
| Forms | `glconnect/forms.py` — `InvestmentCampaignForm`, `InvestmentForm` |
| Templates | `glconnect/templates/book_platform/*campaign*`, `*invest*` |
| Docs to supersede | `INVESTMENT_CAMPAIGN_WORKFLOW.md`, `INVESTMENT_EARNINGS_WORKFLOW.md` |

---

### Patronage backend (shipped, UI unchanged)

- `BOOK_CAMPAIGN_PATRONAGE=1` (default): new campaigns store 0% revenue share; contributions do not accrue sale returns; funder pool on sales is 0% (author gets ~85% after 15% platform).
- Same routes: create campaign, `/investments`, Stripe checkout, FUNDED status, author milestone releases, supporter refunds via accountability.
- Set `BOOK_CAMPAIGN_PATRONAGE=0` to restore legacy investment economics (dev only).

*Optional next: Phase 1 UI copy (`use_of_funds`, disclaimer) without changing layout.*
