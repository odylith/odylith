from __future__ import annotations

from typing import Any

from odylith.runtime.common.casebook_bug_ids import BUG_ID_FIELD, resolve_casebook_bug_id
from odylith.runtime.context_engine import odylith_context_engine_registry_detail_runtime


def bind(host: Any) -> None:
    getter = host.__getitem__ if isinstance(host, dict) else lambda name: getattr(host, name)
    for name in ('Any', 'Mapping', 'Path', 'Sequence', '_BUG_CRITICAL_SEVERITIES', '_DIAGRAM_ID_RE', '_ENGINEERING_NOTE_KINDS', '_ENGINEERING_NOTE_KIND_SET', '_HEADER_RE', '_PROCESS_WARM_CACHE_FINGERPRINTS', '_WORKSTREAM_ID_RE', '_apply_odylith_component_index_ablation', '_apply_odylith_registry_snapshot_ablation', '_available_full_scan_roots', '_bug_agent_guidance', '_bug_archive_bucket_from_link_target', '_bug_intelligence_coverage', '_bug_is_open', '_bug_summary_from_fields', '_build_bug_reference_lookup', '_cached_projection_rows', '_classify_bug_path_refs', '_component_entry_from_runtime_row', '_component_lookup_aliases', '_component_matches_for_bug_paths', '_component_rows_from_index', '_connect', '_context_lookup_key', '_dedupe_strings', '_delivery_context_rows', '_diagram_refs_for_bug_components', '_entity_by_kind_id', '_entity_by_path', '_entity_from_row', '_extract_path_refs', '_extract_workstream_refs', '_full_scan_guidance', '_full_scan_terms', '_is_bug_placeholder_row', '_json_list', '_load_backlog_projection', '_load_bug_projection', '_load_diagram_projection', '_load_idea_specs', '_load_plan_projection', '_markdown_section_bodies', '_normalize_bug_link_target', '_normalize_entity_kind', '_normalize_repo_token', '_odylith_ablation_active', '_odylith_query_targets_disabled', '_odylith_runtime_entity_suppressed', '_odylith_switch_snapshot', '_ordered_bug_detail_sections', '_parse_bug_entry_fields', '_parse_component_tokens', '_parse_link_target', '_path_signal_profile', '_plan_lookup_aliases', '_raw_text', '_recent_context_events', '_related_bug_refs_from_text', '_related_entities', '_relation_rows', '_repo_scan_inferred_kind', '_resolve_context_entity', '_runtime_backlog_detail', '_runtime_backlog_detail_rows', '_search_row_from_entity', '_summarize_entity', '_unique_entity_by_path_alias', '_warm_runtime', '_workstream_lookup_aliases', 'canonicalize_bug_status', 'component_registry', 'entity', 'entity_id', 'entity_kind', 'json', 'load_backlog_detail', 'load_backlog_rows', 'load_bug_rows', 'load_component_index', 'load_component_registry_snapshot', 're', 'record_runtime_timing', 'search_entities_payload', 'summary', 'time'):
        try:
            globals()[name] = getter(name)
        except (AttributeError, KeyError):
            continue


def _entity_from_row(*, kind: str, row: Mapping[str, Any]) -> dict[str, Any]:
    if kind == "workstream":
        metadata = json.loads(str(row["metadata_json"] or "{}"))
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
            "metadata": metadata if isinstance(metadata, Mapping) else {},
        }
    if kind == "plan":
        return {
            "kind": "plan",
            "entity_id": str(row["plan_path"]),
            "title": Path(str(row["plan_path"])).name,
            "status": str(row["status"]),
            "path": str(row["source_path"]),
            "section": str(row["section"]),
            "created": str(row["created"]),
            "updated": str(row["updated"]),
            "backlog": str(row["backlog"]),
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
            "components": _parse_component_tokens(str(row["components"])),
        }
    if kind == "diagram":
        metadata = json.loads(str(row["metadata_json"] or "{}"))
        return {
            "kind": "diagram",
            "entity_id": str(row["diagram_id"]),
            "title": str(row["title"]),
            "status": str(row["status"]),
            "path": str(row["source_mmd"]),
            "slug": str(row["slug"]),
            "owner": str(row["owner"]),
            "summary": str(row["summary"]),
            "metadata": metadata if isinstance(metadata, Mapping) else {},
        }
    if kind == "component":
        metadata = json.loads(str(row["metadata_json"] or "{}"))
        return {
            "kind": "component",
            "entity_id": str(row["component_id"]),
            "title": str(row["name"]),
            "status": str(row["status"]),
            "path": str(row["spec_ref"]),
            "owner": str(row["owner"]),
            "aliases": _json_list(str(row["aliases_json"])),
            "workstreams": _json_list(str(row["workstreams_json"])),
            "diagrams": _json_list(str(row["diagrams_json"])),
            "metadata": metadata if isinstance(metadata, Mapping) else {},
        }
    if kind in _ENGINEERING_NOTE_KIND_SET:
        metadata = json.loads(str(row["metadata_json"] or "{}"))
        return {
            "kind": kind,
            "entity_id": str(row["note_id"]),
            "title": str(row["title"]),
            "status": str(row["status"]),
            "path": str(row["source_path"]),
            "owner": str(row["owner"]),
            "section": str(row["section"]),
            "summary": str(row["summary"]),
            "components": _json_list(str(row["components_json"])),
            "workstreams": _json_list(str(row["workstreams_json"])),
            "path_refs": _json_list(str(row["path_refs_json"])),
            "metadata": metadata if isinstance(metadata, Mapping) else {},
        }
    if kind == "test":
        metadata = json.loads(str(row["metadata_json"] or "{}"))
        return {
            "kind": "test",
            "entity_id": str(row["test_id"]),
            "title": str(row["test_name"]),
            "status": "",
            "path": str(row["test_path"]),
            "node_id": str(row["node_id"]),
            "markers": _json_list(str(row["markers_json"])),
            "target_paths": _json_list(str(row["target_paths_json"])),
            "metadata": metadata if isinstance(metadata, Mapping) else {},
        }
    raise ValueError(f"unsupported entity kind: {kind}")

