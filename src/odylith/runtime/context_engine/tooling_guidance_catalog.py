"""Compiled guidance-catalog support for Odylith Context Engine.

This module keeps the tracked manifest under
`agents-guidelines/indexable-guidance-chunks.v1.json` authoritative while
providing a derived local cache that the runtime can reuse repeatedly without
reparsing every chunk body on every request.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.context_engine import odylith_context_cache

CATALOG_VERSION = "v1"
CANONICAL_MANIFEST_PATH = "odylith/agents-guidelines/indexable-guidance-chunks.v1.json"
LEGACY_MANIFEST_PATHS = ("agents-guidelines/indexable-guidance-chunks.v1.json",)
MANIFEST_PATH = CANONICAL_MANIFEST_PATH
_PROCESS_COMPILED_CATALOG_CACHE: dict[str, tuple[str, dict[str, Any]]] = {}


def compiled_catalog_path(*, repo_root: Path) -> Path:
    """Return the local compiled guidance-catalog cache path."""

    return odylith_context_cache.cache_path(
        repo_root=repo_root,
        namespace="guidance",
        key=f"compiled-catalog-{CATALOG_VERSION}",
    )


def _normalized_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    seen: set[str] = set()
    rows: list[str] = []
    for item in value:
        token = str(item or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def resolve_manifest_path(*, repo_root: Path) -> tuple[Path, str]:
    root = Path(repo_root).resolve()
    for relative in (CANONICAL_MANIFEST_PATH, *LEGACY_MANIFEST_PATHS):
        candidate = (root / relative).resolve()
        if candidate.is_file():
            return candidate, relative
    return (root / CANONICAL_MANIFEST_PATH).resolve(), CANONICAL_MANIFEST_PATH


def _source_fingerprint(*, repo_root: Path, manifest_payload: Mapping[str, Any]) -> str:
    manifest_path, _manifest_relative = resolve_manifest_path(repo_root=repo_root)
    chunk_paths: list[Path] = []
    for item in manifest_payload.get("chunks", []):
        if not isinstance(item, Mapping):
            continue
        chunk_path = str(item.get("chunk_path", "")).strip()
        if not chunk_path:
            continue
        chunk_paths.append((repo_root / chunk_path).resolve())
    return odylith_context_cache.fingerprint_paths([manifest_path, *chunk_paths])


def compile_guidance_catalog(*, repo_root: Path) -> dict[str, Any]:
    """Compile the tracked chunk manifest plus chunk files into one catalog."""

    root = Path(repo_root).resolve()
    manifest_file, manifest_relative = resolve_manifest_path(repo_root=root)
    manifest_payload = odylith_context_cache.read_json_object(manifest_file)
    chunks = manifest_payload.get("chunks", [])
    if not isinstance(chunks, list):
        chunks = []
    compiled_chunks: list[dict[str, Any]] = []
    note_kind_counts: dict[str, int] = {}
    task_family_counts: dict[str, int] = {}
    canonical_sources: set[str] = set()
    for item in chunks:
        if not isinstance(item, Mapping):
            continue
        chunk_id = str(item.get("chunk_id", "")).strip()
        chunk_path = str(item.get("chunk_path", "")).strip()
        canonical_source = str(item.get("canonical_source", "")).strip()
        note_kind = str(item.get("note_kind", "")).strip()
        if not chunk_id or not chunk_path or not canonical_source or not note_kind:
            continue
        resolved_chunk_path = (root / chunk_path).resolve()
        if not resolved_chunk_path.is_file():
            continue
        text = resolved_chunk_path.read_text(encoding="utf-8")
        task_families = _normalized_list(item.get("task_families"))
        compiled_chunk = {
            "chunk_id": chunk_id,
            "note_kind": note_kind,
            "canonical_source": canonical_source,
            "chunk_path": chunk_path,
            "title": str(item.get("title", "")).strip(),
            "section": str(item.get("section", "")).strip(),
            "summary": str(item.get("summary", "")).strip(),
            "tags": _normalized_list(item.get("tags")),
            "task_families": task_families,
            "risk_class": str(item.get("risk_class", "")).strip(),
            "component_affinity": _normalized_list(item.get("component_affinity")),
            "path_prefixes": _normalized_list(item.get("path_prefixes")),
            "path_refs": _normalized_list(item.get("path_refs")),
            "workstreams": _normalized_list(item.get("workstreams")),
            "content_bytes": len(text.encode("utf-8")),
            "line_count": len(text.splitlines()),
            "content_fingerprint": odylith_context_cache.fingerprint_payload(text),
        }
        compiled_chunks.append(compiled_chunk)
        canonical_sources.add(canonical_source)
        note_kind_counts[note_kind] = int(note_kind_counts.get(note_kind, 0)) + 1
        for family in task_families:
            task_family_counts[family] = int(task_family_counts.get(family, 0)) + 1
    source_fingerprint = _source_fingerprint(repo_root=root, manifest_payload=manifest_payload)
    task_families = sorted(task_family_counts)
    payload = {
        "version": CATALOG_VERSION,
        "manifest_path": manifest_relative,
        "canonical_manifest_path": CANONICAL_MANIFEST_PATH,
        "compiled_catalog_path": str(compiled_catalog_path(repo_root=root).relative_to(root)),
        "source_fingerprint": source_fingerprint,
        "catalog_fingerprint": odylith_context_cache.fingerprint_payload(compiled_chunks),
        "chunk_count": len(compiled_chunks),
        "source_doc_count": len(canonical_sources),
        "note_kind_counts": note_kind_counts,
        "task_family_count": len(task_families),
        "task_families": task_families,
        "task_family_counts": task_family_counts,
        "chunks": compiled_chunks,
    }
    return payload


def clear_process_guidance_catalog_cache(*, repo_root: Path | None = None) -> None:
    """Clear the in-process compiled guidance-catalog cache."""

    if repo_root is None:
        _PROCESS_COMPILED_CATALOG_CACHE.clear()
        return
    _PROCESS_COMPILED_CATALOG_CACHE.pop(str(Path(repo_root).resolve()), None)


def load_guidance_catalog(*, repo_root: Path, persist: bool = True) -> dict[str, Any]:
    """Load the compiled guidance catalog, rebuilding when the sources changed."""

    root = Path(repo_root).resolve()
    manifest_file, _manifest_relative = resolve_manifest_path(repo_root=root)
    manifest_payload = odylith_context_cache.read_json_object(manifest_file)
    source_fingerprint = _source_fingerprint(repo_root=root, manifest_payload=manifest_payload)
    process_cache_key = str(root)
    cached_process = _PROCESS_COMPILED_CATALOG_CACHE.get(process_cache_key)
    if cached_process is not None and cached_process[0] == source_fingerprint:
        return dict(cached_process[1])
    cache_path = compiled_catalog_path(repo_root=root)
    cached = odylith_context_cache.read_json_object(cache_path)
    if (
        cached.get("version") == CATALOG_VERSION
        and str(cached.get("source_fingerprint", "")).strip() == source_fingerprint
        and isinstance(cached.get("chunks"), list)
    ):
        _PROCESS_COMPILED_CATALOG_CACHE[process_cache_key] = (source_fingerprint, dict(cached))
        return dict(cached)
    compiled = compile_guidance_catalog(repo_root=root)
    if persist:
        odylith_context_cache.write_json_if_changed(
            repo_root=root,
            path=cache_path,
            payload=compiled,
            lock_key=str(cache_path),
        )
    _PROCESS_COMPILED_CATALOG_CACHE[process_cache_key] = (source_fingerprint, dict(compiled))
    return dict(compiled)


def compact_catalog_summary(catalog: Mapping[str, Any]) -> dict[str, Any]:
    """Return a small, packet-safe summary of a compiled guidance catalog."""

    return {
        "version": str(catalog.get("version", "")).strip(),
        "manifest_path": str(catalog.get("manifest_path", "")).strip(),
        "chunk_count": int(catalog.get("chunk_count", 0) or 0),
        "source_doc_count": int(catalog.get("source_doc_count", 0) or 0),
        "task_family_count": int(catalog.get("task_family_count", 0) or 0),
        "task_families": sorted(_normalized_list(catalog.get("task_families"))),
        "catalog_fingerprint": str(catalog.get("catalog_fingerprint", "")).strip(),
        "source_fingerprint": str(catalog.get("source_fingerprint", "")).strip(),
        "note_kind_counts": dict(catalog.get("note_kind_counts", {}))
        if isinstance(catalog.get("note_kind_counts"), Mapping)
        else {},
        "task_family_counts": dict(catalog.get("task_family_counts", {}))
        if isinstance(catalog.get("task_family_counts"), Mapping)
        else {},
    }


__all__ = [
    "CATALOG_VERSION",
    "CANONICAL_MANIFEST_PATH",
    "LEGACY_MANIFEST_PATHS",
    "MANIFEST_PATH",
    "clear_process_guidance_catalog_cache",
    "compact_catalog_summary",
    "compile_guidance_catalog",
    "compiled_catalog_path",
    "load_guidance_catalog",
    "resolve_manifest_path",
]
