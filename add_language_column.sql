-- Migration script to add language column to book_projects table
-- Run this script to add language support to existing books

ALTER TABLE book_projects 
ADD COLUMN IF NOT EXISTS language VARCHAR(50) NULL;

-- Set default language to 'en' (English) for existing books
UPDATE book_projects 
SET language = 'en' 
WHERE language IS NULL;

-- Add index for faster language-based queries
CREATE INDEX IF NOT EXISTS idx_book_projects_language ON book_projects(language);

