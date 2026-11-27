"""Auth0-protected API for one provisioned organization per deployment."""
from contextlib import asynccontextmanager
import json
import os
from typing import Literal
from uuid import UUID

from auth0_api_python import ApiClient, ApiClientOptions
from auth0_api_python.errors import AuthServerUnavailableError, BaseAuthError
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm.exc import StaleDataError
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from audit_reporting import calculate_sha256, canonical_json
from audit_verification import MAX_AUDIT_BYTES
from risk_intelligence import Scenario, explain
from . import evidence, forge_remote, secure_cases
from .authentication import VerifiedPrincipal
from .authorization import AuthorizationDenied
from .database import make_engine, make_session_factory


class CaseInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=160)


class NoteInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    note: str = Field(min_length=1, max_length=2000)


class AssignmentInput(BaseModel):
    subject: str = Field(min_length=1, max_length=128)


class StatusInput(BaseModel):
    status: Literal["open", "in_review", "closed"]


class TransactionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: str = Field(pattern=r"^(0|[1-9][0-9]{0,8})(\.[0-9]{1,2})?$")
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    country_mismatch: StrictBool | None = None
    new_account: StrictBool | None = None
    unusual_activity: StrictBool | None = None


def assess(tx):
    flags = (tx.country_mismatch, tx.new_account, tx.unusual_activity)
    result = {"policy": "manual-usd-v1", "input_source": "caller",
              "rule_score": None, "risk_band": "abstain", "reason_codes": []}
    if tx.currency != "USD":
        result["reason_codes"].append("unsupported_currency")
    if None in flags:
        result["reason_codes"].append("missing_indicators")
    if not result["reason_codes"]:
        scored = explain(Scenario("intake", tx.amount, *flags))
        result.update({key: scored[key] for key in ("rule_score", "risk_band", "reason_codes")})
    return result


