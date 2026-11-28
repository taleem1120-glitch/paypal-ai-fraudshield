"""OIDC bearer-token verification for server-side authentication.

Configure FRAUDSHIELD_OIDC_ISSUER, FRAUDSHIELD_OIDC_AUDIENCE and
FRAUDSHIELD_OIDC_JWKS_URL. Missing or invalid configuration fails closed.
Only RS256 tokens are accepted; token claims are never trusted before signature,
issuer, audience and time validation complete.
"""
from dataclasses import dataclass
import os
from functools import lru_cache

import jwt
from jwt import PyJWKClient


class AuthenticationDenied(PermissionError):
    """Raised when bearer authentication cannot be established."""


@dataclass(frozen=True)
class VerifiedPrincipal:
    subject_id: str
    issuer: str
    audience: str


@lru_cache(maxsize=8)
def _jwks_client(url: str):
    return PyJWKClient(url, cache_keys=False)


def authenticate_bearer(authorization_header: str) -> VerifiedPrincipal:
    if not isinstance(authorization_header, str):
        raise AuthenticationDenied("Authentication required.")
    scheme, separator, token = authorization_header.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token or " " in token:
        raise AuthenticationDenied("Authentication required.")

    issuer = os.environ.get("FRAUDSHIELD_OIDC_ISSUER", "").strip()
    audience = os.environ.get("FRAUDSHIELD_OIDC_AUDIENCE", "").strip()
    jwks_url = os.environ.get("FRAUDSHIELD_OIDC_JWKS_URL", "").strip()
    if not issuer or not audience or not jwks_url:
        raise AuthenticationDenied("Authentication service is not configured.")

    try:
        signing_key = _jwks_client(jwks_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer,
            audience=audience,
            options={
                "require": ["exp", "iat", "iss", "aud", "sub"],
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_iss": True,
                "verify_aud": True,
            },
        )
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject or subject != subject.strip() or len(subject) > 128:
            raise AuthenticationDenied("Authentication required.")
        return VerifiedPrincipal(
            subject_id=subject, issuer=issuer, audience=audience
        )
    except AuthenticationDenied:
        raise
    except Exception:
        # Do not expose token, key, provider, or claim details to callers.
        raise AuthenticationDenied("Authentication required.") from None
