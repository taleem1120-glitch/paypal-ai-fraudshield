BEGIN;
CREATE TABLE IF NOT EXISTS case_evidence (
    tenant_id varchar(36) NOT NULL,
    case_id varchar(36) NOT NULL,
    digest varchar(64) NOT NULL CHECK (digest ~ '^[0-9a-f]{64}$'),
    payload bytea NOT NULL CHECK (octet_length(payload) BETWEEN 1 AND 1048576),
    actor_id varchar(128) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, case_id, digest),
    FOREIGN KEY (tenant_id, case_id) REFERENCES investigation_cases(tenant_id, id)
);
ALTER TABLE case_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_evidence FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS evidence_scope ON case_evidence;
CREATE POLICY evidence_scope ON case_evidence
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
DROP TRIGGER IF EXISTS immutable_evidence ON case_evidence;
CREATE TRIGGER immutable_evidence BEFORE UPDATE OR DELETE ON case_evidence
    FOR EACH ROW EXECUTE FUNCTION fraudshield_reject_audit_mutation();
COMMIT;
