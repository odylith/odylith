"""Odylith Context Engine Projection Entity Runtime helpers for the Odylith context engine layer."""

from __future__ import annotations

def _store():
    from odylith.runtime.context_engine import odylith_context_engine_store as store

    return store


from typing import Any

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.context_engine import odylith_context_engine_projection_search_runtime
from odylith.runtime.context_engine import odylith_context_engine_runtime_learning_runtime
from odylith.runtime.context_engine import odylith_context_engine_runtime_support
from odylith.runtime.governance import release_planning_contract

_connect = odylith_context_engine_projection_search_runtime._connect
_warm_runtime = odylith_context_engine_projection_search_runtime._warm_runtime
_odylith_ablation_active = odylith_context_engine_runtime_learning_runtime._odylith_ablation_active
record_runtime_timing = odylith_context_engine_runtime_support.record_runtime_timing

def _entity_from_row(*, kind: str, row: Mapping[str, Any]) -> dict[str, Any]:
    if kind == "workstream":
        metadata = _store().json.loads(str(row["metadata_json"] or "{}"))
        return {
            "kind": "workstream",
            "entity_id": str(row["idea_id"]),
            "title": str(row["title"]),
            "status": str(row["status"]),
            "path": str(row["source_path"]),
            "section": str(row["section"]),
            "priority": str(row["priority"]),
            "promoted_to_plan": str(row["promoted_to_plan"]),
            "idea_file": str(row["idea_file"]),
            "metadata": metadata if isinstance(metadata, _store().Mapping) else {},
        }
    if kind == "plan":
        return {
            "kind": "plan",
            "entity_id": str(row["plan_path"]),
            "title": _store().Path(str(row["plan_path"])).name,
            "status": str(row["status"]),
            "path": str(row["source_path"]),
            "section": str(row["section"]),
            "created": str(row["created"]),
            "updated": str(row["updated"]),
            "backlog": str(row["backlog"]),
        }
    if kind == "release":
        metadata = _store().json.loads(str(row["metadata_json"] or "{}"))
        return {
            "kind": "release",
            "entity_id": str(row["release_id"]),
            "title": str(row["display_label"] or row["release_id"]),
            "status": str(row["status"]),
            "path": str(row["source_path"]),
            "version": str(row.get("version", "")),
            "tag": str(row.get("tag", "")),
            "effective_name": str(row.get("effective_name", "")),
            "aliases": _store()._json_list(str(row.get("aliases_json", ""))),
            "active_workstreams": _store()._json_list(str(row.get("active_workstreams_json", ""))),
            "metadata": metadata if isinstance(metadata, _store().Mapping) else {},
        }
    if kind == "bug":
        bug_id = str(row.get("bug_id", "")).strip()
        bug_key = str(row["bug_key"])
        return {
            "kind": "bug",
            "entity_id": bug_id or bug_key,
            "bug_id": bug_id,
            "bug_key": bug_key,
            "title": str(row["title"]),
            "status": str(row["status"]),
            "path": str(row["link_target"] or row["source_path"]),
            "date": str(row["date"]),
            "severity": str(row["severity"]),
            "components": _store()._parse_component_tokens(str(row["components"])),
        }
    if kind == "diagram":
        metadata = _store().json.loads(str(row["metadata_json"] or "{}"))
        return {
            "kind": "diagram",
            "entity_id": str(row["diagram_id"]),
            "title": str(row["title"]),
            "status": str(row["status"]),
            "path": str(row["source_mmd"]),
            "slug": str(row["slug"]),
            "owner": str(row["owner"]),
            "summary": str(row["summary"]),
            "metadata": metadata if isinstance(metadata, _store().Mapping) else {},
        }
    if kind == "component":
        metadata = _store().json.loads(str(row["metadata_json"] or "{}"))
        return {
            "kind": "component",
            "entity_id": str(row["component_id"]),
            "title": str(row["name"]),
            "status": str(row["status"]),
            "path": str(row["spec_ref"]),
            "owner": str(row["owner"]),
            "aliases": _store()._json_list(str(row["aliases_json"])),
            "workstreams": _store()._json_list(str(row["workstreams_json"])),
            "diagrams": _store()._json_list(str(row["diagrams_json"])),
            "metadata": metadata if isinstance(metadata, _store().Mapping) else {},
        }
    if kind in _store()._ENGINEERING_NOTE_KIND_SET:
        metadata = _store().json.loads(str(row["metadata_json"] or "{}"))
        return {
            "kind": kind,
            "entity_id": str(row["note_id"]),
            "title": str(row["title"]),
            "status": str(row["status"]),
            "path": str(row["source_path"]),
            "owner": str(row["owner"]),
            "section": str(row["section"]),
            "summary": str(row["summary"]),
            "components": _store()._json_list(str(row["components_json"])),
            "workstreams": _store()._json_list(str(row["workstreams_json"])),
            "path_refs": _store()._json_list(str(row["path_refs_json"])),
            "metadata": metadata if isinstance(metadata, _store().Mapping) else {},
        }
    if kind == "test":
        metadata = _store().json.loads(str(row["metadata_json"] or "{}"))
        return {
            "kind": "test",
            "entity_id": str(row["test_id"]),
            "title": str(row["test_name"]),
            "status": "",
            "path": str(row["test_path"]),
            "node_id": str(row["node_id"]),
            "markers": _store()._json_list(str(row["markers_json"])),
            "target_paths": _store()._json_list(str(row["target_paths_json"])),
            "metadata": metadata if isinstance(metadata, _store().Mapping) else {},
        }
    raise ValueError(f"unsupported entity kind: {kind}")

