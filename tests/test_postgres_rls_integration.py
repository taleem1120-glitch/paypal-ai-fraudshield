"""Real PostgreSQL RLS integration tests.

The CI job supplies an admin URL for schema/role setup and a separate
non-owner application URL. SQLite tests do not prove PostgreSQL RLS behavior.
"""
import os
import unittest
from pathlib import Path
from uuid import uuid4

import psycopg
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from enterprise_core.authorization import AuthorizationDenied, authorize_tenant
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
            for migration_path in sorted(Path("enterprise_core/migrations").glob("*.sql")):
                conn.execute(migration_path.read_text())
            conn.execute("GRANT CONNECT ON DATABASE fraudshield_test TO fraudshield_app")
            conn.execute("GRANT USAGE ON SCHEMA public TO fraudshield_app")
            conn.execute("""
                GRANT SELECT, INSERT, UPDATE, DELETE
                ON investigation_cases, audit_events TO fraudshield_app
            """)
            conn.execute("GRANT SELECT, INSERT ON case_evidence, transaction_receipts TO fraudshield_app")
            conn.execute("GRANT SELECT ON tenant_memberships TO fraudshield_app")
        sqlalchemy_app_url = APP_URL.replace("postgresql://", "postgresql+psycopg://", 1)
        cls.engine = create_engine(sqlalchemy_app_url, pool_pre_ping=True, future=True)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        self.session = Session(self.engine, expire_on_commit=False)
        self.tenant_a = str(uuid4())
        self.tenant_b = str(uuid4())
        self.subject = "integration-user-" + str(uuid4())
        with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
            conn.execute(
                "INSERT INTO tenant_memberships (id, tenant_id, subject_id, role, active) "
                "VALUES (%s, %s, %s, %s, true)",
                (str(uuid4()), self.tenant_a, self.subject, "investigator"),
            )

    def tearDown(self):
        self.session.rollback()
        self.session.close()
        # The test database is disposable. TRUNCATE is intentionally used by
        # the privileged fixture cleanup because audit_events rejects DELETE.
        # This preserves the production append-only invariant under test.
        with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
            conn.execute("TRUNCATE TABLE transaction_receipts, case_evidence, audit_events, investigation_cases")
            conn.execute(
                "DELETE FROM tenant_memberships WHERE tenant_id IN (%s, %s)",
                (self.tenant_a, self.tenant_b),
            )

    def test_rls_hides_other_tenant_rows_even_when_query_is_unscoped(self):
        case = create_case(
            self.session, tenant_id=self.tenant_a, actor_id="integration-test",
            title="Tenant A protected case",
        )
        self.session.commit()
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
        self.assertIsNone(get_case(self.session, tenant_id=self.tenant_b, case_id=case.id))
        self.assertEqual(list_cases(self.session, tenant_id=self.tenant_b), [])

    def test_membership_authorization_works_through_non_owner_role(self):
        context = authorize_tenant(
            self.session, verified_subject_id=self.subject,
            requested_tenant_id=self.tenant_a, permission="cases.update_status",
        )
        self.assertEqual(context.tenant_id, self.tenant_a)
        self.assertEqual(context.role, "investigator")

    def test_membership_rls_and_missing_membership_deny_cross_tenant(self):
        with self.assertRaises(AuthorizationDenied):
            authorize_tenant(
                self.session, verified_subject_id=self.subject,
                requested_tenant_id=self.tenant_b, permission="cases.read",
            )

    def test_membership_rls_blocks_unscoped_cross_tenant_read(self):
        self.session.execute(
            text("SELECT set_config('app.tenant_id', :tenant, true)"),
            {"tenant": self.tenant_b},
        )
        rows = self.session.scalars(
            text("SELECT subject_id FROM tenant_memberships WHERE subject_id = :subject"),
            {"subject": self.subject},
        ).all()
        self.assertEqual(rows, [])

    def test_evidence_parallel_retry_custody_rls_and_immutability(self):
        from concurrent.futures import ThreadPoolExecutor
        from audit_reporting import create_audit_report, export_audit_json
        from enterprise_core import evidence
        from enterprise_core.authentication import VerifiedPrincipal
        principal = VerifiedPrincipal(self.subject, "test", "test")
        case = create_case(self.session, tenant_id=self.tenant_a, actor_id=self.subject, title="Intake")
        self.session.commit()
        raw = export_audit_json(create_audit_report({}, 0, False, 0, "low", "review", [])).encode()

        def preserve(_):
            with Session(self.engine) as session, session.begin():
                return evidence.preserve(session, principal, self.tenant_a, case.id, raw)

        with ThreadPoolExecutor(max_workers=4) as pool:
            receipts = list(pool.map(preserve, range(12)))
        self.assertTrue(all(r == receipts[0] for r in receipts))
        self.assertEqual(evidence.retrieve(self.session, principal, self.tenant_a, case.id,
                                           receipts[0]["sha256"]), raw)
        count = self.session.scalar(text("SELECT count(*) FROM audit_events WHERE object_id=:id "
                                         "AND event_type='evidence.preserved'"), {"id":case.id})
        self.assertEqual(count, 1)
        with self.assertRaises(DBAPIError):
            self.session.execute(text("UPDATE case_evidence SET actor_id='replacement'"))
        self.session.rollback()
        self.session.execute(text("SELECT set_config('app.tenant_id', :tenant, true)"),
                             {"tenant":self.tenant_b})
        self.assertEqual(self.session.scalar(text("SELECT count(*) FROM case_evidence")),0)

    def test_concurrent_pilot_setup_returns_one_case_and_original(self):
        from concurrent.futures import ThreadPoolExecutor
        from unittest.mock import patch
        from enterprise_core.authentication import VerifiedPrincipal
        from enterprise_core.pilot_case import open_pilot_case

        principal = VerifiedPrincipal(self.subject, "test", "test")

        def open_sample(_):
            with Session(self.engine) as session, session.begin():
                return open_pilot_case(session, principal, self.tenant_a)

        with patch.dict(os.environ, {"FRAUDSHIELD_PILOT_TENANT_ID":self.tenant_a}):
            with ThreadPoolExecutor(max_workers=4) as pool:
                receipts = list(pool.map(open_sample, range(12)))
        self.assertTrue(all(receipt == receipts[0] for receipt in receipts))
        self.session.execute(text("SELECT set_config('app.tenant_id', :tenant, true)"),
                             {"tenant":self.tenant_a})
        events = self.session.scalars(text("SELECT event_type FROM audit_events WHERE object_id=:id"),
                                      {"id":receipts[0]["case_id"]}).all()
        self.assertCountEqual(events, ["case.created","evidence.preserved"])


if __name__ == "__main__":
    unittest.main()
