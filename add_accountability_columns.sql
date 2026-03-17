-- Migration: Add accountability columns to investment_campaigns and book_investments
-- Run this script on your PostgreSQL database

-- Add cancelled_at and cancellation_reason to investment_campaigns
ALTER TABLE investment_campaigns 
ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS cancellation_reason TEXT;

-- Add refunded_at to book_investments
ALTER TABLE book_investments 
ADD COLUMN IF NOT EXISTS refunded_at TIMESTAMP;

-- Add is_guarantee_payment and notes to reviewer_earnings
ALTER TABLE reviewer_earnings 
ADD COLUMN IF NOT EXISTS is_guarantee_payment BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS notes TEXT;

-- Create refund_requests table if it doesn't exist
CREATE TABLE IF NOT EXISTS refund_requests (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(36) UNIQUE NOT NULL DEFAULT gen_random_uuid()::text,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    reason TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    processed_at TIMESTAMP,
    requested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    refund_transaction_id VARCHAR(100),
    payment_method VARCHAR(50),
    investment_id INTEGER NOT NULL REFERENCES book_investments(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on investment_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_refund_requests_investment_id ON refund_requests(investment_id);
CREATE INDEX IF NOT EXISTS idx_refund_requests_status ON refund_requests(status);

-- Add comments for documentation
COMMENT ON COLUMN investment_campaigns.cancelled_at IS 'Timestamp when campaign was cancelled';
COMMENT ON COLUMN investment_campaigns.cancellation_reason IS 'Reason for campaign cancellation';
COMMENT ON COLUMN book_investments.refunded_at IS 'Timestamp when investment was refunded';
COMMENT ON COLUMN reviewer_earnings.is_guarantee_payment IS 'True if this is a guarantee payment (book not published)';
COMMENT ON COLUMN reviewer_earnings.notes IS 'Additional notes about this earning';


