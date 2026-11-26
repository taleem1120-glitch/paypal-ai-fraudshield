"""Real PostgreSQL RLS integration tests.

The CI job supplies an admin URL for schema/role setup and a separate
non-owner application URL. These tests are skipped in local environments
without both URLs; SQLite tests do not prove PostgreSQL RLS behavior.
"""
import os
import unittest
from pathlib import Path
from uuid import uuid4

import psycopg
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from enterprise_core.cases import create_case, get_case, list_cases
from enterprise_core.models import InvestigationCase


ADMIN_URL = os.environ.get("FRAUDSHIELD_TEST_POSTGRES_ADMIN_URL")
APP_URL = os.environ.get("FRAUDSHIELD_TEST_POSTGRES_APP_URL")


@unittest.skipUnless(ADMIN_URL and APP_URL, "PostgreSQL integration URLs are not configured")
class PostgreSQLRLSTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
            conn.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'fraudshield_app') THEN
                        CREATE ROLE fraudshield_app LOGIN PASSWORD 'fraudshield_test_password'
                            NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
                    END IF;
                END
                $$;
            """)
            migration = Path("enterprise_core/migrations/001_initial_postgresql.sql").read_text()
            conn.execute(migration)
            conn.execute("GRANT CONNECT ON DATABASE fraudshield_test TO fraudshield_app")
            conn.execute("GRANT USAGE ON SCHEMA public TO fraudshield_app")
            conn.execute("""
                GRANT SELECT, INSERT, UPDATE, DELETE
                ON investigation_cases, audit_events TO fraudshield_app
            """)
        # SQLAlchemy must select psycopg 3 explicitly; postgresql:// defaults to psycopg2.
        sqlalchemy_app_url = APP_URL.replace("postgresql://", "postgresql+psycopg://", 1)
        cls.engine = create_engine(sqlalchemy_app_url, pool_pre_ping=True, future=True)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        self.session = Session(self.engine, expire_on_commit=False)
        self.tenant_a = str(uuid4())
        self.tenant_b = str(uuid4())

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    def test_rls_hides_other_tenant_rows_even_when_query_is_unscoped(self):
        case = create_case(
            self.session, tenant_id=self.tenant_a, actor_id="integration-test",
            title="Tenant A protected case",
        )
        self.session.commit()

        # Deliberately omit the service-layer tenant predicate. PostgreSQL RLS
        # must still prevent this application role from seeing the row.
        self.session.execute(
            text("SELECT set_config('app.tenant_id', :tenant, true)"),
            {"tenant": self.tenant_b},
        )
        visible = self.session.scalar(
            text("SELECT id FROM investigation_cases WHERE id = :case_id"),
            {"case_id": case.id},
        )
        self.assertIsNone(visible)

    def test_rls_rejects_cross_tenant_insert(self):
        self.session.execute(
            text("SELECT set_config('app.tenant_id', :tenant, true)"),
            {"tenant": self.tenant_a},
        )
        self.session.add(InvestigationCase(
            tenant_id=self.tenant_b, title="Must be blocked",
            description="", status="open", version=1,
        ))
        with self.assertRaises(DBAPIError):
            self.session.flush()
        self.session.rollback()

    def test_service_lookup_remains_tenant_scoped_on_postgres(self):
        case = create_case(
            self.session, tenant_id=self.tenant_a, actor_id="integration-test",
            title="Tenant A lookup",
        )
        self.session.commit()
        self.assertIsNone(get_case(
            self.session, tenant_id=self.tenant_b, case_id=case.id
        ))
        self.assertEqual(list_cases(self.session, tenant_id=self.tenant_b), [])


if __name__ == "__main__":
    unittest.main()
