"""Exact repository write sets sealed into greenfield create transactions."""

from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any

from odylith.install.fs import atomic_write_bytes
from odylith.install.fs import fsync_directory


GREENFIELD_REPOSITORY_WRITE_SET_VERSION = "odylith.greenfield.repository_write_set.v2"
GREENFIELD_REPOSITORY_WRITE_SET_PHASE = "pre_confirm_compile"
GREENFIELD_REPOSITORY_WRITE_PATHS = (
    "odylith/radar",
    "odylith/technical-plans",
    "odylith/atlas",
    "odylith/registry",
    "odylith/compass",
    "odylith/casebook",
    "odylith/surfaces/brand",
    "odylith/runtime/source",
    "odylith/runtime/delivery_intelligence.v4.json",
    "odylith/index.html",
    "odylith/tooling-payload.v1.js",
    "odylith/tooling-app.v1.js",
    "src/odylith/bundle/assets/odylith",
)
_DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}")


def compile_greenfield_repository_write_set(*, source_root: Path, staged_root: Path) -> dict[str, Any]:
    """Capture exact staged bytes, deletions, and source-tree preconditions."""

    source = Path(source_root).expanduser().resolve()
    staged = Path(staged_root).expanduser().resolve()
    source_files = _managed_file_states(source)
    staged_files = _managed_file_states(staged)
    source_dirs = _managed_directories(source)
    staged_dirs = _managed_directories(staged)

    writes = [
        _write_entry(
            path=path,
            data=staged_files[path][0],
            mode=staged_files[path][1],
            previous=source_files[path][0] if path in source_files else None,
        )
        for path in sorted(staged_files)
        if source_files.get(path) != staged_files[path]
    ]
    deletes = [
        {
            "path": path,
            "previous_sha256": _sha256(source_files[path][0]),
        }
        for path in sorted(source_files)
        if path not in staged_files
    ]
    directories = [
        {"path": path}
        for path in sorted(staged_dirs - source_dirs, key=lambda item: (len(Path(item).parts), item))
    ]
    directory_deletes = [
        {"path": path}
        for path in sorted(source_dirs - staged_dirs, key=lambda item: (-len(Path(item).parts), item))
    ]
    payload: dict[str, Any] = {
        "version": GREENFIELD_REPOSITORY_WRITE_SET_VERSION,
        "phase": GREENFIELD_REPOSITORY_WRITE_SET_PHASE,
        "managed_paths": list(GREENFIELD_REPOSITORY_WRITE_PATHS),
        "before_fingerprints": _managed_fingerprints(source),
        "after_fingerprints": _managed_fingerprints(staged),
        "directories": directories,
        "directory_deletes": directory_deletes,
        "writes": writes,
        "deletes": deletes,
        "directory_count": len(directories),
        "directory_delete_count": len(directory_deletes),
        "write_count": len(writes),
        "delete_count": len(deletes),
    }
    payload["write_set_hash"] = _write_set_hash(payload)
    require_compiled_greenfield_repository_write_set(payload)
    return payload


