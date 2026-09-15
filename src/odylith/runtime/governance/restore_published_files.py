"""Explicitly reviewed working-file restoration without changing publication.

A receipt grants new, selected-file restoration intent, never provenance for an
older failed writer. Admission is durable before replacement; interrupted apply
accepts only the sealed pre/post file states and freezes the rest of the managed
boundary. No operation here publishes, renders, or replays an earlier command.
"""

from __future__ import annotations

import argparse
import base64
from collections.abc import Sequence
import hashlib
import json
from pathlib import Path
import shlex
import stat
import sys
from typing import Any

from odylith.install.fs import atomic_write_bytes, fsync_directory
from odylith.runtime.domain_intelligence import greenfield_generation_state as publication
from odylith.runtime.domain_intelligence import greenfield_generation_store as generations
from odylith.runtime.domain_intelligence import greenfield_repository_write_set as write_sets
from odylith.runtime.domain_intelligence.greenfield_commit_journal import GreenfieldCommitJournal
from odylith.runtime.domain_intelligence.greenfield_repository_lock import (
    GreenfieldRepositoryBusyError,
    greenfield_repository_lock,
)


VERSION = "odylith.working-file-restoration.v1"
PURPOSE = "restore-explicit-working-files-from-pinned-publication"
_RECEIPTS = ".odylith/runtime/greenfield/working-file-restorations"
_PLAN_FIELDS = {"version", "purpose", "repository", "publication", "before_fingerprints", "targets", "review_hash"}


def _canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def _digest(value: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError("Restoration requires a lowercase SHA-256 review hash")
    return value


def _identity(root: Path) -> dict[str, Any]:
    value = root.stat()
    return {"path": str(root), "device": value.st_dev, "inode": value.st_ino}


def _safe_path(root: Path, path: Path, *, regular: bool = False) -> Path:
    """Reject aliases before opening data, receipts, or the shared lock object."""
    current = root
    parts = path.relative_to(root).parts
    for index, part in enumerate(parts):
        current = current / part
        if not current.exists() and not current.is_symlink():
            if regular:
                raise ValueError(f"Restoration file is missing: {path.relative_to(root)}")
            continue
        value = current.lstat()
        if stat.S_ISLNK(value.st_mode):
            raise ValueError(f"Restoration refuses symlink: {current.relative_to(root)}")
        if index < len(parts) - 1 and not stat.S_ISDIR(value.st_mode):
            raise ValueError("Restoration path crosses a non-directory")
        if stat.S_ISREG(value.st_mode) and value.st_nlink != 1:
            raise ValueError(f"Restoration refuses hardlink: {current.relative_to(root)}")
        if index == len(parts) - 1 and regular and not stat.S_ISREG(value.st_mode):
            raise ValueError(f"Restoration requires a regular file: {path.relative_to(root)}")
    return path


def _root(repo_root: Path) -> Path:
    root = Path(repo_root).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Restoration repository root is not a directory")
    lock = root / ".odylith/runtime/greenfield/create.lock"
    _safe_path(root, lock, regular=lock.exists())
    return root


def _target(layout: write_sets.GreenfieldRepositoryLayout, token: str) -> Path:
    if not isinstance(token, str) or not token or "\\" in token or Path(token).as_posix() != token:
        raise ValueError("Restoration requires canonical repository-relative paths")
    if any(part in {"", ".", ".."} for part in token.split("/")):
        raise ValueError("Restoration target escapes its canonical path")
    return _safe_path(layout.repo_root, layout.target_path(token), regular=True)


def _file_state(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "mode": stat.S_IMODE(path.stat().st_mode),
        "content_base64": base64.b64encode(data).decode("ascii"),
    }


def _decode_state(state: object) -> bytes:
    if not isinstance(state, dict) or set(state) != {"sha256", "mode", "content_base64"}:
        raise ValueError("Restoration file seal is malformed")
    _digest(state["sha256"])
    mode = state["mode"]
    if type(mode) is not int or not 0 <= mode <= 0o7777:
        raise ValueError("Restoration file mode is invalid")
    encoded = state["content_base64"]
    if not isinstance(encoded, str):
        raise ValueError("Restoration preimage is malformed")
    data = base64.b64decode(encoded, validate=True)
    if base64.b64encode(data).decode("ascii") != encoded or hashlib.sha256(data).hexdigest() != state["sha256"]:
        raise ValueError("Restoration preimage hash differs from its seal")
    return data


def _require_safe_managed_tree(root: Path) -> None:
    layout = write_sets.greenfield_repository_layout(root)
    for token in write_sets.GREENFIELD_REPOSITORY_WRITE_PATHS:
        path = _safe_path(root, layout.target_path(token))
        if not path.exists():
            continue
        candidates = [path, *path.rglob("*")] if path.is_dir() else [path]
        for candidate in candidates:
            _safe_path(root, candidate)
            mode = candidate.lstat().st_mode
            if not stat.S_ISDIR(mode) and not stat.S_ISREG(mode):
                raise ValueError("Restoration refuses non-regular managed inventory")


def _pin(root: Path, expected: object | None = None) -> generations.PinnedGreenfieldGeneration:
    _safe_path(root, root / "odylith/index.html", regular=True)
    pinned = generations.pin_active_greenfield_generation(root)
    _safe_path(root, pinned.generation_root / "generation-manifest.v1.json", regular=True)
    _require_safe_managed_tree(pinned.repository_root)
    if expected is not None and publication.active_generation_identity(root) != expected:
        raise ValueError("Restoration active publication changed after preview")
    return pinned


def _receipt(root: Path, review_hash: str) -> Path:
    path = _safe_path(root, root / _RECEIPTS / _digest(review_hash))
    if path.exists() and not path.is_dir():
        raise ValueError("Restoration receipt is not a directory")
    return path


def _read_json(root: Path, path: Path) -> dict[str, Any]:
    raw = _safe_path(root, path, regular=True).read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict) or _canonical(value) != raw:
        raise ValueError("Restoration receipt is not canonical")
    return value


