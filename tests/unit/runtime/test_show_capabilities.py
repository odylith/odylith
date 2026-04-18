from pathlib import Path

from odylith.install.agents import managed_block
from odylith.runtime.analysis_engine import component_discovery
from odylith.runtime.analysis_engine import show_capabilities
from odylith.runtime.analysis_engine.show_capabilities import format_text
from odylith.runtime.analysis_engine.types import (
    ComponentSuggestion,
    DiagramSuggestion,
    ImportArtifact,
    IssueSuggestion,
    RepoIdentity,
    ShowResult,
    WorkstreamSuggestion,
)


def test_show_text_reads_like_demo_copy_not_command_dump() -> None:
    result = ShowResult(
        identity=RepoIdentity(name="demo", languages=["Python"]),
        total_modules=12,
        already_governed={
            "backlog": True,
            "casebook": True,
            "registry": True,
            "atlas": True,
        },
        components=[
            ComponentSuggestion(
                component_id="dashboard",
                label="Dashboard",
                path="src/demo/dashboard",
                description="Dashboard surface",
                n_modules=8,
                n_inbound=42,
                n_outbound=3,
            )
        ],
        workstreams=[
            WorkstreamSuggestion(
                title="Clarify dashboard ownership",
                description="Dashboard changes cross several runtime paths.",
            )
        ],
        diagrams=[
            DiagramSuggestion(
                slug="dashboard-boundary",
                title="Dashboard Boundary Map",
                description="Show what the dashboard owns.",
            )
        ],
        issues=[
            IssueSuggestion(
                title="Dashboard stale refresh",
                detail="A stale refresh can hide the newest payload.",
            )
        ],
    )

    text = format_text(result)

    assert text.startswith("Odylith read this repo: Python, 12 modules.")
    assert "Radar, Registry, Atlas, and Casebook are already present." in text
    assert "It found 1 Registry component, 1 Radar workstream, 1 Atlas diagram, and 1 Casebook issue" in text
    assert "Say any prompt below verbatim, or use your own words." in text
    assert "Best first move: **Dashboard Registry component**." in text
    assert "defining this logical boundary gives future changes a safer ownership anchor" in text
    assert "Registry candidates - 1 logical component" in text
    assert (
        "Defines: a logical Registry component; "
        "`src/demo/dashboard` is evidence, not the boundary itself."
        in text
    )
    assert (
        "Evidence: 8 source files anchored at `src/demo/dashboard`; "
        "42 inbound imports; 3 outbound imports."
        in text
    )
    assert "Prompt: `Define the Dashboard Registry component.`" in text
    assert "Why: Dashboard changes cross several runtime paths." in text
    assert "Prompt: `Open a Radar workstream for Clarify dashboard ownership.`" in text
    assert "Prompt: `Create the Dashboard Boundary Map Atlas diagram.`" in text
    assert "Prompt: `Capture a Casebook bug for Dashboard stale refresh." in text
    assert "### How to create things" in text
    assert "Everything here: `Apply all suggestions from this Odylith show output.`" in text
    assert "A custom slice: `Define an Odylith plan around <path or feature>" in text
    assert "No files changed." in text
    assert "plain English" in text
    assert "I can scaffold this as an Atlas source diagram." not in text
    assert "I can register this as a Registry boundary" not in text
    assert "Run any command to create it." not in text
    assert "odylith component register" not in text
    assert "odylith backlog create" not in text
    assert "odylith atlas scaffold" not in text
    assert "odylith bug capture" not in text


def test_show_cli_demo_stdout_stays_clean(monkeypatch, tmp_path, capsys) -> None:
    result = ShowResult(
        identity=RepoIdentity(name="demo", languages=["Python"]),
        total_modules=3,
        already_governed={
            "backlog": True,
            "casebook": True,
            "registry": True,
            "atlas": True,
        },
        components=[
            ComponentSuggestion(
                component_id="dashboard",
                label="Dashboard",
                path="src/demo/dashboard",
                description="Dashboard surface",
                n_modules=3,
                n_inbound=8,
                n_outbound=1,
            )
        ],
    )
    monkeypatch.setattr(show_capabilities, "analyze_repo", lambda repo_root: result)

    code = show_capabilities.main(["--repo-root", str(tmp_path)])

    captured = capsys.readouterr()
    assert code == 0
    assert captured.err == ""
    assert "Odylith read this repo:" in captured.out
    assert "Best first move:" in captured.out
    assert "Prompt: `Define the Dashboard Registry component.`" in captured.out
    assert "No files changed." in captured.out
    assert "intervention-status" not in captured.out
    assert "visible-intervention" not in captured.out
    assert "doctor" not in captured.out
    assert "odylith component register" not in captured.out


