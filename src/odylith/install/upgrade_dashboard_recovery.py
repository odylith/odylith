"""Resume only the unchanged dashboard-completion state of an admitted upgrade."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
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
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise UpgradeDashboardRecoveryError("RECOVERY_REQUIRED: upgrade recovery path is outside the repository")
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


def _require_upgrade_plan_link(root: Path, event: dict) -> str:
    from odylith.install import migration_runtime

    plan = event["migration_plan"]
    if (plan["schema_version"] != "odylith.migration-plan.v1" or plan["blocked"]
            or plan["blocked_reason"] or plan["no_op"] != (not plan["selected"])):
        raise ValueError("upgrade migration plan is not complete")
    fingerprint = migration_runtime._fingerprint_plan_payload({
        "repo_root": str(root), **{key: plan[key] for key in (
            "previous_version", "target_version", "repo_schema_version", "scenario", "selected", "blocked", "skipped",
        )},
    })
    if plan["plan_fingerprint"] != fingerprint:
        raise ValueError("selected migration plan/transaction linkage changed")
    if plan["selected"]:
        expected_link = f".odylith/state/migrations/transaction-{fingerprint}.v1.json"
        transaction = json.loads(_safe_path(root, expected_link).read_text(encoding="utf-8"))
        if (plan["transaction_ledger"] != expected_link
                or transaction["schema_version"] != "odylith.migration-ledger.v1"
                or transaction["plan"] != {key: value for key, value in plan.items() if key != "transaction_ledger"}
                or transaction["results"] != event["migration_results"]):
            raise ValueError("selected migration plan/transaction linkage changed")
    elif event["migration_results"] or plan.get("transaction_ledger"):
        raise ValueError("empty migration plan carries a transaction or results")
    return fingerprint


def _require_failed_report(root: Path, event: dict, path: Path, report: dict) -> dict:
    if (report["schema"] != "odylith.upgrade.report.v1" or report["status"] != "failed"
            or report["repo_root"] != str(root) or report["report_path"] != str(path)
            or report["dashboard_refresh"]["success"] is not False
            or report["plan_fingerprint"] != event["migration_plan"]["plan_fingerprint"]
            or report["migration_plan"] != event["migration_plan"]
            or report["migration_results"] != event["migration_results"]
            or report["final_state"]["active_version"] != event["active_version"]
            or report["final_state"]["verification"] != event["verification"]
            or datetime.fromisoformat(report["finished_at"].replace("Z", "+00:00"))
               < datetime.fromisoformat(event["recorded_utc"].replace("Z", "+00:00"))):
        raise ValueError("failed upgrade report linkage changed")
    relative = str(path.relative_to(root))
    return {"path": relative, **_file_state(root, relative)}


def _require_successful_report(root: Path, event: dict, path: Path, report: dict) -> bool:
    """Validate native success or the original, immutable recovery completion."""
    from odylith.install import upgrade_dashboard

    if (report["schema"] != "odylith.upgrade.report.v1" or report["status"] != "succeeded"
            or report["repo_root"] != str(root) or report["report_path"] != str(path)
            or report["plan_fingerprint"] != event["migration_plan"]["plan_fingerprint"]
            or report["migration_plan"] != event["migration_plan"]
            or report["final_state"]["active_version"] != event["active_version"]
            or report["dashboard_refresh"]["success"] is not True
            or datetime.fromisoformat(report["finished_at"].replace("Z", "+00:00"))
               < datetime.fromisoformat(event["recorded_utc"].replace("Z", "+00:00"))):
        raise ValueError("successful upgrade report linkage changed")
    completions = [row for row in report.get("phases", []) if row.get("name") == "dashboard_completion"]
    if not completions:
        if (report["migration_results"] != event["migration_results"]
                or report["final_state"]["verification"] != event["verification"]):
            raise ValueError("successful upgrade report lacks its original runtime/migration linkage")
        return False
    phase = completions[0]
    details = phase["details"]
    original = details["original_report"]
    original_path = _safe_path(root, original["path"])
    published = publication.require_active_generation_identity(details["published_generation"])
    if (len(completions) != 1 or phase["status"] != "ok"
            or report["dashboard_refresh"] != {
                "surfaces": list(upgrade_dashboard.UPGRADE_DASHBOARD_SURFACES),
                "returncode": 0, "success": True, "fresh": True, "mode": "auto",
            }
            or any(details[key] != value for key, value in report["dashboard_refresh"].items())
            or published["status"] != publication.ACTIVE or details["write_set_hash"] != published["write_set_hash"]
            or details["timing_scope"] != "completion readback only"
            or _require_failed_report(root, event, original_path, json.loads(original_path.read_text())) != original):
        raise ValueError("durable dashboard completion linkage changed")
    generation = generations.pin_greenfield_generation(repo_root=root, write_set_hash=published["write_set_hash"])
    entry = publication.compile_greenfield_publication_entry(
        write_set_hash=generation.write_set_hash, generation_manifest_sha256=generation.manifest_sha256,
    )
    if (generation.manifest_sha256 != published["generation_manifest_sha256"]
            or hashlib.sha256(entry.encode("utf-8")).hexdigest() != published["publication_sha256"]):
        raise ValueError("durable dashboard completion generation binding changed")
    return True


def complete_retry(*, repo_root: Path, admitted_receipt: dict[str, object] | None = None) -> None:
    """Close an admitted full refresh after published readback, then retire its receipt."""
    from odylith.install import state, upgrade_dashboard, upgrade_reporting

    root = Path(repo_root).expanduser().resolve()
    started = datetime.now(UTC)
    try:
        path = _safe_path(root, _RECEIPT)
        if admitted_receipt is None and not path.exists():
            return
        generation = generations.require_greenfield_working_generation(root)
        receipt = json.loads(path.read_text(encoding="utf-8"))
        anchors = _anchors(root)
        if ((admitted_receipt is not None and receipt != admitted_receipt)
                or receipt["version"] != _VERSION or any(
            receipt["anchors"][key] != value for key, value in anchors.items() if key != "publication"
        )):
            raise ValueError("upgrade activation changed before completion readback")
        event = json.loads(_safe_path(root, ".odylith/install-ledger.v1.jsonl").read_text().splitlines()[-1])
        fingerprint = _require_upgrade_plan_link(root, event)
        if (event["operation"] != "upgrade" or event["status"] not in {"activated", "already-current"}
                or event["active_version"] != state.load_install_state(repo_root=root)["active_version"]
                or event["active_version"] != event["migration_plan"]["target_version"]):
            raise ValueError("completion is not bound to the activated upgrade")
        original_path, original_report = upgrade_reporting.latest_upgrade_report(repo_root=root)
        if original_report.get("dashboard_refresh", {}).get("success") is True:
            if not _require_successful_report(root, event, original_path, original_report) or _anchors(root) != anchors:
                raise ValueError("receipt is not bound to a durable recovery completion")
            path.unlink()
            fsync_directory(path.parent)
            return
        original = _require_failed_report(root, event, original_path, original_report)
        finished = datetime.now(UTC)
        details = {"surfaces": list(upgrade_dashboard.UPGRADE_DASHBOARD_SURFACES),
                   "returncode": 0, "success": True, "fresh": True, "mode": "auto"}
        report = {
            "schema": "odylith.upgrade.report.v1", "status": "succeeded", "repo_root": str(root),
            "started_at": started.isoformat(), "finished_at": finished.isoformat(),
            "duration_seconds": round((finished - started).total_seconds(), 3),
            "plan_fingerprint": fingerprint, "migration_plan": event["migration_plan"],
            "final_state": {"active_version": event["active_version"], "previous_version": event["previous_version"]},
            "dashboard_refresh": details,
            "phases": [upgrade_reporting.phase_payload(
                name="dashboard_completion", started_at=started, finished_at=finished, status="ok",
                details={**details, "original_report": original, "published_generation": anchors["publication"],
                         "write_set_hash": generation.write_set_hash, "timing_scope": "completion readback only"},
            )],
        }
        _safe_path(root, ".odylith/runtime/logs")
        completed = upgrade_reporting.write_upgrade_report(repo_root=root, report=report, started_at=started, exclusive=True)
        try:
            if _anchors(root) != anchors or _require_failed_report(
                root, event, original_path, json.loads(original_path.read_text()),
            ) != original:
                raise ValueError("upgrade completion evidence changed during report publication")
        except (OSError, ValueError, KeyError, TypeError, AttributeError, RuntimeError):
            completed.unlink()
            fsync_directory(completed.parent)
            raise
        path.unlink()
        fsync_directory(path.parent)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RuntimeError) as exc:
        raise UpgradeDashboardRecoveryError(
            "RECOVERY_REQUIRED: dashboard completion report could not be settled; "
            "no failed upgrade report was overwritten"
        ) from exc


def complete_selected_render_migrations(
    *, repo_root: Path, repository_lock_fd: int, force: bool = False,
) -> bool:
    """Verify unfinished target completion and finish its selected Atlas render.

    Both the predecessor's public dashboard command and the current descriptor
    worker reach this operation after their existing writer admission. Install
    records select work; they never authorize bypassing repository admission.
    True selects the full generated refresh for a predecessor's narrow command.
    Completed upgrades return False; later ordinary refreshes do not scan Atlas.
    """
    from odylith.install import atlas_surface_migration as atlas
    from odylith.install import runtime, state, upgrade_reporting

    root = Path(repo_root).expanduser().resolve()
    ledger = _safe_path(root, ".odylith/install-ledger.v1.jsonl")
    if not ledger.exists():
        return False
    try:
        lines = ledger.read_text(encoding="utf-8").splitlines()
        if not lines:
            return False
        event = json.loads(lines[-1])
        if event.get("operation") != "upgrade" or event.get("status") not in {
            "activated", "already-current",
        }:
            return False
        plan = event.get("migration_plan") or {}
        selected = [row for row in plan.get("selected", []) if row.get("migration_id") == atlas.MIGRATION_ID]
        if not plan or (not selected and plan["scenario"]["state"]["repo_role"] != "consumer_repo"):
            return False
        _require_parent_lock(root, repository_lock_fd)
        target = str(plan["target_version"])
        previous = str(plan["previous_version"])
        active_runtime = runtime.current_runtime_root(repo_root=root)
        if (
            (selected and (len(selected) != 1 or selected[0]["state"] not in {"selected", "satisfied_unrecorded"}))
            or event["active_version"] != target
            or state.load_install_state(repo_root=root)["active_version"] != target
            or (event["operation"] == "upgrade" and event["previous_version"] != previous)
            or active_runtime is None or active_runtime.name != target
            or not Path(__file__).resolve().is_relative_to(active_runtime)
            or not Path(atlas.__file__).resolve().is_relative_to(active_runtime)
            or not Path(atlas.diagram_freshness.__file__).resolve().is_relative_to(active_runtime)
            or plan["scenario"]["state"]["runtime_root"] != str(active_runtime)
            or plan["scenario"]["state"]["repo_role"] != "consumer_repo"
        ):
            raise ValueError("selected migration is not bound to the loaded activated target")
        fingerprint = _require_upgrade_plan_link(root, event)
        recorded = datetime.fromisoformat(event["recorded_utc"].replace("Z", "+00:00"))
        latest = upgrade_reporting.latest_upgrade_report(repo_root=root)
        if latest is not None:
            report = latest[1]
            if datetime.fromisoformat(
                report["finished_at"].replace("Z", "+00:00"),
            ) >= recorded:
                if report.get("plan_fingerprint") != fingerprint:
                    raise ValueError("latest upgrade report does not match the activated migration plan")
                if report.get("dashboard_refresh", {}).get("success") is True:
                    _require_successful_report(root, event, latest[0], report)
                    return False
                if not force:
                    raise ValueError("failed selected migration completion requires the advertised forced refresh")
        anchors = _anchors(root)
        if event["operation"] == "upgrade" and (
            not event.get("verification")
            or event["verification"] != runtime.runtime_verification_evidence(active_runtime)
        ):
            raise ValueError("upgrade is not bound to the activated target verification")
        if not selected:
            require_unchanged_anchors(repo_root=root, admitted_receipt={"anchors": anchors})
            return True
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
        return True
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RuntimeError) as exc:
        raise UpgradeDashboardRecoveryError(
            "RECOVERY_REQUIRED: activated target render migration completion failed; "
            "dashboard freshness was not certified"
        ) from exc
