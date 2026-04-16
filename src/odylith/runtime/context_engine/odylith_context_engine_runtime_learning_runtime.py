"""Runtime learning and reporting helpers for the Odylith context engine."""

from __future__ import annotations

from typing import Any

from odylith.runtime.context_engine import odylith_context_engine_packet_summary_runtime


def bind(host: Any) -> None:
    getter = host.__getitem__ if isinstance(host, dict) else lambda name: getattr(host, name)
    for name in ('Any', 'Mapping', 'OPTIMIZATION_EVALUATION_CORPUS', 'Path', 'Sequence', '_ODYLITH_SUPPRESSED_PATHS', '_PROCESS_JUDGMENT_MEMORY_SNAPSHOT_CACHE', '_PROCESS_OPTIMIZATION_SNAPSHOT_CACHE', '_PROCESS_OPTIMIZATION_SNAPSHOT_CACHE_TTL_SECONDS', '_PROCESS_ORCHESTRATION_ADOPTION_SNAPSHOT_CACHE', '_bool_score', '_normalize_changed_path_list', '_normalize_repo_token', '_ordered_events', '_parse_iso_utc', '_persist_runtime_proof_section', '_rate', '_rate_for', '_record_sort_timestamp', '_runtime_optimization_cache_signature', '_safe_float', '_safe_int', '_sticky_snapshot_from_section', '_utc_now', 'active_sessions', 'actual_key', 'adoption', 'advised_budget_mode', 'advised_packet_strategy', 'advised_retrieval_focus', 'advised_speed_mode', 'advisory_key', 'age_hours', 'alias', 'alias_map', 'areas', 'attempted_rows', 'authoritative_truth', 'avg_bytes', 'avg_context_density_per_1k', 'avg_context_density_score', 'avg_density', 'avg_evidence_diversity_score', 'avg_reasoning_readiness_score', 'avg_tokens', 'avg_utility_score', 'backend_transition', 'backlog_projection', 'benchmark', 'benchmark_report', 'best', 'bootstrap_limit', 'bootstraps_root', 'bucket', 'buckets', 'budget_mode_distribution', 'bug_projection', 'cache_key', 'cache_signature', 'cached', 'cached_payload', 'cached_signature', 'cached_until', 'case', 'case_id', 'cases', 'changed_paths', 'cleaned', 'cold', 'compact_workstream', 'compiler_ready', 'compiler_state', 'component_id', 'component_index', 'component_registry', 'components', 'connection', 'context_density_distribution', 'context_packet', 'corpus', 'count', 'counts', 'coverage', 'decision_quality_reliable', 'decision_summary', 'deep_reasoning_ready_rate', 'default', 'delegated_lane_rate', 'details', 'diagram_projection', 'disabled', 'display_command', 'domain_ids', 'domains_any', 'drift_case_ids', 'dt', 'enabled', 'entity', 'entity_counts', 'entity_id', 'entry', 'evaluation', 'evaluation_snapshot', 'event_type', 'evidence_diversity_distribution', 'evidence_documents', 'execution_agent_role_distribution', 'execution_delegate_preference_distribution', 'execution_profile_distribution', 'execution_reasoning_distribution', 'execution_selection_mode_distribution', 'execution_source_distribution', 'expect_spec', 'expectation_ok', 'expected', 'expected_bool', 'expected_confidence', 'expected_execution_modes', 'expected_min', 'expected_miss_mode', 'expected_risk_tiers', 'fallback_reason_distribution', 'field_name', 'filtered', 'filtered_report', 'focus_limit', 'freshest', 'full_scan_reason', 'governance_runtime_first', 'grouped', 'guidance_catalog', 'high_execution_confidence_rate', 'high_intent_confidence_rate', 'high_routing_confidence_rate', 'high_utility_rate', 'hold_local_rate', 'include_selection', 'index', 'indexed_entities', 'intent_critical_path_distribution', 'intent_explicit_rate', 'intent_families', 'intent_family_distribution', 'intent_mode_distribution', 'item', 'items', 'judgment_memory', 'judgment_memory_path', 'key', 'kind', 'label', 'labels', 'latency_posture', 'latest_budget_mode', 'latest_mtime', 'latest_packet', 'latest_packet_strategy', 'latest_recorded_at', 'latest_retrieval_focus', 'latest_speed_mode', 'learning_advisories', 'learning_control', 'learning_decision_quality', 'learning_decision_quality_confidence', 'learning_evidence_strength', 'learning_freshness', 'learning_orchestration', 'learning_packet', 'learning_router', 'learning_summary', 'learning_trend', 'ledger', 'ledger_paths', 'ledger_root', 'left', 'left_prefix', 'left_token', 'limit', 'live_snapshot', 'mapped_events', 'match', 'match_spec', 'matched', 'matched_case_ids', 'matched_paths', 'math', 'max_chars', 'maximum', 'metadata', 'minimum', 'miss_recovery_applied_rate', 'miss_recovery_mode', 'miss_recovery_rate', 'narrowing_rate', 'native_spawn_ready_rate', 'next_move', 'normalized', 'normalized_items', 'normalized_paths', 'normalized_provenance', 'normalized_state', 'now', 'numeric', 'numeric_float', 'observed', 'observed_bool', 'observed_count', 'observed_miss_mode', 'odylith_ablation', 'odylith_benchmark_contract', 'odylith_context_cache', 'odylith_context_engine_memory_snapshot_runtime', 'odylith_control_state', 'odylith_evaluation_ledger', 'odylith_switch', 'operation', 'operations', 'optimization', 'optimization_snapshot', 'orchestration_adoption', 'orchestration_events', 'orchestration_limit', 'orchestration_rows', 'overall_freshness', 'overall_level', 'overall_rate', 'overall_terms', 'packet', 'packet_events', 'packet_kind', 'packet_limit', 'packet_reliability_distribution', 'packet_rows', 'packet_state_distribution', 'packet_states', 'packet_strategy_distribution', 'packets', 'parallelism_distribution', 'parsed', 'part', 'partial', 'parts', 'path', 'path_token', 'path_tokens', 'paths_all', 'paths_any', 'payload', 'plan_projection', 'planned', 'previous_snapshot', 'product_layer', 'projection_updated_utc', 'proof_path', 'proof_signature', 'proof_surfaces_path', 'provenance', 'query', 'rate', 'raw', 'raw_count', 're', 'reasoning_distribution', 'reasoning_mode_distribution', 'reasoning_readiness_distribution', 'recent_bootstrap_packets', 'recommendation_rows', 'recorded_at', 'recorded_utc', 'repo_dirty_paths', 'repo_root', 'repo_scan_degraded_rate', 'repo_scan_degraded_reason_distribution', 'repo_scan_degraded_rows', 'report', 'resolve_product_path', 'results', 'retrieval_state', 'richest_distribution', 'right', 'right_prefix', 'right_token', 'root', 'route', 'route_ready_rate', 'router_events', 'router_limit', 'router_rows', 'routing_handoff', 'row', 'rows', 'runtime_backed_execution_rate', 'runtime_root', 'runtime_state', 'sample_size', 'samples', 'satisfied_case_count', 'scan_limit', 'seen', 'selection', 'selection_bias_distribution', 'selection_payload', 'severity', 'signature', 'snapshot', 'source', 'source_kind', 'source_path', 'spec_snapshots', 'speed_mode_distribution', 'starter_path', 'starter_slice', 'starter_status', 'stat', 'state', 'strong', 'structured_execution_profile', 'subcomponents', 'summary', 'surfaces', 'switch_snapshot', 'table_name', 'text', 'time', 'timing_events', 'timing_limit', 'timing_row', 'timing_rows', 'timing_summary', 'token', 'tokens', 'top_intent_family', 'traceability', 'transition_status', 'trust', 'unmapped_meaningful_events', 'updated_utc', 'valid_bootstraps', 'value', 'values', 'welcome_state', 'within_budget_rate', 'workstream', 'workstream_id', 'workstream_token'):
        try:
            globals()[name] = getter(name)
        except (AttributeError, KeyError):
            continue
    odylith_context_engine_packet_summary_runtime.bind(host)


def load_runtime_timing_summary(
    *,
    repo_root: Path,
    limit: int = 24,
) -> dict[str, Any]:
    return odylith_control_state.summarize_timings(
        repo_root=Path(repo_root).resolve(),
        limit=max(1, int(limit)),
    )

