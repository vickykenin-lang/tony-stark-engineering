#!/usr/bin/env python3
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {"STATUS_CHECK", "HEALTH_CHECK", "DIAGNOSTIC", "REPAIR_PLAN", "POST_REPAIR_VERIFY"}
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
    now = datetime.now(timezone.utc).isoformat()
    out = ROOT / "integration" / "results" / "tasks" / f"{task_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    strict = {
        "status": "SAFE_STOP" if errors else "ONBOARDING_STRICT",
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
    if task_type == "DIAGNOSTIC":
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
        "strict_supervision": strict,
        "payload": payload,
    }
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if errors:
        raise SystemExit("CONSTITUTIONAL_VALIDATION_FAILED")

if __name__ == "__main__":
    main()
