from __future__ import annotations

import json
from pathlib import Path
import time

from odylith.install.state import write_install_state, write_upgrade_spotlight, write_version_pin
from odylith.runtime.surfaces import render_tooling_dashboard as renderer
from odylith.runtime.surfaces import tooling_dashboard_shell_presenter


def _load_externalized_payload_js(path: Path) -> dict[str, object]:
    raw = path.read_text(encoding="utf-8").strip()
    _prefix, _separator, remainder = raw.partition(" = ")
    payload_text = remainder.removesuffix(";")
    return json.loads(payload_text)


def _seed_inputs(tmp_path: Path) -> None:
    for surface in ("radar", "atlas", "compass", "registry", "casebook"):
        surface_root = tmp_path / "odylith" / surface
        surface_root.mkdir(parents=True, exist_ok=True)
        (surface_root / f"{surface}.html").write_text(f"<!doctype html><title>{surface.title()}</title>\n", encoding="utf-8")
    runtime_source = tmp_path / "odylith" / "runtime" / "source"
    runtime_source.mkdir(parents=True, exist_ok=True)
    (runtime_source / "tooling_shell.v1.json").write_text(
        json.dumps(
            {
                "shell_repo_label": "Repo · Odylith",
                "maintainer_notes": [
                    {
                        "note_id": "N-001",
                        "title": "Product Self-Governance Is Live Here",
                        "recorded_at": "2026-03-26 13:05:00 PDT",
                        "context": "This repository is the public product home for Odylith.",
                        "section_title": "Watch",
                        "bullets": [
                            "Keep product docs, product guidance, product skills, and product runtime behavior source-owned in this repository."
                        ],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _seed_compass_runtime_snapshot(
    tmp_path: Path,
    *,
    generated_utc: str,
    refresh_profile: str = "shell-safe",
    last_refresh_attempt: dict[str, object] | None = None,
    warning: str = "",
) -> None:
    runtime_root = tmp_path / "odylith" / "compass" / "runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "generated_utc": generated_utc,
        "runtime_contract": {
            "version": "v1",
            "refresh_profile": refresh_profile,
        },
    }
    if last_refresh_attempt is not None:
        runtime_contract = dict(payload["runtime_contract"])  # type: ignore[arg-type]
        runtime_contract["last_refresh_attempt"] = dict(last_refresh_attempt)
        payload["runtime_contract"] = runtime_contract
    if warning:
        payload["warning"] = warning
    (runtime_root / "current.v1.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (runtime_root / "current.v1.js").write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )


def _seed_product_repo_posture(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='odylith'\nversion='0.1.0'\n", encoding="utf-8")
    (tmp_path / "src" / "odylith").mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "registry" / "source").mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "radar" / "source").mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "registry" / "source" / "component_registry.v1.json").write_text(
        '{"version":"v1","components":[]}\n',
        encoding="utf-8",
    )
    (tmp_path / "odylith" / "radar" / "source" / "INDEX.md").write_text("# Backlog Index\n", encoding="utf-8")
    write_version_pin(repo_root=tmp_path, version="0.1.0")
    runtime_root = tmp_path / ".odylith" / "runtime" / "versions" / "0.1.0" / "bin"
    runtime_root.mkdir(parents=True, exist_ok=True)
    python_path = runtime_root / "python"
    python_path.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    python_path.chmod(0o755)
    current_link = tmp_path / ".odylith" / "runtime" / "current"
    current_link.parent.mkdir(parents=True, exist_ok=True)
    current_link.symlink_to(runtime_root.parent)
    write_install_state(
        repo_root=tmp_path,
        payload={
            "active_version": "0.1.0",
            "activation_history": ["0.1.0"],
            "installed_versions": {"0.1.0": {"runtime_root": str(runtime_root.parent), "verification": {"wheel_sha256": "abc123"}}},
            "last_known_good_version": "0.1.0",
        },
    )


def _seed_product_repo_source_local_posture(tmp_path: Path) -> None:
    _seed_product_repo_posture(tmp_path)
    source_runtime_root = tmp_path / ".odylith" / "runtime" / "versions" / "source-local" / "bin"
    source_runtime_root.mkdir(parents=True, exist_ok=True)
    source_python = source_runtime_root / "python"
    source_python.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    source_python.chmod(0o755)
    current_link = tmp_path / ".odylith" / "runtime" / "current"
    if current_link.exists() or current_link.is_symlink():
        current_link.unlink()
    current_link.symlink_to(source_runtime_root.parent)
    write_install_state(
        repo_root=tmp_path,
        payload={
            "active_version": "source-local",
            "activation_history": ["0.1.0", "source-local"],
            "detached": True,
            "installed_versions": {
                "0.1.0": {
                    "runtime_root": str(tmp_path / ".odylith" / "runtime" / "versions" / "0.1.0"),
                    "verification": {"wheel_sha256": "abc123"},
                },
                "source-local": {
                    "runtime_root": str(source_runtime_root.parent),
                    "verification": {"mode": "source-local"},
                },
            },
            "last_known_good_version": "0.1.0",
        },
    )


def _seed_existing_odylith_truth(tmp_path: Path) -> None:
    ideas_root = tmp_path / "odylith" / "radar" / "source" / "ideas"
    ideas_root.mkdir(parents=True, exist_ok=True)
    (ideas_root / "B-001-example.md").write_text("# Example backlog item\n", encoding="utf-8")
    component_root = tmp_path / "odylith" / "registry" / "source" / "components" / "core"
    component_root.mkdir(parents=True, exist_ok=True)
    (component_root / "CURRENT_SPEC.md").write_text("# Core\n", encoding="utf-8")
    atlas_root = tmp_path / "odylith" / "atlas" / "source"
    atlas_root.mkdir(parents=True, exist_ok=True)
    (atlas_root / "core-boundary-map.mmd").write_text("graph TD\n  A[Core]\n", encoding="utf-8")


def _seed_legacy_consumer_launcher(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir(exist_ok=True)
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    launcher_path.parent.mkdir(parents=True, exist_ok=True)
    launcher_path.write_text("#!/usr/bin/env bash\nexec \"$PYTHON\" -m odylith.cli \"$@\"\n", encoding="utf-8")
    write_install_state(
        repo_root=tmp_path,
        payload={
            "active_version": "0.1.1",
            "activation_history": ["0.1.1"],
            "installed_versions": {
                "0.1.1": {
                    "runtime_root": str(tmp_path / ".odylith" / "runtime" / "versions" / "0.1.1"),
                    "verification": {"wheel_sha256": "abc123"},
                }
            },
            "last_known_good_version": "0.1.1",
        },
    )
    write_version_pin(repo_root=tmp_path, version="0.1.1")


def _seed_consumer_upgrade_spotlight(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir(exist_ok=True)
    write_install_state(
        repo_root=tmp_path,
        payload={
            "active_version": "1.2.3",
            "activation_history": ["1.2.2", "1.2.3"],
            "installed_versions": {
                "1.2.3": {
                    "runtime_root": str(tmp_path / ".odylith" / "runtime" / "versions" / "1.2.3"),
                    "verification": {"wheel_sha256": "abc123"},
                }
            },
            "last_known_good_version": "1.2.3",
        },
    )
    write_upgrade_spotlight(
        repo_root=tmp_path,
        from_version="1.2.2",
        to_version="1.2.3",
        release_tag="v1.2.3",
        release_url="https://example.com/releases/v1.2.3",
        release_published_at="2026-03-30T14:00:00Z",
        release_body=(
            "Odylith now lands with a stronger consumer upgrade moment.\n\n"
            "The shell refreshes immediately after upgrade so you stay on the current contract."
        ),
        highlights=(
            "Sharper install messaging.",
            "Cleaner shell onboarding.",
            "Faster dashboard refresh after upgrade.",
        ),
    )


def test_render_tooling_dashboard_uses_repo_owned_shell_metadata(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _seed_inputs(tmp_path)
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {},
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])

    assert rc == 0

    html = (tmp_path / "odylith" / "index.html").read_text(encoding="utf-8")
    assert "Repo · Odylith" not in html
    assert "Product Self-Governance Is Live Here" in html
    assert "manifest.json" in html
    assert "favicon.svg" in html
    assert "odylith-lockup-horizontal.svg" in html
    assert "Delivery Governance and Intelligence" not in html
    assert "Odylith | Delivery Governance and Intelligence" not in html
    assert "Mission-control deck for delivery state, architectural truth, defect intelligence, evidence trails, and runtime posture." not in html
    assert "tab-icon" not in html
    assert "Proof Gate Closeout And Shared Test Recovery" not in html
    assert "Start Odylith from one real code path" in html
    assert "Copy prompt" in html
    assert "welcome-launchpad-hero" in html
    assert "Open the cheatsheet drawer on the left and try out commands in this repo." in html
    assert "Three quick steps" in html
    assert "Paste it into Codex or Claude Code." in html
    assert "Try commands in the cheatsheet." in html
    assert "Open the cheatsheet drawer on the left side of the screen and try out commands." not in html
    assert "Paste it into Codex or Claude Code in this repo." not in html
    assert "Let Odylith create the first Radar item, Registry boundary, Atlas map around" not in html
    assert "Copy this starter prompt into your agent. Odylith will create the first Radar item, Registry boundary, and Atlas map around one real code path in this repo." not in html
    assert "First governed slice" not in html
    assert "1 prompt to copy" not in html
    assert "Radar + Registry + Atlas to seed" not in html
    assert "welcome-chip-row" not in html
    assert "No path detected yet" not in html
    assert "No starting path yet" not in html
    assert "src/app" not in html
    assert "services/api" not in html
    assert "What Odylith already sees" not in html
    assert "What happens next" not in html
    assert 'aria-label="Hide starter guide"' in html
    assert "Hide for now" not in html
    assert "Starter Guide" in html
    assert "shellRecoveryDock" in html
    assert "shellRuntimeStatus" in html
    assert "shellRuntimeStatusKicker" in html
    assert "shellRuntimeStatusReload" in html
    assert "shellRuntimeStatusDismiss" in html
    assert "runtimeStatusReopen" not in html
    assert "The shell refreshes itself as Odylith updates local surfaces." in html
    assert "Add a workstream file under" not in html
    assert "welcome-record-grid" not in html
    assert "Open Radar view" not in html
    assert "Open Registry view" not in html
    assert "Open Atlas view" not in html
    assert "What the core surfaces do first" in html
    assert "Radar keeps a clear backlog so the repo always has one governed next step." in html
    assert "Registry is the component ledger for boundaries, ownership, and contracts." in html
    assert "Atlas keeps architecture visible with diagrams of topology and flow." in html
    assert "Compass keeps briefs and timelines so the next move stays clear." in html
    assert "the first real code path you choose" not in html
    assert 'id="themeToggle"' not in html
    assert ">Telemetry<" not in html
    assert 'id="odylithToggle"' in html
    assert "Cheatsheet" in html
    assert "Odylith Dashboard Cheatsheet" in html
    assert "Odylith Dashboard" in html
    assert "Developer Notes" in html
    assert "Platform Maintainer's Notes" not in html
    assert "Persistent shell-owned developer notes." in html
    assert "Create a Radar backlog item" in html
    assert "Create a Registry component" in html
    assert "Create an Atlas diagram" in html
    assert "Create a Casebook bug" in html
    assert "Payments boundary cleanup" in html
    assert "Create a Registry component named" in html
    assert "Create an Atlas diagram for the payments component." in html
    assert "Duplicate payment capture after webhook retry" in html
    assert "Release planning: pick the ship target" in html
    assert "Program/wave planning: sequence umbrella execution" in html
    assert "Release planning picks the ship target for one workstream" in html
    assert "Program/wave planning picks execution order under one umbrella" in html
    assert "A workstream can belong to both." in html
    assert "Add B-067 to release 0.1.11." in html
    assert "odylith release add B-067 0.1.11 --repo-root ." in html
    assert "For umbrella workstream B-021, create a 3-wave execution program." in html
    assert "odylith program next B-021 --repo-root ." in html
    assert "Refresh the full dashboard" in html
    assert "Refresh Compass now" in html
    assert "Deep-refresh Compass" in html
    assert "Keep Compass warm" in html
    assert "odylith compass refresh --repo-root ." in html
    assert "odylith compass deep-refresh --repo-root ." in html
    assert "Run the change-driven watcher so Compass refreshes only when repo truth actually moves." in html
    assert "odylith compass watch-transactions --repo-root ." in html
    assert "Add a developer note" in html
    assert "Open Radar for workstream B-025." in html
    assert "Open Registry for the payments component." in html
    assert "Start Odylith and ground me in src/payments/service.py." in html
    assert "Map a component or workstream in Atlas" in html
    assert "Map the payments component in Atlas." in html
    assert "Find the Atlas diagram for workstream B-025." in html
    assert "Open a known component or workstream" in html
    assert "Show me the files and records for the payments component." in html
    assert "component like payments or a workstream id like B-025" in html
    assert "Odylith scopes to the tied files and governed records." in html
    assert "Validate plan bindings before closing workstream B-025." in html
    assert "Show the critical risks for workstream B-025." in html
    assert "What should I work on next after workstream B-025?" in html
    assert "Open the bug trail for bug CB-001." in html
    assert "Map the current slice in Atlas" not in html
    assert "Find the right Atlas diagram for this workstream." not in html
    assert "These prompts are short on purpose" not in html
    assert 'id="agentCheatsheetSearch"' in html
    assert 'data-cheatsheet-filter="create"' in html
    assert 'data-cheatsheet-filter="edit"' in html
    assert "Example prompt" in html
    assert "Copy prompt" in html
    assert "Telemetry runtime status drawer" not in html
    assert html.index('<h3 class="cheatsheet-card-title">Create a Radar backlog item</h3>') < html.index('<h3 class="cheatsheet-card-title">Odylith Dashboard</h3>')
    assert html.index('<h3 class="cheatsheet-card-title">Create a Registry component</h3>') < html.index('<h3 class="cheatsheet-card-title">Odylith Dashboard</h3>')
    assert html.index('<h3 class="cheatsheet-card-title">Create an Atlas diagram</h3>') < html.index('<h3 class="cheatsheet-card-title">Odylith Dashboard</h3>')
    assert html.index('<h3 class="cheatsheet-card-title">Create a Casebook bug</h3>') < html.index('<h3 class="cheatsheet-card-title">Odylith Dashboard</h3>')


def test_shell_case_preview_rows_include_proof_preview_lines(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _seed_inputs(tmp_path)
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {},
    )
    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])
    assert rc == 0

    rows = tooling_dashboard_shell_presenter.shell_case_preview_rows(
        [
            {
                "id": "case-1",
                "rank": 1,
                "headline": "Stay pinned to the blocker seam",
                "brief": "Preview proof is not live proof.",
                "decision_at_stake": "Fix the live blocker before sidecars.",
                "scope_key": "workstream:B-062",
                "scope_id": "B-062",
                "proof_state": {
                    "lane_id": "proof-state-control-plane",
                    "current_blocker": "Lambda permission lifecycle on ecs-drift-monitor invoke",
                    "failure_fingerprint": "aws:lambda:Permission doesn't support update",
                    "frontier_phase": "manifests-deploy",
                    "proof_status": "fixed_in_code",
                },
                "claim_guard": {
                    "highest_truthful_claim": "fixed in code",
                    "blocked_terms": ["fixed", "cleared", "resolved"],
                },
            }
        ]
    )

    assert rows[0]["proof_lines"][:3] == [
        "Current blocker: Lambda permission lifecycle on ecs-drift-monitor invoke",
        "Failure fingerprint: aws:lambda:Permission doesn't support update",
        "Frontier: manifests-deploy",
    ]
    assert rows[0]["proof_claim"] == "fixed in code"


def test_shell_case_preview_rows_surface_proof_resolution_ambiguity() -> None:
    rows = tooling_dashboard_shell_presenter.shell_case_preview_rows(
        [
            {
                "id": "case-2",
                "rank": 2,
                "headline": "Ambiguous proof lane",
                "brief": "Do not fake a precise blocker.",
                "decision_at_stake": "Pick the right lane before status language.",
                "scope_key": "workstream:B-999",
                "scope_id": "B-999",
                "proof_state": {},
                "proof_state_resolution": {
                    "state": "ambiguous",
                    "lane_ids": ["lane-a", "lane-b"],
                },
            }
        ]
    )

    assert rows[0]["proof_lines"] == [
        "Proof state is ambiguous across multiple blocker lanes: lane-a, lane-b."
    ]


def test_shell_case_preview_rows_surface_same_fingerprint_reopen_summary() -> None:
    rows = tooling_dashboard_shell_presenter.shell_case_preview_rows(
        [
            {
                "id": "case-3",
                "rank": 3,
                "headline": "Keep the blocker seam pinned",
                "brief": "The same live blocker came back.",
                "decision_at_stake": "Reuse the same bug lane instead of narrating a new mystery.",
                "scope_key": "workstream:B-062",
                "scope_id": "B-062",
                "proof_state": {
                    "lane_id": "proof-state-control-plane",
                    "current_blocker": "Lambda permission lifecycle on ecs-drift-monitor invoke",
                    "failure_fingerprint": "aws:lambda:Permission doesn't support update",
                    "frontier_phase": "manifests-deploy",
                    "proof_status": "falsified_live",
                    "last_falsification": {
                        "recorded_at": "2026-04-08T18:42:00Z",
                        "failure_fingerprint": "aws:lambda:Permission doesn't support update",
                        "frontier_phase": "manifests-deploy",
                    },
                    "linked_bug_id": "CB-077",
                    "repeated_fingerprint_count": 2,
                },
                "proof_reopen": {
                    "same_fingerprint_reopened": True,
                    "linked_bug_id": "CB-077",
                    "repeated_fingerprint_count": 2,
                    "summary": "Previous fix did not clear the live blocker; keep Lambda permission lifecycle on ecs-drift-monitor invoke pinned as the active seam. Reuse Casebook bug CB-077 rather than opening a new blocker record.",
                },
            }
        ]
    )

    assert rows[0]["proof_lines"][0].startswith("Previous fix did not clear the live blocker")


def test_render_tooling_dashboard_includes_self_host_payload(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _seed_inputs(tmp_path)
    _seed_product_repo_posture(tmp_path)
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {},
    )
    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])

    assert rc == 0
    html = (tmp_path / "odylith" / "index.html").read_text(encoding="utf-8")
    assert "v0.1.0" in html
    assert ">odylith<" in html
    assert "Telemetry Snapshot" not in html
    assert "Maintainer Benchmark Lane" not in html
    payload_js = (tmp_path / "odylith" / "tooling-payload.v1.js").read_text(encoding="utf-8")
    assert '"self_host"' in payload_js
    assert '"benchmark_story"' not in payload_js
    assert '"odylith_drawer"' not in payload_js
    assert '"odylith_drawer_history"' not in payload_js
    assert '"repo_role": "product_repo"' in payload_js
    assert '"posture": "pinned_release"' in payload_js
    assert '"runtime_source": "pinned_runtime"' in payload_js
    assert '"shell_repo_name": "odylith"' in payload_js
    assert '"shell_version_label": "v0.1.0"' in payload_js
    assert '"compass_href": "compass/compass.html?v=' in payload_js


