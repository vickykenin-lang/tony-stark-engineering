#!/usr/bin/env python3
"""Safe AWS Bedrock Mantle credential/model health check for Tony Stark."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ENDPOINT = "https://bedrock-mantle.us-east-1.api.aws/v1/models"
MODEL_CANDIDATES = ["qwen.qwen3-coder-next", "zai.glm-4.7-flash"]
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "state" / "ai_runtime_status.json"


def check(api_key, opener=urlopen):
    if not api_key:
        return {"health": "CREDENTIAL_MISSING", "credential_status": "MISSING", "paid_inference_call": False}
    request = Request(ENDPOINT, headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json", "User-Agent": "tony-runtime/1.0"})
    try:
        with opener(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        raw = payload.get("data", []) if isinstance(payload, dict) else []
        available = [item.get("id") if isinstance(item, dict) else item for item in raw]
        available = [item for item in available if isinstance(item, str)]
        selected = next((model for model in MODEL_CANDIDATES if model in available), None)
        if not selected:
            return {"health": "FAILED", "credential_status": "SET", "error_class": "DeclaredModelsUnavailable", "available_model_count": len(available), "paid_inference_call": False}
        return {"health": "HEALTHY", "credential_status": "SET", "selected_model": selected, "available_declared_models": [m for m in MODEL_CANDIDATES if m in available], "paid_inference_call": False}
    except HTTPError as exc:
        return {"health": "FAILED", "credential_status": "SET", "error_class": "HTTPError", "http_status": exc.code, "paid_inference_call": False}
    except (URLError, TimeoutError) as exc:
        return {"health": "FAILED", "credential_status": "SET", "error_class": type(exc).__name__, "paid_inference_call": False}
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        return {"health": "FAILED", "credential_status": "SET", "error_class": type(exc).__name__, "paid_inference_call": False}


def main():
    health = check(os.getenv("AWS_BEDROCK_API_KEY"))
    result = {"checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "department": "tony_stark", "provider": "BEDROCK_MANTLE", "provider_health": health, "credential_value_stored": False, "ai_ready": health["health"] == "HEALTHY"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0 if result["ai_ready"] else 1


if __name__ == "__main__": raise SystemExit(main())