def _entity_by_kind_id(
    connection: Any,
    *,
    kind: str,
    entity_id: str,
) -> dict[str, Any] | None:
    normalized_kind = _normalize_entity_kind(kind)
    token = str(entity_id or "").strip()
    if normalized_kind == "workstream":
        row = connection.execute("SELECT * FROM workstreams WHERE idea_id = ?", (token.upper(),)).fetchone()
    elif normalized_kind == "plan":
        row = connection.execute("SELECT * FROM plans WHERE plan_path = ?", (token,)).fetchone()
    elif normalized_kind == "bug":
        row = connection.execute("SELECT * FROM bugs WHERE bug_id = ? OR bug_key = ? LIMIT 1", (token, token)).fetchone()
    elif normalized_kind == "diagram":
        row = connection.execute("SELECT * FROM diagrams WHERE diagram_id = ?", (token.upper(),)).fetchone()
    elif normalized_kind == "component":
        row = connection.execute("SELECT * FROM components WHERE component_id = ?", (token,)).fetchone()
    elif normalized_kind in _ENGINEERING_NOTE_KIND_SET:
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
    normalized_path = _normalize_repo_token(path_ref, repo_root=repo_root)
    if not normalized_path:
        return ""
    normalized_candidate = Path(normalized_path)
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
        "title": Path(normalized_path).name,
        "status": "",
        "path": normalized_path,
    }


