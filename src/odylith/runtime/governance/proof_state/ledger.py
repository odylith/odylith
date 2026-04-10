from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_PROOF_SURFACES_PATH = (".odylith", "runtime", "odylith-proof-surfaces.v1.json")
_LIVE_PROOF_SECTION = "live_proof_lanes"


def proof_surfaces_path(*, repo_root: Path) -> Path:
    return Path(repo_root).resolve().joinpath(*_PROOF_SURFACES_PATH)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_live_proof_lanes(*, repo_root: Path) -> dict[str, dict[str, Any]]:
    payload = _read_json(proof_surfaces_path(repo_root=repo_root))
    section = payload.get(_LIVE_PROOF_SECTION, {})
    if not isinstance(section, dict):
        return {}
    return {
        str(lane_id).strip(): dict(row)
        for lane_id, row in section.items()
        if str(lane_id).strip() and isinstance(row, dict)
    }


def persist_live_proof_lanes(*, repo_root: Path, live_proof_lanes: dict[str, dict[str, Any]]) -> Path:
    path = proof_surfaces_path(repo_root=repo_root)
    payload = _read_json(path)
    payload["contract"] = "odylith_proof_surfaces.v1"
    payload[_LIVE_PROOF_SECTION] = live_proof_lanes
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
