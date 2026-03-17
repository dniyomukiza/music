-- Migration: Add purchase_format, paid_out_amount, and payout_requests for real user flows
-- Run this script on your PostgreSQL database

-- 1. Add purchase_format to book_purchases (digital, audiobook, bundle)
ALTER TABLE book_purchases
ADD COLUMN IF NOT EXISTS purchase_format VARCHAR(20) DEFAULT 'digital';

COMMENT ON COLUMN book_purchases.purchase_format IS 'Purchase type: digital (ebook), audiobook, or bundle';

-- 2. Add paid_out_amount to book_investments (tracks how much has been paid to investor)
ALTER TABLE book_investments
ADD COLUMN IF NOT EXISTS paid_out_amount FLOAT DEFAULT 0.0;

COMMENT ON COLUMN book_investments.paid_out_amount IS 'Total amount already paid out to investor; available = total_returns - paid_out_amount';

-- 3. Create payout_requests table for investor payout requests
CREATE TABLE IF NOT EXISTS payout_requests (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(36) UNIQUE NOT NULL,
    investment_id INTEGER NOT NULL REFERENCES book_investments(id) ON DELETE CASCADE,
    amount FLOAT NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(20) DEFAULT 'PENDING',  -- PENDING, PAID, CANCELLED
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    paid_at TIMESTAMP WITH TIME ZONE,
    admin_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payout_requests_investment ON payout_requests(investment_id);
CREATE INDEX IF NOT EXISTS idx_payout_requests_status ON payout_requests(status);

COMMENT ON TABLE payout_requests IS 'Investor requests to withdraw earnings; admin marks as paid after bank transfer';
