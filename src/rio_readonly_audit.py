#!/usr/bin/env python3
import json
import re
from collections import Counter
from pathlib import Path

TEXT_EXTENSIONS = {".md", ".py", ".js", ".mjs", ".ts", ".tsx", ".json", ".yml", ".yaml", ".toml"}
SKIP_PARTS = {".git", "node_modules", "vendor", "__pycache__"}

def audit_repository(root: Path, task_id: str):
    root = root.resolve()
    files = [p for p in root.rglob("*") if p.is_file() and not any(part in SKIP_PARTS for part in p.parts)]
    relative = [p.relative_to(root).as_posix() for p in files]
    extensions = Counter((p.suffix.lower() or "<none>") for p in files)
    workflows = sorted(p for p in relative if p.startswith(".github/workflows/") and p.endswith((".yml", ".yaml")))
    test_files = sorted(p for p in relative if re.search(r"(^|/)(test[^/]*|tests?)(/|\.|$)", p, re.I))
    markers = []
    write_workflows = []
    for path in files:
        if path.suffix.lower() not in TEXT_EXTENSIONS or path.stat().st_size > 500_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = path.relative_to(root).as_posix()
        count = len(re.findall(r"\b(?:TODO|FIXME|XXX)\b", text, re.I))
        if count:
            markers.append({"path": rel, "count": count})
        if rel in workflows and re.search(r"contents\s*:\s*write|permissions\s*:\s*write-all", text, re.I):
            write_workflows.append(rel)
    findings = []
    if not files:
        findings.append({"severity": "BLOCKER", "code": "TARGET_EMPTY", "detail": "No auditable repository files found."})
    if not workflows:
        findings.append({"severity": "MEDIUM", "code": "NO_GITHUB_WORKFLOWS", "detail": "No GitHub workflow files found."})
    if not test_files:
        findings.append({"severity": "HIGH", "code": "NO_TEST_FILES_DETECTED", "detail": "No test files detected by static inventory."})
    if markers:
        findings.append({"severity": "MEDIUM", "code": "UNRESOLVED_MARKERS", "detail": f"{sum(x['count'] for x in markers)} TODO/FIXME/XXX markers detected."})
    if write_workflows:
        findings.append({"severity": "REVIEW", "code": "WRITE_ENABLED_WORKFLOWS", "detail": f"{len(write_workflows)} workflow(s) request contents write; authority review required."})
    if not findings:
        findings.append({"severity": "INFO", "code": "NO_STATIC_BLOCKER_DETECTED", "detail": "Static L0 audit found no immediate structural blocker; runtime tests remain a separate gate."})
    highest = next((x for x in findings if x["severity"] in {"BLOCKER", "HIGH"}), findings[0])
    return {
        "schema_version": 1,
        "task_id": task_id,
        "audit_mode": "L0_READ_ONLY_STATIC",
        "target_repository": "vickykenin-lang/rio-affiliate-engine",
        "file_count": len(files),
        "extension_counts": dict(sorted(extensions.items())),
        "workflow_files": workflows,
        "test_files_detected": test_files[:50],
        "unresolved_markers": markers[:50],
        "write_enabled_workflows": write_workflows,
        "findings": findings,
        "root_cause": highest["code"],
        "summary": f"RIO read-only static audit completed: {len(findings)} finding(s), {len(files)} files inspected. No repository file was changed and no code was executed.",
        "evidence_files": (["README.md"] if "README.md" in relative else []) + workflows[:10] + test_files[:10],
        "repository_change_performed": False,
        "code_execution_performed": False,
        "secret_access_performed": False,
        "production_action_performed": False,
    }

def build_repair_plan(audit, payload):
    return {
        "schema_version": 1,
        "task_id": audit["task_id"],
        "plan_mode": "L1_GOVERNED_PLAN_ONLY",
        "target_repository": audit["target_repository"],
        "source_audit": f"integration/results/audits/{audit['task_id']}.json",
        "objective": payload.get("objective"),
        "recommended_changes": [
            {
                "priority": "P0",
                "file": ".github/workflows/rio.yml",
                "change": "Gate autonomous_business_cycle, content-review, discover-products and instagram-publish behind an explicit ACTIVE production-state check; PARKED permits audit/document/plan only.",
                "reason": "Scheduled autonomous jobs and external publishing must not run while canonical production state is PARKED.",
            },
            {
                "priority": "P0",
                "file": ".github/workflows/rio.yml",
                "change": "Replace workflow-level contents:write with least-privilege job-level permissions; telegram-test and non-writing checks use contents:read.",
                "reason": "Only jobs that persist validated state require repository write authority.",
            },
            {
                "priority": "P1",
                "file": ".github/workflows/rio.yml",
                "change": "Replace git add -A with explicit allowlisted output paths for heartbeat, content review, product discovery and Instagram status.",
                "reason": "Broad staging can silently commit unrelated code, configuration or generated files.",
            },
            {
                "priority": "P1",
                "file": ".github/workflows/victor-rio-transport.yml",
                "change": "Retain contents:write only for the evidence-persist job and continue staging only integration/results/victor_tasks/{task_id}.json.",
                "reason": "Write access is justified for traceable evidence but must not expand to business execution.",
            },
            {
                "priority": "P1",
                "file": "tests/",
                "change": "Add workflow-policy tests for PARKED gates, job-level permissions, explicit git-add allowlists and prohibition of production/external actions.",
                "reason": "Current static inventory detected only tests/test_economics.py; governance regressions need deterministic coverage.",
            },
        ],
        "implementation_sequence": [
            "Add failing governance tests",
            "Add canonical production-state gate",
            "Narrow job permissions and staged paths",
            "Run validators and workflow-policy tests",
            "Return diff and test evidence to Victor",
            "Require Founder approval before production activation",
        ],
        "prohibited_during_plan": payload.get("prohibited_actions", []),
        "repository_change_performed": False,
        "production_action_performed": False,
        "requires_founder_approval_for_implementation": True,
    }
