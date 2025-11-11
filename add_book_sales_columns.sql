-- Migration: Add revenue distribution columns to book_sales table
-- Run this script on your PostgreSQL database

-- Add revenue distribution tracking columns to book_sales
ALTER TABLE book_sales 
ADD COLUMN IF NOT EXISTS distributed_to_reviewers DECIMAL(10, 2) DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS distributed_to_investors DECIMAL(10, 2) DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS distribution_completed BOOLEAN DEFAULT FALSE;

-- Add comments for documentation
COMMENT ON COLUMN book_sales.distributed_to_reviewers IS 'Total amount distributed to reviewers from this sale';
COMMENT ON COLUMN book_sales.distributed_to_investors IS 'Total amount distributed to investors from this sale';
COMMENT ON COLUMN book_sales.distribution_completed IS 'Whether revenue distribution has been completed for this sale';


