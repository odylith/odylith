"""Ledger helpers for the Odylith governance proof state layer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from odylith.common.json_objects import load_json_object
from .contract import normalize_proof_lane_id

_PROOF_SURFACES_PATH = (".odylith", "runtime", "odylith-proof-surfaces.v1.json")
_LIVE_PROOF_SECTION = "live_proof_lanes"


def proof_surfaces_path(*, repo_root: Path) -> Path:
    return Path(repo_root).resolve().joinpath(*_PROOF_SURFACES_PATH)


def _read_json(path: Path) -> dict[str, Any]:
    return load_json_object(path)


def load_live_proof_lanes(*, repo_root: Path) -> dict[str, dict[str, Any]]:
    payload = _read_json(proof_surfaces_path(repo_root=repo_root))
    section = payload.get(_LIVE_PROOF_SECTION, {})
    if not isinstance(section, dict):
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for lane_id, row in section.items():
        normalized_lane_id = normalize_proof_lane_id(lane_id)
        if not normalized_lane_id or not isinstance(row, dict):
            continue
        lane = dict(rows.get(normalized_lane_id, {}))
        lane.update(dict(row))
        lane["lane_id"] = normalize_proof_lane_id(lane.get("lane_id") or normalized_lane_id)
        rows[normalized_lane_id] = lane
    return rows


def persist_live_proof_lanes(*, repo_root: Path, live_proof_lanes: dict[str, dict[str, Any]]) -> Path:
    path = proof_surfaces_path(repo_root=repo_root)
    payload = _read_json(path)
    payload["contract"] = "odylith_proof_surfaces.v1"
    normalized_rows: dict[str, dict[str, Any]] = {}
    for lane_id, row in live_proof_lanes.items():
        normalized_lane_id = normalize_proof_lane_id(lane_id)
        if not normalized_lane_id or not isinstance(row, dict):
            continue
        lane = dict(row)
        lane["lane_id"] = normalize_proof_lane_id(lane.get("lane_id") or normalized_lane_id)
        normalized_rows[normalized_lane_id] = lane
    payload[_LIVE_PROOF_SECTION] = normalized_rows
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if path.is_file():
        try:
            if path.read_text(encoding="utf-8") == rendered:
                return path
        except OSError:
            pass
    path.write_text(rendered, encoding="utf-8")
    return path