def test_render_tooling_dashboard_enables_passive_live_refresh_for_consumer_repo(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _seed_inputs(tmp_path)
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {},
    )
    monkeypatch.setattr(
        renderer.agent_governance_intelligence,
        "collect_git_changed_paths",
        lambda **kwargs: ["src/payments/service.py", "odylith/registry/registry-payload.v1.js"],
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])

    assert rc == 0
    payload_js = _load_externalized_payload_js(tmp_path / "odylith" / "tooling-payload.v1.js")
    live_refresh = dict(payload_js["live_refresh"])
    assert live_refresh["enabled"] is True
    assert live_refresh["mode"] == "passive_runtime_probe"
    assert live_refresh["policy_id"] == "balanced"
    assert live_refresh["state_href"] == "../.odylith/runtime/odylith-context-engine-state.v1.js"
    assert live_refresh["reloadable_tabs"] == ["radar", "registry", "compass", "casebook"]
    assert live_refresh["surface_policies"]["compass"]["auto_reload"] is True
    assert live_refresh["surface_policies"]["atlas"]["auto_reload"] is False
    assert live_refresh["surface_policies"]["atlas"]["next_command"] == "odylith dashboard refresh --repo-root . --surfaces atlas --atlas-sync"
    assert live_refresh["credit_guard"]["provider_backed_refresh"] == "manual_only"
    assert live_refresh["worktree"]["status"] == "mixed"
    assert live_refresh["worktree"]["meaningful_changed_count"] == 1
    assert live_refresh["worktree"]["generated_changed_count"] == 1


