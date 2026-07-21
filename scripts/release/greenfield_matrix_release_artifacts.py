"""Shared filesystem and digest checks for release-corpus evidence artifacts."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from typing import Mapping


_SAFE_ARTIFACT_IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9-]{0,127}\Z")
RELEASE_PROOF_INPUT_SNAPSHOT_VERSION = "odylith.greenfield.release-input-snapshot.v1"
RELEASE_PROOF_INPUT_SNAPSHOT_FILENAME = "release-proof-input-snapshot.v1.json"


def is_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def is_sha256(value: str) -> bool:
    return bool(value) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def safe_artifact_identifier(value: str) -> str | None:
    """Return a portable identifier that is safe to use in an artifact filename."""

    candidate = str(value or "").strip()
    return candidate if _SAFE_ARTIFACT_IDENTIFIER.fullmatch(candidate) else None


def repo_artifact_path(root: Path, value: str) -> Path | None:
    candidate = Path(value)
    if not value or candidate.is_absolute():
        return None
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return None
    return resolved


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def release_proof_input_snapshot_manifest_path(root: Path) -> Path:
    return Path(root).expanduser().resolve() / RELEASE_PROOF_INPUT_SNAPSHOT_FILENAME


def write_release_proof_input_snapshot_manifest(
    *,
    root: Path,
    case_files: Sequence[Path],
    audit_file: Path,
    input_references: Sequence[Mapping[str, Any]],
) -> Path:
    """Persist the immutable input contract consumed by one release-proof shard."""

    snapshot_root = Path(root).expanduser().resolve()
    manifest_path = release_proof_input_snapshot_manifest_path(snapshot_root)
    payload = {
        "version": RELEASE_PROOF_INPUT_SNAPSHOT_VERSION,
        "snapshot_root": str(snapshot_root),
        "case_files": [_snapshot_relative_path(snapshot_root, path) for path in case_files],
        "audit_file": _snapshot_relative_path(snapshot_root, audit_file),
        "input_references": [
            {
                "kind": str(reference.get("kind") or "release-proof-input"),
                "path": _snapshot_relative_path(snapshot_root, Path(str(reference.get("path") or ""))),
                "sha256": str(reference.get("sha256") or ""),
            }
            for reference in input_references
        ],
    }
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def release_proof_input_snapshot_issues(
    *,
    root: Path,
    case_files: Sequence[Path],
    audit_file: Path,
) -> tuple[str, ...]:
    """Validate a campaign-created snapshot before any release evidence is loaded."""

    snapshot_root = Path(root).expanduser().resolve()
    manifest_path = release_proof_input_snapshot_manifest_path(snapshot_root)
    if not manifest_path.is_file():
        return ("release proof sealed input manifest is missing",)
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return (f"release proof sealed input manifest is unreadable: {exc}",)
    if not isinstance(payload, Mapping):
        return ("release proof sealed input manifest must be an object",)
    if payload.get("version") != RELEASE_PROOF_INPUT_SNAPSHOT_VERSION:
        return ("release proof sealed input manifest has an unsupported version",)
    if str(payload.get("snapshot_root") or "") != str(snapshot_root):
        return ("release proof sealed input manifest does not bind this input root",)

    expected_cases = tuple(_snapshot_relative_path(snapshot_root, path) for path in case_files)
    expected_audit = _snapshot_relative_path(snapshot_root, audit_file)
    if payload.get("case_files") != list(expected_cases) or payload.get("audit_file") != expected_audit:
        return ("release proof sealed input manifest does not match the selected case and audit files",)

    references = payload.get("input_references")
    if not isinstance(references, list) or not references:
        return ("release proof sealed input manifest has no hash-bound inputs",)
    issues: list[str] = []
    bound_paths: set[str] = set()
    for reference in references:
        if not isinstance(reference, Mapping):
            issues.append("release proof sealed input manifest has an invalid input reference")
            continue
        relative_path = str(reference.get("path") or "")
        expected_hash = str(reference.get("sha256") or "")
        artifact = repo_artifact_path(snapshot_root, relative_path)
        if artifact is None or not artifact.is_file():
            issues.append(f"release proof sealed input is missing: {relative_path or '<unnamed>'}")
            continue
        if not is_sha256(expected_hash):
            issues.append(f"release proof sealed input is not hash-bound: {relative_path}")
            continue
        if sha256_file(artifact) != expected_hash:
            issues.append(f"release proof sealed input hash changed: {relative_path}")
            continue
        bound_paths.add(relative_path)
    if expected_audit not in bound_paths or any(path not in bound_paths for path in expected_cases):
        issues.append("release proof sealed input manifest does not bind every selected case and audit file")
    return tuple(dict.fromkeys(issues))


def _snapshot_relative_path(root: Path, path: Path) -> str:
    candidate = Path(path).expanduser().resolve()
    try:
        return str(candidate.relative_to(root))
    except ValueError as exc:
        raise RuntimeError(f"release proof snapshot input is outside the sealed root: {candidate}") from exc
