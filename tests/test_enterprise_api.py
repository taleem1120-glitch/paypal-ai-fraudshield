import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import jwt
from auth0_api_python import ApiClient
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from audit_reporting import create_audit_report, export_audit_json
from enterprise_core.api import create_app
from enterprise_core.database import initialize_schema, make_engine
from enterprise_core.models import TenantMembership


class EnterpriseAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(cls.key.public_key()))
        cls.jwk.update(kid="test", alg="RS256", use="sig")

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tenant = str(uuid4())
        self.issuer = "https://tenant.example/"
        url = "sqlite:///" + str(Path(tmp.name) / "case.db")
        self.enterContext(patch.dict(os.environ, {
            "FRAUDSHIELD_AUTH0_DOMAIN": "tenant.example",
            "FRAUDSHIELD_AUTH0_API_AUDIENCE": "case-api",
            "FRAUDSHIELD_AUTH0_ORGANIZATION": "org_test",
            "FRAUDSHIELD_OIDC_ISSUER": self.issuer,
            "FRAUDSHIELD_DEFAULT_TENANT_ID": self.tenant, "FRAUDSHIELD_DATABASE_URL": url,
        }))
        engine = make_engine()
        initialize_schema(engine)
        with Session(engine) as session:
            for subject, role in [("alice", "investigator"), ("bob", "viewer")]:
                session.add(TenantMembership(tenant_id=self.tenant, subject_id=subject, role=role))
            session.commit()
        engine.dispose()

        async def discovery(url):
            if url == self.issuer + ".well-known/openid-configuration":
                return {"issuer": self.issuer, "jwks_uri": self.issuer + "keys"}
            if url == self.issuer + "keys":
                return {"keys": [self.jwk]}
            raise AssertionError("Unexpected discovery request")

        def offline_client(options):
            options.custom_fetch = discovery
            return ApiClient(options)

        self.enterContext(patch("enterprise_core.api.ApiClient", side_effect=offline_client))
        self.api = self.enterContext(TestClient(create_app()))

    def headers(self, **overrides):
        now = int(time.time())
        claims = dict(iss=self.issuer, aud="case-api", sub="alice", org_id="org_test",
                      iat=now, exp=now+300)
        token = jwt.encode(claims | overrides, self.key, algorithm="RS256", headers={"kid":"test"})
        return {"Authorization": "Bearer " + token}

    def test_signed_token_scope_and_role(self):
        for kwargs in [dict(aud="web-client"), dict(org_id="org_other"), dict(exp=1),
                       dict(iss="https://other.example/")]:
            with self.subTest(kwargs=kwargs):
                self.assertEqual(self.api.post("/cases", headers=self.headers(**kwargs),
                                               json={"title":"x"}).status_code, 401)
        for sub in ["bob", "unknown"]:
            self.assertEqual(self.api.post("/cases", headers=self.headers(sub=sub),
                                           json={"title":"x"}).status_code, 403)

    def test_preserve_retry_and_download_after_restart(self):
        headers = self.headers()
        case_id = self.api.post("/cases", headers=headers, json={"title":"Review"}).json()["case_id"]
        path = f"/cases/{case_id}/evidence"
        raw = export_audit_json(create_audit_report({}, 0, False, 0.2, "low", "review", [])).encode()
        result = self.api.post(path, headers=headers, content=raw)
        self.assertEqual(result.status_code, 200, result.text)
        receipt = result.json()
        self.assertEqual(self.api.post(path, headers=headers, content=raw).json(), receipt)
        self.assertEqual(self.api.post(path, headers=headers, content=b"{}").status_code,422)
        self.assertEqual(self.api.post(path, headers=headers, content=b"x"*1048577).status_code,413)
        with TestClient(create_app()) as restarted:
            url = path + "/" + receipt["sha256"]
            self.assertEqual(restarted.get(url, headers=headers).content,raw)
            self.assertEqual(restarted.get(url, headers=self.headers(sub="bob")).status_code,403)

    def test_abstention_and_reason_codes(self):
        body = dict(amount="1200", currency="USD")
        post = lambda: self.api.post("/assessments", headers=self.headers(), json=body)
        self.assertIsNone(post().json()["rule_score"])
        body.update(country_mismatch=True, new_account=True, unusual_activity=True)
        result = post().json()
        self.assertEqual((result["rule_score"],len(result["reason_codes"])),(100,4))
        body["currency"] = "IQD"
        self.assertEqual(post().json()["risk_band"], "abstain")
        body["new_account"] = "false"
        self.assertEqual(post().status_code,422)

    def test_intake_retry_and_conflict_preserve_original(self):
        headers = self.headers()
        case_id = self.api.post("/cases", headers=headers, json={"title":"Intake"}).json()["case_id"]
        path = f"/cases/{case_id}/transactions/{uuid4()}"
        body = {"amount":"19.00", "currency":"USD"}
        first = self.api.put(path, headers=headers, json=body)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(self.api.put(path,headers=headers,json=body).json(),first.json())
        self.assertEqual(self.api.put(path,headers=headers,json=body | {"amount":"20"}).status_code,409)
        self.assertEqual(self.api.put(path,headers=self.headers(sub="bob"),json=body).status_code,403)
        digest = first.json()["receipt"]["sha256"]
        result = self.api.get(f"/cases/{case_id}/evidence/{digest}",headers=headers)
        self.assertEqual(result.json()["transaction"]["amount"], "19.00")

    def test_case_assignment_note_and_transition(self):
        headers = self.headers()
        case_id = self.api.post("/cases",headers=headers,json={"title":"Case A"}).json()["case_id"]
        path = f"/cases/{case_id}"
        self.assertEqual(self.api.put(path+"/assignment",headers=headers,json={"subject":"bob"}).status_code,404)
        self.assertEqual(self.api.put(path+"/assignment",headers=headers,json={"subject":"alice"}).status_code,200)
        self.assertEqual(self.api.post(path+"/notes",headers=headers,json={"note":"Reviewed receipt"}).status_code,201)
        self.assertEqual(self.api.put(path+"/status",headers=headers,json={"status":"in_review"}).status_code,200)
        timeline = self.api.get(path+"/timeline",headers=headers).json()
        self.assertEqual([e["event"] for e in timeline],["case.created","case.assigned","case.note","case.status_changed"])

    def test_policy_matrix_216_synthetic_inputs(self):
        from itertools import product
        from enterprise_core.api import TransactionInput, assess
        for amount, currency, flags in product(["0","999.99","1000","1000.01"],
                                               ["USD","IQD"], product([None,False,True],repeat=3)):
            result = assess(TransactionInput(amount=amount,currency=currency,
                country_mismatch=flags[0],new_account=flags[1],unusual_activity=flags[2]))
            if currency == "IQD" or None in flags:
                self.assertEqual((result["risk_band"],result["rule_score"]),("abstain",None))
            else:
                expected = (25 if amount=="1000.01" else 0) + sum(
                    weight for flag, weight in zip(flags,[30,20,25]) if flag)
                self.assertEqual(result["rule_score"],expected)

    def test_forge_verification_requires_trusted_installation_and_fresh_membership(self):
        from types import SimpleNamespace
        from enterprise_core.models import CaseEvidence
        self.enterContext(patch.dict(os.environ, {
            "FRAUDSHIELD_FORGE_APP_ID":"test-app",
            "FRAUDSHIELD_FORGE_INSTALLATION_ID":"installation",
            "FRAUDSHIELD_FORGE_ENVIRONMENT_ID":"env",
            "FRAUDSHIELD_FORGE_ACCOUNT_BINDINGS":json.dumps({"account":"alice","viewer":"bob"}),
        }))
        keys = self.enterContext(patch("enterprise_core.forge_remote.forge_keys"))
        keys.return_value.get_signing_key_from_jwt.return_value = SimpleNamespace(key=self.key.public_key())
        now = int(time.time())
        app = {"id":"test-app","installationId":"installation","environment":{"id":"env"},
               "module":{"key":"fraudshield-case-receipt"}}
        claims = {"iss":"forge/invocation-token","aud":"test-app","iat":now,"nbf":now,"exp":now+60,
                  "principal":"account","app":app}

        def invocation(**changes):
            token = jwt.encode(claims | changes,self.key,algorithm="RS256",headers={"kid":"test"})
            return {"Authorization":"Bearer " + token}

        headers = self.headers()
        case = self.api.post("/cases",headers=headers,json={"title":"Forge"}).json()["case_id"]
        receipt = self.api.put(f"/cases/{case}/transactions/{uuid4()}",headers=headers,
                               json={"amount":"5","currency":"USD"}).json()["receipt"]
        path = f"/forge/cases/{case}/receipts"
        url = path + "/" + receipt["sha256"] + "/verify"
        self.assertEqual(self.api.get(path,headers=invocation()).json(),{"receipts":[receipt]})
        verified = self.api.post(url,headers=invocation())
        self.assertEqual(verified.status_code,200,verified.text)
        self.assertEqual(set(verified.json()),{"case_id","sha256","verified","checked_at"})
        self.assertTrue(verified.json()["verified"])
        timeline = self.api.get(f"/cases/{case}/timeline",headers=headers).json()
        self.assertEqual(timeline[-1]["event"],"evidence.verified")
        for changes, status in [
            ({"aud":"other"},401),({"exp":1},401),({"principal":"viewer"},403),
            ({"principal":"other"},403),({"actorAccountId":"impersonator"},403),
            ({"app":app | {"installationId":"other"}},403),
            ({"app":app | {"environment":{"id":"other"}}},403),
            ({"app":app | {"id":"other"}},403)]:
            with self.subTest(changes=changes):
                self.assertEqual(self.api.post(url,headers=invocation(**changes)).status_code,status)
        engine = make_engine()
        try:
            with Session(engine) as session, session.begin():
                row = session.get(CaseEvidence,(self.tenant,case,receipt["sha256"]))
                row.payload = b"synthetic corruption"
            self.assertEqual(self.api.post(url,headers=invocation()).status_code,409)
        finally:
            engine.dispose()

    def test_pilot_is_tenant_gated_repeatable_and_verifiable(self):
        from enterprise_core.forge_remote import forge_identity
        from enterprise_core.authentication import VerifiedPrincipal
        app = self.api.app
        principal = VerifiedPrincipal("alice", "test", "test")
        app.dependency_overrides[forge_identity] = lambda: principal
        path = "/forge/cases/pilot"
        with patch.dict(os.environ, {"FRAUDSHIELD_PILOT_TENANT_ID":str(uuid4())}):
            self.assertEqual(self.api.post(path).status_code,403)
        with patch.dict(os.environ, {"FRAUDSHIELD_PILOT_TENANT_ID":self.tenant}):
            principal = VerifiedPrincipal("bob", "test", "test")
            self.assertEqual(self.api.post(path).status_code,403)
            self.assertEqual(self.api.get("/cases",headers=self.headers()).json(),[])
            principal = VerifiedPrincipal("alice", "test", "test")
            response = self.api.post(path)
            self.assertEqual(response.status_code,200,response.text)
            receipt = response.json()
            self.assertEqual(self.api.post(path).json(),receipt)
            case = receipt["case_id"]
            url = f"/forge/cases/{case}/receipts/{receipt['sha256']}/verify"
            self.assertTrue(self.api.post(url).json()["verified"])
            events = self.api.get(f"/cases/{case}/timeline",headers=self.headers()).json()
            self.assertEqual([e["event"] for e in events],
                             ["case.created","evidence.preserved","evidence.verified"])

    def test_download_fails_closed_on_corrupt_original(self):
        from enterprise_core.models import CaseEvidence
        headers = self.headers()
        case = self.api.post("/cases", headers=headers, json={"title":"Integrity regression"}).json()["case_id"]
        raw = export_audit_json(create_audit_report({}, 0, False, 0.2, "low", "review", [])).encode()
        path = f"/cases/{case}/evidence"
        receipt = self.api.post(path, headers=headers, content=raw).json()
        digest = receipt["sha256"]
        self.assertEqual(self.api.get(path+"/invalid", headers=headers).status_code,422)
        self.assertEqual(self.api.get(path+"/"+"0"*64, headers=headers).status_code,404)
        self.assertEqual(self.api.get(path+"/"+digest, headers=headers).content,raw)
        engine = make_engine()
        try:
            with Session(engine) as session, session.begin():
                row = session.get(CaseEvidence,(self.tenant,case,digest))
                row.payload = b"synthetic corruption"
            result = self.api.get(path+"/"+digest, headers=headers)
            self.assertEqual(result.status_code,409)
            self.assertNotIn(b"synthetic corruption",result.content)
            self.assertEqual(self.api.get(path+"/"+digest,headers=self.headers(sub="bob")).status_code,403)
            timeline = self.api.get(f"/cases/{case}/timeline",headers=headers).json()
            self.assertEqual([e["event"] for e in timeline],
                             ["case.created","evidence.preserved","evidence.exported"])
        finally:
            engine.dispose()

    def test_transaction_boundary_and_invalid_inputs_are_not_preserved(self):
        headers = self.headers()
        case = self.api.post("/cases",headers=headers,json={"title":"Input validation"}).json()["case_id"]
        path = f"/cases/{case}/transactions/{uuid4()}"
        valid = {"amount":"1000.00","currency":"USD","country_mismatch":False,
                 "new_account":False,"unusual_activity":False}
        for changes in ({"amount":1000}, {"amount":True}, {"amount":"1e3"},
                        {"amount":"-1"}, {"amount":"01"}, {"amount":"1.001"},
                        {"amount":"1000000000"}, {"currency":"usd"},
                        {"country_mismatch":1}, {"new_account":"false"},
                        {"unusual_activity":[]}, {"tenant_id":str(uuid4())}):
            with self.subTest(changes=changes):
                self.assertEqual(self.api.put(path,headers=headers,json=valid | changes).status_code,422)
        events = self.api.get(f"/cases/{case}/timeline",headers=headers).json()
        self.assertEqual([e["event"] for e in events],["case.created"])
        first = self.api.put(path,headers=headers,json=valid)
        self.assertEqual(first.status_code,200,first.text)
        self.assertEqual(first.json()["assessment"]["rule_score"],0)
        self.assertEqual(self.api.put(path,headers=headers,json=valid).json(),first.json())
        second = self.api.put(f"/cases/{case}/transactions/{uuid4()}",headers=headers,
                              json=valid | {"amount":"1000.01"})
        self.assertEqual(second.status_code,200,second.text)
        self.assertEqual(second.json()["assessment"]["rule_score"],25)
        abstain = self.api.post("/assessments",headers=headers,
                                json=valid | {"currency":"IQD","new_account":None}).json()
        self.assertIsNone(abstain["rule_score"])
        self.assertEqual(set(abstain["reason_codes"]),{"unsupported_currency","missing_indicators"})
        for suffix, body in (("/status",{"status":"closed","tenant_id":str(uuid4())}),
                             ("/assignment",{"subject":"alice","role":"tenant_admin"})):
            self.assertEqual(self.api.put(f"/cases/{case}"+suffix,headers=headers,json=body).status_code,422)