def test_render_tooling_dashboard_dedupes_stale_compass_runtime_from_shell_status(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _seed_inputs(tmp_path)
    _seed_compass_runtime_snapshot(tmp_path, generated_utc="2026-04-07T17:06:12Z")
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {},
    )
    monkeypatch.setattr(
        renderer.tooling_dashboard_surface_status,
        "now_utc",
        lambda: "2026-04-07T17:17:57Z",
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])

    assert rc == 0
    payload_js = _load_externalized_payload_js(tmp_path / "odylith" / "tooling-payload.v1.js")
    assert payload_js["surface_runtime_status"] == {}


def test_render_tooling_dashboard_dedupes_stale_failed_compass_refresh_from_shell_status(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    _seed_inputs(tmp_path)
    _seed_compass_runtime_snapshot(
        tmp_path,
        generated_utc="2020-01-02T17:06:12Z",
        last_refresh_attempt={
            "status": "failed",
            "requested_profile": "shell-safe",
            "applied_profile": "shell-safe",
            "attempted_utc": "2026-04-07T17:17:57Z",
            "reason": "timeout",
        },
        warning=(
            "Requested Compass refresh did not finish before the refresh timeout. "
            "Showing the last successful shell-safe runtime snapshot from 2020-01-02T17:06:12Z."
        ),
    )
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {},
    )
    monkeypatch.setattr(
        renderer.tooling_dashboard_surface_status,
        "now_utc",
        lambda: "2026-04-09T19:17:57Z",
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])

    assert rc == 0
    payload_js = _load_externalized_payload_js(tmp_path / "odylith" / "tooling-payload.v1.js")
    assert payload_js["surface_runtime_status"] == {}


