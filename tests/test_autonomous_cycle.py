import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import autonomous_cycle


class Response:
    def __init__(self, payload): self.payload = payload
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


if __name__ == "__main__": unittest.main()
