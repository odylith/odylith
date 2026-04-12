from __future__ import annotations

from typing import Any

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.common.casebook_bug_ids import BUG_ID_FIELD, resolve_casebook_bug_id
from odylith.runtime.context_engine import projection_repo_state_runtime


_PROCESS_PROJECTED_INPUTS_CACHE: dict[str, tuple[str, dict[str, str]]] = {}
_PROCESS_PROJECTION_INPUT_FINGERPRINT_CACHE: dict[str, tuple[str, str]] = {}
_PROCESS_PATH_FINGERPRINT_CACHE: dict[str, tuple[str, str]] = {}


def bind(host: Any) -> None:
    getter = host.__getitem__ if isinstance(host, dict) else lambda name: getattr(host, name)
    for name in ('Any', 'Callable', 'Mapping', 'Path', 'SCHEMA_VERSION', 'Sequence', '_BUG_CANONICAL_STATUS_LABELS', '_BUG_CORE_FIELD_ORDER_SET', '_BUG_CRITICAL_SEVERITIES', '_BUG_DETAIL_SECTION_ORDER', '_BUG_INTELLIGENCE_ALL_FIELDS', '_BUG_INTELLIGENCE_REQUIRED_CRITICAL_FIELDS', '_BUG_METADATA_LINE_RE', '_BUG_TERMINAL_STATUSES', '_CONTRACT_PATH_PREFIXES', '_CONTRACT_REF_RE', '_ENGINEERING_CORE_PATHS', '_ENGINEERING_NOTE_KIND_SET', '_GUIDANCE_CHUNK_MANIFEST_PATH', '_GUIDANCE_CHUNK_ROOT', '_MARKDOWN_CODE_REF_RE', '_MISS_RECOVERY_ALLOWED_KINDS', '_MISS_RECOVERY_DOC_LIMIT', '_MISS_RECOVERY_GENERIC_QUERY_TOKENS', '_MISS_RECOVERY_KIND_PRIORITY', '_MISS_RECOVERY_RESULT_LIMIT', '_MISS_RECOVERY_TEST_LIMIT', '_NOTE_TITLE_WORDS', '_PROCESS_ARCHITECTURE_PACKET_CACHE', '_PROCESS_MISS_RECOVERY_INDEX_CACHE', '_PROCESS_OPTIMIZATION_SNAPSHOT_CACHE', '_PROCESS_ORCHESTRATION_ADOPTION_SNAPSHOT_CACHE', '_PROCESS_PATH_SCOPE_CACHE', '_PROCESS_PATH_SIGNAL_PROFILE_CACHE', '_PROCESS_PROJECTION_CONNECTION_CACHE', '_PROCESS_PROJECTION_ROWS_CACHE', '_PROCESS_WARM_CACHE', '_PROCESS_WARM_CACHE_FINGERPRINTS', '_PROCESS_WARM_CACHE_TTL_SECONDS', '_PYTEST_LASTFAILED_PATH', '_PYTHON_GRAPH_ROOTS', '_ProjectionCursor', '_RAW_PATH_TOKEN_RE', '_SECTION_NOTE_SOURCES', '_TEST_HISTORY_REPORT_GLOBS', '_WORKSTREAM_TOKEN_RE', '_add', '_append_lesson', '_available_full_scan_roots', '_commit', '_compact_test_row_for_packet', '_dedupe_strings', '_entity_by_path', '_entity_from_row', '_env_truthy', '_filter_odylith_search_results', '_full_scan_guidance', '_full_scan_reason_message', '_full_scan_terms', '_json_dict', '_json_list', '_lookup_field', '_normalize_bug_field_key', '_normalize_bug_field_name', '_normalize_entity_kind', '_normalize_repo_token', '_normalized_string_list', '_odylith_ablation_active', '_odylith_query_targets_disabled', '_odylith_switch_snapshot', '_parse_component_tokens', '_path_signal_profile', '_path_touches_watch', '_projection_exact_search_results', '_projection_names_for_scope', '_register', '_repair_backend_once', '_repo_scan_candidate_search_results', '_run_full_scan', '_utc_now', 'a', 'allowed', 'anchor_tokens', 'archive_relative', 'atlas_catalog_path', 'backend_ready', 'backlog_contract', 'blank_pending', 'bootstraps_root', 'bucket', 'buckets', 'bug_key', 'bug_lookup', 'bullets', 'bundle', 'cache', 'cache_key', 'cache_name', 'cache_updates', 'cached', 'cached_fingerprint', 'cached_until', 'candidate', 'candidate_keys', 'candidates', 'casebook_bugs_root', 'cell', 'changed_paths', 'clause', 'code_edge_rows', 'column', 'columns', 'compass_stream_path', 'component_id', 'component_ids', 'component_index', 'component_matches', 'component_registry', 'component_registry_path', 'component_rows', 'component_specs_root', 'component_tokens', 'connection', 'content', 'count', 'count_alias', 'count_match', 'critical', 'current_key', 'current_lines', 'date', 'delivery_intelligence_engine', 'descending', 'diagram_id', 'diagram_lookup', 'docs', 'entity', 'entity_id', 'entity_key', 'entry', 'exact_results', 'exact_rows', 'exc', 'existing', 'existing_paths', 'extra_terms', 'f', 'fallback', 'fallback_scan', 'field', 'field_blob', 'field_name', 'field_value', 'fields', 'filtered', 'fingerprint', 'fingerprints', 'force', 'full_scan_reason', 'glob', 'governance', 'group_clause', 'group_fields', 'grouped', 'grouped_counts', 'grouped_rows', 'has_runtime_results', 'having_threshold', 'hit', 'index', 'index_path', 'initial_value', 'item', 'json', 'key', 'kind', 'kinds', 'known_docs', 'known_tests', 'label', 'latest_mtime_ns', 'lessons', 'limit', 'limit_clause', 'limit_value', 'line', 'lines', 'link_target', 'loader', 'local_results', 'local_rows', 'local_sparse_results', 'lookup', 'match', 'match_eq', 'match_in', 'match_lower', 'matched', 'matches', 'merged', 'metadata', 'missing_fields', 'mode_token', 'name', 'normalized', 'normalized_component_id', 'normalized_fields', 'normalized_kinds', 'normalized_name', 'normalized_paths', 'normalized_query', 'note_kind', 'now', 'odylith_ablation_active', 'odylith_architecture_mode', 'odylith_context_cache', 'odylith_context_engine_engineering_notes_runtime', 'odylith_context_engine_projection_compiler_runtime', 'odylith_context_engine_projection_runtime', 'odylith_control_state', 'odylith_evaluation_ledger', 'odylith_memory_backend', 'odylith_projection_snapshot', 'odylith_remote_retrieval', 'order_clause', 'ordered', 'overlap', 'overlap_ratio', 'paragraph', 'param_index', 'params', 'parent_name', 'part', 'parts', 'path', 'path_obj', 'path_prefixes', 'path_ref', 'path_refs', 'payload', 'payloads', 'phrase', 'pieces', 'placeholder_count', 'predicate', 'predicates', 'prefix', 'preflight_checks', 'present_fields', 'projected', 'projected_fields', 'projected_kind', 'projection_contract_version', 'projection_fingerprint', 'projection_snapshot_path', 'proof_paths', 'queries', 'query', 'query_index', 'query_phrase', 'query_tokens', 'radar_source_root', 'rank', 'rank_key', 'ranked_rows', 'raw', 'raw_name', 'raw_path', 'raw_tables', 'raw_value', 're', 'read_runtime_state', 'reason', 'record_runtime_timing', 'recovered_docs', 'recovered_entities', 'recovered_tests', 'recovery_mode', 'recovery_modes', 'ref', 'ref_buckets', 'refs', 'rel_path', 'rel_root', 'related_bug_refs', 'relation', 'relation_limit', 'remainder', 'remote_config', 'remote_results', 'remote_rows', 'repair_attempted', 'repo_root', 'repo_scan_reason', 'requested', 'requested_fingerprint', 'required_fields', 'required_missing', 'results', 'retrieval_mode', 'rhs', 'root', 'row', 'row_count', 'rows', 'rows_by_key', 'runtime_mode', 'runtime_ready', 'runtime_state', 'scan', 'scope', 'scope_token', 'score', 'score_bias', 'section', 'sections', 'seen', 'seen_entities', 'seen_keys', 'select_clause', 'select_terms', 'selection_state', 'self', 'severity', 'shared_only_input', 'signature', 'snapshot', 'source', 'source_id', 'source_kind', 'source_mmd', 'source_path', 'started_at', 'stat', 'status', 'stripped', 'summary', 'surface_root_path', 'switch_snapshot', 'table_name', 'target', 'target_id', 'target_key', 'target_kind', 'target_path', 'technical_plans_root', 'term', 'terms', 'tests', 'text', 'time', 'title', 'token', 'token_index', 'tokens', 'tooling_guidance_catalog', 'traceability_graph_path', 'traceability_rows', 'trailer', 'trimmed', 'truth_root_path', 'use_hybrid', 'v', 'value', 'values', 'variants', 'warmed_at', 'where_clause', 'words', 'workstream_rows', 'workstreams'):
        try:
            globals()[name] = getter(name)
        except (AttributeError, KeyError):
            continue