def _read_plan(root: Path, review_hash: str) -> dict[str, Any]:
    plan = _read_json(root, _receipt(root, review_hash) / "plan.json")
    if set(plan) != _PLAN_FIELDS or plan["version"] != VERSION or plan["purpose"] != PURPOSE:
        raise ValueError("Restoration receipt has a different purpose or schema")
    payload = {key: value for key, value in plan.items() if key != "review_hash"}
    if plan["review_hash"] != review_hash or hashlib.sha256(_canonical(payload)).hexdigest() != review_hash:
        raise ValueError("Restoration plan differs from the reviewed hash")
    identity = publication.require_active_generation_identity(plan["publication"])
    if identity["status"] != publication.ACTIVE:
        raise ValueError("Restoration requires an active publication identity")
    if plan["repository"] != _identity(root):
        raise ValueError("Restoration receipt belongs to a different repository")
    fingerprints = plan["before_fingerprints"]
    if not isinstance(fingerprints, dict) or set(fingerprints) != set(write_sets.GREENFIELD_REPOSITORY_WRITE_PATHS):
        raise ValueError("Restoration managed snapshot is incomplete")
    for value in fingerprints.values():
        _digest(value)
    rows = plan["targets"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("Restoration has no explicitly selected files")
    paths, byte_count = [], 0
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "current", "published"}:
            raise ValueError("Restoration target seal is malformed")
        if not isinstance(row["path"], str):
            raise ValueError("Restoration target path is not a string")
        paths.append(row["path"])
        byte_count += len(_decode_state(row["current"])) + len(_decode_state(row["published"]))
    if paths != sorted(set(paths)) or byte_count > write_sets.MAX_SEALED_GENERATION_BYTES:
        raise ValueError("Restoration targets are duplicated, unordered, or too large")
    return plan


def _marker(review_hash: str, state: str) -> dict[str, str]:
    return {"version": VERSION, "purpose": PURPOSE, "review_hash": review_hash, "state": state}


def _has_marker(root: Path, receipt: Path, review_hash: str, state: str) -> bool:
    path = _safe_path(root, receipt / f"{state}.json")
    if not path.exists():
        return False
    if _read_json(root, path) != _marker(review_hash, state):
        raise ValueError("Restoration admission or completion receipt is corrupt")
    return True


def _incomplete_preview(root: Path, receipt: Path) -> bool:
    """An interrupted preview grants no write authority and needs no rollback.

    Keep empty folders and atomic plan-write temporaries as evidence. A later
    preview can finish the same content address; other previews need not wait.
    Admission/completion without a plan is corruption, never a preview orphan.
    """
    for name in ("plan.json", "admitted.json", "closed.json"):
        path = _safe_path(root, receipt / name)
        if path.exists():
            return False
    for entry in receipt.iterdir():
        _safe_path(root, entry, regular=True)
        if not (entry.name.startswith(".plan.json.") and entry.name.endswith(".tmp")):
            raise ValueError("Incomplete restoration preview contains unrecognized files")
    return True


def _require_settled(root: Path, *, own_hash: str = "") -> None:
    GreenfieldCommitJournal.require_settled_journals(repo_root=root)
    _require_no_pending_restoration(root, own_hash=own_hash)


def require_restoration_writer_admission(*, repo_root: Path) -> None:
    """Fence other writers under their existing lock, before recovery or dispatch.

    Only small status markers and safe file metadata are needed to fence an
    admitted restore. Historical plan payloads are decoded only by restore itself.
    """
    try:
        _require_no_pending_restoration(Path(repo_root).expanduser().resolve())
    except (OSError, RuntimeError, ValueError) as exc:
        raise generations.GreenfieldWorkingGenerationDriftError(
            f"RECOVERY_REQUIRED: working-file restoration must settle before another managed writer: {exc}"
        ) from exc


