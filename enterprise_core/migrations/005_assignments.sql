BEGIN;
ALTER TABLE investigation_cases ADD COLUMN IF NOT EXISTS assigned_subject varchar(128);
COMMIT;
