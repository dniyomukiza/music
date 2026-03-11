-- Add stripe_payment_intent_id to book_investments for Stripe refund integration
-- Run this migration to enable admin-triggered refunds via Stripe API

ALTER TABLE book_investments
ADD COLUMN IF NOT EXISTS stripe_payment_intent_id VARCHAR(100) NULL;
