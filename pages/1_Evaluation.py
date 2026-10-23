"""Synthetic-only evaluation page for FraudShield AI.

No PayPal requests are made here and no user data is stored.
"""
import pandas as pd
import streamlit as st

from evaluation import demonstration_cases, evaluate_synthetic_cases
from scoring import train_model, score_transaction, risk_decision

st.set_page_config(page_title="FraudShield | Evaluation", page_icon="📊", layout="wide")
st.title("📊 Synthetic Risk Evaluation")
st.warning(
    "Demonstration only: six hand-picked synthetic scenarios with no fraud labels. "
    "These results do not measure fraud accuracy, precision, recall, or real-world reliability."
)

@st.cache_resource
def get_model():
    return train_model()

try:
    model = get_model()
    cases = demonstration_cases()
    summary = evaluate_synthetic_cases(model, cases)
    rows = []
    for i, case in enumerate(cases, start=1):
        score, reasons, anomaly, decision_score = score_transaction(model, *case)
        risk_level, action = risk_decision(score, anomaly)
        rows.append({
            "Scenario": f"Synthetic {i}",
            "Amount (USD)": float(case[0]),
            "Country mismatch (manual)": bool(case[2]),
            "New account (manual)": bool(case[3]),
            "Unusual activity (manual)": bool(case[4]),
            "Rule score": int(score),
            "ML anomaly": bool(anomaly),
            "ML decision score": round(float(decision_score), 4),
            "Recommendation": action,
            "Rule explanations": "; ".join(reasons) or "None",
        })
except (ValueError, TypeError, ArithmeticError):
    st.error("The synthetic evaluation could not be completed. No results were saved.")
    st.stop()

left, middle, right = st.columns(3)
left.metric("Synthetic scenarios", summary.total)
middle.metric("ML anomalies", f"{summary.flagged} / {summary.total}")
right.metric("Rule/ML agreement", f"{summary.agreement_rate:.0%}")
st.caption(
    f"Average rule score: {summary.average_rule_score:.1f}/100. "
    "Agreement measures concordance between two model signals, not correctness."
)
frame = pd.DataFrame(rows)
st.subheader("Scenario-level results")
st.dataframe(frame, use_container_width=True, hide_index=True)
st.subheader("Rule scores across synthetic scenarios")
st.bar_chart(frame.set_index("Scenario")[["Rule score"]])
st.download_button(
    "Download synthetic evaluation (CSV)",
    data=frame.to_csv(index=False).encode("utf-8"),
    file_name="fraudshield_synthetic_evaluation.csv",
    mime="text/csv",
)
st.info(
    "This page is offline and does not read PayPal credentials, contact PayPal, "
    "or change the session-only analysis history."
)
