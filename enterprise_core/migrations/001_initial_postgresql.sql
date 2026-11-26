-- FraudShield Enterprise X initial PostgreSQL schema.
-- Apply with a controlled migration runner; do not use create_all() in production.
-- The application role must not own these tables or have BYPASSRLS privileges.

BEGIN;

CREATE TABLE IF NOT EXISTS investigation_cases (
    id varchar(36) PRIMARY KEY,
    tenant_id varchar(36) NOT NULL,
    title varchar(160) NOT NULL CHECK (char_length(title) BETWEEN 1 AND 160),
    description text NOT NULL DEFAULT '',
    status varchar(24) NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'in_review', 'closed')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    version integer NOT NULL DEFAULT 1 CHECK (version >= 1),
    CONSTRAINT uq_investigation_cases_tenant_id UNIQUE (tenant_id, id)
);

CREATE INDEX IF NOT EXISTS ix_investigation_cases_tenant_created
    ON investigation_cases (tenant_id, created_at DESC);

CREATE TABLE IF NOT EXISTS audit_events (
    id varchar(36) PRIMARY KEY,
    tenant_id varchar(36) NOT NULL,
    actor_id varchar(128) NOT NULL,
    event_type varchar(64) NOT NULL,
    object_type varchar(64) NOT NULL,
    object_id varchar(36) NOT NULL,
    occurred_at timestamptz NOT NULL DEFAULT now(),
    details_json text NOT NULL DEFAULT '{}',
    CONSTRAINT fk_audit_case_tenant
        FOREIGN KEY (tenant_id, object_id)
        REFERENCES investigation_cases (tenant_id, id)
);

CREATE INDEX IF NOT EXISTS ix_audit_events_tenant_occurred
    ON audit_events (tenant_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS ix_audit_events_object
    ON audit_events (tenant_id, object_type, object_id);

CREATE OR REPLACE FUNCTION fraudshield_reject_audit_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit_events are append-only';
END;
$$;

DROP TRIGGER IF EXISTS trg_audit_events_no_update ON audit_events;
CREATE TRIGGER trg_audit_events_no_update
    BEFORE UPDATE OR DELETE ON audit_events
    FOR EACH ROW EXECUTE FUNCTION fraudshield_reject_audit_mutation();

ALTER TABLE investigation_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE investigation_cases FORCE ROW LEVEL SECURITY;
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_cases ON investigation_cases;
CREATE POLICY tenant_isolation_cases ON investigation_cases
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

DROP POLICY IF EXISTS tenant_isolation_audit ON audit_events;
CREATE POLICY tenant_isolation_audit ON audit_events
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

COMMIT;