def _entity_by_kind_id(
    connection: Any,
    *,
    kind: str,
    entity_id: str,
) -> dict[str, Any] | None:
    normalized_kind = _store()._normalize_entity_kind(kind)
    token = str(entity_id or "").strip()
    if normalized_kind == "workstream":
        row = connection.execute("SELECT * FROM workstreams WHERE idea_id = ?", (token.upper(),)).fetchone()
    elif normalized_kind == "release":
        selector = release_planning_contract.normalize_release_selector(token)
        selector_key = str(selector or "").strip().casefold()
        row = None
        if selector_key:
            matches: list[Mapping[str, Any]] = []
            for candidate in connection.execute("SELECT * FROM releases").fetchall():
                aliases = {item.casefold() for item in _store()._json_list(str(candidate.get("aliases_json", "")))}
                candidate_keys = {
                    str(candidate.get("release_id", "")).strip().casefold(),
                    str(candidate.get("version", "")).strip().casefold(),
                    str(candidate.get("tag", "")).strip().casefold(),
                    str(candidate.get("effective_name", "")).strip().casefold(),
                }
                if selector_key.startswith("release:"):
                    candidate_keys.add(selector_key.partition(":")[2])
                if selector_key in aliases or selector_key in candidate_keys:
                    matches.append(candidate)
            if len(matches) == 1:
                row = matches[0]
    elif normalized_kind == "plan":
        row = connection.execute("SELECT * FROM plans WHERE plan_path = ?", (token,)).fetchone()
    elif normalized_kind == "bug":
        row = connection.execute("SELECT * FROM bugs WHERE bug_id = ? OR bug_key = ? LIMIT 1", (token, token)).fetchone()
    elif normalized_kind == "diagram":
        row = connection.execute("SELECT * FROM diagrams WHERE diagram_id = ?", (token.upper(),)).fetchone()
    elif normalized_kind == "component":
        row = connection.execute("SELECT * FROM components WHERE component_id = ?", (token,)).fetchone()
    elif normalized_kind in _store()._ENGINEERING_NOTE_KIND_SET:
        row = connection.execute(
            "SELECT * FROM engineering_notes WHERE note_kind = ? AND note_id = ?",
            (normalized_kind, token),
        ).fetchone()
    elif normalized_kind == "test":
        row = connection.execute("SELECT * FROM test_cases WHERE test_id = ?", (token,)).fetchone()
    else:
        row = None
    if row is None:
        return None
    return _entity_from_row(kind=normalized_kind, row=row)


def _existing_repo_local_file(
    *,
    repo_root: Path,
    path_ref: str,
) -> str:
    normalized_path = _store()._normalize_repo_token(path_ref, repo_root=repo_root)
    if not normalized_path:
        return ""
    normalized_candidate = _store().Path(normalized_path)
    if normalized_candidate.is_absolute():
        return ""
    resolved = (repo_root / normalized_candidate).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError:
        return ""
    if not resolved.is_file():
        return ""
    return normalized_candidate.as_posix()


def _synthesized_local_path_entity(
    *,
    repo_root: Path,
    path_ref: str,
) -> dict[str, Any] | None:
    normalized_path = _existing_repo_local_file(repo_root=repo_root, path_ref=path_ref)
    if not normalized_path:
        return None
    lower_path = normalized_path.lower()
    if lower_path.startswith("docs/runbooks/"):
        kind = "runbook"
    elif lower_path.endswith((".py", ".js", ".ts", ".tsx", ".jsx", ".sh", ".css", ".html", ".jinja", ".j2")) or lower_path.startswith(
        ("src/", "bin/", "tests/", "app/", "services/", "infra/", "configs/", "docker/", "policies/")
    ):
        kind = "code"
    else:
        kind = "doc"
    return {
        "kind": kind,
        "entity_id": normalized_path,
        "title": _store().Path(normalized_path).name,
        "status": "",
        "path": normalized_path,
    }


def _entity_kind_matches(entity: Mapping[str, Any] | None, *, expected_kind: str) -> bool:
    if not isinstance(entity, _store().Mapping):
        return False
    return str(entity.get("kind", "")).strip() == str(expected_kind).strip()


