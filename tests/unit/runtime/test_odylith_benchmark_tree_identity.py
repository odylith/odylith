from __future__ import annotations

import json
from pathlib import Path
import subprocess

from odylith.runtime.evaluation import odylith_benchmark_tree_identity as tree_identity_runtime


def test_snapshot_overlay_paths_exclude_mutable_runtime_state() -> None:
    scenario_reports = [
        {
            "results": [
                {
                    "live_execution": {
                        "effective_snapshot_paths": [
                            "README.md",
                            ".odylith/runtime/odylith-benchmarks/latest.v1.json",
                            "./.odylith/runtime/odylith-compiler/projection-snapshot.v1.json",
                            "docs/benchmarks/README.md",
                        ]
                    }
                }
            ]
        }
    ]

    assert tree_identity_runtime.report_snapshot_overlay_paths(scenario_reports) == [
        "README.md",
        "docs/benchmarks/README.md",
    ]


def test_tree_identity_stays_current_when_ignored_runtime_reports_change(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo_root, text=True, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "bench@example.com"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.name", "Benchmark"], cwd=repo_root, check=True)
    (repo_root / ".gitignore").write_text(".odylith/\n", encoding="utf-8")
    (repo_root / "README.md").write_text("repo\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore", "README.md"], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=repo_root, text=True, capture_output=True, check=True)

    report_path = repo_root / ".odylith" / "runtime" / "odylith-benchmarks" / "latest.v1.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps({"report_id": "old"}), encoding="utf-8")
    snapshot_paths = tree_identity_runtime.report_snapshot_overlay_paths(
        [
            {
                "results": [
                    {
                        "live_execution": {
                            "effective_snapshot_paths": [
                                "README.md",
                                ".odylith/runtime/odylith-benchmarks/latest.v1.json",
                            ]
                        }
                    }
                ]
            }
        ]
    )
    report = tree_identity_runtime.benchmark_tree_identity(
        repo_root=repo_root,
        selection={},
        snapshot_paths=snapshot_paths,
    )
    report["snapshot_overlay_paths"] = snapshot_paths

    report_path.write_text(json.dumps({"report_id": "new"}), encoding="utf-8")

    assert tree_identity_runtime.benchmark_report_matches_current_tree(repo_root=repo_root, report=report)
