# Quick Test Links - Reviewer-Investor-Author System

## 🚀 Start Testing

Make sure your server is running:
```bash
python3 run.py
```

Then visit these URLs in your browser:

---

## 📋 Test Checklist

### 1. Reviewer System

#### Register as Reviewer
**URL:** `http://localhost:5000/mybook/reviewers/register`

**Steps:**
1. Login as any user
2. Fill out reviewer registration form
3. Submit application
4. **Expected:** Success message, status "Pending"

#### View Reviewer Marketplace
**URL:** `http://localhost:5000/mybook/reviewers`

**Steps:**
1. View list of accredited reviewers
2. Click on a reviewer to see profile
3. **Expected:** See reviewer details, credentials, specialties

#### Admin Approve Reviewer (Admin Only)
**URL:** `http://localhost:5000/mybook/admin/reviewers`

**Steps:**
1. Login as admin
2. Find pending reviewer
3. Click "Approve"
4. **Expected:** Reviewer status changes to "Accredited"

---

### 2. Investment System

#### View Investment Marketplace
**URL:** `http://localhost:5000/mybook/investments`

**Steps:**
1. View all active investment campaigns
2. Click on a campaign to see details
3. **Expected:** See campaign info, funding progress, book details

#### Create Investment Campaign (Author Only)
**URL:** `http://localhost:5000/mybook/books/<book_id>/create-campaign`

**Steps:**
1. Login as author
2. Navigate to your book
3. Create investment campaign
4. Fill out:
   - Funding Goal: $5,000
   - Revenue Share: 25%
   - Return Multiplier: 3x
5. **Expected:** Campaign created, status "Active"

#### Make Investment
**URL:** `http://localhost:5000/mybook/investments/<campaign_id>/invest`

**Steps:**
1. View campaign details
2. Click "Invest"
3. Enter investment amount
4. Confirm investment
5. **Expected:** Investment confirmed, campaign funding updated

---

### 3. Review System

#### Request Review (Author Only)
**URL:** `http://localhost:5000/mybook/books/<book_id>/request-review`

**Steps:**
1. Login as author
2. Navigate to your book
3. Request review from accredited reviewer
4. Set revenue share (e.g., 2.5%)
5. **Expected:** Review request sent

#### Submit Review (Reviewer Only)
**URL:** `http://localhost:5000/mybook/reviews/<review_id>/submit`

**Steps:**
1. Login as reviewer
2. Accept review request
3. Read the book
4. Submit review with rating and content
5. **Expected:** Review published on book page

---

### 4. Earnings & Transparency

#### Earnings Dashboard
**URL:** `http://localhost:5000/mybook/earnings`

**Steps:**
1. Login as any user (author/reviewer/investor)
2. View earnings dashboard
3. **Expected:** See earnings based on your role:
   - **Reviewers:** See reviewer earnings
   - **Investors:** See investment returns
   - **Authors:** See book sales

#### Sales Transparency
**URL:** `http://localhost:5000/mybook/books/<book_id>/sales-transparency`

**Steps:**
1. Login as author/reviewer/investor of the book
2. View complete sales breakdown
3. **Expected:** See per-sale revenue distribution

#### Reviewer Earnings by Book
**URL:** `http://localhost:5000/mybook/reviewers/my-earnings/<book_id>`

**Steps:**
1. Login as reviewer
2. View earnings for specific book
3. **Expected:** See all earnings from that book

#### Investor Returns by Book
**URL:** `http://localhost:5000/mybook/investments/my-returns/<book_id>`

**Steps:**
1. Login as investor
2. View returns for specific book
3. **Expected:** See ROI, returns, progress to cap

---

### 5. Accountability System

#### Accountability Status (Author Only)
**URL:** `http://localhost:5000/mybook/books/<book_id>/accountability`

**Steps:**
1. Login as author
2. View accountability status
3. **Expected:** See deadlines, days remaining, warnings

#### Refund Status (Investor Only)
**URL:** `http://localhost:5000/mybook/investments/<investment_id>/refund-status`

**Steps:**
1. Login as investor
2. View refund status for your investment
3. **Expected:** See refund requests, status, amounts

---

## 🧪 Complete Test Flow

### End-to-End Test Scenario

