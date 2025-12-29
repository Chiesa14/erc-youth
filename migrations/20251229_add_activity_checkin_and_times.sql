-- Adds activity start/end time window fields + QR check-in session and attendance tables.
-- This project uses raw SQL migrations (see existing migrations/*.sql).

ALTER TABLE family_activities
  ADD COLUMN IF NOT EXISTS start_time TIME;

ALTER TABLE family_activities
  ADD COLUMN IF NOT EXISTS end_time TIME;

CREATE TABLE IF NOT EXISTS family_activity_checkin_sessions (
  id SERIAL PRIMARY KEY,
  activity_id INTEGER NOT NULL UNIQUE REFERENCES family_activities(id) ON DELETE CASCADE,
  token VARCHAR NOT NULL UNIQUE,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  valid_from TIMESTAMPTZ,
  valid_until TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_family_activity_checkin_sessions_token
  ON family_activity_checkin_sessions(token);

CREATE TABLE IF NOT EXISTS family_activity_attendances (
  id SERIAL PRIMARY KEY,
  activity_id INTEGER NOT NULL REFERENCES family_activities(id) ON DELETE CASCADE,
  attendee_name VARCHAR NOT NULL,
  family_of_origin_id INTEGER REFERENCES families(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_family_activity_attendances_activity_id
  ON family_activity_attendances(activity_id);
