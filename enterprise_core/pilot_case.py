"""Create a repeatable synthetic case in the explicitly designated pilot tenant."""
import json
import os
from uuid import UUID, uuid5

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from audit_reporting import calculate_sha256, canonical_json
from risk_intelligence import Scenario, explain
from .authorization import AuthorizationDenied
from .evidence import preserve
from .models import AuditEvent, InvestigationCase
from .secure_cases import require_context


def open_pilot_case(session, principal, tenant):
    if os.getenv("FRAUDSHIELD_PILOT_TENANT_ID") != tenant:
        raise AuthorizationDenied("Synthetic pilot is disabled.")
    ctx = require_context(session, principal, tenant, "cases.create")
    require_context(session, principal, tenant, "evidence.write")
    case_id = str(uuid5(UUID(tenant), "fraudshield:pilot:checkout-review:v1"))
    insert = {"postgresql": pg_insert, "sqlite": sqlite_insert}[session.get_bind().dialect.name]
    stmt = insert(InvestigationCase).values(id=case_id, tenant_id=tenant,
        title="Synthetic pilot · checkout review",
        description="Fictional USD checkout used for evidence handoff.")
    added = session.scalar(stmt.on_conflict_do_nothing(index_elements=["id"]).returning(InvestigationCase.id))
    if added:
        session.add(AuditEvent(tenant_id=tenant, actor_id=ctx.subject_id, object_type="case",
                               object_id=case_id, event_type="case.created",
                               details_json=json.dumps({"status":"open", "source":"synthetic pilot"})))
        session.flush()
    scenario = Scenario("Fictional checkout", "1850.00", country_mismatch=True, new_account=True)
    document = {"schema":"fraudshield-pilot-v1", "source":"synthetic pilot",
                "assessment":explain(scenario)}
    document["integrity"] = {"algorithm":"SHA-256", "digest":calculate_sha256(document)}
    return preserve(session, principal, tenant, case_id, canonical_json(document).encode("utf-8"))