def require_compiled_greenfield_repository_write_set(value: object) -> dict[str, Any]:
    """Validate a transaction write set without consulting mutable product truth."""

    if not isinstance(value, Mapping):
        raise ValueError("ProductCreateTransaction is missing a compiled repository write set")
    payload = dict(value)
    if str(payload.get("version", "")).strip() != GREENFIELD_REPOSITORY_WRITE_SET_VERSION:
        raise ValueError("ProductCreateTransaction repository write set has an unsupported version")
    if str(payload.get("phase", "")).strip() != GREENFIELD_REPOSITORY_WRITE_SET_PHASE:
        raise ValueError("ProductCreateTransaction repository write set was not compiled before confirmation")
    if tuple(_strings(payload.get("managed_paths"))) != GREENFIELD_REPOSITORY_WRITE_PATHS:
        raise ValueError("ProductCreateTransaction repository write set has an unapproved managed-path boundary")

    before = _fingerprint_mapping(payload.get("before_fingerprints"), label="before")
    after = _fingerprint_mapping(payload.get("after_fingerprints"), label="after")
    expected_paths = set(GREENFIELD_REPOSITORY_WRITE_PATHS)
    if set(before) != expected_paths or set(after) != expected_paths:
        raise ValueError("ProductCreateTransaction repository fingerprints do not cover every managed path")

    directories = _mapping_rows(payload.get("directories"), label="directories")
    directory_deletes = _mapping_rows(payload.get("directory_deletes"), label="directory_deletes")
    writes = _mapping_rows(payload.get("writes"), label="writes")
    deletes = _mapping_rows(payload.get("deletes"), label="deletes")
    _require_count(payload, "directory_count", directories)
    _require_count(payload, "directory_delete_count", directory_deletes)
    _require_count(payload, "write_count", writes)
    _require_count(payload, "delete_count", deletes)

    directory_paths = _validated_paths(directories, label="directory")
    directory_delete_paths = _validated_paths(directory_deletes, label="directory delete")
    write_paths = _validated_paths(writes, label="write")
    delete_paths = _validated_paths(deletes, label="delete")
    if set(directory_paths) & set(directory_delete_paths):
        raise ValueError("ProductCreateTransaction repository write set creates and deletes the same directory")
    if set(write_paths) & set(delete_paths):
        raise ValueError("ProductCreateTransaction repository write set writes and deletes the same path")
    for row in writes:
        _decoded_write_bytes(row)
        previous = str(row.get("previous_sha256", "")).strip()
        if previous and previous != "missing" and not _DIGEST_PATTERN.fullmatch(previous):
            raise ValueError("ProductCreateTransaction repository write has an invalid previous digest")
        mode = row.get("mode")
        if not isinstance(mode, int) or mode < 0 or mode > 0o777:
            raise ValueError("ProductCreateTransaction repository write has an invalid file mode")
    for row in deletes:
        if not _DIGEST_PATTERN.fullmatch(str(row.get("previous_sha256", "")).strip()):
            raise ValueError("ProductCreateTransaction repository delete has an invalid previous digest")
    if directory_paths != sorted(directory_paths, key=lambda item: (len(Path(item).parts), item)):
        raise ValueError("ProductCreateTransaction repository directories are not in deterministic order")
    if directory_delete_paths != sorted(
        directory_delete_paths,
        key=lambda item: (-len(Path(item).parts), item),
    ):
        raise ValueError("ProductCreateTransaction repository directory deletes are not in deterministic order")
    if write_paths != sorted(write_paths) or delete_paths != sorted(delete_paths):
        raise ValueError("ProductCreateTransaction repository write set is not in deterministic order")
    if str(payload.get("write_set_hash", "")).strip() != _write_set_hash(payload):
        raise ValueError("ProductCreateTransaction repository write set hash mismatch")
    return payload


def require_greenfield_repository_preconditions(*, repo_root: Path, write_set: object) -> dict[str, Any]:
    """Reject a compiled transaction when governed source changed after compilation."""

    payload = require_compiled_greenfield_repository_write_set(write_set)
    root = Path(repo_root).expanduser().resolve()
    expected = _fingerprint_mapping(payload.get("before_fingerprints"), label="before")
    actual = _managed_fingerprints(root)
    changed = [path for path in GREENFIELD_REPOSITORY_WRITE_PATHS if actual[path] != expected[path]]
    if changed:
        raise ValueError(
            "ProductCreateTransaction repo preconditions changed after pre-confirm compilation: "
            + ", ".join(changed)
            + ". Rebuild the transaction before committing governed records."
        )
    return payload


