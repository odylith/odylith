"""Resume only the unchanged dashboard-completion state of an admitted upgrade."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import stat

from odylith.install.fs import atomic_write_text, fsync_directory
from odylith.runtime.domain_intelligence import greenfield_generation_state as publication
from odylith.runtime.domain_intelligence import greenfield_generation_store as generations
from odylith.runtime.domain_intelligence import greenfield_repository_write_set as write_sets


_VERSION = "odylith.upgrade.dashboard-recovery.v1"
_RECEIPT = ".odylith/runtime/upgrade-dashboard-recovery.v1.json"
_ACTIVATION_FILES = (
    ".odylith/install.json",
    ".odylith/bin/odylith",
    ".odylith/bin/odylith-bootstrap",
    "odylith/runtime/source/product-version.v1.json",
)


class UpgradeDashboardRecoveryError(RuntimeError):
    """The recorded upgrade cannot safely authorize another completion attempt."""


def is_completion_retry(tokens: Sequence[str]) -> bool:
    """Recognize the advertised command only, without accepting partial refreshes."""
    if tuple(tokens[:2]) != ("dashboard", "refresh"):
        return False
    remaining = list(tokens[2:])
    seen: set[str] = set()
    while remaining:
        option = remaining.pop(0)
        if option in seen or option not in {"--repo-root", "--force"}:
            return False
        seen.add(option)
        if option == "--repo-root":
            if not remaining or remaining.pop(0).startswith("--"):
                return False
    return "--force" in seen


def _safe_path(root: Path, relative: str) -> Path:
    path = root / relative
    for candidate in (path, *path.parents):
        if candidate == root:
            break
        if candidate.is_symlink():
            raise UpgradeDashboardRecoveryError("RECOVERY_REQUIRED: upgrade recovery crosses an unsafe symlink")
    return path


def _file_state(root: Path, relative: str) -> dict[str, object] | None:
    path = _safe_path(root, relative)
    if not path.exists():
        return None
    if not path.is_file():
        raise UpgradeDashboardRecoveryError("RECOVERY_REQUIRED: upgrade activation file is not regular")
    return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "mode": stat.S_IMODE(path.stat().st_mode)}


def _anchors(root: Path) -> dict[str, object]:
    identity = root.stat()
    current = root / ".odylith/runtime/current"
    _safe_path(root, ".odylith/runtime")
    if current.exists() and not current.is_symlink():
        raise UpgradeDashboardRecoveryError("RECOVERY_REQUIRED: active runtime selection is not a symlink")
    return {
        "repository": {"path": str(root), "device": identity.st_dev, "inode": identity.st_ino},
        "publication": publication.active_generation_identity(root),
        "activation_files": {relative: _file_state(root, relative) for relative in _ACTIVATION_FILES},
        "runtime_target": str(current.readlink()) if current.is_symlink() else None,
        "resolved_runtime": str(current.resolve(strict=True)) if current.is_symlink() else None,
    }


def _require_parent_lock(root: Path, descriptor: int) -> None:
    lock_path = _safe_path(root, ".odylith/runtime/greenfield/create.lock")
    if not os.path.samestat(os.fstat(descriptor), lock_path.stat()):
        raise UpgradeDashboardRecoveryError("RECOVERY_REQUIRED: upgrade completion lacks its repository lease")


def record_failed_completion(
    *, repo_root: Path, repository_lock_fd: int, admitted_receipt: dict[str, object] | None = None,
) -> None:
    """Retain exact continuation authority, never restore or publish failed output."""
    root = Path(repo_root).expanduser().resolve()
    _require_parent_lock(root, repository_lock_fd)
    if publication.read_active_publication(root) is None:
        return
    generations.pin_active_greenfield_generation(root)
    anchors = _anchors(root)
    if admitted_receipt is not None:
        require_unchanged_anchors(repo_root=root, admitted_receipt=admitted_receipt)
        anchors = admitted_receipt["anchors"]
    receipt = {
        "version": _VERSION, "anchors": anchors,
        "working": write_sets.greenfield_managed_fingerprints(root),
    }
    atomic_write_text(_safe_path(root, _RECEIPT), json.dumps(receipt, sort_keys=True) + "\n")


def require_completion_retry(*, repo_root: Path) -> tuple[generations.PinnedGreenfieldGeneration, dict[str, object]]:
    """Called under the writer lock after ordinary working admission rejects drift."""
    root = Path(repo_root).expanduser().resolve()
    try:
        receipt = json.loads(_safe_path(root, _RECEIPT).read_text(encoding="utf-8"))
        expected = {
            "version": _VERSION, "anchors": _anchors(root),
            "working": write_sets.greenfield_managed_fingerprints(root),
        }
        if receipt != expected:
            raise ValueError("recorded upgrade state changed")
        return generations.pin_active_greenfield_generation(root), receipt
    except (OSError, ValueError, RuntimeError) as exc:
        raise UpgradeDashboardRecoveryError(
            "RECOVERY_REQUIRED: the failed upgrade's exact project/runtime state is unavailable or changed; "
            "no retry was run. Preserve your edits and inspect `odylith doctor --repo-root .`."
        ) from exc


def require_unchanged_anchors(*, repo_root: Path, admitted_receipt: dict[str, object]) -> None:
    if _anchors(repo_root) != admitted_receipt["anchors"]:
        raise UpgradeDashboardRecoveryError(
            "RECOVERY_REQUIRED: upgrade activation changed during dashboard completion; "
            "the predecessor remains published and recovery evidence was preserved"
        )


def complete_retry(*, repo_root: Path) -> None:
    """Discard continuation authority only after complete published readback."""
    root = Path(repo_root).expanduser().resolve()
    generations.require_greenfield_working_generation(root)
    path = _safe_path(root, _RECEIPT)
    path.unlink()
    fsync_directory(path.parent)


def complete_selected_render_migrations(
    *, repo_root: Path, repository_lock_fd: int, force: bool = False,
) -> None:
    """Finish only the activated install's selected Atlas migration in the target.

    Both the predecessor's public dashboard command and the current descriptor
    worker reach this operation after their existing writer admission. Install
    records select work; they never authorize bypassing repository admission.
    A completed upgrade is closed: later ordinary refreshes do not scan Atlas.
    """
    from odylith.install import atlas_surface_migration as atlas
    from odylith.install import migration_runtime, runtime, state, upgrade_reporting

    root = Path(repo_root).expanduser().resolve()
    ledger = _safe_path(root, ".odylith/install-ledger.v1.jsonl")
    if not ledger.exists():
        return
    try:
        lines = ledger.read_text(encoding="utf-8").splitlines()
        if not lines:
            return
        event = json.loads(lines[-1])
        if event.get("operation") not in {"install", "upgrade"} or event.get("status") not in {
            "ready", "activated", "already-current",
        }:
            return
        plan = event.get("migration_plan") or {}
        selected = [row for row in plan.get("selected", []) if row.get("migration_id") == atlas.MIGRATION_ID]
        if not selected:
            return
        _require_parent_lock(root, repository_lock_fd)
        target = str(plan["target_version"])
        previous = str(plan["previous_version"])
        active_runtime = runtime.current_runtime_root(repo_root=root)
        if (
            len(selected) != 1 or selected[0]["state"] not in {"selected", "satisfied_unrecorded"}
            or plan["schema_version"] != "odylith.migration-plan.v1"
            or plan["blocked"] or plan["blocked_reason"] or plan["no_op"]
            or event["active_version"] != target
            or state.load_install_state(repo_root=root)["active_version"] != target
            or (event["operation"] == "upgrade" and event["previous_version"] != previous)
            or active_runtime is None or active_runtime.name != target
            or not Path(__file__).resolve().is_relative_to(active_runtime)
            or not Path(atlas.__file__).resolve().is_relative_to(active_runtime)
            or not Path(atlas.diagram_freshness.__file__).resolve().is_relative_to(active_runtime)
            or plan["scenario"]["state"]["runtime_root"] != str(active_runtime)
            or plan["scenario"]["state"]["repo_role"] != "consumer_repo"
            or (event["operation"] == "upgrade" and (
                not event.get("verification")
                or event["verification"] != runtime.runtime_verification_evidence(active_runtime)
            ))
        ):
            raise ValueError("selected migration is not bound to the loaded activated target")
        fingerprint_payload = {key: plan[key] for key in (
            "previous_version", "target_version", "repo_schema_version", "scenario", "selected", "blocked", "skipped",
        )}
        fingerprint = migration_runtime._fingerprint_plan_payload({"repo_root": str(root), **fingerprint_payload})
        expected_link = f".odylith/state/migrations/transaction-{fingerprint}.v1.json"
        transaction = json.loads(_safe_path(root, expected_link).read_text(encoding="utf-8"))
        if (
            plan["plan_fingerprint"] != fingerprint or plan["transaction_ledger"] != expected_link
            or transaction["schema_version"] != "odylith.migration-ledger.v1"
            or transaction["plan"] != {key: value for key, value in plan.items() if key != "transaction_ledger"}
            or transaction["results"] != event["migration_results"]
        ):
            raise ValueError("selected migration plan/transaction linkage changed")
        recorded = datetime.fromisoformat(event["recorded_utc"].replace("Z", "+00:00"))
        latest = upgrade_reporting.latest_upgrade_report(repo_root=root)
        if latest is not None:
            report = latest[1]
            if report.get("plan_fingerprint") == fingerprint and datetime.fromisoformat(
                report["finished_at"].replace("Z", "+00:00"),
            ) >= recorded:
                if report.get("dashboard_refresh", {}).get("success") is True:
                    return
                if not force:
                    raise ValueError("failed selected migration completion requires the advertised forced refresh")
        anchors = _anchors(root)
        inspection = atlas.inspect_atlas_surface_migration(
            repo_root=root, previous_version=previous, target_version=target,
        )
        if set(inspection.planned_paths) - set(selected[0]["planned_paths"]):
            raise ValueError("target render requires paths outside the selected migration")
        if not inspection.verification_passed:
            result = atlas.migrate_atlas_surface_polish(
                repo_root=root, previous_version=previous, target_version=target,
            )
            if set(result.written_paths) - set(selected[0]["planned_paths"]):
                raise ValueError("target render wrote outside the selected migration's planned paths")
        verification = atlas.inspect_atlas_surface_migration(
            repo_root=root, previous_version=previous, target_version=target,
        )
        if not verification.verification_passed:
            raise ValueError("selected Atlas migration did not verify under the activated target")
        require_unchanged_anchors(repo_root=root, admitted_receipt={"anchors": anchors})
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RuntimeError) as exc:
        raise UpgradeDashboardRecoveryError(
            "RECOVERY_REQUIRED: activated target render migration completion failed; "
            "dashboard freshness was not certified"
        ) from exc