def _entity_by_path(
    connection: Any,
    *,
    repo_root: Path,
    path_ref: str,
) -> dict[str, Any] | None:
    normalized_path = _existing_repo_local_file(repo_root=repo_root, path_ref=path_ref)
    if not normalized_path:
        return None
    for candidate in connection.execute("SELECT * FROM workstreams").fetchall():
        if normalized_path in {
            _store()._normalize_repo_token(str(candidate["source_path"]), repo_root=repo_root),
            _store()._normalize_repo_token(str(candidate["idea_file"]), repo_root=repo_root),
        }:
            return _entity_from_row(kind="workstream", row=candidate)
    for entity_kind, query in (
        ("plan", "SELECT * FROM plans"),
        ("bug", "SELECT * FROM bugs"),
        ("diagram", "SELECT * FROM diagrams"),
        ("component", "SELECT * FROM components"),
        ("test", "SELECT * FROM test_cases"),
    ):
        for candidate in connection.execute(query).fetchall():
            candidate_paths = set()
            if entity_kind == "plan":
                candidate_paths.add(_store()._normalize_repo_token(str(candidate["plan_path"]), repo_root=repo_root))
                candidate_paths.add(_store()._normalize_repo_token(str(candidate["source_path"]), repo_root=repo_root))
            elif entity_kind == "bug":
                candidate_paths.add(_store()._normalize_repo_token(str(candidate["link_target"]), repo_root=repo_root))
                candidate_paths.add(_store()._normalize_repo_token(str(candidate["source_path"]), repo_root=repo_root))
            elif entity_kind == "diagram":
                candidate_paths.update(
                    {
                        _store()._normalize_repo_token(str(candidate["source_mmd"]), repo_root=repo_root),
                        _store()._normalize_repo_token(str(candidate["source_svg"]), repo_root=repo_root),
                        _store()._normalize_repo_token(str(candidate["source_png"]), repo_root=repo_root),
                    }
                )
            elif entity_kind == "component":
                candidate_paths.add(_store()._normalize_repo_token(str(candidate["spec_ref"]), repo_root=repo_root))
            elif entity_kind == "test":
                candidate_paths.add(_store()._normalize_repo_token(str(candidate["test_path"]), repo_root=repo_root))
            if normalized_path in candidate_paths:
                return _entity_from_row(kind=entity_kind, row=candidate)
    note = connection.execute("SELECT * FROM engineering_notes WHERE source_path = ? LIMIT 1", (normalized_path,)).fetchone()
    if note is not None:
        return _entity_from_row(kind=str(note["note_kind"]), row=note)
    edge = connection.execute(
        """
        SELECT target_kind, target_id
        FROM traceability_edges
        WHERE target_kind IN ('runbook', 'doc', 'code')
          AND target_id = ?
        LIMIT 1
        """,
        (normalized_path,),
    ).fetchone()
    if edge is not None:
        target_kind = str(edge["target_kind"])
        return {
            "kind": target_kind,
            "entity_id": normalized_path,
            "title": _store().Path(normalized_path).name,
            "status": "",
            "path": normalized_path,
        }
    return _synthesized_local_path_entity(repo_root=repo_root, path_ref=normalized_path)

def _unique_entity_by_path_alias(
    connection: Any,
    *,
    repo_root: Path,
    ref: str,
) -> tuple[dict[str, Any] | None, str]:
    raw_ref = str(ref or "").strip()
    if not raw_ref or "/" in raw_ref:
        return None, ""
    alias = _store().Path(raw_ref).name
    if not alias or "." not in alias:
        return None, ""
    alias_casefold = alias.casefold()
    matches: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    def _path_matches(path_ref: str) -> bool:
        normalized_path = _store()._normalize_repo_token(path_ref, repo_root=repo_root)
        return bool(normalized_path) and _store().Path(normalized_path).name.casefold() == alias_casefold

    def _add(entity: Mapping[str, Any] | None) -> None:
        if not isinstance(entity, _store().Mapping):
            return
        row = _store()._search_row_from_entity(entity)
        key = (row["kind"], row["entity_id"], row["path"])
        if key in seen:
            return
        seen.add(key)
        matches.append(dict(entity))

    for candidate in connection.execute("SELECT * FROM workstreams").fetchall():
        for path_ref in (str(candidate["source_path"]), str(candidate["idea_file"])):
            if _path_matches(path_ref):
                _add(_entity_from_row(kind="workstream", row=candidate))
    for candidate in connection.execute("SELECT * FROM plans").fetchall():
        for path_ref in (str(candidate["plan_path"]), str(candidate["source_path"])):
            if _path_matches(path_ref):
                _add(_entity_from_row(kind="plan", row=candidate))
    for candidate in connection.execute("SELECT * FROM bugs").fetchall():
        for path_ref in (str(candidate["link_target"]), str(candidate["source_path"])):
            if _path_matches(path_ref):
                _add(_entity_from_row(kind="bug", row=candidate))
    for candidate in connection.execute("SELECT * FROM diagrams").fetchall():
        for path_ref in (str(candidate["source_mmd"]), str(candidate["source_svg"]), str(candidate["source_png"])):
            if _path_matches(path_ref):
                _add(_entity_from_row(kind="diagram", row=candidate))
    for candidate in connection.execute("SELECT * FROM components").fetchall():
        if _path_matches(str(candidate["spec_ref"])):
            _add(_entity_from_row(kind="component", row=candidate))
    for candidate in connection.execute("SELECT * FROM test_cases").fetchall():
        if _path_matches(str(candidate["test_path"])):
            _add(_entity_from_row(kind="test", row=candidate))
    for candidate in connection.execute("SELECT * FROM engineering_notes").fetchall():
        if _path_matches(str(candidate["source_path"])):
            _add(_entity_from_row(kind=str(candidate["note_kind"]), row=candidate))
    for edge in connection.execute(
        """
        SELECT target_kind, target_id
        FROM traceability_edges
        WHERE target_kind IN ('runbook', 'doc', 'code')
        """
    ).fetchall():
        target_kind = str(edge["target_kind"]).strip()
        target_id = str(edge["target_id"]).strip()
        if not target_kind or not _path_matches(target_id):
            continue
        _add(
            {
                "kind": target_kind,
                "entity_id": target_id,
                "title": _store().Path(target_id).name,
                "status": "",
                "path": target_id,
            }
        )
    if len(matches) == 1:
        return matches[0], "path_alias_basename"
    return None, ""

