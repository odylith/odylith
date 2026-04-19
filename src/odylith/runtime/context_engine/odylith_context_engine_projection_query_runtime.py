"""Odylith Context Engine Projection Query Runtime helpers for the Odylith context engine layer."""

from __future__ import annotations

import ast
import contextlib
import datetime as dt
import json
import math
import os
from pathlib import Path
import re
import shlex
import shutil
import socket
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from typing import Any
from typing import Callable
from typing import Iterable
from typing import Mapping
from typing import Sequence
from odylith.runtime.common.value_coercion import normalize_string_list
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.context_engine import odylith_context_engine_contracts
def _normalize_entity_kind(kind: str | None) -> str:
    token = str(kind or "").strip().lower()
    return context_engine_store._ENTITY_KIND_ALIASES.get(token, token)


def _normalize_repo_token(token: str, *, repo_root: Path) -> str:
    raw = str(token or "").strip().replace("\\", "/")
    if not raw:
        return ""
    embedded_match = context_engine_store._RAW_PATH_TOKEN_RE.search(raw)
    if embedded_match is not None:
        raw = str(embedded_match.group(1) or "").strip().replace("\\", "/")
        if not raw:
            return ""
    path = Path(raw)
    if path.is_absolute():
        try:
            normalized = path.resolve().relative_to(repo_root).as_posix()
            return context_engine_store.canonical_truth_token(_resolve_moved_plan_token(normalized, repo_root=repo_root), repo_root=repo_root)
        except ValueError:
            return path.resolve().as_posix()
    while raw.startswith("./"):
        raw = raw[2:]
    normalized = Path(raw).as_posix().strip("/")
    return context_engine_store.canonical_truth_token(_resolve_moved_plan_token(normalized, repo_root=repo_root), repo_root=repo_root)


def _resolve_moved_plan_token(normalized: str, *, repo_root: Path) -> str:
    token = str(normalized or "").strip().replace("\\", "/").strip("/")
    if not token or not token.startswith("odylith/technical-plans/in-progress/") or not token.endswith(".md"):
        return token
    if (repo_root / token).is_file():
        return token
    done_root = repo_root / "plan" / "done"
    if not done_root.is_dir():
        return token
    matches = sorted(
        path.relative_to(repo_root).as_posix()
        for path in done_root.glob(f"**/{Path(token).name}")
        if path.is_file()
    )
    if len(matches) == 1:
        return matches[0]
    return token


def _available_full_scan_roots(*, repo_root: Path) -> list[str]:
    """Return the highest-signal source roots for raw repo discovery fallback."""
    roots = [token for token in context_engine_store._FULL_SCAN_ROOTS if (repo_root / token).exists()]
    return roots or ["."]


def _full_scan_terms(*, repo_root: Path, query: str = "", changed_paths: Sequence[str] = ()) -> list[str]:
    """Derive stable ripgrep terms from the user query and grounded changed paths."""
    terms: list[str] = []
    normalized_query = str(query or "").strip()
    if normalized_query:
        terms.append(normalized_query)
    for raw_path in changed_paths:
        normalized_path = _normalize_repo_token(str(raw_path or ""), repo_root=repo_root)
        if not normalized_path:
            continue
        basename = Path(normalized_path).name
        stem = Path(normalized_path).stem
        for token in (normalized_path, basename, stem, stem.replace("_", "-"), stem.replace("-", "_")):
            stripped = str(token or "").strip()
            if len(stripped) >= 3:
                terms.append(stripped)
    return context_engine_store._dedupe_strings(terms)[:3]


def _full_scan_reason_message(reason: str) -> str:
    normalized = str(reason or "").strip().lower()
    if not normalized:
        return ""
    if normalized == "runtime_unavailable":
        return "Runtime projections were unavailable; confirm with a raw repo scan."
    if normalized == "repo_scan_candidate_only":
        return "The runtime had to fall back to raw repo-scan-derived candidates; confirm with direct source reads."
    if normalized == "odylith_backend_unavailable":
        return "Odylith local retrieval was unavailable; the runtime fell back to raw repo scan evidence."
    if normalized == "context_requires_exact_resolution":
        return "Context resolution requires exact entity/path/alias evidence; raw repo scan is recommended."
    if normalized == "no_grounded_paths":
        return "No explicit or scoped changed paths were available to ground impact analysis."
    if normalized == "working_tree_scope_degraded":
        return "Session-scoped grounding widened into shared/control-plane context; add one concrete code, manifest, or contract anchor."
    if normalized == "broad_shared_paths":
        return "Current shared/control-plane context is still broad; add one concrete code, manifest, or contract anchor."
    if normalized == "selection_ambiguous":
        return "Workstream selection remained ambiguous; inspect raw source before claiming ownership."
    if normalized == "selection_none":
        return "No workstream could be inferred confidently from the available evidence."
    if normalized == "no_runtime_results":
        return "The runtime did not find grounded matches; raw repo scan is recommended."
    return "Raw repo scan is recommended before treating this result as complete context."


