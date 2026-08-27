"""Exact repository write sets sealed into greenfield create transactions."""

from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
import hashlib
import json
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_generation_state
from odylith.runtime.domain_intelligence import greenfield_transaction_path_boundary
from odylith.runtime.domain_intelligence.greenfield_create_contract import is_sha256_digest


GREENFIELD_REPOSITORY_WRITE_SET_VERSION = "odylith.greenfield.repository_write_set.v3"
GREENFIELD_REPOSITORY_WRITE_SET_PHASE = "pre_confirm_compile"
MAX_SEALED_GENERATION_BYTES = 256 * 1024 * 1024
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
    after_image = _compile_after_image(files=staged_files, directories=staged_dirs)
    payload: dict[str, Any] = {
        "version": GREENFIELD_REPOSITORY_WRITE_SET_VERSION,
        "phase": GREENFIELD_REPOSITORY_WRITE_SET_PHASE,
        "managed_paths": list(GREENFIELD_REPOSITORY_WRITE_PATHS),
        "before_fingerprints": _managed_fingerprints(source),
        "after_fingerprints": _managed_fingerprints(staged),
        "active_generation_precondition": greenfield_generation_state.active_generation_identity(source),
        "after_image": after_image,
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
    greenfield_generation_state.require_active_generation_identity(
        payload.get("active_generation_precondition")
    )

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
    after_files = _require_after_image(payload)
    for row in writes:
        path = str(row.get("path", "")).strip()
        after_row = after_files.get(path)
        if after_row is None:
            raise ValueError("ProductCreateTransaction repository write is absent from the sealed after-image")
        if str(row.get("sha256", "")).strip() != str(after_row.get("sha256", "")).strip():
            raise ValueError("ProductCreateTransaction repository write hash differs from its sealed after-image")
        if row.get("mode") != after_row.get("mode"):
            raise ValueError("ProductCreateTransaction repository write mode differs from its sealed after-image")
        previous = str(row.get("previous_sha256", "")).strip()
        if previous and previous != "missing" and not is_sha256_digest(previous):
            raise ValueError("ProductCreateTransaction repository write has an invalid previous digest")
        mode = row.get("mode")
        if not isinstance(mode, int) or mode < 0 or mode > 0o777:
            raise ValueError("ProductCreateTransaction repository write has an invalid file mode")
    for row in deletes:
        if not is_sha256_digest(row.get("previous_sha256")):
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
    expected_generation = greenfield_generation_state.require_active_generation_identity(
        payload.get("active_generation_precondition")
    )
    if greenfield_generation_state.active_generation_identity(root) != expected_generation:
        raise ValueError(
            "ProductCreateTransaction active generation changed after pre-confirm compilation. "
            "Rebuild the transaction before committing governed records."
        )
    return payload


def require_greenfield_repository_after_state(
    *,
    repo_root: Path,
    write_set: object,
    managed_prefix: str = "",
) -> dict[str, Any]:
    """Verify that a prior sealed write still owns the entire managed boundary."""

    payload = require_compiled_greenfield_repository_write_set(write_set)
    root = Path(repo_root).expanduser().resolve()
    expected = _fingerprint_mapping(payload.get("after_fingerprints"), label="after")
    actual = _managed_fingerprints(root, prefix=managed_prefix)
    changed = [path for path in GREENFIELD_REPOSITORY_WRITE_PATHS if actual[path] != expected[path]]
    if changed:
        raise ValueError(
            "ProductCreateTransaction committed repository state changed after confirmation: " + ", ".join(changed)
        )
    return payload


def apply_compiled_greenfield_repository_write_set(
    *,
    repo_root: Path,
    write_set: object,
    temporary_directory: Path | None = None,
) -> dict[str, Any]:
    """Apply sealed bytes and validate final tree fingerprints."""

    root = Path(repo_root).expanduser().resolve()
    payload = require_greenfield_repository_preconditions(repo_root=root, write_set=write_set)
    directories = _mapping_rows(payload.get("directories"), label="directories")
    directory_deletes = _mapping_rows(payload.get("directory_deletes"), label="directory_deletes")
    writes = _mapping_rows(payload.get("writes"), label="writes")
    after_files = _require_after_image(payload)
    deletes = _mapping_rows(payload.get("deletes"), label="deletes")

    for row in directories:
        token = str(row["path"])
        _managed_target_path(root=root, token=token)
        greenfield_transaction_path_boundary.ensure_directory(root, token)
    for row in writes:
        token = str(row["path"])
        _managed_target_path(root=root, token=token)
        transaction_atomic_write_bytes(
            root,
            token,
            _decoded_after_image_bytes(after_files[str(row["path"])]),
            mode=int(row["mode"]),
            temporary_directory=temporary_directory,
        )
    for row in deletes:
        token = str(row["path"])
        _managed_target_path(root=root, token=token)
        greenfield_transaction_path_boundary.unlink_file(root, token)
    for row in directory_deletes:
        token = str(row["path"])
        _managed_target_path(root=root, token=token)
        greenfield_transaction_path_boundary.remove_directory(root, token)

    try:
        require_greenfield_repository_after_state(repo_root=root, write_set=payload)
    except ValueError as exc:
        message = str(exc).replace(
            "ProductCreateTransaction committed repository state changed after confirmation",
            "compiled repository write-set readback drifted after materialization",
        )
        raise RuntimeError(message) from exc
    return {
        "version": GREENFIELD_REPOSITORY_WRITE_SET_VERSION,
        "status": "passed",
        "write_set_hash": str(payload["write_set_hash"]),
        "directory_count": len(directories),
        "directory_delete_count": len(directory_deletes),
        "write_count": len(writes),
        "delete_count": len(deletes),
    }


def materialize_compiled_greenfield_after_image(
    *,
    repo_root: Path,
    destination_root: Path,
    write_set: object,
    temporary_directory: Path | None = None,
) -> dict[str, Any]:
    """Materialize the complete pre-confirm after-image without reading live repo bytes."""

    payload = require_compiled_greenfield_repository_write_set(write_set)
    transaction_root = Path(repo_root).expanduser().resolve()
    destination = Path(destination_root).expanduser()
    if not destination.is_absolute():
        destination = transaction_root / destination
    destination_token = greenfield_transaction_path_boundary.relative_token(
        transaction_root,
        destination,
    )
    destination_kind = greenfield_transaction_path_boundary.path_kind(
        transaction_root,
        destination_token,
    )
    if destination_kind not in {"missing", "directory"}:
        raise ValueError("Greenfield generation destination must be a new empty directory")
    if destination_kind == "directory" and greenfield_transaction_path_boundary.scan_tree(
        transaction_root,
        destination_token,
        require_present=True,
    )[1:]:
        raise ValueError("Greenfield generation destination must be a new empty directory")
    root = greenfield_transaction_path_boundary.ensure_directory(
        transaction_root,
        destination_token,
    )
    if temporary_directory is not None:
        greenfield_transaction_path_boundary.relative_token(transaction_root, temporary_directory)
    after_image = payload["after_image"]
    directories = _mapping_rows(after_image.get("directories"), label="after-image directories")
    files = _require_after_image(payload)
    for row in sorted(directories, key=lambda item: (len(Path(str(item["path"])).parts), str(item["path"]))):
        token = str(row["path"])
        _managed_target_path(root=root, token=token)
        greenfield_transaction_path_boundary.ensure_directory(
            transaction_root,
            f"{destination_token}/{token}",
        )
    for path, row in files.items():
        _managed_target_path(root=root, token=path)
        transaction_atomic_write_bytes(
            transaction_root,
            root / path,
            _decoded_after_image_bytes(row),
            mode=int(row["mode"]),
            temporary_directory=temporary_directory,
        )
    require_greenfield_repository_after_state(
        repo_root=transaction_root,
        write_set=payload,
        managed_prefix=destination_token,
    )
    return {
        "version": str(after_image["version"]),
        "status": "passed",
        "write_set_hash": str(payload["write_set_hash"]),
        "directory_count": int(after_image["directory_count"]),
        "file_count": int(after_image["file_count"]),
        "byte_count": int(after_image["byte_count"]),
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


def greenfield_managed_fingerprints(repo_root: Path) -> dict[str, str]:
    """Fingerprint the complete managed boundary used by generation readers."""

    return _managed_fingerprints(Path(repo_root).expanduser().resolve())


def greenfield_repository_recovery_paths(write_set: object) -> tuple[str, ...]:
    """Return affected governed roots whose complete prestate protects rollback."""

    changed = greenfield_repository_write_paths(write_set)
    return tuple(
        root
        for root in GREENFIELD_REPOSITORY_WRITE_PATHS
        if any(path == root or path.startswith(root + "/") for path in changed)
    )


def require_greenfield_repository_recovery_preconditions(*, repo_root: Path, write_set: object) -> dict[str, Any]:
    """Verify only roots restored from an interrupted commit snapshot."""

    payload = require_compiled_greenfield_repository_write_set(write_set)
    root = Path(repo_root).expanduser().resolve()
    expected = _fingerprint_mapping(payload.get("before_fingerprints"), label="before")
    actual = _managed_fingerprints(root)
    changed = [
        path
        for path in greenfield_repository_recovery_paths(payload)
        if actual[path] != expected[path]
    ]
    if changed:
        raise ValueError(
            "ProductCreateTransaction recovery roots changed after rollback: " + ", ".join(changed)
        )
    return payload


def _write_entry(*, path: str, data: bytes, mode: int, previous: bytes | None) -> dict[str, Any]:
    return {
        "path": path,
        "sha256": _sha256(data),
        "previous_sha256": _sha256(previous) if previous is not None else "missing",
        "mode": mode,
    }


def _compile_after_image(
    *,
    files: Mapping[str, tuple[bytes, int]],
    directories: set[str],
) -> dict[str, Any]:
    byte_count = sum(len(state[0]) for state in files.values())
    if byte_count > MAX_SEALED_GENERATION_BYTES:
        raise ValueError(
            "pre-confirm Greenfield package exceeds the sealed generation byte limit"
        )
    rows = [
        {
            "path": path,
            "encoding": "base64",
            "content_base64": base64.b64encode(data).decode("ascii"),
            "sha256": _sha256(data),
            "mode": mode,
        }
        for path, (data, mode) in sorted(files.items())
    ]
    return {
        "version": "odylith.greenfield.repository-after-image.v1",
        "directories": [{"path": path} for path in sorted(directories)],
        "files": rows,
        "directory_count": len(directories),
        "file_count": len(rows),
        "byte_count": byte_count,
    }


def _managed_file_states(root: Path) -> dict[str, tuple[bytes, int]]:
    files: dict[str, tuple[bytes, int]] = {}
    for token in GREENFIELD_REPOSITORY_WRITE_PATHS:
        for entry in _managed_entries(root, token):
            if entry.kind == "file":
                files[entry.path] = (entry.data, entry.mode)
    return files


def _managed_directories(root: Path) -> set[str]:
    directories: set[str] = set()
    for token in GREENFIELD_REPOSITORY_WRITE_PATHS:
        for entry in _managed_entries(root, token):
            if entry.kind == "directory":
                directories.add(entry.path)
    return directories


def _managed_fingerprints(root: Path, *, prefix: str = "") -> dict[str, str]:
    return {
        token: _tree_fingerprint(root=root, token=token, prefix=prefix)
        for token in GREENFIELD_REPOSITORY_WRITE_PATHS
    }


def _tree_fingerprint(*, root: Path, token: str, prefix: str = "") -> str:
    rows: list[dict[str, Any]] = []
    entries = _managed_entries(root, token, prefix=prefix)
    if not entries:
        rows.append({"kind": "missing", "path": token})
    for entry in entries:
        if entry.kind == "directory":
            rows.append({"kind": "directory", "path": entry.path})
        else:
            rows.append(
                {
                    "kind": "file",
                    "path": entry.path,
                    "sha256": _sha256(entry.data),
                    "mode": entry.mode,
                }
            )
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _managed_entries(
    root: Path,
    token: str,
    *,
    prefix: str = "",
) -> tuple[greenfield_transaction_path_boundary.GreenfieldRepositoryEntry, ...]:
    try:
        path = f"{prefix}/{token}" if prefix else token
        entries = greenfield_transaction_path_boundary.scan_tree(root, path)
        if not prefix:
            return entries
        return tuple(
            greenfield_transaction_path_boundary.GreenfieldRepositoryEntry(
                path=Path(entry.path).relative_to(prefix).as_posix(),
                kind=entry.kind,
                data=entry.data,
                mode=entry.mode,
            )
            for entry in entries
        )
    except greenfield_transaction_path_boundary.GreenfieldTransactionPathError as exc:
        raise ValueError(
            f"greenfield repository write-set compilation refuses managed symlink: {token}"
        ) from exc


def _managed_target_path(*, root: Path, token: str) -> Path:
    path = Path(token)
    if path.is_absolute() or ".." in path.parts or not _is_managed_path(token):
        raise RuntimeError(f"compiled repository write escapes the managed boundary: {token}")
    return root / path


def transaction_atomic_write_bytes(
    repo_root: Path,
    path: Path | str,
    data: bytes,
    *,
    mode: int,
    temporary_directory: Path | None,
) -> Path:
    """Single monkeypatchable sink for descriptor-relative sealed writes."""

    return greenfield_transaction_path_boundary.atomic_write_bytes(
        repo_root,
        path,
        data,
        mode=mode,
        temporary_directory=temporary_directory,
    )


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


def _decoded_after_image_bytes(row: Mapping[str, Any]) -> bytes:
    if str(row.get("encoding", "")).strip() != "base64":
        raise ValueError("ProductCreateTransaction repository write has an unsupported encoding")
    try:
        data = base64.b64decode(str(row.get("content_base64", "")), validate=True)
    except ValueError as exc:
        raise ValueError("ProductCreateTransaction repository write is not valid base64") from exc
    if _sha256(data) != str(row.get("sha256", "")).strip():
        raise ValueError("ProductCreateTransaction repository write payload hash mismatch")
    return data


def _require_after_image(payload: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    value = payload.get("after_image")
    if not isinstance(value, Mapping) or str(value.get("version", "")).strip() != (
        "odylith.greenfield.repository-after-image.v1"
    ):
        raise ValueError("ProductCreateTransaction repository after-image is missing")
    directories = _mapping_rows(value.get("directories"), label="after-image directories")
    files = _mapping_rows(value.get("files"), label="after-image files")
    directory_paths = _validated_paths(directories, label="after-image directory")
    file_paths = _validated_paths(files, label="after-image file")
    if directory_paths != sorted(directory_paths) or file_paths != sorted(file_paths):
        raise ValueError("ProductCreateTransaction repository after-image is not in deterministic order")
    _require_count(value, "directory_count", directories)
    _require_count(value, "file_count", files)
    file_map: dict[str, Mapping[str, Any]] = {}
    byte_count = 0
    for row in files:
        data = _decoded_after_image_bytes(row)
        mode = row.get("mode")
        if not isinstance(mode, int) or mode < 0 or mode > 0o777:
            raise ValueError("ProductCreateTransaction repository after-image has an invalid file mode")
        byte_count += len(data)
        file_map[str(row["path"])] = row
    if byte_count != value.get("byte_count") or byte_count > MAX_SEALED_GENERATION_BYTES:
        raise ValueError("ProductCreateTransaction repository after-image has an invalid byte count")
    expected = _fingerprint_mapping(payload.get("after_fingerprints"), label="after")
    actual = _after_image_fingerprints(directories=set(directory_paths), files=file_map)
    if actual != expected:
        changed = sorted(path for path in set(expected) | set(actual) if expected.get(path) != actual.get(path))
        detail = ", ".join(changed) or "unknown managed path"
        raise ValueError(
            "ProductCreateTransaction repository after-image fingerprint mismatch for " + detail
        )
    return file_map


def _after_image_fingerprints(
    *,
    directories: set[str],
    files: Mapping[str, Mapping[str, Any]],
) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for token in GREENFIELD_REPOSITORY_WRITE_PATHS:
        rows: list[dict[str, Any]] = []
        if token in files:
            row = files[token]
            rows.append(
                {
                    "kind": "file",
                    "path": token,
                    "sha256": str(row["sha256"]),
                    "mode": int(row["mode"]),
                }
            )
        elif token in directories:
            rows.append({"kind": "directory", "path": token})
            descendants = sorted(
                set(path for path in directories if path.startswith(token + "/"))
                | set(path for path in files if path.startswith(token + "/")),
                key=lambda path: Path(path).parts,
            )
            for path in descendants:
                if path in directories:
                    rows.append({"kind": "directory", "path": path})
                else:
                    row = files[path]
                    rows.append(
                        {
                            "kind": "file",
                            "path": path,
                            "sha256": str(row["sha256"]),
                            "mode": int(row["mode"]),
                        }
                    )
        else:
            rows.append({"kind": "missing", "path": token})
        canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        fingerprints[token] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return fingerprints


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
    if any(not is_sha256_digest(item) for item in result.values()):
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
    "MAX_SEALED_GENERATION_BYTES",
    "apply_compiled_greenfield_repository_write_set",
    "compile_greenfield_repository_write_set",
    "greenfield_managed_fingerprints",
    "greenfield_repository_recovery_paths",
    "greenfield_repository_write_paths",
    "materialize_compiled_greenfield_after_image",
    "require_compiled_greenfield_repository_write_set",
    "require_greenfield_repository_after_state",
    "require_greenfield_repository_preconditions",
    "require_greenfield_repository_recovery_preconditions",
]