def _projection_exact_search_results(
    connection: Any,
    *,
    repo_root: Path,
    query: str,
    kinds: Sequence[str],
    limit: int,
) -> list[dict[str, Any]]:
    raw_query = str(query or "").strip()
    if not raw_query:
        return []
    normalized_query = _store()._normalize_repo_token(raw_query, repo_root=repo_root)
    lowered = raw_query.casefold()
    compact_lookup = _store()._context_lookup_key(raw_query)
    allowed = {str(kind).strip().lower() for kind in kinds if str(kind).strip()}
    candidate_kinds = tuple(allowed) if allowed else (
        "workstream",
        "release",
        "plan",
        "bug",
        "diagram",
        "component",
        *_store()._ENGINEERING_NOTE_KINDS,
        "test",
    )
    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    def _add(entity: Mapping[str, Any] | None) -> None:
        if not isinstance(entity, _store().Mapping):
            return
        row = _store()._search_row_from_entity(entity)
        key = (row["kind"], row["entity_id"], row["path"])
        if not row["kind"] or (allowed and row["kind"] not in allowed) or key in seen:
            return
        seen.add(key)
        results.append(row)

    if normalized_query:
        _add(_entity_by_path(connection, repo_root=repo_root, path_ref=normalized_query))

    for entity_kind in candidate_kinds:
        _add(_entity_by_kind_id(connection, kind=entity_kind, entity_id=raw_query))
        if entity_kind in {"workstream", "diagram"}:
            _add(_entity_by_kind_id(connection, kind=entity_kind, entity_id=raw_query.upper()))
        if normalized_query and normalized_query != raw_query:
            _add(_entity_by_kind_id(connection, kind=entity_kind, entity_id=normalized_query))
        if len(results) >= max(1, int(limit)):
            return results[: max(1, int(limit))]

    for row in connection.execute("SELECT * FROM workstreams").fetchall():
        aliases = _store()._workstream_lookup_aliases(dict(row), repo_root=repo_root)
        if lowered in aliases or (compact_lookup and compact_lookup in aliases):
            _add(_entity_from_row(kind="workstream", row=row))
            break

    for row in connection.execute("SELECT * FROM plans").fetchall():
        aliases = _store()._plan_lookup_aliases(dict(row), repo_root=repo_root)
        if lowered in aliases or (compact_lookup and compact_lookup in aliases):
            _add(_entity_from_row(kind="plan", row=row))
            break

    for row in connection.execute("SELECT * FROM components").fetchall():
        aliases = _store()._component_lookup_aliases(dict(row), repo_root=repo_root)
        if lowered in aliases or (compact_lookup and compact_lookup in aliases):
            _add(_entity_from_row(kind="component", row=row))
            break

    if results:
        return results[: max(1, int(limit))]

    title_queries: tuple[tuple[str, str, str], ...] = (
        ("workstream", "SELECT * FROM workstreams WHERE lower(title) = ? LIMIT 1", lowered),
        ("bug", "SELECT * FROM bugs WHERE lower(title) = ? LIMIT 1", lowered),
        ("diagram", "SELECT * FROM diagrams WHERE lower(title) = ? LIMIT 1", lowered),
        ("component", "SELECT * FROM components WHERE lower(name) = ? LIMIT 1", lowered),
        ("test", "SELECT * FROM test_cases WHERE lower(test_name) = ? LIMIT 1", lowered),
    )
    for entity_kind, sql, token in title_queries:
        if allowed and entity_kind not in allowed:
            continue
        row = connection.execute(sql, (token,)).fetchone()
        if row is not None:
            _add(_entity_from_row(kind=entity_kind, row=row))
    if not allowed or any(kind in allowed for kind in _store()._ENGINEERING_NOTE_KIND_SET):
        for note_kind in _store()._ENGINEERING_NOTE_KINDS:
            if allowed and note_kind not in allowed:
                continue
            row = connection.execute(
                "SELECT * FROM engineering_notes WHERE note_kind = ? AND lower(title) = ? LIMIT 1",
                (note_kind, lowered),
            ).fetchone()
            if row is not None:
                _add(_entity_from_row(kind=note_kind, row=row))
    return results[: max(1, int(limit))]