def test_render_tooling_dashboard_dedupes_failed_compass_refresh_when_compass_payload_warns(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    _seed_inputs(tmp_path)
    _seed_compass_runtime_snapshot(
        tmp_path,
        generated_utc="2026-04-07T17:06:12Z",
        last_refresh_attempt={
            "status": "failed",
            "requested_profile": "shell-safe",
            "applied_profile": "shell-safe",
            "attempted_utc": "2026-04-07T17:17:57Z",
            "reason": "timeout",
        },
        warning=(
            "Requested Compass refresh did not finish before the refresh timeout. "
            "Showing the last successful shell-safe runtime snapshot from 2026-04-07T17:06:12Z."
        ),
    )
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {},
    )
    monkeypatch.setattr(
        renderer.tooling_dashboard_surface_status,
        "now_utc",
        lambda: "2026-04-07T18:17:57Z",
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])

    assert rc == 0
    payload_js = _load_externalized_payload_js(tmp_path / "odylith" / "tooling-payload.v1.js")
    assert payload_js["surface_runtime_status"] == {}


def test_render_tooling_dashboard_projects_failed_compass_refresh_into_shell_status(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _seed_inputs(tmp_path)
    _seed_compass_runtime_snapshot(
        tmp_path,
        generated_utc="2026-04-07T17:06:12Z",
        last_refresh_attempt={
            "status": "failed",
            "requested_profile": "shell-safe",
            "applied_profile": "shell-safe",
            "attempted_utc": "2026-04-07T17:17:57Z",
            "reason": "timeout",
        },
    )
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {},
    )
    monkeypatch.setattr(
        renderer.tooling_dashboard_surface_status,
        "now_utc",
        lambda: "2026-04-07T18:17:57Z",
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])

    assert rc == 0
    payload_js = _load_externalized_payload_js(tmp_path / "odylith" / "tooling-payload.v1.js")
    compass_status = dict(payload_js["surface_runtime_status"]["compass"])
    assert compass_status["tone"] == "warning"
    assert compass_status["title"] == "Showing prior Compass snapshot"
    assert compass_status["body"] == (
        "Requested Compass refresh failed before a fresh payload was written. "
        "Showing the prior runtime snapshot from 2026-04-07T17:06:12Z."
    )
    assert "Snapshot: 2026-04-07T17:06:12Z" in compass_status["meta"]
    assert "Attempted: 2026-04-07T17:17:57Z" in compass_status["meta"]
    assert "Next: odylith dashboard refresh --repo-root . --surfaces compass" in compass_status["meta"]


