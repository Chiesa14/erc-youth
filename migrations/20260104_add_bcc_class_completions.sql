CREATE TABLE IF NOT EXISTS bcc_class_completions (
  id SERIAL PRIMARY KEY,
  member_id INTEGER NOT NULL REFERENCES family_members(id) ON DELETE CASCADE,
  class_number INTEGER NOT NULL,
  completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  recorded_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_bcc_member_class UNIQUE (member_id, class_number),
  CONSTRAINT ck_bcc_class_number_range CHECK (class_number >= 1 AND class_number <= 7)
);

CREATE INDEX IF NOT EXISTS ix_bcc_class_completions_member_id
  ON bcc_class_completions(member_id);

CREATE INDEX IF NOT EXISTS ix_bcc_class_completions_class_number
  ON bcc_class_completions(class_number);
