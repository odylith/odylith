"""One-shot disclosure ledger for the frozen Greenfield final holdout.

The exclusive claim is deliberately written before any protected input is
opened.  The same claimant then binds exact input hashes while the ledger is
still in its only terminalizable state.
"""

from __future__ import annotations

from collections.abc import Mapping
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any


FINAL_HOLDOUT_RUN_LEDGER_VERSION = "odylith.greenfield.final-holdout-run.v2"
_REVISION_RE = re.compile(r"[0-9a-f]{40}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_INPUT_LABEL_RE = re.compile(r"[a-z][a-z0-9_]{0,63}")


def claim_final_holdout_run(
    *,
    ledger_path: Path,
    implementation_revision: str,
    distribution_provenance_sha256: str,
) -> dict[str, Any]:
    """Atomically consume the one release attempt before protected disclosure."""

    revision = str(implementation_revision or "").strip().casefold()
    if not _REVISION_RE.fullmatch(revision):
        raise RuntimeError("final holdout run requires a full implementation Git revision")
    provenance_sha256 = str(distribution_provenance_sha256 or "").strip().casefold()
    if not _SHA256_RE.fullmatch(provenance_sha256):
        raise RuntimeError("final holdout run requires exact distribution provenance")
    ledger = Path(ledger_path).expanduser().resolve()
    payload = {
        "version": FINAL_HOLDOUT_RUN_LEDGER_VERSION,
        "status": "claimed",
        "disclosed": True,
        "protected_inputs_bound": False,
        "protected_inputs": {},
        "implementation_revision": revision,
        "distribution_provenance_sha256": provenance_sha256,
        "claimed_at_utc": _now_utc(),
    }
    ledger.parent.mkdir(parents=True, exist_ok=True)
    _exclusive_write_json(ledger, payload)
    _fsync_directory(ledger.parent)
    return payload


def bind_final_holdout_inputs(
    *,
    ledger_path: Path,
    protected_inputs: Mapping[str, Path],
) -> dict[str, Any]:
    """Hash protected inputs only after the exclusive disclosure claim exists."""

    ledger = _safe_file(ledger_path, label="final holdout run ledger")
    payload = _json_object(ledger)
    if (
        payload.get("version") != FINAL_HOLDOUT_RUN_LEDGER_VERSION
        or payload.get("status") != "claimed"
        or payload.get("protected_inputs_bound") is not False
        or payload.get("protected_inputs") != {}
    ):
        raise RuntimeError("final holdout run ledger is not in its one bindable claimed state")
    if not isinstance(protected_inputs, Mapping) or not protected_inputs:
        raise RuntimeError("final holdout run requires protected inputs")
    bound: dict[str, dict[str, str]] = {}
    for raw_label, raw_path in sorted(protected_inputs.items(), key=lambda item: str(item[0])):
        label = str(raw_label or "").strip()
        if not _INPUT_LABEL_RE.fullmatch(label) or label in bound:
            raise RuntimeError("final holdout run has an invalid protected input label")
        path = _safe_file(Path(raw_path), label=f"protected input {label}")
        bound[label] = {
            "filename": path.name,
            "sha256": _sha256_file(path),
        }
    updated = {
        **payload,
        "protected_inputs_bound": True,
        "protected_inputs": bound,
        "protected_inputs_bound_at_utc": _now_utc(),
    }
    _replace_json(ledger, updated)
    return updated


def complete_final_holdout_run(
    *,
    ledger_path: Path,
    result_path: Path,
    outcome: str,
) -> dict[str, Any]:
    """Bind the terminal proof payload without allowing a second claim."""

    ledger = _safe_file(ledger_path, label="final holdout run ledger")
    result = _safe_file(result_path, label="final holdout result")
    payload = _json_object(ledger)
    if payload.get("version") != FINAL_HOLDOUT_RUN_LEDGER_VERSION or payload.get("status") != "claimed":
        raise RuntimeError("final holdout run ledger is not in its one terminalizable claimed state")
    terminal = str(outcome or "").strip().casefold()
    if terminal not in {"passed", "failed", "interrupted"}:
        raise RuntimeError("final holdout outcome must be passed, failed, or interrupted")
    if terminal == "passed" and (
        payload.get("protected_inputs_bound") is not True
        or not isinstance(payload.get("protected_inputs"), Mapping)
        or not payload.get("protected_inputs")
    ):
        raise RuntimeError("a passing final holdout run requires bound protected inputs")
    completed = {
        **payload,
        "status": terminal,
        "result_sha256": _sha256_file(result),
        "completed_at_utc": _now_utc(),
    }
    _replace_json(ledger, completed)
    return completed


def read_final_holdout_run(ledger_path: Path) -> dict[str, Any]:
    return _json_object(_safe_file(ledger_path, label="final holdout run ledger"))


def _exclusive_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as error:
        raise RuntimeError("final holdout hash was already claimed and cannot be rerun") from error
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(payload), sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _replace_json(path: Path, payload: Mapping[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        _exclusive_write_json(temporary, payload)
        temporary.replace(path)
        _fsync_directory(path.parent)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"final holdout ledger is unreadable: {error}") from error
    if not isinstance(payload, Mapping):
        raise RuntimeError("final holdout ledger must be a JSON object")
    return dict(payload)


def _safe_file(path: Path, *, label: str) -> Path:
    expanded = Path(path).expanduser()
    if expanded.is_symlink():
        raise RuntimeError(f"{label} is missing or unsafe")
    candidate = expanded.resolve()
    if not candidate.is_file():
        raise RuntimeError(f"{label} is missing or unsafe")
    return candidate


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


__all__ = [
    "FINAL_HOLDOUT_RUN_LEDGER_VERSION",
    "bind_final_holdout_inputs",
    "claim_final_holdout_run",
    "complete_final_holdout_run",
    "read_final_holdout_run",
]
