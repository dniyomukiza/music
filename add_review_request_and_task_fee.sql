-- Migration: Review requests and author-paid task fee for reviewers
-- Run on PostgreSQL when deploying the collaboration/reviewer task flow.

-- New enum for review request status (if not using SQLAlchemy sync)
-- DO $$ BEGIN CREATE TYPE review_request_status AS ENUM ('pending', 'accepted', 'in_progress', 'completed', 'cancelled'); EXCEPTION WHEN duplicate_object THEN null; END $$;

-- New table: review_requests
CREATE TABLE IF NOT EXISTS review_requests (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(36) UNIQUE NOT NULL DEFAULT gen_random_uuid()::text,
    book_project_id INTEGER NOT NULL REFERENCES book_projects(id) ON DELETE CASCADE,
    reviewer_id INTEGER NOT NULL REFERENCES accredited_reviewers(id) ON DELETE CASCADE,
    requested_by_id INTEGER NOT NULL REFERENCES book_platform_users(id) ON DELETE CASCADE,
    agreed_fee DECIMAL(10,2),
    agreed_revenue_share DECIMAL(5,2),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    accepted_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_review_requests_book ON review_requests(book_project_id);
CREATE INDEX IF NOT EXISTS idx_review_requests_reviewer ON review_requests(reviewer_id);
CREATE INDEX IF NOT EXISTS idx_review_requests_status ON review_requests(status);

-- Add columns to book_reviews
ALTER TABLE book_reviews ADD COLUMN IF NOT EXISTS agreed_fee DECIMAL(10,2);
ALTER TABLE book_reviews ADD COLUMN IF NOT EXISTS author_paid_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE book_reviews ADD COLUMN IF NOT EXISTS review_request_id INTEGER REFERENCES review_requests(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_book_reviews_review_request ON book_reviews(review_request_id);

COMMENT ON COLUMN book_reviews.agreed_fee IS 'Optional fixed fee author pays when review is published (freelancer task)';
COMMENT ON COLUMN book_reviews.author_paid_at IS 'When author marked the task fee as paid';
COMMENT ON COLUMN book_reviews.review_request_id IS 'Links to the review request if author sent one with agreed fee';
