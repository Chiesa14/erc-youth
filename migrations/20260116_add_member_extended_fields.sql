-- Migration: Add extended fields to family_members and families tables
-- Date: 2026-01-16

-- Family Members: Add new columns for documentation requirements
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS id_name VARCHAR;
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS deliverance_name VARCHAR;
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS profile_photo VARCHAR;
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS district VARCHAR;
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS sector VARCHAR;
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS cell VARCHAR;
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS village VARCHAR;
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS living_arrangement VARCHAR;
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS bcc_class_status VARCHAR;
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS commission VARCHAR;
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS parent_guardian_status VARCHAR;
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS employment_type VARCHAR;
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS job_title VARCHAR;
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS organization VARCHAR;
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS business_type VARCHAR;
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS business_name VARCHAR;
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS work_type VARCHAR;
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS work_description VARCHAR;
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS work_location VARCHAR;
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS institution VARCHAR;
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS program VARCHAR;
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS student_level VARCHAR;

-- Families: Add cover photo column
ALTER TABLE families ADD COLUMN IF NOT EXISTS cover_photo VARCHAR;
