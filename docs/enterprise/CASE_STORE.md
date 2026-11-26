# Enterprise Case Store — First Implemented Slice

## Implemented

- SQLAlchemy 2.x models for investigation cases and audit events.
- Tenant-scoped service methods for create, get, list and status transitions.
- Bounded case pagination (1–100).
- UUID validation and bounded text fields.
- Allowed status transitions: open → in_review/closed; in_review → open/closed; closed → terminal.
- Optimistic version column on case records.
- Audit event emitted for case creation and status change.
- ORM event hooks reject update/delete of audit events.
- PostgreSQL migration adds composite tenant/case foreign key, row-level security and a database trigger rejecting audit-event update/delete.
- PostgreSQL service calls set transaction-local app.tenant_id before data access.

## Critical deployment conditions

1. Do not expose the service functions to HTTP until authentication and server-side identity-to-tenant resolution are implemented.
2. Never accept tenant_id as an authorization claim from a browser request.
3. The PostgreSQL application role must be a non-owner and must not have BYPASSRLS.
4. The server must set app.tenant_id from verified identity context inside each transaction. A missing setting intentionally returns no tenant rows.
5. Apply the SQL migration using a controlled migration process. create_all() is for local/test bootstrap only.
6. SQLite tests exercise service-level tenant filters only; they do not validate PostgreSQL RLS or trigger semantics.
7. Database administrators and privileged roles remain part of the trust boundary. For regulated deployments, add independently administered retention/WORM controls and external audit export.

## Local test setup

Install the enterprise dependency set:

```bash
python -m pip install -r requirements-enterprise.txt
python -m unittest discover -s tests -v
```

For SQLite-only local experiments, set an explicit database URL:

```bash
export FRAUDSHIELD_DATABASE_URL=sqlite+pysqlite:///./fraudshield-enterprise-dev.db
```

This is not a production deployment recipe. Production should use PostgreSQL with the supplied migration and a dedicated least-privilege role.
