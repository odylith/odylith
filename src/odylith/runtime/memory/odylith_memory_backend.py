"""Odylith local memory backend built on LanceDB + Tantivy.

This module keeps git-tracked repo truth authoritative while compiling a fast
derived evidence store for the Odylith Context Engine. Compiler-owned
projection tables feed this backend directly; search and miss-recovery move to
the Odylith backend when the optional tooling-memory dependencies are
available.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Iterable, Mapping, Sequence

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.memory import odylith_projection_bundle

try:
    import lancedb
except Exception:  # pragma: no cover - exercised through availability checks
    lancedb = None

try:
    import pyarrow as pa
except Exception:  # pragma: no cover - exercised through availability checks
    pa = None

try:
    import tantivy
except Exception:  # pragma: no cover - exercised through availability checks
    tantivy = None

BACKEND_VERSION = "v1"
DOCUMENTS_TABLE = "documents"
EDGES_TABLE = "edges"
MANIFEST_FILENAME = "odylith-memory-backend.v1.json"
EMBED_DIMENSIONS = 96
SPARSE_DEFAULT_FIELDS = ("entity_id", "title", "path", "content")
VECTOR_CANDIDATE_MULTIPLIER = 3
_QUERY_TOKEN_RE = re.compile(r"[A-Za-z0-9_./:-]+")
_RRF_K = 60.0
_FIELD_TEXT_WEIGHTS: tuple[tuple[str, float], ...] = (
    ("entity_id", 1.2),
    ("title", 1.0),
    ("path", 0.9),
    ("content", 0.35),
)


@contextlib.contextmanager
def _suppress_expected_lance_bootstrap_warnings() -> Iterable[None]:
    saved_stderr_fd: int | None = None
    devnull_handle = None
    try:
        saved_stderr_fd = os.dup(2)
        devnull_handle = open(os.devnull, "w", encoding="utf-8")
        os.dup2(devnull_handle.fileno(), 2)
        yield
    finally:
        if saved_stderr_fd is not None:
            with contextlib.suppress(OSError):
                os.dup2(saved_stderr_fd, 2)
            with contextlib.suppress(OSError):
                os.close(saved_stderr_fd)
        if devnull_handle is not None:
            with contextlib.suppress(OSError):
                devnull_handle.close()


def local_backend_root(*, repo_root: Path) -> Path:
    return (Path(repo_root).resolve() / ".odylith" / "runtime" / "odylith-memory").resolve()


def local_lance_root(*, repo_root: Path) -> Path:
    return (local_backend_root(repo_root=repo_root) / "lance").resolve()


def local_tantivy_root(*, repo_root: Path) -> Path:
    return (local_backend_root(repo_root=repo_root) / "tantivy").resolve()


def local_manifest_path(*, repo_root: Path) -> Path:
    return (local_backend_root(repo_root=repo_root) / MANIFEST_FILENAME).resolve()


def _local_backend_artifacts_present(*, repo_root: Path) -> bool:
    return local_lance_root(repo_root=repo_root).is_dir() and local_tantivy_root(repo_root=repo_root).is_dir()


def backend_dependencies_available() -> bool:
    return lancedb is not None and pa is not None and tantivy is not None


def dependency_snapshot() -> dict[str, Any]:
    return {
        "lancedb": {
            "available": lancedb is not None,
            "version": str(getattr(lancedb, "__version__", "")).strip(),
        },
        "pyarrow": {
            "available": pa is not None,
            "version": str(getattr(pa, "__version__", "")).strip(),
        },
        "tantivy": {
            "available": tantivy is not None,
            "version": str(getattr(tantivy, "__version__", "")).strip(),
        },
    }


def _manifest_matches_compiler(
    *,
    manifest: Mapping[str, Any],
    compiler_manifest: Mapping[str, Any],
) -> bool:
    if not manifest:
        return False
    if not compiler_manifest or not bool(compiler_manifest.get("ready")):
        return bool(str(manifest.get("projection_fingerprint", "")).strip())
    for field_name in ("projection_fingerprint", "projection_scope"):
        manifest_value = str(manifest.get(field_name, "")).strip()
        compiler_value = str(compiler_manifest.get(field_name, "")).strip()
        if not manifest_value or not compiler_value or manifest_value != compiler_value:
            return False
    manifest_input = str(manifest.get("input_fingerprint", "")).strip()
    compiler_input = str(compiler_manifest.get("input_fingerprint", "")).strip()
    if manifest_input and compiler_input and manifest_input != compiler_input:
        return False
    return True


def _ready_manifest_payload(
    *,
    repo_root: Path,
    manifest: Mapping[str, Any],
    compiler_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    payload = dict(manifest)
    compiler_source = str(payload.get("compiler_source", "")).strip()
    if not compiler_source and compiler_manifest:
        compiler_source = "projection_bundle"
    projection_fingerprint = str(payload.get("projection_fingerprint", "")).strip() or str(
        compiler_manifest.get("projection_fingerprint", "")
    ).strip()
    projection_scope = str(payload.get("projection_scope", "")).strip() or str(
        compiler_manifest.get("projection_scope", "")
    ).strip()
    input_fingerprint = str(payload.get("input_fingerprint", "")).strip() or str(
        compiler_manifest.get("input_fingerprint", "")
    ).strip()
    payload.update(
        {
            "version": BACKEND_VERSION,
            "projection_fingerprint": projection_fingerprint,
            "projection_scope": projection_scope,
            "input_fingerprint": input_fingerprint,
            "document_count": int(
                compiler_manifest.get("document_count", payload.get("document_count", 0)) or 0
            ),
            "edge_count": int(compiler_manifest.get("edge_count", payload.get("edge_count", 0)) or 0),
            "dependencies": dependency_snapshot(),
            "ready": True,
            "status": "ready",
            "storage": "lance_local_columnar",
            "sparse_recall": "tantivy_sparse_recall",
            "documents_table": DOCUMENTS_TABLE,
            "edges_table": EDGES_TABLE,
            "compiler_source": compiler_source,
        }
    )
    if compiler_manifest:
        payload["compiler_manifest"] = dict(compiler_manifest)
    return payload


def _restore_ready_manifest_if_possible(
    *,
    repo_root: Path,
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    payload = dict(manifest)
    if not payload or not backend_dependencies_available() or not _local_backend_artifacts_present(repo_root=root):
        return payload
    compiler_manifest = odylith_projection_bundle.load_bundle_manifest(repo_root=root)
    if not _manifest_matches_compiler(manifest=payload, compiler_manifest=compiler_manifest):
        return payload
    ready, _health_error = _backend_operational_check(repo_root=root)
    if not ready:
        return payload
    restored = _ready_manifest_payload(
        repo_root=root,
        manifest=payload,
        compiler_manifest=compiler_manifest,
    )
    odylith_context_cache.write_json_if_changed(
        repo_root=root,
        path=local_manifest_path(repo_root=root),
        payload=restored,
        lock_key=str(local_manifest_path(repo_root=root)),
    )
    return restored


def _hash_text(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _tokenize_text(value: str) -> list[str]:
    return [match.group(0).lower() for match in _QUERY_TOKEN_RE.finditer(str(value or ""))]


def _quote_sql_literal(value: str) -> str:
    return "'" + str(value or "").replace("'", "''") + "'"


def _normalize_kind_filters(kinds: Sequence[str] | None) -> set[str]:
    return {str(kind).strip().lower() for kind in (kinds or []) if str(kind).strip()}


def _coerce_first_string(value: Any) -> str:
    if isinstance(value, list):
        for item in value:
            token = str(item or "").strip()
            if token:
                return token
        return ""
    return str(value or "").strip()


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def derived_embedding(text: str, *, dims: int = EMBED_DIMENSIONS) -> list[float]:
    return _text_embedding(text, dims=dims)


def _row_text(row: Mapping[str, Any], field_name: str) -> str:
    return str(row.get(field_name, "")).strip().casefold()


def _query_variants(query: str) -> tuple[str, str, set[str]]:
    raw = str(query or "").strip()
    normalized = raw.casefold()
    tokens = {token for token in _tokenize_text(raw) if token}
    return raw, normalized, tokens


def _field_match_score(field_text: str, *, normalized_query: str, query_tokens: set[str], weight: float) -> float:
    text = str(field_text or "").strip().casefold()
    if not text:
        return 0.0
    score = 0.0
    if normalized_query and text == normalized_query:
        score += 1.4 * weight
    elif normalized_query and (text.startswith(normalized_query) or normalized_query in text):
        score += 0.6 * weight
    if query_tokens:
        overlaps = sum(1 for token in query_tokens if token in text)
        if overlaps:
            score += min(1.0, overlaps / float(max(1, len(query_tokens)))) * weight
    return score


def _lexical_match_features(row: Mapping[str, Any], *, query: str) -> dict[str, float]:
    _, normalized_query, query_tokens = _query_variants(query)
    field_scores = {
        field_name: _field_match_score(
            _row_text(row, field_name),
            normalized_query=normalized_query,
            query_tokens=query_tokens,
            weight=weight,
        )
        for field_name, weight in _FIELD_TEXT_WEIGHTS
    }
    exact_anchor = max(field_scores.get("entity_id", 0.0), field_scores.get("path", 0.0), field_scores.get("title", 0.0))
    total = round(sum(field_scores.values()), 6)
    return {
        "lexical_score": total,
        "exact_anchor": round(exact_anchor, 6),
        "coverage": round(
            min(1.0, total / max(1.0, sum(weight for _, weight in _FIELD_TEXT_WEIGHTS))),
            6,
        ),
    }


def _rank_rows_with_query_match(
    *,
    rows: Sequence[Mapping[str, Any]],
    query: str,
    limit: int,
    exact: bool,
) -> list[dict[str, Any]]:
    ranked_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        lexical = _lexical_match_features(row, query=query)
        base_score = 0.0 if exact else _safe_float(row.get("score"))
        final_score = (
            lexical["exact_anchor"] * 1.5
            + lexical["coverage"] * 0.9
            + lexical["lexical_score"] * 0.35
            + base_score
        )
        payload = dict(row)
        payload["score"] = round(final_score, 6)
        payload["match_features"] = lexical
        ranked_rows.append(payload)
    ranked_rows.sort(
        key=lambda row: (
            -_safe_float(row.get("score")),
            -_safe_float(dict(row.get("match_features", {})).get("exact_anchor")),
            str(row.get("path", "")),
            str(row.get("entity_id", "")),
        )
    )
    return _normalize_search_rows(rows=ranked_rows, limit=limit, exact=exact)


def _text_embedding(text: str, *, dims: int = EMBED_DIMENSIONS) -> list[float]:
    vector = [0.0] * max(8, int(dims))
    tokens = _tokenize_text(text)
    if not tokens:
        return vector
    for token in tokens[:512]:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
        idx_primary = int.from_bytes(digest[:4], "little") % len(vector)
        idx_secondary = int.from_bytes(digest[4:8], "little") % len(vector)
        sign = -1.0 if digest[8] & 1 else 1.0
        weight = 1.0 + min(len(token), 24) / 24.0
        vector[idx_primary] += sign * weight
        vector[idx_secondary] += sign * weight * 0.5
    norm = math.sqrt(sum(component * component for component in vector))
    if norm <= 0.0:
        return vector
    return [component / norm for component in vector]


def _document_record(row: Mapping[str, Any]) -> dict[str, Any]:
    kind = str(row.get("kind", "")).strip().lower()
    entity_id = str(row.get("entity_id", "")).strip()
    title = str(row.get("title", "")).strip()
    path = str(row.get("path", "")).strip()
    content = str(row.get("content", "")).strip()
    doc_key = f"{kind}:{entity_id}" if kind and entity_id else _hash_text(f"{kind}:{path}:{title}")
    source_text = "\n".join(token for token in (entity_id, title, path, content) if token).strip()
    return {
        "doc_key": doc_key,
        "kind": kind,
        "entity_id": entity_id,
        "title": title,
        "path": path,
        "content": content,
        "entity_id_lower": entity_id.lower(),
        "title_lower": title.lower(),
        "path_lower": path.lower(),
        "content_hash": _hash_text(content),
        "provenance_json": json.dumps(
            {
                "entity_kind": kind,
                "entity_id": entity_id,
                "source_path": path,
                "derived": True,
                "read_only_repo_truth": True,
            },
            sort_keys=True,
            ensure_ascii=False,
        ),
        "embedding": _text_embedding(source_text),
    }


def _edge_record(row: Mapping[str, Any]) -> dict[str, Any]:
    source_kind = str(row.get("source_kind", "")).strip().lower()
    source_id = str(row.get("source_id", "")).strip()
    relation = str(row.get("relation", "")).strip().lower()
    target_kind = str(row.get("target_kind", "")).strip().lower()
    target_id = str(row.get("target_id", "")).strip()
    source_path = str(row.get("source_path", "")).strip()
    return {
        "edge_key": str(row.get("edge_key", "")).strip()
        or _hash_text(f"{source_kind}:{source_id}:{relation}:{target_kind}:{target_id}:{source_path}"),
        "source_kind": source_kind,
        "source_id": source_id,
        "relation": relation,
        "target_kind": target_kind,
        "target_id": target_id,
        "source_path": source_path,
        "provenance_json": json.dumps(
            {
                "source_kind": source_kind,
                "source_id": source_id,
                "target_kind": target_kind,
                "target_id": target_id,
                "source_path": source_path,
                "derived": True,
            },
            sort_keys=True,
            ensure_ascii=False,
        ),
    }


def _table_exists(connection: Any, table_name: str) -> bool:
    table_token = str(table_name).strip()
    if hasattr(connection, "has_table"):
        return bool(connection.has_table(table_token))
    if hasattr(connection, "table_rows"):
        return bool(getattr(connection, "table_rows")(table_token))
    row = connection.execute(f"SELECT COUNT(*) AS row_count FROM {table_token}").fetchone()
    return bool(row) and int(row.get("row_count", 0) or 0) >= 0


def _json_load(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    text = str(value).strip()
    if not text:
        return default
    with contextlib.suppress(Exception):
        return json.loads(text)
    return default


def _json_list(value: Any) -> list[Any]:
    loaded = _json_load(value, [])
    return list(loaded) if isinstance(loaded, list) else []


def _json_dict(value: Any) -> dict[str, Any]:
    loaded = _json_load(value, {})
    return dict(loaded) if isinstance(loaded, Mapping) else {}


def _projection_documents_from_tables(*, connection: Any) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []

    if _table_exists(connection, "workstreams"):
        for row in connection.execute(
            "SELECT idea_id, title, source_path, search_body FROM workstreams ORDER BY idea_id"
        ).fetchall():
            idea_id = str(row["idea_id"]).strip()
            documents.append(
                _document_record(
                    {
                        "kind": "workstream",
                        "entity_id": idea_id,
                        "title": str(row["title"]).strip(),
                        "content": "\n".join(
                            token
                            for token in (idea_id, str(row["search_body"]).strip())
                            if token
                        ),
                        "path": str(row["source_path"]).strip(),
                    }
                )
            )

    if _table_exists(connection, "releases"):
        for row in connection.execute(
            """
            SELECT release_id, display_label, version, tag, effective_name, aliases_json, active_workstreams_json, source_path, metadata_json
            FROM releases
            ORDER BY release_id
            """
        ).fetchall():
            metadata = _json_dict(row["metadata_json"])
            aliases = [str(item).strip() for item in _json_list(row["aliases_json"]) if str(item).strip()]
            active_workstreams = [str(item).strip() for item in _json_list(row["active_workstreams_json"]) if str(item).strip()]
            documents.append(
                _document_record(
                    {
                        "kind": "release",
                        "entity_id": str(row["release_id"]).strip(),
                        "title": str(row["display_label"]).strip() or str(row["release_id"]).strip(),
                        "content": "\n".join(
                            token
                            for token in (
                                str(row["release_id"]).strip(),
                                str(row["version"]).strip(),
                                str(row["tag"]).strip(),
                                str(row["effective_name"]).strip(),
                                " ".join(aliases),
                                " ".join(active_workstreams),
                                str(metadata.get("notes", "")).strip(),
                            )
                            if token
                        ),
                        "path": str(row["source_path"]).strip(),
                    }
                )
            )

    if _table_exists(connection, "plans"):
        for row in connection.execute(
            "SELECT plan_path, source_path, search_body FROM plans ORDER BY plan_path"
        ).fetchall():
            plan_path = str(row["plan_path"]).strip()
            documents.append(
                _document_record(
                    {
                        "kind": "plan",
                        "entity_id": plan_path,
                        "title": Path(plan_path).name,
                        "content": str(row["search_body"]).strip(),
                        "path": str(row["source_path"]).strip(),
                    }
                )
            )

    if _table_exists(connection, "bugs"):
        for row in connection.execute(
            "SELECT bug_id, bug_key, title, link_target, source_path, search_body FROM bugs ORDER BY bug_key"
        ).fetchall():
            bug_id = str(row["bug_id"] or "").strip()
            documents.append(
                _document_record(
                    {
                        "kind": "bug",
                        "entity_id": bug_id or str(row["bug_key"]).strip(),
                        "title": " ".join(token for token in (bug_id, str(row["title"]).strip()) if token).strip(),
                        "content": "\n".join(
                            token for token in (bug_id, str(row["search_body"]).strip()) if token
                        ),
                        "path": str(row["link_target"]).strip() or str(row["source_path"]).strip(),
                    }
                )
            )

    if _table_exists(connection, "diagrams"):
        for row in connection.execute(
            "SELECT diagram_id, title, source_mmd, summary, metadata_json FROM diagrams ORDER BY diagram_id"
        ).fetchall():
            metadata = _json_dict(row["metadata_json"])
            content = "\n".join(
                token
                for token in (
                    str(row["summary"]).strip(),
                    " ".join(str(item).strip() for item in _json_list(metadata.get("related_backlog")) if str(item).strip()),
                    " ".join(str(item).strip() for item in _json_list(metadata.get("related_code")) if str(item).strip()),
                )
                if token
            )
            documents.append(
                _document_record(
                    {
                        "kind": "diagram",
                        "entity_id": str(row["diagram_id"]).strip(),
                        "title": f"{str(row['diagram_id']).strip()} {str(row['title']).strip()}".strip(),
                        "content": content,
                        "path": str(row["source_mmd"]).strip(),
                    }
                )
            )

    if _table_exists(connection, "components"):
        for row in connection.execute(
            """
            SELECT component_id, name, spec_ref, aliases_json, workstreams_json, diagrams_json, metadata_json
            FROM components
            ORDER BY component_id
            """
        ).fetchall():
            metadata = _json_dict(row["metadata_json"])
            aliases = [str(item).strip() for item in _json_list(row["aliases_json"]) if str(item).strip()]
            workstreams = [str(item).strip() for item in _json_list(row["workstreams_json"]) if str(item).strip()]
            diagrams = [str(item).strip() for item in _json_list(row["diagrams_json"]) if str(item).strip()]
            content = "\n".join(
                token
                for token in (
                    str(metadata.get("what_it_is", "")).strip(),
                    str(metadata.get("why_tracked", "")).strip(),
                    " ".join(aliases),
                    " ".join(workstreams),
                    " ".join(diagrams),
                )
                if token
            )
            documents.append(
                _document_record(
                    {
                        "kind": "component",
                        "entity_id": str(row["component_id"]).strip(),
                        "title": f"{str(row['component_id']).strip()} {str(row['name']).strip()}".strip(),
                        "content": content,
                        "path": str(row["spec_ref"]).strip(),
                    }
                )
            )

    if _table_exists(connection, "codex_events"):
        for row in connection.execute(
            "SELECT event_id, summary, workstreams_json, artifacts_json FROM codex_events ORDER BY event_id"
        ).fetchall():
            workstreams = [str(item).strip() for item in _json_list(row["workstreams_json"]) if str(item).strip()]
            artifacts = [str(item).strip() for item in _json_list(row["artifacts_json"]) if str(item).strip()]
            documents.append(
                _document_record(
                    {
                        "kind": "codex_event",
                        "entity_id": str(row["event_id"]).strip(),
                        "title": str(row["summary"]).strip(),
                        "content": "\n".join(
                            token
                            for token in (
                                str(row["summary"]).strip(),
                                " ".join(workstreams),
                                " ".join(artifacts),
                            )
                            if token
                        ),
                        "path": agent_runtime_contract.AGENT_STREAM_PATH,
                    }
                )
            )

    if _table_exists(connection, "engineering_notes"):
        for row in connection.execute(
            """
            SELECT note_id, note_kind, title, source_path, summary, components_json, workstreams_json, path_refs_json
            FROM engineering_notes
            ORDER BY note_kind, note_id
            """
        ).fetchall():
            components = [str(item).strip() for item in _json_list(row["components_json"]) if str(item).strip()]
            workstreams = [str(item).strip() for item in _json_list(row["workstreams_json"]) if str(item).strip()]
            path_refs = [str(item).strip() for item in _json_list(row["path_refs_json"]) if str(item).strip()]
            documents.append(
                _document_record(
                    {
                        "kind": str(row["note_kind"]).strip(),
                        "entity_id": str(row["note_id"]).strip(),
                        "title": str(row["title"]).strip(),
                        "content": "\n".join(
                            token
                            for token in (
                                str(row["summary"]).strip(),
                                " ".join(components),
                                " ".join(workstreams),
                                " ".join(path_refs),
                            )
                            if token
                        ),
                        "path": str(row["source_path"]).strip(),
                    }
                )
            )

    if _table_exists(connection, "code_artifacts"):
        for row in connection.execute(
            "SELECT path, module_name, imports_json, contract_refs_json FROM code_artifacts ORDER BY path"
        ).fetchall():
            imports = [str(item).strip() for item in _json_list(row["imports_json"]) if str(item).strip()]
            contract_refs = [str(item).strip() for item in _json_list(row["contract_refs_json"]) if str(item).strip()]
            path = str(row["path"]).strip()
            documents.append(
                _document_record(
                    {
                        "kind": "code",
                        "entity_id": path,
                        "title": str(row["module_name"]).strip() or Path(path).name,
                        "content": "\n".join([*imports, *contract_refs]),
                        "path": path,
                    }
                )
            )

    if _table_exists(connection, "test_cases"):
        for row in connection.execute(
            "SELECT test_id, test_path, test_name, markers_json, target_paths_json, metadata_json FROM test_cases ORDER BY test_id"
        ).fetchall():
            metadata = _json_dict(row["metadata_json"])
            history = _json_dict(metadata.get("history"))
            history_sources = [str(item).strip() for item in _json_list(history.get("sources")) if str(item).strip()]
            markers = [str(item).strip() for item in _json_list(row["markers_json"]) if str(item).strip()]
            target_paths = [str(item).strip() for item in _json_list(row["target_paths_json"]) if str(item).strip()]
            documents.append(
                _document_record(
                    {
                        "kind": "test",
                        "entity_id": str(row["test_id"]).strip(),
                        "title": str(row["test_name"]).strip(),
                        "content": "\n".join([*markers, *target_paths, *history_sources]),
                        "path": str(row["test_path"]).strip(),
                    }
                )
            )

    return documents


def _projection_documents_from_projection_tables(
    *,
    tables: Mapping[str, Any],
) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []

    for row in tables.get("workstreams", []) if isinstance(tables.get("workstreams"), list) else []:
        if not isinstance(row, Mapping):
            continue
        idea_id = str(row.get("idea_id", "")).strip()
        documents.append(
            _document_record(
                {
                    "kind": "workstream",
                    "entity_id": idea_id,
                    "title": str(row.get("title", "")).strip(),
                    "content": "\n".join(
                        token
                        for token in (idea_id, str(row.get("search_body", "")).strip())
                        if token
                    ),
                    "path": str(row.get("source_path", "")).strip(),
                }
            )
        )

    for row in tables.get("releases", []) if isinstance(tables.get("releases"), list) else []:
        if not isinstance(row, Mapping):
            continue
        metadata = _json_dict(row.get("metadata_json"))
        aliases = [str(item).strip() for item in _json_list(row.get("aliases_json")) if str(item).strip()]
        active_workstreams = [
            str(item).strip()
            for item in _json_list(row.get("active_workstreams_json"))
            if str(item).strip()
        ]
        documents.append(
            _document_record(
                {
                    "kind": "release",
                    "entity_id": str(row.get("release_id", "")).strip(),
                    "title": str(row.get("display_label", "")).strip() or str(row.get("release_id", "")).strip(),
                    "content": "\n".join(
                        token
                        for token in (
                            str(row.get("release_id", "")).strip(),
                            str(row.get("version", "")).strip(),
                            str(row.get("tag", "")).strip(),
                            str(row.get("effective_name", "")).strip(),
                            " ".join(aliases),
                            " ".join(active_workstreams),
                            str(metadata.get("notes", "")).strip(),
                        )
                        if token
                    ),
                    "path": str(row.get("source_path", "")).strip(),
                }
            )
        )

    for row in tables.get("plans", []) if isinstance(tables.get("plans"), list) else []:
        if not isinstance(row, Mapping):
            continue
        plan_path = str(row.get("plan_path", "")).strip()
        documents.append(
            _document_record(
                {
                    "kind": "plan",
                    "entity_id": plan_path,
                    "title": Path(plan_path).name,
                    "content": str(row.get("search_body", "")).strip(),
                    "path": str(row.get("source_path", "")).strip(),
                }
            )
        )

    for row in tables.get("bugs", []) if isinstance(tables.get("bugs"), list) else []:
        if not isinstance(row, Mapping):
            continue
        bug_id = str(row.get("bug_id", "")).strip()
        documents.append(
            _document_record(
                {
                    "kind": "bug",
                    "entity_id": bug_id or str(row.get("bug_key", "")).strip(),
                    "title": " ".join(token for token in (bug_id, str(row.get("title", "")).strip()) if token).strip(),
                    "content": "\n".join(
                        token for token in (bug_id, str(row.get("search_body", "")).strip()) if token
                    ),
                    "path": str(row.get("link_target", "")).strip() or str(row.get("source_path", "")).strip(),
                }
            )
        )

    for row in tables.get("diagrams", []) if isinstance(tables.get("diagrams"), list) else []:
        if not isinstance(row, Mapping):
            continue
        metadata = _json_dict(row.get("metadata_json"))
        content = "\n".join(
            token
            for token in (
                str(row.get("summary", "")).strip(),
                " ".join(str(item).strip() for item in _json_list(metadata.get("related_backlog")) if str(item).strip()),
                " ".join(str(item).strip() for item in _json_list(metadata.get("related_code")) if str(item).strip()),
            )
            if token
        )
        documents.append(
            _document_record(
                {
                    "kind": "diagram",
                    "entity_id": str(row.get("diagram_id", "")).strip(),
                    "title": f"{str(row.get('diagram_id', '')).strip()} {str(row.get('title', '')).strip()}".strip(),
                    "content": content,
                    "path": str(row.get("source_mmd", "")).strip(),
                }
            )
        )

    for row in tables.get("components", []) if isinstance(tables.get("components"), list) else []:
        if not isinstance(row, Mapping):
            continue
        metadata = _json_dict(row.get("metadata_json"))
        aliases = [str(item).strip() for item in _json_list(row.get("aliases_json")) if str(item).strip()]
        workstreams = [str(item).strip() for item in _json_list(row.get("workstreams_json")) if str(item).strip()]
        diagrams = [str(item).strip() for item in _json_list(row.get("diagrams_json")) if str(item).strip()]
        content = "\n".join(
            token
            for token in (
                str(metadata.get("what_it_is", "")).strip(),
                str(metadata.get("why_tracked", "")).strip(),
                " ".join(aliases),
                " ".join(workstreams),
                " ".join(diagrams),
            )
            if token
        )
        documents.append(
            _document_record(
                {
                    "kind": "component",
                    "entity_id": str(row.get("component_id", "")).strip(),
                    "title": f"{str(row.get('component_id', '')).strip()} {str(row.get('name', '')).strip()}".strip(),
                    "content": content,
                    "path": str(row.get("spec_ref", "")).strip(),
                }
            )
        )

    for row in tables.get("codex_events", []) if isinstance(tables.get("codex_events"), list) else []:
        if not isinstance(row, Mapping):
            continue
        workstreams = [str(item).strip() for item in _json_list(row.get("workstreams_json")) if str(item).strip()]
        artifacts = [str(item).strip() for item in _json_list(row.get("artifacts_json")) if str(item).strip()]
        documents.append(
            _document_record(
                {
                    "kind": "codex_event",
                    "entity_id": str(row.get("event_id", "")).strip(),
                    "title": str(row.get("summary", "")).strip(),
                    "content": "\n".join(
                        token
                        for token in (
                            str(row.get("summary", "")).strip(),
                            " ".join(workstreams),
                            " ".join(artifacts),
                        )
                        if token
                    ),
                    "path": agent_runtime_contract.AGENT_STREAM_PATH,
                }
            )
        )

    for row in tables.get("engineering_notes", []) if isinstance(tables.get("engineering_notes"), list) else []:
        if not isinstance(row, Mapping):
            continue
        components = [str(item).strip() for item in _json_list(row.get("components_json")) if str(item).strip()]
        workstreams = [str(item).strip() for item in _json_list(row.get("workstreams_json")) if str(item).strip()]
        path_refs = [str(item).strip() for item in _json_list(row.get("path_refs_json")) if str(item).strip()]
        documents.append(
            _document_record(
                {
                    "kind": str(row.get("note_kind", "")).strip(),
                    "entity_id": str(row.get("note_id", "")).strip(),
                    "title": str(row.get("title", "")).strip(),
                    "content": "\n".join(
                        token
                        for token in (
                            str(row.get("summary", "")).strip(),
                            " ".join(components),
                            " ".join(workstreams),
                            " ".join(path_refs),
                        )
                        if token
                    ),
                    "path": str(row.get("source_path", "")).strip(),
                }
            )
        )

    for row in tables.get("code_artifacts", []) if isinstance(tables.get("code_artifacts"), list) else []:
        if not isinstance(row, Mapping):
            continue
        imports = [str(item).strip() for item in _json_list(row.get("imports_json")) if str(item).strip()]
        contract_refs = [str(item).strip() for item in _json_list(row.get("contract_refs_json")) if str(item).strip()]
        path = str(row.get("path", "")).strip()
        documents.append(
            _document_record(
                {
                    "kind": "code",
                    "entity_id": path,
                    "title": str(row.get("module_name", "")).strip() or Path(path).name,
                    "content": "\n".join([*imports, *contract_refs]),
                    "path": path,
                }
            )
        )

    for row in tables.get("test_cases", []) if isinstance(tables.get("test_cases"), list) else []:
        if not isinstance(row, Mapping):
            continue
        metadata = _json_dict(row.get("metadata_json"))
        history = _json_dict(metadata.get("history"))
        history_sources = [str(item).strip() for item in _json_list(history.get("sources")) if str(item).strip()]
        markers = [str(item).strip() for item in _json_list(row.get("markers_json")) if str(item).strip()]
        target_paths = [str(item).strip() for item in _json_list(row.get("target_paths_json")) if str(item).strip()]
        documents.append(
            _document_record(
                {
                    "kind": "test",
                    "entity_id": str(row.get("test_id", "")).strip(),
                    "title": str(row.get("test_name", "")).strip(),
                    "content": "\n".join([*markers, *target_paths, *history_sources]),
                    "path": str(row.get("test_path", "")).strip(),
                }
            )
        )

    return documents


def build_backend_materialization_inputs(
    *,
    connection: Any,
) -> dict[str, Any]:
    documents = _projection_documents_from_tables(connection=connection)
    traceability_edges = []
    if _table_exists(connection, "traceability_edges"):
        traceability_edges = [
            _edge_record(dict(row))
            for row in connection.execute(
                """
                SELECT edge_key, source_kind, source_id, relation, target_kind, target_id, source_path
                FROM traceability_edges
                ORDER BY source_kind, source_id, relation, target_kind, target_id
                """
            ).fetchall()
        ]
    code_edges = []
    if _table_exists(connection, "code_edges"):
        code_edges = [
            {
                "edge_key": str(row["edge_key"]).strip(),
                "source_kind": "code",
                "source_id": str(row["source_path"]).strip(),
                "relation": str(row["relation"]).strip().lower(),
                "target_kind": "code",
                "target_id": str(row["target_path"]).strip(),
                "source_path": str(row["source_path"]).strip(),
                "provenance_json": json.dumps(
                    {
                        "source_kind": "code",
                        "source_id": str(row["source_path"]).strip(),
                        "target_kind": "code",
                        "target_id": str(row["target_path"]).strip(),
                        "source_path": str(row["source_path"]).strip(),
                        "derived": True,
                    },
                    sort_keys=True,
                    ensure_ascii=False,
                ),
            }
            for row in connection.execute(
                """
                SELECT edge_key, source_path, relation, target_path
                FROM code_edges
                ORDER BY source_path, relation, target_path
                """
            ).fetchall()
        ]
    edge_rows = [*traceability_edges, *code_edges]
    return {
        "documents": documents,
        "edges": edge_rows,
        "document_count": len(documents),
        "edge_count": len(edge_rows),
        "input_fingerprint": odylith_context_cache.fingerprint_payload(
            {
                "documents": [
                    {
                        "doc_key": row["doc_key"],
                        "content_hash": row["content_hash"],
                        "path": row["path"],
                    }
                    for row in documents
                ],
                "edges": [
                    {
                        "edge_key": row["edge_key"],
                        "relation": row["relation"],
                    }
                    for row in edge_rows
                ],
            }
        ),
    }


def build_backend_materialization_inputs_from_projection_tables(
    *,
    tables: Mapping[str, Any],
) -> dict[str, Any]:
    documents = _projection_documents_from_projection_tables(tables=tables)
    traceability_edges = [
        _edge_record(dict(row))
        for row in tables.get("traceability_edges", [])
        if isinstance(tables.get("traceability_edges"), list) and isinstance(row, Mapping)
    ]
    code_edges = [
        {
            "edge_key": str(row.get("edge_key", "")).strip()
            or _hash_text(
                f"{str(row.get('source_path', '')).strip()}:"
                f"{str(row.get('relation', '')).strip()}:"
                f"{str(row.get('target_path', '')).strip()}"
            ),
            "source_kind": "code",
            "source_id": str(row.get("source_path", "")).strip(),
            "relation": str(row.get("relation", "")).strip().lower(),
            "target_kind": "code",
            "target_id": str(row.get("target_path", "")).strip(),
            "source_path": str(row.get("source_path", "")).strip(),
            "provenance_json": json.dumps(
                {
                    "source_kind": "code",
                    "source_id": str(row.get("source_path", "")).strip(),
                    "target_kind": "code",
                    "target_id": str(row.get("target_path", "")).strip(),
                    "source_path": str(row.get("source_path", "")).strip(),
                    "derived": True,
                },
                sort_keys=True,
                ensure_ascii=False,
            ),
        }
        for row in tables.get("code_edges", [])
        if isinstance(tables.get("code_edges"), list) and isinstance(row, Mapping)
    ]
    edge_rows = [*traceability_edges, *code_edges]
    return {
        "documents": documents,
        "edges": edge_rows,
        "document_count": len(documents),
        "edge_count": len(edge_rows),
        "input_fingerprint": odylith_context_cache.fingerprint_payload(
            {
                "documents": [
                    {
                        "doc_key": row["doc_key"],
                        "content_hash": row["content_hash"],
                        "path": row["path"],
                    }
                    for row in documents
                ],
                "edges": [
                    {
                        "edge_key": row["edge_key"],
                        "relation": row["relation"],
                    }
                    for row in edge_rows
                ],
            }
        ),
    }


def load_compiled_materialization_inputs(*, repo_root: Path) -> dict[str, Any]:
    bundle = odylith_projection_bundle.load_bundle(repo_root=repo_root)
    manifest = dict(bundle.get("manifest", {})) if isinstance(bundle.get("manifest"), Mapping) else {}
    if not bool(manifest.get("ready")):
        return {}
    documents = [dict(row) for row in bundle.get("documents", []) if isinstance(row, Mapping)]
    edges = [dict(row) for row in bundle.get("edges", []) if isinstance(row, Mapping)]
    return {
        "documents": documents,
        "edges": edges,
        "document_count": int(manifest.get("document_count", len(documents)) or 0),
        "edge_count": int(manifest.get("edge_count", len(edges)) or 0),
        "input_fingerprint": str(manifest.get("input_fingerprint", "")).strip(),
        "projection_fingerprint": str(manifest.get("projection_fingerprint", "")).strip(),
        "projection_scope": str(manifest.get("projection_scope", "")).strip(),
        "compiler_manifest": manifest,
    }


def load_manifest(*, repo_root: Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    manifest = odylith_context_cache.read_json_object(local_manifest_path(repo_root=root))
    if manifest and not bool(manifest.get("ready")):
        return _restore_ready_manifest_if_possible(repo_root=root, manifest=manifest)
    return manifest


def projection_documents(
    *,
    connection: Any,
) -> list[dict[str, Any]]:
    return list(build_backend_materialization_inputs(connection=connection).get("documents", []))


def local_backend_ready(*, repo_root: Path) -> bool:
    root = Path(repo_root).resolve()
    manifest = load_manifest(repo_root=root)
    if not backend_dependencies_available():
        return False
    return bool(manifest.get("ready")) and _local_backend_artifacts_present(repo_root=root)


def compatible_projection_scopes(*, requested_scope: str) -> tuple[str, ...]:
    scope_token = str(requested_scope or "default").strip().lower() or "default"
    if scope_token == "default":
        return ("default", "reasoning", "full")
    if scope_token == "reasoning":
        return ("reasoning", "full")
    return (scope_token,)


def projection_scope_satisfies(*, available_scope: str, requested_scope: str) -> bool:
    scope_token = str(available_scope or "").strip().lower()
    return bool(scope_token) and scope_token in compatible_projection_scopes(requested_scope=requested_scope)


def local_backend_matches_projection(
    *,
    repo_root: Path,
    projection_fingerprint: str,
    projection_scope: str,
) -> bool:
    manifest = load_manifest(repo_root=repo_root)
    return (
        bool(manifest)
        and str(manifest.get("projection_fingerprint", "")).strip() == str(projection_fingerprint).strip()
        and str(manifest.get("projection_scope", "")).strip() == str(projection_scope or "").strip().lower()
    )


def local_backend_ready_for_projection(
    *,
    repo_root: Path,
    projection_fingerprint: str,
    projection_scope: str,
) -> bool:
    return local_backend_ready(repo_root=repo_root) and local_backend_matches_projection(
        repo_root=repo_root,
        projection_fingerprint=projection_fingerprint,
        projection_scope=projection_scope,
    )


def backend_runtime_status(*, repo_root: Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    manifest = load_manifest(repo_root=root)
    deps = dependency_snapshot()
    ready = local_backend_ready(repo_root=root)
    status = "ready" if ready else "dependencies_missing" if not backend_dependencies_available() else "cold"
    if manifest and not ready and backend_dependencies_available():
        status = str(manifest.get("status", "")).strip() or "degraded"
    health_error = ""
    if ready:
        ready, health_error = _backend_operational_check(repo_root=root)
        if not ready:
            status = "error"
    return {
        "provider": "odylith_memory_backend",
        "storage": "lance_local_columnar" if ready else "compiler_projection_snapshot",
        "sparse_recall": "tantivy_sparse_recall" if ready else "repo_scan_fallback",
        "graph_expansion": "typed_repo_graph",
        "mode": "embedded_local_first",
        "status": status,
        "ready": ready,
        "dependencies": deps,
        "manifest": manifest,
        "health_error": health_error,
    }


def _open_lance_connection(*, lance_root: Path):
    if lancedb is None:
        raise RuntimeError("lancedb dependency is unavailable")
    return lancedb.connect(str(Path(lance_root).resolve()))


def _close_lance_connection(connection: Any) -> None:
    closeables = (
        getattr(connection, "close", None),
        getattr(getattr(connection, "_conn", None), "close", None),
    )
    for close in closeables:
        if callable(close):
            with contextlib.suppress(Exception):
                close()
            break


def _close_lance_table(table: Any) -> None:
    closeables = (
        getattr(table, "close", None),
        getattr(getattr(table, "_table", None), "close", None),
    )
    for close in closeables:
        if callable(close):
            with contextlib.suppress(Exception):
                close()
            break


@contextlib.contextmanager
def _lance_connection(*, lance_root: Path):
    connection = _open_lance_connection(lance_root=lance_root)
    try:
        yield connection
    finally:
        _close_lance_connection(connection)


@contextlib.contextmanager
def _lance_documents_table(*, repo_root: Path):
    with _lance_connection(lance_root=local_lance_root(repo_root=repo_root)) as connection:
        table = connection.open_table(DOCUMENTS_TABLE)
        try:
            yield table
        finally:
            _close_lance_table(table)


def _documents_schema():
    if pa is None:
        raise RuntimeError("pyarrow dependency is unavailable")
    return pa.schema(
        [
            pa.field("doc_key", pa.string()),
            pa.field("kind", pa.string()),
            pa.field("entity_id", pa.string()),
            pa.field("title", pa.string()),
            pa.field("path", pa.string()),
            pa.field("content", pa.string()),
            pa.field("entity_id_lower", pa.string()),
            pa.field("title_lower", pa.string()),
            pa.field("path_lower", pa.string()),
            pa.field("content_hash", pa.string()),
            pa.field("provenance_json", pa.string()),
            pa.field("embedding", pa.list_(pa.float32(), EMBED_DIMENSIONS)),
        ]
    )


def _edges_schema():
    if pa is None:
        raise RuntimeError("pyarrow dependency is unavailable")
    return pa.schema(
        [
            pa.field("edge_key", pa.string()),
            pa.field("source_kind", pa.string()),
            pa.field("source_id", pa.string()),
            pa.field("relation", pa.string()),
            pa.field("target_kind", pa.string()),
            pa.field("target_id", pa.string()),
            pa.field("source_path", pa.string()),
            pa.field("provenance_json", pa.string()),
        ]
    )


def _backend_operational_check(*, repo_root: Path) -> tuple[bool, str]:
    try:
        with _lance_documents_table(repo_root=repo_root) as table:
            table.count_rows()
        index = _open_tantivy_index(repo_root=repo_root)
        index.searcher()
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
    return True, ""


def _create_lance_tables(
    *,
    repo_root: Path,
    documents: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
) -> None:
    temp_root = Path(tempfile.mkdtemp(prefix="odylith-lance-", dir=str(local_backend_root(repo_root=repo_root))))
    target_root = local_lance_root(repo_root=repo_root)
    try:
        with _suppress_expected_lance_bootstrap_warnings():
            with _lance_connection(lance_root=temp_root) as db:
                if documents:
                    db.create_table(DOCUMENTS_TABLE, data=[dict(row) for row in documents], mode="overwrite")
                else:
                    db.create_table(DOCUMENTS_TABLE, schema=_documents_schema(), mode="overwrite")
                if edges:
                    db.create_table(EDGES_TABLE, data=[dict(row) for row in edges], mode="overwrite")
                else:
                    db.create_table(EDGES_TABLE, schema=_edges_schema(), mode="overwrite")
        if target_root.exists():
            shutil.rmtree(target_root)
        temp_root.rename(target_root)
    except Exception:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise


def _create_tantivy_index(
    *,
    repo_root: Path,
    documents: Sequence[Mapping[str, Any]],
) -> None:
    if tantivy is None:
        raise RuntimeError("tantivy dependency is unavailable")
    temp_root = Path(tempfile.mkdtemp(prefix="odylith-tantivy-", dir=str(local_backend_root(repo_root=repo_root))))
    target_root = local_tantivy_root(repo_root=repo_root)
    try:
        builder = tantivy.SchemaBuilder()
        for field_name in ("doc_key", "kind", "entity_id", "title", "path", "content"):
            builder.add_text_field(field_name, stored=True)
        schema = builder.build()
        index = tantivy.Index(schema, path=str(temp_root))
        writer = index.writer()
        for row in documents:
            writer.add_document(
                tantivy.Document(
                    doc_key=[str(row.get("doc_key", "")).strip()],
                    kind=[str(row.get("kind", "")).strip()],
                    entity_id=[str(row.get("entity_id", "")).strip()],
                    title=[str(row.get("title", "")).strip()],
                    path=[str(row.get("path", "")).strip()],
                    content=[str(row.get("content", "")).strip()],
                )
            )
        writer.commit()
        index.reload()
        if target_root.exists():
            shutil.rmtree(target_root)
        temp_root.rename(target_root)
    except Exception:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise


def materialize_local_backend(
    *,
    repo_root: Path,
    connection: Any | None = None,
    projection_fingerprint: str,
    projection_scope: str,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    backend_root = local_backend_root(repo_root=root)
    backend_root.mkdir(parents=True, exist_ok=True)
    inputs = load_compiled_materialization_inputs(repo_root=root)
    if not inputs:
        if connection is None:
            raise RuntimeError("compiled projection bundle is unavailable and no fallback connection was supplied")
        inputs = build_backend_materialization_inputs(connection=connection)
    manifest = load_manifest(repo_root=root)
    reusable_backend = False
    if backend_dependencies_available() and manifest and local_backend_ready(repo_root=root):
        reusable_backend, _ = _backend_operational_check(repo_root=root)
    requested_scope = str(projection_scope or "default").strip().lower() or "default"
    requested_fingerprint = str(projection_fingerprint).strip()
    if (
        backend_dependencies_available()
        and manifest
        and str(manifest.get("input_fingerprint", "")).strip() == inputs["input_fingerprint"]
        and reusable_backend
    ):
        manifest_scope = str(manifest.get("projection_scope", "")).strip().lower()
        manifest_fingerprint = str(manifest.get("projection_fingerprint", "")).strip()
        if manifest_fingerprint == requested_fingerprint and manifest_scope == requested_scope:
            reused = dict(manifest)
            reused["reused"] = True
            reused["reused_projection_scope"] = manifest_scope
            return reused
        if projection_scope_satisfies(available_scope=manifest_scope, requested_scope=requested_scope):
            try:
                from odylith.runtime.context_engine import odylith_context_engine_store as store

                compatible_fingerprint = store.projection_input_fingerprint(
                    repo_root=root,
                    scope=manifest_scope,
                )
            except Exception:
                compatible_fingerprint = ""
            if manifest_fingerprint and compatible_fingerprint and manifest_fingerprint == compatible_fingerprint:
                reused = dict(manifest)
                reused["reused"] = True
                reused["reused_projection_scope"] = manifest_scope
                reused["requested_projection_scope"] = requested_scope
                reused["requested_projection_fingerprint"] = requested_fingerprint
                return reused

    payload = {
        "version": BACKEND_VERSION,
        "projection_fingerprint": requested_fingerprint,
        "projection_scope": requested_scope,
        "input_fingerprint": inputs["input_fingerprint"],
        "document_count": int(inputs["document_count"]),
        "edge_count": int(inputs["edge_count"]),
        "dependencies": dependency_snapshot(),
        "ready": False,
        "status": "dependencies_missing" if not backend_dependencies_available() else "building",
        "storage": "compiler_projection_snapshot" if not backend_dependencies_available() else "lance_local_columnar",
        "sparse_recall": "repo_scan_fallback",
        "compiler_source": "projection_bundle" if inputs.get("compiler_manifest") else "fallback_connection",
    }
    if isinstance(inputs.get("compiler_manifest"), Mapping):
        payload["compiler_manifest"] = dict(inputs.get("compiler_manifest", {}))
    if not backend_dependencies_available():
        odylith_context_cache.write_json_if_changed(
            repo_root=root,
            path=local_manifest_path(repo_root=root),
            payload=payload,
            lock_key=str(local_manifest_path(repo_root=root)),
        )
        return payload

    try:
        _create_lance_tables(
            repo_root=root,
            documents=inputs["documents"],
            edges=inputs["edges"],
        )
        _create_tantivy_index(
            repo_root=root,
            documents=inputs["documents"],
        )
        payload.update(
            {
                "ready": True,
                "status": "ready",
                "storage": "lance_local_columnar",
                "sparse_recall": "tantivy_sparse_recall",
                "documents_table": DOCUMENTS_TABLE,
                "edges_table": EDGES_TABLE,
            }
        )
    except Exception as exc:
        payload.update(
            {
                "ready": False,
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
    odylith_context_cache.write_json_if_changed(
        repo_root=root,
        path=local_manifest_path(repo_root=root),
        payload=payload,
        lock_key=str(local_manifest_path(repo_root=root)),
    )
    return payload


def _filter_result_kinds(
    rows: Sequence[Mapping[str, Any]],
    *,
    kinds: Sequence[str] | None,
) -> list[dict[str, Any]]:
    allowed = _normalize_kind_filters(kinds)
    filtered: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        if allowed and str(row.get("kind", "")).strip().lower() not in allowed:
            continue
        filtered.append(dict(row))
    return filtered


def exact_lookup(
    *,
    repo_root: Path,
    query: str,
    limit: int,
    kinds: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    root = Path(repo_root).resolve()
    if not local_backend_ready(repo_root=root):
        return []
    normalized = str(query or "").strip()
    if not normalized:
        return []
    variants = {
        normalized.casefold(),
        str(Path(normalized).as_posix()).casefold(),
    }
    expressions: list[str] = []
    for token in sorted(variants):
        if not token:
            continue
        literal = _quote_sql_literal(token)
        expressions.extend(
            [
                f"entity_id_lower = {literal}",
                f"path_lower = {literal}",
                f"title_lower = {literal}",
            ]
        )
    if not expressions:
        return []
    with _lance_documents_table(repo_root=root) as table:
        rows = table.search().where(" OR ".join(expressions)).limit(max(1, int(limit) * 4)).to_list()
    return _rank_rows_with_query_match(
        rows=_filter_result_kinds(rows, kinds=kinds),
        query=normalized,
        limit=limit,
        exact=True,
    )


def _open_tantivy_index(*, repo_root: Path):
    if tantivy is None:
        raise RuntimeError("tantivy dependency is unavailable")
    return tantivy.Index.open(str(local_tantivy_root(repo_root=repo_root)))


def _tantivy_query(index: Any, query: str):
    text = str(query or "").strip()
    if not text:
        return None
    candidates = [text]
    tokenized = " ".join(_tokenize_text(text))
    if tokenized and tokenized not in candidates:
        candidates.append(tokenized)
    for candidate in candidates:
        with contextlib.suppress(Exception):
            return index.parse_query(candidate, default_field_names=list(SPARSE_DEFAULT_FIELDS))
    return None


def sparse_search(
    *,
    repo_root: Path,
    query: str,
    limit: int,
    kinds: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    root = Path(repo_root).resolve()
    if not local_backend_ready(repo_root=root):
        return []
    index = _open_tantivy_index(repo_root=root)
    parsed = _tantivy_query(index, query)
    if parsed is None:
        return []
    searcher = index.searcher()
    hits = searcher.search(parsed, limit=max(8, int(limit) * 4)).hits
    rows: list[dict[str, Any]] = []
    for score, doc_address in hits:
        doc = searcher.doc(doc_address)
        doc_payload = doc.to_dict() if hasattr(doc, "to_dict") else {}
        rows.append(
            {
                "doc_key": _coerce_first_string(doc_payload.get("doc_key")),
                "kind": _coerce_first_string(doc_payload.get("kind")),
                "entity_id": _coerce_first_string(doc_payload.get("entity_id")),
                "title": _coerce_first_string(doc_payload.get("title")),
                "path": _coerce_first_string(doc_payload.get("path")),
                "content": _coerce_first_string(doc_payload.get("content")),
                "score": _safe_float(score),
            }
        )
    return _rank_rows_with_query_match(
        rows=_filter_result_kinds(rows, kinds=kinds),
        query=query,
        limit=limit,
        exact=False,
    )


def hybrid_rerank_search(
    *,
    repo_root: Path,
    query: str,
    limit: int,
    kinds: Sequence[str] | None = None,
    sparse_rows: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    root = Path(repo_root).resolve()
    if not local_backend_ready(repo_root=root):
        return _normalize_search_rows(rows=_filter_result_kinds(sparse_rows or [], kinds=kinds), limit=limit, exact=False)
    sparse_candidates = _normalize_search_rows(
        rows=_filter_result_kinds(sparse_rows or [], kinds=kinds),
        limit=max(8, int(limit) * VECTOR_CANDIDATE_MULTIPLIER),
        exact=False,
    )
    query_vector = _text_embedding(query)
    with _lance_documents_table(repo_root=root) as table:
        vector_rows = table.search(query_vector).limit(max(8, int(limit) * VECTOR_CANDIDATE_MULTIPLIER)).to_list()
    vector_rows = _filter_result_kinds(vector_rows, kinds=kinds)
    combined: dict[str, dict[str, Any]] = {}
    for rank, row in enumerate(sparse_candidates, start=1):
        doc_key = str(row.get("doc_key", "")).strip() or f"{row.get('kind', '')}:{row.get('entity_id', '')}"
        lexical = _lexical_match_features(row, query=query)
        combined[doc_key] = {
            **dict(row),
            "sparse_rank": rank,
            "sparse_rrf": 1.0 / (_RRF_K + float(rank)),
            "sparse_score": max(0.0, _safe_float(row.get("score"))),
            "vector_score": 0.0,
            "lexical_score": lexical["lexical_score"],
            "coverage_score": lexical["coverage"],
            "exact_anchor": lexical["exact_anchor"],
        }
    for rank, row in enumerate(vector_rows, start=1):
        doc_key = str(row.get("doc_key", "")).strip()
        distance = _safe_float(row.get("_distance"))
        vector_score = 1.0 / (1.0 + max(0.0, distance))
        vector_rrf = 1.0 / (_RRF_K + float(rank))
        existing = combined.get(doc_key)
        if existing is None:
            lexical = _lexical_match_features(row, query=query)
            combined[doc_key] = {
                "doc_key": doc_key,
                "kind": str(row.get("kind", "")).strip(),
                "entity_id": str(row.get("entity_id", "")).strip(),
                "title": str(row.get("title", "")).strip(),
                "path": str(row.get("path", "")).strip(),
                "content": str(row.get("content", "")).strip(),
                "score": 0.0,
                "sparse_rank": 0,
                "sparse_rrf": 0.0,
                "sparse_score": 0.0,
                "vector_score": vector_score,
                "vector_rrf": vector_rrf,
                "lexical_score": lexical["lexical_score"],
                "coverage_score": lexical["coverage"],
                "exact_anchor": lexical["exact_anchor"],
            }
            continue
        existing["vector_score"] = max(_safe_float(existing.get("vector_score")), vector_score)
        existing["vector_rrf"] = max(_safe_float(existing.get("vector_rrf")), vector_rrf)
    ranked = []
    for row in combined.values():
        sparse_score = _safe_float(row.get("sparse_score"))
        vector_score = _safe_float(row.get("vector_score"))
        sparse_rrf = _safe_float(row.get("sparse_rrf"))
        vector_rrf = _safe_float(row.get("vector_rrf"))
        lexical_score = _safe_float(row.get("lexical_score"))
        coverage_score = _safe_float(row.get("coverage_score"))
        exact_anchor = _safe_float(row.get("exact_anchor"))
        final_score = (
            sparse_score * 0.5
            + vector_score * 0.16
            + sparse_rrf * 6.0
            + vector_rrf * 2.25
            + lexical_score * 0.45
            + coverage_score * 0.75
            + exact_anchor * 1.1
        )
        ranked.append(
            {
                "doc_key": str(row.get("doc_key", "")).strip(),
                "kind": str(row.get("kind", "")).strip(),
                "entity_id": str(row.get("entity_id", "")).strip(),
                "title": str(row.get("title", "")).strip(),
                "path": str(row.get("path", "")).strip(),
                "score": final_score,
                "score_components": {
                    "sparse": round(sparse_score, 6),
                    "vector": round(vector_score, 6),
                    "sparse_rrf": round(sparse_rrf, 6),
                    "vector_rrf": round(vector_rrf, 6),
                    "lexical": round(lexical_score, 6),
                    "coverage": round(coverage_score, 6),
                    "exact_anchor": round(exact_anchor, 6),
                },
            }
        )
    ranked.sort(key=lambda row: (-_safe_float(row.get("score")), str(row.get("path", "")), str(row.get("entity_id", ""))))
    return ranked[: max(1, int(limit))]


def _normalize_search_rows(
    *,
    rows: Sequence[Mapping[str, Any]],
    limit: int,
    exact: bool,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        kind = str(row.get("kind", "")).strip()
        entity_id = str(row.get("entity_id", "")).strip()
        path = str(row.get("path", "")).strip()
        key = (kind, entity_id, path)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(
            {
                "doc_key": str(row.get("doc_key", "")).strip(),
                "kind": kind,
                "entity_id": entity_id,
                "title": str(row.get("title", "")).strip(),
                "path": path,
                "score": 0.0 if exact else _safe_float(row.get("score")),
            }
        )
        if len(normalized) >= max(1, int(limit)):
            break
    return normalized


def all_documents(*, repo_root: Path, include_embedding: bool = False) -> list[dict[str, Any]]:
    root = Path(repo_root).resolve()
    if not local_backend_ready(repo_root=root):
        return []
    try:
        with _lance_documents_table(repo_root=root) as table:
            arrow_table = table.to_arrow()
    except Exception:
        return []
    return [
        {
            key: value
            for key, value in row.items()
            if key
            in {
                "doc_key",
                "kind",
                "entity_id",
                "title",
                "path",
                "content",
                "content_hash",
                "provenance_json",
            }
            or (include_embedding and key == "embedding")
        }
        for row in arrow_table.to_pylist()
    ]


__all__ = [
    "all_documents",
    "backend_dependencies_available",
    "backend_runtime_status",
    "build_backend_materialization_inputs",
    "compatible_projection_scopes",
    "derived_embedding",
    "dependency_snapshot",
    "exact_lookup",
    "hybrid_rerank_search",
    "load_manifest",
    "local_backend_matches_projection",
    "local_backend_ready",
    "local_backend_ready_for_projection",
    "local_backend_root",
    "materialize_local_backend",
    "projection_scope_satisfies",
    "projection_documents",
    "sparse_search",
]
