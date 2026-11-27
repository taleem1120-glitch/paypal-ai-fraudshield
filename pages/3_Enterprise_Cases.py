"""Tenant-scoped durable case and evidence workbench."""
import json

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from enterprise_core import evidence, secure_cases
from enterprise_core.authorization import AuthorizationDenied
from enterprise_core.database import make_engine, make_session_factory
from enterprise_core.streamlit_auth import require_page_enterprise_access

st.set_page_config(page_title="Enterprise cases", layout="wide")
access = require_page_enterprise_access(st)
if access is None:
    st.info("Sign in to an enterprise deployment to open persistent cases.")
    st.stop()

st.title("Enterprise cases")
principal = access.principal
tenant = access.tenant.tenant_id
engine = make_engine()
sessions = make_session_factory(engine)
scope = {"principal": principal, "tenant_id": tenant}
try:
    if access.tenant.role in {"analyst", "investigator", "tenant_admin"}:
        with st.form("create_case", clear_on_submit=True):
            title = st.text_input("Case title", max_chars=160)
            if st.form_submit_button("Create case"):
                with sessions.begin() as session:
                    secure_cases.create_case(session, **scope, title=title)
    with sessions.begin() as session:
        rows = secure_cases.list_cases(session, **scope)
        labels = {row.id: row.title for row in rows}
    if not labels:
        st.info("No cases in this organization.")
        st.stop()
    case_id = st.selectbox("Case", list(labels), format_func=lambda key: f"{labels[key]} · {key}")
    can_handle = access.tenant.role in {"investigator", "tenant_admin"}
    if can_handle:
        upload = st.file_uploader("Preserve an exported FraudShield audit (1 MiB maximum)", type=["json"])
        if st.button("Preserve original", disabled=upload is None):
            with sessions.begin() as session:
                evidence.preserve(session, principal, tenant, case_id, upload.read(1048577))
    with sessions.begin() as session:
        events = secure_cases.list_case_events(session, **scope, case_id=case_id, limit=200)
        st.dataframe([{"Time": e.occurred_at, "Event": e.event_type, "Actor": e.actor_id}
                      for e in events], hide_index=True)
    if can_handle:
        digest = st.text_input("Evidence SHA-256", max_chars=64)
        for event in events:
            if event.event_type == "evidence.preserved":
                st.code(json.dumps({"schema": "fraudshield-receipt-v1", "case_id": case_id,
                                    "sha256": json.loads(event.details_json)["sha256"]}))
        if st.button("Prepare verified export", disabled=len(digest) != 64):
            with sessions.begin() as session:
                raw = evidence.retrieve(session, principal, tenant, case_id, digest)
            st.download_button("Download original bytes", raw, "audit.json", "application/octet-stream")
except (AuthorizationDenied, LookupError):
    st.error("Case or evidence unavailable for this account.")
except ValueError as exc:
    st.error(str(exc))
except SQLAlchemyError:
    st.error("The case database is unavailable. Retry the operation.")
finally:
    engine.dispose()
