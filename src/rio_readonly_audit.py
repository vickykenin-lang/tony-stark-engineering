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