def _require_no_pending_restoration(root: Path, *, own_hash: str = "") -> None:
    parent = _safe_path(root, root / _RECEIPTS)
    if not parent.exists():
        return
    if not parent.is_dir():
        raise ValueError("Restoration receipt store is unsafe")
    for entry in parent.iterdir():
        receipt = _receipt(root, entry.name)
        if _incomplete_preview(root, receipt):
            continue
        admitted = _has_marker(root, receipt, entry.name, "admitted")
        closed = _has_marker(root, receipt, entry.name, "closed")
        if closed and not admitted:
            raise ValueError("Restoration completion has no durable admission")
        if admitted:
            _safe_path(root, receipt / "plan.json", regular=True)
        if entry.name != own_hash and admitted and not closed:
            raise ValueError("Another working-file restoration needs recovery first")


def _check_working(root: Path, plan: dict[str, Any], *, allow_post: bool) -> list[str]:
    if plan["repository"] != _identity(root):
        raise ValueError("Restoration repository identity changed")
    pinned = _pin(root, plan["publication"])
    layout = write_sets.greenfield_repository_layout(root)
    sealed_layout = write_sets.GreenfieldRepositoryLayout(pinned.repository_root, publication_protected=False)
    _require_safe_managed_tree(root)
    remaining = []
    for row in plan["targets"]:
        target = _target(layout, row["path"])
        if target.stat().st_dev != root.stat().st_dev:
            raise ValueError("Restoration requires one filesystem for atomic replacement")
        sealed = _target(sealed_layout, row["path"])
        if _file_state(sealed) != row["published"]:
            raise ValueError("Restoration replacement differs from pinned published bytes")
        current = _file_state(target)
        if current != row["current"] and not (allow_post and current == row["published"]):
            raise ValueError(f"Restoration target changed after preview: {row['path']}")
        if current != row["published"]:
            remaining.append(row["path"])
    normalized = write_sets.greenfield_managed_fingerprints_with_file_states(
        root, file_states={row["path"]: row["current"] for row in plan["targets"]},
    )
    if normalized != plan["before_fingerprints"]:
        raise ValueError("Restoration non-target managed bytes, modes, or directory inventory changed")
    return remaining


def _summary(root: Path, plan: dict[str, Any], status: str) -> dict[str, Any]:
    layout = write_sets.greenfield_repository_layout(root)
    return {
        "status": status, "purpose": PURPOSE, "review_hash": plan["review_hash"],
        "publication": plan["publication"], "receipt_path": str(_receipt(root, plan["review_hash"])),
        "apply_command": shlex.join([
            "odylith", "governance", "restore-published-files", "--repo-root", str(root),
            "--apply", plan["review_hash"],
        ]),
        "targets": [
            {"path": row["path"], "working_path": layout.target_path(row["path"]).relative_to(root).as_posix(), **{
                state: {key: value for key, value in row[state].items() if key != "content_base64"}
                for state in ("current", "published")
            }} for row in plan["targets"]
        ],
    }


def _check_admitted(root: Path, plan: dict[str, Any]) -> list[str]:
    review_hash = plan["review_hash"]
    if _read_plan(root, review_hash) != plan or not _has_marker(root, _receipt(root, review_hash), review_hash, "admitted"):
        raise ValueError("Restoration admission or preserved preimages changed")
    return _check_working(root, plan, allow_post=True)


def _mkdir_durable(root: Path, path: Path) -> None:
    _safe_path(root, path)
    missing = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
        fsync_directory(directory.parent)


def preview_restore(*, repo_root: Path, paths: Sequence[str]) -> dict[str, Any]:
    """Seal a new restoration intent; leave all managed and published bytes alone."""
    root = _root(repo_root)
    selected = list(paths)
    if not selected or not all(isinstance(path, str) for path in selected) or len(selected) != len(set(selected)):
        raise ValueError("Preview requires a nonempty list of unique explicit paths")
    with greenfield_repository_lock(root):
        _require_settled(root)
        pinned = _pin(root)
        layout = write_sets.greenfield_repository_layout(root)
        sealed_layout = write_sets.GreenfieldRepositoryLayout(pinned.repository_root, publication_protected=False)
        _require_safe_managed_tree(root)
        plan = {
            "version": VERSION, "purpose": PURPOSE, "repository": _identity(root),
            "publication": publication.active_generation_identity(root),
            "before_fingerprints": write_sets.greenfield_managed_fingerprints(root),
            "targets": [{
                "path": path, "current": _file_state(_target(layout, path)),
                "published": _file_state(_target(sealed_layout, path)),
            } for path in sorted(selected)],
        }
        if sum(len(_decode_state(row[state])) for row in plan["targets"] for state in ("current", "published")) > write_sets.MAX_SEALED_GENERATION_BYTES:
            raise ValueError("Selected restoration preimages exceed the bounded receipt size")
        plan["review_hash"] = hashlib.sha256(_canonical(plan)).hexdigest()
        _check_working(root, plan, allow_post=False)
        receipt = _receipt(root, plan["review_hash"])
        if receipt.exists() and not _incomplete_preview(root, receipt):
            if _read_plan(root, plan["review_hash"]) != plan:
                raise ValueError("Existing restoration preview differs from its seal")
        else:
            _mkdir_durable(root, receipt)
            atomic_write_bytes(receipt / "plan.json", _canonical(plan), mode=0o600)
        return _summary(root, plan, "previewed")


