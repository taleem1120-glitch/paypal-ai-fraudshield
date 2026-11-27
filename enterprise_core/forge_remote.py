"""Tenant-bound read operations for authenticated Jira issue panels."""
from datetime import datetime, timezone
from functools import lru_cache
import json
import os
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response
import jwt
from sqlalchemy import select

from .authentication import VerifiedPrincipal
from .evidence import check_original
from .models import CaseEvidence
from .pilot_case import open_pilot_case
from .secure_cases import require_context


@lru_cache(maxsize=1)
def forge_keys():
    return jwt.PyJWKClient("https://forge.cdn.prod.atlassian-dev.net/.well-known/jwks.json",
                           timeout=3, cache_keys=False)


def forge_identity(authorization: str = Header(default="")):
    app_id = os.getenv("FRAUDSHIELD_FORGE_APP_ID")
    installation = os.getenv("FRAUDSHIELD_FORGE_INSTALLATION_ID")
    environment = os.getenv("FRAUDSHIELD_FORGE_ENVIRONMENT_ID")
    if not all((app_id, installation, environment)):
        raise HTTPException(503, "Forge connection is not provisioned.")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token or len(token) > 16384:
        raise HTTPException(401, "Invalid invocation.")
    try:
        key = forge_keys().get_signing_key_from_jwt(token)
        claims = jwt.decode(token, key.key, algorithms=["RS256"], audience=app_id,
                            issuer="forge/invocation-token",
                            options={"require":["exp","iat","nbf","aud","iss"]})
    except jwt.PyJWKClientConnectionError:
        raise HTTPException(503, "Forge identity service unavailable.") from None
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid invocation.") from None
    app = claims.get("app")
    account = claims.get("principal")
    if (not isinstance(app, dict) or app.get("id") != app_id
            or app.get("installationId") != installation
            or not isinstance(app.get("environment"), dict)
            or app["environment"].get("id") != environment
            or not isinstance(app.get("module"), dict)
            or app["module"].get("key") != "fraudshield-case-receipt"
            or claims.get("actorAccountId") or not isinstance(account, str) or not account):
        raise HTTPException(403, "Untrusted installation or actor.")
    try:
        bindings = json.loads(os.environ["FRAUDSHIELD_FORGE_ACCOUNT_BINDINGS"])
        if not isinstance(bindings, dict):
            raise ValueError
    except (KeyError, ValueError):
        raise HTTPException(503, "Account mapping unavailable.") from None
    subject = bindings.get(account)
    if not isinstance(subject, str) or not subject.strip() or len(subject) > 128:
        raise HTTPException(403, "Account is not provisioned.")
    return VerifiedPrincipal(subject, "forge/invocation-token", app_id)


def router(sessions, tenant):
    routes = APIRouter(prefix="/forge/cases")

    @routes.post("/pilot")
    def pilot(response: Response, principal=Depends(forge_identity)):
        response.headers["Cache-Control"] = "no-store"
        with sessions.begin() as session:
            return open_pilot_case(session, principal, tenant)

    @routes.get("/{case_id}/receipts")
    def lookup(case_id: UUID, response: Response, principal=Depends(forge_identity)):
        response.headers["Cache-Control"] = "no-store"
        with sessions.begin() as session:
            ctx = require_context(session, principal, tenant, "evidence.read")
            digests = session.scalars(select(CaseEvidence.digest).where(
                CaseEvidence.tenant_id == ctx.tenant_id, CaseEvidence.case_id == str(case_id)
            ).order_by(CaseEvidence.created_at.desc(), CaseEvidence.digest).limit(20)).all()
        return {"receipts": [{"schema":"fraudshield-receipt-v1", "case_id":str(case_id),
                              "sha256":digest} for digest in digests]}

    @routes.post("/{case_id}/receipts/{digest}/verify")
    def verify(case_id: UUID, digest: str, response: Response, principal=Depends(forge_identity)):
        response.headers["Cache-Control"] = "no-store"
        with sessions.begin() as session:
            try:
                check_original(session, principal, tenant, str(case_id), digest)
            except LookupError:
                raise HTTPException(404, "Evidence unavailable.") from None
            except ValueError:
                raise HTTPException(409, "Stored bytes failed verification.") from None
        return {"case_id":str(case_id), "sha256":digest, "verified":True,
                "checked_at":datetime.now(timezone.utc).isoformat()}
    return routes
