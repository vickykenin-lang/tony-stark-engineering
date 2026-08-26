import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class TonyRuntimeTests(unittest.TestCase):
    def test_constitutional_files_are_present_and_valid(self):
        required = ["OBJECTIVE.md", "SOUL.md", "config/authority.json", "state/current_state.json", "integration/victor_contract.json"]
        for path in required:
            self.assertTrue((ROOT / path).is_file(), path)
        authority = json.loads((ROOT / "config/authority.json").read_text())
        state = json.loads((ROOT / "state/current_state.json").read_text())
        self.assertEqual(authority["default"], "PROHIBITED_UNLESS_EXPLICITLY_LISTED")
        self.assertEqual(state["business_execution"], "BLOCKED_PENDING_CERTIFICATION")

    def test_status_check_returns_strict_revert(self):
        task_id = "test-strict-roundtrip"
        env = os.environ.copy()
        env.update({"TONY_TASK_ID": task_id, "TONY_TASK_TYPE": "STATUS_CHECK", "TONY_TASK_PAYLOAD": "{}"})
        result = subprocess.run(["python", "src/tony_runtime.py"], cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads((ROOT / f"integration/results/tasks/{task_id}.json").read_text())
        self.assertEqual(data["sender"], "tony_stark")
        self.assertEqual(data["recipient"], "victor")
        self.assertTrue(data["strict_supervision"]["revert_to_victor"])
        self.assertTrue(data["strict_supervision"]["evidence"])
        (ROOT / f"integration/results/tasks/{task_id}.json").unlink()

if __name__ == "__main__":
    unittest.main()
