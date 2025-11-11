# Testing Guide: Reviewer-Investor-Author System

## Overview

This guide helps you test the complete system that connects authors, reviewers, and investors.

---

## Prerequisites

1. **Local Server Running**
   ```bash
   python3 run.py
   ```
   Server should be running at `http://localhost:5000`

2. **Database Setup**
   - PostgreSQL database running
   - All migrations applied
   - Models created

3. **User Accounts Needed**
   - At least 1 Author account
   - At least 1 Reviewer account (or register as reviewer)
   - At least 1 Investor account (any user can invest)
   - 1 Admin account (for reviewer approval)

---

## Test Scenarios

### Scenario 1: Reviewer Registration & Accreditation

#### Step 1: Register as Reviewer
1. **Login** as a user (or create new account)
2. **Navigate to:** `/mybook/reviewers/register`
3. **Fill out form:**
   - Reviewer Name: "John Doe"
   - Bio: "Experienced book reviewer with 10 years in publishing"
   - Credentials: "M.A. in Literature, Published 50+ reviews"
   - Specialties: "Fiction, Mystery, Science Fiction"
   - Portfolio URL: "https://example.com/reviews"
4. **Submit** the form
5. **Expected:** Success message, status shows "Pending"

#### Step 2: Admin Approves Reviewer
1. **Login** as admin user
2. **Navigate to:** `/mybook/admin/reviewers`
3. **Find** the pending reviewer
4. **Click** "Approve"
5. **Expected:** Reviewer status changes to "Accredited"

#### Step 3: Verify Reviewer Profile
1. **Navigate to:** `/mybook/reviewers`
2. **Find** your reviewer profile
3. **Click** to view details
4. **Expected:** Profile shows accredited status, credentials, specialties

**Test Links:**
- Register: `http://localhost:5000/mybook/reviewers/register`
- Admin Panel: `http://localhost:5000/mybook/admin/reviewers`
- Reviewer List: `http://localhost:5000/mybook/reviewers`

---

### Scenario 2: Author Requests Review

#### Step 1: Author Creates Book
1. **Login** as author
2. **Navigate to:** `/mybook/dashboard`
3. **Create** a new book:
   - Title: "The Mystery Novel"
   - Description: "A thrilling mystery story"
   - Genre: "Mystery"
   - Status: Draft
4. **Save** the book

#### Step 2: Author Requests Review
1. **Navigate to:** `/mybook/books/<book_id>/request-review`
2. **Fill out form:**
   - Select accredited reviewer
   - Revenue Share: 2.5%
   - Minimum Sales Threshold: 0 (earn from first sale)
   - Message: "Please review my book"
3. **Submit** request
4. **Expected:** Review request sent, reviewer notified

#### Step 3: Reviewer Accepts & Submits Review
1. **Login** as reviewer
2. **Navigate to:** Reviewer dashboard or review requests
3. **Accept** the review request
4. **Read** the book (or chapters)
5. **Navigate to:** `/mybook/reviews/<review_id>/submit`
6. **Fill out review:**
   - Title: "Excellent Mystery Novel"
   - Rating: 5 stars
   - Content: "This is a well-written mystery with great characters..."
   - Revenue Share: 2.5% (from agreement)
7. **Submit** review
8. **Expected:** Review published, author notified

**Test Links:**
- Request Review: `http://localhost:5000/mybook/books/<book_id>/request-review`
- Submit Review: `http://localhost:5000/mybook/reviews/<review_id>/submit`

---

### Scenario 3: Investment Campaign

#### Step 1: Author Creates Investment Campaign
1. **Login** as author
2. **Navigate to:** `/mybook/books/<book_id>/create-campaign`
3. **Fill out campaign:**
   - Title: "Fund My Mystery Novel"
   - Description: "Help me publish this amazing mystery novel"
   - Funding Goal: $5,000
   - Minimum Investment: $50
   - Revenue Share: 25%
   - Return Multiplier: 3x
   - Investment Period: 30 days
