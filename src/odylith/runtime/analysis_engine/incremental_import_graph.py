"""Incremental persistent import-graph cache for `odylith show`.

The `show` lane needs repeated repo analysis, but reparsing every source file on
every run is avoidable. This module keeps a disk-backed cache of per-file parse
results under `.odylith/runtime/latency-cache/` and only reparses files whose
metadata signature changed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.analysis_engine import import_graph
from odylith.runtime.analysis_engine.types import ImportArtifact
from odylith.runtime.analysis_engine.types import ImportEdge
from odylith.runtime.analysis_engine.types import ScanContext
from odylith.runtime.analysis_engine.types import progress
from odylith.runtime.context_engine import odylith_context_cache


_CACHE_VERSION = "v1"
_PARSER_VERSION = "v1"
_CACHE_DIR = Path(".odylith/runtime/latency-cache/show-import-graph")
_CACHE_PATH = _CACHE_DIR / "manifest.v1.json"


def has_incremental_cache(*, repo_root: Path) -> bool:
    return _cache_path(repo_root=repo_root).is_file()


def build_import_graph(
    repo_root: Path,
    languages: list[str],
) -> tuple[list[ImportArtifact], list[ImportEdge], ScanContext]:
    progress("Building import graph...")
    root = Path(repo_root).resolve()
    manifest = _load_manifest(repo_root=root)
    cached_entries = (
        dict(manifest.get("entries", {}))
        if isinstance(manifest.get("entries"), Mapping)
        else {}
    )
    next_entries: dict[str, dict[str, Any]] = {}
    changed = False
    file_rows: list[dict[str, Any]] = []
    py_roots = import_graph._auto_detect_python_roots(root) if "Python" in languages else []  # noqa: SLF001
    go_module_prefix = import_graph._detect_go_module_prefix(root) if "Go" in languages else ""  # noqa: SLF001
    language_signature = tuple(sorted(str(language).strip() for language in languages if str(language).strip()))

    for entry in import_graph._iter_source_files(root):  # noqa: SLF001
        rel_path = entry.relative_to(root).as_posix()
        signature = odylith_context_cache.path_signature(entry)
        cached = cached_entries.get(rel_path)
        if _cache_entry_reusable(
            cached,
            signature=signature,
            language_signature=language_signature,
        ):
            row = dict(cached.get("row", {}))
        else:
            row = _parse_source_file(
                repo_root=root,
                entry=entry,
                py_roots=py_roots,
                go_module_prefix=go_module_prefix,
            )
            changed = True
        next_entries[rel_path] = {
            "signature": signature,
            "language_signature": list(language_signature),
            "parser_version": _PARSER_VERSION,
            "row": row,
        }
        file_rows.append(row)

    if len(next_entries) != len(cached_entries):
        changed = True

    artifacts, edges, scan_ctx = _materialize_rows(file_rows)
    if changed or str(manifest.get("version", "")).strip() != _CACHE_VERSION:
        _write_manifest(
            repo_root=root,
            payload={
                "version": _CACHE_VERSION,
                "entry_count": len(next_entries),
                "entries": next_entries,
            },
        )
    return artifacts, edges, scan_ctx


def _cache_path(*, repo_root: Path) -> Path:
    return (Path(repo_root).resolve() / _CACHE_PATH).resolve()


def _load_manifest(*, repo_root: Path) -> dict[str, Any]:
    path = _cache_path(repo_root=repo_root)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def _write_manifest(*, repo_root: Path, payload: Mapping[str, Any]) -> None:
    path = _cache_path(repo_root=repo_root)
    odylith_context_cache.write_json_if_changed(
        repo_root=repo_root,
        path=path,
        payload=dict(payload),
    )


def _cache_entry_reusable(
    cached: Mapping[str, Any] | None,
    *,
    signature: Mapping[str, Any],
    language_signature: Sequence[str],
) -> bool:
    if not isinstance(cached, Mapping):
        return False
    if str(cached.get("parser_version", "")).strip() != _PARSER_VERSION:
        return False
    if list(cached.get("language_signature", [])) != list(language_signature):
        return False
    return dict(cached.get("signature", {})) == dict(signature)


def _parse_source_file(
    *,
    repo_root: Path,
    entry: Path,
    py_roots: list[tuple[str, str]],
    go_module_prefix: str,
) -> dict[str, Any]:
    rel_path = entry.relative_to(repo_root).as_posix()
    is_test = any(pattern in entry.name.lower() for pattern in import_graph._TEST_PATTERNS)  # noqa: SLF001
    try:
        source = entry.read_text(encoding="utf-8", errors="replace")
    except OSError:
        source = ""
    todos: list[tuple[str, str]] = []
    if source and not any(token in rel_path.lower() for token in import_graph._SKIP_PATH_TOKENS):  # noqa: SLF001
        for line in source.splitlines():
            match = import_graph._TODO_RE.search(line)  # noqa: SLF001
            if match is None:
                continue
            text = str(match.group(2) or "").strip()
            if len(text) > 10:
                todos.append((rel_path, text))

    artifact: ImportArtifact | None = None
    file_edges: list[ImportEdge] = []
    if entry.suffix == ".py":
        artifact, _ = import_graph._parse_python_file(rel_path, source, {}, py_roots)  # noqa: SLF001
    elif entry.suffix in (".ts", ".tsx", ".js", ".jsx"):
        artifact, file_edges = import_graph._parse_typescript_file(rel_path, source, repo_root)  # noqa: SLF001
    elif entry.suffix == ".go":
        artifact, file_edges = import_graph._parse_go_file(rel_path, source, go_module_prefix, repo_root)  # noqa: SLF001
    elif entry.suffix == ".rs":
        artifact, file_edges = import_graph._parse_rust_file(rel_path, source, repo_root)  # noqa: SLF001

    return {
        "path": rel_path,
        "language": import_graph._lang_for_ext(entry.suffix),  # noqa: SLF001
        "is_test": bool(is_test),
        "todos": [[path, text] for path, text in todos[:10]],
        "artifact": _artifact_payload(artifact),
        "edges": [_edge_payload(edge) for edge in file_edges],
    }


def _artifact_payload(artifact: ImportArtifact | None) -> dict[str, Any]:
    if artifact is None:
        return {}
    return {
        "path": artifact.path,
        "module_name": artifact.module_name,
        "language": artifact.language,
        "imports": list(artifact.imports),
    }


def _edge_payload(edge: ImportEdge) -> dict[str, str]:
    return {
        "source_path": edge.source_path,
        "target_path": edge.target_path,
    }


def _materialize_rows(rows: Sequence[Mapping[str, Any]]) -> tuple[list[ImportArtifact], list[ImportEdge], ScanContext]:
    scan_ctx = ScanContext()
    artifacts: list[ImportArtifact] = []
    edges: list[ImportEdge] = []
    python_module_index: dict[str, str] = {}
    python_artifacts: list[ImportArtifact] = []

    for row in rows:
        path = str(row.get("path", "")).strip()
        if not path:
            continue
        scan_ctx.file_count += 1
        language = str(row.get("language", "")).strip() or "unknown"
        scan_ctx.language_counts[language] = scan_ctx.language_counts.get(language, 0) + 1
        if bool(row.get("is_test")):
            scan_ctx.test_files.add(path)
        for todo in row.get("todos", []):
            if isinstance(todo, list) and len(todo) == 2:
                scan_ctx.todos.append((str(todo[0]).strip(), str(todo[1]).strip()))
        artifact_payload = dict(row.get("artifact", {})) if isinstance(row.get("artifact"), Mapping) else {}
        if artifact_payload:
            artifact = ImportArtifact(
                path=str(artifact_payload.get("path", "")).strip(),
                module_name=str(artifact_payload.get("module_name", "")).strip(),
                language=str(artifact_payload.get("language", "")).strip(),
                imports=tuple(
                    str(token).strip()
                    for token in artifact_payload.get("imports", [])
                    if str(token).strip()
                ),
            )
            artifacts.append(artifact)
            if artifact.language == "python":
                python_artifacts.append(artifact)
                python_module_index[artifact.module_name] = artifact.path
        for edge_payload in row.get("edges", []):
            if not isinstance(edge_payload, Mapping):
                continue
            source_path = str(edge_payload.get("source_path", "")).strip()
            target_path = str(edge_payload.get("target_path", "")).strip()
            if source_path and target_path:
                edges.append(ImportEdge(source_path=source_path, target_path=target_path))

    if python_module_index:
        edges.extend(import_graph._resolve_python_imports(python_artifacts, python_module_index))  # noqa: SLF001
    scan_ctx.todos = scan_ctx.todos[:10]
    return artifacts, edges, scan_ctx


__all__ = ["build_import_graph", "has_incremental_cache"]
