-- Migration: Add CASCADE DELETE to announcement_views foreign key constraint
-- Date: 2025-08-24
-- Description: Fix announcement deletion issue by adding proper cascade delete to announcement_views

-- Step 1: Drop the existing foreign key constraint
ALTER TABLE announcement_views 
DROP CONSTRAINT IF EXISTS announcement_views_announcement_id_fkey;

-- Step 2: Add the new foreign key constraint with CASCADE DELETE
ALTER TABLE announcement_views 
ADD CONSTRAINT announcement_views_announcement_id_fkey 
FOREIGN KEY (announcement_id) 
REFERENCES announcements(id) 
ON DELETE CASCADE;

-- Verify the constraint was added correctly
SELECT conname, confdeltype 
FROM pg_constraint 
WHERE conname = 'announcement_views_announcement_id_fkey';

-- Expected result: confdeltype should be 'c' (CASCADE)