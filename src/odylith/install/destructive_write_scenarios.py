"""Executable destructive-write scenario inventory for install and migration gates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class DestructiveWriteScenario:
    """A local-state loss mode that install, repair, or migration must guard."""

    scenario_id: str
    surface: str
    lifecycle_paths: tuple[str, ...]
    data_at_risk: str
    unsafe_failure_mode: str
    required_guardrail: str
    proof_markers: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-ready scenario contract."""
        return {
            "scenario_id": self.scenario_id,
            "surface": self.surface,
            "lifecycle_paths": list(self.lifecycle_paths),
            "data_at_risk": self.data_at_risk,
            "unsafe_failure_mode": self.unsafe_failure_mode,
            "required_guardrail": self.required_guardrail,
            "proof_markers": list(self.proof_markers),
        }


_SCENARIOS: tuple[DestructiveWriteScenario, ...] = (
    DestructiveWriteScenario(
        scenario_id="host.claude.preverified-settings",
        surface=".claude/settings.json",
        lifecycle_paths=("install", "reinstall", "upgrade", "doctor --repair"),
        data_at_risk="Claude Code credentials, environment, permissions, statusLine, and user hooks",
        unsafe_failure_mode="write Odylith hooks before release runtime verification, then fail and leave broken host config",
        required_guardrail="defer activation until runtime success; merge additively; preserve first preimage",
        proof_markers=(
            "test_install_bundle_preserves_host_settings_when_runtime_download_fails",
            "test_upgrade_preserves_host_settings_when_runtime_download_fails",
        ),
    ),
    DestructiveWriteScenario(
        scenario_id="host.claude.additive-merge",
        surface=".claude/settings.json",
        lifecycle_paths=("install", "reinstall", "upgrade", "doctor --repair"),
        data_at_risk="existing Claude permissions, unknown top-level settings, statusLine, env, and hooks",
        unsafe_failure_mode="replace the JSON object with an Odylith-only settings template",
        required_guardrail="merge only Odylith additions and keep user-owned shapes intact",
        proof_markers=(
            "test_write_effective_claude_project_settings_merges_without_destroying_user_settings",
            "test_write_effective_claude_project_settings_preserves_nonstandard_user_shapes",
        ),
    ),
    DestructiveWriteScenario(
        scenario_id="host.claude.invalid-or-linked-json",
        surface=".claude/settings.json",
        lifecycle_paths=("install", "reinstall", "upgrade", "doctor --repair"),
        data_at_risk="externally managed or manually edited Claude settings",
        unsafe_failure_mode="repair malformed JSON or write through a symlink target owned outside the repo",
        required_guardrail="fail closed on invalid JSON and symlinks",
        proof_markers=(
            "test_write_effective_claude_project_settings_refuses_invalid_json",
            "test_write_effective_claude_project_settings_refuses_symlink",
        ),
    ),
    DestructiveWriteScenario(
        scenario_id="host.claude.symlinked-project-root",
        surface=".claude/",
        lifecycle_paths=("install", "reinstall", "upgrade", "doctor --repair"),
        data_at_risk="external Claude project settings directories such as dotfile-manager or enterprise-managed config",
        unsafe_failure_mode="write Odylith settings through a symlinked .claude directory into external host config",
        required_guardrail="treat symlinked host config directories as externally owned and leave them untouched",
        proof_markers=("test_write_effective_claude_project_settings_refuses_symlinked_claude_directory",),
    ),
    DestructiveWriteScenario(
        scenario_id="host.claude.preimage-stability",
        surface=".claude/settings.json.odylith-preimage.bak",
        lifecycle_paths=("install", "reinstall", "upgrade", "doctor --repair"),
        data_at_risk="the only local copy of pre-Odylith host settings",
        unsafe_failure_mode="overwrite the first backup with an already-mutated Odylith settings file",
        required_guardrail="write a preimage backup once and never replace it",
        proof_markers=("test_write_effective_claude_project_settings_keeps_first_preimage_backup",),
    ),
    DestructiveWriteScenario(
        scenario_id="host.codex.config",
        surface=".codex/config.toml",
        lifecycle_paths=("install", "reinstall", "upgrade", "doctor --repair"),
        data_at_risk="Codex model, provider, sandbox, and local project settings",
        unsafe_failure_mode="replace a nonempty user config with Odylith project defaults",
        required_guardrail="only create missing/empty config; preserve divergent user config byte-for-byte",
        proof_markers=(
            "test_install_bundle_preserves_host_settings_when_runtime_download_fails",
            "test_write_effective_codex_project_config_preserves_existing_user_config",
        ),
    ),
    DestructiveWriteScenario(
        scenario_id="host.codex.hooks",
        surface=".codex/hooks.json",
        lifecycle_paths=("install", "reinstall", "upgrade", "doctor --repair"),
        data_at_risk="Codex user automation hooks",
        unsafe_failure_mode="replace hook arrays with Odylith-only hooks",
        required_guardrail="merge hook groups by event without dropping existing commands",
        proof_markers=(
            "test_install_bundle_merges_host_settings_after_verified_runtime_activation",
            "test_write_effective_codex_hooks_merges_without_destroying_user_hooks",
        ),
    ),
    DestructiveWriteScenario(
        scenario_id="host.codex.invalid-or-linked-json",
        surface=".codex/hooks.json",
        lifecycle_paths=("install", "reinstall", "upgrade", "doctor --repair"),
        data_at_risk="externally managed Codex hook settings",
        unsafe_failure_mode="repair malformed JSON or write through a symlink target owned outside the repo",
        required_guardrail="fail closed on invalid JSON and symlinks",
        proof_markers=(
            "test_write_effective_codex_hooks_refuses_invalid_json",
            "test_write_effective_codex_hooks_refuses_symlink",
        ),
    ),
    DestructiveWriteScenario(
        scenario_id="host.codex.symlinked-project-root",
        surface=".codex/",
        lifecycle_paths=("install", "reinstall", "upgrade", "doctor --repair"),
        data_at_risk="external Codex project settings directories such as dotfile-manager or enterprise-managed config",
        unsafe_failure_mode="write Odylith config or hooks through a symlinked .codex directory into external host config",
        required_guardrail="treat symlinked host config directories as externally owned and leave them untouched",
        proof_markers=("test_write_effective_codex_assets_refuse_symlinked_codex_directory",),
    ),
    DestructiveWriteScenario(
        scenario_id="host.codex.skill-prune",
        surface=".agents/skills",
        lifecycle_paths=("install", "reinstall", "upgrade", "doctor --repair"),
        data_at_risk="user-authored Codex skills and local command shims",
        unsafe_failure_mode="delete every skill not present in the Odylith curated bundle",
        required_guardrail="prune only known retired Odylith shims, never arbitrary user skills",
        proof_markers=("test_project_root_skill_prune_preserves_user_custom_skills",),
    ),
    DestructiveWriteScenario(
        scenario_id="managed.project-root-linked-targets",
        surface=".claude/, .codex/, .agents/",
        lifecycle_paths=("install", "reinstall", "upgrade", "doctor --repair"),
        data_at_risk="external files reached by symlinked managed project-root assets or symlinked skill cleanup roots",
        unsafe_failure_mode="copy managed assets or prune retired shims through symlinked repo paths into external files",
        required_guardrail="skip managed asset writes and cleanup whenever the destination path contains a symlink",
        proof_markers=(
            "test_sync_managed_project_root_assets_refuses_symlinked_managed_file",
            "test_sync_managed_project_root_assets_refuses_symlinked_managed_directory",
            "test_sync_managed_project_root_assets_refuses_symlinked_skill_prune_root",
        ),
    ),
    DestructiveWriteScenario(
        scenario_id="managed.product-tree-linked-targets",
        surface="odylith/ managed guidance, skills, brand, and release-note assets",
        lifecycle_paths=("install", "reinstall", "upgrade", "doctor --repair"),
        data_at_risk="external product-tree files reached by symlinked odylith/ paths",
        unsafe_failure_mode="copy or clean install-managed Odylith assets through symlinked target roots",
        required_guardrail="skip managed product-tree writes and release-note cleanup whenever the destination path contains a symlink",
        proof_markers=(
            "test_sync_managed_release_notes_refuses_symlinked_target_root",
            "test_sync_managed_agents_guidelines_refuses_symlinked_odylith_root",
        ),
    ),
    DestructiveWriteScenario(
        scenario_id="guidance.root-managed-block",
        surface="AGENTS.md and CLAUDE.md",
        lifecycle_paths=("install", "reinstall", "upgrade", "doctor --repair"),
        data_at_risk="repo-owned human and agent guidance outside Odylith's managed block",
        unsafe_failure_mode="replace root guidance instead of injecting/removing the managed block",
        required_guardrail="scope edits to Odylith markers and preserve surrounding content",
        proof_markers=("test_remove_managed_block_also_removes_legacy_marker_block",),
    ),
    DestructiveWriteScenario(
        scenario_id="governance.source-truth-preserve",
        surface="odylith/radar, odylith/technical-plans, odylith/casebook, odylith/registry, odylith/atlas",
        lifecycle_paths=("install", "reinstall", "upgrade", "doctor --repair"),
        data_at_risk="consumer repo governance source truth",
        unsafe_failure_mode="refresh bundled starter content over existing repo-owned records",
        required_guardrail="seed only missing starter files; upgrades refresh managed guidance, not repo-owned truth",
        proof_markers=("test_install_bundle_preserves_legacy_odylith_created_truth_in_customer_tree",),
    ),
    DestructiveWriteScenario(
        scenario_id="migration.legacy-product-conflict",
        surface="odyssey/ -> odylith/",
        lifecycle_paths=("migrate-legacy-install", "upgrade", "reinstall"),
        data_at_risk="existing Odylith product/guidance files in mixed legacy repos",
        unsafe_failure_mode="unlink existing Odylith files while merging legacy Odyssey paths",
        required_guardrail="preflight conflicts and block before moving either root",
        proof_markers=("test_legacy_odyssey_product_conflict_blocks_before_overwrite",),
    ),
    DestructiveWriteScenario(
        scenario_id="migration.legacy-state-conflict",
        surface=".odyssey/ -> .odylith/",
        lifecycle_paths=("migrate-legacy-install", "upgrade", "reinstall"),
        data_at_risk="current install state, launcher, runtime pointers, and ledgers",
        unsafe_failure_mode="discard legacy or current state when both roots contain the same mapped path",
        required_guardrail="preflight mapped state conflicts and block before deleting either state root",
        proof_markers=("test_legacy_odyssey_state_conflict_blocks_before_deleting_state",),
    ),
    DestructiveWriteScenario(
        scenario_id="runtime.activation-atomicity",
        surface=".odylith/runtime/current and .odylith/install.json",
        lifecycle_paths=("install", "reinstall", "upgrade", "rollback"),
        data_at_risk="active runtime pointer, last-known-good runtime, and launcher target",
        unsafe_failure_mode="advance active state before runtime smoke and rollback retention succeed",
        required_guardrail="stage verified runtime first, retain rollback target, then atomically activate",
        proof_markers=("test_upgrade_preserves_host_settings_when_runtime_download_fails",),
    ),
    DestructiveWriteScenario(
        scenario_id="migration.ledger-staleness",
        surface=".odylith/state/migrations",
        lifecycle_paths=("upgrade --dry-run", "upgrade", "doctor"),
        data_at_risk="migration completion truth and idempotency",
        unsafe_failure_mode="treat corrupt or failed-verification ledger as complete",
        required_guardrail="ledger is complete only when present and verification still passes",
        proof_markers=("test_stale_ledger_blocks_normal_upgrade",),
    ),
    DestructiveWriteScenario(
        scenario_id="migration.satisfied-unrecorded",
        surface=".odylith/state/migrations",
        lifecycle_paths=("upgrade --dry-run", "upgrade"),
        data_at_risk="already-clean repo state without durable migration evidence",
        unsafe_failure_mode="rerun destructive migration or report phantom pending migration forever",
        required_guardrail="report satisfied_unrecorded and write a no-op ledger after verification",
        proof_markers=("test_reports_satisfied_unrecorded_when_clean_artifacts_have_no_ledger",),
    ),
    DestructiveWriteScenario(
        scenario_id="repair.lock-cache-sludge",
        surface=".odylith/locks and .odylith/cache",
        lifecycle_paths=("doctor", "doctor --repair", "upgrade"),
        data_at_risk="active lock ownership and incomplete runtime transactions",
        unsafe_failure_mode="delete live locks during release migration or block upgrade on harmless zero-byte files",
        required_guardrail="report sludge as repair-class cleanup only; do not conflate it with release migration",
        proof_markers=("test_lock_cache_sludge_is_reported_without_blocking_release_migration",),
    ),
    DestructiveWriteScenario(
        scenario_id="surface.generated-refresh",
        surface="odylith/* generated dashboard surfaces",
        lifecycle_paths=("upgrade", "dashboard refresh", "sync"),
        data_at_risk="reviewability of repo-owned generated output",
        unsafe_failure_mode="treat generated surface refresh as migration and hide large diffs from operators",
        required_guardrail="keep generated refresh outside migration and report it separately",
        proof_markers=("test_generated_surfaces_stale_are_reported_separately_from_release_migration",),
    ),
)


