"""Neutral JSON and deterministic-law support for Greenfield release evidence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
import os
from pathlib import Path
from typing import Any


DETERMINISTIC_LAW_REPORT_VERSION = "odylith.greenfield.deterministic-law-report.v3"
REQUIRED_DETERMINISTIC_LAW_IDS = (
    "no_post_confirm_semantic_or_model_work",
    "exact_sealed_byte_publication",
    "no_unsupported_accepted_facts_at_type_boundary",
    "idempotent_retry",
    "no_temporary_paths",
    "no_destructive_clipping",
    "no_partial_visible_generation_under_injected_failure",
)


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def greenfield_runtime_source_fingerprint() -> str:
    """Hash the exact Greenfield runtime and release source set used by evidence."""

    root = Path(__file__).resolve().parents[2]
    paths = sorted(
        {
            *root.glob("src/odylith/runtime/domain_intelligence/greenfield_*.py"),
            *root.glob("scripts/release/greenfield_*.py"),
        },
        key=lambda path: path.relative_to(root).as_posix(),
    )
    if not paths:
        raise RuntimeError("Greenfield runtime source set is unavailable")
    digest = hashlib.sha256()
    for path in paths:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def safe_json_file(path: Path | str, label: str) -> Path:
    expanded = Path(path).expanduser()
    if expanded.is_symlink():
        raise RuntimeError(f"{label} is missing or unsafe")
    candidate = expanded.resolve()
    if not candidate.is_file():
        raise RuntimeError(f"{label} is missing or unsafe")
    return candidate


def json_mapping(path: Path, label: str) -> dict[str, Any]:
    try:
        return mapping(json.loads(path.read_text(encoding="utf-8")), label)
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"{label} is unreadable: {error}") from error


def exclusive_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as error:
        raise RuntimeError(f"release evidence output already exists: {path}") from error
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(value), sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label} must be a JSON object")
    return dict(value)


def mapped_rows(value: Any, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(row, Mapping) for row in value):
        raise RuntimeError(f"{label} must be a JSON object array")
    return [dict(row) for row in value]


def unique_index(
    rows: Sequence[Mapping[str, Any]], key: str, label: str
) -> dict[str, Mapping[str, Any]]:
    indexed: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        value = text(row.get(key), f"{label}.{key}", maximum=200)
        if value in indexed:
            raise RuntimeError(f"{label} contains duplicate {key}: {value}")
        indexed[value] = row
    return indexed


def exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise RuntimeError(f"{label} fields do not match the versioned contract")


def text(value: Any, label: str, *, maximum: int) -> str:
    result = str(value or "").strip()
    if not result or len(result) > maximum:
        raise RuntimeError(f"{label} must be bounded non-empty text")
    return result


def require_sha256(value: Any, label: str, *, length: int = 64) -> str:
    result = text(value, label, maximum=length)
    if len(result) != length or any(character not in "0123456789abcdef" for character in result):
        raise RuntimeError(f"{label} must be a lowercase SHA-256 digest")
    return result


def positive_integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RuntimeError(f"{label} must be a positive integer")
    return value


__all__ = [
    "DETERMINISTIC_LAW_REPORT_VERSION",
    "REQUIRED_DETERMINISTIC_LAW_IDS",
    "canonical_sha256",
    "exact_keys",
    "exclusive_json",
    "greenfield_runtime_source_fingerprint",
    "json_mapping",
    "mapped_rows",
    "mapping",
    "positive_integer",
    "require_sha256",
    "safe_json_file",
    "text",
    "unique_index",
]
