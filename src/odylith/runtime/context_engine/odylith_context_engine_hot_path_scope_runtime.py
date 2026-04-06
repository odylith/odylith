from __future__ import annotations

from typing import Any


def bind(host: Any) -> None:
    getter = host.__getitem__ if isinstance(host, dict) else lambda name: getattr(host, name)
    for name in ('Any', 'Mapping', 'Path', 'SESSION_STALE_SECONDS', 'Sequence', '_PROCESS_PATH_SCOPE_CACHE', '_SESSION_CLAIM_MODES', '_WORKSTREAM_SELECTION_CONFIDENT_SCORE', '_WORKSTREAM_SELECTION_GAP_MIN', '_add_workstream_component_evidence', '_add_workstream_diagram_evidence', '_add_workstream_path_evidence', '_base_workstream_candidate', '_cached_projection_rows', '_candidate', '_components_for_paths', '_dedupe_strings', '_engineering_note_summary', '_entity_by_kind_id', '_entity_from_row', '_extract_path_refs', '_finalize_workstream_candidates', '_git_branch_name', '_git_head_oid', '_json_list', '_load_component_match_rows_from_components', '_normalize_changed_path_list', '_normalize_repo_token', '_normalized_path_match_type', '_normalized_string_list', '_parse_component_tokens', '_path_fingerprint', '_path_signal_profile', '_path_touches_watch', '_prioritize_scope_paths', '_prune_low_precision_workstream_candidates', '_selection_payload', '_summarize_entity', '_utc_now', '_workspace_activity_fingerprint', '_workstream_has_path_signal', '_workstream_token', 'age_seconds', 'ambiguity_class', 'analysis_paths', 'audit', 'authority_graph', 'authority_graph_counts', 'auto_claim_paths', 'benchmark_summary', 'best_path_depth', 'blast_radius', 'blast_radius_counts', 'bootstraps_root', 'broad_only', 'bucket', 'bug_rows', 'cache_key', 'cache_signature', 'cached_scope', 'candidate', 'candidate_by_id', 'candidate_map', 'candidate_paths', 'candidate_rows', 'candidates', 'changed_paths', 'claim_mode', 'claim_sets', 'claimed_paths', 'claimed_workstream', 'claims', 'code_edge_rows', 'code_neighbors', 'compact', 'compact_authority_counts', 'compact_benchmark_summary', 'compact_blast_radius', 'compact_coverage', 'compact_execution_hint', 'compact_fallback_scan', 'compact_historical', 'competing_candidates', 'component', 'component_entities', 'component_id', 'component_ids', 'component_map', 'component_rows', 'components', 'confidence', 'connection', 'contract_consumers', 'contract_refs', 'contract_touchpoint_count', 'coverage', 'covered_by_runbooks', 'degraded', 'detail_level', 'diagram', 'diagram_ids', 'diagram_watch_gap_count', 'direct', 'direct_match_rows', 'documented_by', 'documents', 'domain', 'dt', 'empirical_score', 'entity', 'exact_path_hits', 'execution_hint', 'existing_session', 'expires', 'explicit', 'explicit_claims', 'explicit_entity', 'explicit_paths', 'explicit_workstream', 'failure_count', 'fallback_scan', 'field', 'full_scan_reason', 'generated_surfaces', 'governance', 'hinted_workstream', 'historical_evidence', 'history', 'include_stale', 'intent', 'invoked_by_make', 'item', 'json', 'judgment', 'judgment_hint', 'judgment_reason', 'key', 'lease_expires', 'lease_seconds', 'limit', 'linked_components', 'linked_diagrams', 'make_invocations', 'match', 'match_rows', 'match_type', 'matched_by', 'matched_components', 'matched_id_set', 'matched_ids', 'matched_paths', 'matched_workstreams', 'metadata', 'namespace', 'normalized', 'normalized_changed_paths', 'normalized_component_id', 'normalized_components', 'normalized_workstream', 'note_components', 'note_id', 'note_kind', 'note_path', 'note_paths', 'note_rows', 'note_workstreams', 'now', 'odylith_context_cache', 'operator_consequence_count', 'os', 'overlap', 'packet_state', 'parsed', 'path', 'path_ref', 'payload', 'placeholders', 'projection_snapshot_path', 'prune', 'prune_runtime_records', 'query', 'ranked', 'ratio', 're', 'reason', 'recent_failure', 'record', 'relation', 'repo_dirty_paths', 'repo_root', 'required_reads', 'resolved', 'results', 'reverse', 'root', 'row', 'rows', 'runbook_covers', 'runtime_request_namespace', 'scope_token', 'scoped_working_tree_paths', 'score_gap', 'scored', 'search_body', 'second_score', 'seed', 'seen_paths', 'selected', 'selected_id', 'selected_payload', 'selected_workstream', 'selection_reason', 'selection_state', 'session_id', 'session_record_signature', 'session_seed_paths', 'sessions_root', 'socket', 'source_key', 'source_kind', 'source_path', 'state', 'strong_candidate_count', 'strong_signals', 'summary_only', 'target', 'target_key', 'target_path', 'targets', 'test_rows', 'text', 'token', 'top', 'top_candidate', 'top_evidence', 'top_id', 'top_matches_judgment', 'top_payload', 'top_score', 'top_workstream', 'topology_domains', 'touched_paths', 'traceability_match_rows', 'unresolved_question_count', 'updated', 'use_working_tree', 'validation_obligation_count', 'value', 'watch_path_hits', 'working_tree_scope', 'workstream', 'workstream_entities', 'workstream_id', 'workstream_ids', 'workstream_rows'):
        try:
            globals()[name] = getter(name)
        except (AttributeError, KeyError):
            continue


_MAX_SESSION_SCOPE_PATHS = 12
_SHARED_SCOPE_RESCUE_MAX_PATHS = 3
_PATH_CATEGORY_PRIORITY = {
    "implementation": 0,
    "contract": 1,
    "build": 2,
    "component_spec": 3,
    "runbook": 4,
    "test": 5,
    "planning": 6,
    "doc": 7,
    "component_forensics": 8,
    "other": 9,
    "shared": 10,
    "unknown": 11,
}


def _intent_anchor_paths(*, repo_root: Path, intent: str, repo_dirty_paths: Sequence[str]) -> list[str]:
    extractor = globals().get("_extract_path_refs")
    if not callable(extractor):
        return []
    try:
        candidates = extractor(text=str(intent or "").strip(), repo_root=repo_root)
    except TypeError:
        return []
    if not isinstance(candidates, list):
        return []
    repo_dirty = {str(token).strip() for token in repo_dirty_paths if str(token).strip()}
    normalized: list[str] = []
    for raw in candidates:
        token = _normalize_repo_token(str(raw), repo_root=repo_root)
        if not token:
            continue
        if token in repo_dirty or (repo_root / token).exists():
            normalized.append(token)
    return _prioritize_scope_paths(_dedupe_strings(normalized), max_paths=4)


def _shared_scope_rescue_paths(repo_dirty_paths: Sequence[str]) -> list[str]:
    normalized = _dedupe_strings([str(path_ref).strip() for path_ref in repo_dirty_paths if str(path_ref).strip()])
    if not normalized:
        return []
    preferred = [
        path_ref
        for path_ref in normalized
        if str(path_ref).strip().lower() not in {
            "agents.md",
            "odylith/radar/source/index.md",
            "odylith/technical-plans/index.md",
        }
        and not str(path_ref).strip().lower().endswith("/agents.md")
    ]
    candidates = preferred or normalized
    return _prioritize_scope_paths(candidates, max_paths=_SHARED_SCOPE_RESCUE_MAX_PATHS)


def _prioritize_scope_paths(paths: Sequence[str], *, max_paths: int = _MAX_SESSION_SCOPE_PATHS) -> list[str]:
    normalized = _dedupe_strings([str(token) for token in paths if str(token).strip()])
    if len(normalized) <= max(1, int(max_paths)):
        return list(normalized)
    ranked: list[tuple[tuple[int, int, int, int, str], str]] = []
    for index, path_ref in enumerate(normalized):
        profile = _path_signal_profile(path_ref)
        category = str(profile.get("category", "other")).strip() or "other"
        shared = bool(profile.get("shared"))
        weight = int(profile.get("weight", 0) or 0)
        ranked.append(
            (
                (
                    1 if shared else 0,
                    -weight,
                    int(_PATH_CATEGORY_PRIORITY.get(category, 99)),
                    index,
                    str(path_ref),
                ),
                str(path_ref),
            )
        )
    ranked.sort(key=lambda item: item[0])
    limit = max(1, int(max_paths))
    return [path_ref for _key, path_ref in ranked[:limit]]


