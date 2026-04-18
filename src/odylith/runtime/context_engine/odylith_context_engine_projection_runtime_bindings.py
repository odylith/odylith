"""Odylith Context Engine Projection Runtime Bindings helpers for the Odylith context engine layer."""

from __future__ import annotations

from typing import Any

_BIND_NAMES = ('Any', 'Mapping', 'Path', 'Sequence', '_BUG_CRITICAL_SEVERITIES', '_DIAGRAM_ID_RE', '_ENGINEERING_NOTE_KINDS', '_ENGINEERING_NOTE_KIND_SET', '_HEADER_RE', '_PROCESS_WARM_CACHE_FINGERPRINTS', '_WORKSTREAM_ID_RE', '_apply_odylith_component_index_ablation', '_apply_odylith_registry_snapshot_ablation', '_available_full_scan_roots', '_bug_agent_guidance', '_bug_archive_bucket_from_link_target', '_bug_intelligence_coverage', '_bug_is_open', '_bug_summary_from_fields', '_build_bug_reference_lookup', '_cached_projection_rows', '_classify_bug_path_refs', '_component_entry_from_runtime_row', '_component_lookup_aliases', '_component_matches_for_bug_paths', '_component_rows_from_index', '_connect', '_context_lookup_key', '_dedupe_strings', '_delivery_context_rows', '_diagram_refs_for_bug_components', '_entity_by_kind_id', '_entity_by_path', '_entity_from_row', '_extract_path_refs', '_extract_workstream_refs', '_full_scan_guidance', '_full_scan_terms', '_is_bug_placeholder_row', '_json_list', '_load_backlog_projection', '_load_bug_projection', '_load_diagram_projection', '_load_idea_specs', '_load_plan_projection', '_markdown_section_bodies', '_normalize_bug_link_target', '_normalize_entity_kind', '_normalize_repo_token', '_odylith_ablation_active', '_odylith_query_targets_disabled', '_odylith_runtime_entity_suppressed', '_odylith_switch_snapshot', '_ordered_bug_detail_sections', '_parse_bug_entry_fields', '_parse_component_tokens', '_parse_link_target', '_path_signal_profile', '_plan_lookup_aliases', '_raw_text', '_recent_context_events', '_related_bug_refs_from_text', '_related_entities', '_relation_rows', '_release_lookup_aliases', '_repo_scan_inferred_kind', '_resolve_context_entity', '_runtime_backlog_detail', '_runtime_backlog_detail_rows', '_search_row_from_entity', '_summarize_entity', '_unique_entity_by_path_alias', '_warm_runtime', '_workstream_lookup_aliases', 'canonicalize_bug_status', 'component_registry', 'entity', 'entity_id', 'entity_kind', 'json', 'load_backlog_detail', 'load_backlog_rows', 'load_bug_rows', 'load_component_index', 'load_component_registry_snapshot', 're', 'record_runtime_timing', 'search_entities_payload', 'summary', 'time')

def bind_projection_runtime(target_globals: dict[str, Any], host: Any) -> None:
    getter = host.__getitem__ if isinstance(host, dict) else lambda name: getattr(host, name)
    for name in _BIND_NAMES:
        try:
            target_globals[name] = getter(name)
        except (AttributeError, KeyError):
            continue
