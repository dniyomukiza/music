-- Migration: Add digital_book_published and audiobook_published columns to book_projects table
-- Run this script on your PostgreSQL database
-- This migration is safe to run multiple times - it checks for existing columns before adding

-- Check and add digital book published columns (only if they don't exist)
DO $$
BEGIN
    -- Add digital_book_published column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'book_projects' 
        AND column_name = 'digital_book_published'
    ) THEN
        ALTER TABLE book_projects 
        ADD COLUMN digital_book_published BOOLEAN DEFAULT FALSE;
        
        COMMENT ON COLUMN book_projects.digital_book_published IS 'Whether digital book is published to marketplace';
    END IF;
    
    -- Add digital_book_published_at column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'book_projects' 
        AND column_name = 'digital_book_published_at'
    ) THEN
        ALTER TABLE book_projects 
        ADD COLUMN digital_book_published_at TIMESTAMP;
        
        COMMENT ON COLUMN book_projects.digital_book_published_at IS 'When digital book was published';
    END IF;
    
    -- Add audiobook_published column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'book_projects' 
        AND column_name = 'audiobook_published'
    ) THEN
        ALTER TABLE book_projects 
        ADD COLUMN audiobook_published BOOLEAN DEFAULT FALSE;
        
        COMMENT ON COLUMN book_projects.audiobook_published IS 'Whether audiobook is published to marketplace';
    END IF;
    
    -- Add audiobook_published_at column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'book_projects' 
        AND column_name = 'audiobook_published_at'
    ) THEN
        ALTER TABLE book_projects 
        ADD COLUMN audiobook_published_at TIMESTAMP;
        
        COMMENT ON COLUMN book_projects.audiobook_published_at IS 'When audiobook was published';
    END IF;
END $$;
