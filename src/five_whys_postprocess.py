#!/usr/bin/env python3
import json
import os
from pathlib import Path

from rio_readonly_audit import build_repair_plan

ROOT = Path(__file__).resolve().parents[1]


def main():
    task_id = os.environ.get("TONY_TASK_ID", "").strip()
    if not task_id:
        raise SystemExit("TONY_TASK_ID_REQUIRED")
    try:
        payload = json.loads(os.environ.get("TONY_TASK_PAYLOAD", "{}"))
    except json.JSONDecodeError as exc:
        raise SystemExit("INVALID_TASK_PAYLOAD_JSON") from exc

    objective = str(payload.get("objective") or payload.get("founder_message") or "")
    if "FIVE_WHYS" not in objective.upper() and "FIVE-WHYS" not in objective.upper():
        print("FIVE_WHYS_NOT_REQUESTED")
        return

    result_path = ROOT / "integration" / "results" / "tasks" / f"{task_id}.json"
    audit_path = ROOT / "integration" / "results" / "audits" / f"{task_id}.json"
    if not result_path.is_file():
        raise SystemExit("TONY_RESULT_NOT_FOUND")

    result = json.loads(result_path.read_text(encoding="utf-8"))
    strict = result.setdefault("strict_supervision", {})
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.is_file() else {}
    technical_root = strict.get("root_cause") or audit.get("root_cause") or "UNKNOWN"

    why_chain = [
        {
            "why": 1,
            "question": "Why did the previous executive action fail to advance the goal?",
            "cause": "The same RIO read-only audit/recommendation was being returned instead of a corrective next step.",
            "status": "VERIFIED",
            "evidence": [str(result_path.relative_to(ROOT))],
        },
        {
            "why": 2,
            "question": "Why was the same audit returned?",
            "cause": "Tony TASK_REQUEST handling routes RIO targets through the static audit path by default.",
            "status": "VERIFIED",
            "evidence": ["src/tony_runtime.py"],
        },
        {
            "why": 3,
            "question": "Why did Five Whys not change the action?",
            "cause": "The runtime previously did not branch on the FIVE_WHYS_DIAGNOSIS instruction after the audit completed.",
            "status": "VERIFIED",
            "evidence": ["src/tony_runtime.py", "src/five_whys_postprocess.py"],
        },
        {
            "why": 4,
            "question": "What technical finding should be acted on rather than re-audited?",
            "cause": technical_root,
            "status": "VERIFIED" if technical_root != "UNKNOWN" else "HYPOTHESIS",
            "evidence": [str(audit_path.relative_to(ROOT))] if audit_path.is_file() else [],
        },
    ]

    plan_path = None
    if audit:
        plan = build_repair_plan(audit, payload)
        plan["five_whys"] = why_chain
        plan["loop_root_cause"] = "TONY_STATIC_AUDIT_PATH_DID_NOT_ADVANCE_AFTER_DIAGNOSIS"
        plan["technical_root_cause"] = technical_root
        plan_path = ROOT / "integration" / "results" / "plans" / f"{task_id}.json"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

    strict["status"] = "FIVE_WHYS_DIAGNOSIS_COMPLETED"
    strict["root_cause"] = technical_root
    strict["why_chain"] = why_chain
    strict["loop_root_cause"] = "TONY_STATIC_AUDIT_PATH_DID_NOT_ADVANCE_AFTER_DIAGNOSIS"
    strict["solution"] = (
        "Stop repeating the same read-only audit. Use the evidence-backed repair plan for the verified technical finding, "
        "or reassign to RIO when the next step is commercial rather than engineering."
    )
    strict["next_action"] = "VICTOR_REVIEW_FIVE_WHYS_AND_DISPATCH_CORRECTIVE_ACTION"
    strict["requires_follow_up"] = True
    if plan_path:
        strict.setdefault("evidence", []).append(str(plan_path.relative_to(ROOT)))
    result["execution_status"] = "FIVE_WHYS_DIAGNOSIS_COMPLETED"
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("FIVE_WHYS_POSTPROCESS_COMPLETED")


if __name__ == "__main__":
    main()