def apply_restore(*, repo_root: Path, review_hash: str) -> dict[str, Any]:
    """Finish only an explicit reviewed restoration, including exact partial retries."""
    root = _root(repo_root)
    _digest(review_hash)
    with greenfield_repository_lock(root):
        _require_settled(root, own_hash=review_hash)
        plan = _read_plan(root, review_hash)
        receipt = _receipt(root, review_hash)
        admitted = _has_marker(root, receipt, review_hash, "admitted")
        closed = _has_marker(root, receipt, review_hash, "closed")
        remaining = _check_working(root, plan, allow_post=admitted)
        if closed:
            if remaining:
                raise ValueError("Completed restoration targets changed; preview new intent")
            return _summary(root, plan, "already_restored")
        temporary = _safe_path(root, receipt / ".writes")
        if temporary.exists() and not temporary.is_dir():
            raise ValueError("Restoration temporary store is unsafe")
        _mkdir_durable(root, temporary)
        if temporary.stat().st_dev != root.stat().st_dev:
            raise ValueError("Restoration receipt must share the repository filesystem")
        if not admitted:
            atomic_write_bytes(receipt / "admitted.json", _canonical(_marker(review_hash, "admitted")), mode=0o600)
        layout = write_sets.greenfield_repository_layout(root)
        for row in plan["targets"]:
            remaining = _check_admitted(root, plan)
            if row["path"] in remaining:
                atomic_write_bytes(
                    _target(layout, row["path"]), _decode_state(row["published"]),
                    mode=row["published"]["mode"], temporary_directory=temporary,
                )
        if _check_admitted(root, plan):
            raise RuntimeError("Restoration readback did not reach all sealed replacement bytes")
        atomic_write_bytes(receipt / "closed.json", _canonical(_marker(review_hash, "closed")), mode=0o600)
        return _summary(root, plan, "restored")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith governance restore-published-files", allow_abbrev=False,
        description=("Preview or explicitly apply selected working-file restoration from the current pinned publication. "
                     "This preserves publication and creates new restoration intent, not old-failure provenance."),
    )
    parser.add_argument("--repo-root", default=".")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--preview", action="store_true", help="Seal exact current and published file hashes without restoring files.")
    action.add_argument("--apply", metavar="REVIEW_HASH", help="Apply or resume only this reviewed restoration hash.")
    parser.add_argument("--path", action="append", default=[], help="Explicit managed logical file path; repeat for each preview target.")
    parser.add_argument("--json", action="store_true", dest="as_json")
    tokens = list(sys.argv[1:] if argv is None else argv)
    for option in ("--repo-root", "--preview", "--apply"):
        if sum(token == option or token.startswith(option + "=") for token in tokens) > 1:
            parser.error(f"{option} must be supplied at most once")
    args = parser.parse_args(tokens)
    if args.preview and not args.path:
        parser.error("--preview requires at least one explicit --path")
    if args.apply and args.path:
        parser.error("--apply accepts only the reviewed hash, not additional targets")
    return args


def run(args: argparse.Namespace) -> int:
    try:
        result = (preview_restore(repo_root=Path(args.repo_root), paths=args.path) if args.preview
                  else apply_restore(repo_root=Path(args.repo_root), review_hash=args.apply))
    except GreenfieldRepositoryBusyError as exc:
        print(str(exc), file=sys.stderr)
        return 75
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Working-file restoration refused: {exc}", file=sys.stderr)
        return 1
    if args.as_json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(f"Working-file restoration: {result['status']}; publication unchanged.")
        for row in result["targets"]:
            print(f"  {row['path']} (working file: {row['working_path']}): {row['current']['sha256']} (mode {row['current']['mode']:04o}) -> "
                  f"{row['published']['sha256']} (mode {row['published']['mode']:04o})")
        print(f"Review hash: {result['review_hash']}")
        print(f"Preserved preimages and receipts: {result['receipt_path']}")
        if args.preview:
            print("After reviewing these exact targets and hashes, apply with:")
            print(result["apply_command"])
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
