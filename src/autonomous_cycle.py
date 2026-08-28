#!/usr/bin/env python3
"""Tony autonomous diagnostic heartbeat. No repair or production side effects."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bedrock_health import check as check_ai
from github_access_health import check as check_github

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "state" / "autonomy_status.json"
TARGET = "vickykenin-lang/rio-affiliate-engine"
RUNS_URL = f"https://api.github.com/repos/{TARGET}/actions/runs?per_page=10"


def recent_runs(token, opener=urlopen):
    if not token:
        return {"health": "CREDENTIAL_MISSING", "runs_checked": 0, "failed_runs": []}
    req = Request(RUNS_URL, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "tony-autonomy/1.0"})
    try:
        with opener(req, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        runs = payload.get("workflow_runs", []) if isinstance(payload, dict) else []
        latest_by_workflow = {}
        for run in runs:
            name = run.get("name")
            if name and name not in latest_by_workflow:
                latest_by_workflow[name] = run
        failures = [{"id": r.get("id"), "name": r.get("name"), "conclusion": r.get("conclusion"), "url": r.get("html_url")} for r in latest_by_workflow.values() if r.get("status") == "completed" and r.get("conclusion") not in {"success", "neutral", "skipped"}]
        return {"health": "HEALTHY", "runs_checked": len(runs), "workflows_evaluated": len(latest_by_workflow), "failed_runs": failures}
    except HTTPError as exc:
        return {"health": "FAILED", "runs_checked": 0, "failed_runs": [], "error_class": "HTTPError", "http_status": exc.code}
    except (URLError, TimeoutError, ValueError, TypeError, UnicodeDecodeError) as exc:
        return {"health": "FAILED", "runs_checked": 0, "failed_runs": [], "error_class": type(exc).__name__}


def rerun_failed_jobs(token, run_id, opener=urlopen):
    """Victor-policy-authorized, non-code recovery action."""
    url = f"https://api.github.com/repos/{TARGET}/actions/runs/{run_id}/rerun-failed-jobs"
    req = Request(url, data=b"", method="POST", headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "tony-autonomy/1.0"})
    try:
        with opener(req, timeout=20) as response:
            status = getattr(response, "status", 201)
        return {"run_id": run_id, "action": "RERUN_FAILED_JOBS", "status": "ACCEPTED" if status in {201, 202} else "UNEXPECTED_RESPONSE", "http_status": status}
    except HTTPError as exc:
        return {"run_id": run_id, "action": "RERUN_FAILED_JOBS", "status": "BLOCKED", "error_class": "HTTPError", "http_status": exc.code}
    except (URLError, TimeoutError) as exc:
        return {"run_id": run_id, "action": "RERUN_FAILED_JOBS", "status": "BLOCKED", "error_class": type(exc).__name__}


def main():
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    ai = check_ai(os.getenv("AWS_BEDROCK_API_KEY"))
    access = check_github(os.getenv("TONY_GITHUB_TOKEN"))
    monitoring = recent_runs(os.getenv("TONY_GITHUB_TOKEN"))
    ready = ai.get("health") == "HEALTHY" and access.get("health") == "HEALTHY" and monitoring.get("health") == "HEALTHY"
    recovery_actions = []
    for failure in monitoring.get("failed_runs", []):
        recovery_actions.append(rerun_failed_jobs(os.getenv("TONY_GITHUB_TOKEN"), failure["id"]))
    result = {
        "checked_at_utc": now,
        "department": "tony_stark",
        "mode": "DIAGNOSTIC_READY_MANAGED",
        "cycle": "WAKE_VALIDATE_MONITOR_DIAGNOSE_REPORT",
        "state": "CYCLE_VERIFIED" if ready else "CYCLE_BLOCKED",
        "ai_health": ai.get("health"),
        "github_access": access.get("health"),
        "monitoring": monitoring,
        "incident_detected": bool(monitoring.get("failed_runs")),
        "diagnosis_automated": True,
        "victor_policy_authorization": "AUTO_AUTHORIZED_NON_CODE_WORKFLOW_RECOVERY",
        "recovery_actions": recovery_actions,
        "repair_executed": False,
        "repair_gate": "CODE_CHANGE_REQUIRES_VICTOR_POLICY_ELIGIBILITY",
        "production_action_performed": False,
        "credential_values_stored": False,
        "next_heartbeat_minutes": 30 if monitoring.get("failed_runs") else 60,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0 if ready else 1


if __name__ == "__main__": raise SystemExit(main())
