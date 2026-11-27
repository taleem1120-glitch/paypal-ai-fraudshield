"""Preserve exact uploaded audit bytes and record custody in the same transaction."""
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from audit_verification import verify_uploaded_audit
from . import cases
from .models import AuditEvent, CaseEvidence, TransactionReceipt
from .secure_cases import require_context


def custody(session, ctx, case_id, event, digest):
    session.add(AuditEvent(tenant_id=ctx.tenant_id, actor_id=ctx.subject_id,
                           event_type=event, object_type="case", object_id=case_id,
                           details_json=json.dumps({"sha256": digest})))
    session.flush()


def preserve(session, principal, tenant_id, case_id, raw):
    ctx = require_context(session, principal, tenant_id, "evidence.write")
    case = cases.get_case(session, tenant_id=ctx.tenant_id, case_id=case_id)
    if case is None:
        raise LookupError("Case unavailable.")
    if not verify_uploaded_audit(raw)[0]:
        raise ValueError("Audit integrity check failed.")
    digest = hashlib.sha256(raw).hexdigest()
    insert = {"postgresql": pg_insert, "sqlite": sqlite_insert}[session.get_bind().dialect.name]
    stmt = insert(CaseEvidence).values(tenant_id=ctx.tenant_id, case_id=case.id,
                                       actor_id=ctx.subject_id, payload=raw, digest=digest)
    inserted = session.scalar(stmt.on_conflict_do_nothing().returning(CaseEvidence.digest))
    if inserted:
        custody(session, ctx, case.id, "evidence.preserved", digest)
    return {"schema": "fraudshield-receipt-v1", "case_id": case.id, "sha256": digest}


def retrieve(session, principal, tenant_id, case_id, digest):
    ctx = require_context(session, principal, tenant_id, "evidence.read")
    row = session.scalar(select(CaseEvidence).where(
        CaseEvidence.tenant_id == ctx.tenant_id, CaseEvidence.case_id == case_id,
        CaseEvidence.digest == digest))
    if row is None:
        raise LookupError("Evidence unavailable.")
    if hashlib.sha256(row.payload).hexdigest() != row.digest:
        raise ValueError("Stored evidence integrity check failed.")
    custody(session, ctx, case_id, "evidence.exported", digest)
    return row.payload


class RequestConflict(ValueError):
    pass


def record_transaction(session, principal, tenant_id, case_id, request_id, raw):
    receipt = preserve(session, principal, tenant_id, case_id, raw)
    key = {"tenant_id": tenant_id, "case_id": case_id, "request_id": request_id}
    insert = {"postgresql": pg_insert, "sqlite": sqlite_insert}[session.get_bind().dialect.name]
    stmt = insert(TransactionReceipt).values(**key, digest=receipt["sha256"])
    session.execute(stmt.on_conflict_do_nothing())
    if session.get(TransactionReceipt, key).digest != receipt["sha256"]:
        raise RequestConflict("Transaction key conflict.")
    return receipt
