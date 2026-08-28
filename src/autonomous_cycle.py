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
        failures = [{"id": r.get("id"), "name": r.get("name"), "conclusion": r.get("conclusion"), "url": r.get("html_url")} for r in runs if r.get("status") == "completed" and r.get("conclusion") not in {"success", "neutral", "skipped"}]
        return {"health": "HEALTHY", "runs_checked": len(runs), "failed_runs": failures}
    except HTTPError as exc:
        return {"health": "FAILED", "runs_checked": 0, "failed_runs": [], "error_class": "HTTPError", "http_status": exc.code}
    except (URLError, TimeoutError, ValueError, TypeError, UnicodeDecodeError) as exc:
        return {"health": "FAILED", "runs_checked": 0, "failed_runs": [], "error_class": type(exc).__name__}


def main():
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    ai = check_ai(os.getenv("AWS_BEDROCK_API_KEY"))
    access = check_github(os.getenv("TONY_GITHUB_TOKEN"))
    monitoring = recent_runs(os.getenv("TONY_GITHUB_TOKEN"))
    ready = ai.get("health") == "HEALTHY" and access.get("health") == "HEALTHY" and monitoring.get("health") == "HEALTHY"
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
        "repair_executed": False,
        "repair_gate": "VICTOR_AUTHORIZATION_REQUIRED",
        "production_action_performed": False,
        "credential_values_stored": False,
        "next_heartbeat_minutes": 30 if monitoring.get("failed_runs") else 60,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0 if ready else 1


if __name__ == "__main__": raise SystemExit(main())