def _full_scan_commands(*, repo_root: Path, terms: Sequence[str]) -> list[str]:
    normalized_terms = [str(token).strip() for token in terms if str(token).strip()]
    if not normalized_terms:
        return []
    command: list[str] = [
        "rg",
        "-n",
        "--hidden",
        "--color",
        "never",
        "--fixed-strings",
        "--ignore-case",
    ]
    for glob in context_engine_store._FULL_SCAN_EXCLUDED_GLOBS:
        command.extend(["--glob", glob])
    for term in normalized_terms:
        command.extend(["-e", term])
    command.extend(_available_full_scan_roots(repo_root=repo_root))
    return [" ".join(shlex.quote(token) for token in command)]


def _run_full_scan(
    *,
    repo_root: Path,
    terms: Sequence[str],
    limit: int = 8,
) -> dict[str, Any]:
    """Run one bounded ripgrep fallback so weak runtime answers can cite raw source."""
    normalized_terms = [str(token).strip() for token in terms if str(token).strip()]
    commands = _full_scan_commands(repo_root=repo_root, terms=normalized_terms)
    payload = {
        "performed": False,
        "terms": normalized_terms,
        "roots": _available_full_scan_roots(repo_root=repo_root),
        "commands": commands,
        "results": [],
    }
    if not normalized_terms:
        return payload
    command: list[str] = [
        "rg",
        "-n",
        "--hidden",
        "--color",
        "never",
        "--fixed-strings",
        "--ignore-case",
        "--max-count",
        "2",
        "--json",
    ]
    for glob in context_engine_store._FULL_SCAN_EXCLUDED_GLOBS:
        command.extend(["--glob", glob])
    for term in normalized_terms:
        command.extend(["-e", term])
    command.extend(payload["roots"])
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            cwd=str(repo_root),
        )
    except OSError as exc:
        payload["error"] = str(exc)
        return payload
    results: list[dict[str, Any]] = []
    for raw_line in str(completed.stdout or "").splitlines():
        if len(results) >= max(1, int(limit)):
            break
        try:
            decoded = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if not isinstance(decoded, Mapping) or str(decoded.get("type", "")).strip() != "match":
            continue
        data = decoded.get("data", {})
        if not isinstance(data, Mapping):
            continue
        path_info = data.get("path", {})
        lines_info = data.get("lines", {})
        line_text = str(lines_info.get("text", "")).rstrip("\n") if isinstance(lines_info, Mapping) else ""
        path_text = str(path_info.get("text", "")).strip() if isinstance(path_info, Mapping) else ""
        if not path_text:
            continue
        path_obj = Path(path_text)
        resolved_path = path_obj if path_obj.is_absolute() else (repo_root / path_obj)
        try:
            relative_path = resolved_path.resolve().relative_to(repo_root).as_posix()
        except ValueError:
            relative_path = resolved_path.as_posix()
        results.append(
            {
                "path": relative_path,
                "line_number": int(data.get("line_number", 0) or 0),
                "line": line_text.strip(),
            }
        )
    payload["performed"] = True
    payload["results"] = results
    payload["returncode"] = int(completed.returncode)
    return payload


def _full_scan_guidance(
    *,
    repo_root: Path,
    reason: str,
    query: str = "",
    changed_paths: Sequence[str] = (),
    perform_scan: bool = False,
    result_limit: int = 8,
) -> dict[str, Any]:
    """Build additive raw-scan guidance without forcing every caller to shell out."""
    terms = _full_scan_terms(repo_root=repo_root, query=query, changed_paths=changed_paths)
    payload = _run_full_scan(repo_root=repo_root, terms=terms, limit=result_limit) if perform_scan else {
        "performed": False,
        "terms": terms,
        "roots": _available_full_scan_roots(repo_root=repo_root),
        "commands": _full_scan_commands(repo_root=repo_root, terms=terms),
        "results": [],
    }
    payload["reason"] = str(reason or "").strip()
    payload["reason_message"] = _full_scan_reason_message(reason)
    payload["changed_paths"] = [str(token).strip() for token in changed_paths if str(token).strip()]
    return payload


def _json_list(raw: str) -> list[str]:
    try:
        decoded = json.loads(str(raw or "[]"))
    except json.JSONDecodeError:
        return []
    if not isinstance(decoded, list):
        return []
    return [str(item).strip() for item in decoded if str(item).strip()]


def _json_dict(raw: Any) -> dict[str, Any]:
    try:
        decoded = json.loads(str(raw or "{}"))
    except json.JSONDecodeError:
        return {}
    return dict(decoded) if isinstance(decoded, Mapping) else {}


def _context_lookup_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().casefold())


def _context_lookup_aliases(*, repo_root: Path, values: Sequence[str]) -> set[str]:
    aliases: set[str] = set()
    for raw_value in values:
        value = str(raw_value or "").strip()
        if not value:
            continue
        lowered = value.casefold()
        aliases.add(lowered)
        compact = _context_lookup_key(value)
        if compact:
            aliases.add(compact)
        normalized_path = _normalize_repo_token(value, repo_root=repo_root)
        if normalized_path:
            aliases.add(normalized_path.casefold())
            normalized_compact = _context_lookup_key(normalized_path)
            if normalized_compact:
                aliases.add(normalized_compact)
            for path_token in (Path(normalized_path).name, Path(normalized_path).stem):
                if not path_token:
                    continue
                aliases.add(path_token.casefold())
                path_compact = _context_lookup_key(path_token)
                if path_compact:
                    aliases.add(path_compact)
    return aliases


