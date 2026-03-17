-- Migration: Add independent publishing fields for digital books and audiobooks
-- This allows authors to publish digital books and audiobooks independently

-- Add digital book publishing fields
ALTER TABLE book_projects 
ADD COLUMN IF NOT EXISTS digital_book_published BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS digital_book_published_at TIMESTAMP NULL;

-- Add audiobook publishing fields
ALTER TABLE book_projects 
ADD COLUMN IF NOT EXISTS audiobook_published BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS audiobook_published_at TIMESTAMP NULL;

-- Update existing published books to have digital_book_published = true if they have digital_file_path
UPDATE book_projects 
SET digital_book_published = TRUE, 
    digital_book_published_at = published_at
WHERE status = 'published' 
  AND digital_file_path IS NOT NULL 
  AND digital_book_published = FALSE;

-- Update existing published books to have audiobook_published = true if they have audiobook
UPDATE book_projects 
SET audiobook_published = TRUE, 
    audiobook_published_at = published_at
WHERE status = 'published' 
  AND has_audiobook = TRUE 
  AND audiobook_published = FALSE;