def _repo_scan_candidate_search_results(
    connection: Any,
    *,
    repo_root: Path,
    fallback_scan: Mapping[str, Any],
    query: str,
    kinds: Sequence[str],
    limit: int,
) -> list[dict[str, Any]]:
    allowed = {str(kind).strip().lower() for kind in kinds if str(kind).strip()}
    lowered_query = str(query or "").strip().casefold()
    query_tokens = {token.casefold() for token in _store().re.findall(r"[A-Za-z0-9_./:-]+", str(query or "")) if token}
    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for rank, hit in enumerate(fallback_scan.get("results", []), start=1):
        if not isinstance(hit, _store().Mapping):
            continue
        path_ref = _store()._normalize_repo_token(str(hit.get("path", "")).strip(), repo_root=repo_root)
        if not path_ref:
            continue
        entity = _entity_by_path(connection, repo_root=repo_root, path_ref=path_ref)
        if entity is None:
            if bool(_store()._path_signal_profile(path_ref).get("shared")):
                continue
            inferred_kind = _store()._repo_scan_inferred_kind(path_ref)
            if not inferred_kind:
                continue
            entity = {
                "kind": inferred_kind,
                "entity_id": path_ref,
                "title": _store().Path(path_ref).name,
                "path": path_ref,
            }
        title = str(entity.get("title", "")).strip().casefold()
        entity_id = str(entity.get("entity_id", "")).strip().casefold()
        path_text = str(entity.get("path", "")).strip().casefold()
        lexical_bonus = 0.0
        if lowered_query and any(lowered_query in text for text in (title, entity_id, path_text) if text):
            lexical_bonus += 24.0
        if query_tokens:
            lexical_bonus += float(
                sum(
                    1
                    for token in query_tokens
                    if token and any(token in text for text in (title, entity_id, path_text) if text)
                )
            ) * 4.0
        row = _store()._search_row_from_entity(
            entity,
            score=float(max(1, int(limit) * 3) - rank + 1) + lexical_bonus,
        )
        key = (row["kind"], row["entity_id"], row["path"])
        if not row["kind"] or (allowed and row["kind"] not in allowed) or key in seen:
            continue
        seen.add(key)
        results.append(row)
    results.sort(
        key=lambda row: (
            -float(row.get("score", 0.0) or 0.0),
            str(row.get("path", "")),
            str(row.get("entity_id", "")),
        )
    )
    return results[: max(1, int(limit))]

def _resolve_context_entity(
    connection: Any,
    *,
    repo_root: Path,
    ref: str,
    kind: str | None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], dict[str, Any]]:
    normalized_kind = _store()._normalize_entity_kind(kind)
    raw_ref = str(ref or "").strip()
    if not raw_ref:
        return None, [], {"resolution_mode": "none"}
    normalized_ref = _store()._normalize_repo_token(raw_ref, repo_root=repo_root)
    exact_repo_local_path = _existing_repo_local_file(repo_root=repo_root, path_ref=raw_ref)

    def _fetch_by_id(entity_kind: str, entity_id: str) -> dict[str, Any] | None:
        return _entity_by_kind_id(connection, kind=entity_kind, entity_id=entity_id)

    def _fetch_by_path(path_ref: str) -> dict[str, Any] | None:
        return _entity_by_path(connection, repo_root=repo_root, path_ref=path_ref)

    if normalized_kind in {
        "workstream",
        "plan",
        "bug",
        "diagram",
        "component",
        *_store()._ENGINEERING_NOTE_KIND_SET,
        "test",
    }:
        entity = _fetch_by_id(normalized_kind, raw_ref if normalized_kind != "workstream" else raw_ref.upper())
        if entity is None and normalized_ref and normalized_ref != raw_ref:
            entity = _fetch_by_id(normalized_kind, normalized_ref)
        if entity is None and normalized_ref:
            candidate = _fetch_by_path(normalized_ref)
            if _entity_kind_matches(candidate, expected_kind=normalized_kind):
                entity = candidate
        return entity, [], {"resolution_mode": "kind_exact" if entity is not None else "none"}

    if normalized_kind in {"doc", "runbook", "code"}:
        path_ref = exact_repo_local_path or normalized_ref or raw_ref
        entity = _fetch_by_path(path_ref)
        if not _entity_kind_matches(entity, expected_kind=normalized_kind):
            entity = None
        return entity, [], {"resolution_mode": "path_exact" if entity is not None else "none"}

    if _store()._WORKSTREAM_ID_RE.fullmatch(raw_ref.upper()):
        entity = _fetch_by_id("workstream", raw_ref.upper())
        if entity is not None:
            return entity, [], {"resolution_mode": "workstream_id"}
    if _store()._DIAGRAM_ID_RE.fullmatch(raw_ref.upper()):
        entity = _fetch_by_id("diagram", raw_ref.upper())
        if entity is not None:
            return entity, [], {"resolution_mode": "diagram_id"}
    if exact_repo_local_path:
        entity = _fetch_by_path(exact_repo_local_path)
        if entity is not None:
            return entity, [], {"resolution_mode": "path_exact"}
    if "/" in raw_ref or raw_ref.endswith((".md", ".json", ".py", ".mmd", ".svg", ".png")):
        entity = _fetch_by_path(normalized_ref or raw_ref)
        if entity is not None:
            return entity, [], {"resolution_mode": "path_exact"}
    entity, path_alias_mode = _unique_entity_by_path_alias(
        connection,
        repo_root=repo_root,
        ref=raw_ref,
    )
    if entity is not None:
        return entity, [], {"resolution_mode": path_alias_mode}

    lowered = raw_ref.casefold()
    compact_lookup = _store()._context_lookup_key(raw_ref)
    for row in connection.execute("SELECT * FROM releases").fetchall():
        aliases = _store()._release_lookup_aliases(dict(row), repo_root=repo_root)
        if lowered in aliases or (compact_lookup and compact_lookup in aliases):
            return _entity_from_row(kind="release", row=row), [], {"resolution_mode": "release_alias"}

    for row in connection.execute("SELECT * FROM workstreams").fetchall():
        aliases = _store()._workstream_lookup_aliases(dict(row), repo_root=repo_root)
        if lowered in aliases or (compact_lookup and compact_lookup in aliases):
            return _entity_from_row(kind="workstream", row=row), [], {"resolution_mode": "workstream_alias"}

    component_rows = connection.execute("SELECT * FROM components").fetchall()
    for row in component_rows:
        aliases = _store()._component_lookup_aliases(dict(row), repo_root=repo_root)
        if lowered in aliases or (compact_lookup and compact_lookup in aliases):
            return _entity_from_row(kind="component", row=row), [], {"resolution_mode": "component_alias"}

    for row in connection.execute("SELECT * FROM plans").fetchall():
        aliases = _store()._plan_lookup_aliases(dict(row), repo_root=repo_root)
        if lowered in aliases or (compact_lookup and compact_lookup in aliases):
            return _entity_from_row(kind="plan", row=row), [], {"resolution_mode": "plan_alias"}

    search_payload = _store().search_entities_payload(repo_root=repo_root, query=raw_ref, limit=5, runtime_mode="auto")
    matches = [dict(row) for row in search_payload.get("results", []) if isinstance(row, _store().Mapping)]
    retrieval_mode = str(search_payload.get("retrieval_mode", "")).strip()
    if matches and retrieval_mode == "exact":
        top = matches[0]
        entity = _fetch_by_id(str(top["kind"]), str(top["entity_id"]))
        if entity is not None:
            return entity, matches, {
                "resolution_mode": "runtime_exact_match",
                "retrieval_mode": retrieval_mode,
                "runtime_ready": bool(search_payload.get("runtime_ready")),
            }
    return None, matches, {
        "resolution_mode": (
            "runtime_sparse_candidate_only"
            if matches and retrieval_mode in {"tantivy_sparse", "hybrid_local", "tantivy_plus_vespa", "vespa_remote"}
            else "repo_scan_candidate_only"
            if matches and retrieval_mode == "full_repo_scan"
            else "candidate_only"
            if matches
            else "none"
        ),
        "retrieval_mode": retrieval_mode,
        "runtime_ready": bool(search_payload.get("runtime_ready")),
        "full_scan_recommended": bool(search_payload.get("full_scan_recommended")),
        "full_scan_reason": str(search_payload.get("full_scan_reason", "")).strip(),
        "fallback_scan": dict(search_payload.get("fallback_scan", {}))
        if isinstance(search_payload.get("fallback_scan"), _store().Mapping)
        else {},
    }

