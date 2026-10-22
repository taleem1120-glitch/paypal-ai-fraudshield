import streamlit as st
import pandas as pd
from paypal_simulator import simulate_paypal_transaction
from paypal_sandbox import test_paypal_connection, get_paypal_sandbox_order, create_paypal_sandbox_order
from transactions import parse_order, active_order
from scoring import train_model, risk_decision
from investigations import build_report, csv_export, json_export
from investigation_ui import render_investigations

st.set_page_config(

    
    page_title="FraudShield AI",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ FraudShield AI")
st.caption("Explainable Payment Risk Intelligence | AI Prototype")

st.info(
    "Demonstration only. No real payments are processed. "
    "The machine learning model uses synthetic data, "
    "not real fraud records."
)
if st.button("🔗 Test PayPal Sandbox Connection"):
    with st.spinner("Connecting to PayPal Sandbox..."):
        success, message = test_paypal_connection()
    if success:
        st.success(message)
    else:
        st.error(message)
st.subheader("PayPal Sandbox Order Lookup")

order_id = st.text_input(
    "Enter PayPal Sandbox Order ID"
)

# Editing the lookup ID immediately detaches any previous order.
active_order(st.session_state, requested_id=order_id.strip())

if st.button("Get PayPal Sandbox Order"):
    active_order(st.session_state, lookup_started=True)
    if not order_id.strip():
        st.warning("Please enter an Order ID.")
    else:
        success, result = get_paypal_sandbox_order(order_id.strip())
        if success:
            try:
                snapshot = parse_order(result, order_id.strip())
                st.session_state["order_snapshot"] = snapshot
                st.session_state["transaction_amount"] = float(snapshot.amount)
                st.session_state["transaction_currency"] = snapshot.currency
                st.success("Sandbox order retrieved successfully.")
                st.json({"id": snapshot.order_id, "status": snapshot.status,
                         "amount": str(snapshot.amount), "currency": snapshot.currency})
            except ValueError:
                st.warning("Order could not be loaded: expected a matching ID and one valid currency amount.")
        else:
            st.error(result)
st.subheader("Create PayPal Sandbox Test Order")

if st.button("Create Sandbox Order ($1.00)"):
    with st.spinner("Creating PayPal Sandbox order..."):
        success, result = create_paypal_sandbox_order()

    if success:
        st.success("Sandbox order created successfully!")
        st.write("Order ID:", result.get("id"))
        st.json({"id": result.get("id"), "status": result.get("status")})
    else:
        st.error(str(result))
        
model = st.cache_resource(train_model)()

st.subheader("Transaction Information")
st.caption("PayPal Sandbox supplies the order amount, ID and status after lookup. Risk flags below are entered manually; they are not verified by PayPal.")
snapshot = st.session_state.get("order_snapshot")
if snapshot:
    st.info(f"PayPal Sandbox Order: {snapshot.order_id} | Status: {snapshot.status}")
if "transaction_amount" not in st.session_state:
    st.session_state["transaction_amount"] = 100.0
if "transaction_currency" not in st.session_state:
    st.session_state["transaction_currency"] = "USD"
amount = st.number_input("Transaction amount", min_value=0.0, step=1.0, key="transaction_amount")
currency = st.text_input("Currency code", key="transaction_currency")
# Once edited, the order is detached even if the user later restores the amount.
snapshot = active_order(st.session_state, amount=amount, currency=currency)
if currency != "USD":
    st.warning("Scoring supports USD only. This amount is not converted or treated as USD.")

country_mismatch = st.checkbox(
    "Customer and payment countries differ"
)

new_account = st.checkbox(
    "New customer account"
)

unusual_activity = st.checkbox(
    "Unusual transaction activity"
)

if st.button("Analyze Transaction", type="primary", disabled=currency != "USD"):
    try:
        report = build_report(model, amount, currency, country_mismatch,
                              new_account, unusual_activity, snapshot)
        provenance = report["provenance"]
        rule_score = report["rule_score"]
        reasons = [item["reason"] for item in report["triggered_rules"]]
        is_anomaly = report["is_anomaly"]
        anomaly_score = report["anomaly_decision_score"]
        st.session_state["latest_risk_report"] = report
    except Exception:
        st.session_state.pop("latest_risk_report", None)
        st.error("Analysis could not be completed. Check the transaction inputs and try again.")
        st.stop()

    st.divider()
    st.subheader("Risk Analysis Results")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Rule-Based Score", f"{rule_score}/100")

    with col2:
        st.metric(
            "ML Anomaly Detection",
            "Anomaly" if is_anomaly else "Typical"
        )

    with col3:
        st.metric(
            "Anomaly Decision Score",
            f"{anomaly_score:.3f}"
        )

    st.progress(rule_score / 100)

    
    risk_level, recommended_action = risk_decision(rule_score, is_anomaly)
    if risk_level == "HIGH RISK":
        st.error("HIGH RISK — Manual review recommended")
    elif risk_level == "LOW INDICATED RISK":
        st.success(risk_level)
    else:
        st.warning(f"{risk_level} — {recommended_action}")
    if is_anomaly:
        st.warning(
            "The machine learning model also identified "
            "this transaction as unusual compared with "
            "the synthetic training data."
        )

    st.subheader("Risk Explanation")

    if reasons:
        for reason in reasons:
            st.write("•", reason)
    else:
        st.write("No configured rule-based risk indicators.")

    st.caption("Alert sources describe input provenance. Manual flags are not verified by PayPal; model alerts only identify synthetic-data anomalies.")
    st.dataframe(report["rule_breakdown"], use_container_width=True)
    st.write("Decision basis:", report["decision_basis"])
    if report["alerts"]:
        st.dataframe(report["alerts"], use_container_width=True)

    st.subheader("Analysis Summary")

    summary_df = pd.DataFrame([{
        "Amount": amount,
        "Currency": currency,
        "Rule Score": rule_score,
        "ML Anomaly": "Yes" if is_anomaly else "No",
        "Recommended Action": recommended_action
    }])

    st.dataframe(
        summary_df,
        use_container_width=True
    )

    if "analysis_history" not in st.session_state:
        st.session_state["analysis_history"] = []
    st.session_state["analysis_history"].append({
        **provenance,
        "Report ID": report["report_id"],
        "Country Mismatch (manual)": country_mismatch,
        "New Account (manual)": new_account,
        "Unusual Activity (manual)": unusual_activity,
        "Rule Score": rule_score,
        "ML Anomaly": "Yes" if is_anomaly else "No",
        "ML Decision Score": round(anomaly_score, 4),
        "Risk Level": risk_level,
        "Recommended Action": recommended_action,
    })

    
    st.caption(
        "Important: Isolation Forest detects statistical "
        "anomalies, not proven fraud. Scores are illustrative "
        "and must not be used for real payment decisions."
            )

if st.session_state.get("analysis_history"):
    st.divider()
    st.subheader("Transaction Analysis History")
    st.caption("Session-only demo history. Cleared when the Streamlit session ends; no persistent storage.")
    history_df = pd.DataFrame(st.session_state["analysis_history"])
    st.dataframe(history_df, use_container_width=True)
    st.download_button(
        "Download Analysis History (CSV)",
        data=csv_export(st.session_state["analysis_history"]),
        file_name="fraudshield_analysis_history.csv",
        mime="text/csv",
    )

st.divider()
st.subheader("PayPal-Style Transaction Simulator")
st.caption(
    "Generates fictional transactions for demonstration only. "
    "No PayPal API connection or real payment is involved."
)

if st.button("Generate Simulated Transaction"):
    simulated_transaction = simulate_paypal_transaction(
        amount=max(float(amount), 0.01),
        currency=currency,
        country_mismatch=country_mismatch,
        new_account=new_account,
        unusual_activity=unusual_activity,
    )
    st.json(simulated_transaction)

# Persist the latest report across reruns so case attachment is explicit.
if st.session_state.get("latest_risk_report"):
    st.subheader("Explainable Risk Report")
    st.json(st.session_state["latest_risk_report"])
    st.download_button("Download risk report JSON",
                       json_export(st.session_state["latest_risk_report"]),
                       "fraudshield_risk_report.json", "application/json")

render_investigations(st, model)
