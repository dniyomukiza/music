# Sales Transparency & Earnings Tracking Guide

## Overview

The system provides **complete transparency** for all parties (authors, reviewers, investors) to track sales and see exactly how they're earning. Every sale is tracked, and revenue distributions are visible in real-time.

---

## Access Points

### 1. **Earnings Dashboard** (`/mybook/earnings`)
- **Who can access:** All logged-in users
- **What it shows:**
  - Reviewer earnings (if you're a reviewer)
  - Investment returns (if you're an investor)
  - Author sales (if you're an author)
  - Grouped by book
  - Links to detailed views

### 2. **Book Sales Transparency** (`/mybook/books/<book_id>/sales-transparency`)
- **Who can access:** 
  - Authors of the book
  - Reviewers who reviewed the book
  - Investors who invested in the book
- **What it shows:**
  - Every single sale with complete breakdown
  - Revenue distribution per sale
  - Your earnings per sale
  - Total summaries

### 3. **Reviewer Earnings by Book** (`/mybook/reviewers/my-earnings/<book_id>`)
- **Who can access:** Accredited reviewers who reviewed the book
- **What it shows:**
  - All earnings from that specific book
  - Earnings matched to sales
  - Total earnings summary

### 4. **Investor Returns by Book** (`/mybook/investments/my-returns/<book_id>`)
- **Who can access:** Investors who invested in the book
- **What it shows:**
  - All returns from that specific book
  - Returns matched to sales
  - ROI percentage
  - Progress toward return cap
  - Total returns summary

---

## What Each Party Can See

### Authors Can See:
✅ **Total sales count**
✅ **Total revenue generated**
✅ **Revenue breakdown per sale:**
   - Platform fee (15%)
   - Reviewer distributions (10% pool)
   - Investor distributions (25% pool)
   - Author earnings (50%+ remainder)
✅ **Sales grouped by book**
✅ **Distribution status (completed/pending)**
✅ **Link to full transparency page for each book**

### Reviewers Can See:
✅ **Total earnings across all books**
✅ **Earnings per book**
✅ **Earnings per sale** (matched to specific sales)
✅ **Earnings status** (pending/completed)
✅ **Revenue share percentage** for each review
✅ **Minimum sales threshold** status
✅ **Link to detailed earnings page for each book**

### Investors Can See:
✅ **Total returns across all investments**
✅ **Returns per investment**
✅ **Returns per sale** (matched to specific sales)
✅ **ROI percentage** for each investment
✅ **Progress toward return cap** (e.g., 3x multiplier)
✅ **Investment status** (active/completed)
✅ **Link to detailed returns page for each book**

---

## Transparency Features

### Per-Sale Breakdown

Every sale shows:
- **Sale #** - Sequential number
- **Date** - When the sale occurred
- **Sale Amount** - Total amount ($10.00)
- **Platform Fee** - $1.50 (15%)
- **Reviewers** - List of reviewer distributions
- **Investors** - List of investor distributions
- **Author** - Author's share
- **Your Earnings** - What you specifically earned from this sale

### Revenue Distribution Summary

Shows totals across all sales:
- **Total Sales** - Number of sales
- **Total Revenue** - Sum of all sale amounts
- **Platform Total** - Sum of all platform fees
- **Reviewers Total** - Sum of all reviewer distributions
- **Investors Total** - Sum of all investor distributions
- **Author Total** - Sum of all author earnings

### Visual Progress Bars

- Color-coded progress bars showing revenue distribution percentages
- Easy to see at a glance how revenue is split

---

## Example Views

### Earnings Dashboard (Reviewer)
```
┌─────────────────────────────────────────┐
│ Reviewer Earnings                      │
│ Total: $125.50                         │
├─────────────────────────────────────────┤
│ Earnings by Book:                      │
│                                         │
│ "The Mystery Novel"                    │
│ $75.25 | 15 earnings                   │
│ [View Details]                          │
│                                         │
│ "Adventure Story"                       │
│ $50.25 | 10 earnings                   │
│ [View Details]                          │
└─────────────────────────────────────────┘
```

### Sales Transparency Page
```
┌─────────────────────────────────────────┐
│ Sales Transparency - "The Mystery Novel"│
├─────────────────────────────────────────┤
│ Summary:                                │
│ • Total Sales: 50                       │
│ • Total Revenue: $500.00                 │
│ • Your Earnings: $125.50                │
│                                         │
│ Revenue Distribution:                   │
│ [Platform] [Reviewers] [Investors]     │
│ [Author]                                │
│                                         │
│ Per-Sale Breakdown:                    │
│ Sale #1 | $10.00 | Your: $0.25         │
│ Sale #2 | $10.00 | Your: $0.25         │
│ ...                                     │
└─────────────────────────────────────────┘
```

---

## Key Benefits

### 1. **Complete Transparency**
- Every sale is visible
- Every distribution is tracked
- No hidden calculations

### 2. **Real-Time Updates**
- Earnings update immediately after each sale
- No delays or manual processing

### 3. **Per-Sale Tracking**
- See exactly which sale generated which earnings
- Match earnings to specific dates

### 4. **Multi-Book Support**
- Track earnings across multiple books
- Grouped views for easy navigation

### 5. **Role-Based Access**
- See only what's relevant to you
- Secure access control

---

## How to Access

### For Authors:
1. Go to **Earnings Dashboard** (`/mybook/earnings`)
2. Click **"View Transparency"** next to any book
3. See complete sales breakdown

### For Reviewers:
1. Go to **Earnings Dashboard** (`/mybook/earnings`)
2. Click **"View Details"** next to any book
3. See your earnings per sale

### For Investors:
1. Go to **Earnings Dashboard** (`/mybook/earnings`)
2. Click **"Details"** next to any investment
3. See your returns per sale

---

## Data Accuracy

All data is:
- ✅ **Automatically calculated** - No manual entry
- ✅ **Immediately recorded** - Real-time updates
- ✅ **Immutable** - Cannot be changed after creation
- ✅ **Auditable** - Full transaction history
- ✅ **Transparent** - Visible to all parties

---

## Security

- **Access Control:** Only authorized parties can view sales data
- **Role Verification:** System checks if you're author/reviewer/investor
- **Data Privacy:** You only see your own earnings, not others' personal data
- **Secure Routes:** All endpoints require authentication

---

## Summary

**Yes, reviewers, investors, and authors can all track sales for transparency and see how they're earning!**

The system provides:
- ✅ Complete sales visibility
- ✅ Per-sale earnings breakdown
- ✅ Real-time updates
- ✅ Multi-book tracking
- ✅ Role-based access
- ✅ Detailed transparency pages

Every party has full visibility into how revenue is distributed and how they're earning from book sales.


