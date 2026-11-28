"""Fail-closed tenant authorization tests."""
import unittest
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from enterprise_core.authorization import (
    AuthorizationDenied, authorize_tenant,
)
from enterprise_core.database import initialize_schema
from enterprise_core.models import TenantMembership


class TenantAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        initialize_schema(self.engine)
        self.session = Session(self.engine, expire_on_commit=False)
        self.tenant_a = str(uuid4())
        self.tenant_b = str(uuid4())
        self.subject = "oidc|user-123"

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def add_membership(self, tenant, subject, role, active=True):
        self.session.add(TenantMembership(
            tenant_id=tenant, subject_id=subject, role=role, active=active,
        ))
        self.session.commit()

    def test_active_member_receives_server_derived_context(self):
        self.add_membership(self.tenant_a, self.subject, "investigator")
        context = authorize_tenant(
            self.session, verified_subject_id=self.subject,
            requested_tenant_id=self.tenant_a, permission="cases.update_status",
        )
        self.assertEqual(context.tenant_id, self.tenant_a)
        self.assertEqual(context.subject_id, self.subject)
        self.assertEqual(context.role, "investigator")

    def test_cross_tenant_selector_does_not_grant_membership(self):
        self.add_membership(self.tenant_a, self.subject, "tenant_admin")
        with self.assertRaises(AuthorizationDenied):
            authorize_tenant(
                self.session, verified_subject_id=self.subject,
                requested_tenant_id=self.tenant_b, permission="cases.read",
            )

    def test_inactive_membership_is_denied(self):
        self.add_membership(self.tenant_a, self.subject, "tenant_admin", active=False)
        with self.assertRaises(AuthorizationDenied):
            authorize_tenant(
                self.session, verified_subject_id=self.subject,
                requested_tenant_id=self.tenant_a, permission="cases.read",
            )

    def test_viewer_cannot_create_cases(self):
        self.add_membership(self.tenant_a, self.subject, "viewer")
        with self.assertRaises(AuthorizationDenied):
            authorize_tenant(
                self.session, verified_subject_id=self.subject,
                requested_tenant_id=self.tenant_a, permission="cases.create",
            )

    def test_unknown_role_and_permission_fail_closed(self):
        self.add_membership(self.tenant_a, self.subject, "future_role")
        with self.assertRaises(AuthorizationDenied):
            authorize_tenant(
                self.session, verified_subject_id=self.subject,
                requested_tenant_id=self.tenant_a, permission="cases.read",
            )

    def test_invalid_identity_or_tenant_is_denied(self):
        with self.assertRaises(AuthorizationDenied):
            authorize_tenant(
                self.session, verified_subject_id="",
                requested_tenant_id=self.tenant_a, permission="cases.read",
            )
        with self.assertRaises(AuthorizationDenied):
            authorize_tenant(
                self.session, verified_subject_id=self.subject,
                requested_tenant_id="not-a-uuid", permission="cases.read",
            )


if __name__ == "__main__":
    unittest.main()
