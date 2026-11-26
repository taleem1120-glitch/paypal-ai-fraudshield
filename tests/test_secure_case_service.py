"""Tests for authenticated case-service boundary."""
import unittest
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from enterprise_core.authentication import VerifiedPrincipal
from enterprise_core.authorization import AuthorizationDenied
from enterprise_core.database import initialize_schema
from enterprise_core.models import TenantMembership
from enterprise_core.secure_cases import create_case, get_case, transition_case


class SecureCaseServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        initialize_schema(self.engine)
        self.session = Session(self.engine, expire_on_commit=False)
        self.tenant_a = str(uuid4())
        self.tenant_b = str(uuid4())
        self.principal = VerifiedPrincipal("subject-A", "https://issuer.example/", "fraudshield-api")
        self.session.add_all([
            TenantMembership(tenant_id=self.tenant_a, subject_id="subject-A", role="investigator", active=True),
            TenantMembership(tenant_id=self.tenant_b, subject_id="subject-B", role="tenant_admin", active=True),
        ])
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_authenticated_member_can_create_and_read_case(self):
        case = create_case(
            self.session, principal=self.principal, tenant_id=self.tenant_a,
            title="Authorized case",
        )
        self.session.commit()
        self.assertEqual(get_case(
            self.session, principal=self.principal,
            tenant_id=self.tenant_a, case_id=case.id,
        ).id, case.id)

    def test_tenant_selector_cannot_cross_membership_boundary(self):
        with self.assertRaises(AuthorizationDenied):
            get_case(
                self.session, principal=self.principal,
                tenant_id=self.tenant_b, case_id=str(uuid4()),
            )

    def test_raw_string_is_not_accepted_as_verified_principal(self):
        with self.assertRaises(AuthorizationDenied):
            create_case(
                self.session, principal="subject-A", tenant_id=self.tenant_a,
                title="Forged principal",
            )

    def test_viewer_cannot_change_case_status(self):
        viewer_tenant = str(uuid4())
        self.session.add(TenantMembership(
            tenant_id=viewer_tenant, subject_id="subject-A",
            role="viewer", active=True,
        ))
        self.session.commit()
        with self.assertRaises(AuthorizationDenied):
            transition_case(
                self.session, principal=self.principal, tenant_id=viewer_tenant,
                case_id=str(uuid4()), new_status="closed",
            )


if __name__ == "__main__":
    unittest.main()