def _compact_architecture_audit_for_packet(audit: Mapping[str, Any], *, packet_state: str) -> dict[str, Any]:
    summary_only = str(packet_state or "").strip() == "gated_broad_scope"
    coverage = dict(audit.get("coverage", {})) if isinstance(audit.get("coverage"), Mapping) else {}
    benchmark_summary = (
        dict(audit.get("benchmark_summary", {})) if isinstance(audit.get("benchmark_summary"), Mapping) else {}
    )
    execution_hint = dict(audit.get("execution_hint", {})) if isinstance(audit.get("execution_hint"), Mapping) else {}
    blast_radius = dict(audit.get("blast_radius", {})) if isinstance(audit.get("blast_radius"), Mapping) else {}
    authority_graph = dict(audit.get("authority_graph", {})) if isinstance(audit.get("authority_graph"), Mapping) else {}
    historical_evidence = dict(audit.get("historical_evidence", {})) if isinstance(audit.get("historical_evidence"), Mapping) else {}
    contract_touchpoint_count = (
        int(audit.get("contract_touchpoint_count", 0) or 0)
        if audit.get("contract_touchpoint_count") not in (None, "")
        else len(audit.get("contract_touchpoints", []))
        if isinstance(audit.get("contract_touchpoints"), list)
        else 0
    )
    operator_consequence_count = (
        int(audit.get("operator_consequence_count", 0) or 0)
        if audit.get("operator_consequence_count") not in (None, "")
        else len(audit.get("operator_consequences", []))
        if isinstance(audit.get("operator_consequences"), list)
        else 0
    )
    validation_obligation_count = (
        int(audit.get("validation_obligation_count", 0) or 0)
        if audit.get("validation_obligation_count") not in (None, "")
        else len(audit.get("validation_obligations", []))
        if isinstance(audit.get("validation_obligations"), list)
        else 0
    )
    unresolved_question_count = (
        int(audit.get("unresolved_question_count", 0) or 0)
        if audit.get("unresolved_question_count") not in (None, "")
        else len(audit.get("unresolved_questions", []))
        if isinstance(audit.get("unresolved_questions"), list)
        else 0
    )
    payload = {
        "resolved": bool(audit.get("resolved")),
        "changed_paths": [str(token).strip() for token in audit.get("changed_paths", [])[:1] if str(token).strip()]
        if isinstance(audit.get("changed_paths"), list)
        else [],
        "packet_state": str(packet_state or "").strip(),
        "required_reads": [str(token).strip() for token in audit.get("required_reads", [])[:1] if str(token).strip()]
        if isinstance(audit.get("required_reads"), list)
        else [],
        "required_read_count": len(audit.get("required_reads", [])) if isinstance(audit.get("required_reads"), list) else 0,
        "diagram_watch_gap_count": len(audit.get("diagram_watch_gaps", [])) if isinstance(audit.get("diagram_watch_gaps"), list) else 0,
        "topology_domain_ids": [
            str(row.get("domain_id", "")).strip()
            for row in audit.get("topology_domains", [])[:2]
            if isinstance(row, Mapping) and str(row.get("domain_id", "")).strip()
        ]
        if isinstance(audit.get("topology_domains"), list)
        else [],
        "linked_component_count": len(audit.get("linked_components", [])) if isinstance(audit.get("linked_components"), list) else 0,
        "linked_component_ids": [
            str(row.get("component_id", "")).strip()
            for row in audit.get("linked_components", [])[:2]
            if isinstance(row, Mapping) and str(row.get("component_id", "")).strip()
        ]
        if isinstance(audit.get("linked_components"), list)
        else [],
        "linked_diagram_count": len(audit.get("linked_diagrams", [])) if isinstance(audit.get("linked_diagrams"), list) else 0,
        "linked_diagram_ids": [
            str(row.get("diagram_id", "")).strip()
            for row in audit.get("linked_diagrams", [])[:2]
            if isinstance(row, Mapping) and str(row.get("diagram_id", "")).strip()
        ]
        if isinstance(audit.get("linked_diagrams"), list)
        else [],
        "contract_touchpoint_count": contract_touchpoint_count,
        "coverage": {
            "confidence_tier": str(coverage.get("confidence_tier", "")).strip(),
            "score": int(coverage.get("score", 0) or 0),
            "path_ratio": float(dict(coverage.get("path_coverage", {})).get("ratio", 0.0) or 0.0)
            if isinstance(coverage.get("path_coverage"), Mapping)
            else 0.0,
            "diagram_ratio": float(dict(coverage.get("diagram_coverage", {})).get("ratio", 0.0) or 0.0)
            if isinstance(coverage.get("diagram_coverage"), Mapping)
            else 0.0,
            "contract_ratio": float(dict(coverage.get("contract_coverage", {})).get("ratio", 0.0) or 0.0)
            if isinstance(coverage.get("contract_coverage"), Mapping)
            else 0.0,
            "ownership_ratio": float(dict(coverage.get("ownership_coverage", {})).get("ratio", 0.0) or 0.0)
            if isinstance(coverage.get("ownership_coverage"), Mapping)
            else 0.0,
            "unresolved_edge_count": int(coverage.get("unresolved_edge_count", 0) or 0),
        }
        if coverage
        else {},
        "blast_radius": {
            "components": int(dict(blast_radius.get("counts", {})).get("components", 0) or 0)
            if isinstance(blast_radius.get("counts"), Mapping)
            else 0,
            "diagrams": int(dict(blast_radius.get("counts", {})).get("diagrams", 0) or 0)
            if isinstance(blast_radius.get("counts"), Mapping)
            else 0,
            "docs": int(dict(blast_radius.get("counts", {})).get("docs", 0) or 0)
            if isinstance(blast_radius.get("counts"), Mapping)
            else 0,
            "workstreams": int(dict(blast_radius.get("counts", {})).get("workstreams", 0) or 0)
            if isinstance(blast_radius.get("counts"), Mapping)
            else 0,
            "bugs": int(dict(blast_radius.get("counts", {})).get("bugs", 0) or 0)
            if isinstance(blast_radius.get("counts"), Mapping)
            else 0,
        }
        if blast_radius
        else {},
        "execution_hint": {
            "mode": str(execution_hint.get("mode", "")).strip(),
            "model": str(execution_hint.get("model", "")).strip(),
            "reasoning_effort": str(execution_hint.get("reasoning_effort", "")).strip(),
            "fanout": str(execution_hint.get("fanout", "")).strip(),
            "risk_tier": str(execution_hint.get("risk_tier", "")).strip(),
        }
        if execution_hint
        else {},
        "benchmark_summary": {
            "matched_case_count": int(benchmark_summary.get("matched_case_count", 0) or 0),
            "satisfied_case_count": int(benchmark_summary.get("satisfied_case_count", 0) or 0),
            "drift_case_count": len(benchmark_summary.get("drift_case_ids", []))
            if isinstance(benchmark_summary.get("drift_case_ids"), list)
            else 0,
        }
        if benchmark_summary
        else {},
        "authority_graph": {
            "nodes": int(dict(authority_graph.get("counts", {})).get("nodes", 0) or 0)
            if isinstance(authority_graph.get("counts"), Mapping)
            else 0,
            "edges": int(dict(authority_graph.get("counts", {})).get("edges", 0) or 0)
            if isinstance(authority_graph.get("counts"), Mapping)
            else 0,
            "traceability_edges": int(dict(authority_graph.get("counts", {})).get("traceability_edges", 0) or 0)
            if isinstance(authority_graph.get("counts"), Mapping)
            else 0,
        }
        if authority_graph
        else {},
        "historical_evidence": {
            "bug_count": len(historical_evidence.get("bugs", [])) if isinstance(historical_evidence.get("bugs"), list) else 0,
            "runbook_count": len(historical_evidence.get("runbooks", [])) if isinstance(historical_evidence.get("runbooks"), list) else 0,
            "adr_count": len(historical_evidence.get("adrs", [])) if isinstance(historical_evidence.get("adrs"), list) else 0,
            "workstream_count": len(historical_evidence.get("workstreams", [])) if isinstance(historical_evidence.get("workstreams"), list) else 0,
        }
        if historical_evidence
        else {},
        "full_scan_recommended": bool(audit.get("full_scan_recommended")),
        "full_scan_reason": str(audit.get("full_scan_reason", "")).strip(),
    }
    if summary_only:
        payload["operator_consequence_count"] = operator_consequence_count
        payload["validation_obligation_count"] = validation_obligation_count
        payload["unresolved_question_count"] = unresolved_question_count
        return payload
    payload["operator_consequence_count"] = operator_consequence_count
    payload["validation_obligation_count"] = validation_obligation_count
    payload["unresolved_question_count"] = unresolved_question_count
    return payload

