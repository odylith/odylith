from __future__ import annotations

from pathlib import Path
import subprocess

from odylith.runtime.evaluation import odylith_benchmark_live_diagnostics as diagnostics


def test_failure_artifact_paths_include_runtime_state_and_structured_changed_files() -> None:
    rows = diagnostics.failure_artifact_paths(
        scenario={
            "changed_paths": ["src/odylith/install/manager.py"],
            "required_paths": ["tests/unit/install/test_manager.py"],
            "critical_paths": ["odylith/AGENTS.md"],
        },
        effective_snapshot_paths=["README.md"],
        observed_paths=["src/odylith/install/runtime.py"],
        candidate_write_paths=["src/odylith/install/manager.py"],
        structured_output={"changed_files": ["tests/unit/install/test_manager.py"]},
        strip_paths=[Path("AGENTS.md"), Path("odylith/AGENTS.md")],
    )

    assert "src/odylith/install/manager.py" in rows
    assert "tests/unit/install/test_manager.py" in rows
    assert "README.md" in rows
    assert "odylith/AGENTS.md" in rows
    assert ".odylith/install.json" in rows
    assert ".odylith/runtime/odylith-benchmarks/latest-proof.v1.json" in rows


def test_workspace_state_diff_reports_different_missing_and_extra_files(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    workspace_root = tmp_path / "workspace"
    repo_root.mkdir(parents=True, exist_ok=True)
    workspace_root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=workspace_root, text=True, capture_output=True, check=True)
    (repo_root / "same.txt").write_text("same\n", encoding="utf-8")
    (workspace_root / "same.txt").write_text("same\n", encoding="utf-8")
    (repo_root / "different.txt").write_text("repo\n", encoding="utf-8")
    (workspace_root / "different.txt").write_text("workspace\n", encoding="utf-8")
    (repo_root / "missing.txt").write_text("repo only\n", encoding="utf-8")
    (workspace_root / "extra.txt").write_text("workspace only\n", encoding="utf-8")

    diff = diagnostics.workspace_state_diff(
        repo_root=repo_root,
        workspace_root=workspace_root,
        tracked_paths=["same.txt", "different.txt", "missing.txt", "extra.txt"],
    )

    by_path = {row["path"]: row for row in diff["differences"]}
    assert diff["difference_count"] == 3
    assert by_path["different.txt"]["status"] == "different_file"
    assert "--- repo/different.txt" in by_path["different.txt"]["diff_excerpt"]
    assert by_path["missing.txt"]["status"] == "workspace_missing"
    assert by_path["extra.txt"]["status"] == "workspace_extra"


def test_workspace_state_diff_pulls_extra_paths_from_git_status(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    workspace_root = tmp_path / "workspace"
    repo_root.mkdir(parents=True, exist_ok=True)
    workspace_root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=workspace_root, text=True, capture_output=True, check=True)
    tracked = workspace_root / "tracked.txt"
    tracked.write_text("tracked\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=workspace_root, check=True)
    workspace_extra = workspace_root / "nested" / "extra.txt"
    workspace_extra.parent.mkdir(parents=True, exist_ok=True)
    workspace_extra.write_text("extra\n", encoding="utf-8")

    diff = diagnostics.workspace_state_diff(
        repo_root=repo_root,
        workspace_root=workspace_root,
        tracked_paths=[],
    )

    assert "nested/extra.txt" in diff["git_status_paths"]
    assert any(row["path"] == "nested/extra.txt" and row["status"] == "workspace_extra" for row in diff["differences"])


def test_workspace_state_diff_reports_missing_workspace_root_without_crashing(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / "tracked.txt").write_text("repo\n", encoding="utf-8")

    diff = diagnostics.workspace_state_diff(
        repo_root=repo_root,
        workspace_root=tmp_path / "missing-workspace",
        tracked_paths=["tracked.txt"],
    )

    assert diff["workspace_root_exists"] is False
    assert diff["tracked_paths"] == ["tracked.txt"]
    assert diff["difference_count"] == 1
    assert diff["differences"] == [
        {
            "path": ".",
            "status": "workspace_root_missing",
            "repo_kind": "dir",
            "workspace_kind": "",
        }
    ]
    assert diff["git_status"] == []


def test_focused_local_check_commands_expand_pytest_node_ids() -> None:
    commands = diagnostics.focused_local_check_commands(
        focused_local_checks=[
            "Unit subset: `tests/unit/install/test_agents.py::test_managed_block_defaults_consumers_to_odylith_guidance_and_skills`.",
            "CLI help: `odylith install --help`.",
        ]
    )

    assert commands == [
        "PYTHONPATH=src .venv/bin/pytest -q tests/unit/install/test_agents.py::test_managed_block_defaults_consumers_to_odylith_guidance_and_skills",
        "odylith install --help",
    ]


def test_focused_local_check_result_lines_compact_pytest_commands() -> None:
    lines = diagnostics.focused_local_check_result_lines(
        result={
            "results": [
                {
                    "status": "passed",
                    "command": "PYTHONPATH=src /repo/.venv/bin/pytest -q tests/unit/install/test_agents.py::test_managed_block_defaults_consumers_to_odylith_guidance_and_skills",
                },
                {
                    "status": "failed",
                    "command": "odylith install --help",
                },
            ]
        }
    )

    assert lines == [
        "passed: tests/unit/install/test_agents.py::test_managed_block_defaults_consumers_to_odylith_guidance_and_skills",
        "failed: odylith install --help",
    ]


def test_prompt_payload_helpers_surface_selected_docs_and_observed_paths() -> None:
    prompt_payload = {
        "docs": ["odylith/AGENTS.md"],
        "relevant_docs": ["odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md"],
        "implementation_anchors": ["src/odylith/install/agents.py"],
        "context_packet": {
            "anchors": {
                "changed_paths": ["src/odylith/install/manager.py"],
                "explicit_paths": ["tests/unit/install/test_agents.py"],
            },
            "retrieval_plan": {
                "selected_docs": ["odylith/skills/odylith-subagent-orchestrator/SKILL.md"],
            },
        },
        "architecture_audit": {
            "changed_paths": ["odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md"],
            "required_reads": ["odylith/registry/source/components/benchmark/CURRENT_SPEC.md"],
            "implementation_anchors": ["src/odylith/runtime/context_engine/odylith_context_engine.py"],
        },
    }

    assert diagnostics.prompt_payload_selected_docs(prompt_payload=prompt_payload) == [
        "odylith/AGENTS.md",
        "odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md",
        "odylith/skills/odylith-subagent-orchestrator/SKILL.md",
        "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
    ]
    assert diagnostics.prompt_payload_observed_paths(prompt_payload=prompt_payload) == [
        "odylith/AGENTS.md",
        "odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md",
        "odylith/skills/odylith-subagent-orchestrator/SKILL.md",
        "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
        "src/odylith/install/agents.py",
        "src/odylith/install/manager.py",
        "tests/unit/install/test_agents.py",
        "odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md",
        "src/odylith/runtime/context_engine/odylith_context_engine.py",
    ]
