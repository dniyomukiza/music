-- Migration: Add buyer_user_id column to book_purchases table
-- This allows buyers to purchase books with just a user account, without needing a BookPlatformUser profile

-- Add buyer_user_id column (nullable, references users.user_id)
ALTER TABLE book_purchases 
ADD COLUMN buyer_user_id INTEGER REFERENCES users(user_id);

-- Make buyer_id nullable (it was previously NOT NULL)
ALTER TABLE book_purchases 
ALTER COLUMN buyer_id DROP NOT NULL;

-- Add constraint to ensure at least one buyer identifier is set
ALTER TABLE book_purchases 
ADD CONSTRAINT check_buyer_exists 
CHECK ((buyer_id IS NOT NULL) OR (buyer_user_id IS NOT NULL));

-- Add index for faster queries
CREATE INDEX IF NOT EXISTS idx_book_purchases_buyer_user_id ON book_purchases(buyer_user_id);

-- Add comment
COMMENT ON COLUMN book_purchases.buyer_user_id IS 'Direct reference to users.user_id for buyers without BookPlatformUser profile';
COMMENT ON COLUMN book_purchases.buyer_id IS 'Reference to book_platform_users.id for users with profiles (nullable)';

