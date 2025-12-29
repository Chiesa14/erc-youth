-- Fix migration: ensure family_activities has start_time/end_time columns.
-- Some databases may not have applied earlier migration yet.

ALTER TABLE family_activities
  ADD COLUMN IF NOT EXISTS start_time TIME;

ALTER TABLE family_activities
  ADD COLUMN IF NOT EXISTS end_time TIME;
