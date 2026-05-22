"""Authoritative migration planning, ledgers, and release gates for installs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.install.fs import atomic_write_text, display_path
from odylith.install.atlas_box_explanation_migration import (
    MIGRATION_ID as ATLAS_BOX_EXPLANATION_MIGRATION_ID,
    atlas_box_explanation_decision_state,
    inspect_atlas_box_explanation_migration,
    migrate_atlas_box_explanation_contract,
)
from odylith.install.atlas_surface_migration import (
    MIGRATION_ID as ATLAS_SURFACE_MIGRATION_ID,
    atlas_surface_decision_state,
    inspect_atlas_surface_migration,
    migrate_atlas_surface_polish,
)
from odylith.install.legacy_install_migration import (
    LEGACY_ROOT_MIGRATION_ID,
    MigrationSummary as LegacyMigrationSummary,
    legacy_layout_present,
    legacy_migration_conflicts,
    migrate_legacy_install,
)
from odylith.install.destructive_write_scenarios import (
    destructive_write_fixture_matrix,
    destructive_write_scenarios,
    missing_destructive_write_proofs,
)
from odylith.install.lock_hygiene import LOCK_NOTE_THRESHOLD, lock_hygiene_summary
from odylith.install.casebook_metadata_migration import (
    MIGRATION_ID as CASEBOOK_METADATA_MIGRATION_ID,
    STATUS_FSM_MIGRATION_ID as CASEBOOK_STATUS_FSM_MIGRATION_ID,
    casebook_compact_metadata_decision_state,
    casebook_status_fsm_decision_state,
    inspect_casebook_compact_metadata_migration,
    inspect_casebook_status_fsm_migration,
    migrate_casebook_compact_metadata,
    migrate_casebook_status_fsm,
)
from odylith.install.migration_definitions import MigrationDefinition, registered_migration_specs
from odylith.install.migration_observer import (
    SurfaceMigrationObserverReport,
    observe_surface_migration_needs,
)
from odylith.install.runtime import current_runtime_root, current_runtime_version, runtime_verification_evidence
from odylith.install.state import (
    DEFAULT_REPO_SCHEMA_VERSION,
    current_activation_history,
    install_state_path,
    load_install_state,
    load_version_pin,
    version_pin_path,
)
from odylith.install.upgrade_reporting import latest_upgrade_report
from odylith.install.value_engine_migration import (
    MIGRATION_ID as VALUE_ENGINE_MIGRATION_ID,
    inspect_visible_intervention_value_engine_migration,
    migrate_visible_intervention_value_engine,
    record_visible_intervention_value_engine_migration_satisfied,
)
from odylith.install.versioning import is_at_least, is_before, normalize_version, version_key

MIGRATION_LEDGER_SCHEMA_VERSION = "odylith.migration-ledger.v1"
SCENARIO_FIRST_INSTALL = "first_install"
SCENARIO_HEALTHY_PINNED_CONSUMER = "healthy_pinned_consumer"
SCENARIO_ALREADY_CURRENT_CONSUMER = "already_current_consumer"
SCENARIO_PRODUCT_REPO_PINNED_DOGFOOD = "product_repo_pinned_dogfood"
SCENARIO_DETACHED_SOURCE_LOCAL = "detached_source_local"
SCENARIO_MISSING_LAUNCHER = "missing_launcher"
SCENARIO_MISSING_INSTALL_STATE = "missing_install_state"
SCENARIO_STALE_INSTALL_STATE = "stale_install_state"
SCENARIO_LEGACY_ODYSSEY = "legacy_odyssey"
SCENARIO_PARTIAL_FAILED_UPGRADE = "partial_failed_upgrade"
SCENARIO_RELEASE_MIGRATION_REQUIRED = "release_marked_migration_required"
SCENARIO_REPO_SCHEMA_MISMATCH = "repo_schema_mismatch"
SCENARIO_MISSING_INVALID_PIN = "missing_invalid_pin"
SCENARIO_STALE_MIGRATION_LEDGER = "stale_migration_ledger"
SCENARIO_RUNTIME_VERIFICATION_MISSING = "runtime_artifact_verification_missing"
SCENARIO_ROLLBACK_TARGET_MISSING = "rollback_target_missing"
SCENARIO_GENERATED_SURFACE_STALE = "generated_surface_stale_runtime_healthy"
SCENARIO_LOCK_CACHE_SLUDGE = "lock_cache_sludge"

STATE_SELECTED = "selected"
STATE_SKIPPED = "skipped"
STATE_BLOCKED = "blocked"
STATE_SATISFIED_UNRECORDED = "satisfied_unrecorded"
STATE_LEDGER_STALE = "ledger_stale"
STATE_APPLIED = "applied"
STATE_REPAIR_REQUIRED = "repair_required"

PRODUCT_REPO_ROLE = "product_repo"
CONSUMER_REPO_ROLE = "consumer_repo"
_SOURCE_LOCAL = "source-local"
@dataclass(frozen=True)
class RepoMigrationScenario:
    """Structured repo state used by migration plans and reports."""

    scenario: str
    reasons: tuple[str, ...]
    state: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        """Return the scenario as a JSON-ready payload."""
        return {
            "scenario": self.scenario,
            "reasons": list(self.reasons),
            "state": dict(self.state),
        }


@dataclass(frozen=True)
class MigrationDecision:
    """A selected, skipped, or blocked migration decision."""

    migration_id: str
    state: str
    reason: str
    ledger_path: str
    planned_paths: tuple[str, ...]
    rollback_scope: str
    validation_commands: tuple[str, ...]
    evidence: dict[str, object]

    def blocks_upgrade(self) -> bool:
        """Return whether this decision prevents normal release mutation."""
        return self.state in {STATE_BLOCKED, STATE_LEDGER_STALE}

    def needs_apply(self) -> bool:
        """Return whether upgrade apply must execute this decision."""
        return self.state in {STATE_SELECTED, STATE_SATISFIED_UNRECORDED}

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-ready decision payload."""
        return {
            "migration_id": self.migration_id,
            "state": self.state,
            "reason": self.reason,
            "ledger_path": self.ledger_path,
            "planned_paths": list(self.planned_paths),
            "rollback_scope": self.rollback_scope,
            "validation_commands": list(self.validation_commands),
            "evidence": dict(self.evidence),
        }