4. **Submit** campaign
5. **Expected:** Campaign created, status "Active"

#### Step 2: Investor Views Campaign
1. **Login** as investor (or any user)
2. **Navigate to:** `/mybook/investments`
3. **Find** the campaign
4. **Click** to view details
5. **Expected:** See campaign details, funding progress, book info

#### Step 3: Investor Makes Investment
1. **Click** "Invest" button
2. **Enter** investment amount: $1,000
3. **Review** terms:
   - Investment: $1,000
   - Expected ROI: Based on sales
   - Max Return: $3,000 (3x)
4. **Confirm** investment
5. **Expected:** Investment confirmed, campaign funding updated

#### Step 4: Campaign Reaches Goal
1. **Multiple investors** invest (or single large investment)
2. **When** funding goal reached ($5,000)
3. **Expected:** 
   - Campaign status → "Funded"
   - Book status can be updated
   - Returns start when book is published

**Test Links:**
- Create Campaign: `http://localhost:5000/mybook/books/<book_id>/create-campaign`
- View Campaigns: `http://localhost:5000/mybook/investments`
- Campaign Details: `http://localhost:5000/mybook/investments/<campaign_id>`

---

### Scenario 4: Book Sale & Revenue Distribution

#### Step 1: Author Publishes Book
1. **Login** as author
2. **Navigate to:** Book edit page
3. **Set** book status to "Published"
4. **Set** book price: $10.00
5. **Save** changes

#### Step 2: Customer Purchases Book
1. **Login** as customer (or create account)
2. **Navigate to:** `/mybook/marketplace`
3. **Find** the book
4. **Click** "Purchase"
5. **Complete** purchase
6. **Expected:** Purchase successful, sale recorded

#### Step 3: Verify Revenue Distribution
1. **Login** as author
2. **Navigate to:** `/mybook/earnings`
3. **Check** sales data
4. **Expected:** See sale, net amount, distributions

1. **Login** as reviewer
2. **Navigate to:** `/mybook/earnings`
3. **Expected:** See earnings from the sale (2.5% of $10 = $0.25)

1. **Login** as investor
2. **Navigate to:** `/mybook/earnings`
3. **Expected:** See returns from the sale (proportional share of 25% pool)

**Test Links:**
- Marketplace: `http://localhost:5000/mybook/marketplace`
- Earnings: `http://localhost:5000/mybook/earnings`
- Sales Transparency: `http://localhost:5000/mybook/books/<book_id>/sales-transparency`

---

### Scenario 5: Accountability & Refunds

#### Step 1: Check Accountability Status
1. **Login** as author
2. **Navigate to:** `/mybook/books/<book_id>/accountability`
3. **Expected:** See deadlines, days remaining, warnings

#### Step 2: Simulate Deadline Passed
1. **Manually adjust** campaign `funded_at` date to 200 days ago (in database)
2. **Run** accountability check:
   ```python
   from glconnect.accountability_service import check_author_accountability
   check_author_accountability(book_id, db)
   ```
3. **Expected:** Refunds triggered, campaign cancelled

#### Step 3: Check Refund Status
1. **Login** as investor
2. **Navigate to:** `/mybook/investments/<investment_id>/refund-status`
3. **Expected:** See refund request, status, amount

**Test Links:**
- Accountability: `http://localhost:5000/mybook/books/<book_id>/accountability`
- Refund Status: `http://localhost:5000/mybook/investments/<investment_id>/refund-status`

---

## Quick Test Checklist

### ✅ Reviewer System
- [ ] Register as reviewer
- [ ] Admin approves reviewer
- [ ] Reviewer profile visible
- [ ] Author requests review
- [ ] Reviewer submits review
- [ ] Review appears on book page

### ✅ Investment System
- [ ] Author creates campaign
- [ ] Campaign visible in marketplace
- [ ] Investor views campaign details
- [ ] Investor makes investment
- [ ] Campaign funding updates
- [ ] Campaign reaches goal (status: Funded)