def create_app():
    domain = os.environ["FRAUDSHIELD_AUTH0_DOMAIN"]
    audience = os.environ["FRAUDSHIELD_AUTH0_API_AUDIENCE"]
    org = os.environ["FRAUDSHIELD_AUTH0_ORGANIZATION"]
    tenant = str(UUID(os.environ["FRAUDSHIELD_DEFAULT_TENANT_ID"]))
    issuer = f"https://{domain}/"
    if issuer != os.environ["FRAUDSHIELD_OIDC_ISSUER"] or not org or not audience:
        raise ValueError("Invalid enterprise identity configuration.")
    client = ApiClient(ApiClientOptions(domain=domain, audience=audience,
                                        organization_policy="required", organization_id=org))
    engine = make_engine()
    sessions = make_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app):
        yield
        engine.dispose()

    app = FastAPI(title="FraudShield Enterprise X", lifespan=lifespan)

    async def identity(request: Request):
        header = request.headers.get("authorization", "")
        if not header.lower().startswith("bearer ") or len(header) > 16384:
            raise HTTPException(401, "Bearer token required.")
        try:
            claims = await client.verify_request({"authorization": header})
        except AuthServerUnavailableError:
            raise HTTPException(503, "Identity provider unavailable.") from None
        except BaseAuthError:
            raise HTTPException(401, "Invalid token.") from None
        subject = claims.get("sub")
        if (not isinstance(subject, str) or not 1 <= len(subject) <= 128
                or subject.strip() != subject or claims.get("iss") != issuer):
            raise HTTPException(401, "Invalid identity.")
        return VerifiedPrincipal(subject, issuer, audience)

    @app.exception_handler(AuthorizationDenied)
    async def forbidden(request, exc):
        return JSONResponse({"detail": "Access denied."}, status_code=403)

    @app.post("/cases", status_code=201)
    def open_case(body: CaseInput, principal=Depends(identity)):
        with sessions.begin() as session:
            row = secure_cases.create_case(session, principal=principal, tenant_id=tenant,
                                           title=body.title)
            return {"case_id": row.id}

    @app.get("/cases")
    def list_cases(principal=Depends(identity)):
        with sessions.begin() as session:
            return [{"case_id": row.id, "title": row.title, "status": row.status,
                     "assignee": row.assigned_subject}
                    for row in secure_cases.list_cases(session, principal=principal, tenant_id=tenant)]

    @app.get("/cases/{case_id}/timeline")
    def timeline(case_id: UUID, principal=Depends(identity)):
        with sessions.begin() as session:
            events = secure_cases.list_case_events(session, principal=principal, tenant_id=tenant,
                                                   case_id=str(case_id), limit=200)
            return [{"event": e.event_type, "actor": e.actor_id, "time": e.occurred_at,
                     "details": json.loads(e.details_json)} for e in events]

    @app.post("/cases/{case_id}/notes", status_code=201)
    def add_note(case_id: UUID, body: NoteInput, principal=Depends(identity)):
        with sessions.begin() as session:
            try:
                return {"event_id": secure_cases.record_note(session, principal=principal,
                        tenant_id=tenant, case_id=str(case_id), note=body.note)}
            except LookupError:
                raise HTTPException(404, "Case unavailable.") from None

    @app.put("/cases/{case_id}/assignment")
    def assign(case_id: UUID, body: AssignmentInput, principal=Depends(identity)):
        with sessions.begin() as session:
            try:
                result = secure_cases.assign_case(session, principal=principal, tenant_id=tenant,
                                                  case_id=str(case_id), assignee=body.subject)
            except (ValueError, LookupError):
                raise HTTPException(404, "Case or assignee unavailable.") from None
            except StaleDataError:
                raise HTTPException(409, "Assignment changed. Retry.") from None
            return {"assignee": result}

    @app.put("/cases/{case_id}/status")
    def change_status(case_id: UUID, body: StatusInput, principal=Depends(identity)):
        with sessions.begin() as session:
            try:
                row = secure_cases.transition_case(session, principal=principal, tenant_id=tenant,
                                                   case_id=str(case_id), new_status=body.status)
            except (ValueError, StaleDataError):
                raise HTTPException(409, "Case status conflict.") from None
            if row is None:
                raise HTTPException(404, "Case unavailable.")
            return {"status": row.status}

    @app.post("/assessments")
    def assessment(body: TransactionInput, principal=Depends(identity)):
        with sessions.begin() as session:
            secure_cases.require_context(session, principal, tenant, "cases.create")
            return assess(body)

    @app.post("/cases/{case_id}/evidence")
    async def upload(case_id: UUID, request: Request, principal=Depends(identity)):
        raw = bytearray()
        async for part in request.stream():
            if len(raw) + len(part) > MAX_AUDIT_BYTES:
                raise HTTPException(413, "Audit exceeds 1 MiB.")
            raw.extend(part)
        with sessions.begin() as session:
            try:
                return evidence.preserve(session, principal, tenant, str(case_id), bytes(raw))
            except LookupError:
                raise HTTPException(404, "Case unavailable.") from None
            except ValueError:
                raise HTTPException(422, "Invalid audit.") from None

    @app.put("/cases/{case_id}/transactions/{request_id}")
    def intake(case_id: UUID, request_id: UUID, body: TransactionInput, principal=Depends(identity)):
        result = assess(body)
        document = {"schema": "fraudshield-intake-v1", "request_id": str(request_id),
                    "transaction": body.model_dump(), "assessment": result}
        document["integrity"] = {"algorithm": "SHA-256", "digest": calculate_sha256(document)}
        with sessions.begin() as session:
            try:
                receipt = evidence.record_transaction(session, principal, tenant, str(case_id),
                                                      str(request_id), canonical_json(document).encode())
            except evidence.RequestConflict:
                raise HTTPException(409, "Transaction key already has different content.") from None
            except LookupError:
                raise HTTPException(404, "Case unavailable.") from None
        return {"assessment": result, "receipt": receipt}

    @app.get("/cases/{case_id}/evidence/{digest}")
    def download(case_id: UUID, digest: str, principal=Depends(identity)):
        with sessions.begin() as session:
            try:
                raw = evidence.retrieve(session, principal, tenant, str(case_id), digest)
            except LookupError:
                raise HTTPException(404, "Evidence unavailable.") from None
        return Response(raw, media_type="application/octet-stream",
                        headers={"Cache-Control": "no-store",
                                 "Content-Disposition": "attachment; filename=audit.json"})
    app.include_router(forge_remote.router(sessions, tenant))
    return app
