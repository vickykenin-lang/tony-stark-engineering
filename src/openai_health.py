#!/usr/bin/env python3
"""Safe OpenAI credential health check for Tony Stark."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ENDPOINT = "https://api.openai.com/v1/models"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "state" / "ai_runtime_status.json"


def check(api_key, opener=urlopen):
    if not api_key:
        return {"health": "CREDENTIAL_MISSING", "authenticated": False}
    request = Request(ENDPOINT, headers={"Authorization": f"Bearer {api_key}"})
    try:
        with opener(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        models = payload.get("data") if isinstance(payload, dict) else None
        return {
            "health": "HEALTHY" if isinstance(models, list) else "INVALID_RESPONSE",
            "authenticated": isinstance(models, list),
            "model_count": len(models) if isinstance(models, list) else 0,
        }
    except HTTPError as exc:
        return {"health": "FAILED", "authenticated": False, "error_class": "HTTPError", "http_status": exc.code}
    except (URLError, TimeoutError) as exc:
        return {"health": "FAILED", "authenticated": False, "error_class": type(exc).__name__}
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        return {"health": "FAILED", "authenticated": False, "error_class": type(exc).__name__}


def main():
    health = check(os.getenv("OPENAI_API_KEY"))
    result = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "department": "tony_stark",
        "provider": "OPENAI",
        "provider_health": health,
        "credential_value_stored": False,
        "ai_ready": health["health"] == "HEALTHY",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0 if result["ai_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