def apply_compiled_greenfield_repository_write_set(*, repo_root: Path, write_set: object) -> dict[str, Any]:
    """Apply sealed bytes and validate final tree fingerprints."""

    root = Path(repo_root).expanduser().resolve()
    payload = require_greenfield_repository_preconditions(repo_root=root, write_set=write_set)
    directories = _mapping_rows(payload.get("directories"), label="directories")
    directory_deletes = _mapping_rows(payload.get("directory_deletes"), label="directory_deletes")
    writes = _mapping_rows(payload.get("writes"), label="writes")
    deletes = _mapping_rows(payload.get("deletes"), label="deletes")

    for row in directories:
        _target_path(root=root, token=str(row["path"]), allow_missing=True).mkdir(parents=True, exist_ok=True)
    for row in writes:
        target = _target_path(root=root, token=str(row["path"]), allow_missing=True)
        atomic_write_bytes(target, _decoded_write_bytes(row))
        os.chmod(target, int(row["mode"]))
        fsync_directory(target.parent)
    for row in deletes:
        target = _target_path(root=root, token=str(row["path"]), allow_missing=False)
        target.unlink()
        fsync_directory(target.parent)
    for row in directory_deletes:
        target = _target_path(root=root, token=str(row["path"]), allow_missing=True)
        if not target.is_dir():
            raise RuntimeError(f"compiled repository directory delete target is missing: {row['path']}")
        target.rmdir()
        fsync_directory(target.parent)

    expected_after = _fingerprint_mapping(payload.get("after_fingerprints"), label="after")
    actual_after = _managed_fingerprints(root)
    changed = [path for path in GREENFIELD_REPOSITORY_WRITE_PATHS if actual_after[path] != expected_after[path]]
    if changed:
        raise RuntimeError(
            "compiled repository write-set readback drifted after materialization: " + ", ".join(changed)
        )
    return {
        "version": GREENFIELD_REPOSITORY_WRITE_SET_VERSION,
        "status": "passed",
        "write_set_hash": str(payload["write_set_hash"]),
        "directory_count": len(directories),
        "directory_delete_count": len(directory_deletes),
        "write_count": len(writes),
        "delete_count": len(deletes),
    }


def greenfield_repository_write_paths(write_set: object) -> tuple[str, ...]:
    """Return every path whose pre-commit state must be recoverable."""

    payload = require_compiled_greenfield_repository_write_set(write_set)
    rows = [
        *_mapping_rows(payload.get("directories"), label="directories"),
        *_mapping_rows(payload.get("directory_deletes"), label="directory_deletes"),
        *_mapping_rows(payload.get("writes"), label="writes"),
        *_mapping_rows(payload.get("deletes"), label="deletes"),
    ]
    paths = sorted(
        dict.fromkeys(str(row["path"]) for row in rows),
        key=lambda item: (len(Path(item).parts), item),
    )
    result: list[str] = []
    for path in paths:
        if any(path == owner or path.startswith(owner + "/") for owner in result):
            continue
        result.append(path)
    return tuple(result)


def _write_entry(*, path: str, data: bytes, mode: int, previous: bytes | None) -> dict[str, Any]:
    return {
        "path": path,
        "encoding": "base64",
        "content_base64": base64.b64encode(data).decode("ascii"),
        "sha256": _sha256(data),
        "previous_sha256": _sha256(previous) if previous is not None else "missing",
        "mode": mode,
    }


def _managed_file_states(root: Path) -> dict[str, tuple[bytes, int]]:
    files: dict[str, tuple[bytes, int]] = {}
    for token in GREENFIELD_REPOSITORY_WRITE_PATHS:
        target = root / token
        _reject_symlink(target, root=root)
        if target.is_file():
            files[token] = (target.read_bytes(), stat.S_IMODE(target.stat().st_mode))
            continue
        if not target.is_dir():
            continue
        for candidate in sorted(target.rglob("*")):
            _reject_symlink(candidate, root=root)
            if candidate.is_file():
                files[candidate.relative_to(root).as_posix()] = (
                    candidate.read_bytes(),
                    stat.S_IMODE(candidate.stat().st_mode),
                )
    return files


def _managed_directories(root: Path) -> set[str]:
    directories: set[str] = set()
    for token in GREENFIELD_REPOSITORY_WRITE_PATHS:
        target = root / token
        _reject_symlink(target, root=root)
        if not target.is_dir():
            continue
        directories.add(token)
        for candidate in sorted(target.rglob("*")):
            _reject_symlink(candidate, root=root)
            if candidate.is_dir():
                directories.add(candidate.relative_to(root).as_posix())
    return directories


def _managed_fingerprints(root: Path) -> dict[str, str]:
    return {token: _tree_fingerprint(root=root, token=token) for token in GREENFIELD_REPOSITORY_WRITE_PATHS}


