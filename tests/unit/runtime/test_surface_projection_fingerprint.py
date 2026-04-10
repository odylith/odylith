from __future__ import annotations

from pathlib import Path

from odylith.runtime.governance import agent_governance_intelligence as governance
from odylith.runtime.governance import component_registry_intelligence as component_registry
from odylith.runtime.context_engine import surface_projection_fingerprint


def _seed_projection_tree(repo_root: Path) -> None:
    for relative_path, content in (
        ("odylith/radar/source/INDEX.md", "# backlog\n"),
        ("odylith/technical-plans/INDEX.md", "# plans\n"),
        ("odylith/casebook/bugs/INDEX.md", "# bugs\n"),
        ("odylith/registry/source/component_registry.v1.json", "{}\n"),
        ("odylith/atlas/source/catalog/diagrams.v1.json", "{}\n"),
        ("odylith/compass/runtime/codex-stream.v1.jsonl", ""),
        ("odylith/radar/traceability-graph.v1.json", "{}\n"),
        ("odylith/runtime/delivery_intelligence.v4.json", "{}\n"),
    ):
        path = repo_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    for relative_dir in (
        "odylith/radar/source/archive",
        "odylith/radar/source/ideas",
        "odylith/technical-plans/done",
        "odylith/technical-plans/parked",
        "odylith/casebook/bugs/archive",
        "odylith/registry/source/components",
    ):
        (repo_root / relative_dir).mkdir(parents=True, exist_ok=True)


def test_default_surface_projection_input_fingerprint_changes_when_bug_contract_version_changes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _seed_projection_tree(tmp_path)

    baseline = surface_projection_fingerprint.default_surface_projection_input_fingerprint(repo_root=tmp_path)

    monkeypatch.setattr(
        surface_projection_fingerprint,
        "projection_contract_version",
        lambda name: "v999_bug_contract" if str(name) == "bugs" else "v1",
    )

    updated = surface_projection_fingerprint.default_surface_projection_input_fingerprint(repo_root=tmp_path)

    assert updated != baseline


def test_workspace_activity_fingerprint_ignores_generated_surface_outputs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        surface_projection_fingerprint,
        "_normalize_repo_token",
        lambda token, *, repo_root: str(token).strip(),
    )

    collect_paths = [
        "odylith/compass/runtime/current.v1.json",
        "odylith/compass/compass.html",
        "src/odylith/bundle/assets/odylith/compass/compass.html",
    ]
    monkeypatch.setattr(
        governance,
        "collect_git_changed_paths",
        lambda *, repo_root: list(collect_paths),
    )
    monkeypatch.setattr(
        component_registry,
        "is_meaningful_workspace_artifact",
        lambda _token: True,
    )

    assert surface_projection_fingerprint._workspace_activity_fingerprint(repo_root=tmp_path) == surface_projection_fingerprint.odylith_context_cache.fingerprint_payload([])  # noqa: SLF001


def test_workspace_activity_fingerprint_keeps_source_truth_when_generated_outputs_change_too(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        surface_projection_fingerprint,
        "_normalize_repo_token",
        lambda token, *, repo_root: str(token).strip(),
    )
    monkeypatch.setattr(
        component_registry,
        "is_meaningful_workspace_artifact",
        lambda _token: True,
    )
    monkeypatch.setattr(
        surface_projection_fingerprint.odylith_context_cache,
        "path_signature",
        lambda path: str(Path(path).name),
    )

    monkeypatch.setattr(
        governance,
        "collect_git_changed_paths",
        lambda *, repo_root: [
            "odylith/compass/runtime/current.v1.json",
            "src/odylith/runtime/surfaces/compass_dashboard_runtime.py",
        ],
    )
    mixed = surface_projection_fingerprint._workspace_activity_fingerprint(repo_root=tmp_path)  # noqa: SLF001

    monkeypatch.setattr(
        governance,
        "collect_git_changed_paths",
        lambda *, repo_root: ["src/odylith/runtime/surfaces/compass_dashboard_runtime.py"],
    )
    source_only = surface_projection_fingerprint._workspace_activity_fingerprint(repo_root=tmp_path)  # noqa: SLF001

    assert mixed == source_only
