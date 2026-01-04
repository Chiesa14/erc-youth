-- Adds family_roles catalog + split user name fields (first/last/deliverance) and family_role_id.
-- This project uses raw SQL migrations (see existing migrations/*.sql).

CREATE TABLE IF NOT EXISTS family_roles (
  id SERIAL PRIMARY KEY,
  name VARCHAR NOT NULL UNIQUE,
  system_role VARCHAR NOT NULL DEFAULT 'Other',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_family_roles_name ON family_roles(name);

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS first_name VARCHAR;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS last_name VARCHAR;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS deliverance_name VARCHAR;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS family_role_id INTEGER;
