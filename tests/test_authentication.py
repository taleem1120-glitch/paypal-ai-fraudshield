"""Authentication boundary regression tests."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from enterprise_core.authentication import (
    AuthenticationDenied, VerifiedPrincipal, authenticate_bearer,
)


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "FRAUDSHIELD_OIDC_ISSUER": "https://issuer.example/",
            "FRAUDSHIELD_OIDC_AUDIENCE": "fraudshield-api",
            "FRAUDSHIELD_OIDC_JWKS_URL": "https://issuer.example/.well-known/jwks.json",
        })
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_missing_or_malformed_bearer_is_rejected(self):
        for value in (None, "", "Basic abc", "Bearer ", "Bearer a b"):
            with self.subTest(value=value):
                with self.assertRaises(AuthenticationDenied):
                    authenticate_bearer(value)

    def test_missing_provider_configuration_fails_closed(self):
        with patch.dict(os.environ, {"FRAUDSHIELD_OIDC_AUDIENCE": ""}):
            with self.assertRaises(AuthenticationDenied):
                authenticate_bearer("Bearer signed-token")

    @patch("enterprise_core.authentication.jwt.decode")
    @patch("enterprise_core.authentication._jwks_client")
    def test_verified_token_returns_only_validated_subject(self, jwks, decode):
        jwks.return_value.get_signing_key_from_jwt.return_value = SimpleNamespace(key="public-key")
        decode.return_value = {
            "sub": "user-123", "iss": "https://issuer.example/",
            "aud": "fraudshield-api",
        }
        principal = authenticate_bearer("Bearer signed-token")
        self.assertEqual(principal, VerifiedPrincipal(
            subject_id="user-123", issuer="https://issuer.example/",
            audience="fraudshield-api",
        ))
        decode.assert_called_once()
        self.assertEqual(decode.call_args.kwargs["algorithms"], ["RS256"])
        self.assertEqual(decode.call_args.kwargs["issuer"], "https://issuer.example/")
        self.assertEqual(decode.call_args.kwargs["audience"], "fraudshield-api")

    @patch("enterprise_core.authentication.jwt.decode")
    @patch("enterprise_core.authentication._jwks_client")
    def test_invalid_signature_or_claims_are_rejected(self, jwks, decode):
        jwks.return_value.get_signing_key_from_jwt.return_value = SimpleNamespace(key="public-key")
        decode.side_effect = ValueError("invalid signature")
        with self.assertRaises(AuthenticationDenied):
            authenticate_bearer("Bearer forged-token")

    @patch("enterprise_core.authentication.jwt.decode")
    @patch("enterprise_core.authentication._jwks_client")
    def test_empty_subject_is_rejected(self, jwks, decode):
        jwks.return_value.get_signing_key_from_jwt.return_value = SimpleNamespace(key="public-key")
        decode.return_value = {"sub": " "}
        with self.assertRaises(AuthenticationDenied):
            authenticate_bearer("Bearer signed-token")


if __name__ == "__main__":
    unittest.main()
