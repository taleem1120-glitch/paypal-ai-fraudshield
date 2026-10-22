"""Session-only investigation records and portable reports. No evidence bytes retained."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4
import csv
import io
import json
import math
import platform
from importlib.metadata import version

from scoring import FEATURE_ORDER, rule_details, score_transaction, risk_decision
from audit import METADATA, append_event, content_hash, verify_case
from transactions import money, transaction_record

SCHEMA_VERSION = "1.1"
SCORING_VERSION = "rules-v1-validated"
MODEL_VERSION = "isolation-forest-v1-seed42"
STATUSES = ("Open", "In review", "Closed")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
LIMITATIONS = (
    "Illustrative risk scores are not fraud probabilities or findings. "
    "Isolation Forest detects anomalies relative to synthetic training data. "
    "Manual indicators and source assertions are unverified. Human review is required; "
    "do not use for enforcement or real payment decisions. Session-only records are "
    "not a durable audit ledger. SHA-256 verifies byte consistency, not authenticity "
    "or legal chain of custody. Session audit hashes are unsigned and can be recomputed; "
    "they do not authenticate an investigator or prevent wholesale rewriting."
)


def runtime_versions():
    return {"python": platform.python_version(), "scikit_learn": version("scikit-learn"),
            "numpy": version("numpy")}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def _required(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required.")
    return value.strip()


def new_case(title, investigator_reference, notes=""):
    if not isinstance(notes, str):
        raise ValueError("Case notes must be text.")
    now = utc_now()
    case = {"schema_version": SCHEMA_VERSION, "case_id": str(uuid4()),
            "title": _required(title, "Case title"),
            "investigator_reference": _required(investigator_reference, "Investigator reference"),
            "notes": notes, "status": "Open", "created_at": now, "updated_at": now,
            "evidence": [], "reports": [], "audit_events": []}
    append_event(case, "case_created", {"metadata": {key: case[key] for key in METADATA}})
    return case


def _ensure_integrity(case):
    if not verify_case(case):
        raise ValueError("Case consistency check failed. Export and review the record before further changes.")


def update_case(case, title, investigator_reference, notes, status):
    _ensure_integrity(case)
    if status not in STATUSES:
        raise ValueError("Invalid case status.")
    if not isinstance(notes, str):
        raise ValueError("Case notes must be text.")
    title = _required(title, "Case title")
    investigator_reference = _required(investigator_reference, "Investigator reference")
    case.update(title=title, investigator_reference=investigator_reference,
                notes=notes, status=status)
    append_event(case, "case_updated", {"metadata": {key: case[key] for key in METADATA}})


def evidence_record(data, filename, source_reference, collected_at, description=""):
    if not isinstance(data, bytes) or len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("Evidence must be bytes and at most 10 MB.")
    if not isinstance(description, str):
        raise ValueError("Evidence description must be text.")
    try:
        parsed = datetime.fromisoformat(collected_at.replace("Z", "+00:00"))
        if parsed.utcoffset() is None:
            raise ValueError
        collected_utc = parsed.astimezone(timezone.utc).isoformat()
    except (AttributeError, TypeError, ValueError, OverflowError):
        raise ValueError("Collection timestamp must be ISO 8601 with a timezone.") from None
    return {"evidence_id": str(uuid4()), "filename": _required(filename, "Filename"),
            "byte_count": len(data), "sha256": sha256(data).hexdigest(),
            "source_reference": _required(source_reference, "Source reference"),
            "source_type": "Uploaded file (user assertion)",
            "collected_at": collected_utc,
            "recorded_at": utc_now(), "description": description}


def verify_evidence(evidence, data):
    return sha256(data).hexdigest() == evidence["sha256"]


def add_evidence(case, record):
    _ensure_integrity(case)
    if any(item["evidence_id"] == record["evidence_id"] for item in case["evidence"]):
        raise ValueError("This evidence record is already attached.")
    case["evidence"].append(deepcopy(record))
    append_event(case, "evidence_added", {"evidence": record})


def record_evidence_verification(case, evidence_id, data):
    _ensure_integrity(case)
    if not isinstance(data, bytes) or len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("Verification file must be bytes and at most 10 MB.")
    record = next((item for item in case["evidence"] if item["evidence_id"] == evidence_id), None)
    if record is None:
        raise ValueError("Evidence ID is not present in this case.")
    matched = verify_evidence(record, data)
    append_event(case, "evidence_verified", {"evidence_id": evidence_id,
                 "observed_sha256": sha256(data).hexdigest(), "expected_sha256": record["sha256"],
                 "matched": matched})
    return matched


def build_report(model, amount, currency, country_mismatch=False, new_account=False,
                 unusual_activity=False, snapshot=None, *, source_type="Manual"):
    if source_type not in {"Manual", "Synthetic"}:
        raise ValueError("Invalid source type.")
    flags = (country_mismatch, new_account, unusual_activity)
    if any(type(flag) is not bool for flag in flags):
        raise ValueError("Risk indicators must be booleans.")
    score, _, anomaly, decision = score_transaction(model, amount, currency, *flags)
    if not math.isfinite(decision):
        raise ValueError("Invalid model decision score.")
    provenance = transaction_record(amount, currency, snapshot)
    if provenance["Source"] == "Manual" and source_type == "Synthetic":
        provenance["Source"] = "Synthetic"
    level, action = risk_decision(score, anomaly)
    sources = {"amount": provenance["Source"], "currency": provenance["Source"],
               **{key: "Synthetic" if provenance["Source"] == "Synthetic" else "Manual (unverified)"
                  for key in FEATURE_ORDER[1:]}}
    details = [{**detail, "input_source": sources[detail["input"]]}
               for detail in rule_details(amount, currency, *flags)]
    alerts = [{"alert_id": detail["rule_id"], "source": detail["input_source"],
               "explanation": detail["reason"], "rule_contribution": detail["contribution"]}
              for detail in details if detail["active"]]
    if anomaly:
        alerts.append({"alert_id": "synthetic_model_anomaly", "source": "Isolation Forest (synthetic training)",
                       "explanation": "Model predicts -1: unusual relative to synthetic training data. "
                                      "This is not feature-level attribution or a finding of fraud.",
                       "rule_contribution": None})
    return {"schema_version": SCHEMA_VERSION, "report_id": str(uuid4()), "case_id": None,
            "created_at": provenance["Analyzed At"], "scoring_version": SCORING_VERSION,
            "model_version": MODEL_VERSION, "runtime_versions": runtime_versions(),
            "inputs": {"amount": str(money(amount)), "currency": currency,
                       "country_mismatch": country_mismatch, "new_account": new_account,
                       "unusual_activity": unusual_activity},
            "provenance": provenance,
            "input_sources": sources, "transaction_id": provenance["Transaction ID"],
            "rule_breakdown": details,
            "triggered_rules": [detail for detail in details if detail["active"]],
            "alerts": alerts,
            "decision_basis": "rule score >= 60" if score >= 60 else "model anomaly" if anomaly
                              else "rule score >= 30" if score >= 30 else "no review threshold triggered",
            "model_context": {"training_data": "Synthetic only", "training_seed": 42,
                              "feature_order": list(FEATURE_ORDER), "training_rows": 3000,
                              "n_estimators": 150, "contamination": 0.08,
                              "anomaly_condition": "model.predict returns -1",
                              "feature_level_attribution_available": False},
            "evidence_references": [],
            "evidence_relationship": "Case association only; files do not verify manually entered risk flags.",
            "rule_score": score, "is_anomaly": anomaly, "anomaly_decision_score": decision,
            "risk_level": level, "recommended_action": action, "limitations": LIMITATIONS}


def attach_report(case, report):
    _ensure_integrity(case)
    if any(item["report_id"] == report["report_id"] for item in case["reports"]):
        raise ValueError("This report is already attached to the case.")
    saved = deepcopy(report)
    saved["case_id"] = case["case_id"]
    saved["evidence_references"] = [{"evidence_id": item["evidence_id"], "sha256": item["sha256"]}
                                    for item in case["evidence"]]
    case["reports"].append(saved)
    append_event(case, "report_attached", {"report_id": saved["report_id"], "report_sha256": content_hash(saved)})


def json_export(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")


def _csv_cell(value):
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True)
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def csv_export(rows, fieldnames=None):
    rows = list(rows)
    fieldnames = fieldnames or list(dict.fromkeys(key for row in rows for key in row))
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows({key: _csv_cell(value) for key, value in row.items()} for row in rows)
    return out.getvalue().encode("utf-8")


def case_exports(case):
    summary = {key: value for key, value in case.items() if key not in {"evidence", "reports", "audit_events"}}
    return {"case.json": json_export({**case, "consistency_check_passed": verify_case(case), "limitations": LIMITATIONS}),
            "summary.csv": csv_export([{**summary, "consistency_check_passed": verify_case(case)}]),
            "audit.csv": csv_export(case["audit_events"],
                                    ["event_id", "sequence", "case_id", "event_type", "recorded_at",
                                     "actor_reference", "actor_verified", "payload", "previous_sha256", "sha256"]),
            "evidence.csv": csv_export([{"case_id": case["case_id"], **item} for item in case["evidence"]],
                                       ["case_id", "evidence_id", "filename", "byte_count", "sha256",
                                        "source_reference", "source_type", "collected_at", "recorded_at", "description"]),
            "reports.csv": csv_export(case["reports"],
                                      ["schema_version", "report_id", "case_id", "created_at",
                                       "scoring_version", "model_version", "runtime_versions", "inputs", "provenance", "input_sources",
                                       "triggered_rules", "transaction_id", "rule_breakdown", "alerts", "decision_basis",
                                       "model_context", "evidence_references", "evidence_relationship",
                                       "rule_score", "is_anomaly", "anomaly_decision_score",
                                       "risk_level", "recommended_action", "limitations"])}
