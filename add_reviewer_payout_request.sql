-- Add reviewer_payout_requests table for reviewer payout request flow (min $50, admin approval)
CREATE TABLE IF NOT EXISTS reviewer_payout_requests (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(36) UNIQUE NOT NULL DEFAULT (gen_random_uuid())::text,
    reviewer_id INTEGER NOT NULL REFERENCES accredited_reviewers(id) ON DELETE CASCADE,
    amount FLOAT NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(20) DEFAULT 'PENDING',
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    paid_at TIMESTAMP WITH TIME ZONE,
    admin_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
