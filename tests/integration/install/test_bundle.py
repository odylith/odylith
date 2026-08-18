from odylith.bundle import bundle_root
from odylith.runtime.common.product_assets import bundled_project_root_assets_root


def test_bundle_root_contains_installed_agents_entrypoint() -> None:
    root = bundle_root()
    assert (root / "AGENTS.md").is_file()
    agents_text = (root / "AGENTS.md").read_text(encoding="utf-8")
    assert (
        "deterministically verifies typed endpoints, graph completeness, and the full "
        "ProductCreateTransaction without semantic regexes or repair retries"
    ) in agents_text
    assert "renders the sole visible confirmation view" in agents_text
    assert "**CONFIRM** commits the exact reviewed hash-bound package" in agents_text
    assert "**EDIT** treats corrections as new evidence" in agents_text
    assert "greenfield create --repo-root . --transaction-file" in agents_text
    assert (
        "It does not parse evidence, call a model, generate artifacts, or repair prose "
        "after CONFIRM"
    ) in agents_text
    assert "greenfield compile-transaction" not in agents_text
    assert "confirmed-intent.json" not in agents_text
    assert "rerender only the owned surface" in agents_text
    assert "Generated human-visible content has a non-negotiable clarity floor across all lanes" in agents_text
    anti_slop_text = (root / "agents-guidelines" / "ANTI_SLOP_AND_DECOMPOSITION.md").read_text(encoding="utf-8")
    assert "grammatically coherent, and clear about the thing it describes" in anti_slop_text
    assert "plain English before it tries to be expressive" in anti_slop_text
    assert "Codex-Only Optimizations When Supported" in (root / "agents-guidelines" / "CODEX_HOST_CONTRACT.md").read_text(encoding="utf-8")
    assert "./.odylith/bin/odylith codex compatibility --repo-root ." in (root / "README.md").read_text(encoding="utf-8")
    assert "./.odylith/bin/odylith radar refresh --repo-root ." in (root / "README.md").read_text(encoding="utf-8")
    assert "./.odylith/bin/odylith atlas refresh --repo-root . --atlas-sync" in (root / "README.md").read_text(encoding="utf-8")
    assert "./.odylith/bin/odylith dashboard refresh --repo-root . --surfaces <surface>" not in (root / "agents-guidelines" / "CLI_FIRST_POLICY.md").read_text(encoding="utf-8")
    assert (root / "CLAUDE.md").is_file()
    assert (root / "agents-guidelines").is_dir()
    assert (root / "skills").is_dir()
    assert (root / "skills" / "odylith-diagram-catalog" / "SKILL.md").is_file()

    project_root = bundled_project_root_assets_root()
    assert (project_root / ".claude" / "CLAUDE.md").is_file()
    assert (project_root / ".claude" / "settings.json").is_file()
    assert (project_root / ".claude" / "commands" / "odylith-start.md").is_file()
    assert (project_root / ".claude" / "commands" / "odylith-context.md").is_file()
    assert (project_root / ".claude" / "commands" / "odylith-query.md").is_file()
    assert (project_root / ".claude" / "commands" / "odylith-plan.md").is_file()
    assert (project_root / ".claude" / "commands" / "odylith-worktree.md").is_file()
    worktree_command = (project_root / ".claude" / "commands" / "odylith-worktree.md").read_text(encoding="utf-8")
    assert "./.odylith/bin/odylith doctor --repo-root .claude/worktrees/$ARGUMENTS --repair" in worktree_command
    assert "only call intervention or self-host posture fully end to end there after `intervention-status` reports `Activation: ready` and `Chat-visible proof: proven_this_session`" in worktree_command
    codex_contract = (root / "agents-guidelines" / "CODEX_HOST_CONTRACT.md").read_text(encoding="utf-8")
    assert "Only describe a Codex session or worktree as fully end to end after" in codex_contract
    claude_contract = (root / "agents-guidelines" / "CLAUDE_HOST_CONTRACT.md").read_text(encoding="utf-8")
    assert "Only describe a Claude session or worktree as fully end to end after" in claude_contract
    assert (project_root / ".claude" / "commands" / "odylith-sync-governance.md").is_file()
    sync_command = (project_root / ".claude" / "commands" / "odylith-sync-governance.md").read_text(encoding="utf-8")
    assert "./.odylith/bin/odylith radar refresh --repo-root ." in sync_command
    assert "./.odylith/bin/odylith dashboard refresh --repo-root . --surfaces <surface>" not in sync_command
    assert (project_root / ".claude" / "agents" / "odylith-compass-narrator.md").is_file()
    assert (project_root / ".claude" / "agents" / "odylith-reviewer.md").is_file()
    assert (project_root / ".claude" / "agents" / "odylith-workstream.md").is_file()
    assert (project_root / ".claude" / "agents" / "odylith-validator.md").is_file()
    assert (project_root / ".claude" / "agents" / "odylith-governance-scribe.md").is_file()
    assert (project_root / ".claude" / "hooks" / "odylith_claude_support.py").is_file()
    assert (project_root / ".claude" / "hooks" / "subagent-start-ground.py").is_file()
    assert (project_root / ".claude" / "hooks" / "refresh-governance-after-edit.py").is_file()
    refresh_hook = (project_root / ".claude" / "hooks" / "refresh-governance-after-edit.py").read_text(encoding="utf-8")
    assert "governance refresh completed" not in refresh_hook
    assert "completed after editing" not in refresh_hook
    assert (project_root / ".claude" / "hooks" / "session-start-ground.py").is_file()
    assert (project_root / ".claude" / "hooks" / "log-stop-summary.py").is_file()
    assert (project_root / ".claude" / "hooks" / "guard-destructive-bash.py").is_file()
    assert (project_root / ".claude" / "output-styles" / "odylith-grounded.md").is_file()
    assert (project_root / ".claude" / "skills" / "odylith-code-hygiene-guard" / "SKILL.md").is_file()
    assert (project_root / ".claude" / "skills" / "odylith-subagent-router" / "SKILL.md").is_file()
    assert (project_root / ".claude" / "skills" / "odylith-delivery-governance-surface-ops" / "SKILL.md").is_file()
    assert (project_root / ".claude" / "rules" / "odylith-governance.md").is_file()
    assert (project_root / ".codex" / "config.toml").is_file()
    assert (project_root / ".codex" / "hooks.json").is_file()
    assert (project_root / ".codex" / "agents" / "odylith-workstream.toml").is_file()
    assert (project_root / ".agents" / "bin" / "odylith-host-launcher.py").is_file()
    codex_hooks = (project_root / ".codex" / "hooks.json").read_text(encoding="utf-8")
    assert "python3 ./.agents/bin/odylith-host-launcher.py codex session-start-ground --repo-root ." in codex_hooks
    assert (project_root / ".agents" / "skills" / "odylith-start" / "SKILL.md").is_file()
    assert (project_root / ".agents" / "skills" / "odylith-subagent-router" / "SKILL.md").is_file()
    assert (project_root / ".agents" / "skills" / "odylith-subagent-orchestrator" / "SKILL.md").is_file()
    assert "odylith-code-hygiene-guard" in (project_root / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
    assert "ANTI_SLOP_AND_DECOMPOSITION.md" in (project_root / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
    assert "odylith-code-hygiene-guard" in (project_root / ".claude" / "agents" / "odylith-reviewer.md").read_text(encoding="utf-8")


def test_bundle_root_contains_managed_governance_surface_assets() -> None:
    root = bundle_root()
    assert (root / "atlas" / "source" / "AGENTS.md").is_file()
    assert (root / "atlas" / "source" / "CLAUDE.md").is_file()
    assert not (root / "atlas" / "source" / "architecture-domains.v1.json").exists()
    assert (root / "compass" / "runtime" / "AGENTS.md").is_file()
    assert (root / "compass" / "runtime" / "CLAUDE.md").is_file()
    assert (root / "radar" / "source" / "AGENTS.md").is_file()
    assert (root / "radar" / "source" / "CLAUDE.md").is_file()
    assert (root / "casebook" / "bugs" / "AGENTS.md").is_file()
    assert (root / "casebook" / "bugs" / "CLAUDE.md").is_file()
    assert (root / "registry" / "source" / "AGENTS.md").is_file()
    assert (root / "registry" / "source" / "CLAUDE.md").is_file()
    assert not (root / "registry" / "source" / "component_registry.v1.json").exists()
    assert (root / "runtime" / "contracts" / "delivery_intelligence_snapshot.v4.schema.json").is_file()
    assert (root / "runtime" / "contracts" / "tribunal_case.v1.schema.json").is_file()
    assert (root / "runtime" / "contracts" / "tribunal_outcome.v1.schema.json").is_file()
    assert (root / "runtime" / "contracts" / "correction_packet.v1.schema.json").is_file()
    assert (root / "technical-plans" / "AGENTS.md").is_file()
    assert (root / "technical-plans" / "CLAUDE.md").is_file()
    assert not (root / "casebook" / "bugs" / "INDEX.md").exists()
    assert (root / "agents-guidelines" / "CODEX_HOST_CONTRACT.md").is_file()


def test_bundle_root_does_not_ship_volatile_runtime_artifacts_into_consumer_truth_roots() -> None:
    root = bundle_root()
    assert not (root / "compass" / "runtime" / "codex-stream.v1.jsonl").exists()
    assert not (root / "compass" / "runtime" / "current.v1.json").exists()
    assert not (root / "compass" / "runtime" / "current.v1.js").exists()
    assert not (root / "compass" / "runtime" / "history").exists()