def load_odylith_drawer_history(
    *,
    repo_root: Path,
    packet_limit: int = 16,
    router_limit: int = 16,
    orchestration_limit: int = 16,
    timing_limit: int = 24,
) -> dict[str, Any]:
    """Build a compact recent-history payload for the shell-owned Odylith drawer."""

    root = Path(repo_root).resolve()

    def _ordered_events(event_type: str, *, limit: int) -> list[dict[str, Any]]:
        rows = odylith_evaluation_ledger.load_events(
            repo_root=root,
            limit=max(1, int(limit)),
            event_types=[event_type],
        )
        rows.reverse()
        return [dict(row) for row in rows if isinstance(row, Mapping)]

    def _bool_score(value: Any) -> int:
        return 100 if bool(value) else 0

    def _safe_float(value: Any, default: float = 0.0, *, minimum: float | None = None, maximum: float | None = None) -> float:
        try:
            numeric = float(value or 0.0)
        except (TypeError, ValueError):
            numeric = float(default)
        if math.isnan(numeric):
            numeric = float(default)
        elif math.isinf(numeric):
            if numeric > 0 and maximum is not None:
                numeric = float(maximum)
            elif numeric < 0 and minimum is not None:
                numeric = float(minimum)
            else:
                numeric = float(default)
        if minimum is not None:
            numeric = max(float(minimum), numeric)
        if maximum is not None:
            numeric = min(float(maximum), numeric)
        return numeric

    def _safe_int(
        value: Any,
        default: int = 0,
        *,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> int:
        try:
            numeric_float = float(value or 0)
            if math.isnan(numeric_float):
                raise ValueError("non-finite numeric value")
            if math.isinf(numeric_float):
                if numeric_float > 0 and maximum is not None:
                    return int(maximum)
                if numeric_float < 0 and minimum is not None:
                    return int(minimum)
                raise ValueError("non-finite numeric value")
            numeric = int(round(numeric_float))
        except (TypeError, ValueError, OverflowError):
            numeric = int(default)
        if minimum is not None:
            numeric = max(int(minimum), numeric)
        if maximum is not None:
            numeric = min(int(maximum), numeric)
        return numeric

    packet_rows = _ordered_events("packet", limit=packet_limit)
    router_rows = _ordered_events("router_outcome", limit=router_limit)
    orchestration_rows = _ordered_events("orchestration_feedback", limit=orchestration_limit)
    timing_rows = odylith_control_state.load_timing_rows(repo_root=root, limit=max(1, int(timing_limit)))
    timing_rows.reverse()

    packet_events: list[dict[str, Any]] = []
    for index, row in enumerate(packet_rows, start=1):
        payload = dict(row.get("payload", {})) if isinstance(row.get("payload"), Mapping) else {}
        benchmark = dict(payload.get("benchmark", {})) if isinstance(payload.get("benchmark"), Mapping) else {}
        packet_events.append(
            {
                "index": index,
                "label": f"P{index}",
                "recorded_at": str(row.get("recorded_at", "")).strip(),
                "workstream": str(payload.get("workstream", "")).strip(),
                "session_id": str(payload.get("session_id", "")).strip(),
                "packet_state": str(payload.get("packet_state", "")).strip(),
                "context_density_score": _safe_int(payload.get("context_density_score", 0), minimum=0, maximum=4),
                "reasoning_readiness_score": _safe_int(payload.get("reasoning_readiness_score", 0), minimum=0, maximum=4),
                "evidence_diversity_score": _safe_int(payload.get("evidence_diversity_score", 0), minimum=0, maximum=4),
                "utility_score": _safe_int(payload.get("utility_score", 0), minimum=0, maximum=4),
                "density_per_1k_tokens": round(_safe_float(payload.get("density_per_1k_tokens", 0.0), minimum=0.0, maximum=1000.0), 3),
                "estimated_tokens": _safe_int(payload.get("estimated_tokens", 0), minimum=0, maximum=250000),
                "within_budget_score": _bool_score(payload.get("within_budget")),
                "route_ready_score": _bool_score(payload.get("route_ready")),
                "spawn_ready_score": _bool_score(payload.get("native_spawn_ready")),
                "deep_reasoning_ready_score": _bool_score(payload.get("deep_reasoning_ready")),
                "benchmark_match_score": _bool_score(_safe_int(benchmark.get("matched_case_count", 0), minimum=0) > 0),
                "benchmark_satisfaction_score": _bool_score(_safe_int(benchmark.get("satisfied_case_count", 0), minimum=0) > 0),
                "advisory_alignment_score": _safe_int(
                    round(
                        (
                            (
                                sum(
                                    1
                                    for actual_key, advisory_key in (
                                        ("packet_strategy", "advisory_packet_strategy"),
                                        ("budget_mode", "advisory_budget_mode"),
                                        ("retrieval_focus", "advisory_retrieval_focus"),
                                        ("speed_mode", "advisory_speed_mode"),
                                    )
                                    if str(payload.get(actual_key, "")).strip()
                                    and str(payload.get(advisory_key, "")).strip()
                                    and str(payload.get(actual_key, "")).strip().lower()
                                    == str(payload.get(advisory_key, "")).strip().lower()
                                )
                                * 100.0
                            )
                            / max(
                                1,
                                sum(
                                    1
                                    for actual_key, advisory_key in (
                                        ("packet_strategy", "advisory_packet_strategy"),
                                        ("budget_mode", "advisory_budget_mode"),
                                        ("retrieval_focus", "advisory_retrieval_focus"),
                                        ("speed_mode", "advisory_speed_mode"),
                                    )
                                    if str(payload.get(actual_key, "")).strip()
                                    and str(payload.get(advisory_key, "")).strip()
                                ),
                            )
                        )
                        if any(
                            str(payload.get(advisory_key, "")).strip()
                            for advisory_key in (
                                "advisory_packet_strategy",
                                "advisory_budget_mode",
                                "advisory_retrieval_focus",
                                "advisory_speed_mode",
                            )
                        )
                        else (100.0 * float(payload.get("advisory_alignment_rate", 0.0) or 0.0))
                    ),
                    minimum=0,
                    maximum=100,
                ),
                "execution_profile": str(payload.get("odylith_execution_profile", "")).strip(),
                "execution_delegate_preference": str(payload.get("odylith_execution_delegate_preference", "")).strip(),
            }
        )

    router_events: list[dict[str, Any]] = []
    for index, row in enumerate(router_rows, start=1):
        payload = dict(row.get("payload", {})) if isinstance(row.get("payload"), Mapping) else {}
        router_events.append(
            {
                "index": index,
                "label": f"R{index}",
                "recorded_at": str(row.get("recorded_at", "")).strip(),
                "accepted_score": _bool_score(payload.get("accepted")),
                "failure_score": _bool_score(
                    bool(payload.get("blocked"))
                    or bool(payload.get("ambiguous"))
                    or bool(payload.get("artifact_missing"))
                    or bool(payload.get("quality_too_weak"))
                    or bool(payload.get("broader_coordination"))
                ),
                "escalated_score": _bool_score(payload.get("escalated")),
                "grounding_score": _safe_int(payload.get("grounding_score", 0), minimum=0, maximum=100),
                "context_density_score": _safe_int(payload.get("context_density_score", 0), minimum=0, maximum=100),
                "expected_delegation_value_score": _safe_int(payload.get("expected_delegation_value_score", 0), minimum=0, maximum=100),
                "delegate_preference": str(payload.get("odylith_execution_delegate_preference", "")).strip(),
            }
        )

    orchestration_events: list[dict[str, Any]] = []
    for index, row in enumerate(orchestration_rows, start=1):
        payload = dict(row.get("payload", {})) if isinstance(row.get("payload"), Mapping) else {}
        orchestration_events.append(
            {
                "index": index,
                "label": f"O{index}",
                "recorded_at": str(row.get("recorded_at", "")).strip(),
                "accepted_score": _bool_score(payload.get("accepted")),
                "token_efficient_score": _bool_score(payload.get("token_efficient")),
                "parallel_failure_score": _bool_score(
                    bool(payload.get("false_parallelization")) or _safe_int(payload.get("merge_conflicts", 0), minimum=0) > 0
                ),
                "rescope_required_score": _bool_score(payload.get("rescope_required")),
                "subtask_count": _safe_int(payload.get("subtask_count", 0), minimum=0, maximum=100),
                "mode": str(payload.get("mode", "")).strip(),
            }
        )

    timing_events: list[dict[str, Any]] = []
    for index, row in enumerate(timing_rows, start=1):
        if not isinstance(row, Mapping):
            continue
        operation = str(row.get("operation", "")).strip()
        if operation not in {"impact", "session_brief", "bootstrap_session"}:
            continue
        timing_events.append(
            {
                "index": index,
                "label": f"T{index}",
                "recorded_at": str(row.get("ts_iso", "")).strip(),
                "operation": operation,
                "duration_ms": round(_safe_float(row.get("duration_ms", 0.0), minimum=0.0, maximum=300000.0), 3),
            }
        )

    return {
        "contract": "odylith_drawer_history.v1",
        "version": "v1",
        "generated_utc": _utc_now(),
        "packet_events": packet_events,
        "router_events": router_events,
        "orchestration_events": orchestration_events,
        "timing_events": timing_events,
    }

def _optimization_level_from_rate(rate: float) -> str:
    value = max(0.0, min(1.0, float(rate)))
    if value >= 0.8:
        return "high"
    if value >= 0.55:
        return "medium"
    if value > 0.0:
        return "low"
    return "minimal"

def _sorted_count_map(values: Sequence[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for raw in values:
        token = str(raw or "").strip()
        if not token:
            continue
        counts[token] = int(counts.get(token, 0) or 0) + 1
    return {key: counts[key] for key in sorted(counts, key=lambda item: (-counts[item], item))}

def optimization_evaluation_corpus_path(*, repo_root: Path) -> Path:
    return resolve_product_path(repo_root=Path(repo_root).resolve(), relative_path=OPTIMIZATION_EVALUATION_CORPUS)

def _normalized_string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    tokens: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = str(raw or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens

def _truncate_text(text: str, *, max_chars: int = 140) -> str:
    normalized = " ".join(str(text or "").strip().split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max(0, max_chars - 1)].rstrip() + "…"

def _safe_file_size(path: Path) -> int:
    try:
        return int(path.stat().st_size)
    except OSError:
        return 0

def _table_row_count(connection: Any, table_name: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) AS row_count FROM {table_name}").fetchone()
    if row is None:
        return 0
    return int(row["row_count"] or 0)

def _odylith_switch_snapshot(*, repo_root: Path) -> dict[str, Any]:
    return dict(odylith_ablation.build_odylith_switch_snapshot(repo_root=Path(repo_root).resolve()))

def _odylith_ablation_active(*, repo_root: Path) -> bool:
    return not bool(_odylith_switch_snapshot(repo_root=repo_root).get("enabled", True))

def _memory_area_entry(
    *,
    key: str,
    label: str,
    state: str,
    summary: str,
) -> dict[str, Any]:
    return {
        "key": str(key).strip(),
        "label": str(label).strip(),
        "state": str(state).strip() or "unknown",
        "summary": str(summary).strip(),
    }

def _memory_area_label_list(labels: Sequence[str]) -> str:
    cleaned = [str(label).strip().lower() for label in labels if str(label).strip()]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return f"{', '.join(cleaned[:-1])}, and {cleaned[-1]}"

def _memory_areas_headline(areas: Sequence[Mapping[str, Any]]) -> str:
    grouped: dict[str, list[str]] = {}
    for row in areas:
        if not isinstance(row, Mapping):
            continue
        state = str(row.get("state", "")).strip().lower() or "unknown"
        grouped.setdefault(state, []).append(str(row.get("label", "")).strip())

    strong = _memory_area_label_list(grouped.get("strong", ()))
    partial = _memory_area_label_list(grouped.get("partial", ()))
    cold = _memory_area_label_list(grouped.get("cold", ()))
    planned = _memory_area_label_list(grouped.get("planned", ()))
    disabled = _memory_area_label_list(grouped.get("disabled", ()))
    parts: list[str] = []
    if strong:
        parts.append(f"{strong} {'are' if ',' in strong or ' and ' in strong else 'is'} strong")
    if partial:
        parts.append(f"{partial} {'are' if ',' in partial or ' and ' in partial else 'is'} partial")
    if cold:
        parts.append(f"{cold} {'are' if ',' in cold or ' and ' in cold else 'is'} cold")
    if planned:
        parts.append(f"{planned} {'are' if ',' in planned or ' and ' in planned else 'is'} still planned")
    if disabled:
        parts.append(f"{disabled} {'are' if ',' in disabled or ' and ' in disabled else 'is'} suppressed")
    return " ".join(parts) if parts else "No memory areas are active yet."

def _judgment_memory_headline(areas: Sequence[Mapping[str, Any]]) -> str:
    strong = ", ".join(str(row.get("label", "")).strip().lower() for row in areas if str(row.get("state", "")).strip() == "strong")
    partial = ", ".join(str(row.get("label", "")).strip().lower() for row in areas if str(row.get("state", "")).strip() == "partial")
    cold = ", ".join(str(row.get("label", "")).strip().lower() for row in areas if str(row.get("state", "")).strip() == "cold")
    parts: list[str] = []
    if strong:
        parts.append(f"{strong} {'are' if ',' in strong or ' and ' in strong else 'is'} durable and ready")
    if partial:
        parts.append(f"{partial} {'are' if ',' in partial or ' and ' in partial else 'is'} partially grounded")
    if cold:
        parts.append(f"{cold} {'are' if ',' in cold or ' and ' in cold else 'is'} still cold")
    return " ".join(parts) if parts else "No durable judgment memory is active yet."

def _memory_snapshot_status_from_counts(counts: Mapping[str, Any]) -> str:
    normalized = {
        str(key).strip().lower(): int(value or 0)
        for key, value in counts.items()
        if str(key).strip()
    }
    if normalized.get("disabled", 0) > 0:
        return "disabled"
    if normalized.get("strong", 0) > 0 or normalized.get("partial", 0) > 0:
        return "active"
    if normalized.get("planned", 0) > 0:
        return "planned"
    if normalized.get("cold", 0) > 0:
        return "cold"
    return "unknown"

def _freshness_bucket_for_age_hours(age_hours: float | None) -> str:
    if age_hours is None:
        return "unknown"
    if age_hours <= 24.0:
        return "fresh"
    if age_hours <= 72.0:
        return "recent"
    if age_hours <= 24.0 * 14.0:
        return "stale"
    return "cold"

def _freshness_payload(*, updated_utc: str) -> dict[str, Any]:
    parsed = _parse_iso_utc(updated_utc)
    if parsed is None:
        return {
            "bucket": "unknown",
            "updated_utc": str(updated_utc or "").strip(),
            "newest_age_hours": None,
        }
    age_hours = max(0.0, (dt.datetime.now(dt.timezone.utc) - parsed).total_seconds() / 3600.0)
    return {
        "bucket": _freshness_bucket_for_age_hours(age_hours),
        "updated_utc": parsed.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "newest_age_hours": round(age_hours, 3),
    }

def _latest_updated_utc(*values: str) -> str:
    best: tuple[dt.datetime, str] | None = None
    for value in values:
        parsed = _parse_iso_utc(value)
        if parsed is None:
            continue
        normalized = parsed.replace(microsecond=0).isoformat().replace("+00:00", "Z")
        if best is None or parsed > best[0]:
            best = (parsed, normalized)
    return best[1] if best is not None else ""

def _relative_repo_path(*, repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(Path(repo_root).resolve()).as_posix()
    except ValueError:
        return str(path)

def _humanize_slug(value: str) -> str:
    token = str(value or "").strip().replace("-", " ").replace("_", " ")
    return " ".join(part.capitalize() for part in token.split())

def _workstream_token(value: str) -> str:
    match = re.search(r"B-\d{3,}", str(value or "").upper())
    return match.group(0) if match is not None else ""

def _compact_selection_state_parts(value: str) -> tuple[str, str]:
    token = str(value or "").strip()
    if not token:
        return "", ""
    if token.startswith("x:"):
        return "explicit", _workstream_token(token[2:])
    if token.startswith("i:"):
        return "inferred_confident", _workstream_token(token[2:])
    workstream = _workstream_token(token)
    if workstream and token == workstream:
        return "explicit", workstream
    return token, ""

def _encode_compact_selection_state(*, state: str, workstream: str) -> str:
    normalized_state = str(state or "").strip()
    workstream_token = _workstream_token(workstream)
    if normalized_state == "explicit" and workstream_token:
        return f"x:{workstream_token}"
    if normalized_state == "inferred_confident" and workstream_token:
        return f"i:{workstream_token}"
    return normalized_state

def _decode_compact_selected_counts(value: Any) -> dict[str, int]:
    if isinstance(value, Mapping):
        return {
            str(key).strip(): int(raw or 0)
            for key, raw in value.items()
            if str(key).strip() and int(raw or 0) > 0
        }
    token = str(value or "").strip()
    if not token:
        return {}
    alias_map = {
        "c": "commands",
        "d": "docs",
        "t": "tests",
        "g": "guidance",
    }
    counts: dict[str, int] = {}
    for alias, raw_count in re.findall(r"([cdtg])(\d+)", token):
        key = alias_map.get(alias, "")
        count = int(raw_count or 0)
        if key and count > 0:
            counts[key] = count
    return counts

def _encode_compact_selected_counts(counts: Mapping[str, Any]) -> str:
    normalized = _decode_compact_selected_counts(counts)
    if not normalized:
        return ""
    parts: list[str] = []
    for key, alias in (("commands", "c"), ("docs", "d"), ("tests", "t"), ("guidance", "g")):
        count = int(normalized.get(key, 0) or 0)
        if count > 0:
            parts.append(f"{alias}{count}")
    return "".join(parts)

def _payload_workstream_hint(
    payload: Mapping[str, Any] | None,
    *,
    include_selection: bool = True,
) -> str:
    if not isinstance(payload, Mapping):
        return ""
    for key in ("inferred_workstream", "workstream", "ws"):
        token = _workstream_token(str(payload.get(key, "")).strip())
        if token:
            return token
    context_packet = (
        dict(payload.get("context_packet", {}))
        if isinstance(payload.get("context_packet"), Mapping)
        else {}
    )
    _, compact_workstream = _compact_selection_state_parts(str(context_packet.get("selection_state", "")).strip())
    if compact_workstream:
        return compact_workstream
    if not include_selection:
        return ""
    selection = (
        dict(payload.get("workstream_selection", {}))
        if isinstance(payload.get("workstream_selection"), Mapping)
        else {}
    )
    for field_name in ("selected_workstream", "top_candidate"):
        row = dict(selection.get(field_name, {})) if isinstance(selection.get(field_name), Mapping) else {}
        token = _workstream_token(str(row.get("entity_id", "")).strip())
        if token:
            return token
    selection_payload = (
        dict(context_packet.get("selection", {}))
        if isinstance(context_packet.get("selection"), Mapping)
        else {}
    )
    for token in _normalized_string_list(selection_payload.get("workstream_ids")):
        workstream_token = _workstream_token(token)
        if workstream_token:
            return workstream_token
    return ""

def _payload_packet_kind(
    payload: Mapping[str, Any] | None,
    *,
    context_packet: Mapping[str, Any] | None = None,
    routing_handoff: Mapping[str, Any] | None = None,
) -> str:
    if isinstance(payload, Mapping):
        packet_kind = str(payload.get("packet_kind", "")).strip()
        if packet_kind:
            return packet_kind
    if isinstance(context_packet, Mapping):
        packet_kind = str(context_packet.get("packet_kind", "")).strip()
        if packet_kind:
            return packet_kind
        route = dict(context_packet.get("route", {})) if isinstance(context_packet.get("route"), Mapping) else {}
        if isinstance(route.get("governance"), Mapping):
            return "governance_slice"
    if isinstance(routing_handoff, Mapping):
        packet_kind = str(routing_handoff.get("packet_kind", "")).strip()
        if packet_kind:
            return packet_kind
    return "impact" if isinstance(context_packet, Mapping) and context_packet else ""

def _judgment_memory_item(
    *,
    kind: str,
    summary: str,
    recorded_utc: str = "",
    source_path: str = "",
    source_kind: str = "",
    severity: str = "",
    next_move: str = "",
    surfaces: Sequence[str] = (),
) -> dict[str, Any]:
    payload = {
        "kind": str(kind or "").strip(),
        "summary": str(summary or "").strip(),
        "recorded_utc": str(recorded_utc or "").strip(),
        "source_path": str(source_path or "").strip(),
        "source_kind": str(source_kind or "").strip(),
        "severity": str(severity or "").strip(),
        "next_move": str(next_move or "").strip(),
        "surfaces": [str(token).strip() for token in surfaces if str(token).strip()],
    }
    payload["freshness"] = _freshness_payload(updated_utc=str(payload.get("recorded_utc", "")).strip())
    return payload

def _judgment_memory_area(
    *,
    key: str,
    label: str,
    state: str,
    summary: str,
    items: Sequence[Mapping[str, Any]],
    provenance: Sequence[Mapping[str, Any]],
    updated_utc: str = "",
) -> dict[str, Any]:
    normalized_items = [dict(item) for item in items if isinstance(item, Mapping)]
    normalized_provenance = [dict(item) for item in provenance if isinstance(item, Mapping)]
    freshest = _latest_updated_utc(
        str(updated_utc or "").strip(),
        *[str(item.get("recorded_utc", "")).strip() for item in normalized_items],
        *[str(item.get("updated_utc", "")).strip() for item in normalized_provenance],
    )
    return {
        "key": str(key or "").strip(),
        "label": str(label or "").strip(),
        "state": str(state or "").strip() or "cold",
        "summary": str(summary or "").strip(),
        "updated_utc": freshest,
        "freshness": _freshness_payload(updated_utc=freshest),
        "item_count": len(normalized_items),
        "items": normalized_items,
        "provenance": normalized_provenance,
    }

def _provenance_item(
    *,
    label: str,
    source_kind: str,
    path: str = "",
    updated_utc: str = "",
    trust: str = "",
) -> dict[str, Any]:
    return {
        "label": str(label or "").strip(),
        "source_kind": str(source_kind or "").strip(),
        "path": str(path or "").strip(),
        "updated_utc": str(updated_utc or "").strip(),
        "trust": str(trust or "").strip(),
    }

def _derive_retrieval_memory_state(
    *,
    transition_status: str,
    indexed_entities: int,
    evidence_documents: int,
    compiler_ready: bool,
) -> str:
    if transition_status == "standardized" and indexed_entities > 0:
        return "strong"
    if indexed_entities > 0 or evidence_documents > 0 or compiler_ready:
        return "partial"
    return "cold"

def _load_latest_benchmark_report_snapshot(*, repo_root: Path) -> dict[str, Any]:
    path = (runtime_root(repo_root=repo_root) / "odylith-benchmarks" / "latest.v1.json").resolve()
    payload = odylith_context_cache.read_json_object(path)
    return dict(payload) if isinstance(payload, Mapping) else {}

def _build_judgment_memory_snapshot(
    *,
    repo_root: Path,
    projection_updated_utc: str,
    backlog_projection: Mapping[str, Any],
    plan_projection: Mapping[str, Any],
    bug_projection: Sequence[Mapping[str, Any]],
    diagram_projection: Sequence[Mapping[str, Any]],
    runtime_state: Mapping[str, Any],
    optimization: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    benchmark_report: Mapping[str, Any],
    recent_bootstrap_packets: Sequence[Mapping[str, Any]],
    active_sessions: Sequence[Mapping[str, Any]],
    repo_dirty_paths: Sequence[str],
    welcome_state: Mapping[str, Any],
    previous_snapshot: Mapping[str, Any] | None,
    retrieval_state: str,
) -> dict[str, Any]:
    return odylith_context_engine_memory_snapshot_runtime._build_judgment_memory_snapshot(repo_root=repo_root, projection_updated_utc=projection_updated_utc, backlog_projection=backlog_projection, plan_projection=plan_projection, bug_projection=bug_projection, diagram_projection=diagram_projection, runtime_state=runtime_state, optimization=optimization, evaluation=evaluation, benchmark_report=benchmark_report, recent_bootstrap_packets=recent_bootstrap_packets, active_sessions=active_sessions, repo_dirty_paths=repo_dirty_paths, welcome_state=welcome_state, previous_snapshot=previous_snapshot, retrieval_state=retrieval_state)

def _build_memory_areas_snapshot(
    *,
    enabled: bool,
    authoritative_truth: Mapping[str, Any],
    compiler_state: Mapping[str, Any],
    guidance_catalog: Mapping[str, Any],
    runtime_state: Mapping[str, Any],
    entity_counts: Mapping[str, Any],
    backend_transition: Mapping[str, Any],
    optimization: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    judgment_memory: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return odylith_context_engine_memory_snapshot_runtime._build_memory_areas_snapshot(enabled=enabled, authoritative_truth=authoritative_truth, compiler_state=compiler_state, guidance_catalog=guidance_catalog, runtime_state=runtime_state, entity_counts=entity_counts, backend_transition=backend_transition, optimization=optimization, evaluation=evaluation, judgment_memory=judgment_memory)

def _odylith_disabled_memory_snapshot(
    *,
    repo_root: Path,
    switch_snapshot: Mapping[str, Any],
    optimization_snapshot: Mapping[str, Any],
    evaluation_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    return odylith_context_engine_memory_snapshot_runtime._odylith_disabled_memory_snapshot(repo_root=repo_root, switch_snapshot=switch_snapshot, optimization_snapshot=optimization_snapshot, evaluation_snapshot=evaluation_snapshot)

def _odylith_disabled_optimization_snapshot(
    *,
    repo_root: Path,
    switch_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "contract": "optimization_snapshot.v1",
        "version": "v1",
        "generated_utc": _utc_now(),
        "status": "disabled",
        "status_reason": "odylith_disabled",
        "odylith_switch": dict(switch_snapshot),
        "sample_size": 0,
        "overall": {"score": 0.0, "level": "disabled"},
        "packet_posture": {},
        "quality_posture": {},
        "orchestration_posture": {},
        "intent_posture": {},
        "control_advisories": {
            "state": "disabled",
            "confidence": {"score": 0, "level": "none"},
            "reasoning_mode": "disabled",
            "depth": "disabled",
            "delegation": "disabled",
            "parallelism": "disabled",
            "packet_strategy": "disabled",
            "budget_mode": "disabled",
            "retrieval_focus": "disabled",
            "speed_mode": "disabled",
            "packet_alignment_rate": 0.0,
            "packet_alignment_coverage": 0,
            "reliable_packet_alignment_rate": 0.0,
            "reliable_packet_alignment_count": 0,
            "packet_alignment_state": "disabled",
            "effective_yield_score": 0.0,
            "high_yield_rate": 0.0,
            "reliable_high_yield_rate": 0.0,
            "yield_state": "disabled",
            "focus_areas": [],
            "regressions": [],
        },
        "latency_posture": {},
        "latest_packet": {},
        "evaluation_posture": {},
        "learning_loop": {},
        "recommendations": [
            "Odylith is disabled; optimization diagnostics are suppressed for ablation studies."
        ],
    }

def _odylith_disabled_evaluation_snapshot(
    *,
    repo_root: Path,
    switch_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "contract": "evaluation_snapshot.v1",
        "version": "v1",
        "generated_utc": _utc_now(),
        "status": "disabled",
        "status_reason": "odylith_disabled",
        "odylith_switch": dict(switch_snapshot),
        "program": {
            "umbrella_id": "",
            "status": "disabled",
            "active_wave_id": "",
            "active_workstream_id": "",
        },
        "corpus_size": 0,
        "covered_case_count": 0,
        "satisfied_case_count": 0,
        "coverage_rate": 0.0,
        "satisfaction_rate": 0.0,
        "family_distribution": {},
        "status_distribution": {},
        "focus_cases": [],
        "architecture": {
            "status": "disabled",
            "corpus_size": 0,
            "covered_case_count": 0,
            "satisfied_case_count": 0,
            "coverage_rate": 0.0,
            "satisfaction_rate": 0.0,
            "avg_latency_ms": 0.0,
            "avg_estimated_bytes": 0.0,
            "avg_estimated_tokens": 0.0,
            "focus_cases": [],
            "recommendations": [
                "Odylith is disabled; architecture evaluation posture is suppressed for ablation studies."
            ],
        },
        "recommendations": [
            "Odylith is disabled; evaluation corpus posture is suppressed for ablation studies."
        ],
    }

def _rebuild_component_entry(
    entry: component_registry.ComponentEntry,
    *,
    subcomponents: Sequence[str] | None = None,
    product_layer: str | None = None,
) -> component_registry.ComponentEntry:
    return component_registry.ComponentEntry(
        component_id=entry.component_id,
        name=entry.name,
        kind=entry.kind,
        category=entry.category,
        qualification=entry.qualification,
        aliases=list(entry.aliases),
        path_prefixes=list(entry.path_prefixes),
        workstreams=list(entry.workstreams),
        diagrams=list(entry.diagrams),
        owner=entry.owner,
        status=entry.status,
        what_it_is=entry.what_it_is,
        why_tracked=entry.why_tracked,
        spec_ref=entry.spec_ref,
        sources=list(entry.sources),
        subcomponents=list(subcomponents if subcomponents is not None else entry.subcomponents),
        product_layer=str(product_layer if product_layer is not None else entry.product_layer),
    )

def _apply_odylith_component_index_ablation(
    component_index: Mapping[str, component_registry.ComponentEntry],
) -> dict[str, component_registry.ComponentEntry]:
    filtered: dict[str, component_registry.ComponentEntry] = {}
    for component_id, entry in component_index.items():
        if component_id == "odylith" or not isinstance(entry, component_registry.ComponentEntry):
            continue
        filtered[component_id] = _rebuild_component_entry(
            entry,
            subcomponents=[],
            product_layer="",
        )
    return filtered

def _apply_odylith_registry_snapshot_ablation(
    *,
    repo_root: Path,
    report: component_registry.ComponentRegistryReport,
    traceability: Mapping[str, Mapping[str, list[str]]],
    spec_snapshots: Mapping[str, component_registry.ComponentSpecSnapshot],
) -> dict[str, Any]:
    components = _apply_odylith_component_index_ablation(report.components)
    mapped_events = [
        component_registry.MappedEvent(
            event_index=row.event_index,
            ts_iso=row.ts_iso,
            kind=row.kind,
            summary=row.summary,
            workstreams=list(row.workstreams),
            artifacts=list(row.artifacts),
            explicit_components=[token for token in row.explicit_components if token != "odylith"],
            mapped_components=[token for token in row.mapped_components if token != "odylith"],
            confidence=row.confidence,
            meaningful=row.meaningful,
        )
        for row in report.mapped_events
    ]
    unmapped_meaningful_events = [
        component_registry.MappedEvent(
            event_index=row.event_index,
            ts_iso=row.ts_iso,
            kind=row.kind,
            summary=row.summary,
            workstreams=list(row.workstreams),
            artifacts=list(row.artifacts),
            explicit_components=[token for token in row.explicit_components if token != "odylith"],
            mapped_components=[token for token in row.mapped_components if token != "odylith"],
            confidence=row.confidence,
            meaningful=row.meaningful,
        )
        for row in report.unmapped_meaningful_events
    ]
    filtered_report = component_registry.ComponentRegistryReport(
        components=components,
        mapped_events=mapped_events,
        unmapped_meaningful_events=unmapped_meaningful_events,
        candidate_queue=[
            dict(item)
            for item in report.candidate_queue
            if str(item.get("component_id", "")).strip() != "odylith"
        ],
        forensic_coverage={
            component_id: coverage
            for component_id, coverage in report.forensic_coverage.items()
            if component_id in components
        },
        diagnostics=list(report.diagnostics),
    )
    return {
        "report": filtered_report,
        "traceability": {
            component_id: {
                bucket: list(values)
                for bucket, values in buckets.items()
            }
            for component_id, buckets in traceability.items()
            if component_id in components
        },
        "spec_snapshots": {
            component_id: snapshot
            for component_id, snapshot in spec_snapshots.items()
            if component_id in components
        },
        "odylith_switch": _odylith_switch_snapshot(repo_root=repo_root),
    }

def _odylith_runtime_entity_suppressed(*, repo_root: Path, entity: Mapping[str, Any]) -> bool:
    kind = str(entity.get("kind", "")).strip().lower()
    entity_id = str(entity.get("entity_id", "")).strip().lower()
    path_token = _normalize_repo_token(str(entity.get("path", "")).strip(), repo_root=repo_root)
    if kind == "component" and entity_id == "odylith":
        return True
    return bool(path_token and path_token in _ODYLITH_SUPPRESSED_PATHS and kind in {"component", "doc"})

def _odylith_query_targets_disabled(*, repo_root: Path, query: str) -> bool:
    token = str(query or "").strip().lower()
    normalized = _normalize_repo_token(str(query or "").strip(), repo_root=repo_root)
    return token in {"odylith", "odylith-platform"} or normalized in _ODYLITH_SUPPRESSED_PATHS

def _filter_odylith_search_results(
    *,
    repo_root: Path,
    results: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for row in results:
        if not isinstance(row, Mapping):
            continue
        if _odylith_runtime_entity_suppressed(repo_root=repo_root, entity=row):
            continue
        filtered.append(dict(row))
    return filtered

def load_runtime_memory_snapshot(
    *,
    repo_root: Path,
    optimization_snapshot: Mapping[str, Any] | None = None,
    evaluation_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return odylith_context_engine_memory_snapshot_runtime.load_runtime_memory_snapshot(repo_root=repo_root, optimization_snapshot=optimization_snapshot, evaluation_snapshot=evaluation_snapshot)

def _load_recent_bootstrap_packets(
    *,
    repo_root: Path,
    bootstrap_limit: int,
) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    root = Path(repo_root).resolve()
    valid_bootstraps: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(bootstraps_root(repo_root=root).glob("*.json")):
        payload = odylith_context_cache.read_json_object(path)
        if not payload:
            continue
        valid_bootstraps.append((path, payload))
    valid_bootstraps.sort(
        key=lambda item: _record_sort_timestamp(payload=item[1], key="bootstrapped_at", path=item[0]),
        reverse=True,
    )
    for path, payload in valid_bootstraps[: max(1, int(bootstrap_limit))]:
        packets.append(_packet_summary_from_bootstrap_payload(payload))
    return packets

def _packet_summary_from_bootstrap_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return odylith_context_engine_packet_summary_runtime._packet_summary_from_bootstrap_payload(payload=payload)

def _repo_paths_overlap(*, repo_root: Path, left: str, right: str) -> bool:
    left_token = _normalize_repo_token(str(left or "").strip(), repo_root=repo_root)
    right_token = _normalize_repo_token(str(right or "").strip(), repo_root=repo_root)
    if not left_token or not right_token:
        return False
    if left_token == right_token:
        return True
    left_prefix = left_token.rstrip("/") + "/"
    right_prefix = right_token.rstrip("/") + "/"
    return left_token.startswith(right_prefix) or right_token.startswith(left_prefix)

def _file_cache_signature(path: Path) -> tuple[bool, int, int]:
    try:
        stat = path.stat()
    except OSError:
        return (False, 0, 0)
    return (True, int(stat.st_mtime_ns), int(stat.st_size))

def _judgment_memory_snapshot_cached(*, repo_root: Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    path = judgment_memory_path(repo_root=root)
    cache_key = str(path)
    signature = _file_cache_signature(path)
    cached = _PROCESS_JUDGMENT_MEMORY_SNAPSHOT_CACHE.get(cache_key)
    if cached is not None and cached[0] == signature:
        return dict(cached[1])
    snapshot = odylith_context_cache.read_json_object(path) if signature[0] else {}
    payload = dict(snapshot) if isinstance(snapshot, Mapping) else {}
    _PROCESS_JUDGMENT_MEMORY_SNAPSHOT_CACHE[cache_key] = (signature, payload)
    return dict(payload)

def _load_judgment_workstream_hint(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    normalized_paths = _normalize_changed_path_list(repo_root=root, values=changed_paths)
    if not normalized_paths:
        return {}
    snapshot = _judgment_memory_snapshot_cached(repo_root=root)
    starter_slice = dict(snapshot.get("starter_slice", {})) if isinstance(snapshot.get("starter_slice"), Mapping) else {}
    workstream_id = _workstream_token(str(starter_slice.get("workstream_id", "")).strip())
    starter_path = _normalize_repo_token(str(starter_slice.get("path", "")).strip(), repo_root=root)
    if not workstream_id or not starter_path:
        return {}
    matched_paths = [
        path
        for path in normalized_paths
        if _repo_paths_overlap(repo_root=root, left=path, right=starter_path)
    ]
    if not matched_paths:
        return {}
    starter_status = str(starter_slice.get("status", "")).strip()
    return {
        "workstream_id": workstream_id,
        "slice_path": starter_path,
        "matched_paths": matched_paths[:4],
        "status": starter_status,
        "confidence": "high" if starter_status == "established" else "medium",
        "reason": f"Durable slice memory already ties `{starter_path}` to `{workstream_id}`.",
    }

def _repo_scan_degraded_reason(packet: Mapping[str, Any]) -> str:
    full_scan_reason = str(packet.get("full_scan_reason", "")).strip()
    miss_recovery_mode = str(packet.get("miss_recovery_mode", "")).strip()
    if miss_recovery_mode == "repo_scan_fallback":
        return full_scan_reason or "miss_recovery_repo_scan_fallback"
    if full_scan_reason in {
        "odylith_backend_unavailable",
        "repo_scan_candidate_only",
        "runtime_unavailable",
        "working_tree_scope_degraded",
    }:
        return full_scan_reason
    return ""


def _reason_distribution(
    rows: Sequence[Mapping[str, Any]],
    *,
    reason_key: str,
) -> dict[str, int]:
    return _sorted_count_map([str(row.get(reason_key, "")).strip() for row in rows])

def _governance_runtime_first_snapshot(
    *,
    repo_root: Path,
    limit: int = 24,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    scan_limit = max(64, max(1, int(limit)) * 12)
    rows = [
        row
        for row in odylith_control_state.load_timing_rows(repo_root=root, limit=scan_limit)
        if str(row.get("category", "")).strip() == "sync"
        and str(row.get("operation", "")).strip() == "governance_runtime_first"
    ][: max(1, int(limit))]
    samples = [
        dict(row.get("metadata", {}))
        for row in rows
        if isinstance(row, Mapping) and isinstance(row.get("metadata"), Mapping)
    ]
    attempted_rows = [row for row in samples if bool(row.get("runtime_fast_path"))]

    def _rate(items: Sequence[Mapping[str, Any]], field_name: str) -> float:
        if not items:
            return 0.0
        return round(
            sum(1 for row in items if bool(row.get(field_name))) / max(1, len(items)),
            3,
        )

    fallback_reason_distribution = _sorted_count_map(
        [str(row.get("fallback_reason", "")).strip() for row in attempted_rows if str(row.get("fallback_reason", "")).strip()]
    )
    live_snapshot = {
        "status": "active" if attempted_rows else "no_history",
        "sample_size": len(attempted_rows),
        "usage_rate": _rate(attempted_rows, "used_governance_packet"),
        "fallback_rate": _rate(attempted_rows, "fallback_applied"),
        "fallback_reason_distribution": fallback_reason_distribution,
        "evidence_source": "live_timings",
    }
    if int(live_snapshot.get("sample_size", 0) or 0) > 0:
        _persist_runtime_proof_section(
            repo_root=root,
            section="governance_runtime_first",
            payload=live_snapshot,
        )
        return live_snapshot
    return _sticky_snapshot_from_section(
        repo_root=root,
        section="governance_runtime_first",
        live_snapshot=live_snapshot,
        valid_when=lambda snapshot: int(snapshot.get("sample_size", 0) or 0) > 0,
    )

def _packet_benchmark_summary_for_runtime_packet(
    *,
    repo_root: Path,
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    corpus = odylith_context_cache.read_json_object(optimization_evaluation_corpus_path(repo_root=root))
    if not isinstance(corpus, Mapping):
        corpus = {}
    cases = odylith_benchmark_contract.packet_benchmark_scenarios(corpus)
    matched_case_ids: list[str] = []
    drift_case_ids: list[str] = []
    satisfied_case_count = 0
    for case in cases:
        match_spec = dict(case.get("match", {})) if isinstance(case.get("match"), Mapping) else {}
        if not _packet_matches_evaluation_case(packet, match_spec):
            continue
        case_id = str(case.get("case_id", "")).strip()
        if case_id:
            matched_case_ids.append(case_id)
        expect_spec = dict(case.get("expect", {})) if isinstance(case.get("expect"), Mapping) else {}
        expectation_ok, _details = _packet_satisfies_evaluation_expectations(packet, expect_spec)
        if expectation_ok:
            satisfied_case_count += 1
        elif case_id:
            drift_case_ids.append(case_id)
    return {
        "matched_case_count": len(matched_case_ids),
        "satisfied_case_count": satisfied_case_count,
        "matched_case_ids": matched_case_ids,
        "drift_case_ids": drift_case_ids,
    }

def _expected_token_set(value: Any) -> set[str]:
    if isinstance(value, list):
        return {str(token).strip() for token in value if str(token).strip()}
    token = str(value or "").strip()
    return {token} if token else set()

def _packet_matches_evaluation_case(packet: Mapping[str, Any], match_spec: Mapping[str, Any]) -> bool:
    path_tokens = {str(token).strip() for token in packet.get("path_tokens", []) if str(token).strip()}
    paths_all = {str(token).strip() for token in match_spec.get("paths_all", []) if str(token).strip()} if isinstance(match_spec.get("paths_all"), list) else set()
    paths_any = {str(token).strip() for token in match_spec.get("paths_any", []) if str(token).strip()} if isinstance(match_spec.get("paths_any"), list) else set()
    if paths_all and not paths_all.issubset(path_tokens):
        return False
    if paths_any and not path_tokens.intersection(paths_any):
        return False
    workstream = str(match_spec.get("workstream", "")).strip().upper()
    if workstream and str(packet.get("workstream", "")).strip().upper() != workstream:
        return False
    packet_states = _expected_token_set(match_spec.get("packet_state"))
    if packet_states and str(packet.get("packet_state", "")).strip() not in packet_states:
        return False
    intent_families = _expected_token_set(match_spec.get("intent_family"))
    if intent_families and str(packet.get("intent_family", "")).strip() not in intent_families:
        return False
    return True

def _packet_satisfies_evaluation_expectations(
    packet: Mapping[str, Any],
    expect_spec: Mapping[str, Any],
) -> tuple[bool, dict[str, Any]]:
    details = {
        "expected_packet_state": "",
        "observed_packet_state": str(packet.get("packet_state", "")).strip(),
        "expected_intent_family": "",
        "observed_intent_family": str(packet.get("intent_family", "")).strip(),
    }
    if not isinstance(expect_spec, Mapping) or not expect_spec:
        return True, details
    matched = True
    for field_name in (
        "packet_source",
        "packet_kind",
        "selection_state",
        "packet_state",
        "workstream",
        "intent_family",
        "accuracy_posture",
        "routing_confidence",
        "proof_resolution_state",
        "proof_status",
        "proof_frontier_phase",
        "proof_first_failing_phase",
        "claim_guard_highest_truthful_claim",
        "claim_guard_claim_scope",
        "claim_guard_gate_state",
        "execution_engine_outcome",
        "execution_engine_mode",
        "execution_engine_next_move",
        "execution_engine_current_phase",
        "execution_engine_last_successful_phase",
        "execution_engine_closure",
        "execution_engine_wait_status",
        "execution_engine_resume_token",
        "execution_engine_validation_archetype",
        "execution_engine_authoritative_lane",
        "execution_engine_target_lane",
        "execution_engine_host_family",
        "execution_engine_model_family",
    ):
        expected = _expected_token_set(expect_spec.get(field_name))
        if not expected:
            continue
        observed = str(packet.get(field_name, "")).strip()
        details[f"expected_{field_name}"] = sorted(expected)
        details[f"observed_{field_name}"] = observed
        if observed not in expected:
            matched = False
    for field_name in (
        "within_budget",
        "route_ready",
        "native_spawn_ready",
        "narrowing_required",
        "proof_state_present",
        "claim_guard_hosted_frontier_advanced",
        "claim_guard_same_fingerprint_as_last_falsification",
        "proof_same_fingerprint_reopened",
        "execution_engine_present",
        "execution_engine_requires_reanchor",
    ):
        if field_name not in expect_spec:
            continue
        expected_bool = bool(expect_spec.get(field_name))
        observed_bool = bool(packet.get(field_name))
        details[f"expected_{field_name}"] = expected_bool
        details[f"observed_{field_name}"] = observed_bool
        if observed_bool != expected_bool:
            matched = False
    for field_name in ("miss_recovery_active", "miss_recovery_applied"):
        if field_name not in expect_spec:
            continue
        expected_bool = bool(expect_spec.get(field_name))
        observed_bool = bool(packet.get(field_name))
        details[f"expected_{field_name}"] = expected_bool
        details[f"observed_{field_name}"] = observed_bool
        if observed_bool != expected_bool:
            matched = False
    expected_miss_mode = _expected_token_set(expect_spec.get("miss_recovery_mode"))
    if expected_miss_mode:
        observed_miss_mode = str(packet.get("miss_recovery_mode", "")).strip()
        details["expected_miss_recovery_mode"] = sorted(expected_miss_mode)
        details["observed_miss_recovery_mode"] = observed_miss_mode
        if observed_miss_mode not in expected_miss_mode:
            matched = False
    return matched, details

def _architecture_timing_matches_evaluation_case(
    timing_row: Mapping[str, Any],
    match_spec: Mapping[str, Any],
) -> bool:
    metadata = dict(timing_row.get("metadata", {})) if isinstance(timing_row.get("metadata"), Mapping) else {}
    changed_paths = {
        str(token).strip()
        for token in metadata.get("changed_paths", [])
        if str(token).strip()
    } if isinstance(metadata.get("changed_paths"), list) else set()
    domain_ids = {
        str(token).strip()
        for token in metadata.get("domain_ids", [])
        if str(token).strip()
    } if isinstance(metadata.get("domain_ids"), list) else set()
    paths_all = {str(token).strip() for token in match_spec.get("paths_all", []) if str(token).strip()} if isinstance(match_spec.get("paths_all"), list) else set()
    paths_any = {str(token).strip() for token in match_spec.get("paths_any", []) if str(token).strip()} if isinstance(match_spec.get("paths_any"), list) else set()
    domains_any = {str(token).strip() for token in match_spec.get("domains_any", []) if str(token).strip()} if isinstance(match_spec.get("domains_any"), list) else set()
    if paths_all and not paths_all.issubset(changed_paths):
        return False
    if paths_any and not changed_paths.intersection(paths_any):
        return False
    if domains_any and not domain_ids.intersection(domains_any):
        return False
    return True

def _architecture_timing_satisfies_evaluation_expectations(
    timing_row: Mapping[str, Any],
    expect_spec: Mapping[str, Any],
) -> tuple[bool, dict[str, Any]]:
    metadata = dict(timing_row.get("metadata", {})) if isinstance(timing_row.get("metadata"), Mapping) else {}
    details = {
        "observed_confidence_tier": str(metadata.get("confidence_tier", "")).strip(),
        "observed_full_scan_recommended": bool(metadata.get("full_scan_recommended")),
        "observed_contract_touchpoint_count": int(metadata.get("contract_touchpoint_count", 0) or 0),
        "observed_execution_hint_mode": str(metadata.get("execution_hint_mode", "")).strip(),
        "observed_risk_tier": str(metadata.get("risk_tier", "")).strip(),
    }
    if not isinstance(expect_spec, Mapping) or not expect_spec:
        return True, details
    matched = True
    expected_confidence = _expected_token_set(expect_spec.get("confidence_tier"))
    if expected_confidence:
        details["expected_confidence_tier"] = sorted(expected_confidence)
        if details["observed_confidence_tier"] not in expected_confidence:
            matched = False
    for field_name in ("full_scan_recommended", "resolved"):
        if field_name not in expect_spec:
            continue
        expected_bool = bool(expect_spec.get(field_name))
        observed_bool = bool(metadata.get(field_name))
        details[f"expected_{field_name}"] = expected_bool
        details[f"observed_{field_name}"] = observed_bool
        if observed_bool != expected_bool:
            matched = False
    expected_execution_modes = _expected_token_set(expect_spec.get("execution_hint_mode"))
    if expected_execution_modes:
        details["expected_execution_hint_mode"] = sorted(expected_execution_modes)
        if details["observed_execution_hint_mode"] not in expected_execution_modes:
            matched = False
    expected_risk_tiers = _expected_token_set(expect_spec.get("risk_tier"))
    if expected_risk_tiers:
        details["expected_risk_tier"] = sorted(expected_risk_tiers)
        if details["observed_risk_tier"] not in expected_risk_tiers:
            matched = False
    if "contract_touchpoints_min" in expect_spec:
        expected_min = int(expect_spec.get("contract_touchpoints_min", 0) or 0)
        details["expected_contract_touchpoints_min"] = expected_min
        if details["observed_contract_touchpoint_count"] < expected_min:
            matched = False
    if "authority_graph_edges_min" in expect_spec:
        expected_min = int(expect_spec.get("authority_graph_edges_min", 0) or 0)
        observed_count = int(metadata.get("authority_graph_edge_count", 0) or 0)
        details["expected_authority_graph_edges_min"] = expected_min
        details["observed_authority_graph_edge_count"] = observed_count
        if observed_count < expected_min:
            matched = False
    return matched, details

def _architecture_evaluation_snapshot(
    *,
    repo_root: Path,
    corpus: Mapping[str, Any],
    focus_limit: int = 4,
    timing_limit: int = 48,
) -> dict[str, Any]:
    return odylith_context_engine_memory_snapshot_runtime._architecture_evaluation_snapshot(repo_root=repo_root, corpus=corpus, focus_limit=focus_limit, timing_limit=timing_limit)

def orchestration_decision_ledgers_root(*, repo_root: Path) -> Path:
    return (Path(repo_root).resolve() / ".odylith" / "subagent_orchestrator" / "decision-ledgers").resolve()

def _orchestration_adoption_snapshot_cache_signature(
    *,
    repo_root: Path,
    limit: int,
) -> tuple[Any, ...]:
    root = orchestration_decision_ledgers_root(repo_root=repo_root)
    proof_path = proof_surfaces_path(repo_root=repo_root)
    proof_signature = odylith_context_cache.path_signature(proof_path)
    if not root.is_dir():
        return (str(root), int(limit), 0, 0, int(proof_signature.get("mtime_ns", 0) or 0))
    rows = sorted(
        ((path.stat().st_mtime_ns, path.name) for path in root.glob("*.json") if path.is_file()),
        reverse=True,
    )[: max(1, int(limit))]
    latest_mtime = rows[0][0] if rows else 0
    return (str(root), int(limit), len(rows), latest_mtime, int(proof_signature.get("mtime_ns", 0) or 0))

def load_orchestration_adoption_snapshot(
    *,
    repo_root: Path,
    limit: int = 12,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    cache_key = f"{root}:orchestration_adoption_snapshot:{max(1, int(limit))}"
    cache_signature = _orchestration_adoption_snapshot_cache_signature(repo_root=root, limit=limit)
    now = time.monotonic()
    cached = _PROCESS_ORCHESTRATION_ADOPTION_SNAPSHOT_CACHE.get(cache_key)
    if cached is not None:
        cached_signature, cached_until, cached_payload = cached
        if cached_signature == cache_signature and cached_until > now:
            return dict(cached_payload)

    ledger_root = orchestration_decision_ledgers_root(repo_root=root)
    ledger_paths = (
        sorted(
            (path for path in ledger_root.glob("*.json") if path.is_file()),
            key=lambda path: path.stat().st_mtime_ns,
            reverse=True,
        )[: max(1, int(limit))]
        if ledger_root.is_dir()
        else []
    )
    rows: list[dict[str, Any]] = []
    latest_recorded_at = ""
    for path in ledger_paths:
        ledger = odylith_context_cache.read_json_object(path)
        if not isinstance(ledger, Mapping):
            continue
        decision_summary = dict(ledger.get("decision_summary", {})) if isinstance(ledger.get("decision_summary"), Mapping) else {}
        adoption = dict(decision_summary.get("odylith_adoption", {})) if isinstance(decision_summary.get("odylith_adoption"), Mapping) else {}
        if not adoption:
            continue
        recorded_at = str(ledger.get("updated_at", "")).strip() or str(ledger.get("recorded_at", "")).strip()
        if recorded_at and not latest_recorded_at:
            latest_recorded_at = recorded_at
        rows.append(
            {
                "recorded_at": recorded_at,
                "packet_present": bool(adoption.get("packet_present")),
                "auto_grounded": bool(adoption.get("auto_grounding_applied")),
                "route_ready": bool(adoption.get("route_ready")),
                "native_spawn_ready": bool(adoption.get("native_spawn_ready")),
                "requires_widening": bool(adoption.get("requires_widening")),
                "grounded_delegate": bool(adoption.get("grounded_delegate")),
                "workspace_daemon_reused": bool(adoption.get("workspace_daemon_reused")),
                "session_namespaced": bool(adoption.get("session_namespaced")),
                "operation": str(adoption.get("operation", "")).strip(),
                "grounding_source": str(adoption.get("grounding_source", "")).strip(),
                "runtime_source": str(adoption.get("runtime_source", "")).strip(),
            }
        )

    def _rate_for(field_name: str) -> float:
        if not rows:
            return 0.0
        return round(sum(1 for row in rows if bool(row.get(field_name))) / max(1, len(rows)), 3)

    live_snapshot = {
        "status": "active" if rows else "no_history",
        "sample_size": len(rows),
        "latest_recorded_at": latest_recorded_at,
        "packet_present_rate": _rate_for("packet_present"),
        "auto_grounded_rate": _rate_for("auto_grounded"),
        "route_ready_rate": _rate_for("route_ready"),
        "native_spawn_ready_rate": _rate_for("native_spawn_ready"),
        "requires_widening_rate": _rate_for("requires_widening"),
        "grounded_delegate_rate": _rate_for("grounded_delegate"),
        "workspace_daemon_reused_rate": _rate_for("workspace_daemon_reused"),
        "session_namespaced_rate": _rate_for("session_namespaced"),
        "operation_distribution": _sorted_count_map([str(row.get("operation", "")).strip() for row in rows]),
        "grounding_source_distribution": _sorted_count_map([str(row.get("grounding_source", "")).strip() for row in rows]),
        "runtime_source_distribution": _sorted_count_map([str(row.get("runtime_source", "")).strip() for row in rows]),
        "evidence_source": "live_decision_ledgers",
    }
    payload = dict(live_snapshot)
    if int(live_snapshot.get("sample_size", 0) or 0) > 0:
        _persist_runtime_proof_section(
            repo_root=root,
            section="orchestration_adoption",
            payload=live_snapshot,
        )
    else:
        payload = _sticky_snapshot_from_section(
            repo_root=root,
            section="orchestration_adoption",
            live_snapshot=live_snapshot,
            valid_when=lambda snapshot: int(snapshot.get("sample_size", 0) or 0) > 0,
        )
    _PROCESS_ORCHESTRATION_ADOPTION_SNAPSHOT_CACHE[cache_key] = (
        cache_signature,
        now + _PROCESS_OPTIMIZATION_SNAPSHOT_CACHE_TTL_SECONDS,
        dict(payload),
    )
    return payload

def persist_orchestration_adoption_snapshot(
    *,
    repo_root: Path,
    snapshot: Mapping[str, Any],
    source: str = "external_proof",
) -> dict[str, Any]:
    payload = dict(snapshot)
    if int(payload.get("sample_size", 0) or 0) <= 0:
        return payload
    payload.setdefault("evidence_source", str(source or "external_proof").strip() or "external_proof")
    return _persist_runtime_proof_section(
        repo_root=Path(repo_root).resolve(),
        section="orchestration_adoption",
        payload=payload,
    )

def load_runtime_optimization_snapshot(
    *,
    repo_root: Path,
    bootstrap_limit: int = 12,
    timing_limit: int = 24,
) -> dict[str, Any]:
    """Summarize recent runtime packet and routing posture for operator tuning."""

    root = Path(repo_root).resolve()
    cache_key = f"{root}:optimization_snapshot:{int(bootstrap_limit)}:{int(timing_limit)}"
    cache_signature = _runtime_optimization_cache_signature(repo_root=root)
    now = time.monotonic()
    cached = _PROCESS_OPTIMIZATION_SNAPSHOT_CACHE.get(cache_key)
    if cached is not None:
        cached_signature, cached_until, cached_payload = cached
        if cached_signature == cache_signature and cached_until > now:
            return dict(cached_payload)
    odylith_switch = _odylith_switch_snapshot(repo_root=root)
    if not bool(odylith_switch.get("enabled", True)):
        payload = _odylith_disabled_optimization_snapshot(
            repo_root=root,
            switch_snapshot=odylith_switch,
        )
        _PROCESS_OPTIMIZATION_SNAPSHOT_CACHE[cache_key] = (
            cache_signature,
            now + _PROCESS_OPTIMIZATION_SNAPSHOT_CACHE_TTL_SECONDS,
            dict(payload),
        )
        return payload
    packets = _load_recent_bootstrap_packets(repo_root=root, bootstrap_limit=bootstrap_limit)
    timing_summary = load_runtime_timing_summary(repo_root=root, limit=max(1, int(timing_limit)))
    learning_summary = odylith_evaluation_ledger.summarize(
        repo_root=root,
        limit=max(64, bootstrap_limit * 8),
    )
    operations = timing_summary.get("operations", []) if isinstance(timing_summary, Mapping) else []
    if not isinstance(operations, list):
        operations = []
    governance_runtime_first = _governance_runtime_first_snapshot(repo_root=root, limit=max(12, timing_limit))

    sample_size = len(packets)
    avg_bytes = round(sum(int(row.get("estimated_bytes", 0) or 0) for row in packets) / max(1, sample_size), 1)
    avg_tokens = round(sum(int(row.get("estimated_tokens", 0) or 0) for row in packets) / max(1, sample_size), 1)
    avg_utility_score = round(sum(int(row.get("utility_score", 0) or 0) for row in packets) / max(1, sample_size), 1)
    avg_density = round(sum(float(row.get("density_per_1k_tokens", 0.0) or 0.0) for row in packets) / max(1, sample_size), 2)
    avg_context_density_score = round(
        sum(int(row.get("context_density_score", 0) or 0) for row in packets) / max(1, sample_size),
        2,
    )
    avg_context_density_per_1k = round(
        sum(float(row.get("context_density_per_1k_tokens", 0.0) or 0.0) for row in packets) / max(1, sample_size),
        2,
    )
    avg_reasoning_readiness_score = round(
        sum(int(row.get("reasoning_readiness_score", 0) or 0) for row in packets) / max(1, sample_size),
        2,
    )
    avg_evidence_diversity_score = round(
        sum(int(row.get("evidence_diversity_score", 0) or 0) for row in packets) / max(1, sample_size),
        2,
    )
    within_budget_rate = round(
        sum(1 for row in packets if bool(row.get("within_budget"))) / max(1, sample_size),
        3,
    )
    route_ready_rate = round(
        sum(1 for row in packets if bool(row.get("route_ready"))) / max(1, sample_size),
        3,
    )
    native_spawn_ready_rate = round(
        sum(1 for row in packets if bool(row.get("native_spawn_ready"))) / max(1, sample_size),
        3,
    )
    orchestration_adoption = load_orchestration_adoption_snapshot(repo_root=root, limit=max(12, bootstrap_limit))
    if int(orchestration_adoption.get("sample_size", 0) or 0) > 0:
        route_ready_rate = max(route_ready_rate, float(orchestration_adoption.get("route_ready_rate", 0.0) or 0.0))
        native_spawn_ready_rate = max(
            native_spawn_ready_rate,
            float(orchestration_adoption.get("native_spawn_ready_rate", 0.0) or 0.0),
        )
    high_utility_rate = round(
        sum(1 for row in packets if str(row.get("utility_level", "")).strip() == "high") / max(1, sample_size),
        3,
    )
    high_routing_confidence_rate = round(
        sum(1 for row in packets if str(row.get("routing_confidence", "")).strip() == "high") / max(1, sample_size),
        3,
    )
    narrowing_rate = round(
        sum(1 for row in packets if bool(row.get("narrowing_required"))) / max(1, sample_size),
        3,
    )
    miss_recovery_rate = round(
        sum(1 for row in packets if bool(row.get("miss_recovery_active"))) / max(1, sample_size),
        3,
    )
    miss_recovery_applied_rate = round(
        sum(1 for row in packets if bool(row.get("miss_recovery_applied"))) / max(1, sample_size),
        3,
    )
    deep_reasoning_ready_rate = round(
        sum(1 for row in packets if bool(row.get("deep_reasoning_ready"))) / max(1, sample_size),
        3,
    )
    repo_scan_degraded_rows = [row for row in packets if bool(row.get("repo_scan_degraded"))]
    repo_scan_degraded_rate = round(len(repo_scan_degraded_rows) / max(1, sample_size), 3)
    repo_scan_degraded_reason_distribution = _reason_distribution(
        repo_scan_degraded_rows,
        reason_key="repo_scan_degraded_reason",
    )
    hard_grounding_failure_rows = [row for row in packets if bool(row.get("hard_grounding_failure"))]
    hard_grounding_failure_rate = round(len(hard_grounding_failure_rows) / max(1, sample_size), 3)
    hard_grounding_failure_reason_distribution = _reason_distribution(
        hard_grounding_failure_rows,
        reason_key="hard_grounding_failure_reason",
    )
    soft_widening_rows = [row for row in packets if bool(row.get("soft_widening"))]
    soft_widening_rate = round(len(soft_widening_rows) / max(1, sample_size), 3)
    soft_widening_reason_distribution = _reason_distribution(
        soft_widening_rows,
        reason_key="soft_widening_reason",
    )
    visible_fallback_receipt_rows = [row for row in packets if bool(row.get("visible_fallback_receipt"))]
    visible_fallback_receipt_rate = round(len(visible_fallback_receipt_rows) / max(1, sample_size), 3)
    visible_fallback_receipt_reason_distribution = _reason_distribution(
        visible_fallback_receipt_rows,
        reason_key="visible_fallback_receipt_reason",
    )
    packet_state_distribution = _sorted_count_map([str(row.get("packet_state", "")).strip() for row in packets])
    packet_strategy_distribution = _sorted_count_map([str(row.get("adaptive_packet_strategy", "")).strip() for row in packets])
    budget_mode_distribution = _sorted_count_map([str(row.get("adaptive_budget_mode", "")).strip() for row in packets])
    speed_mode_distribution = _sorted_count_map([str(row.get("adaptive_speed_mode", "")).strip() for row in packets])
    selection_bias_distribution = _sorted_count_map([str(row.get("adaptive_selection_bias", "")).strip() for row in packets])
    packet_reliability_distribution = _sorted_count_map([str(row.get("adaptive_reliability", "")).strip() for row in packets])
    parallelism_distribution = _sorted_count_map([str(row.get("parallelism_hint", "")).strip() for row in packets])
    reasoning_distribution = _sorted_count_map([str(row.get("reasoning_bias", "")).strip() for row in packets])
    richest_distribution = _sorted_count_map([str(row.get("context_richness", "")).strip() for row in packets])
    context_density_distribution = _sorted_count_map([str(row.get("context_density_level", "")).strip() for row in packets])
    reasoning_readiness_distribution = _sorted_count_map([str(row.get("reasoning_readiness_level", "")).strip() for row in packets])
    reasoning_mode_distribution = _sorted_count_map([str(row.get("reasoning_readiness_mode", "")).strip() for row in packets])
    evidence_diversity_distribution = _sorted_count_map([str(row.get("evidence_diversity_level", "")).strip() for row in packets])
    intent_family_distribution = _sorted_count_map([str(row.get("intent_family", "")).strip() for row in packets])
    intent_mode_distribution = _sorted_count_map([str(row.get("intent_mode", "")).strip() for row in packets])
    intent_critical_path_distribution = _sorted_count_map([str(row.get("intent_critical_path", "")).strip() for row in packets])
    execution_profile_distribution = _sorted_count_map([str(row.get("odylith_execution_profile", "")).strip() for row in packets])
    execution_reasoning_distribution = _sorted_count_map(
        [str(row.get("odylith_execution_reasoning_effort", "")).strip() for row in packets]
    )
    execution_agent_role_distribution = _sorted_count_map(
        [str(row.get("odylith_execution_agent_role", "")).strip() for row in packets]
    )
    execution_selection_mode_distribution = _sorted_count_map(
        [str(row.get("odylith_execution_selection_mode", "")).strip() for row in packets]
    )
    execution_delegate_preference_distribution = _sorted_count_map(
        [str(row.get("odylith_execution_delegate_preference", "")).strip() for row in packets]
    )
    execution_source_distribution = _sorted_count_map(
        [str(row.get("odylith_execution_source", "")).strip() for row in packets]
    )
    intent_explicit_rate = round(
        sum(1 for row in packets if bool(row.get("intent_explicit"))) / max(1, sample_size),
        3,
    )
    high_intent_confidence_rate = round(
        sum(1 for row in packets if str(row.get("intent_confidence", "")).strip() == "high") / max(1, sample_size),
        3,
    )
    delegated_lane_rate = round(
        sum(1 for row in packets if str(row.get("odylith_execution_delegate_preference", "")).strip() == "delegate")
        / max(1, sample_size),
        3,
    )
    hold_local_rate = round(
        sum(1 for row in packets if str(row.get("odylith_execution_delegate_preference", "")).strip() == "hold_local")
        / max(1, sample_size),
        3,
    )
    high_execution_confidence_rate = round(
        sum(1 for row in packets if int(row.get("odylith_execution_confidence_score", 0) or 0) >= 3) / max(1, sample_size),
        3,
    )
    runtime_backed_execution_rate = round(
        sum(
            1
            for row in packets
            if str(row.get("odylith_execution_source", "")).strip() in {"odylith_runtime_packet", "odylith_runtime"}
        )
        / max(1, sample_size),
        3,
    )
    top_intent_family = next(iter(intent_family_distribution), "")
    learning_packet = (
        dict(learning_summary.get("packet_events", {}))
        if isinstance(learning_summary.get("packet_events"), Mapping)
        else {}
    )
    learning_router = (
        dict(learning_summary.get("router_outcomes", {}))
        if isinstance(learning_summary.get("router_outcomes"), Mapping)
        else {}
    )
    learning_orchestration = (
        dict(learning_summary.get("orchestration_feedback", {}))
        if isinstance(learning_summary.get("orchestration_feedback"), Mapping)
        else {}
    )
    learning_decision_quality = (
        dict(learning_summary.get("decision_quality", {}))
        if isinstance(learning_summary.get("decision_quality"), Mapping)
        else {}
    )
    learning_decision_quality_confidence = (
        dict(learning_decision_quality.get("confidence", {}))
        if isinstance(learning_decision_quality.get("confidence"), Mapping)
        else {}
    )
    learning_trend = (
        dict(learning_summary.get("trend_posture", {}))
        if isinstance(learning_summary.get("trend_posture"), Mapping)
        else {}
    )
    learning_control = (
        dict(learning_summary.get("control_posture", {}))
        if isinstance(learning_summary.get("control_posture"), Mapping)
        else {}
    )
    learning_freshness = (
        dict(learning_summary.get("freshness", {}))
        if isinstance(learning_summary.get("freshness"), Mapping)
        else {}
    )
    learning_evidence_strength = (
        dict(learning_summary.get("evidence_strength", {}))
        if isinstance(learning_summary.get("evidence_strength"), Mapping)
        else {}
    )
    learning_advisories = (
        dict(learning_summary.get("control_advisories", {}))
        if isinstance(learning_summary.get("control_advisories"), Mapping)
        else {}
    )

    latency_posture: dict[str, Any] = {}
    for row in operations:
        if not isinstance(row, Mapping):
            continue
        operation = str(row.get("operation", "")).strip()
        if operation not in {"impact", "session_brief", "bootstrap_session"}:
            continue
        latency_posture[operation] = {
            "avg_ms": round(float(row.get("avg_ms", 0.0) or 0.0), 3),
            "latest_ms": round(float(row.get("latest_ms", 0.0) or 0.0), 3),
            "count": int(row.get("count", 0) or 0),
        }

    recommendation_rows: list[str] = []
    if sample_size == 0:
        recommendation_rows.append(
            f"Optimization history is sparse; run `{display_command('context-engine', '--repo-root', '.', 'bootstrap-session', '<path>')}` on a grounded slice to seed packet evidence."
        )
    else:
        if within_budget_rate < 1.0:
            recommendation_rows.append(
                "Recent packets are not consistently within budget; inspect `packet_metrics.sections.largest` on the newest slice before expanding context further."
            )
        if high_utility_rate < 0.5:
            recommendation_rows.append(
                "Retained context utility is not yet consistently high; tighten anchors or explicit workstream selection before asking for richer execution."
            )
        if route_ready_rate < 0.5 and narrowing_rate >= 0.25:
            recommendation_rows.append(
                "A meaningful share of recent slices still required narrowing; improve prompt anchors or explicit path/workstream grounding before pushing more delegation."
            )
        if native_spawn_ready_rate < route_ready_rate:
            recommendation_rows.append(
                "Route-ready slices are not always native-spawn-ready; check retained validation/test/command clarity before widening delegated fan-out."
            )
        if avg_context_density_score < 2.0:
            recommendation_rows.append(
                "Context density is still shallow on average; improve path anchors and reduce redundant broad guidance before asking Odylith for deeper reasoning."
            )
        if deep_reasoning_ready_rate < 0.5 and route_ready_rate >= 0.5:
            recommendation_rows.append(
                "Many slices are route-ready but not yet deep-reasoning-ready; prefer unique actionable guidance and compact validation evidence over wider recall."
            )
        if miss_recovery_rate > 0.0 and miss_recovery_applied_rate < miss_recovery_rate:
            recommendation_rows.append(
                "Miss recovery is activating without always adding retained evidence; tighten the recovery gates or query stems before widening that lane."
            )
        if intent_explicit_rate < 0.5:
            recommendation_rows.append(
                "Recent session packets rely heavily on derived intent; pass `--intent` explicitly on high-value slices so routing and orchestration can specialize earlier."
            )
    if float(learning_router.get("failure_rate", 0.0) or 0.0) >= 0.35:
        recommendation_rows.append(
            "Delegated router outcomes are failing too often; bias toward narrower grounded slices and reduce speculative fan-out until acceptance recovers."
        )
        if float(learning_orchestration.get("parallel_failure_rate", 0.0) or 0.0) >= 0.25:
            recommendation_rows.append(
                "Recent orchestration feedback shows merge or false-parallel regressions; keep parallel fan-out guarded unless the slice is explicitly disjoint."
            )
    overall_freshness = dict(learning_freshness.get("overall", {})) if isinstance(learning_freshness.get("overall"), Mapping) else {}
    if str(overall_freshness.get("bucket", "")).strip() in {"aging", "stale"}:
        recommendation_rows.append(
            "Optimization history is aging or stale; prefer fresh grounded bootstrap sessions before trusting the current advisory loop for aggressive depth or fan-out."
        )
    if str(learning_evidence_strength.get("sample_balance", "")).strip() in {"thin", "partial"}:
        recommendation_rows.append(
            "Evaluation evidence is still thin or imbalanced across packet/router/orchestration lanes; treat the current control posture as provisional."
        )
    decision_quality_reliable = bool(
        int(learning_decision_quality_confidence.get("score", 0) or 0) >= 3
        and float(learning_decision_quality.get("closeout_observation_rate", 0.0) or 0.0) >= 0.34
    )
    if learning_decision_quality and not decision_quality_reliable:
        recommendation_rows.append(
            "Decision-quality evidence is still thin or only partially observed; do not overreact to regret or churn until more delegated slices reach clean closeout."
        )
    if decision_quality_reliable and float(learning_decision_quality.get("delegation_regret_rate", 0.0) or 0.0) >= 0.25:
        recommendation_rows.append(
            "Recent delegated slices are producing regret after execution; tighten delegated scope and require stronger route readiness before widening fan-out again."
        )
    if decision_quality_reliable and float(learning_decision_quality.get("followup_churn_rate", 0.0) or 0.0) >= 0.25:
        recommendation_rows.append(
            "Delegated leaves are accumulating too much follow-up churn; treat clean closeout as a hard success gate before trusting raw acceptance rates."
        )
    if decision_quality_reliable and float(learning_decision_quality.get("merge_burden_underestimate_rate", 0.0) or 0.0) >= 0.2:
        recommendation_rows.append(
            "Odylith is still underpredicting merge burden on recent delegated slices; keep parallel write fan-out guarded until merge calibration improves."
        )
    if decision_quality_reliable and float(learning_decision_quality.get("validation_pressure_underestimate_rate", 0.0) or 0.0) >= 0.25:
        recommendation_rows.append(
            "Odylith is still underpredicting validation pressure on recent delegated slices; favor narrower packets and stronger validation-oriented reasoning until calibration improves."
        )
    if float(learning_packet.get("avg_effective_yield_score", 0.0) or 0.0) < 0.6 and packets:
        recommendation_rows.append(
            "Recent packets are still too expensive for the grounded signal they retain; prefer denser anchors and more selective evidence packing before spending extra depth."
        )
    latest_packet = packets[0] if packets else {}
    if str(learning_control.get("packet_strategy", "")).strip() == "precision_first":
        recommendation_rows.append(
            "Self-evaluation currently prefers precision-first packet construction; tighten anchors and trim redundant context before widening depth."
        )
    latest_packet_strategy = str(latest_packet.get("adaptive_packet_strategy", "")).strip()
    advised_packet_strategy = str(learning_advisories.get("packet_strategy", "")).strip()
    if latest_packet_strategy and advised_packet_strategy and latest_packet_strategy != advised_packet_strategy:
        recommendation_rows.append(
            "The latest retained packet strategy diverged from the current advisory posture; inspect packet anchors and freshness before trusting aggressive execution tuning."
        )
    latest_budget_mode = str(latest_packet.get("adaptive_budget_mode", "")).strip()
    advised_budget_mode = str(learning_advisories.get("budget_mode", "")).strip()
    latest_speed_mode = str(latest_packet.get("adaptive_speed_mode", "")).strip()
    advised_speed_mode = str(learning_advisories.get("speed_mode", "")).strip()
    latest_retrieval_focus = str(latest_packet.get("adaptive_retrieval_focus", "")).strip()
    advised_retrieval_focus = str(learning_advisories.get("retrieval_focus", "")).strip()
    if latest_budget_mode and advised_budget_mode and latest_budget_mode != advised_budget_mode:
        recommendation_rows.append(
            "The latest packet budget mode diverged from the measured advisory loop; verify that packet compaction is actually following the current budget posture."
        )
    if latest_speed_mode and advised_speed_mode and latest_speed_mode != advised_speed_mode:
        recommendation_rows.append(
            "The latest packet speed mode diverged from the measured advisory loop; prefer guarded depth and fan-out until packet shaping and control advice converge again."
        )
    if latest_retrieval_focus and advised_retrieval_focus and latest_retrieval_focus != advised_retrieval_focus:
        recommendation_rows.append(
            "The latest packet retrieval focus diverged from the measured advisory loop; inspect anchors and miss-recovery posture before widening coverage or precision repair."
        )
    if str(latest_packet.get("adaptive_reliability", "")).strip() == "guarded":
        recommendation_rows.append(
            "The latest packet was shaped under guarded advisory reliability; keep depth and fan-out conservative until fresher evidence accumulates."
        )
    if str(learning_advisories.get("yield_state", "")).strip() == "wasteful":
        recommendation_rows.append(
            "The measured advisory loop currently sees wasteful packet yield; bias toward tighter packets and narrower delegated slices until yield recovers."
        )
    overall_terms = [within_budget_rate, high_utility_rate, route_ready_rate]
    if learning_packet:
        overall_terms.append(float(learning_packet.get("benchmark_satisfaction_rate", 0.0) or 0.0))
    if learning_router:
        overall_terms.append(float(learning_router.get("acceptance_rate", 0.0) or 0.0))
    overall_rate = round(sum(overall_terms) / max(1, len(overall_terms)), 3) if sample_size or learning_summary else 0.0
    overall_level = _optimization_level_from_rate(overall_rate)
    structured_execution_profile = {
        key: value
        for key, value in {
            "profile": str(latest_packet.get("odylith_execution_profile", "")).strip(),
            "model": str(latest_packet.get("odylith_execution_model", "")).strip(),
            "reasoning_effort": str(latest_packet.get("odylith_execution_reasoning_effort", "")).strip(),
            "agent_role": str(latest_packet.get("odylith_execution_agent_role", "")).strip(),
            "selection_mode": str(latest_packet.get("odylith_execution_selection_mode", "")).strip(),
            "delegate_preference": str(latest_packet.get("odylith_execution_delegate_preference", "")).strip(),
            "source": str(latest_packet.get("odylith_execution_source", "")).strip()
            or ("optimization_snapshot_latest_packet" if latest_packet else ""),
            "confidence": {
                "score": int(latest_packet.get("odylith_execution_confidence_score", 0) or 0),
                "level": str(latest_packet.get("odylith_execution_confidence_level", "")).strip(),
            }
            if latest_packet
            else {},
            "constraints": {
                key: value
                for key, value in {
                    "route_ready": bool(latest_packet.get("odylith_execution_route_ready")),
                    "narrowing_required": bool(latest_packet.get("odylith_execution_narrowing_required")),
                    "spawn_worthiness": int(latest_packet.get("odylith_execution_spawn_worthiness", 0) or 0),
                    "merge_burden": int(latest_packet.get("odylith_execution_merge_burden", 0) or 0),
                    "reasoning_mode": str(latest_packet.get("odylith_execution_reasoning_mode", "")).strip(),
                }.items()
                if value not in ("", [], {}, None, 0)
            }
            if latest_packet
            else {},
        }.items()
        if value not in ("", [], {}, None)
    }
    payload = {
        "contract": "optimization_snapshot.v1",
        "version": "v1",
        "generated_utc": _utc_now(),
        "odylith_switch": odylith_switch,
        "sample_size": sample_size,
        "status": "active" if sample_size else "insufficient_history",
        "freshness_utc": str(latest_packet.get("bootstrapped_at", "")).strip(),
        "overall": {
            "score": round(overall_rate * 100.0, 1),
            "level": overall_level,
        },
        "execution_profile": structured_execution_profile,
        "packet_posture": {
            "avg_bytes": avg_bytes,
            "avg_tokens": avg_tokens,
            "within_budget_rate": within_budget_rate,
            "state_distribution": packet_state_distribution,
            "packet_strategy_distribution": packet_strategy_distribution,
            "budget_mode_distribution": budget_mode_distribution,
            "speed_mode_distribution": speed_mode_distribution,
            "selection_bias_distribution": selection_bias_distribution,
            "packet_reliability_distribution": packet_reliability_distribution,
            "avg_effective_yield_score": float(learning_packet.get("avg_effective_yield_score", 0.0) or 0.0),
            "high_yield_rate": float(learning_packet.get("high_yield_rate", 0.0) or 0.0),
            "reliable_high_yield_rate": float(learning_packet.get("reliable_high_yield_rate", 0.0) or 0.0),
            "yield_state": str(learning_packet.get("yield_state", "")).strip(),
            "advisory_alignment_rate": float(learning_packet.get("advisory_alignment_rate", 0.0) or 0.0),
            "advisory_alignment_coverage": int(learning_packet.get("advisory_alignment_coverage", 0) or 0),
            "reliable_advisory_alignment_rate": float(
                learning_packet.get("reliable_advisory_alignment_rate", 0.0) or 0.0
            ),
            "reliable_advisory_alignment_count": int(
                learning_packet.get("reliable_advisory_alignment_count", 0) or 0
            ),
            "packet_alignment_state": str(learning_packet.get("alignment_state", "")).strip(),
            "context_richness_distribution": richest_distribution,
        },
        "quality_posture": {
            "avg_utility_score": avg_utility_score,
            "avg_density_per_1k_tokens": avg_density,
            "avg_context_density_score": avg_context_density_score,
            "avg_context_density_per_1k_tokens": avg_context_density_per_1k,
            "avg_reasoning_readiness_score": avg_reasoning_readiness_score,
            "avg_evidence_diversity_score": avg_evidence_diversity_score,
            "high_utility_rate": high_utility_rate,
            "avg_effective_yield_score": float(learning_packet.get("avg_effective_yield_score", 0.0) or 0.0),
            "high_yield_rate": float(learning_packet.get("high_yield_rate", 0.0) or 0.0),
            "reliable_high_yield_rate": float(learning_packet.get("reliable_high_yield_rate", 0.0) or 0.0),
            "yield_state": str(learning_packet.get("yield_state", "")).strip(),
            "high_routing_confidence_rate": high_routing_confidence_rate,
            "route_ready_rate": route_ready_rate,
            "native_spawn_ready_rate": native_spawn_ready_rate,
            "narrowing_rate": narrowing_rate,
            "miss_recovery_rate": miss_recovery_rate,
            "miss_recovery_applied_rate": miss_recovery_applied_rate,
            "deep_reasoning_ready_rate": deep_reasoning_ready_rate,
            "context_density_distribution": context_density_distribution,
            "reasoning_readiness_distribution": reasoning_readiness_distribution,
            "reasoning_mode_distribution": reasoning_mode_distribution,
            "evidence_diversity_distribution": evidence_diversity_distribution,
        },
        "degraded_fallback_posture": {
            "repo_scan_degraded_fallback_rate": repo_scan_degraded_rate,
            "repo_scan_degraded_reason_distribution": repo_scan_degraded_reason_distribution,
            "hard_grounding_failure_rate": hard_grounding_failure_rate,
            "hard_grounding_failure_reason_distribution": hard_grounding_failure_reason_distribution,
            "soft_widening_rate": soft_widening_rate,
            "soft_widening_reason_distribution": soft_widening_reason_distribution,
            "visible_fallback_receipt_rate": visible_fallback_receipt_rate,
            "visible_fallback_receipt_reason_distribution": visible_fallback_receipt_reason_distribution,
        },
        "governance_runtime_first_posture": governance_runtime_first,
        "orchestration_posture": {
            "parallelism_hint_distribution": parallelism_distribution,
            "reasoning_bias_distribution": reasoning_distribution,
            "odylith_execution_profile_distribution": execution_profile_distribution,
            "odylith_execution_selection_mode_distribution": execution_selection_mode_distribution,
            "odylith_execution_reasoning_distribution": execution_reasoning_distribution,
            "odylith_execution_agent_role_distribution": execution_agent_role_distribution,
            "odylith_execution_delegate_preference_distribution": execution_delegate_preference_distribution,
            "odylith_execution_source_distribution": execution_source_distribution,
            "delegated_lane_rate": delegated_lane_rate,
            "hold_local_rate": hold_local_rate,
            "high_execution_confidence_rate": high_execution_confidence_rate,
            "runtime_backed_execution_rate": runtime_backed_execution_rate,
        },
        "control_advisories": learning_advisories,
        "evaluation_posture": {
            "packet_events": learning_packet,
            "router_outcomes": learning_router,
            "orchestration_feedback": learning_orchestration,
            "decision_quality": learning_decision_quality,
            "trend_posture": learning_trend,
            "control_posture": learning_control,
            "freshness": learning_freshness,
            "evidence_strength": learning_evidence_strength,
            "control_advisories": learning_advisories,
            "regressions": list(learning_summary.get("regressions", []))
            if isinstance(learning_summary.get("regressions"), list)
            else [],
        },
        "intent_posture": {
            "top_family": top_intent_family,
            "family_distribution": intent_family_distribution,
            "mode_distribution": intent_mode_distribution,
            "critical_path_distribution": intent_critical_path_distribution,
            "explicit_rate": intent_explicit_rate,
            "high_confidence_rate": high_intent_confidence_rate,
        },
        "latency_posture": latency_posture,
        "latest_packet": {
            "session_id": str(latest_packet.get("session_id", "")).strip(),
            "workstream": str(latest_packet.get("workstream", "")).strip(),
            "packet_state": str(latest_packet.get("packet_state", "")).strip(),
            "utility_level": str(latest_packet.get("utility_level", "")).strip(),
            "context_density_level": str(latest_packet.get("context_density_level", "")).strip(),
            "reasoning_readiness_level": str(latest_packet.get("reasoning_readiness_level", "")).strip(),
            "reasoning_readiness_mode": str(latest_packet.get("reasoning_readiness_mode", "")).strip(),
            "evidence_diversity_level": str(latest_packet.get("evidence_diversity_level", "")).strip(),
            "packet_strategy": str(latest_packet.get("adaptive_packet_strategy", "")).strip(),
            "budget_mode": str(latest_packet.get("adaptive_budget_mode", "")).strip(),
            "retrieval_focus": str(latest_packet.get("adaptive_retrieval_focus", "")).strip(),
            "speed_mode": str(latest_packet.get("adaptive_speed_mode", "")).strip(),
            "reliability": str(latest_packet.get("adaptive_reliability", "")).strip(),
            "selection_bias": str(latest_packet.get("adaptive_selection_bias", "")).strip(),
            "advised_packet_strategy": str(learning_advisories.get("packet_strategy", "")).strip(),
            "advised_budget_mode": str(learning_advisories.get("budget_mode", "")).strip(),
            "advised_retrieval_focus": str(learning_advisories.get("retrieval_focus", "")).strip(),
            "advised_speed_mode": str(learning_advisories.get("speed_mode", "")).strip(),
            "advised_yield_state": str(learning_advisories.get("yield_state", "")).strip(),
            "packet_alignment_state": str(learning_advisories.get("packet_alignment_state", "")).strip(),
            "packet_alignment_rate": float(learning_advisories.get("packet_alignment_rate", 0.0) or 0.0),
            "reliable_packet_alignment_rate": float(
                learning_advisories.get("reliable_packet_alignment_rate", 0.0) or 0.0
            ),
            "budget_scale": float(latest_packet.get("adaptive_budget_scale", 0.0) or 0.0),
            "adaptive_source": str(latest_packet.get("adaptive_source", "")).strip(),
            "intent_family": str(latest_packet.get("intent_family", "")).strip(),
            "intent_mode": str(latest_packet.get("intent_mode", "")).strip(),
            "routing_confidence": str(latest_packet.get("routing_confidence", "")).strip(),
            "odylith_execution_profile": str(latest_packet.get("odylith_execution_profile", "")).strip(),
            "odylith_execution_reasoning_effort": str(latest_packet.get("odylith_execution_reasoning_effort", "")).strip(),
            "odylith_execution_agent_role": str(latest_packet.get("odylith_execution_agent_role", "")).strip(),
            "odylith_execution_selection_mode": str(latest_packet.get("odylith_execution_selection_mode", "")).strip(),
            "odylith_execution_delegate_preference": str(latest_packet.get("odylith_execution_delegate_preference", "")).strip(),
            "odylith_execution_confidence_score": int(latest_packet.get("odylith_execution_confidence_score", 0) or 0),
            "odylith_execution_confidence_level": str(latest_packet.get("odylith_execution_confidence_level", "")).strip(),
            "odylith_execution_source": str(latest_packet.get("odylith_execution_source", "")).strip()
            or ("optimization_snapshot_latest_packet" if latest_packet else ""),
            "odylith_execution_route_ready": bool(latest_packet.get("odylith_execution_route_ready")),
            "odylith_execution_narrowing_required": bool(latest_packet.get("odylith_execution_narrowing_required")),
            "odylith_execution_spawn_worthiness": int(latest_packet.get("odylith_execution_spawn_worthiness", 0) or 0),
            "odylith_execution_merge_burden": int(latest_packet.get("odylith_execution_merge_burden", 0) or 0),
            "odylith_execution_reasoning_mode": str(latest_packet.get("odylith_execution_reasoning_mode", "")).strip(),
            "route_ready": bool(latest_packet.get("route_ready")),
            "native_spawn_ready": bool(latest_packet.get("native_spawn_ready")),
            "within_budget": bool(latest_packet.get("within_budget")),
            "miss_recovery_mode": str(latest_packet.get("miss_recovery_mode", "")).strip(),
            "execution_engine_present": bool(latest_packet.get("execution_engine_present")),
            "execution_engine_outcome": str(latest_packet.get("execution_engine_outcome", "")).strip(),
            "execution_engine_requires_reanchor": bool(
                latest_packet.get("execution_engine_requires_reanchor")
            ),
            "execution_engine_mode": str(latest_packet.get("execution_engine_mode", "")).strip(),
            "execution_engine_next_move": str(latest_packet.get("execution_engine_next_move", "")).strip(),
            "execution_engine_current_phase": str(
                latest_packet.get("execution_engine_current_phase", "")
            ).strip(),
            "execution_engine_last_successful_phase": str(
                latest_packet.get("execution_engine_last_successful_phase", "")
            ).strip(),
            "execution_engine_blocker": str(latest_packet.get("execution_engine_blocker", "")).strip(),
            "execution_engine_closure": str(latest_packet.get("execution_engine_closure", "")).strip(),
            "execution_engine_wait_status": str(
                latest_packet.get("execution_engine_wait_status", "")
            ).strip(),
            "execution_engine_wait_detail": str(
                latest_packet.get("execution_engine_wait_detail", "")
            ).strip(),
            "execution_engine_resume_token": str(
                latest_packet.get("execution_engine_resume_token", "")
            ).strip(),
            "execution_engine_validation_archetype": str(
                latest_packet.get("execution_engine_validation_archetype", "")
            ).strip(),
            "execution_engine_validation_minimum_pass_count": int(
                latest_packet.get("execution_engine_validation_minimum_pass_count", 0) or 0
            ),
            "execution_engine_contradiction_count": int(
                latest_packet.get("execution_engine_contradiction_count", 0) or 0
            ),
            "execution_engine_history_rule_count": int(
                latest_packet.get("execution_engine_history_rule_count", 0) or 0
            ),
            "execution_engine_authoritative_lane": str(
                latest_packet.get("execution_engine_authoritative_lane", "")
            ).strip(),
            "execution_engine_host_family": str(
                latest_packet.get("execution_engine_host_family", "")
            ).strip(),
            "execution_engine_model_family": str(
                latest_packet.get("execution_engine_model_family", "")
            ).strip(),
            "execution_engine_target_lane": str(
                latest_packet.get("execution_engine_target_lane", "")
            ).strip(),
            "execution_engine_candidate_target_count": int(
                latest_packet.get("execution_engine_candidate_target_count", 0) or 0
            ),
            "execution_engine_diagnostic_anchor_count": int(
                latest_packet.get("execution_engine_diagnostic_anchor_count", 0) or 0
            ),
            "execution_engine_has_writable_targets": bool(
                latest_packet.get("execution_engine_has_writable_targets")
            ),
            "execution_engine_requires_more_consumer_context": bool(
                latest_packet.get("execution_engine_requires_more_consumer_context")
            ),
            "execution_engine_consumer_failover": str(
                latest_packet.get("execution_engine_consumer_failover", "")
            ).strip(),
            "execution_engine_commentary_mode": str(
                latest_packet.get("execution_engine_commentary_mode", "")
            ).strip(),
            "execution_engine_suppress_routing_receipts": bool(
                latest_packet.get("execution_engine_suppress_routing_receipts")
            ),
            "execution_engine_surface_fast_lane": bool(
                latest_packet.get("execution_engine_surface_fast_lane")
            ),
            "turn_intent": str(latest_packet.get("turn_intent", "")).strip(),
            "turn_surface_count": int(latest_packet.get("turn_surface_count", 0) or 0),
            "turn_visible_text_count": int(latest_packet.get("turn_visible_text_count", 0) or 0),
            "turn_active_tab": str(latest_packet.get("turn_active_tab", "")).strip(),
            "turn_user_turn_id": str(latest_packet.get("turn_user_turn_id", "")).strip(),
            "turn_supersedes_turn_id": str(latest_packet.get("turn_supersedes_turn_id", "")).strip(),
            "estimated_tokens": int(latest_packet.get("estimated_tokens", 0) or 0),
        }
        if latest_packet
        else {},
        "learning_loop": {
            "event_count": int(learning_summary.get("event_count", 0) or 0),
            "state": str(learning_trend.get("learning_state", "")).strip(),
            "packet_trend": str(learning_trend.get("packet_trend", "")).strip(),
            "router_trend": str(learning_trend.get("router_trend", "")).strip(),
            "orchestration_trend": str(learning_trend.get("orchestration_trend", "")).strip(),
            "freshness": learning_freshness,
            "evidence_strength": learning_evidence_strength,
            "control_posture": learning_control,
            "control_advisories": learning_advisories,
        },
        "recommendations": recommendation_rows[:4],
    }
    _PROCESS_OPTIMIZATION_SNAPSHOT_CACHE[cache_key] = (
        cache_signature,
        now + _PROCESS_OPTIMIZATION_SNAPSHOT_CACHE_TTL_SECONDS,
        dict(payload),
    )
    return payload