def _compact_packet_level_architecture_audit(audit: Mapping[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {
        "resolved": bool(audit.get("resolved")),
    }
    changed_paths = _normalized_string_list(audit.get("changed_paths"))
    if changed_paths:
        compact["changed_paths"] = changed_paths[:2]

    required_reads = _normalized_string_list(audit.get("required_reads"))
    if required_reads:
        compact["required_reads"] = required_reads[:4]
        if len(required_reads) > 4:
            compact["required_read_count"] = len(required_reads)
    elif int(audit.get("required_read_count", 0) or 0) > 0:
        compact["required_read_count"] = int(audit.get("required_read_count", 0) or 0)

    authority_graph_counts = (
        dict(dict(audit.get("authority_graph", {})).get("counts", {}))
        if isinstance(audit.get("authority_graph"), Mapping)
        and isinstance(dict(audit.get("authority_graph", {})).get("counts"), Mapping)
        else {}
    )
    compact_authority_counts = {
        key: int(value or 0)
        for key, value in authority_graph_counts.items()
        if str(key).strip() in {"edges", "traceability_edges"} and int(value or 0) > 0
    }
    if compact_authority_counts:
        compact["authority_graph"] = {"counts": compact_authority_counts}

    for key in (
        "contract_touchpoint_count",
        "validation_obligation_count",
    ):
        value = int(audit.get(key, 0) or 0)
        if value > 0:
            compact[key] = value

    coverage = dict(audit.get("coverage", {})) if isinstance(audit.get("coverage"), Mapping) else {}
    compact_coverage = {
        key: value
        for key, value in {
            "confidence_tier": str(coverage.get("confidence_tier", "")).strip(),
        }.items()
        if value not in ("", [], {}, None, 0)
    }
    if compact_coverage:
        compact["coverage"] = compact_coverage

    execution_hint = dict(audit.get("execution_hint", {})) if isinstance(audit.get("execution_hint"), Mapping) else {}
    compact_execution_hint = {
        key: value
        for key, value in {
            "mode": str(execution_hint.get("mode", "")).strip(),
            "fanout": str(execution_hint.get("fanout", "")).strip(),
            "risk_tier": str(execution_hint.get("risk_tier", "")).strip(),
        }.items()
        if value not in ("", [], {}, None)
    }
    if compact_execution_hint:
        compact["execution_hint"] = compact_execution_hint

    if bool(audit.get("full_scan_recommended")):
        compact["full_scan_recommended"] = True
    full_scan_reason = str(audit.get("full_scan_reason", "")).strip()
    if full_scan_reason:
        compact["full_scan_reason"] = full_scan_reason
    fallback_scan = dict(audit.get("fallback_scan", {})) if isinstance(audit.get("fallback_scan"), Mapping) else {}
    compact_fallback_scan = {
        key: value
        for key, value in {
            "performed": bool(fallback_scan.get("performed")),
            "reason": full_scan_reason or str(fallback_scan.get("reason", "")).strip(),
        }.items()
        if value not in ("", [], {}, None, False)
    }
    if isinstance(fallback_scan.get("results"), list):
        results = [
            {
                key: value
                for key, value in {
                    "path": str(row.get("path", "")).strip(),
                    "kind": str(row.get("kind", "")).strip(),
                }.items()
                if value not in ("", [], {}, None)
            }
            for row in fallback_scan.get("results", [])[:4]
            if isinstance(row, Mapping) and str(row.get("path", "")).strip()
        ]
        if results:
            compact_fallback_scan["results"] = results
    if compact_fallback_scan:
        compact["fallback_scan"] = compact_fallback_scan
    return compact


def _path_prefixes(path_ref: str) -> tuple[str, ...]:
    normalized = str(path_ref or "").strip().strip("/")
    if not normalized:
        return ()
    parts = [part for part in normalized.split("/") if part]
    return tuple("/".join(parts[: index + 1]) for index in range(len(parts)))


def _selector_projection_signature(*, repo_root: Path) -> str:
    root = Path(repo_root).resolve()
    snapshot = projection_snapshot_path(repo_root=root)
    return _path_fingerprint(snapshot) or "projection_snapshot:missing"


def _selector_cache_fetch(
    *,
    repo_root: Path,
    namespace: str,
    payload: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, str, str]:
    root = Path(repo_root).resolve()
    cache_key = f"{root}:selector:{str(namespace).strip()}"
    cache_signature = odylith_context_cache.fingerprint_payload(
        {
            "projection_signature": _selector_projection_signature(repo_root=root),
            "namespace": str(namespace).strip(),
            **dict(payload),
        }
    )
    cached = _PROCESS_PATH_SCOPE_CACHE.get(cache_key)
    if cached is None or cached[0] != cache_signature:
        return None, cache_key, cache_signature
    return dict(cached[1]), cache_key, cache_signature


def _selector_cache_store(
    *,
    cache_key: str,
    cache_signature: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    stored = {
        key: value
        for key, value in dict(payload).items()
    }
    _PROCESS_PATH_SCOPE_CACHE[cache_key] = (cache_signature, stored)
    return stored


def _path_row_match_index(
    *,
    repo_root: Path,
    namespace: str,
    rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], bool]:
    cached, cache_key, cache_signature = _selector_cache_fetch(
        repo_root=repo_root,
        namespace=f"{namespace}:index",
        payload={"row_count": len(rows)},
    )
    if cached is not None:
        return cached, True
    exact: dict[str, list[dict[str, Any]]] = {}
    prefix: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        target = str(row.get("target_path", "")).strip()
        if not target:
            continue
        row_payload = dict(row)
        exact.setdefault(target, []).append(row_payload)
        for prefix_token in _path_prefixes(target):
            prefix.setdefault(prefix_token, []).append(row_payload)
    payload = {"exact": exact, "prefix": prefix}
    return _selector_cache_store(
        cache_key=cache_key,
        cache_signature=cache_signature,
        payload=payload,
    ), False


def _path_index_row_key(row: Mapping[str, Any]) -> str:
    return "|".join(
        [
            str(row.get("component_id", "")).strip(),
            str(row.get("source_id", "")).strip().upper(),
            str(row.get("source_kind", "")).strip(),
            str(row.get("target_path", "")).strip(),
        ]
    )


def _candidate_rows_for_changed_paths(
    *,
    changed_paths: Sequence[str],
    index_payload: Mapping[str, Any],
) -> list[dict[str, Any]]:
    exact = dict(index_payload.get("exact", {})) if isinstance(index_payload.get("exact"), Mapping) else {}
    prefix = dict(index_payload.get("prefix", {})) if isinstance(index_payload.get("prefix"), Mapping) else {}
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path_ref in changed_paths:
        normalized = str(path_ref or "").strip()
        if not normalized:
            continue
        for row in prefix.get(normalized, []):
            if not isinstance(row, Mapping):
                continue
            row_key = _path_index_row_key(row)
            if row_key in seen:
                continue
            seen.add(row_key)
            selected.append(dict(row))
        for ancestor in _path_prefixes(normalized)[:-1]:
            for row in exact.get(ancestor, []):
                if not isinstance(row, Mapping):
                    continue
                row_key = _path_index_row_key(row)
                if row_key in seen:
                    continue
                seen.add(row_key)
                selected.append(dict(row))
    return selected


def _component_path_match_rows(component_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    match_rows = _load_component_match_rows_from_components(component_rows)
    rows: list[dict[str, Any]] = []
    for row in match_rows:
        component_id = str(row.get("component_id", "")).strip()
        if not component_id:
            continue
        candidates = [
            str(row.get("spec_ref", "")).strip(),
            *[str(token).strip() for token in row.get("path_prefixes", []) if str(token).strip()],
        ]
        for target_path in _dedupe_strings(candidates):
            rows.append(
                {
                    "component_id": component_id,
                    "target_path": target_path,
                }
            )
    return rows

def _workstream_selection(
    *,
    connection: Any,
    candidates: Sequence[Mapping[str, Any]],
    explicit_workstream: str = "",
    judgment_hint: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    candidate_rows = [dict(candidate) for candidate in candidates]
    candidate_by_id = {
        str(row.get("entity_id", "")).strip().upper(): row
        for row in candidate_rows
        if str(row.get("entity_id", "")).strip()
    }

    def _selection_payload(
        *,
        state: str,
        reason: str,
        selected_workstream: Mapping[str, Any] | None,
        top_candidate: Mapping[str, Any] | None,
        score_gap: int | None,
        confidence: str,
        ambiguity_class: str = "",
    ) -> dict[str, Any]:
        selected_id = (
            str(selected_workstream.get("entity_id", "")).strip().upper()
            if isinstance(selected_workstream, Mapping)
            else ""
        )
        top_id = (
            str(top_candidate.get("entity_id", "")).strip().upper()
            if isinstance(top_candidate, Mapping)
            else ""
        )
        selected_payload = (
            dict(selected_workstream)
            if isinstance(selected_workstream, Mapping) and selected_id
            else {}
        )
        top_payload = dict(top_candidate) if isinstance(top_candidate, Mapping) and top_id else {}
        competing_candidates = [
            dict(row)
            for row in candidate_rows
            if str(row.get("entity_id", "")).strip().upper() not in {selected_id, top_id}
        ][:3]
        return {
            "state": state,
            "reason": reason,
            "why_selected": reason,
            "selected_workstream": selected_payload,
            "top_candidate": top_payload,
            "score_gap": score_gap,
            "confidence": confidence,
            "candidate_count": len(candidate_rows),
            "ambiguity_class": ambiguity_class,
            "strong_candidate_count": sum(
                1
                for row in candidate_rows
                if int(dict(row.get("evidence", {})).get("strong_signal_count", 0) or 0) > 0
            ),
            "competing_candidates": competing_candidates,
        }

    explicit = str(explicit_workstream or "").strip().upper()
    top_candidate = dict(candidate_rows[0]) if candidate_rows else {}
    if explicit:
        selected = candidate_by_id.get(explicit)
        if selected is None:
            explicit_entity = _entity_by_kind_id(connection, kind="workstream", entity_id=explicit)
            if explicit_entity is not None:
                selected = _base_workstream_candidate(explicit_entity)
                selected["selection_reason"] = "explicit workstream override"
        if selected is not None:
            return _selection_payload(
                state="explicit",
                reason=f"Using explicit workstream override `{explicit}`.",
                selected_workstream=selected,
                top_candidate=top_candidate,
                score_gap=None,
                confidence="explicit",
                ambiguity_class="explicit",
            )
        return _selection_payload(
            state="none",
            reason=f"Explicit workstream `{explicit}` does not resolve in the runtime projection store.",
            selected_workstream={},
            top_candidate=top_candidate,
            score_gap=None,
            confidence="none",
            ambiguity_class="explicit_missing",
        )
    if not candidate_rows:
        return _selection_payload(
            state="none",
            reason="No workstream evidence matched the current changed-path set.",
            selected_workstream={},
            top_candidate={},
            score_gap=None,
            confidence="none",
            ambiguity_class="no_candidates",
        )
    top = dict(candidate_rows[0])
    top_evidence = dict(top.get("evidence", {})) if isinstance(top.get("evidence"), Mapping) else {}
    top_score = int(top_evidence.get("score", 0) or 0)
    second_score = (
        int(dict(candidate_rows[1].get("evidence", {})).get("score", 0) or 0)
        if len(candidate_rows) > 1 and isinstance(candidate_rows[1], Mapping)
        else 0
    )
    score_gap = top_score - second_score
    broad_only = bool(top_evidence.get("broad_only"))
    strong_signals = int(top_evidence.get("strong_signal_count", 0) or 0)
    judgment = dict(judgment_hint) if isinstance(judgment_hint, Mapping) else {}
    hinted_workstream = _workstream_token(str(judgment.get("workstream_id", "")).strip())
    top_workstream = _workstream_token(str(top.get("entity_id", "")).strip())
    top_matches_judgment = bool(
        hinted_workstream
        and top_workstream
        and hinted_workstream == top_workstream
        and _workstream_has_path_signal(top)
    )
    judgment_reason = str(judgment.get("reason", "")).strip()
    if top_score < _WORKSTREAM_SELECTION_CONFIDENT_SCORE:
        if top_matches_judgment:
            return _selection_payload(
                state="inferred_confident",
                reason=(
                    f"{judgment_reason} Current evidence is lighter than ideal, but it still aligns with the same governed slice."
                    if judgment_reason
                    else "Durable slice memory confirms the same workstream despite lighter current evidence."
                ),
                selected_workstream=top,
                top_candidate=top,
                score_gap=score_gap,
                confidence=str(judgment.get("confidence", "")).strip() or "medium",
                ambiguity_class="judgment_memory_confirmed",
            )
        return _selection_payload(
            state="ambiguous",
            reason=f"Top candidate `{top.get('entity_id', '')}` is too weak to auto-trust.",
            selected_workstream={},
            top_candidate=top,
            score_gap=score_gap,
            confidence="low",
            ambiguity_class="low_signal",
        )
    if broad_only and strong_signals == 0:
        return _selection_payload(
            state="ambiguous",
            reason=f"Top workstream candidate `{top.get('entity_id', '')}` is driven only by broad shared-path evidence.",
            selected_workstream={},
            top_candidate=top,
            score_gap=score_gap,
            confidence="low",
            ambiguity_class="broad_shared_only",
        )
    if len(candidate_rows) > 1 and second_score > 0 and score_gap < _WORKSTREAM_SELECTION_GAP_MIN:
        ambiguity_class = "close_competition"
        strong_candidate_count = sum(
            1
            for row in candidate_rows
            if int(dict(row.get("evidence", {})).get("strong_signal_count", 0) or 0) > 0
        )
        if int(top_evidence.get("strong_signal_count", 0) or 0) > 0 and strong_candidate_count > 1:
            ambiguity_class = "historical_fanout"
        if top_matches_judgment:
            return _selection_payload(
                state="inferred_confident",
                reason=(
                    f"{judgment_reason} Current evidence still has nearby competitors, but retained slice memory confirms the same workstream."
                    if judgment_reason
                    else "Durable slice memory confirms the same workstream despite nearby competing candidates."
                ),
                selected_workstream=top,
                top_candidate=top,
                score_gap=score_gap,
                confidence=str(judgment.get("confidence", "")).strip() or "medium",
                ambiguity_class="judgment_memory_confirmed",
            )
        return _selection_payload(
            state="ambiguous",
            reason=(
                "Multiple historically related workstreams retain near-identical strong path evidence; pin the active slice explicitly."
                if ambiguity_class == "historical_fanout"
                else "Competing workstream candidates are too close in evidence score to choose safely."
            ),
            selected_workstream={},
            top_candidate=top,
            score_gap=score_gap,
            confidence="medium",
            ambiguity_class=ambiguity_class,
        )
    return _selection_payload(
        state="inferred_confident",
        reason=str(top_evidence.get("summary", "")).strip() or "Strong deterministic workstream evidence won.",
        selected_workstream=top,
        top_candidate=top,
        score_gap=score_gap,
        confidence="high" if strong_signals > 0 else "medium",
        ambiguity_class="resolved",
    )

def _bug_excerpt(text: str, field: str) -> str:
    match = re.search(rf"-?\s*{re.escape(field)}:\s*(.+)", str(text or ""), re.MULTILINE)
    return str(match.group(1)).strip() if match is not None else ""

def _session_record_path(*, repo_root: Path, session_id: str) -> Path:
    token = re.sub(r"[^A-Za-z0-9._-]+", "-", str(session_id or "").strip()).strip("-") or f"codex-{os.getpid()}"
    return (sessions_root(repo_root=repo_root) / f"{token}.json").resolve()

def _bootstrap_record_path(*, repo_root: Path, session_id: str) -> Path:
    token = re.sub(r"[^A-Za-z0-9._-]+", "-", str(session_id or "").strip()).strip("-") or f"codex-{os.getpid()}"
    return (bootstraps_root(repo_root=repo_root) / f"{token}.json").resolve()

def _parse_iso_utc(value: str) -> dt.datetime | None:
    token = str(value or "").strip()
    if not token:
        return None
    normalized = token.replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)

def _normalize_claim_mode(value: str) -> str:
    token = str(value or "").strip().lower()
    return token if token in _SESSION_CLAIM_MODES else "shared"

def _lease_expires_utc(*, lease_seconds: int) -> str:
    expires = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=max(60, int(lease_seconds)))
    return expires.replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _is_session_expired(payload: Mapping[str, Any], *, now: dt.datetime) -> bool:
    lease_expires = _parse_iso_utc(str(payload.get("lease_expires_utc", "")).strip())
    if lease_expires is not None and lease_expires <= now:
        return True
    updated = _parse_iso_utc(str(payload.get("updated_utc", "")).strip())
    age_seconds = (now - updated).total_seconds() if updated is not None else float("inf")
    return age_seconds > SESSION_STALE_SECONDS

def _load_session_state(
    *,
    repo_root: Path,
    session_id: str,
    include_stale: bool = False,
) -> dict[str, Any] | None:
    payload = odylith_context_cache.read_json_object(_session_record_path(repo_root=repo_root, session_id=session_id))
    if not payload:
        return None
    if not include_stale and _is_session_expired(payload, now=dt.datetime.now(dt.timezone.utc)):
        return None
    return payload

def _resolve_changed_path_scope_context(
    *,
    repo_root: Path,
    explicit_paths: Sequence[str],
    use_working_tree: bool,
    working_tree_scope: str,
    session_id: str = "",
    claimed_paths: Sequence[str] = (),
    intent: str = "",
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    explicit = _normalize_changed_path_list(repo_root=root, values=explicit_paths)
    explicit_claims = _normalize_changed_path_list(repo_root=root, values=claimed_paths)
    scope_token = str(working_tree_scope or "repo").strip().lower()
    if scope_token not in {"repo", "session"}:
        scope_token = "repo"
    namespace = runtime_request_namespace(
        repo_root=root,
        changed_paths=explicit,
        session_id=session_id,
        claimed_paths=explicit_claims,
        working_tree_scope=scope_token,
    )
    session_record_signature = (
        _path_fingerprint(_session_record_path(repo_root=root, session_id=session_id))
        if str(session_id or "").strip()
        else ""
    )
    cache_key = f"{root}:path_scope:{str(namespace.get('request_namespace', '')).strip() or 'default'}"
    cache_signature = odylith_context_cache.fingerprint_payload(
        {
            "use_working_tree": bool(use_working_tree),
            "working_tree_scope": scope_token,
            "intent": str(intent or "").strip(),
            "session_record_signature": session_record_signature,
            "workspace_activity": _workspace_activity_fingerprint(repo_root=root) if use_working_tree else "",
        }
    )
    cached_scope = _PROCESS_PATH_SCOPE_CACHE.get(cache_key)
    if cached_scope is not None and cached_scope[0] == cache_signature:
        return {
            key: list(value) if isinstance(value, list) else value
            for key, value in cached_scope[1].items()
        }
    repo_dirty_paths = (
        _prioritize_scope_paths(
            governance.collect_meaningful_changed_paths(repo_root=root, changed_paths=(), include_git=True),
        )
        if use_working_tree
        else []
    )
    intent_anchor_paths = _intent_anchor_paths(
        repo_root=root,
        intent=intent,
        repo_dirty_paths=repo_dirty_paths,
    )
    existing_session = _load_session_state(repo_root=root, session_id=session_id, include_stale=False) if session_id else None
    session_seed_paths = _dedupe_strings(
        [
            *explicit,
            *explicit_claims,
            *intent_anchor_paths,
            *(
                [str(token) for token in existing_session.get("explicit_paths", [])]
                if isinstance(existing_session, Mapping) and isinstance(existing_session.get("explicit_paths"), list)
                else []
            ),
            *(
                [str(token) for token in existing_session.get("claimed_paths", [])]
                if isinstance(existing_session, Mapping) and isinstance(existing_session.get("claimed_paths"), list)
                else []
            ),
            *(
                [str(token) for token in existing_session.get("analysis_paths", [])]
                if isinstance(existing_session, Mapping) and isinstance(existing_session.get("analysis_paths"), list)
                else []
            ),
        ]
    )
    if not use_working_tree:
        scoped_working_tree_paths: list[str] = []
        degraded = False
        scope_rescue_mode = ""
    elif scope_token == "repo":
        scoped_working_tree_paths = _prioritize_scope_paths(repo_dirty_paths)
        degraded = False
        scope_rescue_mode = ""
    elif session_seed_paths:
        scoped_working_tree_paths = _prioritize_scope_paths([
            path_ref
            for path_ref in repo_dirty_paths
            if any(
                _path_touches_watch(changed_path=path_ref, watch_path=seed)
                or _path_touches_watch(changed_path=seed, watch_path=path_ref)
                for seed in session_seed_paths
            )
        ])
        degraded = False
        scope_rescue_mode = "intent_seed" if intent_anchor_paths else ""
    else:
        non_shared_dirty_paths = [
            path_ref
            for path_ref in repo_dirty_paths
            if not bool(_path_signal_profile(path_ref).get("shared"))
        ]
        if non_shared_dirty_paths:
            scoped_working_tree_paths = _prioritize_scope_paths(non_shared_dirty_paths)
            degraded = False
            scope_rescue_mode = ""
        else:
            scoped_working_tree_paths = _shared_scope_rescue_paths(repo_dirty_paths)
            degraded = not bool(scoped_working_tree_paths)
            scope_rescue_mode = "shared_only_seed" if scoped_working_tree_paths else ""
    analysis_paths = _dedupe_strings([*explicit, *intent_anchor_paths, *scoped_working_tree_paths])
    resolved = {
        "explicit_paths": explicit,
        "explicit_claim_paths": explicit_claims,
        "intent_anchor_paths": intent_anchor_paths,
        "repo_dirty_paths": repo_dirty_paths,
        "scoped_working_tree_paths": _dedupe_strings(scoped_working_tree_paths),
        "analysis_paths": analysis_paths,
        "scope_rescue_mode": scope_rescue_mode,
        "working_tree_scope": scope_token,
        "working_tree_scope_degraded": degraded,
        "session_seed_paths": session_seed_paths,
    }
    _PROCESS_PATH_SCOPE_CACHE[cache_key] = (cache_signature, resolved)
    return {
        key: list(value) if isinstance(value, list) else value
        for key, value in resolved.items()
    }

def _claim_sets(
    *,
    claimed_workstream: str,
    generated_surfaces: Sequence[str],
    auto_claim_paths: Sequence[str],
    claimed_paths: Sequence[str],
) -> dict[str, list[str]]:
    normalized_workstream = str(claimed_workstream or "").strip().upper()
    return {
        "claimed_workstreams": [normalized_workstream] if normalized_workstream else [],
        "claimed_paths": _dedupe_strings([*map(str, auto_claim_paths), *map(str, claimed_paths)]),
        "claimed_surfaces": _dedupe_strings([str(token) for token in generated_surfaces]),
    }

def list_session_states(
    *,
    repo_root: Path,
    include_stale: bool = False,
    prune: bool = True,
) -> list[dict[str, Any]]:
    if prune and not include_stale:
        prune_runtime_records(repo_root=repo_root)
    root = sessions_root(repo_root=repo_root)
    if not root.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    now = dt.datetime.now(dt.timezone.utc)
    for path in sorted(root.glob("*.json")):
        payload = odylith_context_cache.read_json_object(path)
        if not payload:
            continue
        if not include_stale and _is_session_expired(payload, now=now):
            continue
        claim_sets = _claim_sets(
            claimed_workstream=str(payload.get("workstream", "")).strip().upper(),
            generated_surfaces=payload.get("generated_surfaces", []) if isinstance(payload.get("generated_surfaces"), list) else [],
            auto_claim_paths=[],
            claimed_paths=payload.get("claimed_paths", []) if isinstance(payload.get("claimed_paths"), list) else [],
        )
        rows.append(
            {
                "session_id": str(payload.get("session_id", "")).strip() or path.stem,
                "updated_utc": str(payload.get("updated_utc", "")).strip(),
                "workstream": str(payload.get("workstream", "")).strip().upper(),
                "intent": str(payload.get("intent", "")).strip(),
                "touched_paths": _dedupe_strings([str(item) for item in payload.get("touched_paths", [])])
                if isinstance(payload.get("touched_paths"), list)
                else [],
                "explicit_paths": _dedupe_strings([str(item) for item in payload.get("explicit_paths", [])])
                if isinstance(payload.get("explicit_paths"), list)
                else [],
                "repo_dirty_paths": _dedupe_strings([str(item) for item in payload.get("repo_dirty_paths", [])])
                if isinstance(payload.get("repo_dirty_paths"), list)
                else [],
                "analysis_paths": _dedupe_strings([str(item) for item in payload.get("analysis_paths", [])])
                if isinstance(payload.get("analysis_paths"), list)
                else [],
                "generated_surfaces": _dedupe_strings([str(item) for item in payload.get("generated_surfaces", [])])
                if isinstance(payload.get("generated_surfaces"), list)
                else [],
                "claim_mode": _normalize_claim_mode(str(payload.get("claim_mode", "")).strip()),
                "lease_expires_utc": str(payload.get("lease_expires_utc", "")).strip(),
                "claimed_workstreams": claim_sets["claimed_workstreams"],
                "claimed_paths": claim_sets["claimed_paths"],
                "claimed_surfaces": claim_sets["claimed_surfaces"],
                "working_tree_scope": str(payload.get("working_tree_scope", "")).strip(),
                "selection_state": str(payload.get("selection_state", "")).strip(),
                "selection_reason": str(payload.get("selection_reason", "")).strip(),
                "branch_name": str(payload.get("branch_name", "")).strip(),
                "head_oid": str(payload.get("head_oid", "")).strip(),
                "hostname": str(payload.get("hostname", "")).strip(),
                "pid": int(payload.get("pid", 0) or 0),
            }
        )
    return rows

def register_session_state(
    *,
    repo_root: Path,
    session_id: str,
    workstream: str,
    touched_paths: Sequence[str],
    explicit_paths: Sequence[str],
    repo_dirty_paths: Sequence[str],
    analysis_paths: Sequence[str],
    generated_surfaces: Sequence[str],
    intent: str,
    claim_mode: str = "shared",
    selection_state: str = "",
    selection_reason: str = "",
    working_tree_scope: str = "",
    auto_claim_paths: Sequence[str] = (),
    claimed_paths: Sequence[str] = (),
    lease_seconds: int = 15 * 60,
) -> dict[str, Any]:
    prune_runtime_records(repo_root=repo_root)
    claims = _claim_sets(
        claimed_workstream=workstream,
        generated_surfaces=generated_surfaces,
        auto_claim_paths=auto_claim_paths,
        claimed_paths=claimed_paths,
    )
    record = {
        "session_id": re.sub(r"[^A-Za-z0-9._-]+", "-", str(session_id or "").strip()).strip("-") or f"codex-{os.getpid()}",
        "updated_utc": _utc_now(),
        "workstream": str(workstream or "").strip().upper(),
        "intent": str(intent or "").strip(),
        "touched_paths": _dedupe_strings([str(token) for token in touched_paths]),
        "explicit_paths": _dedupe_strings([str(token) for token in explicit_paths]),
        "repo_dirty_paths": _dedupe_strings([str(token) for token in repo_dirty_paths]),
        "analysis_paths": _dedupe_strings([str(token) for token in analysis_paths]),
        "generated_surfaces": _dedupe_strings([str(token) for token in generated_surfaces]),
        "claim_mode": _normalize_claim_mode(claim_mode),
        "lease_expires_utc": _lease_expires_utc(lease_seconds=int(lease_seconds)),
        "selection_state": str(selection_state or "").strip(),
        "selection_reason": str(selection_reason or "").strip(),
        "working_tree_scope": str(working_tree_scope or "").strip().lower(),
        "claimed_workstreams": claims["claimed_workstreams"],
        "claimed_paths": claims["claimed_paths"],
        "claimed_surfaces": claims["claimed_surfaces"],
        "branch_name": _git_branch_name(repo_root=repo_root),
        "head_oid": _git_head_oid(repo_root=repo_root),
        "hostname": socket.gethostname(),
        "pid": os.getpid(),
    }
    target = _session_record_path(repo_root=repo_root, session_id=str(record["session_id"]))
    odylith_context_cache.write_json_if_changed(
        repo_root=repo_root,
        path=target,
        payload=record,
        lock_key=str(target),
    )
    return record

def _collect_impacted_components(
    connection: Any,
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    return_diagnostics: bool = False,
) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], dict[str, Any]]:
    normalized_changed_paths = _dedupe_strings(
        [
            _normalize_repo_token(str(path_ref).strip(), repo_root=repo_root)
            for path_ref in changed_paths
            if str(path_ref).strip()
        ]
    )
    diagnostics = {
        "component_fast_selector_used": False,
        "component_selector_cache_hit": False,
        "component_selector_candidate_row_count": 0,
    }
    if not normalized_changed_paths:
        return ([], diagnostics) if return_diagnostics else []
    component_rows = _cached_projection_rows(
        repo_root=repo_root,
        cache_name="components_full_rows",
        loader=lambda: [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM components"
            ).fetchall()
        ],
    )
    match_rows = _cached_projection_rows(
        repo_root=repo_root,
        cache_name="component_path_match_rows",
        loader=lambda: _component_path_match_rows(component_rows),
    )
    index_payload, cache_hit = _path_row_match_index(
        repo_root=repo_root,
        namespace="component_path_match_rows",
        rows=match_rows,
    )
    candidate_rows = _candidate_rows_for_changed_paths(
        changed_paths=normalized_changed_paths,
        index_payload=index_payload,
    )
    if not candidate_rows:
        candidate_rows = [dict(row) for row in match_rows]
    diagnostics["component_fast_selector_used"] = True
    diagnostics["component_selector_cache_hit"] = bool(cache_hit)
    diagnostics["component_selector_candidate_row_count"] = len(candidate_rows)
    matched_id_set: set[str] = set()
    for row in candidate_rows:
        component_id = str(row.get("component_id", "")).strip()
        target_path = str(row.get("target_path", "")).strip()
        if not component_id or not target_path:
            continue
        if any(
            _normalized_path_match_type(changed_path=path_ref, target_path=target_path)
            for path_ref in normalized_changed_paths
        ):
            matched_id_set.add(component_id)
    component_entities = {
        str(row.get("component_id", "")).strip(): _summarize_entity(_entity_from_row(kind="component", row=row))
        for row in component_rows
        if str(row.get("component_id", "")).strip() in matched_id_set
    }
    results: list[dict[str, Any]] = []
    for component_id in [
        str(row.get("component_id", "")).strip()
        for row in component_rows
        if str(row.get("component_id", "")).strip() in matched_id_set
    ]:
        entity = component_entities.get(component_id)
        if entity is not None:
            results.append(entity)
    return (results, diagnostics) if return_diagnostics else results

