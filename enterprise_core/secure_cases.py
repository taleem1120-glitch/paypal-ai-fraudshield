"""Authenticated case-service boundary.

HTTP handlers must call these functions with a VerifiedPrincipal produced by
authenticate_bearer(). Do not expose the lower-level cases module to routes.
"""
from sqlalchemy.orm import Session

from .authentication import VerifiedPrincipal
from .authorization import AuthorizationDenied, authorize_tenant
from . import cases


def _context(session: Session, principal: VerifiedPrincipal, tenant_id: str, permission: str):
    if not isinstance(principal, VerifiedPrincipal):
        raise AuthorizationDenied("Authentication required.")
    return authorize_tenant(
        session,
        verified_subject_id=principal.subject_id,
        requested_tenant_id=tenant_id,
        permission=permission,
    )


def create_case(session: Session, *, principal, tenant_id, title, description=""):
    context = _context(session, principal, tenant_id, "cases.create")
    return cases.create_case(
        session, tenant_id=context.tenant_id, actor_id=context.subject_id,
        title=title, description=description,
    )


def get_case(session: Session, *, principal, tenant_id, case_id):
    context = _context(session, principal, tenant_id, "cases.read")
    return cases.get_case(session, tenant_id=context.tenant_id, case_id=case_id)


def list_cases(session: Session, *, principal, tenant_id, limit=50):
    context = _context(session, principal, tenant_id, "cases.read")
    return cases.list_cases(session, tenant_id=context.tenant_id, limit=limit)


def transition_case(session: Session, *, principal, tenant_id, case_id, new_status):
    context = _context(session, principal, tenant_id, "cases.update_status")
    return cases.transition_case(
        session, tenant_id=context.tenant_id, actor_id=context.subject_id,
        case_id=case_id, new_status=new_status,
    )


def list_case_events(session: Session, *, principal, tenant_id, case_id, limit=100):
    context = _context(session, principal, tenant_id, "cases.read")
    return cases.list_case_events(
        session, tenant_id=context.tenant_id, case_id=case_id, limit=limit,
    )
