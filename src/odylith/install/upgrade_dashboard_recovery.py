"""Resume only the unchanged dashboard-completion state of an admitted upgrade."""

from __future__ import annotations

from collections.abc import Sequence
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