def test_render_tooling_dashboard_disables_live_refresh_for_product_repo(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _seed_inputs(tmp_path)
    _seed_product_repo_posture(tmp_path)
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {},
    )
    monkeypatch.setattr(
        renderer.agent_governance_intelligence,
        "collect_git_changed_paths",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("product repo live refresh should stay benchmark-frozen")),
    )
    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])

    assert rc == 0
    payload_js = _load_externalized_payload_js(tmp_path / "odylith" / "tooling-payload.v1.js")
    live_refresh = dict(payload_js["live_refresh"])
    assert live_refresh["enabled"] is False
    assert live_refresh["policy_id"] == "proof_frozen"
    assert live_refresh["disabled_reason"] == "benchmark_frozen_product_repo"


def test_render_tooling_dashboard_shows_detached_product_repo_version_readout(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _seed_inputs(tmp_path)
    _seed_product_repo_source_local_posture(tmp_path)
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {},
    )
    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])

    assert rc == 0
    html = (tmp_path / "odylith" / "index.html").read_text(encoding="utf-8")
    assert '<p class="toolbar-version">source-local</p>' in html
    payload_js = (tmp_path / "odylith" / "tooling-payload.v1.js").read_text(encoding="utf-8")
    assert '"posture": "detached_source_local"' in payload_js
    assert '"runtime_source": "source_checkout"' in payload_js
    assert '"shell_version_label": "source-local"' in payload_js


def test_render_tooling_dashboard_enables_balanced_live_refresh_for_detached_source_local(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _seed_inputs(tmp_path)
    _seed_product_repo_source_local_posture(tmp_path)
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {},
    )
    monkeypatch.setattr(
        renderer.agent_governance_intelligence,
        "collect_git_changed_paths",
        lambda **kwargs: ["src/odylith/runtime/surfaces/render_tooling_dashboard.py"],
    )
    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])

    assert rc == 0
    payload_js = _load_externalized_payload_js(tmp_path / "odylith" / "tooling-payload.v1.js")
    live_refresh = dict(payload_js["live_refresh"])
    assert live_refresh["enabled"] is True
    assert live_refresh["policy_id"] == "balanced"
    assert live_refresh["reloadable_tabs"] == ["radar", "registry", "compass", "casebook"]


def test_render_tooling_dashboard_allows_explicit_full_dev_live_refresh_override(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _seed_inputs(tmp_path)
    source_path = tmp_path / "odylith" / "runtime" / "source" / "tooling_shell.v1.json"
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    payload["live_refresh_policy"] = "full_dev"
    source_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {},
    )
    monkeypatch.setattr(
        renderer.agent_governance_intelligence,
        "collect_git_changed_paths",
        lambda **kwargs: [],
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])

    assert rc == 0
    payload_js = _load_externalized_payload_js(tmp_path / "odylith" / "tooling-payload.v1.js")
    live_refresh = dict(payload_js["live_refresh"])
    assert live_refresh["enabled"] is True
    assert live_refresh["policy_id"] == "full_dev"
    assert live_refresh["poll_interval_ms"] == 12000
    assert live_refresh["surface_policies"]["atlas"]["auto_reload"] is True
    assert live_refresh["reloadable_tabs"] == ["radar", "registry", "compass", "casebook", "atlas"]


def test_render_tooling_dashboard_uses_tab_local_state_for_shell_surface_switches(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _seed_inputs(tmp_path)
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {},
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])

    assert rc == 0
    control_js = (tmp_path / "odylith" / "tooling-app.v1.js").read_text(encoding="utf-8")
    assert "const tabStateMemory =" in control_js
    assert "function sanitizeShellState(rawState)" in control_js
    assert "function buildTabActivationState(tab)" in control_js
    assert "const hasOdylithDrawer = Boolean(" in control_js
    assert "const welcomeDismissStorageKey =" in control_js
    assert "const welcomeDismissKeyToken =" in control_js
    assert "const recoveryDock = document.getElementById(\"shellRecoveryDock\");" in control_js
    assert "const viewport = document.querySelector(\".viewport\");" in control_js
    assert "const welcomeReopen = document.getElementById(\"welcomeReopen\");" in control_js
    assert "const runtimeStatusReopen = document.getElementById(\"runtimeStatusReopen\");" not in control_js
    assert "const runtimeStatusKicker = document.getElementById(\"shellRuntimeStatusKicker\");" in control_js
    assert "const runtimeStatusDismiss = document.getElementById(\"shellRuntimeStatusDismiss\");" in control_js
    assert "const upgradeReopen = document.getElementById(\"upgradeReopen\");" in control_js
    assert "initToolingShellCheatsheetDrawer" in control_js
    assert "const searchInput = root.querySelector(\"[data-cheatsheet-search]\");" in control_js
    assert "const UPGRADE_SPOTLIGHT_MAX_AGE_MS = 30 * 60 * 1000;" in control_js
    assert "function resolveUpgradeSpotlightExpiryMs(rawPayload) {" in control_js
    assert "function hasUpgradeSpotlight() {" in control_js
    assert "const shouldDeferWelcomeUntilUpgradeCloses = Boolean(" in control_js
    assert "const shellStateStorageKey =" in control_js
    assert "function eachBrowserStorage(visitor)" in control_js
    assert "window.sessionStorage" in control_js
    assert "const upgradeSpotlightBackdrop = document.getElementById(\"upgradeSpotlightBackdrop\");" in control_js
    assert "function syncRecoveryDock()" in control_js
    assert "const showUpgradeReopen = Boolean(upgradeReopen && hasUpgradeSpotlight() && !upgradeVisible && !welcomeVisible);" in control_js
    assert "function dismissUpgradeSpotlight()" in control_js
    assert "function reopenUpgradeSpotlight()" in control_js
    assert "function expireUpgradeSpotlightWindow() {" in control_js
    assert "function scheduleUpgradeSpotlightExpiry() {" in control_js
    assert 'document.body.classList.toggle("shell-upgrade-spotlight-open"' in control_js
    assert 'localStorageWrite(shellStateStorageKey, JSON.stringify(state));' in control_js
    assert "const rememberedState = localStorageRead(shellStateStorageKey);" in control_js
    assert "setWelcomeDismissed(true);" in control_js
    assert "welcomeReopen.addEventListener(\"click\"" in control_js
    assert "upgradeReopen.addEventListener(\"click\", reopenUpgradeSpotlight);" in control_js
    assert "if (shouldDeferWelcomeUntilUpgradeCloses) {" in control_js
    assert "if (hasOdylithDrawer) {" in control_js
    assert "function liveRefreshSurfacePolicy(tab)" in control_js
    assert "function runtimeStateAffectsTab(tab, runtimeState)" in control_js
    assert "function runtimeAutoReloadReadyForTab(tab)" in control_js
    assert "function buildRuntimeStatusFingerprint(posture) {" in control_js
    assert "const initialSurfaceRuntimeStatus = payload && payload.surface_runtime_status" in control_js
    assert "const surfaceRuntimeStatus = runtimeState && runtimeState.surface_runtime_status" in control_js
    assert "const rawPosture = surfaceRuntimeStatus[currentTab];" in control_js
    assert "function mergeRuntimeStatusState(runtimeState) {" in control_js
    assert "function runtimeStatusDismissed() {" in control_js
    assert "function syncRuntimeStatusLayout() {" in control_js
    assert "function scheduleRuntimeStatusLayoutSync() {" in control_js
    assert "setRuntimeStatusDismissed(true);" in control_js
    assert "runtimeStatusReopen.addEventListener(\"click\"" not in control_js
    assert "function buildRuntimeStatusPosture(runtimeState) {" in control_js
    assert "visible: false," in control_js
    assert "applyRuntimeStatus(latestRuntimeStatusState || {});" in control_js
    assert "applyRuntimeStatus(mergeRuntimeStatusState(payload));" in control_js
    assert 'applyTab(buildTabActivationState("atlas"), { pushHistory: true });' in control_js
    assert 'applyTab(buildTabActivationState("radar"), { pushHistory: true });' in control_js
    html = (tmp_path / "odylith" / "index.html").read_text(encoding="utf-8")
    assert 'id="upgradeReopen"' in html
    assert 'id="runtimeStatusReopen"' not in html
    assert 'id="shellRuntimeStatusKicker"' in html
    assert 'id="shellRuntimeStatusDismiss"' in html
    assert 'id="shellRecoveryDock"' in html
    assert 'id="agentCheatsheetSearch"' in html
    assert 'data-cheatsheet-filter="refresh"' in html
    assert 'data-cheatsheet-filter="edit"' in html
    assert ".welcome-state[hidden]" in html
    assert ".upgrade-spotlight[hidden]" in html


