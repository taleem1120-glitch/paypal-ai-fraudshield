"""Tenant-scoped case operations and audit event creation."""
import json
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .models import AuditEvent, InvestigationCase

ALLOWED_TRANSITIONS = {
    "open": {"in_review", "closed"},
    "in_review": {"open", "closed"},
    "closed": set(),
}


def _required_text(value, field, maximum):
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text.")
    value = value.strip()
    if not value or len(value) > maximum:
        raise ValueError(f"{field} must contain 1 to {maximum} characters.")
    return value


def _uuid(value, field):
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise ValueError(f"{field} must be a valid UUID.") from None


def _set_tenant_context(session: Session, tenant_id: str):
    """Set transaction-local PostgreSQL RLS context; SQLite tests use service filters."""
    if session.get_bind().dialect.name == "postgresql":
        session.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
            {"tenant_id": tenant_id},
        )


def create_case(session: Session, *, tenant_id, actor_id, title, description=""):
    tenant_id = _uuid(tenant_id, "tenant_id")
    _set_tenant_context(session, tenant_id)
    actor_id = _required_text(actor_id, "actor_id", 128)
    title = _required_text(title, "title", 160)
    if not isinstance(description, str) or len(description) > 10000:
        raise ValueError("description must be text up to 10000 characters.")
    case = InvestigationCase(
        tenant_id=tenant_id, title=title, description=description
    )
    session.add(case)
    session.flush()
    session.add(AuditEvent(
        tenant_id=tenant_id, actor_id=actor_id,
        event_type="case.created", object_type="case", object_id=case.id,
        details_json=json.dumps({"status": "open"}, sort_keys=True),
    ))
    session.flush()
    return case


def get_case(session: Session, *, tenant_id, case_id):
    tenant_id = _uuid(tenant_id, "tenant_id")
    _set_tenant_context(session, tenant_id)
    case_id = _uuid(case_id, "case_id")
    return session.scalar(select(InvestigationCase).where(
        InvestigationCase.tenant_id == tenant_id,
        InvestigationCase.id == case_id,
    ))


def list_cases(session: Session, *, tenant_id, limit=50):
    tenant_id = _uuid(tenant_id, "tenant_id")
    _set_tenant_context(session, tenant_id)
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer between 1 and 100.")
    return list(session.scalars(
        select(InvestigationCase)
        .where(InvestigationCase.tenant_id == tenant_id)
        .order_by(InvestigationCase.created_at.desc(), InvestigationCase.id)
        .limit(limit)
    ))


def transition_case(session: Session, *, tenant_id, actor_id, case_id, new_status):
    tenant_id = _uuid(tenant_id, "tenant_id")
    _set_tenant_context(session, tenant_id)
    actor_id = _required_text(actor_id, "actor_id", 128)
    case = get_case(session, tenant_id=tenant_id, case_id=case_id)
    if case is None:
        return None
    if new_status not in ALLOWED_TRANSITIONS.get(case.status, set()):
        raise ValueError("Invalid case status transition.")
    old_status = case.status
    case.status = new_status
    session.flush()
    session.add(AuditEvent(
        tenant_id=tenant_id, actor_id=actor_id,
        event_type="case.status_changed", object_type="case", object_id=case.id,
        details_json=json.dumps(
            {"from": old_status, "to": new_status}, sort_keys=True
        ),
    ))
    session.flush()
    return case
