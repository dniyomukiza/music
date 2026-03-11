-- Add author_sales_payout_requests table for author sales payout flow (min $50, admin approval)
CREATE TABLE IF NOT EXISTS author_sales_payout_requests (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(36) UNIQUE NOT NULL DEFAULT (gen_random_uuid())::text,
    author_id INTEGER NOT NULL REFERENCES book_platform_users(id) ON DELETE CASCADE,
    amount FLOAT NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(20) DEFAULT 'PENDING',
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    paid_at TIMESTAMP WITH TIME ZONE,
    admin_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
