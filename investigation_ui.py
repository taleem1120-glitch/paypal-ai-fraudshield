"""Streamlit investigation workspace. All records remain in the current session."""

from benchmarking import (benchmark_csv, evaluate, parse_labeled_csv, synthetic_dataset)
from investigations import (STATUSES, MAX_UPLOAD_BYTES, LIMITATIONS, add_evidence,
                           attach_report, case_exports, evidence_record, json_export,
                           new_case, update_case, record_evidence_verification, utc_now)
from audit import verify_case


def render_investigations(st, model):
    st.divider()
    st.subheader("Investigation Cases")
    st.caption("Session-only proof of concept. Export cases before leaving; records do not survive session loss.")
    st.caption(LIMITATIONS)
    cases = st.session_state.setdefault("investigation_cases", {})
    with st.form("create_case"):
        title = st.text_input("Case title", key="new_case_title")
        investigator = st.text_input("Investigator reference", key="new_case_investigator")
        notes = st.text_area("Case notes", key="new_case_notes")
        if st.form_submit_button("Create investigation case"):
            try:
                case = new_case(title, investigator, notes)
                cases[case["case_id"]] = case
                st.session_state["selected_case"] = case["case_id"]
                st.success("Case created.")
            except ValueError as error:
                st.error(str(error))
    if cases:
        selected = st.selectbox("Selected case", list(cases), key="selected_case",
                                format_func=lambda key: f"{cases[key]['title']} ({key})")
        case = cases[selected]
        st.write("Case ID:", selected)
        if not verify_case(case):
            st.error("Case consistency check failed. Export and review the record before further changes.")
        st.caption("Unsigned session audit history detects inconsistent records; it does not authenticate authors or prevent a full rewrite.")
        if st.button("Check case consistency"):
            if verify_case(case):
                st.success("Session event links and current case records are consistent.")
            else:
                st.error("Case consistency check failed.")
        with st.form(f"edit_case_{selected}"):
            title = st.text_input("Edit case title", value=case["title"])
            investigator = st.text_input("Edit investigator reference", value=case["investigator_reference"])
            notes = st.text_area("Edit case notes", value=case["notes"])
            status = st.selectbox("Case status", STATUSES, index=STATUSES.index(case["status"]))
            if st.form_submit_button("Save case details"):
                try:
                    update_case(case, title, investigator, notes, status)
                    st.success("Case details saved.")
                except ValueError as error:
                    st.error(str(error))
        latest = st.session_state.get("latest_risk_report")
        if latest:
            st.write("Latest analysis report:", latest["report_id"])
            if st.button("Attach latest analysis to selected case"):
                try:
                    attach_report(case, latest)
                    st.success("Analysis snapshot attached.")
                except ValueError as error:
                    st.warning(str(error))
        st.caption("Evidence: metadata and SHA-256 only. Keep original files separately. Maximum file size: 10 MB.")
        with st.form(f"evidence_{selected}", clear_on_submit=True):
            upload = st.file_uploader("Evidence file", key=f"evidence_file_{selected}")
            source = st.text_input("Evidence source reference")
            collected_key = f"evidence_collected_{selected}"
            st.session_state.setdefault(collected_key, utc_now())
            collected = st.text_input("Collected at (ISO 8601 with timezone)", key=collected_key)
            description = st.text_area("Evidence description")
            if st.form_submit_button("Record evidence metadata"):
                try:
                    if upload is None:
                        raise ValueError("Choose an evidence file.")
                    if upload.size > MAX_UPLOAD_BYTES:
                        raise ValueError("Evidence must be at most 10 MB.")
                    record = evidence_record(upload.getvalue(), upload.name, source, collected, description)
                    add_evidence(case, record)
                    st.success("Evidence metadata and SHA-256 recorded. File bytes are not stored in the case.")
                except ValueError as error:
                    st.error(str(error))
        if case["evidence"]:
            st.dataframe(case["evidence"], use_container_width=True)
            evidence_id = st.selectbox("Evidence to verify", [item["evidence_id"] for item in case["evidence"]],
                                       key=f"verify_id_{selected}")
            check_file = st.file_uploader("Re-upload original file to verify hash", key=f"verify_file_{selected}")
            if st.button("Verify evidence hash"):
                if check_file is None or check_file.size > MAX_UPLOAD_BYTES:
                    st.error("Choose a file of at most 10 MB.")
                else:
                    try:
                        if record_evidence_verification(case, evidence_id, check_file.getvalue()):
                            st.success("SHA-256 matches the recorded bytes.")
                        else:
                            st.error("SHA-256 mismatch: the bytes differ from the recorded evidence.")
                    except ValueError as error:
                        st.error(str(error))
        st.write("Attached analysis reports:", len(case["reports"]))
        if case["reports"]:
            st.json(case["reports"])
        with st.expander("Session audit history"):
            st.json(case["audit_events"])
        for filename, data in case_exports(case).items():
            st.download_button(f"Download case {filename}", data=data,
                               file_name=f"{selected}_{filename}",
                               mime="application/json" if filename.endswith("json") else "text/csv",
                               key=f"export_{selected}_{filename}")
    st.divider()
    st.subheader("Benchmark Review Policies")
    st.caption("Compare rules (score ≥30), anomaly detection, and combined review. Labels describe scenarios, not proven fraud.")
    with st.form("synthetic_benchmark"):
        size = st.number_input("Synthetic evaluation rows", min_value=1, max_value=10000, value=1000, step=1)
        seed = st.number_input("Evaluation seed", min_value=0, max_value=2147483647, value=2026, step=1)
        if st.form_submit_button("Run synthetic benchmark"):
            try:
                with st.spinner("Evaluating synthetic scenarios..."):
                    st.session_state["benchmark_result"] = evaluate(synthetic_dataset(int(size), int(seed)), model, seed=int(seed))
            except Exception:
                st.session_state.pop("benchmark_result", None)
                st.error("Benchmark could not be completed. Check inputs and model availability.")
    st.caption("Labeled CSV: amount,currency,country_mismatch,new_account,unusual_activity,is_fraud. USD only; flags and labels must be 0 or 1. Maximum 10 MB / 10,000 rows. Labels are unverified; no retraining occurs.")
    with st.form("import_benchmark", clear_on_submit=True):
        labeled = st.file_uploader("Labeled evaluation CSV", type=["csv"], key="labeled_csv")
        if st.form_submit_button("Evaluate labeled CSV"):
            try:
                if labeled is None:
                    raise ValueError("Choose a labeled CSV.")
                if labeled.size > MAX_UPLOAD_BYTES:
                    raise ValueError("CSV must be at most 10 MB.")
                data = labeled.getvalue()
                rows = parse_labeled_csv(data)
                st.session_state["benchmark_result"] = evaluate(rows, model, source="Imported labels (unverified)",
                                                                seed=None, raw_data=data)
                st.success("Labeled CSV evaluated.")
            except ValueError as error:
                st.session_state.pop("benchmark_result", None)
                st.error(str(error))
            except Exception:
                st.session_state.pop("benchmark_result", None)
                st.error("Benchmark could not be completed. Check inputs and model availability.")
    result = st.session_state.get("benchmark_result")
    if result:
        st.dataframe([{"policy": name, **metrics} for name, metrics in result["policies"].items()], use_container_width=True)
        st.json(result)
        st.caption("Undefined ratios are null when their denominator is zero; see undefined_metrics. " + result["limitations"])
        st.download_button("Download benchmark JSON", json_export(result), "benchmark.json", "application/json")
        st.download_button("Download benchmark CSV", benchmark_csv(result), "benchmark.csv", "text/csv")