### ✅ Revenue Distribution
- [ ] Book published
- [ ] Customer purchases book
- [ ] Sale recorded
- [ ] Revenue distributed to:
  - [ ] Platform (15%)
  - [ ] Reviewer (2.5%)
  - [ ] Investors (25% pool)
  - [ ] Author (remainder)

### ✅ Transparency & Tracking
- [ ] Earnings dashboard shows data
- [ ] Sales transparency page works
- [ ] Reviewer earnings visible
- [ ] Investor returns visible
- [ ] Author sales visible

### ✅ Accountability
- [ ] Accountability status page loads
- [ ] Deadlines displayed correctly
- [ ] Refund system works (if tested)

---

## Test Data Setup

### Create Test Users

```python
# In Python shell or script
from glconnect.models import db, User
from glconnect.book_platform_models import BookPlatformUser

# Create Author
author_user = User(username='author1', email='author@test.com', role='author')
# ... set password, etc.

# Create Reviewer User
reviewer_user = User(username='reviewer1', email='reviewer@test.com', role='user')
# ... set password, etc.

# Create Investor User
investor_user = User(username='investor1', email='investor@test.com', role='user')
# ... set password, etc.

# Create Admin
admin_user = User(username='admin', email='admin@test.com', role='admin')
# ... set password, etc.
```

---

## Common Issues & Solutions

### Issue: Reviewer not showing in list
**Solution:** Check if reviewer is approved by admin

### Issue: Investment not updating campaign funding
**Solution:** Check database - `current_funding` should update

### Issue: Revenue not distributing
**Solution:** 
- Check if book is published
- Check if sale status is COMPLETED
- Check revenue_distribution_service logs

### Issue: Accountability page not loading
**Solution:** Ensure book has an investment campaign

---

## API Endpoints to Test

### Reviewer Endpoints
- `GET /mybook/reviewers` - List reviewers
- `GET /mybook/reviewers/register` - Register form
- `POST /mybook/reviewers/register` - Submit registration
- `GET /mybook/reviewers/<id>` - Reviewer profile
- `GET /mybook/admin/reviewers` - Admin panel
- `POST /mybook/admin/reviewers/<id>/approve` - Approve reviewer

### Investment Endpoints
- `GET /mybook/investments` - List campaigns
- `GET /mybook/investments/<id>` - Campaign details
- `GET /mybook/investments/<id>/invest` - Investment form
- `POST /mybook/investments/<id>/invest` - Make investment
- `GET /mybook/investments/my-returns/<book_id>` - Returns by book

### Review Endpoints
- `GET /mybook/books/<id>/request-review` - Request review form
- `POST /mybook/books/<id>/request-review` - Submit request
- `GET /mybook/reviews/<id>/submit` - Submit review form
- `POST /mybook/reviews/<id>/submit` - Submit review

### Earnings Endpoints
- `GET /mybook/earnings` - Earnings dashboard
- `GET /mybook/books/<id>/sales-transparency` - Sales transparency
- `GET /mybook/reviewers/my-earnings/<book_id>` - Reviewer earnings
- `GET /mybook/investments/my-returns/<book_id>` - Investor returns

---

## Next Steps

1. **Run through all scenarios** above
2. **Check database** to verify data is stored correctly
3. **Test edge cases** (multiple reviewers, multiple investors, etc.)
4. **Verify calculations** (revenue distribution percentages)
5. **Test accountability** system (deadlines, refunds)

---

## Success Criteria

✅ Reviewers can register and get accredited
✅ Authors can request reviews
✅ Reviewers can submit reviews
✅ Authors can create investment campaigns
✅ Investors can invest in campaigns
✅ Revenue distributes correctly on sales
✅ All parties can track earnings
✅ Accountability system works

If all checkboxes pass, the system is working correctly! 🎉


