import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import github_access_health


class Response:
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return json.dumps(self.payload).encode()


class GitHubAccessTests(unittest.TestCase):
    def test_missing_token(self):
        self.assertEqual(github_access_health.check("")["health"], "CREDENTIAL_MISSING")

    def test_push_access(self):
        result = github_access_health.check("token", lambda req, timeout: Response({"permissions": {"pull": True, "push": True}}))
        self.assertEqual(result["health"], "HEALTHY")
        self.assertTrue(result["push"])

    def test_read_only_is_not_repair_ready(self):
        result = github_access_health.check("token", lambda req, timeout: Response({"permissions": {"pull": True, "push": False}}))
        self.assertEqual(result["health"], "READ_ONLY")


if __name__ == "__main__": unittest.main()
