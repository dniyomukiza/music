-- Add revenue distribution tracking columns to book_sales table
-- Run this SQL script on your PostgreSQL database

-- Add columns to book_sales table
ALTER TABLE book_sales 
ADD COLUMN IF NOT EXISTS distributed_to_reviewers FLOAT DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS distributed_to_investors FLOAT DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS distribution_completed BOOLEAN DEFAULT FALSE;

-- Add investment and sales tracking columns to book_projects table
ALTER TABLE book_projects
ADD COLUMN IF NOT EXISTS has_investment_campaign BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS total_sales INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_revenue FLOAT DEFAULT 0.0;