1. **Setup:**
   - Create 3 user accounts: Author, Reviewer, Investor
   - Create 1 admin account

2. **Step 1: Reviewer Registration**
   - Login as Reviewer
   - Register at `/mybook/reviewers/register`
   - Fill out credentials and specialties
   - Submit application

3. **Step 2: Admin Approval**
   - Login as Admin
   - Go to `/mybook/admin/reviewers`
   - Approve the reviewer

4. **Step 3: Author Creates Book**
   - Login as Author
   - Create a new book
   - Add some chapters
   - Set book details

5. **Step 4: Author Requests Review**
   - Go to book page
   - Request review from accredited reviewer
   - Set revenue share to 2.5%

6. **Step 5: Reviewer Submits Review**
   - Login as Reviewer
   - Accept review request
   - Submit review with rating and content

7. **Step 6: Author Creates Campaign**
   - Login as Author
   - Create investment campaign
   - Set funding goal: $5,000
   - Set revenue share: 25%

8. **Step 7: Investor Invests**
   - Login as Investor
   - View campaign at `/mybook/investments`
   - Invest $1,000
   - (Repeat with other investors to reach goal)

9. **Step 8: Author Publishes Book**
   - Login as Author
   - Set book status to "Published"
   - Set book price: $10.00

10. **Step 9: Customer Purchases Book**
    - Login as Customer (or new user)
    - Go to marketplace
    - Purchase the book

11. **Step 10: Verify Revenue Distribution**
    - Login as Author → Check earnings
    - Login as Reviewer → Check earnings ($0.25 per sale)
    - Login as Investor → Check returns (proportional share)

12. **Step 11: Check Transparency**
    - All parties check sales transparency page
    - Verify per-sale breakdowns
    - Verify totals match

---

## 🔍 Verification Points

### Database Checks

You can verify data in the database:

```sql
-- Check reviewers
SELECT * FROM accredited_reviewers;

-- Check campaigns
SELECT * FROM investment_campaigns;

-- Check investments
SELECT * FROM book_investments;

-- Check reviews
SELECT * FROM book_reviews;

-- Check sales
SELECT * FROM book_sales;

-- Check revenue distributions
SELECT * FROM revenue_distributions;

-- Check reviewer earnings
SELECT * FROM reviewer_earnings;

-- Check investment payouts
SELECT * FROM investment_payouts;
```

---

## ⚠️ Common Issues

### Issue: Reviewer not showing
**Solution:** Check if reviewer is approved by admin

### Issue: Campaign not visible
**Solution:** Check campaign status is "ACTIVE" or "FUNDED"

### Issue: Investment not updating
**Solution:** Check database - `current_funding` should update

### Issue: Revenue not distributing
**Solution:** 
- Check book is published
- Check sale status is COMPLETED
- Check revenue_distribution_service is called

### Issue: Routes return 404
**Solution:** 
- Check server is running
- Check URL paths are correct
- Check user is logged in

---

## 📊 Expected Results

### After Complete Test Flow:

✅ **Reviewer:**
- 1 accredited reviewer
- 1 published review
- Earnings from book sales ($0.25 per sale)

✅ **Investor:**
- 1+ investments
- Returns from book sales (proportional share)
- ROI tracking

✅ **Author:**
- 1 published book
- 1 investment campaign (funded)
- Sales revenue
- Revenue distributions visible

✅ **System:**
- All revenue distributed correctly
- Transparency pages working
- Accountability system active

---

## 🎯 Quick Test Commands

### Check if server is running:
```bash
curl http://localhost:5000/health
```

### Check routes exist:
```bash
curl -I http://localhost:5000/mybook/reviewers
curl -I http://localhost:5000/mybook/investments
curl -I http://localhost:5000/mybook/earnings
```

---

## 📝 Test Notes

- All routes require login
- Admin routes require admin role
- Some routes require specific roles (author/reviewer/investor)
- Database must have proper schema
- All models must be created

---

## ✅ Success Criteria

If you can:
1. ✅ Register as reviewer
2. ✅ Approve reviewer (as admin)
3. ✅ Create investment campaign
4. ✅ Make investment
5. ✅ Request and submit review
6. ✅ Purchase book
7. ✅ See revenue distributions
8. ✅ View earnings/transparency pages

Then the system is **working correctly**! 🎉