@dataclass(frozen=True)
class MigrationPlan:
    """Migration transaction plan shared by dry-run and apply."""

    repo_root: Path
    previous_version: str
    target_version: str
    repo_schema_version: int
    scenario: RepoMigrationScenario
    selected: tuple[MigrationDecision, ...]
    skipped: tuple[MigrationDecision, ...]
    blocked: tuple[MigrationDecision, ...]
    release_manifest_migration_required: bool
    no_op: bool
    plan_fingerprint: str

    @property
    def decisions(self) -> tuple[MigrationDecision, ...]:
        """Return every migration decision in operator order."""
        return (*self.selected, *self.blocked, *self.skipped)

    @property
    def blocked_reason(self) -> str:
        """Return the first blocking reason, if any."""
        reasons: list[str] = []
        seen: set[str] = set()
        for decision in self.blocked:
            reason = str(decision.reason or "").strip()
            if not reason or reason in seen:
                continue
            seen.add(reason)
            reasons.append(reason)
        return "; ".join(reasons)

    @property
    def ledger_state(self) -> dict[str, str]:
        """Return migration-id to decision-state ledger summary."""
        return {decision.migration_id: decision.state for decision in self.decisions}

    @property
    def migration_ids(self) -> tuple[str, ...]:
        """Return migration IDs that either apply or block the transaction."""
        return tuple(
            decision.migration_id
            for decision in (*self.selected, *self.blocked)
            if decision.migration_id
        )

    def satisfies_manifest_requirement(self) -> bool:
        """Return whether a migration_required release has a registered plan path."""
        if not self.release_manifest_migration_required:
            return True
        return any(
            _decision_satisfies_manifest_requirement(
                decision,
                previous_version=self.previous_version,
                target_version=self.target_version,
            )
            for decision in self.decisions
        )

    def as_dict(self) -> dict[str, object]:
        """Return the plan as a JSON-ready payload."""
        return {
            "schema_version": "odylith.migration-plan.v1",
            "scenario": self.scenario.as_dict(),
            "previous_version": self.previous_version,
            "target_version": self.target_version,
            "repo_schema_version": self.repo_schema_version,
            "selected": [decision.as_dict() for decision in self.selected],
            "skipped": [decision.as_dict() for decision in self.skipped],
            "blocked": [decision.as_dict() for decision in self.blocked],
            "ledger_state": dict(self.ledger_state),
            "no_op": self.no_op,
            "release_manifest_migration_required": self.release_manifest_migration_required,
            "satisfies_manifest_requirement": self.satisfies_manifest_requirement(),
            "blocked_reason": self.blocked_reason,
            "plan_fingerprint": self.plan_fingerprint,
        }


@dataclass(frozen=True)
class MigrationResult:
    """Migration apply result emitted into upgrade reports and ledgers."""

    migration_id: str
    state: str
    reason: str
    written_paths: tuple[str, ...]
    removed_paths: tuple[str, ...]
    ledger_path: str
    verification_result: dict[str, object]
    follow_up_repair_advice: str = ""
    legacy_summary: LegacyMigrationSummary | None = None

    def as_dict(self) -> dict[str, object]:
        """Return the result as a JSON-ready payload."""
        return {
            "schema_version": MIGRATION_LEDGER_SCHEMA_VERSION,
            "migration_id": self.migration_id,
            "state": self.state,
            "reason": self.reason,
            "written_paths": list(self.written_paths),
            "removed_paths": list(self.removed_paths),
            "ledger_path": self.ledger_path,
            "verification_result": dict(self.verification_result),
            "follow_up_repair_advice": self.follow_up_repair_advice,
        }


@dataclass(frozen=True)
class ReleaseMigrationGateReport:
    """Release gate report for migration registry coverage."""

    ok: bool
    registered_migrations: tuple[MigrationDefinition, ...]
    covered_version_ranges: tuple[str, ...]
    fixture_matrix: dict[str, dict[str, bool]]
    destructive_write_matrix: dict[str, dict[str, bool]]
    surface_migration_observer: SurfaceMigrationObserverReport
    blocked_manual_migrations: tuple[str, ...]
    ungated_lifecycle_paths: tuple[str, ...]
    notes: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        """Return the report as a JSON-ready payload."""
        return {
            "schema_version": "odylith.release-migration-gate.v1",
            "ok": self.ok,
            "registered_migrations": [definition.as_dict() for definition in self.registered_migrations],
            "covered_version_ranges": list(self.covered_version_ranges),
            "fixture_matrix": dict(self.fixture_matrix),
            "destructive_write_scenarios": [scenario.as_dict() for scenario in destructive_write_scenarios()],
            "destructive_write_matrix": dict(self.destructive_write_matrix),
            "surface_migration_observer": self.surface_migration_observer.as_dict(),
            "blocked_manual_migrations": list(self.blocked_manual_migrations),
            "ungated_lifecycle_paths": list(self.ungated_lifecycle_paths),
            "notes": list(self.notes),
        }


def _is_source_local(value: object) -> bool:
    return str(value or "").strip().lower() == _SOURCE_LOCAL


def _decision_satisfies_manifest_requirement(
    decision: "MigrationDecision",
    *,
    previous_version: str,
    target_version: str,
) -> bool:
    if not decision.migration_id or decision.migration_id.startswith("repo-state:"):
        return False
    try:
        definition = _definition_for(decision.migration_id)
    except KeyError:
        return False
    if not _definition_covers_manifest_target(definition, target_version):
        return False
    if decision.state in {STATE_SELECTED, STATE_SATISFIED_UNRECORDED}:
        return True
    if decision.state != STATE_SKIPPED:
        return False
    crosses_introduced_version = not normalize_version(previous_version) or is_before(
        previous_version,
        definition.introduced_version,
    )
    return crosses_introduced_version and "target window" not in decision.reason


def _definition_covers_manifest_target(definition: MigrationDefinition, target_version: str) -> bool:
    """Return whether a registered migration can satisfy a migration-required release.

    Runtime inspections may still select historical repair migrations when a later
    release encounters stale repo state. That does not mean the later release has a
    registered migration contract of its own. Manifest satisfaction is intentionally
    limited to the release train that introduced the migration so a future
    migration_required release cannot activate because an older repair happened to
    run.
    """
    target = normalize_version(target_version)
    introduced = normalize_version(definition.introduced_version)
    if not target or not introduced or not is_at_least(target, introduced):
        return False
    target_key = version_key(target)
    introduced_key = version_key(introduced)
    return target_key[:2] == introduced_key[:2]


def registered_migrations() -> tuple[MigrationDefinition, ...]:
    """Return every release migration known to the migration runtime."""
    return tuple(MigrationDefinition(**spec) for spec in registered_migration_specs())


