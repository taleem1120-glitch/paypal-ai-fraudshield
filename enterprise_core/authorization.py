"""Fail-closed tenant authorization primitives.

The verified_subject_id argument MUST come from verified authentication
middleware (for example, a validated OIDC token). Never pass a browser-supplied
subject_id or tenant_id directly to this function.
"""
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .models import TenantMembership

ROLE_PERMISSIONS = {
    "viewer": frozenset({"cases.read"}),
    "analyst": frozenset({"cases.read", "cases.create"}),
    "investigator": frozenset({"cases.read", "cases.create", "cases.update_status"}),
    "tenant_admin": frozenset({
        "cases.read", "cases.create", "cases.update_status",
        "memberships.read", "memberships.manage",
    }),
}


class AuthorizationDenied(PermissionError):
    """Raised when identity, membership, or permission cannot be established."""


@dataclass(frozen=True)
class TenantContext:
    """Server-derived authorization context; never deserialize from a request."""
    tenant_id: str
    subject_id: str
    role: str


def _canonical_tenant_id(value):
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise AuthorizationDenied("Tenant access denied.") from None


def authorize_tenant(
    session: Session, *, verified_subject_id: str, requested_tenant_id: str,
    permission: str,
) -> TenantContext:
    """Resolve active membership and permission; deny by default.

    verified_subject_id must come from trusted server-side auth middleware.
    requested_tenant_id is only a selector, never proof of membership.
    """
    if (not isinstance(verified_subject_id, str)
            or not verified_subject_id.strip()
            or len(verified_subject_id) > 128):
        raise AuthorizationDenied("Tenant access denied.")
    tenant_id = _canonical_tenant_id(requested_tenant_id)
    subject_id = verified_subject_id.strip()

    # Set transaction-local RLS scope before querying tenant membership.
    if session.get_bind().dialect.name == "postgresql":
        session.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
            {"tenant_id": tenant_id},
        )

    membership = session.scalar(select(TenantMembership).where(
        TenantMembership.tenant_id == tenant_id,
        TenantMembership.subject_id == subject_id,
        TenantMembership.active.is_(True),
    ))
    if membership is None:
        raise AuthorizationDenied("Tenant access denied.")

    allowed = ROLE_PERMISSIONS.get(membership.role, frozenset())
    if permission not in allowed:
        raise AuthorizationDenied("Tenant access denied.")

    return TenantContext(
        tenant_id=tenant_id, subject_id=subject_id, role=membership.role
    )
