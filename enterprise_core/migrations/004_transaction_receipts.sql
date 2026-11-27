BEGIN;
CREATE TABLE IF NOT EXISTS transaction_receipts (
    tenant_id varchar(36) NOT NULL, case_id varchar(36) NOT NULL,
    request_id varchar(36) NOT NULL, digest varchar(64) NOT NULL,
    PRIMARY KEY (tenant_id, case_id, request_id),
    FOREIGN KEY (tenant_id, case_id, digest) REFERENCES case_evidence(tenant_id, case_id, digest)
);
ALTER TABLE transaction_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE transaction_receipts FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS receipt_scope ON transaction_receipts;
CREATE POLICY receipt_scope ON transaction_receipts
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
DROP TRIGGER IF EXISTS immutable_receipts ON transaction_receipts;
CREATE TRIGGER immutable_receipts BEFORE UPDATE OR DELETE ON transaction_receipts
    FOR EACH ROW EXECUTE FUNCTION fraudshield_reject_audit_mutation();
COMMIT;
