#!/usr/bin/env python3
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from rio_readonly_audit import audit_repository, build_repair_plan

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {"STATUS_CHECK", "HEALTH_CHECK", "DIAGNOSTIC", "REPAIR_PLAN", "POST_REPAIR_VERIFY", "TASK_REQUEST"}
MANDATORY_TASK_PROHIBITIONS = {"EXPOSE_OR_ROTATE_SECRETS", "PAID_ACTION", "DESTRUCTIVE_ACTION", "PRODUCTION_DEPLOYMENT", "LOCKED_OBJECTIVE_OR_AUTHORITY_CHANGE"}
REQUIRED = [
    ROOT / "OBJECTIVE.md",
    ROOT / "SOUL.md",
    ROOT / "config" / "authority.json",
    ROOT / "state" / "current_state.json",
    ROOT / "integration" / "victor_contract.json",
]

def load_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)

def validate_constitution():
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED if not path.is_file() or not path.read_text(encoding="utf-8").strip()]
    errors = []
    if missing:
        errors.append("MISSING:" + ",".join(missing))
        return errors
    authority = load_json(ROOT / "config" / "authority.json")
    state = load_json(ROOT / "state" / "current_state.json")
    contract = load_json(ROOT / "integration" / "victor_contract.json")
    if authority.get("default") != "PROHIBITED_UNLESS_EXPLICITLY_LISTED":
        errors.append("AUTHORITY_DEFAULT_NOT_FAIL_CLOSED")
    if state.get("department") != "tony_stark":
        errors.append("STATE_IDENTITY_MISMATCH")
    if state.get("business_execution") != "BLOCKED_PENDING_CERTIFICATION":
        errors.append("BUSINESS_EXECUTION_GATE_OPEN")
    if contract.get("reports_to") != "victor" or contract.get("supervision_mode") != "STRICT":
        errors.append("VICTOR_CONTRACT_INVALID")
    return errors

def safe_task_id(value):
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")[:120]
    if not cleaned or cleaned != value:
        raise SystemExit("INVALID_TASK_ID")
    return cleaned

def validate_task_request(payload):
    errors = []
    if payload.get("schema_version") != 1:
        errors.append("TASK_SCHEMA_INVALID")
    if not isinstance(payload.get("objective"), str) or not payload["objective"].strip():
        errors.append("TASK_OBJECTIVE_REQUIRED")
    target = payload.get("target_repository")
    if not isinstance(target, str) or not re.fullmatch(r"vickykenin-lang/[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9_-])?", target):
        errors.append("TARGET_REPOSITORY_REQUIRED_OR_INVALID")
    actions = payload.get("requested_actions")
    if not isinstance(actions, list) or not actions:
        errors.append("REQUESTED_ACTIONS_REQUIRED")
    authority = payload.get("authority")
    if not isinstance(authority, dict) or authority.get("supervision_mode") != "STRICT":
        errors.append("STRICT_AUTHORITY_REQUIRED")
    elif authority.get("maximum_level") not in {"L0", "L1", "L2"}:
        errors.append("AUTHORITY_LEVEL_INVALID")
    elif authority.get("production_activation_authorized") is not False:
        errors.append("PRODUCTION_GATE_MUST_REMAIN_CLOSED")
    prohibited = payload.get("prohibited_actions")
    if not isinstance(prohibited, list) or not MANDATORY_TASK_PROHIBITIONS.issubset(set(prohibited)):
        errors.append("MANDATORY_PROHIBITIONS_MISSING")
    evidence = payload.get("evidence_requirements")
    if not isinstance(evidence, list) or not {"TASK_RESULT_ENVELOPE", "TEST_RESULTS", "BLOCKERS"}.issubset(set(evidence)):
        errors.append("EVIDENCE_REQUIREMENTS_INCOMPLETE")
    return errors

