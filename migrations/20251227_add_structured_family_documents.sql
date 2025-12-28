-- Adds support for DB-stored (structured) family documents.
-- This project uses raw SQL migrations (see existing migrations/*.sql).

ALTER TABLE family_documents
  ADD COLUMN IF NOT EXISTS storage_type VARCHAR NOT NULL DEFAULT 'file';

ALTER TABLE family_documents
  ADD COLUMN IF NOT EXISTS title VARCHAR;

ALTER TABLE family_documents
  ADD COLUMN IF NOT EXISTS content_json TEXT;

ALTER TABLE family_documents
  ADD COLUMN IF NOT EXISTS content_html TEXT;

ALTER TABLE family_documents
  ALTER COLUMN file_path DROP NOT NULL;