def classify_repo_migration_scenario(
    *,
    repo_root: str | Path,
    repo_role: str = "",
    active_version: str = "",
    pinned_version: str = "",
    target_version: str = "",
    source_repo: bool = False,
    state: Mapping[str, object] | None = None,
    release_manifest: Mapping[str, object] | None = None,
    runtime_root: str | Path | None = None,
    runtime_verification: Mapping[str, object] | None = None,
) -> RepoMigrationScenario:
    """Classify repo migration state once for every lifecycle surface."""
    root = Path(repo_root).expanduser().resolve()
    loaded_state = dict(state if state is not None else load_install_state(repo_root=root))
    runtime = Path(runtime_root).expanduser().resolve() if runtime_root is not None else current_runtime_root(repo_root=root)
    observed_active = normalize_version(active_version or current_runtime_version(repo_root=root) or loaded_state.get("active_version"))
    pin_exists = version_pin_path(repo_root=root).is_file()
    pin = load_version_pin(repo_root=root, fallback_version=None)
    observed_pin = normalize_version(pinned_version or (pin.odylith_version if pin is not None and pin_exists else ""))
    target = normalize_version(target_version)
    manifest = dict(release_manifest or {})
    launcher_exists = (root / ".odylith" / "bin" / "odylith").is_file()
    state_exists = install_state_path(repo_root=root).is_file()
    verification = (
        {str(key): value for key, value in runtime_verification.items()}
        if runtime_verification is not None
        else (runtime_verification_evidence(runtime) if runtime is not None else {})
    )
    activation_history = current_activation_history(loaded_state)
    rollback_target = next((item for item in reversed(activation_history[:-1]) if item and item != observed_active), "")
    lock_summary = lock_hygiene_summary(repo_root=root)
    generated_surface_stale = _generated_surfaces_stale(repo_root=root)
    reasons: list[str] = []
    scenario = SCENARIO_HEALTHY_PINNED_CONSUMER

    if legacy_layout_present(repo_root=root):
        scenario = SCENARIO_LEGACY_ODYSSEY
        reasons.append("legacy odyssey/.odyssey root is present")
    elif (
        source_repo
        or _is_source_local(target)
        or _is_source_local(observed_pin)
        or (
            _is_source_local(observed_active)
            and str(repo_role or "").strip() != PRODUCT_REPO_ROLE
        )
    ):
        scenario = SCENARIO_DETACHED_SOURCE_LOCAL
        reasons.append("source-local maintainer runtime is active or requested")
    elif not (root / "odylith").exists() and not state_exists:
        scenario = SCENARIO_FIRST_INSTALL
        reasons.append("no installed Odylith product tree or install state found")
    elif not pin_exists or not observed_pin:
        scenario = SCENARIO_MISSING_INVALID_PIN
        reasons.append("tracked product-version pin is missing or invalid")
    elif not state_exists:
        scenario = SCENARIO_MISSING_INSTALL_STATE
        reasons.append("Odylith starter tree exists but .odylith/install.json is missing")
    elif not launcher_exists:
        scenario = SCENARIO_MISSING_LAUNCHER
        reasons.append("repo-local launcher is missing")
    elif observed_active and str(loaded_state.get("active_version") or "").strip() and observed_active != normalize_version(loaded_state.get("active_version")):
        scenario = SCENARIO_STALE_INSTALL_STATE
        reasons.append("live runtime pointer and install state active version disagree")
    elif _latest_upgrade_failed(repo_root=root, state=loaded_state):
        scenario = SCENARIO_PARTIAL_FAILED_UPGRADE
        reasons.append("install state records a failed upgrade phase")
    elif int(manifest.get("repo_schema_version") or DEFAULT_REPO_SCHEMA_VERSION) != DEFAULT_REPO_SCHEMA_VERSION:
        scenario = SCENARIO_REPO_SCHEMA_MISMATCH
        reasons.append("target release repo_schema_version differs from this runtime contract")
    elif str(repo_role or "").strip() == PRODUCT_REPO_ROLE:
        scenario = SCENARIO_PRODUCT_REPO_PINNED_DOGFOOD
        if _is_source_local(observed_active) and target and not _is_source_local(target):
            reasons.append("Odylith product repo is realigning detached source-local runtime to the pinned release target")
        else:
            reasons.append("Odylith product repo is using pinned dogfood posture")
    elif bool(manifest.get("migration_required")):
        scenario = SCENARIO_RELEASE_MIGRATION_REQUIRED
        reasons.append("target release manifest declares migration_required=true")
    elif runtime is not None and not verification and observed_active:
        scenario = SCENARIO_RUNTIME_VERIFICATION_MISSING
        reasons.append("runtime artifact exists but verification evidence is missing")
    elif target and observed_active == target and observed_pin == target:
        scenario = SCENARIO_ALREADY_CURRENT_CONSUMER
        reasons.append("active runtime and tracked pin already match the resolved target")
    elif observed_active and not rollback_target and target and observed_active != target and current_runtime_root(repo_root=root) is None:
        scenario = SCENARIO_ROLLBACK_TARGET_MISSING
        reasons.append("upgrade would replace the active runtime but no rollback target is retained")
    elif lock_summary.zero_byte_files >= LOCK_NOTE_THRESHOLD:
        scenario = SCENARIO_LOCK_CACHE_SLUDGE
        reasons.append("lock/cache sludge is present; release migration remains separate from repair cleanup")
    elif generated_surface_stale and observed_active:
        scenario = SCENARIO_GENERATED_SURFACE_STALE
        reasons.append("generated dashboard surfaces are stale or missing, but runtime state is otherwise healthy")

    state_payload = {
        "active_version": observed_active,
        "pinned_version": observed_pin,
        "target_version": target,
        "repo_role": str(repo_role or "").strip() or CONSUMER_REPO_ROLE,
        "pin_exists": pin_exists,
        "launcher_exists": launcher_exists,
        "install_state_exists": state_exists,
        "runtime_root": str(runtime) if runtime is not None else "",
        "runtime_verification_present": bool(verification),
        "rollback_target": rollback_target,
        "migration_required": bool(manifest.get("migration_required")),
        "lock_files": lock_summary.total_files,
        "zero_byte_lock_files": lock_summary.zero_byte_files,
        "generated_surface_stale": generated_surface_stale,
    }
    return RepoMigrationScenario(
        scenario=scenario,
        reasons=tuple(reasons or ("repo state is compatible with normal migration planning",)),
        state=state_payload,
    )


def _definition_for(migration_id: str) -> MigrationDefinition:
    for definition in registered_migrations():
        if definition.migration_id == migration_id:
            return definition
    raise KeyError(migration_id)


def _latest_upgrade_failed(*, repo_root: Path, state: Mapping[str, object]) -> bool:
    if str(state.get("last_upgrade_status") or "").strip().lower() == "failed":
        return True
    latest_report = latest_upgrade_report(repo_root=repo_root)
    if latest_report is None:
        return False
    _, report = latest_report
    return str(report.get("status") or "").strip().lower() == "failed"