def _tree_fingerprint(*, root: Path, token: str) -> str:
    target = root / token
    _reject_symlink(target, root=root)
    rows: list[dict[str, Any]] = []
    if target.is_file():
        rows.append(_file_fingerprint_row(root=root, path=target))
    elif target.is_dir():
        rows.append({"kind": "directory", "path": token})
        for candidate in sorted(target.rglob("*")):
            _reject_symlink(candidate, root=root)
            if candidate.is_dir():
                rows.append({"kind": "directory", "path": candidate.relative_to(root).as_posix()})
            elif candidate.is_file():
                rows.append(_file_fingerprint_row(root=root, path=candidate))
    else:
        rows.append({"kind": "missing", "path": token})
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _file_fingerprint_row(*, root: Path, path: Path) -> dict[str, Any]:
    return {
        "kind": "file",
        "path": path.relative_to(root).as_posix(),
        "sha256": _sha256(path.read_bytes()),
        "mode": stat.S_IMODE(path.stat().st_mode),
    }


def _target_path(*, root: Path, token: str, allow_missing: bool) -> Path:
    path = Path(token)
    if path.is_absolute() or ".." in path.parts or not _is_managed_path(token):
        raise RuntimeError(f"compiled repository write escapes the managed boundary: {token}")
    target = root / path
    current = root
    for part in path.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise RuntimeError(f"compiled repository write crosses a symlink: {token}")
    if target.is_symlink():
        raise RuntimeError(f"compiled repository write targets a symlink: {token}")
    if not allow_missing and not target.is_file():
        raise RuntimeError(f"compiled repository delete target is missing: {token}")
    return target


def _reject_symlink(path: Path, *, root: Path) -> None:
    if path.is_symlink():
        try:
            token = path.relative_to(root).as_posix()
        except ValueError:
            token = str(path)
        raise ValueError(f"greenfield repository write-set compilation refuses managed symlink: {token}")


def _validated_paths(rows: Sequence[Mapping[str, Any]], *, label: str) -> list[str]:
    paths = [str(row.get("path", "")).strip() for row in rows]
    if any(not path or not _is_managed_path(path) for path in paths):
        raise ValueError(f"ProductCreateTransaction repository {label} escapes the managed boundary")
    if len(paths) != len(set(paths)):
        raise ValueError(f"ProductCreateTransaction repository {label} paths are duplicated")
    return paths


def _is_managed_path(token: str) -> bool:
    path = Path(token)
    if path.is_absolute() or ".." in path.parts:
        return False
    return any(token == root or token.startswith(root + "/") for root in GREENFIELD_REPOSITORY_WRITE_PATHS)


def _decoded_write_bytes(row: Mapping[str, Any]) -> bytes:
    if str(row.get("encoding", "")).strip() != "base64":
        raise ValueError("ProductCreateTransaction repository write has an unsupported encoding")
    try:
        data = base64.b64decode(str(row.get("content_base64", "")), validate=True)
    except ValueError as exc:
        raise ValueError("ProductCreateTransaction repository write is not valid base64") from exc
    if _sha256(data) != str(row.get("sha256", "")).strip():
        raise ValueError("ProductCreateTransaction repository write payload hash mismatch")
    return data


def _mapping_rows(value: object, *, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"ProductCreateTransaction repository {label} must be a list")
    rows = list(value)
    if not all(isinstance(row, Mapping) for row in rows):
        raise ValueError(f"ProductCreateTransaction repository {label} contains a non-object entry")
    return rows


def _fingerprint_mapping(value: object, *, label: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError(f"ProductCreateTransaction repository {label} fingerprints are missing")
    result = {str(key): str(item).strip() for key, item in value.items()}
    if any(not _DIGEST_PATTERN.fullmatch(item) for item in result.values()):
        raise ValueError(f"ProductCreateTransaction repository {label} fingerprints are invalid")
    return result


def _require_count(payload: Mapping[str, Any], key: str, rows: Sequence[object]) -> None:
    if payload.get(key) != len(rows):
        raise ValueError(f"ProductCreateTransaction repository write set has an invalid {key}")


def _write_set_hash(payload: Mapping[str, Any]) -> str:
    canonical_payload = {str(key): value for key, value in payload.items() if str(key) != "write_set_hash"}
    canonical = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


__all__ = [
    "GREENFIELD_REPOSITORY_WRITE_PATHS",
    "GREENFIELD_REPOSITORY_WRITE_SET_PHASE",
    "GREENFIELD_REPOSITORY_WRITE_SET_VERSION",
    "apply_compiled_greenfield_repository_write_set",
    "compile_greenfield_repository_write_set",
    "greenfield_repository_write_paths",
    "require_compiled_greenfield_repository_write_set",
    "require_greenfield_repository_preconditions",
]
