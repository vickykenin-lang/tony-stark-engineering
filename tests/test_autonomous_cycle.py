import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import autonomous_cycle


class Response:
    def __init__(self, payload, status=200): self.payload = payload; self.status = status
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return json.dumps(self.payload).encode()


class AutonomousCycleTests(unittest.TestCase):
    def test_missing_token_blocks_monitor(self):
        self.assertEqual(autonomous_cycle.recent_runs("")["health"], "CREDENTIAL_MISSING")

    def test_failures_are_detected(self):
        payload = {"workflow_runs": [{"id": 1, "name": "test", "status": "completed", "conclusion": "failure", "html_url": "https://example.invalid"}]}
        result = autonomous_cycle.recent_runs("token", lambda req, timeout: Response(payload))
        self.assertEqual(result["health"], "HEALTHY")
        self.assertEqual(len(result["failed_runs"]), 1)

    def test_newer_success_resolves_old_failure(self):
        payload = {"workflow_runs": [
            {"id": 2, "name": "RIO", "status": "completed", "conclusion": "success"},
            {"id": 1, "name": "RIO", "status": "completed", "conclusion": "failure"},
        ]}
        result = autonomous_cycle.recent_runs("token", lambda req, timeout: Response(payload))
        self.assertEqual(result["failed_runs"], [])

    def test_failed_jobs_rerun(self):
        result = autonomous_cycle.rerun_failed_jobs("token", 42, lambda req, timeout: Response({}, 201))
        self.assertEqual(result["status"], "ACCEPTED")


if __name__ == "__main__": unittest.main()
