import tempfile
import unittest
from pathlib import Path
from src.rio_readonly_audit import audit_repository, build_repair_plan

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

    def test_builds_plan_without_modifying_repository(self):
        audit = {"task_id": "plan-1", "target_repository": "vickykenin-lang/rio-affiliate-engine"}
        payload = {"objective": "workflow governance REPAIR_PLAN", "prohibited_actions": ["PRODUCTION_DEPLOYMENT"]}
        plan = build_repair_plan(audit, payload)
        self.assertEqual(plan["plan_mode"], "L1_GOVERNED_PLAN_ONLY")
        self.assertTrue(plan["recommended_changes"])
        self.assertFalse(plan["repository_change_performed"])
        self.assertTrue(plan["requires_founder_approval_for_implementation"])

if __name__ == "__main__":
    unittest.main()