def _workstream_lookup_aliases(row: Mapping[str, Any], *, repo_root: Path) -> set[str]:
    metadata = _json_dict(row.get("metadata_json"))
    return _context_lookup_aliases(
        repo_root=repo_root,
        values=(
            str(row.get("idea_id", "")).strip(),
            str(row.get("title", "")).strip(),
            str(metadata.get("title", "")).strip(),
            str(row.get("source_path", "")).strip(),
            str(row.get("idea_file", "")).strip(),
            str(row.get("promoted_to_plan", "")).strip(),
            str(metadata.get("active_release_id", "")).strip(),
            str(metadata.get("active_release_label", "")).strip(),
            str(metadata.get("active_release_version", "")).strip(),
            str(metadata.get("active_release_tag", "")).strip(),
            str(metadata.get("active_release_name", "")).strip(),
            *(
                [str(item).strip() for item in metadata.get("active_release_aliases", []) if str(item).strip()]
                if isinstance(metadata.get("active_release_aliases"), list)
                else []
            ),
        ),
    )


def _release_lookup_aliases(row: Mapping[str, Any], *, repo_root: Path) -> set[str]:
    metadata = _json_dict(row.get("metadata_json"))
    aliases = _json_list(str(row.get("aliases_json", "")))
    values = [
        str(row.get("release_id", "")).strip(),
        str(row.get("version", "")).strip(),
        str(row.get("tag", "")).strip(),
        str(row.get("effective_name", "")).strip(),
        str(row.get("display_label", "")).strip(),
        str(row.get("source_path", "")).strip(),
        *aliases,
    ]
    release_id = str(row.get("release_id", "")).strip()
    if release_id:
        values.append(f"release:{release_id}")
    if "current" in aliases:
        values.extend(("current release", "release current"))
    if "next" in aliases:
        values.extend(("next release", "release next"))
    if metadata:
        values.append(str(metadata.get("name", "")).strip())
        values.append(str(metadata.get("notes", "")).strip())
    return _context_lookup_aliases(repo_root=repo_root, values=values)


def _component_lookup_aliases(row: Mapping[str, Any], *, repo_root: Path) -> set[str]:
    alias_rows = _json_list(str(row.get("aliases_json", "")))
    return _context_lookup_aliases(
        repo_root=repo_root,
        values=(
            str(row.get("component_id", "")).strip(),
            str(row.get("name", "")).strip(),
            str(row.get("spec_ref", "")).strip(),
            *alias_rows,
        ),
    )


def _plan_lookup_aliases(row: Mapping[str, Any], *, repo_root: Path) -> set[str]:
    return _context_lookup_aliases(
        repo_root=repo_root,
        values=(
            str(row.get("plan_path", "")).strip(),
            str(row.get("source_path", "")).strip(),
        ),
    )


def _parse_component_tokens(raw: str) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for token in re.split(r"[,;|]", str(raw or "")):
        value = str(token).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        rows.append(value)
    return rows


