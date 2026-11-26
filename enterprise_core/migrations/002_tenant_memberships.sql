-- Tenant membership registry for server-side authorization.
-- Provision memberships only through a trusted administrative process.
BEGIN;

CREATE TABLE IF NOT EXISTS tenant_memberships (
    id varchar(36) PRIMARY KEY,
    tenant_id varchar(36) NOT NULL,
    subject_id varchar(128) NOT NULL,
    role varchar(32) NOT NULL CHECK (
        role IN ('viewer', 'analyst', 'investigator', 'tenant_admin')
    ),
    active boolean NOT NULL DEFAULT true,
    CONSTRAINT uq_tenant_membership_subject UNIQUE (tenant_id, subject_id)
);

CREATE INDEX IF NOT EXISTS ix_tenant_memberships_subject
    ON tenant_memberships (subject_id, tenant_id);

ALTER TABLE tenant_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_memberships FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_memberships ON tenant_memberships;
CREATE POLICY tenant_isolation_memberships ON tenant_memberships
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

COMMIT;
