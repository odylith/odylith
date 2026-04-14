"""Fingerprint-gated surface refresh reuse for dashboard and owned-surface lanes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from typing import Iterable
from typing import Mapping

from odylith.runtime.common.consumer_profile import truth_root_path
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.context_engine import odylith_context_engine_store
from odylith.runtime.context_engine.surface_projection_fingerprint import (
    default_surface_projection_input_fingerprint,
)


_MANIFEST_PATH = Path(".odylith/runtime/latency-cache/surface-refresh-dag.v1.json")
_VERSION = "v1"


def can_reuse_surface_refresh(
    *,
    repo_root: Path,
    surface: str,
    atlas_sync: bool,
    outputs: Iterable[str],
) -> tuple[bool, dict[str, Any]]:
    root = Path(repo_root).resolve()
    surface_token = str(surface).strip().lower()
    input_fingerprint = surface_input_fingerprint(
        repo_root=root,
        surface=surface_token,
        atlas_sync=atlas_sync,
    )
    output_fingerprint, outputs_exist = surface_output_fingerprint(
        repo_root=root,
        outputs=outputs,
    )
    manifest = _load_manifest(repo_root=root)
    entries = dict(manifest.get("surfaces", {})) if isinstance(manifest.get("surfaces"), Mapping) else {}
    cached = dict(entries.get(_entry_key(surface=surface_token, atlas_sync=atlas_sync), {}))
    reusable = bool(
        outputs_exist
        and cached
        and str(cached.get("input_fingerprint", "")).strip() == input_fingerprint
        and str(cached.get("output_fingerprint", "")).strip() == output_fingerprint
    )
    return reusable, {
        "input_fingerprint": input_fingerprint,
        "output_fingerprint": output_fingerprint,
        "outputs_exist": outputs_exist,
    }


def record_surface_refresh(
    *,
    repo_root: Path,
    surface: str,
    atlas_sync: bool,
    outputs: Iterable[str],
    details: Mapping[str, Any] | None = None,
) -> None:
    root = Path(repo_root).resolve()
    surface_token = str(surface).strip().lower()
    manifest = _load_manifest(repo_root=root)
    entries = dict(manifest.get("surfaces", {})) if isinstance(manifest.get("surfaces"), Mapping) else {}
    input_fingerprint = surface_input_fingerprint(
        repo_root=root,
        surface=surface_token,
        atlas_sync=atlas_sync,
    )
    output_fingerprint, outputs_exist = surface_output_fingerprint(
        repo_root=root,
        outputs=outputs,
    )
    entries[_entry_key(surface=surface_token, atlas_sync=atlas_sync)] = {
        "surface": surface_token,
        "atlas_sync": bool(atlas_sync),
        "input_fingerprint": input_fingerprint,
        "output_fingerprint": output_fingerprint,
        "outputs_exist": bool(outputs_exist),
        "details": dict(details) if isinstance(details, Mapping) else {},
    }
    _write_manifest(
        repo_root=root,
        payload={
            "version": _VERSION,
            "surfaces": entries,
        },
    )


def surface_input_fingerprint(*, repo_root: Path, surface: str, atlas_sync: bool) -> str:
    root = Path(repo_root).resolve()
    token = str(surface).strip().lower()
    if token in {"compass", "radar", "tooling_shell"}:
        return odylith_context_cache.fingerprint_payload(
            {
                "surface": token,
                "atlas_sync": bool(atlas_sync),
                "projection": default_surface_projection_input_fingerprint(repo_root=root),
                "delivery": odylith_context_cache.path_signature(
                    root / "odylith/runtime/delivery_intelligence.v4.json",
                ),
            }
        )
    if token == "casebook":
        bugs_root = truth_root_path(repo_root=root, key="casebook_bugs")
        return odylith_context_cache.fingerprint_payload(
            {
                "surface": token,
                "bugs": odylith_context_cache.fingerprint_tree(bugs_root),
            }
        )
    if token == "registry":
        specs_root = truth_root_path(repo_root=root, key="component_specs")
        manifest_path = truth_root_path(repo_root=root, key="component_registry")
        return odylith_context_cache.fingerprint_payload(
            {
                "surface": token,
                "components": odylith_context_cache.fingerprint_tree(specs_root),
                "manifest": odylith_context_cache.fingerprint_paths([manifest_path]),
                "delivery": odylith_context_cache.path_signature(
                    root / "odylith/runtime/delivery_intelligence.v4.json",
                ),
            }
        )
    if token == "atlas":
        atlas_root = root / "odylith" / "atlas" / "source"
        return odylith_context_cache.fingerprint_payload(
            {
                "surface": token,
                "atlas_sync": bool(atlas_sync),
                "catalog": odylith_context_cache.path_signature(atlas_root / "catalog" / "diagrams.v1.json"),
                "mmd": odylith_context_cache.fingerprint_tree(atlas_root, glob="*.mmd"),
            }
        )
    return odylith_context_cache.fingerprint_payload(
        {
            "surface": token,
            "atlas_sync": bool(atlas_sync),
            "projection": odylith_context_engine_store.projection_input_fingerprint(
                repo_root=root,
                scope="default",
            ),
        }
    )


def surface_output_fingerprint(*, repo_root: Path, outputs: Iterable[str]) -> tuple[str, bool]:
    root = Path(repo_root).resolve()
    expanded: list[Path] = []
    for token in outputs:
        pattern = str(token).strip()
        if not pattern:
            continue
        if "*" in pattern or "?" in pattern or "[" in pattern:
            expanded.extend(sorted(root.glob(pattern)))
            continue
        candidate = (root / pattern).resolve()
        if candidate.exists():
            expanded.append(candidate)
    if not expanded:
        return (
            odylith_context_cache.fingerprint_payload({"outputs": []}),
            False,
        )
    return (
        odylith_context_cache.fingerprint_paths(expanded),
        True,
    )


def _entry_key(*, surface: str, atlas_sync: bool) -> str:
    return f"{str(surface).strip().lower()}:{'atlas-sync' if atlas_sync else 'default'}"


def _load_manifest(*, repo_root: Path) -> dict[str, Any]:
    path = (Path(repo_root).resolve() / _MANIFEST_PATH).resolve()
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def _write_manifest(*, repo_root: Path, payload: Mapping[str, Any]) -> None:
    path = (Path(repo_root).resolve() / _MANIFEST_PATH).resolve()
    odylith_context_cache.write_json_if_changed(
        repo_root=repo_root,
        path=path,
        payload=dict(payload),
    )


__all__ = [
    "can_reuse_surface_refresh",
    "record_surface_refresh",
    "surface_input_fingerprint",
    "surface_output_fingerprint",
]