class _ProjectionConnection:
    def __init__(self, *, repo_root: Path, snapshot: Mapping[str, Any]) -> None:
        self.repo_root = Path(repo_root).resolve()
        raw_tables = snapshot.get("tables", {}) if isinstance(snapshot, Mapping) else {}
        self._tables = {
            str(name).strip(): [dict(row) for row in rows if isinstance(row, Mapping)]
            for name, rows in raw_tables.items()
            if str(name).strip() and isinstance(rows, list)
        }

    def close(self) -> None:
        return None

    def commit(self) -> None:
        return None

    def table_rows(self, table_name: str) -> list[dict[str, Any]]:
        return [dict(row) for row in self._tables.get(str(table_name).strip(), [])]

    def has_table(self, table_name: str) -> bool:
        return str(table_name).strip() in self._tables

    def execute(self, query: str, params: Sequence[Any] = ()) -> _ProjectionCursor:
        normalized = " ".join(str(query or "").strip().split())
        rows = self._select_rows(normalized, tuple(params))
        return _ProjectionCursor(rows)

    def _select_rows(self, query: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        if not query:
            return []
        if query.startswith("SELECT COUNT(*) AS row_count FROM "):
            table_name = str(query.partition("FROM ")[2]).strip()
            return [{"row_count": len(self.table_rows(table_name))}]
        if " GROUP BY " in query and "COUNT(*) AS " in query:
            grouped = self._select_grouped_rows(query=query)
            if grouped is not None:
                return grouped
        if "WHERE (source_kind = ? AND source_id = ?)" in query and "OR (target_kind = ? AND target_id = ?)" in query:
            return self._select_traceability_bidirectional(query=query, params=params)
        return self._select_rows_generic(query=query, params=params)

    def _select_grouped_rows(self, *, query: str) -> list[dict[str, Any]] | None:
        match = re.match(
            r"^SELECT\s+(.+?)\s+FROM\s+([A-Za-z_][A-Za-z0-9_]*)\s+GROUP BY\s+(.+?)(?:\s+HAVING\s+COUNT\(\*\)\s*>\s*(\d+))?$",
            query,
        )
        if match is None:
            return None
        select_clause = str(match.group(1) or "").strip()
        table_name = str(match.group(2) or "").strip()
        group_clause = str(match.group(3) or "").strip()
        having_threshold = int(str(match.group(4) or "0").strip() or 0)
        select_terms = [str(token).strip() for token in select_clause.split(",") if str(token).strip()]
        group_fields = [str(token).strip() for token in group_clause.split(",") if str(token).strip()]
        count_alias = ""
        projected_fields: list[str] = []
        for term in select_terms:
            count_match = re.match(r"^COUNT\(\*\)\s+AS\s+([A-Za-z_][A-Za-z0-9_]*)$", term, flags=re.IGNORECASE)
            if count_match is not None:
                count_alias = str(count_match.group(1) or "").strip()
                continue
            projected_fields.append(term)
        if not group_fields or not count_alias:
            return None
        grouped_rows: dict[tuple[str, ...], dict[str, Any]] = {}
        grouped_counts: dict[tuple[str, ...], int] = {}
        for row in self.table_rows(table_name):
            key = tuple(str(row.get(field, "")).strip() for field in group_fields)
            grouped_counts[key] = grouped_counts.get(key, 0) + 1
            if key in grouped_rows:
                continue
            grouped_rows[key] = {field: row.get(field) for field in projected_fields or group_fields}
        results: list[dict[str, Any]] = []
        for key in sorted(grouped_rows):
            count = grouped_counts.get(key, 0)
            if count <= having_threshold:
                continue
            projected = dict(grouped_rows[key])
            projected[count_alias] = count
            results.append(projected)
        return results

    def _select_traceability_bidirectional(self, *, query: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        relation_limit = int(params[4] or 0) if len(params) >= 5 else 0
        source_kind, source_id, target_kind, target_id = (
            str(params[0] or "").strip(),
            str(params[1] or "").strip(),
            str(params[2] or "").strip(),
            str(params[3] or "").strip(),
        )
        rows = [
            dict(row)
            for row in self.table_rows("traceability_edges")
            if (
                str(row.get("source_kind", "")).strip() == source_kind
                and str(row.get("source_id", "")).strip() == source_id
            )
            or (
                str(row.get("target_kind", "")).strip() == target_kind
                and str(row.get("target_id", "")).strip() == target_id
            )
        ]
        rows.sort(
            key=lambda row: (
                str(row.get("relation", "")),
                str(row.get("source_kind", "")),
                str(row.get("source_id", "")),
                str(row.get("target_kind", "")),
                str(row.get("target_id", "")),
            )
        )
        return rows[: max(1, relation_limit)] if relation_limit else rows

    def _select_rows_generic(self, *, query: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        match = re.match(r"^SELECT\s+(.+?)\s+FROM\s+([A-Za-z_][A-Za-z0-9_]*)\s*(.*)$", query)
        if match is None:
            return []
        select_clause = str(match.group(1) or "").strip()
        table_name = str(match.group(2) or "").strip()
        remainder = str(match.group(3) or "").strip()
        where_clause = ""
        order_clause = ""
        limit_clause = ""
        if remainder.startswith("WHERE "):
            where_clause = remainder[6:]
            for token in (" ORDER BY ", " LIMIT "):
                if token in where_clause:
                    where_clause, trailer = where_clause.split(token, 1)
                    if token.strip() == "ORDER BY":
                        order_clause = trailer
                    else:
                        limit_clause = trailer
                    break
        elif remainder.startswith("ORDER BY "):
            order_clause = remainder[9:]
        elif remainder.startswith("LIMIT "):
            limit_clause = remainder[6:]
        if order_clause and " LIMIT " in order_clause:
            order_clause, limit_clause = order_clause.split(" LIMIT ", 1)
        rows = self.table_rows(table_name)
        rows = self._apply_where(rows=rows, where_clause=where_clause, params=params)
        rows = self._apply_order(rows=rows, table_name=table_name, order_clause=order_clause)
        rows = self._apply_limit(rows=rows, limit_clause=limit_clause, params=params)
        return [self._project_row(row=row, select_clause=select_clause) for row in rows]

    def _apply_where(
        self,
        *,
        rows: Sequence[Mapping[str, Any]],
        where_clause: str,
        params: tuple[Any, ...],
    ) -> list[dict[str, Any]]:
        clause = str(where_clause or "").strip()
        if not clause:
            return [dict(row) for row in rows]
        parts = [part.strip() for part in re.split(r"\s+AND\s+", clause) if part.strip()]
        param_index = 0
        predicates: list[Any] = []
        for part in parts:
            match_lower = re.match(r"^lower\(([A-Za-z_][A-Za-z0-9_]*)\)\s*=\s*(.+)$", part)
            if match_lower is not None:
                field = str(match_lower.group(1) or "").strip()
                rhs = str(match_lower.group(2) or "").strip()
                if rhs == "?":
                    value = str(params[param_index] if param_index < len(params) else "").strip().casefold()
                    param_index += 1
                else:
                    value = rhs.strip("'").casefold()
                predicates.append(lambda row, f=field, v=value: str(row.get(f, "")).strip().casefold() == v)
                continue
            match_eq = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$", part)
            if match_eq is not None:
                field = str(match_eq.group(1) or "").strip()
                rhs = str(match_eq.group(2) or "").strip()
                if rhs == "?":
                    value = str(params[param_index] if param_index < len(params) else "").strip()
                    param_index += 1
                else:
                    value = rhs.strip("'")
                predicates.append(lambda row, f=field, v=value: str(row.get(f, "")).strip() == v)
                continue
            match_in = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s+IN\s+\((.+)\)$", part)
            if match_in is not None:
                field = str(match_in.group(1) or "").strip()
                rhs = str(match_in.group(2) or "").strip()
                values: list[str] = []
                if "?" in rhs:
                    placeholder_count = rhs.count("?")
                    values = [
                        str(item).strip()
                        for item in params[param_index : param_index + placeholder_count]
                        if str(item).strip()
                    ]
                    param_index += placeholder_count
                else:
                    values = [token.strip().strip("'") for token in rhs.split(",") if token.strip().strip("'")]
                allowed = set(values)
                predicates.append(lambda row, f=field, a=allowed: str(row.get(f, "")).strip() in a)
                continue
        filtered = [dict(row) for row in rows]
        for predicate in predicates:
            filtered = [row for row in filtered if predicate(row)]
        return filtered

    def _apply_order(
        self,
        *,
        rows: Sequence[Mapping[str, Any]],
        table_name: str,
        order_clause: str,
    ) -> list[dict[str, Any]]:
        clause = str(order_clause or "").strip()
        ordered = [dict(row) for row in rows]
        if not clause:
            return ordered
        if table_name == "workstreams" and "CASE" in clause and "rank" in clause:
            ordered.sort(
                key=lambda row: (
                    999999
                    if str(row.get("rank", "")).strip() == "-"
                    else int(str(row.get("rank", "")).strip())
                    if str(row.get("rank", "")).strip().isdigit()
                    else 999999,
                    str(row.get("idea_id", "")),
                )
            )
            return ordered
        terms = [term.strip() for term in clause.split(",") if term.strip()]
        for term in reversed(terms):
            pieces = term.split()
            field = str(pieces[0] or "").strip()
            descending = len(pieces) > 1 and str(pieces[1] or "").strip().upper() == "DESC"
            ordered.sort(key=lambda row, f=field: self._sortable_value(row.get(f)), reverse=descending)
        return ordered

    def _apply_limit(
        self,
        *,
        rows: Sequence[Mapping[str, Any]],
        limit_clause: str,
        params: tuple[Any, ...],
    ) -> list[dict[str, Any]]:
        clause = str(limit_clause or "").strip()
        if not clause:
            return [dict(row) for row in rows]
        if clause == "?":
            limit_value = int(params[-1] or 0) if params else 0
        else:
            try:
                limit_value = int(clause)
            except ValueError:
                limit_value = 0
        return [dict(row) for row in rows[: max(0, limit_value)]] if limit_value > 0 else [dict(row) for row in rows]

    def _project_row(self, *, row: Mapping[str, Any], select_clause: str) -> dict[str, Any]:
        clause = str(select_clause or "").strip()
        if clause == "*":
            return dict(row)
        columns = [str(token).strip() for token in clause.split(",") if str(token).strip()]
        return {column: row.get(column) for column in columns}

    @staticmethod
    def _sortable_value(value: Any) -> Any:
        if isinstance(value, (int, float)):
            return value
        token = str(value or "").strip()
        if token.isdigit():
            return int(token)
        return token

def _projection_snapshot_cache_signature(*, repo_root: Path) -> tuple[Any, ...]:
    path = odylith_projection_snapshot.snapshot_path(repo_root=repo_root)
    if not path.is_file():
        return ("missing", str(path))
    try:
        stat = path.stat()
    except OSError:
        return ("error", str(path))
    return ("ready", stat.st_mtime_ns, stat.st_size)

def _connect(repo_root: Path) -> _ProjectionConnection:
    root = Path(repo_root).resolve()
    cache_key = str(root)
    signature = _projection_snapshot_cache_signature(repo_root=root)
    cached = _PROCESS_PROJECTION_CONNECTION_CACHE.get(cache_key)
    if cached is not None and cached[0] == signature:
        connection = cached[1]
        if isinstance(connection, _ProjectionConnection):
            return connection
    snapshot = odylith_projection_snapshot.load_snapshot(repo_root=root)
    if bool(snapshot.get("ready")) and isinstance(snapshot.get("tables"), Mapping):
        connection = _ProjectionConnection(repo_root=root, snapshot=snapshot)
        _PROCESS_PROJECTION_CONNECTION_CACHE[cache_key] = (signature, connection)
        return connection
    raise RuntimeError(
        f"Odylith projection snapshot is unavailable at {projection_snapshot_path(repo_root=root)}; run warmup first."
    )

def _path_fingerprint(path: Path, *, repo_root: Path | None = None, glob: str = "*.md") -> str:
    target = Path(path)
    state_token = ""
    if repo_root is not None:
        root = Path(repo_root).resolve()
        state_token = projection_repo_state_runtime.projection_repo_state_token(repo_root=root)
        cache_key = f"{target.resolve()}::{glob}"
        cached = _PROCESS_PATH_FINGERPRINT_CACHE.get(cache_key)
        if cached is not None and cached[0] == state_token:
            return str(cached[1]).strip()
    if target.is_dir():
        fingerprint = odylith_context_cache.fingerprint_tree(target, glob=glob)
    else:
        fingerprint = odylith_context_cache.fingerprint_paths([target])
    if state_token:
        _PROCESS_PATH_FINGERPRINT_CACHE[cache_key] = (state_token, fingerprint)
    return fingerprint

def _test_history_report_inputs(*, repo_root: Path) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "lastfailed": odylith_context_cache.path_signature(repo_root / _PYTEST_LASTFAILED_PATH),
    }
    for rel_root, glob in _TEST_HISTORY_REPORT_GLOBS:
        root = repo_root / rel_root
        key = f"{rel_root or 'repo'}:{glob}"
        if root.is_dir():
            payload[key] = _path_fingerprint(root, repo_root=repo_root, glob=glob)
            continue
        if root.is_file():
            payload[key] = _path_fingerprint(root, repo_root=repo_root, glob=glob)
            continue
        payload[key] = {"exists": False}
    return payload

def _workspace_activity_fingerprint(*, repo_root: Path) -> str:
    return projection_repo_state_runtime.workspace_activity_fingerprint(repo_root=repo_root)

def _radar_source_root(*, repo_root: Path) -> Path:
    return truth_root_path(repo_root=repo_root, key="radar_source")

def _technical_plans_root(*, repo_root: Path) -> Path:
    return truth_root_path(repo_root=repo_root, key="technical_plans")

def _casebook_bugs_root(*, repo_root: Path) -> Path:
    return truth_root_path(repo_root=repo_root, key="casebook_bugs")

def _component_specs_root(*, repo_root: Path) -> Path:
    return truth_root_path(repo_root=repo_root, key="component_specs")

def _component_registry_path(*, repo_root: Path) -> Path:
    return truth_root_path(repo_root=repo_root, key="component_registry")

def _product_root(*, repo_root: Path) -> Path:
    return surface_root_path(repo_root=repo_root, key="product_root")

def _atlas_catalog_path(*, repo_root: Path) -> Path:
    return _product_root(repo_root=repo_root) / "atlas" / "source" / "catalog" / "diagrams.v1.json"

def _compass_stream_path(*, repo_root: Path) -> Path:
    return agent_runtime_contract.resolve_agent_stream_path(repo_root=_product_root(repo_root=repo_root))

def _traceability_graph_path(*, repo_root: Path) -> Path:
    return _product_root(repo_root=repo_root) / "radar" / "traceability-graph.v1.json"

def _compute_projected_input_fingerprints(*, repo_root: Path, scope: str = "default") -> dict[str, str]:
    radar_source_root = _radar_source_root(repo_root=repo_root)
    technical_plans_root = _technical_plans_root(repo_root=repo_root)
    casebook_bugs_root = _casebook_bugs_root(repo_root=repo_root)
    component_specs_root = _component_specs_root(repo_root=repo_root)
    component_registry_path = _component_registry_path(repo_root=repo_root)
    atlas_catalog_path = _atlas_catalog_path(repo_root=repo_root)
    compass_stream_path = _compass_stream_path(repo_root=repo_root)
    traceability_graph_path = _traceability_graph_path(repo_root=repo_root)
    fingerprints = {
        "workstreams": odylith_context_cache.fingerprint_payload(
            {
                "contract_version": projection_contract_version("workstreams"),
                "backlog_index": _path_fingerprint(radar_source_root / "INDEX.md", repo_root=repo_root),
                "backlog_archive": _path_fingerprint(radar_source_root / "archive", repo_root=repo_root),
                "ideas": _path_fingerprint(radar_source_root / "ideas", repo_root=repo_root),
            }
        ),
        "releases": odylith_context_cache.fingerprint_payload(
            {
                "contract_version": projection_contract_version("releases"),
                "traceability": _path_fingerprint(traceability_graph_path, repo_root=repo_root),
                "release_registry": _path_fingerprint(
                    radar_source_root / "releases" / "releases.v1.json",
                    repo_root=repo_root,
                ),
                "release_events": _path_fingerprint(
                    radar_source_root / "releases" / "release-assignment-events.v1.jsonl",
                    repo_root=repo_root,
                ),
            }
        ),
        "plans": odylith_context_cache.fingerprint_payload(
            {
                "contract_version": projection_contract_version("plans"),
                "plan_index": _path_fingerprint(technical_plans_root / "INDEX.md", repo_root=repo_root),
                "plan_done": _path_fingerprint(technical_plans_root / "done", repo_root=repo_root),
                "plan_parked": _path_fingerprint(technical_plans_root / "parked", repo_root=repo_root),
            }
        ),
        "bugs": odylith_context_cache.fingerprint_payload(
            {
                "contract_version": projection_contract_version("bugs"),
                "bugs_index": _path_fingerprint(casebook_bugs_root / "INDEX.md", repo_root=repo_root),
                "bugs_archive": _path_fingerprint(casebook_bugs_root / "archive", repo_root=repo_root),
            }
        ),
        "diagrams": odylith_context_cache.fingerprint_payload(
            {
                "contract_version": projection_contract_version("diagrams"),
                "catalog": _path_fingerprint(atlas_catalog_path, repo_root=repo_root),
            }
        ),
        "components": odylith_context_cache.fingerprint_payload(
            {
                "contract_version": projection_contract_version("components"),
                "manifest": _path_fingerprint(component_registry_path, repo_root=repo_root),
                "catalog": _path_fingerprint(atlas_catalog_path, repo_root=repo_root),
                "ideas": _path_fingerprint(radar_source_root / "ideas", repo_root=repo_root),
                "stream": _path_fingerprint(compass_stream_path, repo_root=repo_root),
                "component_specs": _path_fingerprint(component_specs_root, repo_root=repo_root),
                "traceability": _path_fingerprint(traceability_graph_path, repo_root=repo_root),
                "workspace_activity": _workspace_activity_fingerprint(repo_root=repo_root),
            }
        ),
        "codex_events": odylith_context_cache.fingerprint_payload(
            {
                "contract_version": projection_contract_version("codex_events"),
                "stream": _path_fingerprint(compass_stream_path, repo_root=repo_root),
            }
        ),
        "traceability": odylith_context_cache.fingerprint_payload(
            {
                "contract_version": projection_contract_version("traceability"),
                "graph": _path_fingerprint(traceability_graph_path, repo_root=repo_root),
            }
        ),
        "delivery": odylith_context_cache.fingerprint_payload(
            {
                "contract_version": projection_contract_version("delivery"),
                "output": _path_fingerprint(
                    repo_root / delivery_intelligence_engine.DEFAULT_OUTPUT_PATH,
                    repo_root=repo_root,
                ),
            }
        ),
    }
    requested = set(_projection_names_for_scope(scope))
    if "engineering_graph" in requested:
        fingerprints["engineering_graph"] = odylith_context_cache.fingerprint_payload(
            (
                {
                    key: _path_fingerprint(repo_root / rel_path, repo_root=repo_root)
                    for key, rel_path in (
                        *_ENGINEERING_CORE_PATHS,
                        *_SECTION_NOTE_SOURCES,
                        ("runbook_index", "agents-guidelines/RUNBOOK_INDEX.MD"),
                        ("guidance_chunk_manifest", _GUIDANCE_CHUNK_MANIFEST_PATH),
                    )
                }
                | {
                    "contract_version": projection_contract_version("engineering_graph"),
                }
            )
            | {
                "guidance_chunks": _path_fingerprint(repo_root / _GUIDANCE_CHUNK_ROOT, repo_root=repo_root, glob="*.md"),
                "runbooks": _path_fingerprint(truth_root_path(repo_root=repo_root, key="runbooks"), repo_root=repo_root),
                "bugs": _path_fingerprint(casebook_bugs_root, repo_root=repo_root),
                "make": _path_fingerprint(repo_root / "mk", repo_root=repo_root, glob="*.mk"),
                "contracts": _path_fingerprint(repo_root / "contracts", repo_root=repo_root, glob="*.json"),
            }
        )
    if "code_graph" in requested:
        fingerprints["code_graph"] = odylith_context_cache.fingerprint_payload(
            (
                {
                    rel_root: _path_fingerprint(repo_root / rel_root, repo_root=repo_root, glob="*.py")
                    for rel_root, _module_root in _PYTHON_GRAPH_ROOTS
                }
                | {
                    "contract_version": projection_contract_version("code_graph"),
                }
            )
            | {
                "contracts": _path_fingerprint(repo_root / "contracts", repo_root=repo_root, glob="*.json"),
                "makefile": _path_fingerprint(repo_root / "Makefile", repo_root=repo_root),
                "mk": _path_fingerprint(repo_root / "mk", repo_root=repo_root, glob="*.mk"),
                "docs": _path_fingerprint(repo_root / "docs", repo_root=repo_root, glob="*.md"),
                "agents_guidelines_md": _path_fingerprint(
                    repo_root / "agents-guidelines",
                    repo_root=repo_root,
                    glob="*.md",
                ),
                "agents_guidelines_MD": _path_fingerprint(
                    repo_root / "agents-guidelines",
                    repo_root=repo_root,
                    glob="*.MD",
                ),
                "traceability": _path_fingerprint(traceability_graph_path, repo_root=repo_root),
            }
        )
    if "test_graph" in requested:
        fingerprints["test_graph"] = odylith_context_cache.fingerprint_payload(
            {
                "tests": _path_fingerprint(repo_root / "tests", repo_root=repo_root, glob="*.py"),
                "testing": _path_fingerprint(repo_root / "agents-guidelines" / "TESTING.MD", repo_root=repo_root),
                "history": _test_history_report_inputs(repo_root=repo_root),
            }
        )
    return fingerprints


def _projected_input_fingerprints(*, repo_root: Path, scope: str = "default") -> dict[str, str]:
    root = Path(repo_root).resolve()
    scope_token = str(scope or "default").strip().lower() or "default"
    state_token = projection_repo_state_runtime.projection_repo_state_token(repo_root=root)
    cache_key = f"{root}:{scope_token}"
    cached = _PROCESS_PROJECTED_INPUTS_CACHE.get(cache_key)
    if cached is not None and cached[0] == state_token:
        return dict(cached[1])
    fingerprints = _compute_projected_input_fingerprints(repo_root=root, scope=scope_token)
    _PROCESS_PROJECTED_INPUTS_CACHE[cache_key] = (state_token, dict(fingerprints))
    return fingerprints

def projection_input_fingerprint(*, repo_root: Path, scope: str = "default") -> str:
    """Return the deterministic runtime-input fingerprint without rebuilding projections."""

    root = Path(repo_root).resolve()
    scope_token = str(scope or "default").strip().lower() or "default"
    state_token = projection_repo_state_runtime.projection_repo_state_token(repo_root=root)
    cache_key = f"{root}:{scope_token}"
    cached = _PROCESS_PROJECTION_INPUT_FINGERPRINT_CACHE.get(cache_key)
    if cached is not None and cached[0] == state_token:
        return str(cached[1]).strip()
    fingerprint = odylith_context_cache.fingerprint_payload(
        {
            "schema": SCHEMA_VERSION,
            "scope": scope_token,
            "inputs": _projected_input_fingerprints(repo_root=root, scope=scope_token),
        }
    )
    _PROCESS_PROJECTION_INPUT_FINGERPRINT_CACHE[cache_key] = (state_token, fingerprint)
    return fingerprint

def _archive_files(root: Path) -> list[Path]:
    return odylith_context_engine_projection_runtime._archive_files(root)

def _collect_markdown_sections(path: Path) -> dict[str, list[str]]:
    return odylith_context_engine_projection_runtime._collect_markdown_sections(path)

def _parse_markdown_table(lines: Sequence[str]) -> tuple[list[str], list[dict[str, str]]]:
    return odylith_context_engine_projection_runtime._parse_markdown_table(lines)

def _parse_link_target(cell: str) -> str:
    return odylith_context_engine_projection_runtime._parse_link_target(cell)

def _load_idea_specs(*, repo_root: Path) -> dict[str, backlog_contract.IdeaSpec]:
    return odylith_context_engine_projection_runtime._load_idea_specs(repo_root=repo_root)

def _load_backlog_projection(*, repo_root: Path) -> dict[str, Any]:
    return odylith_context_engine_projection_runtime._load_backlog_projection(repo_root=repo_root)

def _load_plan_projection(*, repo_root: Path) -> dict[str, list[dict[str, str]]]:
    return odylith_context_engine_projection_runtime._load_plan_projection(repo_root=repo_root)

def _load_bug_projection(*, repo_root: Path) -> list[dict[str, str]]:
    return odylith_context_engine_projection_runtime._load_bug_projection(repo_root=repo_root)

def _normalize_bug_projection_rows(
    *,
    repo_root: Path,
    index_path: Path,
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    return odylith_context_engine_projection_runtime._normalize_bug_projection_rows(
        repo_root=repo_root,
        index_path=index_path,
        rows=rows,
    )

def _normalize_bug_link_target(*, repo_root: Path, index_path: Path, link_target: str) -> str:
    return odylith_context_engine_projection_runtime._normalize_bug_link_target(
        repo_root=repo_root,
        index_path=index_path,
        link_target=link_target,
    )

def _is_bug_placeholder_row(row: Mapping[str, Any]) -> bool:
    return odylith_context_engine_projection_runtime._is_bug_placeholder_row(row)

def _safe_json(value: Any) -> str:
    return odylith_context_engine_projection_runtime._safe_json(value)

def _raw_text(path: Path) -> str:
    return odylith_context_engine_projection_runtime._raw_text(path)

def _load_codex_event_projection(*, repo_root: Path) -> list[dict[str, Any]]:
    return odylith_context_engine_projection_runtime._load_codex_event_projection(repo_root=repo_root)

def _load_traceability_projection(*, repo_root: Path) -> list[dict[str, str]]:
    return odylith_context_engine_projection_runtime._load_traceability_projection(repo_root=repo_root)

def _load_diagram_projection(*, repo_root: Path) -> list[dict[str, Any]]:
    return odylith_context_engine_projection_runtime._load_diagram_projection(repo_root=repo_root)

def _looks_like_repo_path(token: str) -> bool:
    value = str(token or "").strip()
    if not value or "://" in value:
        return False
    if value.startswith("Plan: [") or value.startswith("["):
        return False
    return "/" in value or value.endswith((".py", ".md", ".json", ".jsonl", ".mmd", ".mk", ".yml", ".yaml", ".svg", ".png"))

def _extract_path_refs(*, text: str, repo_root: Path) -> list[str]:
    refs: set[str] = set()
    for match in _MARKDOWN_CODE_REF_RE.findall(str(text or "")):
        candidate = _normalize_repo_token(str(match), repo_root=repo_root)
        if candidate and _looks_like_repo_path(candidate):
            refs.add(candidate)
    for match in _RAW_PATH_TOKEN_RE.findall(str(text or "")):
        candidate = _normalize_repo_token(str(match), repo_root=repo_root)
        if candidate and _looks_like_repo_path(candidate):
            refs.add(candidate)
    for match in _CONTRACT_REF_RE.findall(str(text or "")):
        candidate = _normalize_repo_token(str(match), repo_root=repo_root)
        if candidate:
            refs.add(candidate)
    return sorted(refs)

def _extract_workstream_refs(text: str) -> list[str]:
    return sorted({token.upper() for token in _WORKSTREAM_TOKEN_RE.findall(str(text or "").upper())})

def _first_summary(lines: Sequence[str]) -> str:
    paragraph: list[str] = []
    bullets: list[str] = []
    for raw in lines:
        line = str(raw).strip()
        if not line or line.startswith("<!--") or line.startswith("#"):
            if paragraph:
                break
            continue
        if line.startswith("|"):
            continue
        if line.startswith(("- ", "* ")):
            bullets.append(line[2:].strip())
            if not paragraph and len(bullets) >= 2:
                break
            continue
        if re.fullmatch(r"-?\s*[A-Za-z0-9/() _.-]+:\s*.*", line):
            continue
        paragraph.append(line)
        if len(" ".join(paragraph)) >= 220:
            break
    if paragraph:
        return " ".join(paragraph).strip()
    if bullets:
        return " ".join(bullets[:2]).strip()
    return ""

def _note_title(section: str, content: str) -> str:
    title = " ".join(str(content or "").split())
    if not title:
        title = str(section or "").strip()
    words = title.split()
    if len(words) > _NOTE_TITLE_WORDS:
        title = " ".join(words[:_NOTE_TITLE_WORDS]).strip()
    return title

def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(token).strip() for token in value if str(token).strip()]
    if isinstance(value, str):
        return [token.strip() for token in value.replace(";", ",").split(",") if token.strip()]
    return []

def _parse_markdown_fields(lines: Sequence[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw in lines:
        line = str(raw).strip()
        if not line:
            continue
        match = re.fullmatch(r"-?\s*([A-Za-z0-9/() _.-]+):\s*(.*)", line)
        if match is None:
            continue
        fields[str(match.group(1)).strip()] = str(match.group(2)).strip()
    return fields

def _trim_multiline_lines(lines: Sequence[str]) -> list[str]:
    trimmed = [str(line).rstrip() for line in lines]
    while trimmed and not trimmed[0].strip():
        trimmed.pop(0)
    while trimmed and not trimmed[-1].strip():
        trimmed.pop()
    normalized: list[str] = []
    blank_pending = False
    for raw in trimmed:
        if not raw.strip():
            if normalized:
                blank_pending = True
            continue
        if blank_pending and normalized:
            normalized.append("")
            blank_pending = False
        normalized.append(raw)
    return normalized

def _join_bug_field_lines(lines: Sequence[str]) -> str:
    normalized = _trim_multiline_lines(lines)
    return "\n".join(normalized).strip()

def _parse_bug_entry_fields(lines: Sequence[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    def _commit() -> None:
        nonlocal current_key, current_lines
        if current_key is None:
            return
        value = _join_bug_field_lines(current_lines)
        fields[current_key] = value
        current_key = None
        current_lines = []

    for raw in lines:
        line = str(raw).rstrip("\n")
        stripped = line.strip()
        if not stripped and current_key is None:
            continue
        if stripped.startswith("#"):
            if current_key is not None:
                _commit()
            continue
        match = _BUG_METADATA_LINE_RE.fullmatch(stripped)
        if match is not None:
            _commit()
            current_key = _normalize_bug_field_name(str(match.group(1)))
            initial_value = str(match.group(2)).rstrip()
            current_lines = [initial_value] if initial_value else []
            continue
        if current_key is None:
            continue
        current_lines.append(line)
    _commit()
    return fields

def _bug_archive_bucket_from_link_target(link_target: str) -> str:
    token = str(link_target or "").strip()
    if not token:
        return ""
    path = Path(token)
    parts = list(path.parts)
    if len(parts) >= 3 and parts[0] == "bugs" and parts[1] == "archive":
        bucket = Path(*parts[2:-1]).as_posix() if len(parts) > 3 else ""
        return bucket or "archive"
    return ""

def canonicalize_bug_status(status: str) -> str:
    raw = str(status or "").strip()
    if not raw:
        return ""
    return _BUG_CANONICAL_STATUS_LABELS.get(raw.lower(), raw)

def _bug_is_open(status: str) -> bool:
    return str(status or "").strip().lower() not in _BUG_TERMINAL_STATUSES

def _ordered_bug_detail_sections(fields: Mapping[str, str]) -> list[dict[str, Any]]:
    normalized_fields: dict[str, dict[str, str]] = {}
    for raw_name, raw_value in fields.items():
        normalized_name = _normalize_bug_field_key(raw_name)
        if normalized_name in normalized_fields:
            continue
        value = str(raw_value).strip()
        if not value:
            continue
        normalized_fields[normalized_name] = {
            "name": _normalize_bug_field_name(raw_name),
            "value": value,
        }

    sections: list[dict[str, Any]] = []
    seen: set[str] = set()
    for name in _BUG_DETAIL_SECTION_ORDER:
        normalized_name = _normalize_bug_field_key(name)
        field_value = normalized_fields.get(normalized_name)
        if field_value is None:
            continue
        value = field_value["value"]
        if not value:
            continue
        seen.add(normalized_name)
        sections.append(
            {
                "field": name,
                "value": value,
                "kind": "primary",
            }
        )
    for normalized_name in normalized_fields:
        if normalized_name in seen or normalized_name in _BUG_CORE_FIELD_ORDER_SET:
            continue
        field_value = normalized_fields[normalized_name]
        field = field_value["name"]
        value = field_value["value"]
        if not value:
            continue
        seen.add(normalized_name)
        sections.append(
            {
                "field": field,
                "value": value,
                "kind": "extended",
            }
        )
    return sections

def _bug_summary_from_fields(fields: Mapping[str, str], lines: Sequence[str]) -> str:
    def _lookup_field(key: str) -> str:
        target = _normalize_bug_field_key(key)
        for field_name, raw_value in fields.items():
            if _normalize_bug_field_key(field_name) != target:
                continue
            value = str(raw_value).strip()
            if value:
                return value
        return ""

    for key in ("Description", "Impact", "Root Cause", "Solution"):
        value = _lookup_field(key)
        if value:
            return value
    return _first_summary(lines)

def _component_rows_from_index(
    component_index: Mapping[str, component_registry.ComponentEntry],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for component_id, entry in component_index.items():
        if not component_id or not isinstance(entry, component_registry.ComponentEntry):
            continue
        rows.append(
            {
                "component_id": component_id,
                "name": entry.name,
                "spec_ref": entry.spec_ref,
                "path_prefixes": list(entry.path_prefixes),
                "workstreams": list(entry.workstreams),
                "diagrams": list(entry.diagrams),
            }
        )
    return rows

def _build_bug_reference_lookup(
    *,
    rows: Sequence[Mapping[str, Any]],
    repo_root: Path,
) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for row in rows:
        if _is_bug_placeholder_row(row):
            continue
        link_target = _normalize_repo_token(_parse_link_target(str(row.get("Link", ""))), repo_root=repo_root)
        bug_id = resolve_casebook_bug_id(
            explicit_bug_id=str(row.get(BUG_ID_FIELD, "")).strip(),
            seed=link_target or f"{row.get('Date', '')}::{row.get('Title', '')}",
        )
        title = str(row.get("Title", "")).strip()
        date = str(row.get("Date", "")).strip()
        severity = str(row.get("Severity", "")).strip()
        status = str(row.get("Status", "")).strip()
        if not link_target and not bug_id:
            continue
        payload = {
            "bug_id": bug_id,
            "bug_key": link_target,
            "source_path": link_target,
            "title": title,
            "date": date,
            "severity": severity,
            "status": status,
        }
        variants = {
            bug_id,
            link_target,
            Path(link_target).name,
        }
        if link_target.startswith("odylith/casebook/bugs/"):
            variants.add(link_target.removeprefix("odylith/casebook/bugs/"))
        if link_target.startswith("odylith/casebook/bugs/archive/"):
            archive_relative = link_target.removeprefix("odylith/casebook/bugs/archive/")
            variants.add(archive_relative)
            variants.add(Path(archive_relative).name)
        for token in variants:
            normalized = str(token).strip().lower()
            if normalized and normalized not in lookup:
                lookup[normalized] = payload
    return lookup

def _related_bug_refs_from_text(
    *,
    text: str,
    bug_lookup: Mapping[str, Mapping[str, str]],
    repo_root: Path,
) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    seen: set[str] = set()
    candidates = list(_extract_path_refs(text=text, repo_root=repo_root))
    candidates.extend(
        match.group(0)
        for match in re.finditer(
            r"(?:odylith/casebook/bugs/)?(?:archive/[A-Za-z0-9._-]+/)?\d{4}-\d{2}-\d{2}-[A-Za-z0-9._-]+\.md",
            str(text or ""),
            flags=re.IGNORECASE,
        )
    )
    candidates.extend(
        match.group(0)
        for match in re.finditer(r"\bCB(?:X-[A-F0-9]{8}|-\d{3,})\b", str(text or ""), flags=re.IGNORECASE)
    )
    for raw in candidates:
        normalized = _normalize_repo_token(str(raw), repo_root=repo_root).lower()
        variants = [
            normalized,
            Path(normalized).name.lower() if normalized else "",
        ]
        if normalized and not normalized.startswith("odylith/casebook/bugs/"):
            variants.append(f"odylith/casebook/bugs/{normalized}")
        for token in variants:
            payload = bug_lookup.get(str(token).strip().lower())
            if payload is None:
                continue
            bug_key = str(payload.get("bug_key", "")).strip()
            if not bug_key or bug_key in seen:
                break
            refs.append(
                {
                    "bug_id": str(payload.get("bug_id", "")).strip(),
                    "bug_key": bug_key,
                    "source_path": str(payload.get("source_path", "")).strip(),
                    "title": str(payload.get("title", "")).strip(),
                    "date": str(payload.get("date", "")).strip(),
                    "severity": str(payload.get("severity", "")).strip(),
                    "status": str(payload.get("status", "")).strip(),
                }
            )
            seen.add(bug_key)
            break
    return refs

def _classify_bug_path_refs(path_refs: Sequence[str]) -> dict[str, list[str]]:
    buckets = {
        "code": [],
        "docs": [],
        "tests": [],
        "contracts": [],
    }
    for token in path_refs:
        path = str(token).strip()
        if not path or path.startswith("odylith/casebook/bugs/"):
            continue
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}-[A-Za-z0-9._-]+\.md", Path(path).name):
            continue
        if path.startswith("docs/"):
            buckets["docs"].append(path)
        elif path.startswith("tests/"):
            buckets["tests"].append(path)
        elif path.startswith(_CONTRACT_PATH_PREFIXES):
            buckets["contracts"].append(path)
        else:
            buckets["code"].append(path)
    return {name: _dedupe_strings(values) for name, values in buckets.items()}

def _component_matches_for_bug_paths(
    *,
    component_rows: Sequence[Mapping[str, Any]],
    component_index: Mapping[str, component_registry.ComponentEntry],
    path_refs: Sequence[str],
) -> list[dict[str, Any]]:
    component_ids = _components_for_paths(component_rows=component_rows, path_refs=path_refs)
    matches: list[dict[str, Any]] = []
    seen: set[str] = set()
    for component_id in component_ids:
        normalized_component_id = component_id.strip().lower()
        if not normalized_component_id or normalized_component_id in seen:
            continue
        seen.add(normalized_component_id)
        entry = component_index.get(component_id)
        if entry is None:
            continue
        matches.append(
            {
                "component_id": component_id,
                "name": entry.name,
                "spec_ref": entry.spec_ref,
                "workstreams": _dedupe_strings([str(token).strip().upper() for token in entry.workstreams if str(token).strip()]),
                "diagrams": _dedupe_strings([str(token).strip().upper() for token in entry.diagrams if str(token).strip()]),
            }
        )
    return matches

def _diagram_refs_for_bug_components(
    *,
    component_matches: Sequence[Mapping[str, Any]],
    diagram_lookup: Mapping[str, Mapping[str, str]],
) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in component_matches:
        for raw in match.get("diagrams", []) if isinstance(match.get("diagrams"), list) else []:
            diagram_id = str(raw).strip().upper()
            if not diagram_id or diagram_id in seen:
                continue
            payload = diagram_lookup.get(diagram_id)
            if payload is None:
                continue
            refs.append(dict(payload))
            seen.add(diagram_id)
    return refs

def _bug_intelligence_coverage(
    *,
    fields: Mapping[str, str],
    severity: str,
) -> dict[str, Any]:
    present_fields = [
        field
        for field in _BUG_INTELLIGENCE_ALL_FIELDS
        if str(fields.get(field, "")).strip()
    ]
    missing_fields = [
        field
        for field in _BUG_INTELLIGENCE_ALL_FIELDS
        if field not in present_fields
    ]
    critical = str(severity or "").strip().lower() in _BUG_CRITICAL_SEVERITIES
    required_fields = _BUG_INTELLIGENCE_REQUIRED_CRITICAL_FIELDS if critical else ()
    required_missing = [
        field
        for field in required_fields
        if not str(fields.get(field, "")).strip()
    ]
    return {
        "present_fields": present_fields,
        "missing_fields": missing_fields,
        "required_missing_fields": required_missing,
        "captured_count": len(present_fields),
        "total_fields": len(_BUG_INTELLIGENCE_ALL_FIELDS),
        "critical_expectations": critical,
    }

def _split_bug_guidance_items(value: str) -> list[str]:
    raw = str(value or "").strip()
    if not raw or raw == "-":
        return []
    lines = [
        str(line).strip().lstrip("-*").strip()
        for line in raw.replace("\r\n", "\n").split("\n")
        if str(line).strip()
    ]
    if len(lines) > 1:
        return _dedupe_strings(lines)
    if " / " in raw:
        return _dedupe_strings([part.strip() for part in raw.split(" / ")])
    return [raw]

def _bug_agent_guidance(
    *,
    fields: Mapping[str, str],
    ref_buckets: Mapping[str, Sequence[str]],
    component_matches: Sequence[Mapping[str, Any]],
    workstreams: Sequence[str],
    related_bug_refs: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    lessons: list[dict[str, str]] = []

    def _append_lesson(label: str, value: str) -> None:
        text = str(value or "").strip()
        if not text:
            return
        lessons.append({"label": label, "value": text})

    _append_lesson("Failure signature", str(fields.get("Failure Signature", "")))
    _append_lesson("Broken invariant", str(fields.get("Invariant Violated", "")))
    _append_lesson("Reintroduction guardrails", str(fields.get("Agent Guardrails", "") or fields.get("Prevention", "")))
    _append_lesson("Recovery posture", str(fields.get("Rollback/Forward Fix", "") or fields.get("Workaround", "")))
    _append_lesson("Regression proof", str(fields.get("Regression Tests Added", "")))
    _append_lesson("Monitoring follow-through", str(fields.get("Monitoring Updates", "")))

    preflight_checks = _split_bug_guidance_items(str(fields.get("Preflight Checks", "")))
    if ref_buckets.get("code"):
        preflight_checks.append(
            "Inspect linked code paths before editing: "
            + ", ".join(str(token).strip() for token in list(ref_buckets.get("code", []))[:3] if str(token).strip())
        )
    if ref_buckets.get("tests"):
        preflight_checks.append(
            "Keep the linked regression tests passing: "
            + ", ".join(str(token).strip() for token in list(ref_buckets.get("tests", []))[:3] if str(token).strip())
        )
    if ref_buckets.get("docs"):
        preflight_checks.append(
            "Review linked docs/runbooks: "
            + ", ".join(str(token).strip() for token in list(ref_buckets.get("docs", []))[:3] if str(token).strip())
        )
    if component_matches:
        preflight_checks.append(
            "Check Registry context for related components: "
            + ", ".join(
                str(match.get("name", "") or match.get("component_id", "")).strip()
                for match in list(component_matches)[:3]
                if str(match.get("name", "") or match.get("component_id", "")).strip()
            )
        )
    if workstreams:
        preflight_checks.append(
            "Review related Radar workstreams: "
            + ", ".join(str(token).strip() for token in list(workstreams)[:3] if str(token).strip())
        )
    if related_bug_refs:
        preflight_checks.append(
            "Compare prior bug history: "
            + ", ".join(
                str(ref.get("title", "") or ref.get("bug_key", "")).strip()
                for ref in list(related_bug_refs)[:3]
                if str(ref.get("title", "") or ref.get("bug_key", "")).strip()
            )
        )

    proof_paths = _dedupe_strings(
        [
            *[str(token).strip() for token in ref_buckets.get("code", [])],
            *[str(token).strip() for token in ref_buckets.get("tests", [])],
            *[str(token).strip() for token in ref_buckets.get("docs", [])],
            *[str(token).strip() for token in ref_buckets.get("contracts", [])],
        ]
    )
    return {
        "lessons": lessons,
        "preflight_checks": _dedupe_strings(preflight_checks),
        "proof_paths": proof_paths,
    }

def _load_component_match_rows_from_components(component_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for row in component_rows:
        if not isinstance(row, Mapping):
            continue
        metadata = _json_dict(row.get("metadata_json"))
        path_prefixes = list(metadata.get("path_prefixes", [])) if isinstance(metadata, Mapping) else []
        payloads.append(
            {
                "component_id": str(row.get("component_id", "")).strip(),
                "name": str(row.get("name", "")).strip(),
                "spec_ref": str(row.get("spec_ref", "")).strip(),
                "aliases": _json_list(row.get("aliases_json")),
                "path_prefixes": [str(token).strip() for token in path_prefixes if str(token).strip()],
                "workstreams": _json_list(row.get("workstreams_json")),
                "diagrams": _json_list(row.get("diagrams_json")),
            }
        )
    return payloads

def _load_component_match_rows(connection: Any) -> list[dict[str, Any]]:
    rows = connection.execute(
        "SELECT component_id, name, spec_ref, aliases_json, workstreams_json, diagrams_json, metadata_json FROM components"
    ).fetchall()
    return _load_component_match_rows_from_components(rows)

def _components_for_paths(*, component_rows: Sequence[Mapping[str, Any]], path_refs: Sequence[str]) -> list[str]:
    matched: set[str] = set()
    normalized_paths = [_normalize_repo_token(str(token), repo_root=Path(".")) for token in path_refs if str(token).strip()]
    for row in component_rows:
        component_id = str(row.get("component_id", "")).strip()
        if not component_id:
            continue
        candidates = [str(row.get("spec_ref", "")).strip()]
        candidates.extend(str(token).strip() for token in row.get("path_prefixes", []) if str(token).strip())
        for path_ref in normalized_paths:
            if any(_path_touches_watch(changed_path=path_ref, watch_path=candidate) for candidate in candidates):
                matched.add(component_id)
                break
    return sorted(matched)

def _load_adr_notes(*, repo_root: Path, component_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return odylith_context_engine_engineering_notes_runtime._load_adr_notes(
        repo_root=repo_root,
        component_rows=component_rows,
    )

def _load_invariant_notes(*, repo_root: Path, component_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return odylith_context_engine_engineering_notes_runtime._load_invariant_notes(
        repo_root=repo_root,
        component_rows=component_rows,
    )

def _load_data_ownership_notes(*, repo_root: Path, component_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return odylith_context_engine_engineering_notes_runtime._load_data_ownership_notes(
        repo_root=repo_root,
        component_rows=component_rows,
    )

def _load_section_bullet_notes(
    *,
    repo_root: Path,
    rel_path: str,
    note_kind: str,
    component_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return odylith_context_engine_engineering_notes_runtime._load_section_bullet_notes(
        repo_root=repo_root,
        rel_path=rel_path,
        note_kind=note_kind,
        component_rows=component_rows,
    )

def _markdown_title(*, lines: Sequence[str], fallback: str) -> str:
    return odylith_context_engine_engineering_notes_runtime._markdown_title(
        lines=lines,
        fallback=fallback,
    )

def _load_guidance_chunk_notes(
    *,
    repo_root: Path,
    component_rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], set[str]]:
    return odylith_context_engine_engineering_notes_runtime._load_guidance_chunk_notes(
        repo_root=repo_root,
        component_rows=component_rows,
    )

def _load_runbook_notes(*, repo_root: Path, component_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return odylith_context_engine_engineering_notes_runtime._load_runbook_notes(
        repo_root=repo_root,
        component_rows=component_rows,
    )

def _projection_state_row(
    *,
    name: str,
    fingerprint: str,
    row_count: int,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "name": str(name).strip(),
        "fingerprint": str(fingerprint).strip(),
        "row_count": int(row_count),
        "updated_utc": _utc_now(),
        "payload_json": _safe_json(payload or {}),
    }

def _empty_projection_tables() -> dict[str, list[dict[str, Any]]]:
    return {
        "projection_state": [],
        "workstreams": [],
        "releases": [],
        "plans": [],
        "bugs": [],
        "diagrams": [],
        "diagram_watch_paths": [],
        "components": [],
        "component_specs": [],
        "component_traceability": [],
        "registry_events": [],
        "codex_events": [],
        "traceability_edges": [],
        "delivery_scopes": [],
        "delivery_surfaces": [],
        "engineering_notes": [],
        "code_artifacts": [],
        "code_edges": [],
        "test_cases": [],
        "test_history": [],
    }

def warm_projections(
    *,
    repo_root: Path,
    force: bool = False,
    reason: str = "manual",
    scope: str = "default",
) -> dict[str, Any]:
    summary = odylith_context_engine_projection_compiler_runtime.warm_projections(
        repo_root=repo_root,
        force=force,
        reason=reason,
        scope=scope,
    )
    _record_process_warm_cache(repo_root=repo_root, scope=scope)
    return summary

def _runtime_enabled(runtime_mode: str) -> bool:
    return str(runtime_mode or "auto").strip().lower() != "standalone"


def _compatible_projection_scopes(scope: str) -> tuple[str, ...]:
    return odylith_memory_backend.compatible_projection_scopes(requested_scope=scope)


def _matched_runtime_projection(
    *,
    repo_root: Path,
    runtime_state: Mapping[str, Any],
    requested_scope: str,
) -> tuple[str, str]:
    root = Path(repo_root).resolve()
    runtime_scope = str(runtime_state.get("projection_scope", "")).strip().lower()
    runtime_fingerprint = str(runtime_state.get("projection_fingerprint", "")).strip()
    for candidate_scope in _compatible_projection_scopes(requested_scope):
        candidate_fingerprint = projection_input_fingerprint(repo_root=root, scope=candidate_scope)
        if runtime_scope == candidate_scope and runtime_fingerprint == candidate_fingerprint:
            return (candidate_scope, candidate_fingerprint)
    return ("", "")


def _local_backend_match_for_requested_scope(
    *,
    repo_root: Path,
    requested_scope: str,
) -> tuple[bool, str, str]:
    root = Path(repo_root).resolve()
    scope_token = str(requested_scope or "default").strip().lower() or "default"
    requested_fingerprint = projection_input_fingerprint(repo_root=root, scope=scope_token)
    for candidate_scope in _compatible_projection_scopes(scope_token):
        candidate_fingerprint = projection_input_fingerprint(repo_root=root, scope=candidate_scope)
        if odylith_memory_backend.local_backend_ready_for_projection(
            repo_root=root,
            projection_fingerprint=candidate_fingerprint,
            projection_scope=candidate_scope,
        ):
            return (True, candidate_scope, candidate_fingerprint)
    return (False, scope_token, requested_fingerprint)


def _warm_runtime_can_reuse_snapshot(
    *,
    repo_root: Path,
    scope: str,
    requested_fingerprint: str,
) -> bool:
    root = Path(repo_root).resolve()
    scope_token = str(scope or "default").strip().lower() or "default"
    if not projection_snapshot_path(repo_root=root).is_file():
        return False
    runtime_state = read_runtime_state(repo_root=root)
    matched_scope, matched_fingerprint = _matched_runtime_projection(
        repo_root=root,
        runtime_state=runtime_state,
        requested_scope=scope_token,
    )
    candidate_scope = matched_scope
    candidate_fingerprint = matched_fingerprint
    if not candidate_scope:
        snapshot_manifest = odylith_projection_snapshot.load_snapshot(repo_root=root)
        snapshot_scope = str(snapshot_manifest.get("projection_scope", "")).strip().lower()
        snapshot_fingerprint = str(snapshot_manifest.get("projection_fingerprint", "")).strip()
        if (
            bool(snapshot_manifest.get("ready"))
            and snapshot_scope
            and snapshot_fingerprint
            and odylith_memory_backend.projection_scope_satisfies(
                available_scope=snapshot_scope,
                requested_scope=scope_token,
            )
            and snapshot_fingerprint == projection_input_fingerprint(repo_root=root, scope=snapshot_scope)
        ):
            candidate_scope = snapshot_scope
            candidate_fingerprint = snapshot_fingerprint
    if not candidate_scope:
        return False
    if not odylith_memory_backend.backend_dependencies_available():
        return True
    return odylith_memory_backend.local_backend_ready_for_projection(
        repo_root=root,
        projection_fingerprint=candidate_fingerprint or requested_fingerprint,
        projection_scope=candidate_scope or scope_token,
    )


def _record_process_warm_cache(
    *,
    repo_root: Path,
    scope: str,
    warmed_at: float | None = None,
) -> None:
    root = Path(repo_root).resolve()
    scope_token = str(scope or "default").strip().lower() or "default"
    applied_at = time.monotonic() if warmed_at is None else float(warmed_at)
    cache_updates: list[tuple[str, str]] = [
        (f"{root}:{scope_token}", projection_input_fingerprint(repo_root=root, scope=scope_token))
    ]
    if scope_token == "full":
        cache_updates.extend(
            [
                (f"{root}:default", projection_input_fingerprint(repo_root=root, scope="default")),
                (f"{root}:reasoning", projection_input_fingerprint(repo_root=root, scope="reasoning")),
            ]
        )
    elif scope_token == "reasoning":
        cache_updates.append(
            (f"{root}:default", projection_input_fingerprint(repo_root=root, scope="default"))
        )
    for target_key, fingerprint in cache_updates:
        _PROCESS_WARM_CACHE[target_key] = applied_at + _PROCESS_WARM_CACHE_TTL_SECONDS
        _PROCESS_WARM_CACHE_FINGERPRINTS[target_key] = str(fingerprint).strip()


def _warm_runtime(
    *,
    repo_root: Path,
    runtime_mode: str,
    reason: str,
    scope: str = "default",
) -> bool:
    root = Path(repo_root).resolve()
    scope_token = str(scope or "default").strip().lower()
    try:
        from odylith.runtime.governance import sync_session as governed_sync_session
    except ImportError:  # pragma: no cover - defensive bootstrap fallback
        governed_sync_session = None
    if governed_sync_session is not None:
        session = governed_sync_session.active_sync_session()
        if session is not None and session.repo_root == root:
            return bool(
                session.get_or_compute(
                    namespace="runtime_warm",
                    key=scope_token,
                    builder=lambda: _warm_runtime_uncached(
                        repo_root=root,
                        runtime_mode=runtime_mode,
                        reason=reason,
                        scope=scope_token,
                    ),
                )
            )
    return _warm_runtime_uncached(
        repo_root=root,
        runtime_mode=runtime_mode,
        reason=reason,
        scope=scope_token,
    )


def _warm_runtime_uncached(
    *,
    repo_root: Path,
    runtime_mode: str,
    reason: str,
    scope: str = "default",
) -> bool:
    if not _runtime_enabled(runtime_mode):
        return False
    root = Path(repo_root).resolve()
    scope_token = str(scope or "default").strip().lower()
    cache_key = f"{root}:{scope_token}"
    now = time.monotonic()
    cached_until = _PROCESS_WARM_CACHE.get(cache_key)
    cached_fingerprint = _PROCESS_WARM_CACHE_FINGERPRINTS.get(cache_key, "")
    requested_fingerprint = projection_input_fingerprint(repo_root=root, scope=scope_token)
    if cached_until is not None and cached_until > now and cached_fingerprint == requested_fingerprint:
        return True
    if cached_fingerprint and cached_fingerprint != requested_fingerprint:
        _PROCESS_WARM_CACHE.pop(cache_key, None)
        _PROCESS_WARM_CACHE_FINGERPRINTS.pop(cache_key, None)
    if cached_fingerprint and cached_fingerprint == requested_fingerprint:
        _PROCESS_WARM_CACHE[cache_key] = now + _PROCESS_WARM_CACHE_TTL_SECONDS
        return True
    if _warm_runtime_can_reuse_snapshot(
        repo_root=root,
        scope=scope_token,
        requested_fingerprint=requested_fingerprint,
    ):
        _record_process_warm_cache(repo_root=root, scope=scope_token)
        return True
    try:
        warm_projections(repo_root=root, reason=reason, scope=scope_token)
    except Exception:
        if str(runtime_mode or "").strip().lower() == "daemon":
            raise
        return False
    return True

def _projection_cache_signature(
    *,
    repo_root: Path,
    scope: str = "reasoning",
) -> str:
    root = Path(repo_root).resolve()
    scope_token = str(scope or "reasoning").strip().lower() or "reasoning"
    return projection_input_fingerprint(repo_root=root, scope=scope_token)

def _cached_projection_rows(
    *,
    repo_root: Path,
    cache_name: str,
    loader: Callable[[], Any],
    scope: str = "reasoning",
) -> Any:
    root = Path(repo_root).resolve()
    signature = _projection_cache_signature(repo_root=root, scope=scope)
    cache_key = f"{root}:{str(cache_name).strip()}"
    cached = _PROCESS_PROJECTION_ROWS_CACHE.get(cache_key)
    if cached is not None and cached[0] == signature:
        return cached[1]
    value = loader()
    _PROCESS_PROJECTION_ROWS_CACHE[cache_key] = (signature, value)
    return value

def clear_runtime_process_caches(*, repo_root: Path | None = None) -> None:
    """Clear process-local Odylith caches used by warm/cold benchmark lanes."""

    if repo_root is None:
        _PROCESS_PROJECTED_INPUTS_CACHE.clear()
        _PROCESS_PROJECTION_INPUT_FINGERPRINT_CACHE.clear()
        _PROCESS_PATH_FINGERPRINT_CACHE.clear()
        _PROCESS_WARM_CACHE.clear()
        _PROCESS_WARM_CACHE_FINGERPRINTS.clear()
        _PROCESS_PROJECTION_ROWS_CACHE.clear()
        _PROCESS_PROJECTION_CONNECTION_CACHE.clear()
        _PROCESS_OPTIMIZATION_SNAPSHOT_CACHE.clear()
        _PROCESS_MISS_RECOVERY_INDEX_CACHE.clear()
        _PROCESS_PATH_SCOPE_CACHE.clear()
        _PROCESS_PATH_SIGNAL_PROFILE_CACHE.clear()
        _PROCESS_ARCHITECTURE_PACKET_CACHE.clear()
        _PROCESS_ORCHESTRATION_ADOPTION_SNAPSHOT_CACHE.clear()
        projection_repo_state_runtime.clear_projection_repo_state_cache()
        tooling_guidance_catalog.clear_process_guidance_catalog_cache()
    else:
        root = Path(repo_root).resolve()
        prefix = f"{root}:"
        projection_repo_state_runtime.clear_projection_repo_state_cache(repo_root=root)
        for cache in (
            _PROCESS_PROJECTED_INPUTS_CACHE,
            _PROCESS_PROJECTION_INPUT_FINGERPRINT_CACHE,
            _PROCESS_PATH_FINGERPRINT_CACHE,
            _PROCESS_WARM_CACHE,
            _PROCESS_WARM_CACHE_FINGERPRINTS,
            _PROCESS_PROJECTION_ROWS_CACHE,
            _PROCESS_PROJECTION_CONNECTION_CACHE,
            _PROCESS_OPTIMIZATION_SNAPSHOT_CACHE,
            _PROCESS_MISS_RECOVERY_INDEX_CACHE,
            _PROCESS_PATH_SCOPE_CACHE,
            _PROCESS_PATH_SIGNAL_PROFILE_CACHE,
            _PROCESS_ARCHITECTURE_PACKET_CACHE,
            _PROCESS_ORCHESTRATION_ADOPTION_SNAPSHOT_CACHE,
        ):
            for key in [token for token in list(cache) if str(token).startswith(prefix)]:
                cache.pop(key, None)
        tooling_guidance_catalog.clear_process_guidance_catalog_cache(repo_root=root)
    # Architecture caches are process-local and safe to clear wholesale here.
    odylith_architecture_mode._PROCESS_ARCHITECTURE_BUNDLE_CACHE.clear()  # noqa: SLF001
    odylith_architecture_mode._PROCESS_ARCHITECTURE_STRUCTURAL_BASE_CACHE.clear()  # noqa: SLF001
    odylith_architecture_mode._PROCESS_ARCHITECTURE_STRUCTURAL_CORE_CACHE.clear()  # noqa: SLF001
    odylith_architecture_mode._PROCESS_ARCHITECTURE_BENCHMARK_CASES_CACHE.clear()  # noqa: SLF001
    odylith_architecture_mode._PROCESS_ARCHITECTURE_SOURCE_HASH_CACHE.clear()  # noqa: SLF001
    odylith_architecture_mode._PROCESS_ARCHITECTURE_TRACEABILITY_INDEX_CACHE.clear()  # noqa: SLF001
    odylith_architecture_mode._PROCESS_ARCHITECTURE_WORKSTREAM_INDEX_CACHE.clear()

def prime_reasoning_projection_cache(*, repo_root: Path) -> None:
    root = Path(repo_root).resolve()
    connection = _connect(root)
    try:
        _cached_projection_rows(
            repo_root=root,
            cache_name="components_full_rows",
            loader=lambda: [dict(row) for row in connection.execute("SELECT * FROM components").fetchall()],
        )
        workstream_rows = _cached_projection_rows(
            repo_root=root,
            cache_name="workstreams_full_rows",
            loader=lambda: [dict(row) for row in connection.execute("SELECT * FROM workstreams").fetchall()],
        )
        traceability_rows = _cached_projection_rows(
            repo_root=root,
            cache_name="workstream_traceability_rows",
            loader=lambda: [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT source_id, target_kind, target_id
                    FROM traceability_edges
                    WHERE target_kind IN ('runbook', 'doc', 'code')
                """
                ).fetchall()
            ],
        )
        _cached_projection_rows(
            repo_root=root,
            cache_name="workstream_direct_match_rows",
            loader=lambda: [
                {
                    "source_id": str(row.get("idea_id", "")).strip().upper(),
                    "target_path": target_path,
                }
                for row in workstream_rows
                for target_path in (
                    _normalize_repo_token(str(row.get("source_path", "")), repo_root=root),
                    _normalize_repo_token(str(row.get("idea_file", "")), repo_root=root),
                    _normalize_repo_token(str(row.get("promoted_to_plan", "")), repo_root=root),
                )
                if str(row.get("idea_id", "")).strip() and target_path
            ],
        )
        _cached_projection_rows(
            repo_root=root,
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
                for row in traceability_rows
                if (target_path := _normalize_repo_token(str(row.get("target_id", "")), repo_root=root))
            ],
        )
        _cached_projection_rows(
            repo_root=root,
            cache_name="engineering_notes_full_rows",
            loader=lambda: [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM engineering_notes ORDER BY note_kind, note_id"
                ).fetchall()
            ],
        )
        _cached_projection_rows(
            repo_root=root,
            cache_name="code_edges_full_rows",
            loader=lambda: [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM code_edges ORDER BY source_path, relation, target_path"
                ).fetchall()
            ],
        )
        _cached_projection_rows(
            repo_root=root,
            cache_name="bugs_full_rows",
            loader=lambda: [dict(row) for row in connection.execute("SELECT * FROM bugs ORDER BY date DESC, title").fetchall()],
        )
        _cached_projection_rows(
            repo_root=root,
            cache_name="plans_full_rows",
            loader=lambda: [dict(row) for row in connection.execute("SELECT * FROM plans ORDER BY plan_path").fetchall()],
        )
        _cached_projection_rows(
            repo_root=root,
            cache_name="diagrams_full_rows",
            loader=lambda: [dict(row) for row in connection.execute("SELECT * FROM diagrams ORDER BY diagram_id").fetchall()],
        )
        _cached_projection_rows(
            repo_root=root,
            cache_name="diagram_rows",
            loader=lambda: [
                dict(row)
                for row in connection.execute(
                    "SELECT diagram_id, slug, title, source_mmd, source_svg, source_png, source_mmd_hash FROM diagrams"
                ).fetchall()
            ],
        )
        _cached_projection_rows(
            repo_root=root,
            cache_name="diagram_watch_rows",
            loader=lambda: [dict(row) for row in connection.execute("SELECT diagram_id, watch_path FROM diagram_watch_paths").fetchall()],
        )
        _cached_projection_rows(
            repo_root=root,
            cache_name="tests_full_rows",
            loader=lambda: [dict(row) for row in connection.execute("SELECT * FROM test_cases ORDER BY test_path, test_name").fetchall()],
        )
        _cached_miss_recovery_projection_index(connection, repo_root=root)
    finally:
        connection.close()
    odylith_architecture_mode.prime_architecture_projection_cache(repo_root=root)

def _path_signature(path: Path) -> tuple[bool, int, int]:
    target = Path(path).resolve()
    if not target.exists():
        return (False, 0, 0)
    try:
        stat = target.stat()
    except OSError:
        return (False, 0, 0)
    return (True, int(stat.st_mtime_ns), int(stat.st_size))

def _architecture_bundle_mermaid_signature_hash(
    *,
    repo_root: Path,
    bundle: Mapping[str, Any],
) -> str:
    root = Path(repo_root).resolve()
    rows: list[dict[str, Any]] = []
    for raw in bundle.get("diagrams", []):
        if not isinstance(raw, Mapping):
            continue
        source_mmd = _normalize_repo_token(str(raw.get("source_mmd", "")).strip(), repo_root=root)
        if not source_mmd:
            continue
        rows.append(
            {
                "diagram_id": str(raw.get("diagram_id", "")).strip(),
                "source_mmd": source_mmd,
                "signature": _path_signature(root / source_mmd),
            }
        )
    rows.sort(key=lambda row: (str(row.get("diagram_id", "")), str(row.get("source_mmd", ""))))
    return odylith_context_cache.fingerprint_payload(rows or [{"diagram_id": "", "source_mmd": "", "signature": (False, 0, 0)}])

def _bootstraps_signature(*, repo_root: Path) -> tuple[bool, int, int]:
    root = bootstraps_root(repo_root=repo_root)
    if not root.is_dir():
        return (False, 0, 0)
    latest_mtime_ns = 0
    count = 0
    for path in root.glob("*.json"):
        count += 1
        try:
            latest_mtime_ns = max(latest_mtime_ns, int(path.stat().st_mtime_ns))
        except OSError:
            continue
    return (True, count, latest_mtime_ns)

def _runtime_optimization_cache_signature(*, repo_root: Path) -> tuple[Any, ...]:
    root = Path(repo_root).resolve()
    switch_snapshot = _odylith_switch_snapshot(repo_root=root)
    return (
        json.dumps(switch_snapshot, sort_keys=True, separators=(",", ":")),
        _path_signature(odylith_control_state.timings_path(repo_root=root)),
        _path_signature(odylith_evaluation_ledger.ledger_path(repo_root=root)),
        _bootstraps_signature(repo_root=root),
    )

def _merge_search_results(
    *,
    local_rows: Sequence[Mapping[str, Any]],
    remote_rows: Sequence[Mapping[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for source, rows in (("local", local_rows), ("remote", remote_rows)):
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            key = (
                str(row.get("kind", "")).strip(),
                str(row.get("entity_id", "")).strip(),
                str(row.get("path", "")).strip(),
            )
            if key in seen:
                continue
            seen.add(key)
            payload = dict(row)
            payload.setdefault("source", source)
            merged.append(payload)
            if len(merged) >= max(1, int(limit)):
                return merged
    return merged

def _repair_odylith_backend(
    connection: Any,
    *,
    repo_root: Path,
    reason: str,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    if not odylith_memory_backend.backend_dependencies_available():
        return {
            "ready": False,
            "status": "dependencies_missing",
            "reason": str(reason).strip() or "repair_skipped",
        }
    runtime_state = read_runtime_state(repo_root=root)
    scope = str(runtime_state.get("projection_scope", "")).strip().lower() or "full"
    projection_fingerprint = str(runtime_state.get("projection_fingerprint", "")).strip() or projection_input_fingerprint(
        repo_root=root,
        scope=scope,
    )
    started_at = time.perf_counter()
    try:
        summary = odylith_memory_backend.materialize_local_backend(
            repo_root=root,
            connection=connection,
            projection_fingerprint=projection_fingerprint,
            projection_scope=scope,
        )
    except Exception as exc:
        summary = {
            "ready": False,
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
        }
    record_runtime_timing(
        repo_root=root,
        category="projection",
        operation="odylith_backend_repair",
        duration_ms=(time.perf_counter() - started_at) * 1000.0,
        metadata={
            "reason": str(reason).strip() or "repair",
            "projection_scope": scope,
            "projection_fingerprint": projection_fingerprint,
            "ready": bool(summary.get("ready")),
            "status": str(summary.get("status", "")).strip(),
            "document_count": int(summary.get("document_count", 0) or 0),
            "edge_count": int(summary.get("edge_count", 0) or 0),
        },
    )
    return summary

def _search_row_from_entity(entity: Mapping[str, Any], *, score: float = 0.0) -> dict[str, Any]:
    return {
        "kind": str(entity.get("kind", "")).strip(),
        "entity_id": str(entity.get("entity_id", "")).strip(),
        "title": str(entity.get("title", "")).strip(),
        "path": str(entity.get("path", "")).strip(),
        "score": float(score),
    }

def search_entities_payload(
    *,
    repo_root: Path,
    query: str,
    limit: int = 20,
    kinds: Sequence[str] | None = None,
    runtime_mode: str = "auto",
) -> dict[str, Any]:
    """Search the runtime store and expose when raw repo scanning is still required."""
    root = Path(repo_root).resolve()
    odylith_ablation_active = _odylith_ablation_active(repo_root=root)
    started_at = time.perf_counter()
    normalized_query = str(query or "").strip()
    normalized_kinds = tuple(_normalize_entity_kind(kind) for kind in (kinds or []) if str(kind).strip())
    if odylith_ablation_active and _odylith_query_targets_disabled(repo_root=root, query=normalized_query):
        return {
            "query": normalized_query,
            "requested_kinds": list(normalized_kinds),
            "runtime_ready": True,
            "retrieval_mode": "disabled_component",
            "results": [],
            "full_scan_recommended": False,
            "full_scan_reason": "odylith_disabled",
            "fallback_scan": {
                "performed": False,
                "terms": _full_scan_terms(repo_root=root, query=normalized_query),
                "roots": _available_full_scan_roots(repo_root=root),
                "commands": [],
                "results": [],
                "reason": "odylith_disabled",
                "reason_message": "Odylith is disabled for ablation; its platform component is intentionally suppressed.",
                "changed_paths": [],
            },
        }
    runtime_ready = _warm_runtime(repo_root=root, runtime_mode=runtime_mode, reason="query", scope="reasoning")
    if not runtime_ready:
        fallback_scan = _full_scan_guidance(
            repo_root=root,
            reason="runtime_unavailable",
            query=normalized_query,
            perform_scan=True,
            result_limit=max(8, int(limit) * 4),
        )
        record_runtime_timing(
            repo_root=root,
            category="reasoning",
            operation="query",
            duration_ms=(time.perf_counter() - started_at) * 1000.0,
            metadata={
                "query": normalized_query,
                "result_count": 0,
                "retrieval_mode": "full_repo_scan" if fallback_scan.get("results") else "none",
                "runtime_ready": False,
            },
        )
        return {
            "query": normalized_query,
            "requested_kinds": list(normalized_kinds),
            "runtime_ready": False,
            "retrieval_mode": "full_repo_scan" if fallback_scan.get("results") else "none",
            "results": [],
            "full_scan_recommended": True,
            "full_scan_reason": "runtime_unavailable",
            "fallback_scan": fallback_scan,
        }
    use_hybrid = _env_truthy("ODYLITH_HYBRID_RERANK")
    backend_ready, _backend_scope, _backend_fingerprint = _local_backend_match_for_requested_scope(
        repo_root=root,
        requested_scope="reasoning",
    )
    repair_attempted = False

    def _repair_backend_once(reason: str) -> bool:
        nonlocal backend_ready, repair_attempted
        if repair_attempted:
            return backend_ready
        repair_attempted = True
        connection = _connect(root)
        try:
            summary = _repair_odylith_backend(connection, repo_root=root, reason=reason)
        finally:
            connection.close()
        backend_ready = bool(summary.get("ready"))
        return backend_ready

    if not backend_ready and odylith_memory_backend.backend_dependencies_available():
        backend_ready = _repair_backend_once("query_backend_not_ready")
    exact_results: list[dict[str, Any]] = []
    if backend_ready:
        try:
            exact_results = odylith_memory_backend.exact_lookup(
                repo_root=root,
                query=normalized_query,
                limit=max(1, int(limit)),
                kinds=normalized_kinds,
            )
        except Exception:
            if _repair_backend_once("query_exact_lookup_error"):
                try:
                    exact_results = odylith_memory_backend.exact_lookup(
                        repo_root=root,
                        query=normalized_query,
                        limit=max(1, int(limit)),
                        kinds=normalized_kinds,
                    )
                except Exception:
                    backend_ready = False
            if not exact_results and not backend_ready:
                backend_ready = False
    if not exact_results and not backend_ready:
        connection = _connect(root)
        try:
            exact_results = _projection_exact_search_results(
                connection,
                repo_root=root,
                query=normalized_query,
                kinds=normalized_kinds,
                limit=max(1, int(limit)),
            )
        finally:
            connection.close()
    if odylith_ablation_active:
        exact_results = _filter_odylith_search_results(repo_root=root, results=exact_results)
    if exact_results:
        record_runtime_timing(
            repo_root=root,
            category="reasoning",
            operation="query",
            duration_ms=(time.perf_counter() - started_at) * 1000.0,
            metadata={
                "query": normalized_query,
                "result_count": len(exact_results),
                "retrieval_mode": "exact",
                "runtime_ready": True,
            },
        )
        return {
            "query": normalized_query,
            "requested_kinds": list(normalized_kinds),
            "runtime_ready": True,
            "retrieval_mode": "exact",
            "results": exact_results,
            "full_scan_recommended": False,
            "full_scan_reason": "",
            "fallback_scan": _full_scan_guidance(repo_root=root, reason="", query=normalized_query),
        }

    local_sparse_results: list[dict[str, Any]] = []
    if backend_ready:
        try:
            local_sparse_results = odylith_memory_backend.sparse_search(
                repo_root=root,
                query=normalized_query,
                limit=max(1, int(limit)),
                kinds=normalized_kinds,
            )
        except Exception:
            if _repair_backend_once("query_sparse_search_error"):
                try:
                    local_sparse_results = odylith_memory_backend.sparse_search(
                        repo_root=root,
                        query=normalized_query,
                        limit=max(1, int(limit)),
                        kinds=normalized_kinds,
                    )
                except Exception:
                    backend_ready = False
            if not local_sparse_results and not backend_ready:
                backend_ready = False
    if use_hybrid and local_sparse_results and backend_ready:
        try:
            local_results = odylith_memory_backend.hybrid_rerank_search(
                repo_root=root,
                query=normalized_query,
                limit=max(1, int(limit)),
                kinds=normalized_kinds,
                sparse_rows=local_sparse_results,
            )
            retrieval_mode = "hybrid_local"
        except Exception:
            if _repair_backend_once("query_hybrid_rerank_error"):
                try:
                    local_results = odylith_memory_backend.hybrid_rerank_search(
                        repo_root=root,
                        query=normalized_query,
                        limit=max(1, int(limit)),
                        kinds=normalized_kinds,
                        sparse_rows=local_sparse_results,
                    )
                    retrieval_mode = "hybrid_local"
                except Exception:
                    local_results = local_sparse_results
                    retrieval_mode = "tantivy_sparse" if local_results else "none"
            else:
                backend_ready = False
                local_results = local_sparse_results
                retrieval_mode = "tantivy_sparse" if local_sparse_results else "none"
    else:
        local_results = local_sparse_results
        retrieval_mode = "tantivy_sparse" if local_sparse_results and backend_ready else "none"

    remote_results: list[dict[str, Any]] = []
    remote_config = odylith_remote_retrieval.remote_config(repo_root=root)
    remote_mode = str(remote_config.get("mode", "")).strip()
    remote_ready = bool(remote_config.get("enabled")) and str(remote_config.get("status", "")).strip() == "ready"
    if remote_ready and (remote_mode == "remote_only" or len(local_results) < max(1, int(limit))):
        try:
            remote_results = odylith_remote_retrieval.query_remote(
                repo_root=root,
                query=normalized_query,
                limit=max(1, int(limit)),
                kinds=normalized_kinds,
            )
        except Exception:
            remote_results = []

    use_remote_only = remote_ready and remote_mode == "remote_only" and bool(remote_results)
    results = _merge_search_results(
        local_rows=[] if use_remote_only else local_results,
        remote_rows=remote_results,
        limit=max(1, int(limit)),
    )
    if use_remote_only:
        retrieval_mode = "vespa_remote"
    elif remote_results:
        retrieval_mode = "tantivy_plus_vespa" if local_results else "vespa_remote"

    if odylith_ablation_active:
        results = _filter_odylith_search_results(repo_root=root, results=results)
    has_runtime_results = bool(results)
    repo_scan_reason = "odylith_backend_unavailable" if not backend_ready and not remote_results else "no_runtime_results"
    full_scan_reason = (
        "runtime_sparse_only"
        if has_runtime_results and retrieval_mode in {"tantivy_sparse", "hybrid_local", "tantivy_plus_vespa", "vespa_remote"}
        else "repo_scan_candidate_only"
        if has_runtime_results and retrieval_mode == "full_repo_scan"
        else repo_scan_reason
    )
    fallback_scan = _full_scan_guidance(
        repo_root=root,
        reason=full_scan_reason,
        query=normalized_query,
        perform_scan=True,
        result_limit=max(8, int(limit) * 4),
    )
    if not has_runtime_results:
        connection = _connect(root)
        try:
            results = _repo_scan_candidate_search_results(
                connection,
                repo_root=root,
                fallback_scan=fallback_scan,
                query=normalized_query,
                kinds=normalized_kinds,
                limit=max(1, int(limit)),
            )
        finally:
            connection.close()
        has_runtime_results = bool(results)
        if has_runtime_results:
            retrieval_mode = "full_repo_scan"
            full_scan_reason = "odylith_backend_unavailable" if not backend_ready else "repo_scan_candidate_only"
        else:
            retrieval_mode = "full_repo_scan" if fallback_scan.get("results") else "none"
    if isinstance(fallback_scan, dict):
        fallback_scan["reason"] = full_scan_reason
        fallback_scan["reason_message"] = _full_scan_reason_message(full_scan_reason)
    record_runtime_timing(
        repo_root=root,
        category="reasoning",
        operation="query",
        duration_ms=(time.perf_counter() - started_at) * 1000.0,
        metadata={
            "query": normalized_query,
            "result_count": len(results),
            "retrieval_mode": retrieval_mode,
            "runtime_ready": True,
        },
    )
    return {
        "query": normalized_query,
        "requested_kinds": list(normalized_kinds),
        "runtime_ready": True,
        "retrieval_mode": retrieval_mode,
        "results": results,
        "full_scan_recommended": True,
        "full_scan_reason": full_scan_reason,
        "fallback_scan": fallback_scan,
    }

def search_entities(
    *,
    repo_root: Path,
    query: str,
    limit: int = 20,
    kinds: Sequence[str] | None = None,
    runtime_mode: str = "auto",
) -> list[dict[str, Any]]:
    payload = search_entities_payload(
        repo_root=repo_root,
        query=query,
        limit=limit,
        kinds=kinds,
        runtime_mode=runtime_mode,
    )
    return [dict(row) for row in payload.get("results", []) if isinstance(row, Mapping)]

def _miss_recovery_query_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    seen: set[str] = set()
    for raw in re.findall(r"[A-Za-z0-9]+", str(text or "").replace("_", " ").replace("-", " ")):
        token = raw.strip().lower()
        if len(token) < 3 or token in _MISS_RECOVERY_GENERIC_QUERY_TOKENS or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens

def _build_miss_recovery_queries(
    *,
    changed_paths: Sequence[str],
    component_ids: Sequence[str],
) -> list[str]:
    queries: list[str] = []
    seen: set[str] = set()
    anchor_tokens: set[str] = set()

    def _add(value: str) -> None:
        query_tokens = _miss_recovery_query_tokens(value)
        if not query_tokens:
            return
        anchor_tokens.update(query_tokens)
        phrase = " ".join(query_tokens[:4])
        if phrase in seen:
            return
        seen.add(phrase)
        queries.append(phrase)

    for raw_path in changed_paths:
        path_ref = str(raw_path).strip()
        if not path_ref:
            continue
        path_obj = Path(path_ref)
        _add(path_obj.stem)
        parent_name = str(path_obj.parent.name).strip()
        if parent_name and parent_name not in {"scripts", "tests", "docs", "source", "runbooks", "components", "specs"}:
            _add(f"{parent_name} {path_obj.stem}")
    for component_id in component_ids:
        component_tokens = _miss_recovery_query_tokens(component_id)
        if anchor_tokens and not set(component_tokens).intersection(anchor_tokens):
            continue
        _add(component_id)
    return queries[:4]

def _repo_scan_inferred_kind(path_ref: str) -> str:
    path = str(path_ref or "").strip().replace("\\", "/").strip("/")
    if not path:
        return ""
    if path.startswith("docs/runbooks/"):
        return "runbook"
    if path.startswith("odylith/technical-plans/"):
        return "plan"
    if path.startswith("odylith/casebook/bugs/"):
        return "bug"
    if path.startswith("odylith/radar/source/"):
        return "workstream"
    if path.startswith("odylith/atlas/source/"):
        return "diagram"
    if path.startswith("tests/"):
        return "test"
    if path.endswith(".py") or path.endswith(".ts") or path.endswith(".tsx") or path.endswith(".js") or path.endswith(".sh"):
        return "code"
    return ""

def _repo_scan_recovery_rows(
    connection: Any,
    *,
    repo_root: Path,
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    query_tokens = _miss_recovery_query_tokens(query)
    scan = _run_full_scan(repo_root=repo_root, terms=query_tokens, limit=max(8, int(limit) * 3))
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for rank, hit in enumerate(scan.get("results", []), start=1):
        if not isinstance(hit, Mapping):
            continue
        path_ref = _normalize_repo_token(str(hit.get("path", "")).strip(), repo_root=repo_root)
        if not path_ref:
            continue
        entity = _entity_by_path(connection, repo_root=repo_root, path_ref=path_ref)
        if entity is None:
            if bool(_path_signal_profile(path_ref).get("shared")):
                continue
            kind = _repo_scan_inferred_kind(path_ref)
            if not kind:
                continue
            entity = {
                "kind": kind,
                "entity_id": path_ref,
                "title": Path(path_ref).name,
                "path": path_ref,
            }
        kind = str(entity.get("kind", "")).strip()
        if kind not in _MISS_RECOVERY_ALLOWED_KINDS:
            continue
        entity_id = str(entity.get("entity_id", "")).strip()
        key = (kind, entity_id, path_ref)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "kind": kind,
                "entity_id": entity_id or path_ref,
                "title": str(entity.get("title", "")).strip() or Path(path_ref).name,
                "path": str(entity.get("path", "")).strip() or path_ref,
                "score": max(0.0, float(max(1, int(limit) * 3) - rank + 1)),
                "query": " ".join(query_tokens),
                "mode": "repo_scan_fallback",
            }
        )
        if len(rows) >= max(1, int(limit)):
            break
    return rows

def _recovery_search_payload(
    connection: Any,
    *,
    repo_root: Path,
    query: str,
    limit: int,
) -> dict[str, Any]:
    query_tokens = _miss_recovery_query_tokens(query)
    if not query_tokens:
        return {"mode": "none", "rows": []}
    exact_rows = _projection_miss_recovery_rows(
        connection,
        repo_root=repo_root,
        query=" ".join(query_tokens),
        limit=limit,
    )
    if exact_rows:
        return {
            "mode": "projection_exact_rescue",
            "rows": exact_rows,
        }
    backend_ready, _backend_scope, _backend_fingerprint = _local_backend_match_for_requested_scope(
        repo_root=repo_root,
        requested_scope="reasoning",
    )
    if not backend_ready and odylith_memory_backend.backend_dependencies_available():
        summary = _repair_odylith_backend(connection, repo_root=repo_root, reason="miss_recovery_backend_not_ready")
        backend_ready = bool(summary.get("ready"))
    if backend_ready:
        try:
            rows = odylith_memory_backend.sparse_search(
                repo_root=repo_root,
                query=" ".join(query_tokens),
                limit=max(1, int(limit)),
                kinds=_MISS_RECOVERY_ALLOWED_KINDS,
            )
        except Exception:
            summary = _repair_odylith_backend(connection, repo_root=repo_root, reason="miss_recovery_sparse_error")
            if not bool(summary.get("ready")):
                rows = []
            else:
                try:
                    rows = odylith_memory_backend.sparse_search(
                        repo_root=repo_root,
                        query=" ".join(query_tokens),
                        limit=max(1, int(limit)),
                        kinds=_MISS_RECOVERY_ALLOWED_KINDS,
                    )
                except Exception:
                    rows = []
        try:
            return {
                "mode": "tantivy_sparse_recall",
                "rows": [
                {
                    "kind": str(row.get("kind", "")).strip(),
                    "entity_id": str(row.get("entity_id", "")).strip(),
                    "title": str(row.get("title", "")).strip(),
                    "path": str(row.get("path", "")).strip(),
                    "score": float(row.get("score", 0.0) or 0.0),
                    "query": " ".join(query_tokens),
                    "mode": "tantivy_sparse_recall",
                }
                for row in rows
                if str(row.get("kind", "")).strip()
                ],
            }
        except Exception:
            pass
    return {
        "mode": "repo_scan_fallback",
        "rows": _repo_scan_recovery_rows(
            connection,
            repo_root=repo_root,
            query=" ".join(query_tokens),
            limit=limit,
        ),
    }

def _recovery_search_rows(
    connection: Any,
    *,
    repo_root: Path,
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    payload = _recovery_search_payload(
        connection,
        repo_root=repo_root,
        query=query,
        limit=limit,
    )
    rows = payload.get("rows", [])
    return [dict(row) for row in rows if isinstance(row, Mapping)]

def _recovery_note_like_kind(kind: str) -> bool:
    token = str(kind or "").strip().lower()
    return token in _ENGINEERING_NOTE_KIND_SET or token in {
        "plan",
        "bug",
        "workstream",
        "component",
        "diagram",
    }

def _miss_recovery_projection_path_kind(path_ref: str) -> str:
    normalized = str(path_ref or "").strip().replace("\\", "/")
    if not normalized:
        return ""
    if normalized.startswith("docs/runbooks/"):
        return "runbook"
    return "code"

def _miss_recovery_projection_terms(*values: Any) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for value in values:
        if isinstance(value, (list, tuple, set)):
            tokens = _miss_recovery_projection_terms(*value)
        else:
            tokens = _miss_recovery_query_tokens(str(value or ""))
        for token in tokens:
            if token in seen:
                continue
            seen.add(token)
            rows.append(token)
    return rows

def _cached_miss_recovery_projection_index(
    connection: Any,
    *,
    repo_root: Path,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    cache_key = f"{root}:miss_recovery_projection_index"
    signature = _projection_cache_signature(repo_root=root, scope="reasoning")
    cached = _PROCESS_MISS_RECOVERY_INDEX_CACHE.get(cache_key)
    if cached is not None and cached[0] == signature:
        return cached[1]

    rows_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    token_index: dict[str, list[tuple[str, str, str]]] = {}

    def _register(
        row: Mapping[str, Any],
        *,
        extra_terms: Sequence[Any] = (),
        score_bias: float = 0.0,
    ) -> None:
        kind = str(row.get("kind", "")).strip()
        entity_id = str(row.get("entity_id", "")).strip()
        title = str(row.get("title", "")).strip()
        path_ref = _normalize_repo_token(str(row.get("path", "")).strip(), repo_root=root)
        if not kind or kind not in _MISS_RECOVERY_ALLOWED_KINDS:
            return
        if not entity_id:
            entity_id = path_ref or title
        key = (kind, entity_id, path_ref)
        terms = _miss_recovery_projection_terms(title, entity_id, path_ref, Path(path_ref).stem if path_ref else "", extra_terms)
        if not terms:
            return
        field_blob = " ".join(
            token
            for token in (
                title,
                entity_id,
                path_ref,
                *[str(value or "").strip() for value in extra_terms],
            )
            if token
        ).casefold()
        payload = {
            "kind": kind,
            "entity_id": entity_id,
            "title": title or Path(path_ref).name,
            "path": path_ref,
            "terms": tuple(terms),
            "field_blob": field_blob,
            "score_bias": float(score_bias or 0.0),
        }
        existing = rows_by_key.get(key)
        if existing is not None and float(existing.get("score_bias", 0.0) or 0.0) >= payload["score_bias"]:
            return
        rows_by_key[key] = payload
        for term in terms:
            bucket = token_index.setdefault(term, [])
            if key not in bucket and len(bucket) < 32:
                bucket.append(key)

    workstream_rows = _cached_projection_rows(
        repo_root=root,
        cache_name="workstreams_full_rows",
        loader=lambda: [dict(row) for row in connection.execute("SELECT * FROM workstreams").fetchall()],
    )
    for row in workstream_rows:
        metadata = _json_dict(row.get("metadata_json"))
        _register(
            _entity_from_row(kind="workstream", row=row),
            extra_terms=(
                [str(row.get("section", "")).strip(), str(row.get("priority", "")).strip()]
                + _normalized_string_list(metadata.get("code_references"))
                + _normalized_string_list(metadata.get("developer_docs"))
                + _normalized_string_list(metadata.get("runbooks"))
            ),
            score_bias=20.0,
        )

    for row in _cached_projection_rows(
        repo_root=root,
        cache_name="plans_full_rows",
        loader=lambda: [dict(item) for item in connection.execute("SELECT * FROM plans ORDER BY plan_path").fetchall()],
    ):
        _register(_entity_from_row(kind="plan", row=row), extra_terms=[str(row.get("backlog", "")).strip()], score_bias=18.0)

    for row in _cached_projection_rows(
        repo_root=root,
        cache_name="bugs_full_rows",
        loader=lambda: [dict(item) for item in connection.execute("SELECT * FROM bugs ORDER BY date DESC, title").fetchall()],
    ):
        _register(
            _entity_from_row(kind="bug", row=row),
            extra_terms=_parse_component_tokens(str(row.get("components", ""))),
            score_bias=16.0,
        )

    for row in _cached_projection_rows(
        repo_root=root,
        cache_name="components_full_rows",
        loader=lambda: [dict(item) for item in connection.execute("SELECT * FROM components").fetchall()],
    ):
        _register(
            _entity_from_row(kind="component", row=row),
            extra_terms=(
                _json_list(str(row.get("aliases_json", "")))
                + _json_list(str(row.get("workstreams_json", "")))
                + _json_list(str(row.get("diagrams_json", "")))
            ),
            score_bias=22.0,
        )

    for row in _cached_projection_rows(
        repo_root=root,
        cache_name="diagrams_full_rows",
        loader=lambda: [dict(item) for item in connection.execute("SELECT * FROM diagrams ORDER BY diagram_id").fetchall()],
    ):
        _register(
            _entity_from_row(kind="diagram", row=row),
            extra_terms=[str(row.get("slug", "")).strip(), str(row.get("summary", "")).strip()],
            score_bias=18.0,
        )

    for row in _cached_projection_rows(
        repo_root=root,
        cache_name="engineering_notes_full_rows",
        loader=lambda: [
            dict(item)
            for item in connection.execute(
                "SELECT * FROM engineering_notes ORDER BY note_kind, note_id"
            ).fetchall()
        ],
    ):
        note_kind = str(row.get("note_kind", "")).strip()
        _register(
            _entity_from_row(kind=note_kind, row=row),
            extra_terms=(
                _json_list(str(row.get("components_json", "")))
                + _json_list(str(row.get("workstreams_json", "")))
                + _json_list(str(row.get("path_refs_json", "")))
            ),
            score_bias=26.0,
        )

    for row in _cached_projection_rows(
        repo_root=root,
        cache_name="tests_full_rows",
        loader=lambda: [dict(item) for item in connection.execute("SELECT * FROM test_cases ORDER BY test_path, test_name").fetchall()],
    ):
        _register(
            _entity_from_row(kind="test", row=row),
            extra_terms=(
                _json_list(str(row.get("target_paths_json", "")))
                + _json_list(str(row.get("markers_json", "")))
                + [str(row.get("node_id", "")).strip()]
            ),
            score_bias=24.0,
        )

    traceability_rows = _cached_projection_rows(
        repo_root=root,
        cache_name="workstream_traceability_rows",
        loader=lambda: [
            dict(item)
            for item in connection.execute(
                """
                SELECT source_id, target_kind, target_id
                FROM traceability_edges
                WHERE target_kind IN ('runbook', 'doc', 'code')
                """
            ).fetchall()
        ],
    )
    for row in traceability_rows:
        target_id = _normalize_repo_token(str(row.get("target_id", "")).strip(), repo_root=root)
        if not target_id:
            continue
        target_kind = str(row.get("target_kind", "")).strip().lower()
        projected_kind = "code" if target_kind == "doc" else target_kind
        if projected_kind not in _MISS_RECOVERY_ALLOWED_KINDS:
            continue
        _register(
            {
                "kind": projected_kind,
                "entity_id": target_id,
                "title": Path(target_id).name,
                "path": target_id,
            },
            extra_terms=[str(row.get("source_id", "")).strip()],
            score_bias=14.0,
        )

    code_edge_rows = _cached_projection_rows(
        repo_root=root,
        cache_name="code_edges_full_rows",
        loader=lambda: [
            dict(item)
            for item in connection.execute(
                "SELECT * FROM code_edges ORDER BY source_path, relation, target_path"
            ).fetchall()
        ],
    )
    for row in code_edge_rows:
        relation = str(row.get("relation", "")).strip()
        if relation not in {"documents_code", "runbook_covers_code"}:
            continue
        source_path = _normalize_repo_token(str(row.get("source_path", "")).strip(), repo_root=root)
        if not source_path:
            continue
        projected_kind = _miss_recovery_projection_path_kind(source_path)
        if projected_kind not in _MISS_RECOVERY_ALLOWED_KINDS:
            continue
        _register(
            {
                "kind": projected_kind,
                "entity_id": source_path,
                "title": Path(source_path).name,
                "path": source_path,
            },
            extra_terms=[str(row.get("target_path", "")).strip(), relation],
            score_bias=12.0,
        )

    payload = {
        "rows": rows_by_key,
        "token_index": token_index,
    }
    _PROCESS_MISS_RECOVERY_INDEX_CACHE[cache_key] = (signature, payload)
    return payload

def _projection_miss_recovery_rows(
    connection: Any,
    *,
    repo_root: Path,
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    query_tokens = _miss_recovery_query_tokens(query)
    if not query_tokens:
        return []
    index = _cached_miss_recovery_projection_index(connection, repo_root=repo_root)
    rows_by_key = index.get("rows", {})
    token_index = index.get("token_index", {})
    if not isinstance(rows_by_key, Mapping) or not isinstance(token_index, Mapping):
        return []
    candidate_keys: list[tuple[str, str, str]] = []
    seen_keys: set[tuple[str, str, str]] = set()
    for token in query_tokens:
        for key in token_index.get(token, []) if isinstance(token_index.get(token), list) else []:
            if not isinstance(key, tuple) or len(key) != 3 or key in seen_keys:
                continue
            seen_keys.add(key)
            candidate_keys.append(key)
            if len(candidate_keys) >= 96:
                break
        if len(candidate_keys) >= 96:
            break
    query_phrase = " ".join(query_tokens)
    results: list[dict[str, Any]] = []
    for key in candidate_keys:
        candidate = rows_by_key.get(key)
        if not isinstance(candidate, Mapping):
            continue
        terms = {
            str(token).strip()
            for token in candidate.get("terms", ())
            if str(token).strip()
        }
        overlap = [token for token in query_tokens if token in terms]
        if not overlap:
            continue
        field_blob = str(candidate.get("field_blob", "")).strip()
        overlap_ratio = len(overlap) / max(1, len(query_tokens))
        score = (
            float(candidate.get("score_bias", 0.0) or 0.0)
            + float(len(overlap) * 40)
            + float(overlap_ratio * 20.0)
            + (18.0 if query_phrase and query_phrase.casefold() in field_blob else 0.0)
            + (12.0 if len(overlap) == len(query_tokens) else 0.0)
        )
        results.append(
            {
                "kind": str(candidate.get("kind", "")).strip(),
                "entity_id": str(candidate.get("entity_id", "")).strip(),
                "title": str(candidate.get("title", "")).strip(),
                "path": str(candidate.get("path", "")).strip(),
                "score": round(score, 3),
                "query": query_phrase,
                "mode": "projection_exact_rescue",
            }
        )
    results.sort(
        key=lambda row: (
            -float(row.get("score", 0.0) or 0.0),
            int(_MISS_RECOVERY_KIND_PRIORITY.get(str(row.get("kind", "")).strip(), 9)),
            str(row.get("path", "")),
            str(row.get("entity_id", "")),
        )
    )
    return results[: max(1, int(limit))]

def _compact_miss_recovery_result(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in {
            "kind": str(row.get("kind", "")).strip(),
            "entity_id": str(row.get("entity_id", "")).strip(),
            "title": str(row.get("title", "")).strip(),
            "path": str(row.get("path", "")).strip(),
            "query": str(row.get("query", "")).strip(),
        }.items()
        if value not in ("", [], {}, None)
    }

def _compact_miss_recovery_for_packet(summary: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(summary, Mapping):
        return {}
    recovered_entities = summary.get("recovered_entities", [])
    if not isinstance(recovered_entities, list):
        recovered_entities = []
    recovered_tests = summary.get("recovered_tests", [])
    if not isinstance(recovered_tests, list):
        recovered_tests = []
    return {
        key: value
        for key, value in {
            "active": bool(summary.get("active")),
            "applied": bool(summary.get("applied")),
            "mode": str(summary.get("mode", "")).strip(),
            "activation_reason": str(summary.get("activation_reason", "")).strip(),
            "queries": [str(token).strip() for token in summary.get("queries", [])[:3] if str(token).strip()]
            if isinstance(summary.get("queries"), list)
            else [],
            "recovered_docs": [
                str(token).strip()
                for token in summary.get("recovered_docs", [])[:_MISS_RECOVERY_DOC_LIMIT]
                if str(token).strip()
            ]
            if isinstance(summary.get("recovered_docs"), list)
            else [],
            "recovered_tests": [
                _compact_test_row_for_packet(row)
                for row in recovered_tests[:_MISS_RECOVERY_TEST_LIMIT]
                if isinstance(row, Mapping)
            ],
            "recovered_entities": [
                _compact_miss_recovery_result(row)
                for row in recovered_entities[:_MISS_RECOVERY_RESULT_LIMIT]
                if isinstance(row, Mapping)
            ],
        }.items()
        if value not in ("", [], {}, None)
    }

def _collect_retrieval_miss_recovery(
    connection: Any,
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    shared_only_input: bool,
    selection_state: str,
    component_ids: Sequence[str],
    docs: Sequence[str],
    tests: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    normalized_paths = _dedupe_strings([str(path).strip() for path in changed_paths if str(path).strip()])
    if shared_only_input:
        return {"active": False, "activation_reason": "shared_only_input"}
    if str(selection_state or "").strip() not in {"ambiguous", "none"}:
        return {"active": False, "activation_reason": "selection_confident"}
    queries = _build_miss_recovery_queries(
        changed_paths=normalized_paths,
        component_ids=component_ids,
    )
    if not queries:
        return {"active": False, "activation_reason": "no_recovery_queries"}
    known_docs = {str(path).strip() for path in docs if str(path).strip()}
    known_tests = {
        str(row.get("path", row.get("test_path", ""))).strip()
        for row in tests
        if isinstance(row, Mapping) and str(row.get("path", row.get("test_path", ""))).strip()
    }
    existing_paths = set(normalized_paths).union(known_docs).union(known_tests)
    ranked_rows: list[tuple[tuple[int, int, float, str], dict[str, Any]]] = []
    seen_entities: set[tuple[str, str, str]] = set()
    recovery_modes: set[str] = set()
    for query_index, query in enumerate(queries):
        payload = _recovery_search_payload(
            connection,
            repo_root=repo_root,
            query=query,
            limit=_MISS_RECOVERY_RESULT_LIMIT,
        )
        mode_token = str(payload.get("mode", "")).strip()
        if mode_token and mode_token != "none":
            recovery_modes.add(mode_token)
        for row in payload.get("rows", []) if isinstance(payload.get("rows"), list) else []:
            kind = str(row.get("kind", "")).strip()
            path_ref = str(row.get("path", "")).strip()
            entity_id = str(row.get("entity_id", "")).strip()
            if not kind or (path_ref and path_ref in existing_paths):
                continue
            entity_key = (kind, entity_id, path_ref)
            if entity_key in seen_entities:
                continue
            seen_entities.add(entity_key)
            rank_key = (
                int(query_index),
                int(_MISS_RECOVERY_KIND_PRIORITY.get(kind, 9)),
                -int(round(float(row.get("score", 0.0) or 0.0) * 1000)),
                path_ref or entity_id,
            )
            ranked_rows.append((rank_key, row))
    ranked_rows.sort(key=lambda item: item[0])
    recovered_entities = [dict(row) for _rank, row in ranked_rows[:_MISS_RECOVERY_RESULT_LIMIT]]
    recovery_mode = (
        next(iter(recovery_modes))
        if len(recovery_modes) == 1
        else "mixed_sparse_plus_repo_scan"
        if recovery_modes
        else "repo_scan_fallback"
    )
    recovered_docs: list[str] = []
    recovered_tests: list[dict[str, Any]] = []
    for row in recovered_entities:
        kind = str(row.get("kind", "")).strip()
        path_ref = str(row.get("path", "")).strip()
        if not path_ref:
            continue
        if kind == "test":
            if path_ref in known_tests:
                continue
            recovered_tests.append(
                {
                    "path": path_ref,
                    "test_path": path_ref,
                    "nodeid": "",
                    "reason": (
                        f"runtime miss recovery matched `{str(row.get('query', '')).strip()}` through Odylith local sparse recall."
                        if str(row.get("mode", "")).strip() == "tantivy_sparse_recall"
                        else f"runtime miss recovery matched `{str(row.get('query', '')).strip()}` through raw repo scan fallback."
                    ),
                }
            )
            known_tests.add(path_ref)
            continue
        if _recovery_note_like_kind(kind) or kind == "code":
            if path_ref in known_docs:
                continue
            recovered_docs.append(path_ref)
            known_docs.add(path_ref)
    recovered_docs = recovered_docs[:_MISS_RECOVERY_DOC_LIMIT]
    recovered_tests = recovered_tests[:_MISS_RECOVERY_TEST_LIMIT]
    if not recovered_docs and not recovered_tests and not recovered_entities:
        return {
            "active": False,
            "activation_reason": "no_sparse_hits",
            "mode": recovery_mode,
            "queries": queries,
        }
    return {
        "active": True,
        "applied": bool(recovered_docs or recovered_tests),
        "mode": recovery_mode,
        "activation_reason": "low_confidence_non_shared_slice",
        "queries": queries,
        "recovered_docs": recovered_docs,
        "recovered_tests": recovered_tests,
        "recovered_entities": recovered_entities,
    }