def destructive_write_scenarios() -> tuple[DestructiveWriteScenario, ...]:
    """Return the destructive-write scenarios every install/migration release gate tracks."""
    return _SCENARIOS


def destructive_write_fixture_matrix(
    *,
    repo_root: str | Path,
    fixture_paths: Sequence[str | Path] | None = None,
) -> dict[str, dict[str, bool]]:
    """Return scenario proof-marker coverage from the repo's test corpus."""
    root = Path(repo_root).expanduser().resolve()
    paths = tuple(Path(path) for path in fixture_paths) if fixture_paths is not None else _default_fixture_paths(root)
    combined = "\n".join((root / path).read_text(encoding="utf-8") for path in paths if (root / path).is_file())
    return {
        scenario.scenario_id: {marker: marker in combined for marker in scenario.proof_markers}
        for scenario in destructive_write_scenarios()
    }


def missing_destructive_write_proofs(
    *,
    repo_root: str | Path,
    fixture_paths: Sequence[str | Path] | None = None,
) -> tuple[str, ...]:
    """Return human-readable missing proof markers for destructive-write scenarios."""
    missing: list[str] = []
    matrix = destructive_write_fixture_matrix(repo_root=repo_root, fixture_paths=fixture_paths)
    for scenario_id, markers in sorted(matrix.items()):
        absent = [marker for marker, present in markers.items() if not present]
        if absent:
            missing.append(f"{scenario_id} proof missing: {', '.join(absent)}")
    return tuple(missing)


def _default_fixture_paths(repo_root: Path) -> tuple[Path, ...]:
    del repo_root
    return (
        Path("tests/unit/install/test_claude_effective_settings.py"),
        Path("tests/unit/install/test_codex_project_assets.py"),
        Path("tests/unit/install/test_migration_runtime.py"),
        Path("tests/integration/install/test_manager.py"),
        Path("tests/unit/install/test_agents.py"),
    )


__all__ = [
    "DestructiveWriteScenario",
    "destructive_write_fixture_matrix",
    "destructive_write_scenarios",
    "missing_destructive_write_proofs",
]
