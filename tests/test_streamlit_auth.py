"""Streamlit OIDC-to-tenant gate tests."""
import unittest
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from enterprise_core.database import initialize_schema
from enterprise_core.models import TenantMembership
from enterprise_core.streamlit_auth import require_enterprise_session


class StopRequested(Exception):
    pass


class FakeStreamlit:
    def __init__(self, user):
        self.user = user
        self.messages = []
        self.login_called = False

    def info(self, message):
        self.messages.append(message)

    def error(self, message):
        self.messages.append(message)

    def login(self):
        self.login_called = True

    def stop(self):
        raise StopRequested()


class StreamlitOIDCGateTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        initialize_schema(self.engine)
        self.factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.tenant = str(uuid4())
        with Session(self.engine) as session:
            session.add(TenantMembership(
                tenant_id=self.tenant, subject_id="oidc-user-1",
                role="investigator", active=True,
            ))
            session.commit()
        self.env = patch.dict("os.environ", {
            "FRAUDSHIELD_OIDC_ISSUER": "https://id.example/",
            "FRAUDSHIELD_OIDC_AUDIENCE": "fraudshield-enterprise",
            "FRAUDSHIELD_DEFAULT_TENANT_ID": self.tenant,
        })
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.engine.dispose()

    def test_logged_out_user_is_redirected_to_oidc_login(self):
        st = FakeStreamlit({"is_logged_in": False})
        with self.assertRaises(StopRequested):
            require_enterprise_session(st, self.factory)
        self.assertTrue(st.login_called)

    def test_valid_oidc_identity_requires_active_tenant_membership(self):
        st = FakeStreamlit({
            "is_logged_in": True,
            "sub": "oidc-user-1",
            "iss": "https://id.example/",
            "aud": ["fraudshield-enterprise"],
        })
        result = require_enterprise_session(st, self.factory)
        self.assertEqual(result.principal.subject_id, "oidc-user-1")
        self.assertEqual(result.tenant.tenant_id, self.tenant)
        self.assertEqual(result.tenant.role, "investigator")

    def test_wrong_issuer_is_rejected(self):
        st = FakeStreamlit({
            "is_logged_in": True, "sub": "oidc-user-1",
            "iss": "https://attacker.example/", "aud": "fraudshield-enterprise",
        })
        with self.assertRaises(StopRequested):
            require_enterprise_session(st, self.factory)
        self.assertTrue(any("could not be verified" in m for m in st.messages))

    def test_unregistered_user_is_denied(self):
        st = FakeStreamlit({
            "is_logged_in": True, "sub": "unregistered",
            "iss": "https://id.example/", "aud": "fraudshield-enterprise",
        })
        with self.assertRaises(StopRequested):
            require_enterprise_session(st, self.factory)
        self.assertTrue(any("not an active member" in m for m in st.messages))


if __name__ == "__main__":
    unittest.main()
