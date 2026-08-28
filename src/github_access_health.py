#!/usr/bin/env python3
"""Safe GitHub target-repository permission probe for Tony Stark."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

TARGET = "vickykenin-lang/rio-affiliate-engine"
ENDPOINT = f"https://api.github.com/repos/{TARGET}"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "state" / "github_access_status.json"


def check(token, opener=urlopen):
    if not token:
        return {"health": "CREDENTIAL_MISSING", "target": TARGET, "read": False, "push": False}
    req = Request(ENDPOINT, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "tony-runtime/1.0"})
    try:
        with opener(req, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        permissions = payload.get("permissions", {}) if isinstance(payload, dict) else {}
        push = permissions.get("push") is True
        return {"health": "HEALTHY" if push else "READ_ONLY", "target": TARGET, "read": True, "push": push}
    except HTTPError as exc:
        return {"health": "FAILED", "target": TARGET, "read": False, "push": False, "error_class": "HTTPError", "http_status": exc.code}
    except (URLError, TimeoutError, ValueError, TypeError, UnicodeDecodeError) as exc:
        return {"health": "FAILED", "target": TARGET, "read": False, "push": False, "error_class": type(exc).__name__}


def main():
    access = check(os.getenv("TONY_GITHUB_TOKEN"))
    result = {"checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "department": "tony_stark", "access": access, "credential_value_stored": False, "cross_repo_repair_ready": access["health"] == "HEALTHY"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0 if result["cross_repo_repair_ready"] else 1


if __name__ == "__main__": raise SystemExit(main())