def test_render_tooling_dashboard_hides_welcome_state_once_truth_exists(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _seed_inputs(tmp_path)
    _seed_existing_odylith_truth(tmp_path)
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {},
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])

    assert rc == 0
    html = (tmp_path / "odylith" / "index.html").read_text(encoding="utf-8")
    payload_js = (tmp_path / "odylith" / "tooling-payload.v1.js").read_text(encoding="utf-8")
    assert "Odylith is ready in this repository" not in html
    assert 'id="welcomeCopyPrompt"' not in html
    assert '"welcome_state": {"chosen_slice": {' in payload_js
    assert '"show": false' in payload_js


def test_render_tooling_dashboard_shows_compact_legacy_upgrade_notice(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _seed_inputs(tmp_path)
    _seed_existing_odylith_truth(tmp_path)
    _seed_legacy_consumer_launcher(tmp_path)
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {},
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])

    assert rc == 0
    html = (tmp_path / "odylith" / "index.html").read_text(encoding="utf-8")
    assert "Odylith needs attention in this repository" in html
    assert "Legacy upgrade path detected" in html
    assert "Copy rescue install" in html
    assert "https://odylith.ai/install.sh | bash" in html
    assert "Odylith is live in this repository" not in html


def test_render_tooling_dashboard_shows_release_spotlight_for_recent_upgrade(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _seed_inputs(tmp_path)
    _seed_existing_odylith_truth(tmp_path)
    _seed_consumer_upgrade_spotlight(tmp_path)
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {},
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])

    assert rc == 0
    html = (tmp_path / "odylith" / "index.html").read_text(encoding="utf-8")
    payload_js = (tmp_path / "odylith" / "tooling-payload.v1.js").read_text(encoding="utf-8")
    control_js = (tmp_path / "odylith" / "tooling-app.v1.js").read_text(encoding="utf-8")
    assert "upgrade-spotlight-stage" in html
    assert "upgradeSpotlightBackdrop" in html
    assert '>v1.2.3</h2>' in html
    assert "v1.2.2 -&gt; v1.2.3" in html
    assert "upgrade-spotlight-list" in html
    assert "Upgrade complete. v1.2.3 is live in this repo, and the full release note is ready on the right." not in html
    assert "The shell refreshes immediately after upgrade so you stay on the current contract." not in html
    assert '<p class="toolbar-version">v1.2.3</p>' in html
    assert 'id="toolbarVersionStoryLink"' not in html
    assert "What changed since v1.2.2?" not in html
    assert 'id="themeToggle"' not in html
    assert '>v1.2.2<' not in html
    assert "Open full release note" not in html
    assert "Sharper install messaging." in html
    assert "Open release note on GitHub" in html
    assert (
        'href="https://github.com/odylith/odylith/blob/v1.2.3/odylith/runtime/source/release-notes/v1.2.3.md"'
        in html
    )
    assert 'target="_blank" rel="noreferrer"' in html
    assert "upgrade-spotlight-secondary-link" not in html
    assert "The bottom recovery pill keeps it close for thirty minutes after the upgrade is recorded." not in html
    assert 'id="upgradeReopen"' in html
    assert '"release_spotlight"' in payload_js
    assert '"shell_version_label": "v1.2.3"' in payload_js
    assert '"reopen_label": "v1.2.3"' in payload_js
    assert '"to_version": "1.2.3"' in payload_js
    assert (
        '"notes_url": "https://github.com/odylith/odylith/blob/v1.2.3/odylith/runtime/source/release-notes/v1.2.3.md"'
        in payload_js
    )
    assert "const upgradeSpotlightDismissStorageKey =" in control_js
    assert 'upgradeReopen.textContent = upgradeSpotlightReopenLabel;' in control_js
    assert 'welcomeReopen.textContent = "Starter Guide";' in control_js
    assert 'const upgradeSpotlightReopenLabel = hasUpgradeSpotlight()' in control_js
    assert not (tmp_path / "odylith" / "release-notes" / "1.2.3.html").exists()