def _entity_kind_matches(entity: Mapping[str, Any] | None, *, expected_kind: str) -> bool:
    if not isinstance(entity, Mapping):
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
            _normalize_repo_token(str(candidate["source_path"]), repo_root=repo_root),
            _normalize_repo_token(str(candidate["idea_file"]), repo_root=repo_root),
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
                candidate_paths.add(_normalize_repo_token(str(candidate["plan_path"]), repo_root=repo_root))
                candidate_paths.add(_normalize_repo_token(str(candidate["source_path"]), repo_root=repo_root))
            elif entity_kind == "bug":
                candidate_paths.add(_normalize_repo_token(str(candidate["link_target"]), repo_root=repo_root))
                candidate_paths.add(_normalize_repo_token(str(candidate["source_path"]), repo_root=repo_root))
            elif entity_kind == "diagram":
                candidate_paths.update(
                    {
                        _normalize_repo_token(str(candidate["source_mmd"]), repo_root=repo_root),
                        _normalize_repo_token(str(candidate["source_svg"]), repo_root=repo_root),
                        _normalize_repo_token(str(candidate["source_png"]), repo_root=repo_root),
                    }
                )
            elif entity_kind == "component":
                candidate_paths.add(_normalize_repo_token(str(candidate["spec_ref"]), repo_root=repo_root))
            elif entity_kind == "test":
                candidate_paths.add(_normalize_repo_token(str(candidate["test_path"]), repo_root=repo_root))
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
            "title": Path(normalized_path).name,
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
    alias = Path(raw_ref).name
    if not alias or "." not in alias:
        return None, ""
    alias_casefold = alias.casefold()
    matches: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    def _path_matches(path_ref: str) -> bool:
        normalized_path = _normalize_repo_token(path_ref, repo_root=repo_root)
        return bool(normalized_path) and Path(normalized_path).name.casefold() == alias_casefold

    def _add(entity: Mapping[str, Any] | None) -> None:
        if not isinstance(entity, Mapping):
            return
        row = _search_row_from_entity(entity)
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
                "title": Path(target_id).name,
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
    normalized_query = _normalize_repo_token(raw_query, repo_root=repo_root)
    lowered = raw_query.casefold()
    compact_lookup = _context_lookup_key(raw_query)
    allowed = {str(kind).strip().lower() for kind in kinds if str(kind).strip()}
    candidate_kinds = tuple(allowed) if allowed else (
        "workstream",
        "plan",
        "bug",
        "diagram",
        "component",
        *_ENGINEERING_NOTE_KINDS,
        "test",
    )
    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    def _add(entity: Mapping[str, Any] | None) -> None:
        if not isinstance(entity, Mapping):
            return
        row = _search_row_from_entity(entity)
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
        aliases = _workstream_lookup_aliases(dict(row), repo_root=repo_root)
        if lowered in aliases or (compact_lookup and compact_lookup in aliases):
            _add(_entity_from_row(kind="workstream", row=row))
            break

    for row in connection.execute("SELECT * FROM plans").fetchall():
        aliases = _plan_lookup_aliases(dict(row), repo_root=repo_root)
        if lowered in aliases or (compact_lookup and compact_lookup in aliases):
            _add(_entity_from_row(kind="plan", row=row))
            break

    for row in connection.execute("SELECT * FROM components").fetchall():
        aliases = _component_lookup_aliases(dict(row), repo_root=repo_root)
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
    if not allowed or any(kind in allowed for kind in _ENGINEERING_NOTE_KIND_SET):
        for note_kind in _ENGINEERING_NOTE_KINDS:
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
    query_tokens = {token.casefold() for token in re.findall(r"[A-Za-z0-9_./:-]+", str(query or "")) if token}
    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for rank, hit in enumerate(fallback_scan.get("results", []), start=1):
        if not isinstance(hit, Mapping):
            continue
        path_ref = _normalize_repo_token(str(hit.get("path", "")).strip(), repo_root=repo_root)
        if not path_ref:
            continue
        entity = _entity_by_path(connection, repo_root=repo_root, path_ref=path_ref)
        if entity is None:
            if bool(_path_signal_profile(path_ref).get("shared")):
                continue
            inferred_kind = _repo_scan_inferred_kind(path_ref)
            if not inferred_kind:
                continue
            entity = {
                "kind": inferred_kind,
                "entity_id": path_ref,
                "title": Path(path_ref).name,
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
        row = _search_row_from_entity(
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
    normalized_kind = _normalize_entity_kind(kind)
    raw_ref = str(ref or "").strip()
    if not raw_ref:
        return None, [], {"resolution_mode": "none"}
    normalized_ref = _normalize_repo_token(raw_ref, repo_root=repo_root)
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
        *_ENGINEERING_NOTE_KIND_SET,
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

    if _WORKSTREAM_ID_RE.fullmatch(raw_ref.upper()):
        entity = _fetch_by_id("workstream", raw_ref.upper())
        if entity is not None:
            return entity, [], {"resolution_mode": "workstream_id"}
    if _DIAGRAM_ID_RE.fullmatch(raw_ref.upper()):
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
    compact_lookup = _context_lookup_key(raw_ref)
    for row in connection.execute("SELECT * FROM workstreams").fetchall():
        aliases = _workstream_lookup_aliases(dict(row), repo_root=repo_root)
        if lowered in aliases or (compact_lookup and compact_lookup in aliases):
            return _entity_from_row(kind="workstream", row=row), [], {"resolution_mode": "workstream_alias"}

    component_rows = connection.execute("SELECT * FROM components").fetchall()
    for row in component_rows:
        aliases = _component_lookup_aliases(dict(row), repo_root=repo_root)
        if lowered in aliases or (compact_lookup and compact_lookup in aliases):
            return _entity_from_row(kind="component", row=row), [], {"resolution_mode": "component_alias"}

    for row in connection.execute("SELECT * FROM plans").fetchall():
        aliases = _plan_lookup_aliases(dict(row), repo_root=repo_root)
        if lowered in aliases or (compact_lookup and compact_lookup in aliases):
            return _entity_from_row(kind="plan", row=row), [], {"resolution_mode": "plan_alias"}

    search_payload = search_entities_payload(repo_root=repo_root, query=raw_ref, limit=5, runtime_mode="auto")
    matches = [dict(row) for row in search_payload.get("results", []) if isinstance(row, Mapping)]
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
        if isinstance(search_payload.get("fallback_scan"), Mapping)
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
            _add(_summarize_entity(resolved))
            return
        if kind in {"doc", "runbook", "code"}:
            _add(
                {
                    "kind": kind,
                    "entity_id": entity_id,
                    "title": Path(entity_id).name,
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
            if workstream_id in set(_json_list(str(row["workstreams_json"]))):
                _add(_summarize_entity(_entity_from_row(kind="component", row=row)))
    elif kind == "component":
        for workstream_id in entity.get("workstreams", []) if isinstance(entity.get("workstreams"), list) else []:
            _add_kind_id("workstream", str(workstream_id))
        for diagram_id in entity.get("diagrams", []) if isinstance(entity.get("diagrams"), list) else []:
            _add_kind_id("diagram", str(diagram_id))
    elif kind == "diagram":
        diagram_id = str(entity.get("entity_id", "")).strip()
        for row in connection.execute("SELECT * FROM components").fetchall():
            if diagram_id in set(_json_list(str(row["diagrams_json"]))):
                _add(_summarize_entity(_entity_from_row(kind="component", row=row)))
    elif kind == "plan":
        backlog = str(entity.get("backlog", "")).strip().strip("`")
        if _WORKSTREAM_ID_RE.fullmatch(backlog):
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
    normalized_paths = {Path(item).as_posix() for item in artifact_paths if item}
    for row in rows:
        event_workstreams = set(_json_list(str(row["workstreams_json"])))
        event_components = set(_json_list(str(row["components_json"])))
        event_artifacts = {Path(item).as_posix() for item in _json_list(str(row["artifacts_json"]))}
        if not (
            event_workstreams.intersection(workstream_ids)
            or event_components.intersection(component_ids)
            or event_artifacts.intersection(normalized_paths)
        ):
            continue
        metadata = json.loads(str(row["metadata_json"] or "{}"))
        results.append(
            {
                "event_id": str(row["event_id"]),
                "ts_iso": str(row["ts_iso"]),
                "kind": str(row["kind"]),
                "summary": str(row["summary"]),
                "workstreams": sorted(event_workstreams),
                "components": sorted(event_components),
                "artifacts": sorted(event_artifacts),
                "metadata": metadata if isinstance(metadata, Mapping) else {},
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
        decoded = json.loads(str(payload["payload_json"]))
        if isinstance(decoded, Mapping):
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

    root = Path(repo_root).resolve()
    started_at = time.perf_counter()
    runtime_ready = _warm_runtime(repo_root=root, runtime_mode=runtime_mode, reason="context", scope="reasoning")
    if not runtime_ready:
        fallback_scan = _full_scan_guidance(
            repo_root=root,
            reason="runtime_unavailable",
            query=str(ref or "").strip(),
            perform_scan=True,
            result_limit=max(3, min(8, int(relation_limit))),
        )
        return {
            "query": str(ref or "").strip(),
            "requested_kind": _normalize_entity_kind(kind),
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
                if isinstance(row, Mapping) and not _odylith_runtime_entity_suppressed(repo_root=root, entity=row)
            ]
            if isinstance(entity, Mapping) and _odylith_runtime_entity_suppressed(repo_root=root, entity=entity):
                entity = None
                lookup = {
                    **dict(lookup),
                    "resolution_mode": "odylith_disabled",
                    "runtime_ready": True,
                    "odylith_switch": _odylith_switch_snapshot(repo_root=root),
                }
            if entity is None and _odylith_query_targets_disabled(repo_root=root, query=str(ref or "").strip()):
                return {
                    "query": str(ref or "").strip(),
                    "requested_kind": _normalize_entity_kind(kind),
                    "resolved": False,
                    "matches": [],
                    "lookup": dict(lookup),
                    "full_scan_recommended": False,
                    "full_scan_reason": "odylith_disabled",
                    "fallback_scan": {
                        "performed": False,
                        "terms": _full_scan_terms(repo_root=root, query=str(ref or "").strip()),
                        "roots": _available_full_scan_roots(repo_root=root),
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
                if isinstance(lookup.get("fallback_scan"), Mapping)
                else _full_scan_guidance(
                    repo_root=root,
                    reason=full_scan_reason,
                    query=str(ref or "").strip(),
                    perform_scan=True,
                    result_limit=max(3, min(8, int(relation_limit))),
                )
            )
            return {
                "query": str(ref or "").strip(),
                "requested_kind": _normalize_entity_kind(kind),
                "resolved": False,
                "matches": matches,
                "lookup": dict(lookup),
                "full_scan_recommended": True,
                "full_scan_reason": full_scan_reason,
                "fallback_scan": fallback_scan,
            }
        relations = _relation_rows(connection, entity=entity, relation_limit=relation_limit)
        related = _related_entities(connection, entity=entity, relations=relations)
        return {
            "query": str(ref or "").strip(),
            "requested_kind": _normalize_entity_kind(kind),
            "resolved": True,
            "entity": entity,
            "matches": matches,
            "lookup": dict(lookup),
            "full_scan_recommended": False,
            "full_scan_reason": "",
            "fallback_scan": {
                "performed": False,
                "terms": _full_scan_terms(repo_root=root, query=str(ref or "").strip()),
                "roots": _available_full_scan_roots(repo_root=root),
                "commands": [],
                "results": [],
                "reason": "",
                "reason_message": "",
                "changed_paths": [],
            },
            "relations": relations,
            "related_entities": related,
            "recent_codex_events": _recent_context_events(
                connection,
                entity=entity,
                related=related,
                event_limit=event_limit,
            ),
            "delivery_scopes": _delivery_context_rows(
                connection,
                entity=entity,
                related=related,
            ),
        }
    finally:
        connection.close()
        record_runtime_timing(
            repo_root=root,
            category="reasoning",
            operation="context",
            duration_ms=(time.perf_counter() - started_at) * 1000.0,
            metadata={
                "query": str(ref or "").strip(),
                "requested_kind": _normalize_entity_kind(kind),
            },
        )

def load_backlog_rows(
    *,
    repo_root: Path,
    runtime_mode: str = "auto",
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    if _warm_runtime(repo_root=root, runtime_mode=runtime_mode, reason="backlog_rows"):
        connection = _connect(root)
        try:
            result: dict[str, Any] = {
                "updated_utc": str(
                    json.loads(
                        (
                            connection.execute(
                                "SELECT payload_json FROM projection_state WHERE name = 'workstreams'"
                            ).fetchone() or {"payload_json": "{}"}
                        )["payload_json"]
                    ).get("updated_utc", "")
                ).strip(),
                "rationale_map": _load_backlog_projection(repo_root=root).get("rationale_map", {}),
            }
            for section in ("active", "execution", "finished", "parked"):
                rows = connection.execute(
                    """
                    SELECT rank, idea_id, title, priority, ordering_score, metadata_json, idea_file
                    FROM workstreams
                    WHERE section = ?
                    ORDER BY
                        CASE
                            WHEN rank = '-' THEN 999999
                            WHEN rank GLOB '[0-9]*' THEN CAST(rank AS INTEGER)
                            ELSE 999999
                        END,
                        idea_id
                    """,
                    (section,),
                ).fetchall()
                values: list[dict[str, str]] = []
                for row in rows:
                    metadata = json.loads(str(row["metadata_json"] or "{}"))
                    values.append(
                        {
                            "rank": str(row["rank"]),
                            "idea_id": str(row["idea_id"]),
                            "title": str(row["title"]),
                            "priority": str(row["priority"]),
                            "ordering_score": str(row["ordering_score"]),
                            "commercial_value": str(metadata.get("commercial_value", "")).strip(),
                            "product_impact": str(metadata.get("product_impact", "")).strip(),
                            "market_value": str(metadata.get("market_value", "")).strip(),
                            "sizing": str(metadata.get("sizing", "")).strip(),
                            "complexity": str(metadata.get("complexity", "")).strip(),
                            "impacted_lanes": str(metadata.get("impacted_lanes", "")).strip(),
                            "status": str(metadata.get("status", "")).strip(),
                            "link": (
                                f"[{Path(str(row['idea_file'])).stem}]({str(row['idea_file'])})"
                                if str(row["idea_file"]).strip()
                                else ""
                            ),
                        }
                    )
                result[section] = values
            return result
        finally:
            connection.close()
    return _load_backlog_projection(repo_root=root)

def _markdown_section_bodies(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current: str | None = None
    lines: list[str] = []
    for raw_line in str(text or "").splitlines():
        match = _HEADER_RE.match(raw_line)
        if match:
            if current is not None:
                sections[current] = "\n".join(lines).strip()
            current = str(match.group(1) or "").strip()
            lines = []
            continue
        if current is not None:
            lines.append(raw_line.rstrip())
    if current is not None:
        sections[current] = "\n".join(lines).strip()
    return sections

def load_backlog_list(
    *,
    repo_root: Path,
    runtime_mode: str = "auto",
) -> dict[str, Any]:
    return load_backlog_rows(repo_root=repo_root, runtime_mode=runtime_mode)

def _runtime_backlog_detail_rows(
    *,
    repo_root: Path,
) -> dict[str, dict[str, Any]]:
    root = Path(repo_root).resolve()

    def _load() -> dict[str, dict[str, Any]]:
        connection = _connect(root)
        try:
            rows = connection.execute(
                """
                SELECT idea_id, metadata_json, idea_file
                FROM workstreams
                ORDER BY idea_id
                """
            ).fetchall()
        finally:
            connection.close()
        payload: dict[str, dict[str, Any]] = {}
        for row in rows:
            token = str(row["idea_id"] or "").strip().upper()
            if not _WORKSTREAM_ID_RE.fullmatch(token):
                continue
            try:
                metadata = json.loads(str(row["metadata_json"] or "{}"))
            except json.JSONDecodeError:
                metadata = {}
            payload[token] = {
                "metadata": dict(metadata) if isinstance(metadata, Mapping) else {},
                "idea_file": str(row["idea_file"] or "").strip(),
            }
        return payload

    cache_key = f"{root}:default"
    if _PROCESS_WARM_CACHE_FINGERPRINTS.get(cache_key, ""):
        rows = _cached_projection_rows(
            repo_root=root,
            cache_name="workstream_detail_rows",
            loader=_load,
            scope="default",
        )
    else:
        rows = _load()
    return dict(rows) if isinstance(rows, Mapping) else {}

def _runtime_backlog_detail(
    *,
    repo_root: Path,
    workstream_id: str,
) -> dict[str, Any] | None:
    root = Path(repo_root).resolve()
    row = _runtime_backlog_detail_rows(repo_root=root).get(str(workstream_id or "").strip().upper())
    if not isinstance(row, Mapping):
        return None
    idea_token = str(row.get("idea_file", "")).strip()
    if not idea_token:
        return None
    idea_path = (root / idea_token).resolve() if not Path(idea_token).is_absolute() else Path(idea_token).resolve()
    if not idea_path.is_file():
        return None
    raw_text = _raw_text(idea_path)
    metadata = dict(row.get("metadata", {})) if isinstance(row.get("metadata"), Mapping) else {}
    metadata.setdefault("idea_id", str(workstream_id or "").strip().upper())
    promoted_to_plan = str(metadata.get("promoted_to_plan", "")).strip()
    if promoted_to_plan:
        metadata["promoted_to_plan"] = _normalize_repo_token(promoted_to_plan, repo_root=root)
    return {
        "idea_id": str(workstream_id or "").strip().upper(),
        "idea_file": str(idea_path.relative_to(root)) if idea_path.is_relative_to(root) else str(idea_path),
        "metadata": metadata,
        "sections": _markdown_section_bodies(raw_text),
        "search_body": raw_text,
        "promoted_to_plan": str(metadata.get("promoted_to_plan", "")).strip(),
    }

def load_backlog_detail(
    *,
    repo_root: Path,
    workstream_id: str,
    runtime_mode: str = "auto",
) -> dict[str, Any] | None:
    root = Path(repo_root).resolve()
    token = str(workstream_id or "").strip().upper()
    if not _WORKSTREAM_ID_RE.fullmatch(token):
        return None
    del runtime_mode
    if not _odylith_ablation_active(repo_root=root):
        try:
            runtime_detail = _runtime_backlog_detail(repo_root=root, workstream_id=token)
        except RuntimeError:
            runtime_detail = None
        if runtime_detail is not None:
            return runtime_detail
    spec = _load_idea_specs(repo_root=root).get(token)
    if spec is None:
        return None
    raw_text = _raw_text(spec.path)
    metadata = dict(spec.metadata)
    if str(metadata.get("promoted_to_plan", "")).strip():
        metadata["promoted_to_plan"] = _normalize_repo_token(str(metadata.get("promoted_to_plan", "")).strip(), repo_root=root)
    return {
        "idea_id": token,
        "idea_file": str(spec.path.relative_to(root)) if spec.path.is_relative_to(root) else str(spec.path),
        "metadata": metadata,
        "sections": _markdown_section_bodies(raw_text),
        "search_body": raw_text,
        "promoted_to_plan": str(metadata.get("promoted_to_plan", "")).strip(),
    }

def load_backlog_document(
    *,
    repo_root: Path,
    workstream_id: str,
    view: str,
    runtime_mode: str = "auto",
) -> dict[str, Any] | None:
    del runtime_mode  # detail/document bodies are still sourced from markdown contracts today.
    root = Path(repo_root).resolve()
    token = str(workstream_id or "").strip().upper()
    mode = str(view or "").strip().lower()
    detail = load_backlog_detail(repo_root=root, workstream_id=token)
    if detail is None:
        return None
    if mode == "spec":
        spec_token = str(detail.get("idea_file", "")).strip()
        spec_path = (root / spec_token).resolve() if spec_token and not Path(spec_token).is_absolute() else Path(spec_token).resolve()
        return {
            "idea_id": token,
            "view": "spec",
            "path": str(spec_path.relative_to(root)) if spec_path.is_relative_to(root) else str(spec_path),
            "markdown": _raw_text(spec_path),
        }
    if mode == "plan":
        plan_token = str(detail.get("promoted_to_plan", "")).strip()
        if not plan_token:
            return None
        plan_path = (root / plan_token).resolve() if not Path(plan_token).is_absolute() else Path(plan_token).resolve()
        if not plan_path.is_file():
            return None
        return {
            "idea_id": token,
            "view": "plan",
            "path": str(plan_path.relative_to(root)) if plan_path.is_relative_to(root) else str(plan_path),
            "markdown": _raw_text(plan_path),
        }
    return None

def load_plan_rows(
    *,
    repo_root: Path,
    runtime_mode: str = "auto",
) -> dict[str, list[dict[str, str]]]:
    root = Path(repo_root).resolve()
    if _warm_runtime(repo_root=root, runtime_mode=runtime_mode, reason="plan_rows"):
        connection = _connect(root)
        try:
            result: dict[str, list[dict[str, str]]] = {}
            for section in ("active", "parked", "done"):
                rows = connection.execute(
                    """
                    SELECT plan_path, status, created, updated, backlog
                    FROM plans
                    WHERE section = ?
                    ORDER BY updated DESC, plan_path
                    """,
                    (section,),
                ).fetchall()
                result[section] = [
                    {
                        "Plan": f"`{row['plan_path']}`",
                        "Status": str(row["status"]),
                        "Created": str(row["created"]),
                        "Updated": str(row["updated"]),
                        "Backlog": f"`{row['backlog']}`" if str(row["backlog"]) else "`-`",
                    }
                    for row in rows
                ]
            return result
        finally:
            connection.close()
    return _load_plan_projection(repo_root=root)

def load_bug_rows(
    *,
    repo_root: Path,
    runtime_mode: str = "auto",
) -> list[dict[str, str]]:
    root = Path(repo_root).resolve()
    if _warm_runtime(repo_root=root, runtime_mode=runtime_mode, reason="bug_rows"):
        connection = _connect(root)
        try:
            rows = connection.execute(
                """
                SELECT bug_id, date, title, severity, components, status, link_target, source_path
                FROM bugs
                ORDER BY date DESC, title
                """
            ).fetchall()
            payload_rows: list[dict[str, str]] = []
            for row in rows:
                source_path = str(row["source_path"] or "").strip()
                index_path = (root / source_path).resolve() if source_path else root / "bugs" / "INDEX.md"
                normalized_link = _normalize_bug_link_target(
                    repo_root=root,
                    index_path=index_path,
                    link_target=str(row["link_target"] or "").strip(),
                )
                if normalized_link and not (root / normalized_link).is_file():
                    continue
                bug_id = resolve_casebook_bug_id(
                    explicit_bug_id=str(row["bug_id"] or "").strip(),
                    seed=normalized_link or f"{row['date']}::{row['title']}",
                )
                payload = {
                    BUG_ID_FIELD: bug_id,
                    "Date": str(row["date"]),
                    "Title": str(row["title"]),
                    "Severity": str(row["severity"]),
                    "Components": str(row["components"]),
                    "Status": canonicalize_bug_status(str(row["status"])),
                    "Link": f"[bug]({normalized_link})" if normalized_link else "",
                    "IndexPath": source_path or "odylith/casebook/bugs/INDEX.md",
                }
                if _is_bug_placeholder_row(payload):
                    continue
                payload_rows.append(payload)
            return payload_rows
        finally:
            connection.close()
    return _load_bug_projection(repo_root=root)

def load_bug_snapshot(
    *,
    repo_root: Path,
    runtime_mode: str = "auto",
) -> list[dict[str, Any]]:
    root = Path(repo_root).resolve()
    rows = load_bug_rows(repo_root=root, runtime_mode=runtime_mode)
    bug_lookup = _build_bug_reference_lookup(rows=rows, repo_root=root)
    component_index = load_component_index(repo_root=root, runtime_mode=runtime_mode)
    component_rows = _component_rows_from_index(component_index)
    diagram_lookup = {
        str(row.get("diagram_id", "")).strip().upper(): {
            "diagram_id": str(row.get("diagram_id", "")).strip().upper(),
            "title": str(row.get("title", "")).strip(),
            "slug": str(row.get("slug", "")).strip(),
        }
        for row in _load_diagram_projection(repo_root=root)
        if str(row.get("diagram_id", "")).strip()
    }
    snapshot: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        if _is_bug_placeholder_row(row):
            continue
        link_target = _parse_link_target(str(row.get("Link", "")))
        bug_id = resolve_casebook_bug_id(
            explicit_bug_id=str(row.get(BUG_ID_FIELD, "")).strip(),
            seed=link_target or f"{row.get('Date', '')}::{row.get('Title', '')}",
        )
        bug_key = link_target or f"{row.get('Date', '')}::{row.get('Title', '')}"
        bug_path = (root / link_target).resolve() if link_target else None
        raw_text = _raw_text(bug_path) if bug_path is not None else ""
        lines = raw_text.splitlines() if raw_text else []
        fields = _parse_bug_entry_fields(lines) if lines else {}

        date = str(row.get("Date", "")).strip() or str(fields.get("Created", "")).strip()
        title = str(row.get("Title", "")).strip()
        severity = str(row.get("Severity", "")).strip() or str(fields.get("Severity", "")).strip()
        status = canonicalize_bug_status(str(row.get("Status", "")).strip() or str(fields.get("Status", "")).strip())
        if status:
            fields["Status"] = status
        components_raw = str(row.get("Components", "")).strip() or str(fields.get("Components Affected", "")).strip()
        components = _parse_component_tokens(components_raw)
        path_refs = _extract_path_refs(
            text="\n".join(
                token
                for token in (
                    raw_text,
                    str(fields.get("Code References", "")).strip(),
                    str(fields.get("Runbook References", "")).strip(),
                    str(fields.get("Components Affected", "")).strip(),
                )
                if token
            ),
            repo_root=root,
        )
        ref_buckets = _classify_bug_path_refs(path_refs)
        component_matches = _component_matches_for_bug_paths(
            component_rows=component_rows,
            component_index=component_index,
            path_refs=path_refs,
        )
        diagram_refs = _diagram_refs_for_bug_components(
            component_matches=component_matches,
            diagram_lookup=diagram_lookup,
        )
        workstreams = _extract_workstream_refs(
            "\n".join(
                token
                for token in (
                    raw_text,
                    str(fields.get("Related Incidents/Bugs", "")).strip(),
                    str(fields.get("Config/Flags", "")).strip(),
                )
                if token
            )
        )
        related_bug_refs = _related_bug_refs_from_text(
            text=str(fields.get("Related Incidents/Bugs", "")).strip(),
            bug_lookup=bug_lookup,
            repo_root=root,
        )
        agent_guidance = _bug_agent_guidance(
            fields=fields,
            ref_buckets=ref_buckets,
            component_matches=component_matches,
            workstreams=workstreams,
            related_bug_refs=related_bug_refs,
        )
        detail_sections = _ordered_bug_detail_sections(fields)
        search_text = "\n".join(
            token
            for token in (
                bug_id,
                title,
                severity,
                status,
                components_raw,
                raw_text,
                "\n".join(match.get("name", "") for match in component_matches),
                "\n".join(ref.get("title", "") for ref in related_bug_refs),
                "\n".join(
                    str(item.get("value", "")).strip()
                    for item in agent_guidance.get("lessons", [])
                    if isinstance(item, Mapping)
                ),
                "\n".join(str(item).strip() for item in agent_guidance.get("preflight_checks", [])),
            )
            if token
        )
        is_open = _bug_is_open(status)
        intelligence_coverage = _bug_intelligence_coverage(fields=fields, severity=severity)
        snapshot.append(
            {
                "bug_id": bug_id,
                "bug_key": str(bug_key).strip(),
                "title": title,
                "date": date,
                "severity": severity,
                "severity_token": str(severity).strip().lower(),
                "status": status,
                "status_token": str(status).strip().lower(),
                "components": components_raw,
                "component_tokens": components,
                "archive_bucket": _bug_archive_bucket_from_link_target(link_target),
                "source_path": link_target,
                "source_exists": bool(link_target and bug_path is not None and bug_path.is_file()),
                "is_open": is_open,
                "is_open_critical": is_open and str(severity).strip().lower() in _BUG_CRITICAL_SEVERITIES,
                "workstreams": workstreams,
                "primary_workstream": workstreams[0] if workstreams else "",
                "summary": _bug_summary_from_fields(fields, lines),
                "detail_sections": detail_sections,
                "fields": dict(fields),
                "path_refs": path_refs,
                "code_refs": ref_buckets["code"],
                "doc_refs": ref_buckets["docs"],
                "test_refs": ref_buckets["tests"],
                "contract_refs": ref_buckets["contracts"],
                "component_matches": component_matches,
                "diagram_refs": diagram_refs,
                "related_bug_refs": related_bug_refs,
                "agent_guidance": agent_guidance,
                "intelligence_coverage": intelligence_coverage,
                "search_text": search_text,
            }
        )
    return snapshot

def _component_entry_from_runtime_row(row: Mapping[str, Any]) -> component_registry.ComponentEntry:
    metadata = json.loads(str(row["metadata_json"] or "{}"))
    payload = dict(metadata) if isinstance(metadata, Mapping) else {}
    if payload.get("component_id"):
        return component_registry.ComponentEntry(
            component_id=str(payload.get("component_id", "")).strip(),
            name=str(payload.get("name", "")).strip(),
            kind=str(payload.get("kind", "")).strip(),
            category=str(payload.get("category", "")).strip(),
            qualification=str(payload.get("qualification", "")).strip(),
            aliases=[str(token).strip() for token in payload.get("aliases", []) if str(token).strip()]
            if isinstance(payload.get("aliases"), list)
            else [],
            path_prefixes=[str(token).strip() for token in payload.get("path_prefixes", []) if str(token).strip()]
            if isinstance(payload.get("path_prefixes"), list)
            else [],
            workstreams=[str(token).strip() for token in payload.get("workstreams", []) if str(token).strip()]
            if isinstance(payload.get("workstreams"), list)
            else [],
            diagrams=[str(token).strip() for token in payload.get("diagrams", []) if str(token).strip()]
            if isinstance(payload.get("diagrams"), list)
            else [],
            owner=str(payload.get("owner", "")).strip(),
            status=str(payload.get("status", "")).strip(),
            what_it_is=str(payload.get("what_it_is", "")).strip(),
            why_tracked=str(payload.get("why_tracked", "")).strip(),
            spec_ref=str(payload.get("spec_ref", "")).strip(),
            sources=[str(token).strip() for token in payload.get("sources", []) if str(token).strip()]
            if isinstance(payload.get("sources"), list)
            else [],
            subcomponents=[str(token).strip() for token in payload.get("subcomponents", []) if str(token).strip()]
            if isinstance(payload.get("subcomponents"), list)
            else [],
            product_layer=str(payload.get("product_layer", "")).strip(),
        )
    return component_registry.ComponentEntry(
        component_id=str(row["component_id"]).strip(),
        name=str(row["name"]).strip(),
        kind=str(payload.get("kind", "")).strip(),
        category=str(payload.get("category", "")).strip(),
        qualification=str(payload.get("qualification", "")).strip(),
        aliases=_json_list(str(row["aliases_json"])),
        path_prefixes=[str(token).strip() for token in payload.get("path_prefixes", []) if str(token).strip()]
        if isinstance(payload.get("path_prefixes"), list)
        else [],
        workstreams=_json_list(str(row["workstreams_json"])),
        diagrams=_json_list(str(row["diagrams_json"])),
        owner=str(row["owner"]).strip(),
        status=str(row["status"]).strip(),
        what_it_is=str(payload.get("what_it_is", "")).strip(),
        why_tracked=str(payload.get("why_tracked", "")).strip(),
        spec_ref=str(row["spec_ref"]).strip(),
        sources=[str(token).strip() for token in payload.get("sources", []) if str(token).strip()]
        if isinstance(payload.get("sources"), list)
        else [],
        subcomponents=[str(token).strip() for token in payload.get("subcomponents", []) if str(token).strip()]
        if isinstance(payload.get("subcomponents"), list)
        else [],
        product_layer=str(payload.get("product_layer", "")).strip(),
    )

def load_component_index(
    *,
    repo_root: Path,
    runtime_mode: str = "auto",
) -> dict[str, component_registry.ComponentEntry]:
    root = Path(repo_root).resolve()
    if _warm_runtime(repo_root=root, runtime_mode=runtime_mode, reason="component_index"):
        connection = _connect(root)
        try:
            rows = connection.execute("SELECT * FROM components ORDER BY component_id").fetchall()
            component_index = {
                str(row["component_id"]).strip(): _component_entry_from_runtime_row(row)
                for row in rows
                if str(row["component_id"]).strip()
            }
            if _odylith_ablation_active(repo_root=root):
                return _apply_odylith_component_index_ablation(component_index)
            return component_index
        finally:
            connection.close()
    manifest_path = component_registry.default_manifest_path(repo_root=root)
    catalog_path = root / component_registry.DEFAULT_CATALOG_PATH
    ideas_root = root / component_registry.DEFAULT_IDEAS_ROOT
    if not manifest_path.is_file():
        return {}
    components, _alias_to_component, _diagnostics = component_registry.build_component_index(
        repo_root=root,
        manifest_path=manifest_path,
        catalog_path=catalog_path,
        ideas_root=ideas_root,
    )
    if _odylith_ablation_active(repo_root=root):
        return _apply_odylith_component_index_ablation(components)
    return components

def load_registry_list(
    *,
    repo_root: Path,
    runtime_mode: str = "auto",
) -> list[dict[str, Any]]:
    components = load_component_index(repo_root=repo_root, runtime_mode=runtime_mode)
    rows: list[dict[str, Any]] = []
    for component_id in sorted(components):
        entry = components[component_id]
        rows.append(
            {
                "component_id": entry.component_id,
                "name": entry.name,
                "kind": entry.kind,
                "category": entry.category,
                "qualification": entry.qualification,
                "owner": entry.owner,
                "status": entry.status,
                "what_it_is": entry.what_it_is,
                "why_tracked": entry.why_tracked,
                "aliases": list(entry.aliases),
            }
        )
    return rows

def load_component_registry_snapshot(
    *,
    repo_root: Path,
    runtime_mode: str = "auto",
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    odylith_ablation_active = _odylith_ablation_active(repo_root=root)
    if _warm_runtime(repo_root=root, runtime_mode=runtime_mode, reason="component_registry_snapshot"):
        connection = _connect(root)
        try:
            component_rows = connection.execute("SELECT * FROM components ORDER BY component_id").fetchall()
            spec_rows = connection.execute("SELECT * FROM component_specs ORDER BY component_id").fetchall()
            trace_rows = connection.execute(
                "SELECT component_id, bucket, path FROM component_traceability ORDER BY component_id, bucket, path"
            ).fetchall()
            event_rows = connection.execute(
                """
                SELECT event_index, ts_iso, kind, summary, workstreams_json, artifacts_json,
                       explicit_components_json, mapped_components_json, confidence, meaningful
                FROM registry_events
                ORDER BY ts_iso DESC, event_index DESC
                """
            ).fetchall()
            state_row = connection.execute(
                "SELECT payload_json FROM projection_state WHERE name = 'components'"
            ).fetchone()
        finally:
            connection.close()
        components = {
            str(row["component_id"]).strip(): _component_entry_from_runtime_row(row)
            for row in component_rows
            if str(row["component_id"]).strip()
        }
        payload = json.loads(str(state_row["payload_json"] or "{}")) if state_row is not None else {}
        diagnostics = [str(item) for item in payload.get("diagnostics", []) if str(item).strip()] if isinstance(payload, Mapping) else []
        candidate_queue = [
            dict(item)
            for item in payload.get("candidate_queue", [])
            if isinstance(payload, Mapping) and isinstance(payload.get("candidate_queue"), list) and isinstance(item, Mapping)
        ] if isinstance(payload, Mapping) else []
        unmapped_meaningful_events = [
            component_registry.MappedEvent(
                event_index=int(item.get("event_index", 0) or 0),
                ts_iso=str(item.get("ts_iso", "")).strip(),
                kind=str(item.get("kind", "")).strip(),
                summary=str(item.get("summary", "")).strip(),
                workstreams=[str(token).strip() for token in item.get("workstreams", []) if str(token).strip()]
                if isinstance(item.get("workstreams"), list)
                else [],
                artifacts=[str(token).strip() for token in item.get("artifacts", []) if str(token).strip()]
                if isinstance(item.get("artifacts"), list)
                else [],
                explicit_components=[str(token).strip() for token in item.get("explicit_components", []) if str(token).strip()]
                if isinstance(item.get("explicit_components"), list)
                else [],
                mapped_components=[str(token).strip() for token in item.get("mapped_components", []) if str(token).strip()]
                if isinstance(item.get("mapped_components"), list)
                else [],
                confidence=str(item.get("confidence", "")).strip(),
                meaningful=bool(item.get("meaningful")),
            )
            for item in payload.get("unmapped_meaningful_events", [])
            if isinstance(payload, Mapping) and isinstance(payload.get("unmapped_meaningful_events"), list) and isinstance(item, Mapping)
        ] if isinstance(payload, Mapping) else []
        mapped_events = [
            component_registry.MappedEvent(
                event_index=int(row["event_index"] or 0),
                ts_iso=str(row["ts_iso"]).strip(),
                kind=str(row["kind"]).strip(),
                summary=str(row["summary"]).strip(),
                workstreams=_json_list(str(row["workstreams_json"])),
                artifacts=_json_list(str(row["artifacts_json"])),
                explicit_components=_json_list(str(row["explicit_components_json"])),
                mapped_components=_json_list(str(row["mapped_components_json"])),
                confidence=str(row["confidence"]).strip(),
                meaningful=bool(int(row["meaningful"] or 0)),
            )
            for row in event_rows
        ]
        report = component_registry.ComponentRegistryReport(
            components=components,
            mapped_events=mapped_events,
            unmapped_meaningful_events=unmapped_meaningful_events,
            candidate_queue=candidate_queue,
            forensic_coverage=component_registry.build_component_forensic_coverage(
                component_index=components,
                mapped_events=mapped_events,
                repo_root=repo_root,
            ),
            diagnostics=diagnostics,
        )
        spec_snapshots: dict[str, component_registry.ComponentSpecSnapshot] = {}
        for row in spec_rows:
            component_id = str(row["component_id"]).strip()
            if not component_id:
                continue
            feature_history_payload = json.loads(str(row["feature_history_json"] or "[]"))
            skill_tiers_payload = json.loads(str(row["skill_trigger_tiers_json"] or "{}"))
            playbook_payload = json.loads(str(row["validation_playbook_commands_json"] or "[]"))
            spec_snapshots[component_id] = component_registry.ComponentSpecSnapshot(
                title=str(row["title"]).strip(),
                last_updated=str(row["last_updated"]).strip(),
                feature_history=[dict(item) for item in feature_history_payload if isinstance(item, Mapping)]
                if isinstance(feature_history_payload, list)
                else [],
                markdown=str(row["markdown"] or ""),
                skill_trigger_tiers=dict(skill_tiers_payload) if isinstance(skill_tiers_payload, Mapping) else {},
                skill_trigger_structure=str(row["skill_trigger_structure"]).strip(),
                validation_playbook_commands=[dict(item) for item in playbook_payload if isinstance(item, Mapping)]
                if isinstance(playbook_payload, list)
                else [],
            )
        traceability: dict[str, dict[str, list[str]]] = {}
        for row in trace_rows:
            component_id = str(row["component_id"]).strip()
            bucket = str(row["bucket"]).strip()
            path = str(row["path"]).strip()
            if not component_id or not bucket or not path:
                continue
            traceability.setdefault(
                component_id,
                {"runbooks": [], "developer_docs": [], "code_references": []},
            ).setdefault(bucket, []).append(path)
        for component_id, buckets in traceability.items():
            for bucket, values in buckets.items():
                buckets[bucket] = _dedupe_strings(values)
        snapshot = {
            "report": report,
            "traceability": traceability,
            "spec_snapshots": spec_snapshots,
            "odylith_switch": _odylith_switch_snapshot(repo_root=root),
        }
        if odylith_ablation_active:
            return _apply_odylith_registry_snapshot_ablation(
                repo_root=root,
                report=report,
                traceability=traceability,
                spec_snapshots=spec_snapshots,
            )
        return snapshot

    manifest_path = component_registry.default_manifest_path(repo_root=root)
    catalog_path = root / component_registry.DEFAULT_CATALOG_PATH
    ideas_root = root / component_registry.DEFAULT_IDEAS_ROOT
    stream_path = root / component_registry.DEFAULT_STREAM_PATH
    report = component_registry.build_component_registry_report(
        repo_root=root,
        manifest_path=manifest_path,
        catalog_path=catalog_path,
        ideas_root=ideas_root,
        stream_path=stream_path,
    )
    traceability = component_registry.build_component_traceability_index(
        repo_root=root,
        components=report.components,
    )
    spec_snapshots = {
        component_id: component_registry.load_component_spec_snapshot(spec_path=root / entry.spec_ref)
        for component_id, entry in report.components.items()
        if entry.spec_ref and (root / entry.spec_ref).is_file()
    }
    snapshot = {
        "report": report,
        "traceability": traceability,
        "spec_snapshots": spec_snapshots,
        "odylith_switch": _odylith_switch_snapshot(repo_root=root),
    }
    if odylith_ablation_active:
        return _apply_odylith_registry_snapshot_ablation(
            repo_root=root,
            report=report,
            traceability=traceability,
            spec_snapshots=spec_snapshots,
        )
    return snapshot

def load_registry_detail(
    *,
    repo_root: Path,
    component_id: str,
    runtime_mode: str = "auto",
    detail_level: str = "full",
) -> dict[str, Any] | None:
    token = str(component_id or "").strip().lower()
    if not token:
        return None
    root = Path(repo_root).resolve()
    normalized_detail_level = str(detail_level or "").strip().lower()
    if normalized_detail_level == "grounding_light" and not _odylith_ablation_active(repo_root=root):
        def _load_runtime_detail() -> dict[str, Any] | None:
            try:
                connection = _connect(root)
            except RuntimeError:
                return None
            try:
                component_row = connection.execute(
                    "SELECT * FROM components WHERE component_id = ? LIMIT 1",
                    (token,),
                ).fetchone()
                if component_row is None:
                    return None
                spec_row = connection.execute(
                    "SELECT * FROM component_specs WHERE component_id = ? LIMIT 1",
                    (token,),
                ).fetchone()
                trace_rows = connection.execute(
                    """
                    SELECT bucket, path
                    FROM component_traceability
                    WHERE component_id = ?
                    ORDER BY bucket, path
                    """,
                    (token,),
                ).fetchall()
                return odylith_context_engine_registry_detail_runtime.build_runtime_registry_detail(
                    entry=_component_entry_from_runtime_row(component_row),
                    spec_row=spec_row,
                    trace_rows=trace_rows,
                )
            finally:
                connection.close()

        cache_key = f"{root}:reasoning"
        if _PROCESS_WARM_CACHE_FINGERPRINTS.get(cache_key, ""):
            detail = _cached_projection_rows(
                repo_root=root,
                cache_name=f"registry_detail_grounding_light:{token}",
                loader=_load_runtime_detail,
                scope="reasoning",
            )
        else:
            detail = _load_runtime_detail()
        if isinstance(detail, Mapping):
            return dict(detail)
    snapshot = load_component_registry_snapshot(repo_root=repo_root, runtime_mode=runtime_mode)
    return odylith_context_engine_registry_detail_runtime.build_registry_detail(
        snapshot=snapshot,
        component_id=token,
        detail_level=detail_level,
    )
