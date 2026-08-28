import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import openai_health


class Response:
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return json.dumps(self.payload).encode()


class OpenAIHealthTests(unittest.TestCase):
    def test_missing_key(self):
        self.assertEqual(openai_health.check("")["health"], "CREDENTIAL_MISSING")

    def test_authenticated_models(self):
        def opener(request, timeout):
            self.assertEqual(request.full_url, openai_health.ENDPOINT)
            self.assertEqual(request.headers["Authorization"], "Bearer test-key")
            self.assertEqual(timeout, 20)
            return Response({"data": [{"id": "model"}]})
        result = openai_health.check("test-key", opener)
        self.assertEqual(result["health"], "HEALTHY")
        self.assertTrue(result["authenticated"])


if __name__ == "__main__": unittest.main()