def test_render_tooling_dashboard_persists_version_story_without_live_upgrade_popup(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _seed_inputs(tmp_path)
    _seed_existing_odylith_truth(tmp_path)
    (tmp_path / ".git").mkdir(exist_ok=True)
    write_install_state(
        repo_root=tmp_path,
        payload={
            "active_version": "1.2.3",
            "activation_history": ["1.2.2", "1.2.3"],
            "installed_versions": {
                "1.2.3": {
                    "runtime_root": str(tmp_path / ".odylith" / "runtime" / "versions" / "1.2.3"),
                    "verification": {"wheel_sha256": "abc123"},
                }
            },
        },
    )
    notes_root = tmp_path / "odylith" / "runtime" / "source" / "release-notes"
    notes_root.mkdir(parents=True, exist_ok=True)
    (notes_root / "v1.2.3.md").write_text(
        (
            "---\n"
            "version: 1.2.3\n"
            "published_at: 2026-03-30T14:00:00Z\n"
            "summary: Persistent version story.\n"
            "highlights:\n"
            "  - Highlight one.\n"
            "---\n\n"
            "Persistent version story.\n\n"
            "Keep the release note available after the popup moment."
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {},
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])

    assert rc == 0
    html = (tmp_path / "odylith" / "index.html").read_text(encoding="utf-8")
    payload_js = (tmp_path / "odylith" / "tooling-payload.v1.js").read_text(encoding="utf-8")
    assert 'id="shellUpgradeSpotlight"' not in html
    assert 'id="toolbarVersionStoryLink"' not in html
    assert "What changed since v1.2.2?" not in html
    assert '"version_story"' in payload_js
    assert (
        '"notes_url": "https://github.com/odylith/odylith/blob/v1.2.3/odylith/runtime/source/release-notes/v1.2.3.md"'
        in payload_js
    )
    assert not (tmp_path / "odylith" / "release-notes").exists()


def test_render_tooling_dashboard_release_note_prefers_highlights_over_full_body_paragraphs(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _seed_inputs(tmp_path)
    _seed_existing_odylith_truth(tmp_path)
    _seed_consumer_upgrade_spotlight(tmp_path)
    notes_root = tmp_path / "odylith" / "runtime" / "source" / "release-notes"
    notes_root.mkdir(parents=True, exist_ok=True)
    long_paragraph = (
        "This release turns benchmarking into part of the product, not a sidecar maintainer ritual. "
        "Odylith now runs a live release-proof lane across a 37-scenario corpus, measures warm and cold matched pairs, "
        "publishes family heatmaps and operating-posture graphs, and separates diagnostic tuning from proof so the public claim stays anchored to validator-backed outcomes instead of flattering prompt demos."
    )
    (notes_root / "v1.2.3.md").write_text(
        (
            "---\n"
            "version: 1.2.3\n"
            "published_at: 2026-03-30T14:00:00Z\n"
            "summary: Full paragraph release note.\n"
            "highlights:\n"
            "  - Highlight one.\n"
            "---\n\n"
            "Full paragraph release note.\n\n"
            f"{long_paragraph}\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {},
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])

    assert rc == 0
    html = (tmp_path / "odylith" / "index.html").read_text(encoding="utf-8")
    assert "Highlight one." in html
    assert long_paragraph not in html


def test_render_tooling_dashboard_includes_version_in_authored_release_hero_title(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _seed_inputs(tmp_path)
    _seed_existing_odylith_truth(tmp_path)
    _seed_consumer_upgrade_spotlight(tmp_path)
    notes_root = tmp_path / "odylith" / "runtime" / "source" / "release-notes"
    notes_root.mkdir(parents=True, exist_ok=True)
    (notes_root / "v1.2.3.md").write_text(
        (
            "---\n"
            "version: 1.2.3\n"
            "title: Trusted In Public\n"
            "published_at: 2026-03-30T14:00:00Z\n"
            "summary: Authored release summary.\n"
            "highlights:\n"
            "  - Highlight one.\n"
            "---\n\n"
            "Authored release summary.\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {},
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])

    assert rc == 0
    html = (tmp_path / "odylith" / "index.html").read_text(encoding="utf-8")
    assert '<span class="upgrade-spotlight-title-copy">Trusted In Public</span>' in html
    assert '<span class="upgrade-spotlight-title-version">v1.2.3</span>' in html


def test_render_tooling_dashboard_prunes_stale_release_note_pages(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _seed_inputs(tmp_path)
    _seed_existing_odylith_truth(tmp_path)
    _seed_consumer_upgrade_spotlight(tmp_path)
    notes_root = tmp_path / "odylith" / "runtime" / "source" / "release-notes"
    notes_root.mkdir(parents=True, exist_ok=True)
    (notes_root / "v1.2.3.md").write_text(
        (
            "---\n"
            "version: 1.2.3\n"
            "published_at: 2026-03-30T14:00:00Z\n"
            "summary: Current release note.\n"
            "---\n\n"
            "Current release note.\n\n"
            "Keep only the current rendered note."
        ),
        encoding="utf-8",
    )
    rendered_notes_root = tmp_path / "odylith" / "release-notes"
    rendered_notes_root.mkdir(parents=True, exist_ok=True)
    (rendered_notes_root / "1.2.2.html").write_text("stale\n", encoding="utf-8")
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {},
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])

    assert rc == 0
    assert not rendered_notes_root.exists()


def test_render_tooling_dashboard_escapes_authored_release_note_content(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _seed_inputs(tmp_path)
    _seed_existing_odylith_truth(tmp_path)
    _seed_consumer_upgrade_spotlight(tmp_path)
    notes_root = tmp_path / "odylith" / "runtime" / "source" / "release-notes"
    notes_root.mkdir(parents=True, exist_ok=True)
    (notes_root / "v1.2.3.md").write_text(
        (
            "---\n"
            "version: 1.2.3\n"
            "published_at: 2026-03-30T14:00:00Z\n"
            "summary: <script>alert(1)</script> summary\n"
            "highlights:\n"
            "  - <script>alert(2)</script> highlight\n"
            "---\n\n"
            "First paragraph stays readable.\n\n"
            "<script>alert(3)</script> detail paragraph."
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {},
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])

    assert rc == 0
    html = (tmp_path / "odylith" / "index.html").read_text(encoding="utf-8")
    assert "<script>alert(1)</script> summary" not in html
    assert "alert(1) summary" in html
    assert "<script>alert(2)</script> highlight" not in html
    assert "alert(2) highlight" in html
    assert str(tmp_path.resolve()) not in html
    assert not (tmp_path / "odylith" / "release-notes").exists()


def test_render_tooling_dashboard_ignores_stale_upgrade_payload_on_first_install(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _seed_inputs(tmp_path)
    (tmp_path / ".git").mkdir(exist_ok=True)
    (tmp_path / "src" / "billing").mkdir(parents=True, exist_ok=True)
    write_install_state(
        repo_root=tmp_path,
        payload={
            "active_version": "1.2.3",
            "activation_history": ["1.2.3"],
            "installed_versions": {
                "1.2.3": {
                    "runtime_root": str(tmp_path / ".odylith" / "runtime" / "versions" / "1.2.3"),
                    "verification": {"wheel_sha256": "abc123"},
                }
            },
            "last_known_good_version": "1.2.3",
        },
    )
    write_version_pin(repo_root=tmp_path, version="1.2.3")
    write_upgrade_spotlight(
        repo_root=tmp_path,
        from_version="1.2.2",
        to_version="1.2.3",
        release_tag="v1.2.3",
        release_url="https://example.com/releases/v1.2.3",
        release_published_at="2026-03-30T14:00:00Z",
        release_body="This should stay hidden on first install.",
        highlights=("Hidden on first install.",),
    )
    rendered_notes_root = tmp_path / "odylith" / "release-notes"
    rendered_notes_root.mkdir(parents=True, exist_ok=True)
    (rendered_notes_root / "1.2.2.html").write_text("stale\n", encoding="utf-8")
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {},
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])

    assert rc == 0
    html = (tmp_path / "odylith" / "index.html").read_text(encoding="utf-8")
    payload_js = (tmp_path / "odylith" / "tooling-payload.v1.js").read_text(encoding="utf-8")
    assert 'id="shellUpgradeSpotlight"' not in html
    assert "Starter Guide" in html
    assert 'id="upgradeReopen"' in html
    assert "Show release note" not in html
    assert '<p class="toolbar-version">v1.2.3</p>' in html
    assert '"release_spotlight": {}' in payload_js
    assert not rendered_notes_root.exists()


def test_render_tooling_dashboard_includes_memory_area_readout(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _seed_inputs(tmp_path)
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {
            "memory_snapshot": {
                "engine": {
                    "backend": {
                        "storage": "lance_local_columnar",
                        "sparse_recall": "tantivy_sparse_recall",
                    },
                    "target_backend": {
                        "storage": "lance_local_columnar",
                        "sparse_recall": "tantivy_sparse_recall",
                    },
                    "backend_transition": {"status": "standardized"},
                },
                "backend_transition": {
                    "status": "standardized",
                    "actual_local_backend": {
                        "storage": "lance_local_columnar",
                        "sparse_recall": "tantivy_sparse_recall",
                    },
                },
                "guidance_catalog": {"chunk_count": 6, "source_doc_count": 2, "task_family_count": 2},
                "runtime_state": {"active_sessions": 1, "bootstrap_packets": 1},
                "entity_counts": {"indexed_entity_count": 42, "evidence_documents": 17},
                "memory_areas": {
                    "headline": "Repo truth and retrieval memory are strong. Decision memory is still planned.",
                    "counts": {"strong": 2, "partial": 1, "planned": 3},
                    "gaps": [
                        "Decision memory: Resolved decisions are not first-class durable memory yet.",
                        "Collaboration memory: Workspace and actor memory are not first-class durable memory yet.",
                    ],
                    "areas": [
                        {
                            "key": "repo_truth",
                            "label": "Repo truth",
                            "state": "strong",
                            "summary": "Git-tracked backlog, plans, bugs, diagrams, components, and code remain authoritative.",
                        },
                        {
                            "key": "retrieval",
                            "label": "Retrieval memory",
                            "state": "strong",
                            "summary": "Lance / Tantivy is active across the local evidence set.",
                        },
                        {
                            "key": "decisions",
                            "label": "Decision memory",
                            "state": "planned",
                            "summary": "Resolved decisions are not first-class durable memory yet.",
                        },
                    ],
                },
                "judgment_memory": {
                    "headline": "Decision memory and onboarding memory are durable.",
                    "counts": {"strong": 5, "partial": 2, "cold": 1},
                    "gaps": [
                        "Negative memory: One retained failure signal still needs remediation.",
                    ],
                    "areas": [
                        {
                            "key": "decisions",
                            "label": "Decision memory",
                            "state": "strong",
                            "summary": "Done plans and benchmark proof are retained.",
                        },
                        {
                            "key": "onboarding",
                            "label": "Onboarding memory",
                            "state": "strong",
                            "summary": "Odylith retains the first governed slice and the latest bootstrap evidence for it.",
                        },
                    ],
                },
                "remote_retrieval": {"enabled": False},
            },
            "optimization_snapshot": {"overall": {"score": 0.0, "level": "cold"}},
            "evaluation_snapshot": {"status": "cold", "coverage_rate": 0.0, "satisfaction_rate": 0.0},
        },
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])

    assert rc == 0
    html = (tmp_path / "odylith" / "index.html").read_text(encoding="utf-8")
    payload_js = (tmp_path / "odylith" / "tooling-payload.v1.js").read_text(encoding="utf-8")
    assert "tooling-payload.v1.js?v=" in html
    assert "tooling-app.v1.js?v=" in html
    assert "memory_areas" in payload_js
    assert "Repo truth" in payload_js
    assert "Decision memory" in payload_js
    assert "Onboarding memory" in payload_js
    assert "judgment_memory" in payload_js


def test_render_tooling_dashboard_skips_noop_writes_when_bundle_is_unchanged(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    _seed_inputs(tmp_path)
    _seed_compass_runtime_snapshot(tmp_path, generated_utc="2026-04-07T17:06:12Z")
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {},
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])
    assert rc == 0

    tracked_paths = (
        tmp_path / "odylith" / "index.html",
        tmp_path / "odylith" / "tooling-payload.v1.js",
        tmp_path / "odylith" / "tooling-app.v1.js",
    )
    first_mtimes = {path: path.stat().st_mtime_ns for path in tracked_paths}

    time.sleep(0.01)
    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])
    assert rc == 0

    second_mtimes = {path: path.stat().st_mtime_ns for path in tracked_paths}
    assert second_mtimes == first_mtimes


def test_render_tooling_dashboard_skips_cached_rebuild_before_surface_validation(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    _seed_inputs(tmp_path)
    _seed_compass_runtime_snapshot(tmp_path, generated_utc="2026-04-07T17:06:12Z")
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {},
    )

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])
    assert rc == 0

    def _boom(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("surface validation should be skipped on a cache hit")

    monkeypatch.setattr(renderer.tooling_dashboard_runtime_builder, "validate_surface_paths", _boom)

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])
    assert rc == 0