def _collect_impacted_workstreams(
    connection: Any,
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    component_ids: Sequence[str],
    diagram_ids: Sequence[str],
    return_diagnostics: bool = False,
) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], dict[str, Any]]:
    normalized_changed_paths = _dedupe_strings(
        [
            _normalize_repo_token(str(path_ref).strip(), repo_root=repo_root)
            for path_ref in changed_paths
            if str(path_ref).strip()
        ]
    )
    diagnostics = {
        "fast_selector_used": False,
        "selector_cache_hit": False,
        "selector_candidate_row_count": 0,
    }
    if not normalized_changed_paths and not component_ids and not diagram_ids:
        return ([], diagnostics) if return_diagnostics else []
    workstream_rows = _cached_projection_rows(
        repo_root=repo_root,
        cache_name="workstreams_full_rows",
        loader=lambda: [dict(row) for row in connection.execute("SELECT * FROM workstreams").fetchall()],
    )
    workstream_entities = {
        str(row.get("idea_id", "")).strip().upper(): _entity_from_row(kind="workstream", row=row)
        for row in workstream_rows
        if str(row.get("idea_id", "")).strip()
    }
    direct_match_rows = _cached_projection_rows(
        repo_root=repo_root,
        cache_name="workstream_direct_match_rows",
        loader=lambda: [
            {
                "source_id": str(row.get("idea_id", "")).strip().upper(),
                "target_path": target_path,
            }
            for row in workstream_rows
            for target_path in (
                _normalize_repo_token(str(row.get("source_path", "")), repo_root=repo_root),
                _normalize_repo_token(str(row.get("idea_file", "")), repo_root=repo_root),
                _normalize_repo_token(str(row.get("promoted_to_plan", "")), repo_root=repo_root),
            )
            if str(row.get("idea_id", "")).strip() and target_path
        ],
    )
    traceability_match_rows = _cached_projection_rows(
        repo_root=repo_root,
        cache_name="workstream_traceability_match_rows",
        loader=lambda: [
            {
                "source_id": str(row.get("source_id", "")).strip().upper(),
                "source_kind": {
                    "code": "trace_code",
                    "doc": "trace_doc",
                    "runbook": "trace_runbook",
                }.get(str(row.get("target_kind", "")).strip().lower(), "trace_doc"),
                "target_path": target_path,
            }
            for row in connection.execute(
                """
                SELECT source_id, target_kind, target_id
                FROM traceability_edges
                WHERE target_kind IN ('runbook', 'doc', 'code')
                """
            ).fetchall()
            if (target_path := _normalize_repo_token(str(row.get("target_id", "")), repo_root=repo_root))
        ],
    )
    direct_index_payload, direct_cache_hit = _path_row_match_index(
        repo_root=repo_root,
        namespace="workstream_direct_match_rows",
        rows=direct_match_rows,
    )
    trace_index_payload, trace_cache_hit = _path_row_match_index(
        repo_root=repo_root,
        namespace="workstream_traceability_match_rows",
        rows=traceability_match_rows,
    )
    candidate_direct_rows = _candidate_rows_for_changed_paths(
        changed_paths=normalized_changed_paths,
        index_payload=direct_index_payload,
    )
    candidate_traceability_rows = _candidate_rows_for_changed_paths(
        changed_paths=normalized_changed_paths,
        index_payload=trace_index_payload,
    )
    if not candidate_direct_rows and normalized_changed_paths:
        candidate_direct_rows = [dict(row) for row in direct_match_rows]
    if not candidate_traceability_rows and normalized_changed_paths:
        candidate_traceability_rows = [dict(row) for row in traceability_match_rows]
    diagnostics["fast_selector_used"] = bool(normalized_changed_paths)
    diagnostics["selector_cache_hit"] = bool(direct_cache_hit and trace_cache_hit)
    diagnostics["selector_candidate_row_count"] = len(candidate_direct_rows) + len(candidate_traceability_rows)
    candidate_map: dict[str, dict[str, Any]] = {}

    def _candidate(workstream_id: str) -> dict[str, Any] | None:
        token = str(workstream_id or "").strip().upper()
        if not token:
            return None
        if token not in candidate_map:
            entity = workstream_entities.get(token)
            if entity is None:
                return None
            candidate_map[token] = _base_workstream_candidate(entity)
        return candidate_map[token]

    for row in candidate_direct_rows:
        workstream_id = str(row.get("source_id", "")).strip().upper()
        target_path = str(row.get("target_path", "")).strip()
        if not workstream_id or not target_path:
            continue
        for path_ref in normalized_changed_paths:
            match_type = _normalized_path_match_type(changed_path=path_ref, target_path=target_path)
            if not match_type:
                continue
            candidate = _candidate(workstream_id)
            if candidate is None:
                continue
            _add_workstream_path_evidence(
                candidate,
                changed_path=path_ref,
                target_path=target_path,
                source_kind="direct",
                match_type=match_type,
            )
    for row in candidate_traceability_rows:
        target_path = str(row.get("target_path", "")).strip()
        source_kind = str(row.get("source_kind", "")).strip() or "trace_doc"
        if not target_path:
            continue
        for path_ref in normalized_changed_paths:
            match_type = _normalized_path_match_type(changed_path=path_ref, target_path=target_path)
            if not match_type:
                continue
            candidate = _candidate(str(row.get("source_id", "")))
            if candidate is None:
                continue
            _add_workstream_path_evidence(
                candidate,
                changed_path=path_ref,
                target_path=target_path,
                source_kind=source_kind,
                match_type=match_type,
            )
    if component_ids:
        component_rows = _cached_projection_rows(
            repo_root=repo_root,
            cache_name="components_full_rows",
            loader=lambda: [dict(row) for row in connection.execute("SELECT * FROM components").fetchall()],
        )
        component_map = {
            str(row.get("component_id", "")).strip(): row
            for row in component_rows
            if str(row.get("component_id", "")).strip()
        }
        for component_id in component_ids:
            row = component_map.get(str(component_id).strip())
            if row is None:
                continue
            normalized_component_id = str(row.get("component_id", "")).strip()
            for workstream_id in _json_list(str(row.get("workstreams_json", ""))):
                candidate = _candidate(workstream_id)
                if candidate is not None:
                    _add_workstream_component_evidence(candidate, component_id=normalized_component_id)
    if diagram_ids:
        placeholders = ",".join("?" for _ in diagram_ids)
        query = (
            "SELECT source_id, target_id FROM traceability_edges "
            f"WHERE relation = 'related_diagram_ids' AND target_kind = 'diagram' AND target_id IN ({placeholders})"
        )
        for row in connection.execute(query, tuple(diagram_ids)).fetchall():
            workstream_id = str(row["source_id"]).strip().upper()
            candidate = _candidate(workstream_id)
            if candidate is None:
                continue
            _add_workstream_diagram_evidence(candidate, diagram_id=str(row["target_id"]).strip())
    ranked = _finalize_workstream_candidates(list(candidate_map.values()))
    pruned = _prune_low_precision_workstream_candidates(ranked)
    return (pruned, diagnostics) if return_diagnostics else pruned

