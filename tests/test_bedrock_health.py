import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import bedrock_health


class Response:
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return json.dumps(self.payload).encode()


class BedrockHealthTests(unittest.TestCase):
    def test_missing_key(self):
        self.assertEqual(bedrock_health.check("")["health"], "CREDENTIAL_MISSING")

    def test_declared_model_selected(self):
        def opener(request, timeout):
            self.assertEqual(request.full_url, bedrock_health.ENDPOINT)
            self.assertEqual(request.headers["Authorization"], "Bearer test-key")
            self.assertEqual(timeout, 30)
            return Response({"data": [{"id": "qwen.qwen3-coder-next"}]})
        result = bedrock_health.check("test-key", opener)
        self.assertEqual(result["health"], "HEALTHY")
        self.assertEqual(result["selected_model"], "qwen.qwen3-coder-next")


if __name__ == "__main__": unittest.main()
