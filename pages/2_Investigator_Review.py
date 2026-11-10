import streamlit as st

from audit_reporting import export_audit_json, verify_audit_report
from review_queue import review_rows, synthetic_reports
from scoring import train_model

st.set_page_config(page_title="FraudShield | Investigator review", layout="wide")
st.title("Investigator review")
source = st.radio("Case source", ["Session analyses", "Synthetic demonstration"],
                  horizontal=True)
if source == "Synthetic demonstration":
    st.caption("Six fictional cases scored by the live model. Priority changes do not measure fraud accuracy.")
    if "review_demo_reports" not in st.session_state:
        st.session_state["review_demo_reports"] = synthetic_reports(st.cache_resource(train_model)())
    reports = st.session_state["review_demo_reports"]
else:
    reports = st.session_state.get("audit_reports", [])

if not reports:
    st.info("Analyze a transaction on the main page, or select Synthetic demonstration above.")
    st.stop()

by_id = {report["analysis_id"]: report for report in reports}
rows = review_rows(reports)
completed = st.session_state.setdefault("reviewed_analyses", set())
view = st.radio("Review status", ["Open", "Reviewed", "All"], horizontal=True)
visible = [r for r in rows if view == "All" or (r["Analysis"] in completed) == (view == "Reviewed")]
if not visible:
    st.info("No cases with this review status.")
    st.stop()

st.caption("Highest priority first. Within each priority, higher rule scores appear first, then earlier cases.")
st.dataframe(visible, hide_index=True, use_container_width=True)
labels = {r["Analysis"]: f'{r["Review priority"]} · {r["Amount"]} {r["Currency"]} · {r["Analysis"][:8]}'
          for r in visible}
case_id = st.selectbox("Inspect case", list(labels), format_func=labels.get)
report = by_id[case_id]
risk = report["risk_analysis"]
txn = report["transaction"]
row = next(r for r in visible if r["Analysis"] == case_id)
st.subheader(risk["recommended_action"])
st.write("Rules alone:", row["Rules only"], "→ Final priority:", risk["risk_level"])
st.write("Rule triggers:", ", ".join(risk["reasons"]) or "None")
st.write("Model finding:", "Unusual relative to synthetic training data" if risk["ml_anomaly"]
         else "Typical relative to synthetic training data")
st.write("Amount source:", report["source"], "· Order ID:", txn["order_id"])
st.write("Indicator source:", risk["indicator_source"])
st.json(risk.get("manual_indicators", {}))
if verify_audit_report(report):
    st.caption("Original analysis · SHA-256 " + report["integrity"]["digest"])
    st.download_button("Download original audit report", export_audit_json(report),
                       file_name=f"fraudshield_{case_id}.json", mime="application/json")
else:
    st.error("The stored analysis failed its integrity check.")
    st.stop()

st.caption("Review status is session-only. Marking a case reviewed records no fraud verdict and triggers no payment action.")
if case_id in completed:
    if st.button("Reopen case"):
        completed.remove(case_id)
        st.rerun()
elif st.button("Mark reviewed"):
    completed.add(case_id)
    st.rerun()