def _engineering_note_match(
    *,
    note_paths: Sequence[str],
    note_components: Sequence[str],
    note_workstreams: Sequence[str],
    changed_paths: Sequence[str],
    component_ids: Sequence[str],
    workstream_ids: Sequence[str],
) -> dict[str, Any]:
    matched_paths: list[str] = []
    exact_path_hits = 0
    watch_path_hits = 0
    best_path_depth = 0
    seen_paths: set[str] = set()
    for path_ref in changed_paths:
        for note_path in note_paths:
            if not note_path:
                continue
            if path_ref == note_path:
                exact_path_hits += 1
            elif _path_touches_watch(changed_path=path_ref, watch_path=note_path):
                watch_path_hits += 1
            else:
                continue
            if note_path not in seen_paths:
                matched_paths.append(note_path)
                seen_paths.add(note_path)
            best_path_depth = max(best_path_depth, len(Path(note_path).parts))
    matched_components = sorted(set(note_components).intersection(component_ids))
    matched_workstreams = sorted(set(note_workstreams).intersection(workstream_ids))
    matched_by: list[str] = []
    if matched_paths:
        matched_by.append("path")
    if matched_components:
        matched_by.append("component")
    if matched_workstreams:
        matched_by.append("workstream")
    return {
        "matched": bool(matched_by),
        "matched_by": matched_by,
        "matched_paths": matched_paths,
        "matched_components": matched_components,
        "matched_workstreams": matched_workstreams,
        "relevance": {
            "exact_path_hits": exact_path_hits,
            "watch_path_hits": watch_path_hits,
            "best_path_depth": best_path_depth,
            "component_hits": len(matched_components),
            "workstream_hits": len(matched_workstreams),
        },
        "sort_key": (
            1 if exact_path_hits else 0,
            exact_path_hits,
            1 if watch_path_hits else 0,
            watch_path_hits,
            best_path_depth,
            len(matched_components),
            len(matched_workstreams),
            -len(note_paths),
            -len(note_components),
            -len(note_workstreams),
        ),
    }

