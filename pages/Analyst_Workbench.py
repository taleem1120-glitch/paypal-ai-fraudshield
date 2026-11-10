"""Analyst Workbench — offline, manually entered synthetic batch triage."""
import json
import csv
import pandas as pd
import streamlit as st
from batch_triage import triage
from scoring import train_model

st.set_page_config(page_title="FraudShield | Analyst Workbench", layout="wide")
st.title("FraudShield AI — Analyst Workbench")
st.caption("Synthetic/manual risk triage only. No actual fraud identification, automatic blocking or PayPal-verified risk signals.")
st.info("Analyze up to 200 fictional USD transactions together. This workbench never calls PayPal or processes real payments.")
example = ("case_id,amount_usd,country_mismatch,new_account,unusual_activity\n"
           "CASE001,18.00,no,no,no\nCASE002,1800.00,yes,yes,yes\n"
           "CASE003,25.00,no,yes,no\nCASE004,200.00,yes,no,yes")
raw = st.text_area("Synthetic CSV — exact column names required", value=example, height=160)
if st.button("Analyze batch", type="primary"):
    try:
        with st.spinner("Evaluating reproducible synthetic indicators..."):
            @st.cache_resource
            def cached_model():
                return train_model()
            result = triage(raw, cached_model())
        items = result["payload"]["findings"]
        high = sum(x["risk_band"] == "HIGH RISK" for x in items)
        flagged = sum(x["anomaly"] for x in items)
        a, b, c = st.columns(3)
        a.metric("Cases", len(items))
        b.metric("Rule-based high risk", high)
        c.metric("Synthetic model anomalies", flagged)
        st.subheader("Analyst review queue (not a fraud verdict)")
        st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)
        st.caption("Ranking is by illustrative rule score, then anomaly, then case ID. Scores are not calibrated fraud probabilities.")
        st.subheader("Reproducible audit export")
        st.code(result["sha256"], language="text")
        st.download_button("Download batch audit JSON",
            data=json.dumps(result, indent=2, ensure_ascii=False).encode("utf-8"),
            file_name="fraudshield_batch_audit.json", mime="application/json")
    except (ValueError, csv.Error) as exc:
        st.error(str(exc))
    except Exception:
        st.error("Analysis failed. Please check inputs and retry.")