def test_show_me_skill_blocks_host_status_detours() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    skill_paths = [
        repo_root / ".agents" / "skills" / "odylith-show-me" / "SKILL.md",
        repo_root / ".claude" / "skills" / "odylith-show-me" / "SKILL.md",
        repo_root / "odylith" / "skills" / "odylith-show-me" / "SKILL.md",
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "project-root"
        / ".agents"
        / "skills"
        / "odylith-show-me"
        / "SKILL.md",
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "skills"
        / "odylith-show-me"
        / "SKILL.md",
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "project-root"
        / ".claude"
        / "skills"
        / "odylith-show-me"
        / "SKILL.md",
    ]

    for path in skill_paths:
        text = path.read_text(encoding="utf-8")
        if "@../../../odylith/skills/odylith-show-me/SKILL.md" in text:
            assert "clean advisory demo output" in text or "clean show-me output" in text
            assert "with CLI commands" not in text
        else:
            assert "Run the first available show command" in text
            assert "PYTHONPATH=src python -m odylith.cli show --repo-root ." not in text
            assert "`./.odylith/bin/odylith show --repo-root .`" in text
            assert "`odylith show --repo-root .`" in text
            assert "`intervention-status`, `visible-intervention`" in text
            assert "not proof" in text
            assert "capture stdout only" in text


def test_claude_show_me_guard_is_shipped_in_project_assets() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    guard_paths = [
        repo_root / ".claude" / "hooks" / "show-me-prompt-guard.py",
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "project-root"
        / ".claude"
        / "hooks"
        / "show-me-prompt-guard.py",
    ]

    for path in guard_paths:
        text = path.read_text(encoding="utf-8")
        assert "Odylith show-me first-match route" in text
        assert "odylith-show-me" in text
        assert "PYTHONPATH=src python -m odylith.cli show --repo-root ." not in text
        assert "`./.odylith/bin/odylith show --repo-root .`" in text
        assert "`odylith show --repo-root .`" in text
        assert "`intervention-status`, `visible-intervention`" in text


def test_managed_guidance_exempts_show_me_from_intervention_proof() -> None:
    block = managed_block(repo_role="product_repo")

    assert "Odylith, show me what you can do" in block
    assert "advisory `odylith show` repo-capability demo" in block
    assert "not a request to prove intervention UX" in block
    assert "print stdout only" in block


def test_component_discovery_uses_real_anchor_for_logical_candidates() -> None:
    artifacts = [
        *[
            ImportArtifact(
                path=f"src/demo/runtime/surfaces/{name}_{idx}.py",
                module_name=f"demo.runtime.surfaces.{name}_{idx}",
                language="python",
                imports=(),
            )
            for idx, name in enumerate(
                [
                    "render_backlog",
                    "render_registry",
                    "render_compass",
                    "render_casebook",
                    "dashboard_shell",
                    "surface_bundle",
                    "brand_assets",
                    "tooling_frontend",
                    "layout_audit",
                    "deep_link",
                    "payload_builder",
                    "template_runtime",
                    "workstream_button",
                    "kpi_cards",
                    "release_targets",
                    "program_cards",
                ]
            )
        ],
        *[
            ImportArtifact(
                path=f"src/demo/runtime/common/{name}_{idx}.py",
                module_name=f"demo.runtime.common.{name}_{idx}",
                language="python",
                imports=(),
            )
            for idx, name in enumerate(
                [
                    "paths",
                    "json_cache",
                    "profile",
                    "clock",
                    "logging",
                    "checksum",
                    "filesystem",
                    "runtime_contract",
                    "process",
                    "repo_shape",
                    "dirty_overlap",
                    "command_surface",
                    "stable_utc",
                    "guidance_paths",
                    "budget_policy",
                    "casebook_ids",
                ]
            )
        ],
        *[
            ImportArtifact(
                path=f"src/demo/runtime/governance/{name}_{idx}.py",
                module_name=f"demo.runtime.governance.{name}_{idx}",
                language="python",
                imports=(),
            )
            for idx, name in enumerate(
                [
                    "component_authoring",
                    "backlog_authoring",
                    "sync_workstream",
                    "validate_backlog",
                    "delivery_intelligence",
                    "traceability",
                    "release_planning",
                    "casebook_validation",
                    "registry_intelligence",
                    "owned_refresh",
                    "plan_binding",
                    "wave_contract",
                    "risk_mitigation",
                    "scope_signal",
                    "governance_slice",
                    "capture_apply",
                ]
            )
        ],
    ]

    components = component_discovery.discover_components_from_imports(Path("."), artifacts, [])
    dashboard = next(component for component in components if component.label == "Dashboard")

    assert dashboard.component_id == "dashboard"
    assert dashboard.path == "src/demo/runtime/surfaces"
    assert dashboard.path != "src/demo/runtime/surfaces/core"
    assert len(dashboard.member_paths) == 16
    assert all(path.startswith("src/demo/runtime/surfaces/") for path in dashboard.member_paths)
    assert "16 source files anchored at `src/demo/runtime/surfaces`" in dashboard.evidence
