# Book Collaboration & Reviewers (Platform as Publishing Replacement)

This document describes how **book collaboration** and the **accredited reviewer** system work. The platform is designed as a **replacement for traditional publishing houses**: authors hire reviewers (and collaborate with co-authors/editors) and pay for completed work; reviewers earn extra income like freelancers.

---

## 1. Book Collaboration

### Purpose
Authors can invite others to work on a book in defined roles: **co-author**, **editor**, **reviewer** (for in-draft feedback), or **viewer** (read-only). Collaborators get access to the book in Ink Studio and can comment, suggest edits, or edit (depending on role).

### Flow
1. **Author** goes to **Book → Collaborate** and invites by **email** with a **role** and optional message.
2. System creates a **Collaboration** (with a placeholder until acceptance) and a **CollaborationInvitation** (unique link, 7-day expiry).
3. **Invitee** receives email, clicks link, and lands on the accept page. They must:
   - **Log in** (or create an account).
   - Have an **Ink Studio profile** (one-time setup if needed).
4. On **Accept**, the collaboration is updated with the invitee’s profile (`collaborator_id`, `joined_at`). The invitation is marked accepted.
5. **Collaboration list** shows:
   - **Active collaborators** (accepted, with `joined_at` set).
   - **Pending invitations** (all invitations for this book with status PENDING), so the author sees every outstanding invite by email/role.

### Roles
- **Co-author** – Can edit content and share ownership.
- **Editor** – Can suggest edits (e.g. chapter suggestions) and comment.
- **Reviewer** – In-book feedback role (distinct from *accredited* reviewers who do formal reviews for the marketplace).
- **Viewer** – Read-only access.

### Technical notes
- Pending invitations are loaded with a single query: all `CollaborationInvitation` rows whose `Collaboration` belongs to this book and status is PENDING.
- Collaborations are scoped per book; one invitation per (book, email, role) in practice.

---

## 2. Accredited Reviewers (Sign Up, Credentials, Approval)

### Purpose
**Accredited reviewers** are vetted freelancers who write **formal reviews** for books (for the marketplace and for author marketing). They can earn in two ways:
- **Revenue share** – A percentage of each book sale (from the platform’s reviewer pool).
- **Fixed fee per task** – Author agrees to pay a set amount when the review is completed (author-paid, like a freelancer task).

### Sign up and credentials
1. User goes to **Reviewers → Register** (or equivalent).
2. They submit:
   - **Name**, **bio**, **profile picture**, **portfolio URL**
   - **Credentials** – Education, certifications, publications (text)
   - **Specialties** – Genres they review (e.g. Fiction, Non-fiction)
   - **Default revenue share %** (e.g. 2.5%)
3. Application is saved with status **PENDING**. No review work is allowed until approved.

### Approval (admin)
- **Admin** uses **Admin → Reviewers** (or pending queue) to list **PENDING** applications.
- Admin **approves** → status becomes **ACCREDITED**, accreditation date set, expiry set (e.g. 1 year), and level set (e.g. Bronze/Silver from credentials).
- Admin can **reject** (status **REVOKED**) or **suspend** (status **SUSPENDED**).

Only **ACCREDITED** reviewers appear in the reviewer marketplace and can be chosen by authors for review requests.

---

## 3. Author Requests Review (Optional Fixed Fee)

### Flow
1. **Author** goes to **Book → Request review** and selects an **accredited reviewer**.
2. Optionally, author sets an **agreed fee** (fixed amount in currency) they will pay when the review is completed.
3. System creates a **ReviewRequest** with:
   - Book, reviewer, author (`requested_by_id`)
   - **agreed_fee** (optional)
   - Status **PENDING**
4. Reviewer is notified (e.g. by email). No separate “accept” step is required: when the reviewer **submits** a review for that book, the request is linked and the **agreed_fee** is applied to the review.

### Per-task (freelancer) model
- The **agreed fee** is a **fixed amount per completed review**, paid by the author (not from sales revenue).
- This is stored on **ReviewRequest** and copied to **BookReview** when the reviewer submits, so the platform can create a **ReviewerEarning** when the author **publishes** the review.

---

## 4. Reviewer Submits Review

1. **Reviewer** (accredited) goes to the book and **submits a review** (title, content, rating, revenue share %, minimum sales threshold, visibility).
2. If there is an open **ReviewRequest** for this book and this reviewer (PENDING or ACCEPTED):
   - The new **BookReview** is linked to that request (`review_request_id`).
   - **agreed_fee** from the request is copied to the review.
   - Review request status is set to **IN_PROGRESS**.
3. Review is saved with status **SUBMITTED**. Author can then **publish** or reject.

---

## 5. Author Publishes Review and Pays Task Fee

1. **Author** sees **submitted** reviews (e.g. on dashboard or book page) and can **publish** a review.
2. **Publish** (e.g. POST `/books/<book_id>/reviews/<review_id>/publish`):
   - Sets review status to **PUBLISHED** and `published_at`.
   - If the review has an **agreed_fee**:
     - Creates a **ReviewerEarning** for that amount (status PENDING), linked to the review.
     - Updates reviewer’s **total_earnings**.
   - If the review was linked to a **ReviewRequest**, marks the request **COMPLETED** and sets `completed_at`.
3. **Mark task as paid** (e.g. POST `/books/<book_id>/reviews/<review_id>/pay-task`):
   - Author confirms they have paid the reviewer (e.g. bank transfer or platform payout).
   - Sets **author_paid_at** on the review and marks the corresponding **ReviewerEarning** as **COMPLETED** and `paid_at`.

So: **reviewers get paid per completed task** (fixed fee) when the author publishes and then marks the task as paid; they can **also** earn **revenue share** from sales as before.

---

## 6. Revenue Share (Existing)

- When a book is sold, a **reviewer pool** (e.g. 10% of sale) is distributed among **published** reviews according to each review’s **revenue_share_percentage** and **minimum_sales_threshold**.
- This is unchanged and works alongside the new **author-paid task** flow.

---

## 7. Summary: Platform as Publishing Replacement

| Actor        | Role                                                                 |
|-------------|----------------------------------------------------------------------|
| **Author**  | Invites collaborators; requests accredited reviews; can offer a fixed fee per review; publishes reviews and marks task fees as paid. |
| **Collaborator** | Accepts invite, gets role-based access (co-author / editor / reviewer / viewer), comments and suggests edits. |
| **Reviewer**| Signs up with credentials → admin approves → accredited; accepts review requests; submits review; earns **fixed fee** (when author pays) and/or **revenue share** from sales. |
| **Admin**   | Approves or rejects reviewer applications (credentials and quality gate). |

Reviewers are treated as **freelancers**: they are **approved** once (credentials), then **paid per completed task** (fixed fee) by the author, and can also earn ongoing **revenue share** from book sales. Collaboration is **invitation-based** by email with clear roles and a single list of pending invitations per book.