def _collect_relevant_notes(
    connection: Any,
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    component_ids: Sequence[str],
    workstream_ids: Sequence[str],
) -> dict[str, list[dict[str, Any]]]:
    ranked: dict[str, list[tuple[tuple[Any, ...], str, dict[str, Any]]]] = {}
    note_rows = _cached_projection_rows(
        repo_root=repo_root,
        cache_name="engineering_notes_full_rows",
        loader=lambda: [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM engineering_notes ORDER BY note_kind, note_id"
            ).fetchall()
        ],
    )
    for row in note_rows:
        note_paths = _json_list(str(row.get("path_refs_json", "")))
        note_components = _json_list(str(row.get("components_json", "")))
        note_workstreams = _json_list(str(row.get("workstreams_json", "")))
        match = _engineering_note_match(
            note_paths=note_paths,
            note_components=note_components,
            note_workstreams=note_workstreams,
            changed_paths=changed_paths,
            component_ids=component_ids,
            workstream_ids=workstream_ids,
        )
        if not bool(match.get("matched")):
            continue
        note_kind = str(row.get("note_kind", ""))
        note_id = str(row.get("note_id", ""))
        ranked.setdefault(note_kind, []).append(
            (
                tuple(match["sort_key"]),
                note_id,
                _engineering_note_summary(row, match=match),
            )
        )
    results: dict[str, list[dict[str, Any]]] = {}
    for note_kind, rows in ranked.items():
        rows.sort(key=lambda item: item[1])
        rows.sort(key=lambda item: item[0], reverse=True)
        results[note_kind] = [payload for _key, _note_id, payload in rows]
    return results

