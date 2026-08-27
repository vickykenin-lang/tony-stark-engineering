import tempfile
import unittest
from pathlib import Path
from src.rio_readonly_audit import audit_repository

class RioReadonlyAuditTests(unittest.TestCase):
    def test_reports_static_findings_without_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "README.md").write_text("# RIO\nTODO add tests\n", encoding="utf-8")
            before = (root / "README.md").read_text()
            result = audit_repository(root, "task-audit-1")
            self.assertEqual(result["audit_mode"], "L0_READ_ONLY_STATIC")
            self.assertFalse(result["repository_change_performed"])
            self.assertFalse(result["code_execution_performed"])
            self.assertEqual((root / "README.md").read_text(), before)
            self.assertIn("NO_TEST_FILES_DETECTED", [x["code"] for x in result["findings"]])

if __name__ == "__main__":
    unittest.main()
