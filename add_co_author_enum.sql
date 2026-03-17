-- Migration: Add 'co_author' to collaborationrole enum
-- This adds the CO_AUTHOR role to the database enum if it doesn't exist

-- For PostgreSQL, we need to add the new enum value
-- Note: This will fail if the value already exists, which is fine
DO $$ 
BEGIN
    -- Check if 'co_author' already exists in the enum
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'co_author' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'collaborationrole')
    ) THEN
        -- Add the new enum value
        ALTER TYPE collaborationrole ADD VALUE 'co_author';
    END IF;
END $$;

-- Verify the enum values
SELECT enumlabel FROM pg_enum 
WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'collaborationrole')
ORDER BY enumsortorder;
