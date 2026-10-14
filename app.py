
import streamlit as st

st.set_page_config(
    page_title="FraudShield AI",
    page_icon="🛡️",
    layout="centered"
)

st.title("🛡️ FraudShield AI")
st.caption("Payment Fraud Risk Analysis | Prototype")

st.info("Demo mode: No real payments are processed.")

amount = st.number_input(
    "Transaction amount (USD)",
    min_value=0.0,
    value=100.0
)

country_mismatch = st.checkbox(
    "Customer and payment countries differ"
)

new_account = st.checkbox(
    "New customer account"
)

unusual_activity = st.checkbox(
    "Unusual transaction activity"
)

if st.button("Analyze Transaction"):
    score = 0

    if amount > 1000:
        score += 25

    if country_mismatch:
        score += 30

    if new_account:
        score += 20

    if unusual_activity:
        score += 25

    st.metric("Risk Score", f"{score}/100")

    if score >= 60:
        st.error("High Risk - Manual review recommended")
    elif score >= 30:
        st.warning("Medium Risk - Additional verification")
    else:
        st.success("Low Risk - No major indicators detected")

    st.caption(
        "Illustrative rule-based assessment, not a "
        "validated fraud prediction."
    )
