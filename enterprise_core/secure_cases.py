"""Authenticated case-service boundary.

HTTP handlers must call these functions with a VerifiedPrincipal produced by
authenticate_bearer(). Do not expose the lower-level cases module to routes.
"""
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AuditEvent, TenantMembership

from .authentication import VerifiedPrincipal
from .authorization import AuthorizationDenied, authorize_tenant
from . import cases


def require_context(session: Session, principal: VerifiedPrincipal, tenant_id: str, permission: str):
    if not isinstance(principal, VerifiedPrincipal):
        raise AuthorizationDenied("Authentication required.")
    return authorize_tenant(
        session,
        verified_subject_id=principal.subject_id,
        requested_tenant_id=tenant_id,
        permission=permission,
    )


def create_case(session: Session, *, principal, tenant_id, title, description=""):
    context = require_context(session, principal, tenant_id, "cases.create")
    return cases.create_case(
        session, tenant_id=context.tenant_id, actor_id=context.subject_id,
        title=title, description=description,
    )


def get_case(session: Session, *, principal, tenant_id, case_id):
    context = require_context(session, principal, tenant_id, "cases.read")
    return cases.get_case(session, tenant_id=context.tenant_id, case_id=case_id)


def list_cases(session: Session, *, principal, tenant_id, limit=50):
    context = require_context(session, principal, tenant_id, "cases.read")
    return cases.list_cases(session, tenant_id=context.tenant_id, limit=limit)


def transition_case(session: Session, *, principal, tenant_id, case_id, new_status):
    context = require_context(session, principal, tenant_id, "cases.update_status")
    return cases.transition_case(
        session, tenant_id=context.tenant_id, actor_id=context.subject_id,
        case_id=case_id, new_status=new_status,
    )


def list_case_events(session: Session, *, principal, tenant_id, case_id, limit=100):
    context = require_context(session, principal, tenant_id, "cases.read")
    return cases.list_case_events(
        session, tenant_id=context.tenant_id, case_id=case_id, limit=limit,
    )


def record_note(session, *, principal, tenant_id, case_id, note):
    ctx = require_context(session, principal, tenant_id, "cases.update_status")
    case = cases.get_case(session, tenant_id=ctx.tenant_id, case_id=case_id)
    if case is None:
        raise LookupError("Case unavailable.")
    note = cases._required_text(note, "note", 2000)
    event = AuditEvent(tenant_id=ctx.tenant_id, actor_id=ctx.subject_id, event_type="case.note",
                       object_type="case", object_id=case.id, details_json=json.dumps({"note": note}))
    session.add(event)
    session.flush()
    return event.id


def assign_case(session, *, principal, tenant_id, case_id, assignee):
    ctx = require_context(session, principal, tenant_id, "cases.update_status")
    case = cases.get_case(session, tenant_id=ctx.tenant_id, case_id=case_id)
    if case is None:
        raise LookupError("Case unavailable.")
    membership = session.scalar(select(TenantMembership).where(
        TenantMembership.tenant_id == ctx.tenant_id,
        TenantMembership.subject_id == assignee,
        TenantMembership.active.is_(True),
        TenantMembership.role.in_(("investigator", "tenant_admin")),
    ).with_for_update(read=True))
    if membership is None:
        raise ValueError("Assignee unavailable.")
    if case.assigned_subject != membership.subject_id:
        case.assigned_subject = membership.subject_id
        session.add(AuditEvent(tenant_id=ctx.tenant_id, actor_id=ctx.subject_id,
                               event_type="case.assigned", object_type="case", object_id=case.id,
                               details_json=json.dumps({"assignee": membership.subject_id})))
        session.flush()
    return case.assigned_subject