def _relation_rows(
    connection: Any,
    *,
    entity: Mapping[str, Any],
    relation_limit: int,
) -> list[dict[str, Any]]:
    kind = str(entity.get("kind", "")).strip()
    entity_id = str(entity.get("entity_id", "")).strip()
    if not kind or not entity_id:
        return []
    rows = connection.execute(
        """
        SELECT source_kind, source_id, relation, target_kind, target_id, source_path
        FROM traceability_edges
        WHERE (source_kind = ? AND source_id = ?)
           OR (target_kind = ? AND target_id = ?)
        ORDER BY relation, source_kind, source_id, target_kind, target_id
        LIMIT ?
        """,
        (kind, entity_id, kind, entity_id, max(1, int(relation_limit))),
    ).fetchall()
    return [
        {
            "direction": "outgoing"
            if str(row["source_kind"]) == kind and str(row["source_id"]) == entity_id
            else "incoming",
            "source_kind": str(row["source_kind"]),
            "source_id": str(row["source_id"]),
            "relation": str(row["relation"]),
            "target_kind": str(row["target_kind"]),
            "target_id": str(row["target_id"]),
            "source_path": str(row["source_path"]),
        }
        for row in rows
    ]

def _related_entities(
    connection: Any,
    *,
    entity: Mapping[str, Any],
    relations: Sequence[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    related: dict[str, dict[str, dict[str, Any]]] = {}

    def _add(summary: dict[str, Any]) -> None:
        kind = str(summary.get("kind", "")).strip()
        entity_id = str(summary.get("entity_id", "")).strip()
        if not kind or not entity_id:
            return
        related.setdefault(kind, {})[entity_id] = summary

    def _add_kind_id(kind: str, entity_id: str) -> None:
        resolved = _entity_by_kind_id(connection, kind=kind, entity_id=entity_id)
        if resolved is not None:
            _add(_store()._summarize_entity(resolved))
            return
        if kind in {"doc", "runbook", "code"}:
            _add(
                {
                    "kind": kind,
                    "entity_id": entity_id,
                    "title": _store().Path(entity_id).name,
                    "path": entity_id,
                    "status": "",
                }
            )

    for row in relations:
        direction = str(row.get("direction", "")).strip()
        if direction == "outgoing":
            _add_kind_id(str(row.get("target_kind", "")), str(row.get("target_id", "")))
        else:
            _add_kind_id(str(row.get("source_kind", "")), str(row.get("source_id", "")))

    kind = str(entity.get("kind", "")).strip()
    if kind == "workstream":
        workstream_id = str(entity.get("entity_id", "")).strip()
        promoted_to_plan = str(entity.get("promoted_to_plan", "")).strip()
        if promoted_to_plan:
            _add_kind_id("plan", promoted_to_plan)
        for row in connection.execute("SELECT * FROM components").fetchall():
            if workstream_id in set(_store()._json_list(str(row["workstreams_json"]))):
                _add(_store()._summarize_entity(_entity_from_row(kind="component", row=row)))
    elif kind == "component":
        for workstream_id in entity.get("workstreams", []) if isinstance(entity.get("workstreams"), list) else []:
            _add_kind_id("workstream", str(workstream_id))
        for diagram_id in entity.get("diagrams", []) if isinstance(entity.get("diagrams"), list) else []:
            _add_kind_id("diagram", str(diagram_id))
    elif kind == "diagram":
        diagram_id = str(entity.get("entity_id", "")).strip()
        for row in connection.execute("SELECT * FROM components").fetchall():
            if diagram_id in set(_store()._json_list(str(row["diagrams_json"]))):
                _add(_store()._summarize_entity(_entity_from_row(kind="component", row=row)))
    elif kind == "plan":
        backlog = str(entity.get("backlog", "")).strip().strip("`")
        if _store()._WORKSTREAM_ID_RE.fullmatch(backlog):
            _add_kind_id("workstream", backlog)
    elif kind == "bug":
        for component_id in entity.get("components", []) if isinstance(entity.get("components"), list) else []:
            _add_kind_id("component", component_id.lower())

    return {
        kind_name: [bucket[key] for key in sorted(bucket)]
        for kind_name, bucket in sorted(related.items())
    }

def _recent_context_events(
    connection: Any,
    *,
    entity: Mapping[str, Any],
    related: Mapping[str, Sequence[Mapping[str, Any]]],
    event_limit: int,
) -> list[dict[str, Any]]:
    workstream_ids: set[str] = set()
    component_ids: set[str] = set()
    artifact_paths: set[str] = set()
    kind = str(entity.get("kind", "")).strip()
    entity_id = str(entity.get("entity_id", "")).strip()
    path = str(entity.get("path", "")).strip()
    if kind == "workstream":
        workstream_ids.add(entity_id)
    elif kind == "component":
        component_ids.add(entity_id)
    elif kind in {"plan", "diagram", "doc", "runbook", "code"} and path:
        artifact_paths.add(path)
    for row in related.get("workstream", []):
        workstream_ids.add(str(row.get("entity_id", "")).strip())
    for row in related.get("component", []):
        component_ids.add(str(row.get("entity_id", "")).strip())
    for bucket in related.values():
        for row in bucket:
            related_path = str(row.get("path", "")).strip()
            if related_path:
                artifact_paths.add(related_path)

    rows = connection.execute(
        """
        SELECT event_id, ts_iso, kind, summary, workstreams_json, artifacts_json, components_json, metadata_json
        FROM codex_events
        ORDER BY ts_iso DESC, event_id DESC
        """
    ).fetchall()
    results: list[dict[str, Any]] = []
    normalized_paths = {_store().Path(item).as_posix() for item in artifact_paths if item}
    for row in rows:
        event_workstreams = set(_store()._json_list(str(row["workstreams_json"])))
        event_components = set(_store()._json_list(str(row["components_json"])))
        event_artifacts = {_store().Path(item).as_posix() for item in _store()._json_list(str(row["artifacts_json"]))}
        if not (
            event_workstreams.intersection(workstream_ids)
            or event_components.intersection(component_ids)
            or event_artifacts.intersection(normalized_paths)
        ):
            continue
        metadata = _store().json.loads(str(row["metadata_json"] or "{}"))
        results.append(
            {
                "event_id": str(row["event_id"]),
                "ts_iso": str(row["ts_iso"]),
                "kind": str(row["kind"]),
                "summary": str(row["summary"]),
                "workstreams": sorted(event_workstreams),
                "components": sorted(event_components),
                "artifacts": sorted(event_artifacts),
                "metadata": metadata if isinstance(metadata, _store().Mapping) else {},
            }
        )
        if len(results) >= max(1, int(event_limit)):
            break
    return results

def _delivery_context_rows(
    connection: Any,
    *,
    entity: Mapping[str, Any],
    related: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    candidates: set[tuple[str, str]] = set()
    kind = str(entity.get("kind", "")).strip()
    entity_id = str(entity.get("entity_id", "")).strip()
    if kind in {"workstream", "component", "diagram"} and entity_id:
        candidates.add((kind, entity_id))
    for related_kind in ("workstream", "component", "diagram"):
        for row in related.get(related_kind, []):
            candidate_id = str(row.get("entity_id", "")).strip()
            if candidate_id:
                candidates.add((related_kind, candidate_id))
    rows: list[dict[str, Any]] = []
    for scope_type, scope_id in sorted(candidates):
        payload = connection.execute(
            "SELECT payload_json FROM delivery_scopes WHERE scope_type = ? AND scope_id = ?",
            (scope_type, scope_id),
        ).fetchone()
        if payload is None:
            continue
        decoded = _store().json.loads(str(payload["payload_json"]))
        if isinstance(decoded, _store().Mapping):
            rows.append(dict(decoded))
    return rows

def load_context_dossier(
    *,
    repo_root: Path,
    ref: str,
    kind: str | None = None,
    runtime_mode: str = "auto",
    event_limit: int = 8,
    relation_limit: int = 32,
) -> dict[str, Any]:
    """Resolve one entity or path into a deterministic repo-grounded context dossier."""

    root = _store().Path(repo_root).resolve()
    started_at = _store().time.perf_counter()
    runtime_ready = _warm_runtime(repo_root=root, runtime_mode=runtime_mode, reason="context", scope="reasoning")
    if not runtime_ready:
        fallback_scan = _store()._full_scan_guidance(
            repo_root=root,
            reason="runtime_unavailable",
            query=str(ref or "").strip(),
            perform_scan=True,
            result_limit=max(3, min(8, int(relation_limit))),
        )
        return {
            "query": str(ref or "").strip(),
            "requested_kind": _store()._normalize_entity_kind(kind),
            "resolved": False,
            "matches": [],
            "lookup": {
                "resolution_mode": "runtime_unavailable",
                "runtime_ready": False,
            },
            "full_scan_recommended": True,
            "full_scan_reason": "runtime_unavailable",
            "fallback_scan": fallback_scan,
        }
    connection = _connect(root)
    try:
        entity, matches, lookup = _resolve_context_entity(
            connection,
            repo_root=root,
            ref=ref,
            kind=kind,
        )
        odylith_ablation_active = _odylith_ablation_active(repo_root=root)
        if odylith_ablation_active:
            matches = [
                dict(row)
                for row in matches
                if isinstance(row, _store().Mapping) and not _store()._odylith_runtime_entity_suppressed(repo_root=root, entity=row)
            ]
            if isinstance(entity, _store().Mapping) and _store()._odylith_runtime_entity_suppressed(repo_root=root, entity=entity):
                entity = None
                lookup = {
                    **dict(lookup),
                    "resolution_mode": "odylith_disabled",
                    "runtime_ready": True,
                    "odylith_switch": _store()._odylith_switch_snapshot(repo_root=root),
                }
            if entity is None and _store()._odylith_query_targets_disabled(repo_root=root, query=str(ref or "").strip()):
                return {
                    "query": str(ref or "").strip(),
                    "requested_kind": _store()._normalize_entity_kind(kind),
                    "resolved": False,
                    "matches": [],
                    "lookup": dict(lookup),
                    "full_scan_recommended": False,
                    "full_scan_reason": "odylith_disabled",
                    "fallback_scan": {
                        "performed": False,
                        "terms": _store()._full_scan_terms(repo_root=root, query=str(ref or "").strip()),
                        "roots": _store()._available_full_scan_roots(repo_root=root),
                        "commands": [],
                        "results": [],
                        "reason": "odylith_disabled",
                        "reason_message": "Odylith is disabled for ablation; its platform component is intentionally suppressed.",
                        "changed_paths": [],
                    },
                }
        if entity is None:
            full_scan_reason = str(lookup.get("full_scan_reason", "")).strip() or (
                "context_requires_exact_resolution" if matches else "no_runtime_results"
            )
            fallback_scan = (
                dict(lookup.get("fallback_scan", {}))
                if isinstance(lookup.get("fallback_scan"), _store().Mapping)
                else _store()._full_scan_guidance(
                    repo_root=root,
                    reason=full_scan_reason,
                    query=str(ref or "").strip(),
                    perform_scan=True,
                    result_limit=max(3, min(8, int(relation_limit))),
                )
            )
            return {
                "query": str(ref or "").strip(),
                "requested_kind": _store()._normalize_entity_kind(kind),
                "resolved": False,
                "matches": matches,
                "lookup": dict(lookup),
                "full_scan_recommended": True,
                "full_scan_reason": full_scan_reason,
                "fallback_scan": fallback_scan,
            }
        relations = _relation_rows(connection, entity=entity, relation_limit=relation_limit)
        related = _related_entities(connection, entity=entity, relations=relations)
        delivery_scopes = _delivery_context_rows(
            connection,
            entity=entity,
            related=related,
        )
        from odylith.runtime.governance import proof_state as proof_state_runtime

        return {
            **proof_state_runtime.resolve_scope_collection_proof_state(delivery_scopes),
            "query": str(ref or "").strip(),
            "requested_kind": _store()._normalize_entity_kind(kind),
            "resolved": True,
            "entity": entity,
            "matches": matches,
            "lookup": dict(lookup),
            "full_scan_recommended": False,
            "full_scan_reason": "",
            "fallback_scan": {
                "performed": False,
                "terms": _store()._full_scan_terms(repo_root=root, query=str(ref or "").strip()),
                "roots": _store()._available_full_scan_roots(repo_root=root),
                "commands": [],
                "results": [],
                "reason": "",
                "reason_message": "",
                "changed_paths": [],
            },
            "relations": relations,
            "related_entities": related,
            agent_runtime_contract.AGENT_EVENT_KEY: _recent_context_events(
                connection,
                entity=entity,
                related=related,
                event_limit=event_limit,
            ),
            "delivery_scopes": delivery_scopes,
        }
    finally:
        connection.close()
        record_runtime_timing(
            repo_root=root,
            category="reasoning",
            operation="context",
            duration_ms=(_store().time.perf_counter() - started_at) * 1000.0,
            metadata={
                "query": str(ref or "").strip(),
                "requested_kind": _store()._normalize_entity_kind(kind),
            },
        )