def main():
    task_id = safe_task_id(os.getenv("TONY_TASK_ID", "").strip())
    task_type = os.getenv("TONY_TASK_TYPE", "").strip().upper()
    if task_type not in ALLOWED:
        raise SystemExit("INVALID_OR_UNAUTHORIZED_TASK_TYPE")
    try:
        payload = json.loads(os.getenv("TONY_TASK_PAYLOAD", "{}"))
    except json.JSONDecodeError:
        raise SystemExit("INVALID_TASK_PAYLOAD_JSON")
    if not isinstance(payload, dict):
        raise SystemExit("TASK_PAYLOAD_MUST_BE_OBJECT")

    errors = validate_constitution()
    if task_type == "TASK_REQUEST":
        errors.extend(validate_task_request(payload))
    now = datetime.now(timezone.utc).isoformat()
    out = ROOT / "integration" / "results" / "tasks" / f"{task_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    strict = {
        "status": "SAFE_STOP" if errors else ("TASK_ACCEPTED_GOVERNED" if task_type == "TASK_REQUEST" else "ONBOARDING_STRICT"),
        "objective_alignment": "BLOCKED_CONSTITUTION_INVALID" if errors else "CHECKED_AGAINST_LOCKED_OBJECTIVE",
        "error_or_blocker": ";".join(errors) if errors else None,
        "root_cause": "CONSTITUTIONAL_VALIDATION_FAILED" if errors else None,
        "solution": "Restore and validate mandatory constitutional binding." if errors else "No repair is executed unless evidence and authority permit it.",
        "next_action": "VICTOR_REVIEW_AND_PUSH_NEXT_ACTION",
        "evidence": [str(out.relative_to(ROOT)), "OBJECTIVE.md", "SOUL.md", "config/authority.json", "state/current_state.json"],
        "revert_to_victor": True,
        "requires_follow_up": True,
    }

    execution_status = "COMPLETED_DIAGNOSTIC"
    if task_type == "TASK_REQUEST":
        strict["evidence"].extend(["integration/victor_contract.json", "config/authority.json"])
        if not errors:
            execution_status = "ACCEPTED_PENDING_EXECUTION_EVIDENCE"
            strict["solution"] = "Governed task envelope accepted. Only authorized repository work may proceed; production, secrets, paid and destructive actions remain blocked."
            target_path = os.getenv("TONY_TARGET_REPO_PATH", "").strip()
            if payload.get("target_repository") == "vickykenin-lang/rio-affiliate-engine" and target_path:
                audit = audit_repository(Path(target_path), task_id)
                audit_out = ROOT / "integration" / "results" / "audits" / f"{task_id}.json"
                audit_out.parent.mkdir(parents=True, exist_ok=True)
                audit_out.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
                execution_status = "COMPLETED_READ_ONLY_AUDIT"
                strict["status"] = "READ_ONLY_AUDIT_COMPLETED"
                strict["root_cause"] = audit["root_cause"]
                strict["solution"] = audit["summary"]
                strict["next_action"] = "VICTOR_REVIEW_AUDIT_AND_AUTHORIZE_REPAIR_PLAN"
                strict["evidence"].extend([str(audit_out.relative_to(ROOT))] + audit["evidence_files"][:12])
                if payload.get("authority", {}).get("maximum_level") == "L1" and re.search(r"repair[ _-]?plan", payload.get("objective", ""), re.I):
                    plan = build_repair_plan(audit, payload)
                    plan_out = ROOT / "integration" / "results" / "plans" / f"{task_id}.json"
                    plan_out.parent.mkdir(parents=True, exist_ok=True)
                    plan_out.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
                    execution_status = "REPAIR_PLAN_READY"
                    strict["status"] = "REPAIR_PLAN_READY"
                    strict["solution"] = f"Governed RIO workflow repair plan prepared with {len(plan['recommended_changes'])} evidence-based changes. No repository change was executed."
                    strict["next_action"] = "VICTOR_REVIEW_PLAN_AND_REQUEST_FOUNDER_IMPLEMENTATION_APPROVAL"
                    strict["evidence"].append(str(plan_out.relative_to(ROOT)))
    elif task_type == "DIAGNOSTIC":
        strict["error_or_blocker"] = strict["error_or_blocker"] or payload.get("error_or_blocker") or "DIAGNOSTIC_INPUT_REQUIRED"
        strict["root_cause"] = strict["root_cause"] or "PENDING_EVIDENCE_BASED_ROOT_CAUSE_ANALYSIS"
        strict["solution"] = "Collect relevant logs/config/runtime evidence, isolate root cause, then propose the least-risk authorized repair."
    elif task_type == "REPAIR_PLAN":
        execution_status = "REPAIR_PLAN_READY"
        strict["solution"] = "Prepare governed repair plan only; execution authority must be evaluated separately."
    elif task_type == "POST_REPAIR_VERIFY":
        execution_status = "VERIFICATION_PENDING_EVIDENCE"
        strict["solution"] = "Run relevant tests and evidence checks; do not close without verified recovery."

    result = {
        "schema_version": 1,
        "message_type": "TASK_RESULT",
        "sender": "tony_stark",
        "recipient": "victor",
        "task_id": task_id,
        "task_type": task_type,
        "observed_at": now,
        "execution_status": "SAFE_STOP" if errors else execution_status,
        "repair_executed": False,
        "destructive_action_performed": False,
        "paid_action_performed": False,
        "production_action_performed": False,
        "strict_supervision": strict,
        "task_request": payload if task_type == "TASK_REQUEST" else None,
        "payload": payload,
    }
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if errors:
        raise SystemExit("CONSTITUTIONAL_VALIDATION_FAILED")

if __name__ == "__main__":
    main()
