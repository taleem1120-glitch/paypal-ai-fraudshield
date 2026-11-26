"""Authorized case operations; recheck membership on every operation."""
from .authorization import authorize_tenant
from . import cases


def _context(session, identity, permission):
    return authorize_tenant(session, verified_subject_id=identity.principal.subject_id,
                            requested_tenant_id=identity.tenant.tenant_id,
                            permission=permission)


def read_cases(session, identity, limit=50):
    ctx = _context(session, identity, "cases.read")
    return cases.list_cases(session, tenant_id=ctx.tenant_id, limit=limit)


def open_case(session, identity, title, description=""):
    ctx = _context(session, identity, "cases.create")
    return cases.create_case(session, tenant_id=ctx.tenant_id, actor_id=ctx.subject_id,
                             title=title, description=description)


def change_status(session, identity, case_id, new_status):
    ctx = _context(session, identity, "cases.update_status")
    return cases.transition_case(session, tenant_id=ctx.tenant_id, actor_id=ctx.subject_id,
                                 case_id=case_id, new_status=new_status)


def read_timeline(session, identity, case_id, limit=100):
    ctx = _context(session, identity, "cases.read")
    return cases.list_case_events(session, tenant_id=ctx.tenant_id, case_id=case_id, limit=limit)