def _load_schema_contract_notes(*, repo_root: Path, component_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return context_engine_store.odylith_context_engine_engineering_notes_runtime._load_schema_contract_notes(
        repo_root=repo_root,
        component_rows=component_rows,
    )


def _load_make_target_notes(*, repo_root: Path, component_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return context_engine_store.odylith_context_engine_engineering_notes_runtime._load_make_target_notes(
        repo_root=repo_root,
        component_rows=component_rows,
    )


def _load_bug_learning_notes(*, repo_root: Path, component_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return context_engine_store.odylith_context_engine_engineering_notes_runtime._load_bug_learning_notes(
        repo_root=repo_root,
        component_rows=component_rows,
    )


def _load_engineering_notes(
    *,
    repo_root: Path,
    connection: Any | None = None,
    component_rows: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    return context_engine_store.odylith_context_engine_engineering_notes_runtime._load_engineering_notes(
        repo_root=repo_root,
        connection=connection,
        component_rows=component_rows,
    )


def _python_module_name(*, rel_path: str, source_root: str, module_root: str) -> str:
    return context_engine_store.odylith_context_engine_code_graph_runtime._python_module_name(
        rel_path=rel_path,
        source_root=source_root,
        module_root=module_root,
    )


def _collect_python_module_index(repo_root: Path) -> dict[str, str]:
    return context_engine_store.odylith_context_engine_code_graph_runtime._collect_python_module_index(repo_root)


def _resolve_from_import(
    *,
    current_module: str,
    is_package: bool,
    module: str | None,
    level: int,
    alias_name: str,
    module_index: Mapping[str, str],
) -> str:
    return context_engine_store.odylith_context_engine_code_graph_runtime._resolve_from_import(
        current_module=current_module,
        is_package=is_package,
        module=module,
        level=level,
        alias_name=alias_name,
        module_index=module_index,
    )


def _extract_marker_names(decorators: Sequence[ast.expr]) -> list[str]:
    return context_engine_store.odylith_context_engine_code_graph_runtime._extract_marker_names(decorators)


def _parse_python_artifact(
    *,
    repo_root: Path,
    rel_path: str,
    module_name: str,
    module_index: Mapping[str, str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    return context_engine_store.odylith_context_engine_code_graph_runtime._parse_python_artifact(
        repo_root=repo_root,
        rel_path=rel_path,
        module_name=module_name,
        module_index=module_index,
    )


def _module_command_to_path(
    *,
    repo_root: Path,
    module_token: str,
    module_index: Mapping[str, str],
) -> str:
    return context_engine_store.odylith_context_engine_code_graph_runtime._module_command_to_path(
        repo_root=repo_root,
        module_token=module_token,
        module_index=module_index,
    )


def _relation_for_target_path(target_path: str) -> str:
    return context_engine_store.odylith_context_engine_code_graph_runtime._relation_for_target_path(target_path)


def _load_make_artifacts(
    *,
    repo_root: Path,
    module_index: Mapping[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return context_engine_store.odylith_context_engine_code_graph_runtime._load_make_artifacts(
        repo_root=repo_root,
        module_index=module_index,
    )


def _doc_source_paths(*, repo_root: Path) -> list[Path]:
    return context_engine_store.odylith_context_engine_code_graph_runtime._doc_source_paths(repo_root=repo_root)


def _load_doc_relationship_edges(*, repo_root: Path) -> list[dict[str, Any]]:
    return context_engine_store.odylith_context_engine_code_graph_runtime._load_doc_relationship_edges(repo_root=repo_root)


def _load_traceability_doc_code_edges_from_rows(trace_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return context_engine_store.odylith_context_engine_code_graph_runtime._load_traceability_doc_code_edges_from_rows(trace_rows)


def _load_traceability_doc_code_edges(connection: Any) -> list[dict[str, Any]]:
    return context_engine_store.odylith_context_engine_code_graph_runtime._load_traceability_doc_code_edges(connection)


def _merge_edge_metadata_values(*values: Any) -> list[Any]:
    rows: list[Any] = []
    seen: set[str] = set()
    for value in values:
        candidates: Sequence[Any]
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            candidates = list(value)
        elif value in (None, "", [], {}):
            candidates = []
        else:
            candidates = [value]
        for candidate in candidates:
            if candidate in (None, "", [], {}):
                continue
            token = context_engine_store.odylith_context_cache.fingerprint_payload(candidate)
            if token in seen:
                continue
            seen.add(token)
            rows.append(candidate)
    return rows


def _merge_edge_metadata(existing: Mapping[str, Any], incoming: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for key in sorted({*existing.keys(), *incoming.keys()}):
        values = _merge_edge_metadata_values(existing.get(key), incoming.get(key))
        if not values:
            continue
        merged[key] = values[0] if len(values) == 1 else values
    return merged


def _dedupe_code_edges(edges: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str, str], dict[str, Any]] = {}
    counts: dict[tuple[str, str, str], int] = {}
    for row in edges:
        source_path = str(row.get("source_path", "")).strip()
        relation = str(row.get("relation", "")).strip()
        target_path = str(row.get("target_path", "")).strip()
        if not source_path or not relation or not target_path:
            continue
        key = (source_path, relation, target_path)
        metadata = dict(row.get("metadata") or {})
        counts[key] = counts.get(key, 0) + 1
        if key not in merged:
            merged[key] = {
                "source_path": source_path,
                "relation": relation,
                "target_path": target_path,
                "metadata": metadata,
            }
            continue
        merged[key]["metadata"] = _merge_edge_metadata(
            dict(merged[key].get("metadata") or {}),
            metadata,
        )
    rows: list[dict[str, Any]] = []
    for key in sorted(merged):
        payload = dict(merged[key])
        metadata = dict(payload.get("metadata") or {})
        if counts.get(key, 0) > 1:
            metadata["evidence_count"] = counts[key]
        payload["metadata"] = metadata
        rows.append(payload)
    return rows


def _load_code_graph(
    *,
    repo_root: Path,
    connection: Any | None = None,
    trace_rows: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return context_engine_store.odylith_context_engine_code_graph_runtime._load_code_graph(
        repo_root=repo_root,
        connection=connection,
        trace_rows=trace_rows,
    )


def _module_index_from_code_artifacts_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    return {
        str(row.get("module_name", "")).strip(): str(row.get("path", "")).strip()
        for row in rows
        if isinstance(row, Mapping) and str(row.get("module_name", "")).strip() and str(row.get("path", "")).strip()
    }


def _module_index_from_code_artifacts(connection: Any) -> dict[str, str]:
    rows = connection.execute("SELECT module_name, path FROM code_artifacts").fetchall()
    return _module_index_from_code_artifacts_rows(rows)


def _iter_test_functions(tree: ast.AST) -> list[tuple[str, list[str]]]:
    rows: list[tuple[str, list[str]]] = []
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            rows.append((node.name, _extract_marker_names(node.decorator_list)))
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            class_markers = _extract_marker_names(node.decorator_list)
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name.startswith("test_"):
                    rows.append((f"{node.name}::{child.name}", sorted(set([*class_markers, *_extract_marker_names(child.decorator_list)]))))
    return rows


def _path_mtime_iso(path: Path) -> str:
    try:
        stamp = path.stat().st_mtime
    except OSError:
        return ""
    return dt.datetime.fromtimestamp(stamp, tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_pytest_lastfailed(*, repo_root: Path) -> dict[str, dict[str, Any]]:
    target = repo_root / context_engine_store._PYTEST_LASTFAILED_PATH
    if not target.is_file():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(payload, Mapping):
        node_ids = [str(key).strip() for key, value in payload.items() if value]
    elif isinstance(payload, list):
        node_ids = [str(item).strip() for item in payload if str(item).strip()]
    else:
        node_ids = []
    seen_at = _path_mtime_iso(target)
    rows: dict[str, dict[str, Any]] = {}
    for node_id in node_ids:
        if not node_id:
            continue
        rows[node_id] = {
            "recent_failure": True,
            "failure_count": 1,
            "last_seen_utc": seen_at,
            "last_failure_utc": seen_at,
            "sources": ["pytest_lastfailed"],
        }
    return rows


def _candidate_test_report_paths(*, repo_root: Path) -> list[Path]:
    rows: list[Path] = []
    seen: set[str] = set()
    for rel_root, glob in context_engine_store._TEST_HISTORY_REPORT_GLOBS:
        root = repo_root / rel_root
        candidates: Iterable[Path]
        if root.is_dir():
            candidates = sorted(path for path in root.rglob(glob) if path.is_file())
        elif root.is_file():
            candidates = [root]
        else:
            candidates = []
        for path in candidates:
            token = str(path.resolve())
            if token in seen:
                continue
            seen.add(token)
            rows.append(path.resolve())
    return rows


def _node_id_from_junit_case(*, repo_root: Path, testcase: ET.Element) -> str:
    file_attr = str(testcase.attrib.get("file", "")).strip()
    name_attr = str(testcase.attrib.get("name", "")).strip()
    if not name_attr:
        return ""
    if file_attr:
        return f"{_normalize_repo_token(file_attr, repo_root=repo_root)}::{name_attr}"
    classname = str(testcase.attrib.get("classname", "")).strip()
    if not classname:
        return ""
    path_guess = classname.replace(".", "/")
    if not path_guess.endswith(".py"):
        path_guess = f"{path_guess}.py"
    return f"{_normalize_repo_token(path_guess, repo_root=repo_root)}::{name_attr}"


def _read_junit_failures(*, repo_root: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for report_path in _candidate_test_report_paths(repo_root=repo_root):
        try:
            root = ET.fromstring(report_path.read_text(encoding="utf-8"))
        except (OSError, ET.ParseError):
            continue
        seen_at = _path_mtime_iso(report_path)
        for testcase in root.iter("testcase"):
            has_failure = any(child.tag in {"failure", "error"} for child in list(testcase))
            if not has_failure:
                continue
            node_id = _node_id_from_junit_case(repo_root=repo_root, testcase=testcase)
            if not node_id:
                continue
            payload = rows.setdefault(
                node_id,
                {
                    "recent_failure": False,
                    "failure_count": 0,
                    "last_seen_utc": seen_at,
                    "last_failure_utc": seen_at,
                    "sources": [],
                },
            )
            payload["recent_failure"] = True
            payload["failure_count"] = int(payload.get("failure_count", 0)) + 1
            payload["last_seen_utc"] = max(str(payload.get("last_seen_utc", "")), seen_at)
            payload["last_failure_utc"] = max(str(payload.get("last_failure_utc", "")), seen_at)
            sources = [str(token).strip() for token in payload.get("sources", []) if str(token).strip()]
            if "junit" not in sources:
                sources.append("junit")
            payload["sources"] = sources
    return rows


def _merge_test_history_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for row in rows:
        node_id = str(row.get("node_id", "")).strip()
        if not node_id:
            continue
        payload = merged.setdefault(
            node_id,
            {
                "recent_failure": False,
                "failure_count": 0,
                "last_seen_utc": "",
                "last_failure_utc": "",
                "sources": [],
            },
        )
        payload["recent_failure"] = bool(payload.get("recent_failure")) or bool(row.get("recent_failure"))
        payload["failure_count"] = int(payload.get("failure_count", 0)) + int(row.get("failure_count", 0) or 0)
        payload["last_seen_utc"] = max(str(payload.get("last_seen_utc", "")), str(row.get("last_seen_utc", "")))
        payload["last_failure_utc"] = max(str(payload.get("last_failure_utc", "")), str(row.get("last_failure_utc", "")))
        payload["sources"] = context_engine_store._dedupe_strings(
            [
                *[str(token).strip() for token in payload.get("sources", []) if str(token).strip()],
                *[str(token).strip() for token in row.get("sources", []) if str(token).strip()],
            ]
        )
    for payload in merged.values():
        payload["empirical_score"] = (100 if bool(payload.get("recent_failure")) else 0) + int(payload.get("failure_count", 0))
    return merged


def _load_test_history(*, repo_root: Path) -> dict[str, dict[str, Any]]:
    lastfailed_rows = [
        {"node_id": node_id, **payload}
        for node_id, payload in _read_pytest_lastfailed(repo_root=repo_root).items()
    ]
    junit_rows = [
        {"node_id": node_id, **payload}
        for node_id, payload in _read_junit_failures(repo_root=repo_root).items()
    ]
    return _merge_test_history_rows([*lastfailed_rows, *junit_rows])


def _load_test_graph(
    *,
    repo_root: Path,
    connection: Any | None = None,
    code_artifacts: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if code_artifacts is not None:
        module_index = _module_index_from_code_artifacts_rows(code_artifacts)
    elif connection is not None:
        module_index = _module_index_from_code_artifacts(connection)
    else:
        raise RuntimeError("code artifacts or connection required for test graph compilation")
    history_by_node = _load_test_history(repo_root=repo_root)
    rows: list[dict[str, Any]] = []
    tests_root = repo_root / "tests"
    if not tests_root.is_dir():
        return rows
    for path in sorted(tests_root.rglob("test_*.py")):
        rel_path = path.relative_to(repo_root).as_posix()
        module_name = _python_module_name(rel_path=rel_path, source_root="tests", module_root="tests")
        artifact, _edges = _parse_python_artifact(
            repo_root=repo_root,
            rel_path=rel_path,
            module_name=module_name,
            module_index=module_index,
        )
        source = _raw_text(path)
        try:
            tree = ast.parse(source or "", filename=rel_path)
        except SyntaxError:
            continue
        test_functions = _iter_test_functions(tree)
        for name, markers in test_functions:
            node_id = f"{rel_path}::{name}"
            history = history_by_node.get(node_id, {})
            rows.append(
                {
                    "test_id": node_id,
                    "test_path": rel_path,
                    "test_name": name,
                    "node_id": node_id,
                    "markers": markers,
                    "target_paths": sorted(set([*artifact["imports"], *artifact["contract_refs"]])),
                    "metadata": {
                        "layer": "tests",
                        "history": {
                            "recent_failure": bool(history.get("recent_failure")),
                            "failure_count": int(history.get("failure_count", 0) or 0),
                            "last_seen_utc": str(history.get("last_seen_utc", "")).strip(),
                            "last_failure_utc": str(history.get("last_failure_utc", "")).strip(),
                            "sources": [
                                str(token).strip()
                                for token in history.get("sources", [])
                                if str(token).strip()
                            ]
                            if isinstance(history.get("sources"), list)
                            else [],
                            "empirical_score": int(history.get("empirical_score", 0) or 0),
                        },
                    },
                }
            )
    return rows


def _summarize_entity(entity: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "kind": str(entity.get("kind", "")).strip(),
        "entity_id": str(entity.get("entity_id", "")).strip(),
        "title": str(entity.get("title", "")).strip(),
        "path": str(entity.get("path", "")).strip(),
        "status": str(entity.get("status", "")).strip(),
    }


from odylith.runtime.context_engine import odylith_context_engine_projection_backlog_runtime
from odylith.runtime.context_engine import odylith_context_engine_projection_entity_runtime
from odylith.runtime.context_engine import odylith_context_engine_projection_registry_runtime
from odylith.runtime.context_engine import odylith_context_engine_projection_runtime
from odylith.runtime.context_engine import odylith_context_engine_projection_search_runtime
from odylith.runtime.context_engine import tooling_guidance_catalog

_MAKE_TARGET_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.-]*):(?:\s|$)")


_ProjectionConnection = odylith_context_engine_projection_search_runtime._ProjectionConnection

_projection_snapshot_cache_signature = odylith_context_engine_projection_search_runtime._projection_snapshot_cache_signature

_connect = odylith_context_engine_projection_search_runtime._connect

_path_fingerprint = odylith_context_engine_projection_search_runtime._path_fingerprint

_test_history_report_inputs = odylith_context_engine_projection_search_runtime._test_history_report_inputs

_workspace_activity_fingerprint = odylith_context_engine_projection_search_runtime._workspace_activity_fingerprint

_radar_source_root = odylith_context_engine_projection_search_runtime._radar_source_root

_technical_plans_root = odylith_context_engine_projection_search_runtime._technical_plans_root

_casebook_bugs_root = odylith_context_engine_projection_search_runtime._casebook_bugs_root

_component_specs_root = odylith_context_engine_projection_search_runtime._component_specs_root

_component_registry_path = odylith_context_engine_projection_search_runtime._component_registry_path

_product_root = odylith_context_engine_projection_search_runtime._product_root

_atlas_catalog_path = odylith_context_engine_projection_search_runtime._atlas_catalog_path

_compass_stream_path = odylith_context_engine_projection_search_runtime._compass_stream_path

_traceability_graph_path = odylith_context_engine_projection_search_runtime._traceability_graph_path

_projected_input_fingerprints = odylith_context_engine_projection_search_runtime._projected_input_fingerprints

projection_input_fingerprint = odylith_context_engine_projection_search_runtime.projection_input_fingerprint

_archive_files = odylith_context_engine_projection_search_runtime._archive_files

_collect_markdown_sections = odylith_context_engine_projection_search_runtime._collect_markdown_sections

_parse_markdown_table = odylith_context_engine_projection_search_runtime._parse_markdown_table

_parse_link_target = odylith_context_engine_projection_search_runtime._parse_link_target

_load_idea_specs = odylith_context_engine_projection_search_runtime._load_idea_specs

_load_backlog_projection = odylith_context_engine_projection_search_runtime._load_backlog_projection

_load_plan_projection = odylith_context_engine_projection_search_runtime._load_plan_projection

_load_bug_projection = odylith_context_engine_projection_search_runtime._load_bug_projection

_normalize_bug_projection_rows = odylith_context_engine_projection_search_runtime._normalize_bug_projection_rows

_normalize_bug_link_target = odylith_context_engine_projection_search_runtime._normalize_bug_link_target

_is_bug_placeholder_row = odylith_context_engine_projection_search_runtime._is_bug_placeholder_row

_safe_json = odylith_context_engine_projection_search_runtime._safe_json

_raw_text = odylith_context_engine_projection_search_runtime._raw_text

_load_codex_event_projection = odylith_context_engine_projection_search_runtime._load_codex_event_projection

_load_traceability_projection = odylith_context_engine_projection_search_runtime._load_traceability_projection

_load_release_projection = odylith_context_engine_projection_runtime._load_release_projection

_load_diagram_projection = odylith_context_engine_projection_search_runtime._load_diagram_projection

_looks_like_repo_path = odylith_context_engine_projection_search_runtime._looks_like_repo_path

_extract_path_refs = odylith_context_engine_projection_search_runtime._extract_path_refs

_extract_workstream_refs = odylith_context_engine_projection_search_runtime._extract_workstream_refs

_first_summary = odylith_context_engine_projection_search_runtime._first_summary

_note_title = odylith_context_engine_projection_search_runtime._note_title

_string_list = odylith_context_engine_projection_search_runtime._string_list

_parse_markdown_fields = odylith_context_engine_projection_search_runtime._parse_markdown_fields

_trim_multiline_lines = odylith_context_engine_projection_search_runtime._trim_multiline_lines

_join_bug_field_lines = odylith_context_engine_projection_search_runtime._join_bug_field_lines

_parse_bug_entry_fields = odylith_context_engine_projection_search_runtime._parse_bug_entry_fields

_bug_archive_bucket_from_link_target = odylith_context_engine_projection_search_runtime._bug_archive_bucket_from_link_target

canonicalize_bug_status = odylith_context_engine_projection_search_runtime.canonicalize_bug_status

_bug_is_open = odylith_context_engine_projection_search_runtime._bug_is_open

_ordered_bug_detail_sections = odylith_context_engine_projection_search_runtime._ordered_bug_detail_sections

_bug_summary_from_fields = odylith_context_engine_projection_search_runtime._bug_summary_from_fields

_component_rows_from_index = odylith_context_engine_projection_search_runtime._component_rows_from_index

_build_bug_reference_lookup = odylith_context_engine_projection_search_runtime._build_bug_reference_lookup

_related_bug_refs_from_text = odylith_context_engine_projection_search_runtime._related_bug_refs_from_text

_classify_bug_path_refs = odylith_context_engine_projection_search_runtime._classify_bug_path_refs

_component_matches_for_bug_paths = odylith_context_engine_projection_search_runtime._component_matches_for_bug_paths

_diagram_refs_for_bug_components = odylith_context_engine_projection_search_runtime._diagram_refs_for_bug_components

_bug_intelligence_coverage = odylith_context_engine_projection_search_runtime._bug_intelligence_coverage

_split_bug_guidance_items = odylith_context_engine_projection_search_runtime._split_bug_guidance_items

_bug_agent_guidance = odylith_context_engine_projection_search_runtime._bug_agent_guidance

_load_component_match_rows_from_components = odylith_context_engine_projection_search_runtime._load_component_match_rows_from_components

_load_component_match_rows = odylith_context_engine_projection_search_runtime._load_component_match_rows

_components_for_paths = odylith_context_engine_projection_search_runtime._components_for_paths

_load_adr_notes = odylith_context_engine_projection_search_runtime._load_adr_notes

_load_invariant_notes = odylith_context_engine_projection_search_runtime._load_invariant_notes

_load_data_ownership_notes = odylith_context_engine_projection_search_runtime._load_data_ownership_notes

_load_section_bullet_notes = odylith_context_engine_projection_search_runtime._load_section_bullet_notes

_markdown_title = odylith_context_engine_projection_search_runtime._markdown_title

_load_guidance_chunk_notes = odylith_context_engine_projection_search_runtime._load_guidance_chunk_notes

_load_runbook_notes = odylith_context_engine_projection_search_runtime._load_runbook_notes

_ENGINEERING_NOTE_KIND_SET = odylith_context_engine_contracts._ENGINEERING_NOTE_KIND_SET
_SECTION_NOTE_SOURCES = odylith_context_engine_contracts._SECTION_NOTE_SOURCES
_WORKSTREAM_ID_RE = odylith_context_engine_contracts._WORKSTREAM_ID_RE
_dedupe_strings = normalize_string_list

_projection_state_row = odylith_context_engine_projection_search_runtime._projection_state_row

_empty_projection_tables = odylith_context_engine_projection_search_runtime._empty_projection_tables

warm_projections = odylith_context_engine_projection_search_runtime.warm_projections

_runtime_enabled = odylith_context_engine_projection_search_runtime._runtime_enabled

_warm_runtime = odylith_context_engine_projection_search_runtime._warm_runtime

_projection_cache_signature = odylith_context_engine_projection_search_runtime._projection_cache_signature

_cached_projection_rows = odylith_context_engine_projection_search_runtime._cached_projection_rows

clear_runtime_process_caches = odylith_context_engine_projection_search_runtime.clear_runtime_process_caches

prime_reasoning_projection_cache = odylith_context_engine_projection_search_runtime.prime_reasoning_projection_cache

_path_signature = odylith_context_engine_projection_search_runtime._path_signature

_architecture_bundle_mermaid_signature_hash = odylith_context_engine_projection_search_runtime._architecture_bundle_mermaid_signature_hash

_bootstraps_signature = odylith_context_engine_projection_search_runtime._bootstraps_signature

_runtime_optimization_cache_signature = odylith_context_engine_projection_search_runtime._runtime_optimization_cache_signature

_merge_search_results = odylith_context_engine_projection_search_runtime._merge_search_results

_repair_odylith_backend = odylith_context_engine_projection_search_runtime._repair_odylith_backend

_search_row_from_entity = odylith_context_engine_projection_search_runtime._search_row_from_entity

search_entities_payload = odylith_context_engine_projection_search_runtime.search_entities_payload

search_entities = odylith_context_engine_projection_search_runtime.search_entities

_miss_recovery_query_tokens = odylith_context_engine_projection_search_runtime._miss_recovery_query_tokens

_build_miss_recovery_queries = odylith_context_engine_projection_search_runtime._build_miss_recovery_queries

_repo_scan_inferred_kind = odylith_context_engine_projection_search_runtime._repo_scan_inferred_kind

_repo_scan_recovery_rows = odylith_context_engine_projection_search_runtime._repo_scan_recovery_rows

_recovery_search_payload = odylith_context_engine_projection_search_runtime._recovery_search_payload

_recovery_search_rows = odylith_context_engine_projection_search_runtime._recovery_search_rows

_recovery_note_like_kind = odylith_context_engine_projection_search_runtime._recovery_note_like_kind

_miss_recovery_projection_path_kind = odylith_context_engine_projection_search_runtime._miss_recovery_projection_path_kind

_miss_recovery_projection_terms = odylith_context_engine_projection_search_runtime._miss_recovery_projection_terms

_cached_miss_recovery_projection_index = odylith_context_engine_projection_search_runtime._cached_miss_recovery_projection_index

_projection_miss_recovery_rows = odylith_context_engine_projection_search_runtime._projection_miss_recovery_rows

_compact_miss_recovery_result = odylith_context_engine_projection_search_runtime._compact_miss_recovery_result

_compact_miss_recovery_for_packet = odylith_context_engine_projection_search_runtime._compact_miss_recovery_for_packet

_collect_retrieval_miss_recovery = odylith_context_engine_projection_search_runtime._collect_retrieval_miss_recovery





# Keep the store dependency explicit without pulling it through module bootstrap.
from odylith.runtime.context_engine import odylith_context_engine_store as context_engine_store

_entity_from_row = odylith_context_engine_projection_entity_runtime._entity_from_row

_entity_by_kind_id = odylith_context_engine_projection_entity_runtime._entity_by_kind_id

_entity_by_path = odylith_context_engine_projection_entity_runtime._entity_by_path

_unique_entity_by_path_alias = odylith_context_engine_projection_entity_runtime._unique_entity_by_path_alias

_projection_exact_search_results = odylith_context_engine_projection_entity_runtime._projection_exact_search_results

_repo_scan_candidate_search_results = odylith_context_engine_projection_entity_runtime._repo_scan_candidate_search_results

_resolve_context_entity = odylith_context_engine_projection_entity_runtime._resolve_context_entity

_relation_rows = odylith_context_engine_projection_entity_runtime._relation_rows

_related_entities = odylith_context_engine_projection_entity_runtime._related_entities

_recent_context_events = odylith_context_engine_projection_entity_runtime._recent_context_events

_delivery_context_rows = odylith_context_engine_projection_entity_runtime._delivery_context_rows

load_context_dossier = odylith_context_engine_projection_entity_runtime.load_context_dossier

load_backlog_rows = odylith_context_engine_projection_backlog_runtime.load_backlog_rows

_markdown_section_bodies = odylith_context_engine_projection_backlog_runtime._markdown_section_bodies

load_backlog_list = odylith_context_engine_projection_backlog_runtime.load_backlog_list

_runtime_backlog_detail_rows = odylith_context_engine_projection_backlog_runtime._runtime_backlog_detail_rows

_runtime_backlog_detail = odylith_context_engine_projection_backlog_runtime._runtime_backlog_detail

load_backlog_detail = odylith_context_engine_projection_backlog_runtime.load_backlog_detail

load_backlog_document = odylith_context_engine_projection_backlog_runtime.load_backlog_document

load_plan_rows = odylith_context_engine_projection_backlog_runtime.load_plan_rows

load_bug_rows = odylith_context_engine_projection_backlog_runtime.load_bug_rows

load_bug_snapshot = odylith_context_engine_projection_backlog_runtime.load_bug_snapshot

_component_entry_from_runtime_row = odylith_context_engine_projection_registry_runtime._component_entry_from_runtime_row

load_component_index = odylith_context_engine_projection_registry_runtime.load_component_index

load_registry_list = odylith_context_engine_projection_registry_runtime.load_registry_list

load_component_registry_snapshot = odylith_context_engine_projection_registry_runtime.load_component_registry_snapshot

load_registry_detail = odylith_context_engine_projection_registry_runtime.load_registry_detail