def _collect_relevant_bugs(
    connection: Any,
    *,
    repo_root: Path,
    component_ids: Sequence[str],
    changed_paths: Sequence[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    normalized_components = {str(token).lower() for token in component_ids}
    bug_rows = _cached_projection_rows(
        repo_root=repo_root,
        cache_name="bugs_full_rows",
        loader=lambda: [dict(row) for row in connection.execute("SELECT * FROM bugs ORDER BY date DESC, title").fetchall()],
    )
    for row in bug_rows:
        components = {token.lower() for token in _parse_component_tokens(str(row.get("components", "")))}
        if not (
            components.intersection(normalized_components)
            or any(
                _path_touches_watch(changed_path=path_ref, watch_path=_normalize_repo_token(str(row.get("link_target", "")), repo_root=repo_root))
                for path_ref in changed_paths
                if str(row.get("link_target", "")).strip()
            )
        ):
            continue
        search_body = str(row.get("search_body", ""))
        rows.append(
            {
                "bug_key": str(row.get("bug_key", "")),
                "title": str(row.get("title", "")),
                "severity": str(row.get("severity", "")),
                "status": str(row.get("status", "")),
                "path": str(row.get("link_target") or row.get("source_path", "")),
                "root_cause": _bug_excerpt(search_body, "Root Cause"),
                "prevention": _bug_excerpt(search_body, "Prevention"),
            }
        )
    return rows

def _collect_code_neighbors(
    connection: Any,
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
) -> dict[str, list[dict[str, Any]]]:
    direct: dict[str, dict[str, Any]] = {}
    reverse: dict[str, dict[str, Any]] = {}
    contract_consumers: dict[str, dict[str, Any]] = {}
    contract_refs: dict[str, dict[str, Any]] = {}
    make_invocations: dict[str, dict[str, Any]] = {}
    invoked_by_make: dict[str, dict[str, Any]] = {}
    documents: dict[str, dict[str, Any]] = {}
    documented_by: dict[str, dict[str, Any]] = {}
    runbook_covers: dict[str, dict[str, Any]] = {}
    covered_by_runbooks: dict[str, dict[str, Any]] = {}
    code_edge_rows = _cached_projection_rows(
        repo_root=repo_root,
        cache_name="code_edges_full_rows",
        loader=lambda: [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM code_edges ORDER BY source_path, relation, target_path"
            ).fetchall()
        ],
    )
    for row in code_edge_rows:
        source_path = str(row.get("source_path", ""))
        target_path = str(row.get("target_path", ""))
        relation = str(row.get("relation", ""))
        if source_path in changed_paths and relation == "imports":
            direct[target_path] = {"path": target_path, "relation": "imports"}
        if target_path in changed_paths and relation == "imports":
            reverse[source_path] = {"path": source_path, "relation": "imported_by"}
        if target_path in changed_paths and relation == "references_contract":
            contract_consumers[source_path] = {"path": source_path, "relation": "references_contract"}
        if source_path in changed_paths and relation == "references_contract":
            contract_refs[target_path] = {"path": target_path, "relation": "references_contract"}
        if source_path in changed_paths and relation == "invokes_code":
            make_invocations[target_path] = {"path": target_path, "relation": "invokes_code"}
        if target_path in changed_paths and relation == "invokes_code":
            invoked_by_make[source_path] = {"path": source_path, "relation": "invoked_by_make"}
        if source_path in changed_paths and relation == "documents_code":
            documents[target_path] = {"path": target_path, "relation": "documents_code"}
        if target_path in changed_paths and relation == "documents_code":
            documented_by[source_path] = {"path": source_path, "relation": "documented_by"}
        if source_path in changed_paths and relation == "runbook_covers_code":
            runbook_covers[target_path] = {"path": target_path, "relation": "runbook_covers_code"}
        if target_path in changed_paths and relation == "runbook_covers_code":
            covered_by_runbooks[source_path] = {"path": source_path, "relation": "covered_by_runbooks"}
    return {
        "imports": [direct[key] for key in sorted(direct)],
        "imported_by": [reverse[key] for key in sorted(reverse)],
        "contract_consumers": [contract_consumers[key] for key in sorted(contract_consumers)],
        "contract_refs": [contract_refs[key] for key in sorted(contract_refs)],
        "make_invocations": [make_invocations[key] for key in sorted(make_invocations)],
        "invoked_by_make": [invoked_by_make[key] for key in sorted(invoked_by_make)],
        "documents": [documents[key] for key in sorted(documents)],
        "documented_by": [documented_by[key] for key in sorted(documented_by)],
        "runbook_covers": [runbook_covers[key] for key in sorted(runbook_covers)],
        "covered_by_runbooks": [covered_by_runbooks[key] for key in sorted(covered_by_runbooks)],
    }

def _collect_recommended_tests(
    connection: Any,
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    code_neighbors: Mapping[str, Sequence[Mapping[str, Any]]],
    limit: int,
) -> list[dict[str, Any]]:
    if int(limit) <= 0:
        return []
    candidate_paths = set(changed_paths)
    for bucket in code_neighbors.values():
        for row in bucket:
            candidate_paths.add(str(row.get("path", "")).strip())
    scored: list[tuple[tuple[int, int, int, int], dict[str, Any]]] = []
    test_rows = _cached_projection_rows(
        repo_root=repo_root,
        cache_name="tests_full_rows",
        loader=lambda: [dict(row) for row in connection.execute("SELECT * FROM test_cases ORDER BY test_path, test_name").fetchall()],
    )
    for row in test_rows:
        targets = set(_json_list(str(row["target_paths_json"])))
        overlap = sorted(targets.intersection(candidate_paths))
        if not overlap:
            continue
        metadata = json.loads(str(row["metadata_json"] or "{}"))
        history = metadata.get("history", {}) if isinstance(metadata, Mapping) else {}
        empirical_score = int(history.get("empirical_score", 0) or 0) if isinstance(history, Mapping) else 0
        recent_failure = bool(history.get("recent_failure")) if isinstance(history, Mapping) else False
        failure_count = int(history.get("failure_count", 0) or 0) if isinstance(history, Mapping) else 0
        scored.append(
            (
                (
                    len(overlap),
                    1 if recent_failure else 0,
                    failure_count,
                    empirical_score,
                ),
                {
                    "test_id": str(row["test_id"]),
                    "test_path": str(row["test_path"]),
                    "node_id": str(row["node_id"]),
                    "test_name": str(row["test_name"]),
                    "markers": _json_list(str(row["markers_json"])),
                    "matched_targets": overlap,
                    "history": {
                        "recent_failure": recent_failure,
                        "failure_count": failure_count,
                        "sources": [
                            str(token).strip()
                            for token in history.get("sources", [])
                            if str(token).strip()
                        ]
                        if isinstance(history, Mapping) and isinstance(history.get("sources"), list)
                        else [],
                        "last_failure_utc": str(history.get("last_failure_utc", "")).strip()
                        if isinstance(history, Mapping)
                        else "",
                    },
                },
            )
        )
    scored.sort(
        key=lambda item: (
            -item[0][1],
            -item[0][2],
            -item[0][0],
            -item[0][3],
            item[1]["test_path"],
            item[1]["node_id"],
        )
    )
    return [payload for _score, payload in scored[: max(1, int(limit))]]
