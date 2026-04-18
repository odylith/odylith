"""Compiled projection bundle helpers for the Odylith Context Engine.

This bundle is the first compiler-owned read model shared across Odylith
subsystems. It keeps the public CLI and packet contracts stable while allowing
Lance/Tantivy materialization to consume one deterministic compiled substrate.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Mapping

from odylith.runtime.context_engine import odylith_context_cache

BUNDLE_VERSION = "v1"
BUNDLE_DIRNAME = "odylith-compiler"
MANIFEST_FILENAME = "projection-manifest.v1.json"
DOCUMENTS_FILENAME = "documents.v1.jsonl"
EDGES_FILENAME = "edges.v1.jsonl"


def runtime_root(*, repo_root: Path) -> Path:
    """Return the mutable runtime root that stores compiled projection bundles."""
    return (Path(repo_root).resolve() / ".odylith" / "runtime").resolve()


def compiler_root(*, repo_root: Path) -> Path:
    """Return the compiler-owned bundle directory under the runtime root."""
    return (runtime_root(repo_root=repo_root) / BUNDLE_DIRNAME).resolve()


def manifest_path(*, repo_root: Path) -> Path:
    """Return the compiled bundle manifest path."""
    return (compiler_root(repo_root=repo_root) / MANIFEST_FILENAME).resolve()


def documents_path(*, repo_root: Path) -> Path:
    """Return the compiled bundle documents JSONL path."""
    return (compiler_root(repo_root=repo_root) / DOCUMENTS_FILENAME).resolve()


def edges_path(*, repo_root: Path) -> Path:
    """Return the compiled bundle edges JSONL path."""
    return (compiler_root(repo_root=repo_root) / EDGES_FILENAME).resolve()


def _utc_now() -> str:
    """Return a zero-microsecond UTC timestamp string for bundle manifests."""
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    """Load JSONL rows from disk while skipping malformed records."""
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for raw in lines:
        line = str(raw or "").strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, Mapping):
            rows.append(dict(payload))
    return rows


def _render_jsonl_rows(rows: list[dict[str, Any]]) -> str:
    """Render bundle rows as deterministic JSONL content."""
    return "".join(json.dumps(dict(row), sort_keys=True, ensure_ascii=False) + "\n" for row in rows)


def write_bundle(
    *,
    repo_root: Path,
    documents: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    projection_fingerprint: str,
    projection_scope: str,
    input_fingerprint: str,
    provenance: Mapping[str, Any] | None = None,
    source: str = "projection_compile",
) -> dict[str, Any]:
    """Write the compiled projection bundle documents, edges, and manifest."""
    root = Path(repo_root).resolve()
    bundle_root = compiler_root(repo_root=root)
    bundle_root.mkdir(parents=True, exist_ok=True)
    docs_target = documents_path(repo_root=root)
    edges_target = edges_path(repo_root=root)
    manifest_target = manifest_path(repo_root=root)
    lock_key = str(bundle_root)
    documents_rendered = _render_jsonl_rows(documents)
    edges_rendered = _render_jsonl_rows(edges)
    manifest = {
        "version": BUNDLE_VERSION,
        "compiled_utc": _utc_now(),
        "ready": True,
        "source": str(source).strip() or "projection_compile",
        "projection_fingerprint": str(projection_fingerprint).strip(),
        "projection_scope": str(projection_scope).strip().lower() or "default",
        "input_fingerprint": str(input_fingerprint).strip(),
        "document_count": len(documents),
        "edge_count": len(edges),
        "provenance": dict(provenance) if isinstance(provenance, Mapping) else {},
        "documents_path": str(docs_target.relative_to(root)),
        "edges_path": str(edges_target.relative_to(root)),
    }
    odylith_context_cache.write_text_if_changed(
        repo_root=root,
        path=docs_target,
        content=documents_rendered,
        lock_key=lock_key,
    )
    odylith_context_cache.write_text_if_changed(
        repo_root=root,
        path=edges_target,
        content=edges_rendered,
        lock_key=lock_key,
    )
    odylith_context_cache.write_json_if_changed(
        repo_root=root,
        path=manifest_target,
        payload=manifest,
        lock_key=lock_key,
    )
    return manifest


def load_bundle_manifest(*, repo_root: Path) -> dict[str, Any]:
    """Load the current projection bundle manifest."""
    return odylith_context_cache.read_json_object(manifest_path(repo_root=repo_root))


def load_documents(*, repo_root: Path) -> list[dict[str, Any]]:
    """Load compiled projection documents from the bundle JSONL."""
    return _read_jsonl_rows(documents_path(repo_root=repo_root))


def load_edges(*, repo_root: Path) -> list[dict[str, Any]]:
    """Load compiled projection edges from the bundle JSONL."""
    return _read_jsonl_rows(edges_path(repo_root=repo_root))


def load_bundle(*, repo_root: Path) -> dict[str, Any]:
    """Load the bundle manifest plus documents and edges together."""
    manifest = load_bundle_manifest(repo_root=repo_root)
    return {
        "manifest": manifest,
        "documents": load_documents(repo_root=repo_root),
        "edges": load_edges(repo_root=repo_root),
    }


__all__ = [
    "BUNDLE_DIRNAME",
    "BUNDLE_VERSION",
    "DOCUMENTS_FILENAME",
    "EDGES_FILENAME",
    "MANIFEST_FILENAME",
    "compiler_root",
    "documents_path",
    "edges_path",
    "load_bundle",
    "load_bundle_manifest",
    "load_documents",
    "load_edges",
    "manifest_path",
    "runtime_root",
    "write_bundle",
]
