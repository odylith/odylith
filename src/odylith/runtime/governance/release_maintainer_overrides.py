"""Release Maintainer Overrides helpers for the Odylith governance layer."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

_OVERRIDES_PATH = Path("odylith/runtime/source/release-maintainer-overrides.v1.json")


@dataclass(frozen=True)
class BenchmarkProofOverride:
    version: str
    mode: str
    reason: str
    owner: str
    updated_utc: str


def load_benchmark_proof_override(*, repo_root: str | Path, version: str) -> BenchmarkProofOverride | None:
    normalized_version = str(version or "").strip()
    if not normalized_version:
        return None
    path = Path(repo_root).expanduser().resolve() / _OVERRIDES_PATH
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, Mapping):
        return None
    entries = payload.get("benchmark_proof_overrides")
    if not isinstance(entries, list):
        return None
    for raw_entry in entries:
        if not isinstance(raw_entry, Mapping):
            continue
        entry_version = str(raw_entry.get("version") or "").strip()
        if entry_version != normalized_version:
            continue
        mode = str(raw_entry.get("mode") or "").strip()
        reason = str(raw_entry.get("reason") or "").strip()
        owner = str(raw_entry.get("owner") or "").strip()
        updated_utc = str(raw_entry.get("updated_utc") or "").strip()
        if not mode or not reason:
            continue
        return BenchmarkProofOverride(
            version=entry_version,
            mode=mode,
            reason=reason,
            owner=owner,
            updated_utc=updated_utc,
        )
    return None
