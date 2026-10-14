import streamlit as st
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from paypal_simulator import simulate_paypal_transaction
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


@st.cache_resource
def train_model():
    rng = np.random.default_rng(42)
    n = 3000

    data = np.column_stack([
        rng.lognormal(4.5, 1.0, n),
        rng.binomial(1, 0.10, n),
        rng.binomial(1, 0.20, n),
        rng.binomial(1, 0.08, n),
    ])

    model = IsolationForest(
        n_estimators=150,
        contamination=0.08,
        random_state=42
    )

    model.fit(data)
    return model


model = train_model()

st.subheader("Transaction Information")

amount = st.number_input(
    "Transaction amount (USD)",
    min_value=0.0,
    value=100.0,
    step=50.0
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

if st.button("Analyze Transaction", type="primary"):

    reasons = []
    rule_score = 0

    if amount > 1000:
        rule_score += 25
        reasons.append("Large transaction amount")

    if country_mismatch:
        rule_score += 30
        reasons.append("Country mismatch")

    if new_account:
        rule_score += 20
        reasons.append("New customer account")

    if unusual_activity:
        rule_score += 25
        reasons.append("Unusual transaction activity")

    features = pd.DataFrame([{
        "amount": amount,
        "country_mismatch": int(country_mismatch),
        "new_account": int(new_account),
        "unusual_activity": int(unusual_activity)
    }])

    prediction = model.predict(features)[0]
    anomaly_score = float(model.decision_function(features)[0])

    is_anomaly = prediction == -1

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

    
    if rule_score >= 60:
        risk_level = "HIGH RISK"
        recommended_action = "Manual review"
        st.error("HIGH RISK — Manual review recommended")
    elif is_anomaly:
        risk_level = "ANOMALY DETECTED"
        recommended_action = "Review unusual transaction"
        st.warning("ANOMALY DETECTED — Review recommended")
    elif rule_score >= 30:
        risk_level = "MEDIUM RISK"
        recommended_action = "Additional verification"
        st.warning("MEDIUM RISK — Additional verification")
    else:
        risk_level = "LOW INDICATED RISK"
        recommended_action = "Routine processing (demo only)"
        st.success("LOW INDICATED RISK")
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

    st.subheader("Analysis Summary")

    summary_df = pd.DataFrame([{
        "Amount (USD)": amount,
        "Rule Score": rule_score,
        "ML Anomaly": "Yes" if is_anomaly else "No",
        "Recommended Action": recommended_action
    }])

    st.dataframe(
        summary_df,
        use_container_width=True
    )

    
    st.caption(
        "Important: Isolation Forest detects statistical "
        "anomalies, not proven fraud. Scores are illustrative "
        "and must not be used for real payment decisions."
            )