def _fingerprint_plan_payload(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _decision(
    *,
    migration_id: str,
    state: str,
    reason: str,
    ledger_path: str,
    planned_paths: Sequence[str],
    evidence: Mapping[str, object],
) -> MigrationDecision:
    definition = _definition_for(migration_id)
    return MigrationDecision(
        migration_id=migration_id,
        state=state,
        reason=reason,
        ledger_path=ledger_path,
        planned_paths=tuple(str(path).strip() for path in planned_paths if str(path).strip()),
        rollback_scope=definition.rollback_scope,
        validation_commands=definition.validation_commands,
        evidence={str(key): value for key, value in evidence.items()},
    )


def _repo_state_decision(
    *,
    migration_id: str,
    state: str,
    reason: str,
    planned_paths: Sequence[str],
    evidence: Mapping[str, object],
    rollback_scope: str = "",
    validation_commands: Sequence[str] = (),
    ledger_path: str = "",
) -> MigrationDecision:
    return MigrationDecision(
        migration_id=migration_id,
        state=state,
        reason=reason,
        ledger_path=ledger_path,
        planned_paths=tuple(str(path).strip() for path in planned_paths if str(path).strip()),
        rollback_scope=str(rollback_scope or "").strip(),
        validation_commands=tuple(str(command).strip() for command in validation_commands if str(command).strip()),
        evidence={str(key): value for key, value in evidence.items()},
    )


def _generated_surfaces_stale(*, repo_root: Path) -> bool:
    required = (
        "odylith/index.html",
        "odylith/radar/radar.html",
        "odylith/compass/compass.html",
        "odylith/registry/registry.html",
        "odylith/casebook/casebook.html",
        "odylith/atlas/atlas.html",
    )
    return any(not (repo_root / path).is_file() for path in required)


def _legacy_root_decision(*, repo_root: Path, scenario: RepoMigrationScenario) -> MigrationDecision:
    definition = _definition_for(LEGACY_ROOT_MIGRATION_ID)
    ledger_path = ".odylith/state/migrations/legacy-odyssey-root-migration.v1.json"
    if scenario.scenario != SCENARIO_LEGACY_ODYSSEY:
        return MigrationDecision(
            migration_id=LEGACY_ROOT_MIGRATION_ID,
            state=STATE_SKIPPED,
            reason="legacy odyssey roots are not present",
            ledger_path=ledger_path,
            planned_paths=definition.write_set,
            rollback_scope=definition.rollback_scope,
            validation_commands=definition.validation_commands,
            evidence={"legacy_layout_present": False},
        )
    conflicts = legacy_migration_conflicts(repo_root=repo_root)
    if conflicts:
        return MigrationDecision(
            migration_id=LEGACY_ROOT_MIGRATION_ID,
            state=STATE_BLOCKED,
            reason="legacy odyssey migration would overwrite existing Odylith paths: " + ", ".join(conflicts),
            ledger_path=ledger_path,
            planned_paths=definition.write_set,
            rollback_scope=definition.rollback_scope,
            validation_commands=definition.validation_commands,
            evidence={"legacy_layout_present": True, "conflicts": list(conflicts)},
        )
    return MigrationDecision(
        migration_id=LEGACY_ROOT_MIGRATION_ID,
        state=STATE_SELECTED,
        reason="legacy odyssey/.odyssey roots must migrate before runtime activation",
        ledger_path=ledger_path,
        planned_paths=definition.write_set,
        rollback_scope=definition.rollback_scope,
        validation_commands=definition.validation_commands,
        evidence={"legacy_layout_present": legacy_layout_present(repo_root=repo_root)},
    )


def _scenario_blockers(scenario: RepoMigrationScenario) -> tuple[MigrationDecision, ...]:
    state = scenario.state
    scenario_id = scenario.scenario
    repair_command = "./.odylith/bin/odylith doctor --repo-root . --repair"
    blocks: dict[str, tuple[str, tuple[str, ...], str]] = {
        SCENARIO_MISSING_INVALID_PIN: (
            "repo pin is missing or invalid; run `odylith install --repo-root .`, `odylith doctor --repo-root . --repair`, or `odylith upgrade --to X.Y.Z --write-pin`",
            ("odylith/runtime/source/product-version.v1.json",),
            "pin repair only; release migration must wait for a valid tracked target",
        ),
        SCENARIO_MISSING_INSTALL_STATE: (
            f"install state is missing; repair with `{repair_command}` before release migration",
            (".odylith/install.json",),
            "install-state repair only",
        ),
        SCENARIO_MISSING_LAUNCHER: (
            f"repo-local launcher is missing; repair with `{repair_command}` before release migration",
            (".odylith/bin/odylith", ".odylith/bin/odylith-bootstrap"),
            "launcher repair only",
        ),
        SCENARIO_STALE_INSTALL_STATE: (
            f"live runtime pointer and install state disagree; repair with `{repair_command}` before release migration",
            (".odylith/install.json", ".odylith/runtime/current"),
            "runtime pointer repair only",
        ),
        SCENARIO_PARTIAL_FAILED_UPGRADE: (
            "previous upgrade failed; inspect the last upgrade report and choose resume or rollback before release migration",
            (".odylith/install.json", ".odylith/runtime/logs/"),
            "resume or rollback prior transaction before a new release migration",
        ),
        SCENARIO_REPO_SCHEMA_MISMATCH: (
            "target release repo_schema_version does not match this runtime contract",
            ("odylith/runtime/source/product-version.v1.json",),
            "schema migration must be registered before release activation",
        ),
        SCENARIO_RUNTIME_VERIFICATION_MISSING: (
            f"runtime artifact verification evidence is missing; repair with `{repair_command}` before release migration",
            (".odylith/runtime/current", ".odylith/runtime/versions/"),
            "runtime verification repair only",
        ),
        SCENARIO_ROLLBACK_TARGET_MISSING: (
            "upgrade would replace the active runtime but no rollback target is retained",
            (".odylith/install.json", ".odylith/runtime/versions/"),
            "retain a valid rollback target before activation",
        ),
    }
    if scenario_id not in blocks:
        return ()
    reason, paths, rollback_scope = blocks[scenario_id]
    return (
        _repo_state_decision(
            migration_id=f"repo-state:{scenario_id}",
            state=STATE_BLOCKED,
            reason=reason,
            planned_paths=paths,
            rollback_scope=rollback_scope,
            validation_commands=("PYTHONPATH=src python -m pytest -q tests/unit/install/test_migration_runtime.py",),
            evidence=state,
        ),
    )


def _value_engine_decision(
    *,
    repo_root: Path,
    previous_version: str,
    target_version: str,
    runtime_root: Path | None,
    scenario: RepoMigrationScenario,
) -> MigrationDecision:
    inspection = inspect_visible_intervention_value_engine_migration(
        repo_root=repo_root,
        previous_version=previous_version,
        target_version=target_version,
        runtime_root=runtime_root,
    )
    evidence = inspection.as_dict()
    if scenario.scenario == SCENARIO_LEGACY_ODYSSEY:
        return _decision(
            migration_id=VALUE_ENGINE_MIGRATION_ID,
            state=STATE_SELECTED if inspection.target_in_window else STATE_SKIPPED,
            reason=(
                "value-engine migration runs after the legacy root migration"
                if inspection.target_in_window
                else "target version is not in target window for the v0.1.11 value-engine migration"
            ),
            ledger_path=inspection.ledger_path,
            planned_paths=inspection.planned_paths,
            evidence=evidence,
        )
    if scenario.scenario == SCENARIO_DETACHED_SOURCE_LOCAL:
        return _decision(
            migration_id=VALUE_ENGINE_MIGRATION_ID,
            state=STATE_BLOCKED,
            reason="release migrations are blocked while the product repo is in detached source-local posture",
            ledger_path=inspection.ledger_path,
            planned_paths=inspection.planned_paths,
            evidence=evidence,
        )
    if scenario.scenario == SCENARIO_PRODUCT_REPO_PINNED_DOGFOOD:
        return _decision(
            migration_id=VALUE_ENGINE_MIGRATION_ID,
            state=STATE_SKIPPED,
            reason="product repo source truth is validated by maintainer release gates, not consumer release migration apply",
            ledger_path=inspection.ledger_path,
            planned_paths=inspection.planned_paths,
            evidence=evidence,
        )
    if not inspection.target_in_window:
        return _decision(
            migration_id=VALUE_ENGINE_MIGRATION_ID,
            state=STATE_SKIPPED,
            reason="target version is not in target window for the v0.1.11 value-engine migration",
            ledger_path=inspection.ledger_path,
            planned_paths=inspection.planned_paths,
            evidence=evidence,
        )
    if inspection.ledger_exists and not inspection.ledger_valid:
        return _decision(
            migration_id=VALUE_ENGINE_MIGRATION_ID,
            state=STATE_LEDGER_STALE,
            reason=f"migration ledger is stale: {inspection.ledger_stale_reason}",
            ledger_path=inspection.ledger_path,
            planned_paths=inspection.planned_paths,
            evidence=evidence,
        )
    if inspection.ledger_exists and inspection.verification_passed:
        return _decision(
            migration_id=VALUE_ENGINE_MIGRATION_ID,
            state=STATE_SKIPPED,
            reason="ledger and verification already satisfy the v0.1.11 value-engine migration",
            ledger_path=inspection.ledger_path,
            planned_paths=inspection.planned_paths,
            evidence=evidence,
        )
    if inspection.ledger_exists and inspection.ledger_valid and not inspection.verification_passed:
        if inspection.target_in_window and (inspection.legacy_artifacts_present or not inspection.value_corpus_present):
            return _decision(
                migration_id=VALUE_ENGINE_MIGRATION_ID,
                state=STATE_SELECTED,
                reason="valid migration ledger exists, but owned value-engine artifacts need repair",
                ledger_path=inspection.ledger_path,
                planned_paths=inspection.planned_paths,
                evidence=evidence,
            )
        return _decision(
            migration_id=VALUE_ENGINE_MIGRATION_ID,
            state=STATE_LEDGER_STALE,
            reason="migration ledger exists, but value-engine verification no longer passes",
            ledger_path=inspection.ledger_path,
            planned_paths=inspection.planned_paths,
            evidence=evidence,
        )
    if inspection.legacy_artifacts_present or (inspection.previous_requires_migration and not inspection.value_corpus_present):
        return _decision(
            migration_id=VALUE_ENGINE_MIGRATION_ID,
            state=STATE_SELECTED,
            reason="legacy artifacts or missing value-engine corpus require automatic migration",
            ledger_path=inspection.ledger_path,
            planned_paths=inspection.planned_paths,
            evidence=evidence,
        )
    if inspection.previous_requires_migration and not inspection.ledger_exists:
        return _decision(
            migration_id=VALUE_ENGINE_MIGRATION_ID,
            state=STATE_SATISFIED_UNRECORDED,
            reason="target artifacts are already clean, but the migration ledger is missing",
            ledger_path=inspection.ledger_path,
            planned_paths=inspection.planned_paths,
            evidence=evidence,
        )
    return _decision(
        migration_id=VALUE_ENGINE_MIGRATION_ID,
        state=STATE_SKIPPED,
        reason="migration predicates do not require local state changes",
        ledger_path=inspection.ledger_path,
        planned_paths=inspection.planned_paths,
        evidence=evidence,
    )


def _casebook_metadata_decision(
    *,
    repo_root: Path,
    previous_version: str,
    target_version: str,
    scenario: RepoMigrationScenario,
) -> MigrationDecision:
    inspection = inspect_casebook_compact_metadata_migration(
        repo_root=repo_root,
        previous_version=previous_version,
        target_version=target_version,
    )
    state, reason = casebook_compact_metadata_decision_state(
        repo_scenario=scenario.scenario,
        inspection=inspection,
    )
    return _decision(
        migration_id=CASEBOOK_METADATA_MIGRATION_ID,
        state=state,
        reason=reason,
        ledger_path=inspection.ledger_path,
        planned_paths=inspection.planned_paths,
        evidence=inspection.as_dict(),
    )


def _casebook_status_fsm_decision(
    *,
    repo_root: Path,
    previous_version: str,
    target_version: str,
    scenario: RepoMigrationScenario,
) -> MigrationDecision:
    inspection = inspect_casebook_status_fsm_migration(
        repo_root=repo_root,
        previous_version=previous_version,
        target_version=target_version,
    )
    state, reason = casebook_status_fsm_decision_state(
        repo_scenario=scenario.scenario,
        inspection=inspection,
    )
    return _decision(
        migration_id=CASEBOOK_STATUS_FSM_MIGRATION_ID,
        state=state,
        reason=reason,
        ledger_path=inspection.ledger_path,
        planned_paths=inspection.planned_paths,
        evidence=inspection.as_dict(),
    )


def _atlas_surface_decision(
    *,
    repo_root: Path,
    previous_version: str,
    target_version: str,
    scenario: RepoMigrationScenario,
) -> MigrationDecision:
    inspection = inspect_atlas_surface_migration(
        repo_root=repo_root,
        previous_version=previous_version,
        target_version=target_version,
    )
    state, reason = atlas_surface_decision_state(
        repo_scenario=scenario.scenario,
        inspection=inspection,
    )
    return _decision(
        migration_id=ATLAS_SURFACE_MIGRATION_ID,
        state=state,
        reason=reason,
        ledger_path=inspection.ledger_path,
        planned_paths=inspection.planned_paths,
        evidence=inspection.as_dict(),
    )


def _atlas_box_explanation_decision(
    *,
    repo_root: Path,
    previous_version: str,
    target_version: str,
    scenario: RepoMigrationScenario,
) -> MigrationDecision:
    inspection = inspect_atlas_box_explanation_migration(
        repo_root=repo_root,
        previous_version=previous_version,
        target_version=target_version,
    )
    state, reason = atlas_box_explanation_decision_state(
        repo_scenario=scenario.scenario,
        inspection=inspection,
    )
    return _decision(
        migration_id=ATLAS_BOX_EXPLANATION_MIGRATION_ID,
        state=state,
        reason=reason,
        ledger_path=inspection.ledger_path,
        planned_paths=inspection.planned_paths,
        evidence=inspection.as_dict(),
    )


def _repo_schema_from_manifest(manifest: Mapping[str, object]) -> int:
    try:
        return int(manifest.get("repo_schema_version") or DEFAULT_REPO_SCHEMA_VERSION)
    except (TypeError, ValueError):
        return DEFAULT_REPO_SCHEMA_VERSION


def plan_release_migrations(
    *,
    repo_root: str | Path,
    repo_role: str = "",
    active_version: str = "",
    previous_version: str = "",
    target_version: str = "",
    runtime_root: str | Path | None = None,
    release_manifest: Mapping[str, object] | None = None,
    source_repo: bool = False,
    state: Mapping[str, object] | None = None,
    pinned_version: str = "",
    runtime_verification: Mapping[str, object] | None = None,
) -> MigrationPlan:
    """Build one authoritative migration plan for dry-run and apply."""
    root = Path(repo_root).expanduser().resolve()
    runtime = Path(runtime_root).expanduser().resolve() if runtime_root is not None else current_runtime_root(repo_root=root)
    manifest = dict(release_manifest or {})
    target = normalize_version(target_version)
    previous = normalize_version(previous_version)
    scenario = classify_repo_migration_scenario(
        repo_root=root,
        repo_role=repo_role,
        active_version=active_version,
        pinned_version=pinned_version,
        target_version=target,
        source_repo=source_repo,
        state=state,
        release_manifest=manifest,
        runtime_root=runtime,
        runtime_verification=runtime_verification,
    )
    decisions = [
        _legacy_root_decision(repo_root=root, scenario=scenario),
        *_scenario_blockers(scenario),
        _value_engine_decision(repo_root=root, previous_version=previous, target_version=target, runtime_root=runtime, scenario=scenario),
        _casebook_metadata_decision(repo_root=root, previous_version=previous, target_version=target, scenario=scenario),
        _casebook_status_fsm_decision(repo_root=root, previous_version=previous, target_version=target, scenario=scenario),
        _atlas_surface_decision(repo_root=root, previous_version=previous, target_version=target, scenario=scenario),
        _atlas_box_explanation_decision(repo_root=root, previous_version=previous, target_version=target, scenario=scenario),
    ]
    selected = tuple(decision for decision in decisions if decision.needs_apply())
    blocked = [decision for decision in decisions if decision.blocks_upgrade()]
    skipped = tuple(decision for decision in decisions if decision.state == STATE_SKIPPED)
    if any(decision.state == STATE_LEDGER_STALE for decision in decisions):
        scenario = RepoMigrationScenario(
            scenario=SCENARIO_STALE_MIGRATION_LEDGER,
            reasons=("one or more migration ledgers exist but no longer verify",),
            state=scenario.state,
        )
    if (
        scenario.scenario != SCENARIO_PRODUCT_REPO_PINNED_DOGFOOD
        and bool(manifest.get("migration_required"))
        and not any(
            _decision_satisfies_manifest_requirement(
                decision,
                previous_version=previous,
                target_version=target,
            )
            for decision in decisions
        )
    ):
        blocked.append(
            _repo_state_decision(
                migration_id="release:migration-required",
                state=STATE_BLOCKED,
                reason="release manifest declares migration_required=true, but no registered migration satisfies the target release",
                planned_paths=("odylith/runtime/source/product-version.v1.json",),
                rollback_scope="release activation must wait for a registered migration target",
                evidence={"migration_required": True, "target_version": target},
            )
        )
    plan_payload = {
        "repo_root": str(root),
        "previous_version": previous,
        "target_version": target,
        "repo_schema_version": _repo_schema_from_manifest(manifest),
        "scenario": scenario.as_dict(),
        "selected": [decision.as_dict() for decision in selected],
        "blocked": [decision.as_dict() for decision in blocked],
        "skipped": [decision.as_dict() for decision in skipped],
    }
    return MigrationPlan(
        repo_root=root,
        previous_version=previous,
        target_version=target,
        repo_schema_version=_repo_schema_from_manifest(manifest),
        scenario=scenario,
        selected=selected,
        skipped=skipped,
        blocked=tuple(blocked),
        release_manifest_migration_required=bool(manifest.get("migration_required")),
        no_op=not selected and not blocked,
        plan_fingerprint=_fingerprint_plan_payload(plan_payload),
    )


def apply_release_migrations(*, plan: MigrationPlan, runtime_root: str | Path | None = None) -> tuple[MigrationResult, ...]:
    """Apply the selected migration decisions from a dry-run-equivalent plan."""
    if plan.blocked:
        raise ValueError(plan.blocked_reason)
    runtime = Path(runtime_root).expanduser().resolve() if runtime_root is not None else current_runtime_root(repo_root=plan.repo_root)
    results: list[MigrationResult] = []
    for decision in plan.selected:
        if decision.migration_id == LEGACY_ROOT_MIGRATION_ID:
            summary = migrate_legacy_install(repo_root=plan.repo_root)
            ledger_path = _write_legacy_root_ledger(plan=plan, decision=decision, summary=summary)
            results.append(
                MigrationResult(
                    migration_id=decision.migration_id,
                    state=STATE_APPLIED if not summary.already_migrated else STATE_SKIPPED,
                    reason=decision.reason if not summary.already_migrated else "legacy odyssey roots are already migrated",
                    written_paths=summary.moved_paths,
                    removed_paths=summary.removed_paths,
                    ledger_path=ledger_path,
                    verification_result={"status": "passed", "legacy_layout_present": legacy_layout_present(repo_root=plan.repo_root)},
                    legacy_summary=summary,
                )
            )
            continue
        if decision.migration_id == CASEBOOK_METADATA_MIGRATION_ID:
            casebook_result = migrate_casebook_compact_metadata(
                repo_root=plan.repo_root,
                previous_version=plan.previous_version,
                target_version=plan.target_version,
            )
            results.append(
                MigrationResult(
                    migration_id=casebook_result.migration_id,
                    state=STATE_APPLIED if casebook_result.applied else STATE_SKIPPED,
                    reason=casebook_result.skipped_reason,
                    written_paths=casebook_result.written_paths,
                    removed_paths=casebook_result.removed_paths,
                    ledger_path=casebook_result.ledger_path,
                    verification_result=dict(casebook_result.verification_result or {"status": "skipped"}),
                )
            )
            continue
        if decision.migration_id == CASEBOOK_STATUS_FSM_MIGRATION_ID:
            casebook_result = migrate_casebook_status_fsm(
                repo_root=plan.repo_root,
                previous_version=plan.previous_version,
                target_version=plan.target_version,
            )
            results.append(
                MigrationResult(
                    migration_id=casebook_result.migration_id,
                    state=STATE_APPLIED if casebook_result.applied else STATE_SKIPPED,
                    reason=casebook_result.skipped_reason,
                    written_paths=casebook_result.written_paths,
                    removed_paths=casebook_result.removed_paths,
                    ledger_path=casebook_result.ledger_path,
                    verification_result=dict(casebook_result.verification_result or {"status": "skipped"}),
                )
            )
            continue
        if decision.migration_id == ATLAS_SURFACE_MIGRATION_ID:
            atlas_result = migrate_atlas_surface_polish(
                repo_root=plan.repo_root,
                previous_version=plan.previous_version,
                target_version=plan.target_version,
            )
            results.append(
                MigrationResult(
                    migration_id=atlas_result.migration_id,
                    state=STATE_APPLIED if atlas_result.applied else STATE_SKIPPED,
                    reason=atlas_result.skipped_reason,
                    written_paths=atlas_result.written_paths,
                    removed_paths=atlas_result.removed_paths,
                    ledger_path=atlas_result.ledger_path,
                    verification_result=dict(atlas_result.verification_result or {"status": "skipped"}),
                )
            )
            continue
        if decision.migration_id == ATLAS_BOX_EXPLANATION_MIGRATION_ID:
            atlas_result = migrate_atlas_box_explanation_contract(
                repo_root=plan.repo_root,
                previous_version=plan.previous_version,
                target_version=plan.target_version,
            )
            results.append(
                MigrationResult(
                    migration_id=atlas_result.migration_id,
                    state=STATE_APPLIED if atlas_result.applied else STATE_SKIPPED,
                    reason=atlas_result.skipped_reason,
                    written_paths=atlas_result.written_paths,
                    removed_paths=atlas_result.removed_paths,
                    ledger_path=atlas_result.ledger_path,
                    verification_result=dict(atlas_result.verification_result or {"status": "skipped"}),
                )
            )
            continue
        if decision.migration_id != VALUE_ENGINE_MIGRATION_ID:
            raise ValueError(f"no applier registered for migration {decision.migration_id}")
        if decision.state == STATE_SATISFIED_UNRECORDED:
            value_result = record_visible_intervention_value_engine_migration_satisfied(
                repo_root=plan.repo_root,
                previous_version=plan.previous_version,
                target_version=plan.target_version,
                runtime_root=runtime,
                repo_scenario=plan.scenario.scenario,
                plan_fingerprint=plan.plan_fingerprint,
            )
            results.append(
                MigrationResult(
                    migration_id=value_result.migration_id,
                    state=STATE_SATISFIED_UNRECORDED,
                    reason=value_result.skipped_reason,
                    written_paths=(),
                    removed_paths=(),
                    ledger_path=value_result.ledger_path,
                    verification_result={"status": "passed", "mode": STATE_SATISFIED_UNRECORDED},
                )
            )
            continue
        value_result = migrate_visible_intervention_value_engine(
            repo_root=plan.repo_root,
            previous_version=plan.previous_version,
            target_version=plan.target_version,
            runtime_root=runtime,
        )
        results.append(
            MigrationResult(
                migration_id=value_result.migration_id,
                state=STATE_APPLIED if value_result.applied else STATE_SKIPPED,
                reason=value_result.skipped_reason,
                written_paths=value_result.written_paths,
                removed_paths=value_result.removed_paths,
                ledger_path=value_result.ledger_path,
                verification_result={"status": "passed" if value_result.applied else "skipped"},
            )
        )
    return tuple(results)


def apply_repo_state_migrations(*, plan: MigrationPlan) -> tuple[MigrationResult, ...]:
    """Apply only repo-shape migrations that must happen before runtime staging."""
    repo_state_plan = MigrationPlan(
        repo_root=plan.repo_root,
        previous_version=plan.previous_version,
        target_version=plan.target_version,
        repo_schema_version=plan.repo_schema_version,
        scenario=plan.scenario,
        selected=tuple(decision for decision in plan.selected if decision.migration_id == LEGACY_ROOT_MIGRATION_ID),
        skipped=(),
        blocked=tuple(
            decision
            for decision in plan.blocked
            if decision.migration_id == LEGACY_ROOT_MIGRATION_ID or decision.migration_id.startswith("repo-state:")
        ),
        release_manifest_migration_required=plan.release_manifest_migration_required,
        no_op=not any(decision.migration_id == LEGACY_ROOT_MIGRATION_ID for decision in plan.selected),
        plan_fingerprint=plan.plan_fingerprint,
    )
    return apply_release_migrations(plan=repo_state_plan)


def legacy_migration_summary(results: Sequence[MigrationResult]) -> LegacyMigrationSummary | None:
    """Return the legacy migration summary carried by migration results."""
    for result in results:
        if result.migration_id == LEGACY_ROOT_MIGRATION_ID:
            return result.legacy_summary
    return None


def _write_legacy_root_ledger(*, plan: MigrationPlan, decision: MigrationDecision, summary: LegacyMigrationSummary) -> str:
    path = plan.repo_root / ".odylith" / "state" / "migrations" / "legacy-odyssey-root-migration.v1.json"
    payload = {
        "schema_version": MIGRATION_LEDGER_SCHEMA_VERSION,
        "migration_id": LEGACY_ROOT_MIGRATION_ID,
        "recorded_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "from_version": plan.previous_version,
        "to_version": plan.target_version,
        "repo_scenario": plan.scenario.scenario,
        "predicate_evidence": decision.evidence,
        "planned_write_set": list(decision.planned_paths),
        "actual_write_set": list(summary.moved_paths),
        "removed_paths": list(summary.removed_paths),
        "verification_result": {
            "status": "passed",
            "legacy_layout_present": legacy_layout_present(repo_root=plan.repo_root),
        },
        "runtime_snapshot": {
            "active_version": current_runtime_version(repo_root=plan.repo_root),
            "target_version": plan.target_version,
        },
        "plan_fingerprint": plan.plan_fingerprint,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return display_path(repo_root=plan.repo_root, path=path)


def migration_plan_payload(plan: MigrationPlan) -> dict[str, object]:
    """Return a JSON-ready migration plan payload."""
    return plan.as_dict()


def migration_results_payload(results: Sequence[MigrationResult]) -> list[dict[str, object]]:
    """Return JSON-ready migration result payloads."""
    return [result.as_dict() for result in results]


def legacy_value_engine_payload(results: Sequence[MigrationResult], plan: MigrationPlan) -> dict[str, object]:
    """Return the legacy install-ledger value_engine_migration field for compatibility."""
    for result in results:
        if result.migration_id == VALUE_ENGINE_MIGRATION_ID:
            return {
                "migration_id": result.migration_id,
                "applied": result.state == STATE_APPLIED,
                "previous_version": plan.previous_version,
                "target_version": plan.target_version,
                "removed_paths": list(result.removed_paths),
                "written_paths": list(result.written_paths),
                "skipped_reason": result.reason,
                "ledger_path": result.ledger_path,
            }
    return {
        "migration_id": VALUE_ENGINE_MIGRATION_ID,
        "applied": False,
        "previous_version": plan.previous_version,
        "target_version": plan.target_version,
        "skipped_reason": "migration_runtime_no_action",
        "ledger_path": next((decision.ledger_path for decision in plan.decisions if decision.migration_id == VALUE_ENGINE_MIGRATION_ID), ""),
    }


def doctor_migration_observability_lines(*, repo_root: str | Path, status: object | None = None) -> tuple[str, ...]:
    """Return concise migration observability lines for doctor output."""
    root = Path(repo_root).expanduser().resolve()
    active = str(getattr(status, "active_version", "") or "").strip()
    pinned = str(getattr(status, "pinned_version", "") or "").strip()
    repo_role = str(getattr(status, "repo_role", "") or "").strip()
    plan = plan_release_migrations(
        repo_root=root,
        repo_role=repo_role,
        previous_version=active,
        target_version=pinned or active,
        runtime_root=current_runtime_root(repo_root=root),
        state=load_install_state(repo_root=root),
        pinned_version=pinned,
    )
    lines = [
        f"Migration scenario: {plan.scenario.scenario}",
        f"Migration ledger state: {', '.join(f'{key}={value}' for key, value in sorted(plan.ledger_state.items()))}",
    ]
    if plan.blocked_reason:
        lines.append(f"Migration blocked: {plan.blocked_reason}")
    elif plan.selected:
        lines.append("Migration pending: " + ", ".join(decision.migration_id for decision in plan.selected))
    return tuple(lines)


def _release_manifest_paths(repo_root: Path) -> tuple[Path, ...]:
    return (
        repo_root / "dist" / "release-manifest.json",
        repo_root / ".odylith" / "cache" / "release-manifest.json",
    )


def _load_manifest_for_gate(repo_root: Path) -> dict[str, object]:
    for path in _release_manifest_paths(repo_root):
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, Mapping):
            return dict(payload)
    return {}


def _fixture_matrix(repo_root: Path, definitions: Sequence[MigrationDefinition]) -> dict[str, dict[str, bool]]:
    fixture_files = (
        repo_root / "tests" / "unit" / "install" / "test_migration_runtime.py",
        repo_root / "tests" / "unit" / "install" / "test_value_engine_migration.py",
        repo_root / "tests" / "integration" / "install" / "test_manager.py",
        repo_root / "tests" / "integration" / "install" / "test_lifecycle_simulator.py",
    )
    combined = "\n".join(path.read_text(encoding="utf-8") for path in fixture_files if path.is_file())
    matrix: dict[str, dict[str, bool]] = {}
    for definition in definitions:
        matrix[definition.migration_id] = {
            fixture: f"{definition.migration_id}:{fixture}" in combined
            for fixture in definition.coverage_fixtures
        }
    return matrix


def _ungated_lifecycle_paths(repo_root: Path) -> tuple[str, ...]:
    banned = (
        "migrate_visible_intervention_value_engine",
        "migrate_legacy_install_if_needed",
        "visible_intervention_value_engine_migration_pending",
        "visible_intervention_value_engine_migration_ledger_path",
        "value_engine_migration_payload",
    )
    allowed = {
        Path("src/odylith/install/migration_runtime.py"),
        Path("src/odylith/install/value_engine_migration.py"),
        Path("src/odylith/install/legacy_install_migration.py"),
    }
    findings: list[str] = []
    for relative in (
        Path("src/odylith/install/manager.py"),
        Path("src/odylith/install/bootstrap_assets.py"),
        Path("src/odylith/cli.py"),
    ):
        path = repo_root / relative
        if relative in allowed or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for token in banned:
            if token in text:
                findings.append(f"{relative.as_posix()} references {token}")
    return tuple(findings)


def validate_release_migration_gate(
    *,
    repo_root: str | Path,
    target_version: str = "",
    release_manifest: Mapping[str, object] | None = None,
    changed_paths: Sequence[str] | None = None,
) -> ReleaseMigrationGateReport:
    """Validate that release migration requirements are registered and fixture-proven."""
    root = Path(repo_root).expanduser().resolve()
    definitions = registered_migrations()
    manifest = dict(release_manifest if release_manifest is not None else _load_manifest_for_gate(root))
    observer_target = str(target_version or manifest.get("version") or manifest.get("tag") or "")
    surface_observer = observe_surface_migration_needs(
        repo_root=root,
        target_version=observer_target,
        changed_paths=changed_paths,
    )
    blocked_manual: list[str] = []
    if bool(manifest.get("migration_required")):
        target = normalize_version(target_version or manifest.get("version") or manifest.get("tag"))
        if not any(_definition_covers_manifest_target(definition, target) for definition in definitions):
            blocked_manual.append(
                f"migration_required manifest for {target or 'unknown target'} has no registered migration definition"
            )
    matrix = _fixture_matrix(root, definitions)
    for migration_id, coverage in matrix.items():
        missing = [fixture for fixture, present in coverage.items() if not present]
        if missing:
            blocked_manual.append(f"{migration_id} fixture coverage missing: {', '.join(missing)}")
    destructive_matrix = destructive_write_fixture_matrix(repo_root=root)
    blocked_manual.extend(missing_destructive_write_proofs(repo_root=root))
    for need in surface_observer.needs:
        if need.need_id in surface_observer.blocked_need_ids:
            blocked_manual.append(f"{need.need_id} surface migration assessment incomplete: {need.governance_prompt}")
    ungated = _ungated_lifecycle_paths(root)
    covered_ranges = tuple(
        f"{definition.migration_id}: {definition.from_version_range} -> {definition.to_version_range}"
        for definition in definitions
    )
    notes = (
        "Release migration gate checks registry definitions, fixture coverage, and lifecycle bypasses.",
        "Destructive-write guardrails are tracked as first-class adoption-risk fixtures.",
        "Consumer-visible surface changes are observed and must have completed migration assessment records.",
        "Generated dashboard refresh is intentionally outside migration scope.",
    )
    return ReleaseMigrationGateReport(
        ok=not blocked_manual and not ungated and surface_observer.ok,
        registered_migrations=definitions,
        covered_version_ranges=covered_ranges,
        fixture_matrix=matrix,
        destructive_write_matrix=destructive_matrix,
        surface_migration_observer=surface_observer,
        blocked_manual_migrations=tuple(blocked_manual),
        ungated_lifecycle_paths=ungated,
        notes=notes,
    )


def append_migration_ledger_snapshot(*, repo_root: str | Path, plan: MigrationPlan, results: Sequence[MigrationResult]) -> str:
    """Write a transaction-level migration ledger snapshot for observability."""
    root = Path(repo_root).expanduser().resolve()
    path = root / ".odylith" / "state" / "migrations" / f"transaction-{plan.plan_fingerprint}.v1.json"
    payload = {
        "schema_version": MIGRATION_LEDGER_SCHEMA_VERSION,
        "recorded_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "plan": plan.as_dict(),
        "results": migration_results_payload(results),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return display_path(repo_root=root, path=path)
