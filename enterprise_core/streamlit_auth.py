"""Streamlit OIDC login and tenant authorization gate for Enterprise mode.

Streamlit's built-in OIDC flow validates the ID token using .streamlit/secrets.toml.
This module only accepts claims exposed by Streamlit's authenticated st.user object,
then independently checks configured issuer/audience and active tenant membership.
"""
import os
import time
from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from .authentication import VerifiedPrincipal
from .authorization import AuthorizationDenied, TenantContext, authorize_tenant


class EnterpriseConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class EnterpriseSession:
    principal: VerifiedPrincipal
    tenant: TenantContext


def _claim(user, key):
    try:
        value = user.get(key)
    except AttributeError:
        value = getattr(user, key, None)
    return value


def require_enterprise_session(st, session_factory: sessionmaker) -> EnterpriseSession:
    """Redirect unauthenticated users to OIDC login; fail closed on all errors."""
    if _claim(st.user, "is_logged_in") is not True:
        st.info("Sign in with your organization's identity provider to continue.")
        st.login()
        st.stop()

    expected_issuer = os.environ.get("FRAUDSHIELD_OIDC_ISSUER", "").strip()
    expected_audience = os.environ.get("FRAUDSHIELD_OIDC_AUDIENCE", "").strip()
    tenant_id = os.environ.get("FRAUDSHIELD_DEFAULT_TENANT_ID", "").strip()
    if not expected_issuer or not expected_audience or not tenant_id:
        st.error("Enterprise authentication is not fully configured. Access is blocked.")
        st.stop()

    expected_org = os.environ.get("FRAUDSHIELD_AUTH0_ORGANIZATION")
    if expected_org and _claim(st.user, "org_id") != expected_org:
        st.error("Organization access denied.")
        st.stop()

    subject = _claim(st.user, "sub")
    issuer = _claim(st.user, "iss")
    audience = _claim(st.user, "aud")
    valid_audience = (
        audience == expected_audience
        or isinstance(audience, (list, tuple)) and expected_audience in audience
    )
    if (not isinstance(subject, str) or not subject or subject != subject.strip()
            or len(subject) > 128 or issuer != expected_issuer or not valid_audience):
        st.error("Your identity could not be verified for this application.")
        st.stop()

    issued, expires = _claim(st.user, "iat"), _claim(st.user, "exp")
    now = time.time()
    if not (type(issued) is int and type(expires) is int and issued <= now < expires):
        st.error("Your sign-in has expired or is invalid. Sign in again.")
        st.logout()
        st.stop()

    principal = VerifiedPrincipal(
        subject_id=subject,
        issuer=expected_issuer,
        audience=expected_audience,
    )
    session: Session = session_factory()
    try:
        tenant = authorize_tenant(
            session,
            verified_subject_id=principal.subject_id,
            requested_tenant_id=tenant_id,
            permission="cases.read",
        )
        session.rollback()
    except AuthorizationDenied:
        session.rollback()
        st.error("Your account is not an active member of this organization.")
        st.stop()
    except Exception:
        session.rollback()
        st.error("Enterprise authorization is temporarily unavailable. Access is blocked.")
        st.stop()
    finally:
        session.close()

    return EnterpriseSession(principal=principal, tenant=tenant)

def enterprise_auth_required():
    """Authentication is mandatory unless explicit local demo mode is selected."""
    return os.environ.get("FRAUDSHIELD_ENTERPRISE_AUTH_ENABLED", "true").strip().lower() not in {"0", "false", "no"}


def require_page_enterprise_access(st):
    """Apply the same login and tenant gate to directly opened multipage routes."""
    enabled = enterprise_auth_required()
    if not enabled:
        st.warning(
            "Enterprise authentication is disabled. This page is prototype-only "
            "and must not be exposed as a customer deployment."
        )
        return None

    from .database import make_engine, make_session_factory

    try:
        engine = make_engine()
    except Exception:
        st.error("Enterprise database is not configured. Access is blocked.")
        st.stop()
    try:
        return require_enterprise_session(st, make_session_factory(engine))
    finally:
        engine.dispose()

