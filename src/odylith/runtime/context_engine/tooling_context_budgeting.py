"""Deterministic packet budgeting for Odylith Context Engine context packets."""

from __future__ import annotations

import copy
import json
import math
from collections import Counter
from typing import Any, Mapping, Sequence

from pathlib import Path

from odylith.runtime.common.consumer_profile import (
    PUBLIC_PRODUCT_RUNBOOK_PATHS,
    canonical_truth_token,
    is_component_forensics_path,
    is_component_spec_path,
    is_runbook_path,
)

ESTIMATED_BYTES_PER_TOKEN = 4
SECTION_SUMMARY_LIMIT = 8
TRIM_STEP_RECORD_LIMIT = 8
DEFAULT_PACKET_BUDGETS: dict[str, dict[str, int]] = {
    "impact": {"max_bytes": 40_000, "max_tokens": 10_000},
    "governance_slice": {"max_bytes": 28_000, "max_tokens": 7_000},
    "session_brief": {"max_bytes": 30_000, "max_tokens": 7_500},
    "bootstrap_session": {"max_bytes": 24_000, "max_tokens": 6_000},
}
DEFAULT_PACKET_META_RESERVE_BYTES: dict[str, int] = {
    "impact": 2_400,
    "governance_slice": 2_200,
    "session_brief": 2_000,
    "bootstrap_session": 2_200,
}
_STATE_BYTE_MULTIPLIERS = {
    "gated_broad_scope": 0.70,
    "gated_ambiguous": 0.80,
    "compact": 1.0,
    "expanded": 1.15,
}
_MATCH_TIER_PRIORITY = {
    "direct_path": 180,
    "anchored_context": 135,
    "canonical_source": 80,
    "note_match": 72,
    "task_family": 48,
}
DEFAULT_TRIM_ORDERS: dict[str, list[tuple[str, ...]]] = {
    "impact": [
        ("candidate_workstreams",),
        ("engineering_notes",),
        ("docs",),
        ("guidance_brief",),
        ("retrieval_plan", "selected_guidance_chunks"),
        ("working_memory_tiers", "warm", "guidance_chunks"),
        ("recommended_commands",),
        ("recommended_tests",),
        ("diagrams",),
        ("components",),
        ("bugs",),
        ("code_neighbors",),
        ("architecture_audit",),
    ],
    "governance_slice": [
        ("governance_obligations", "closeout_docs"),
        ("docs",),
        ("candidate_workstreams",),
        ("components",),
        ("diagrams",),
        ("governance_obligations", "required_diagrams"),
        ("governance_obligations", "linked_bugs"),
        ("surface_refs", "reasons"),
        ("validation_bundle", "recommended_commands"),
        ("validation_bundle", "strict_gate_commands"),
        ("architecture_audit",),
    ],
    "session_brief": [
        ("active_conflicts",),
        ("candidate_workstreams",),
        ("guidance_brief",),
        ("retrieval_plan", "selected_guidance_chunks"),
        ("working_memory_tiers", "warm", "guidance_chunks"),
        ("impact", "candidate_workstreams"),
        ("impact", "guidance_brief"),
        ("impact", "engineering_notes"),
        ("impact", "docs"),
        ("impact", "recommended_commands"),
        ("impact", "recommended_tests"),
        ("workstream_context",),
    ],
    "bootstrap_session": [
        ("candidate_workstreams",),
        ("guidance_brief",),
        ("retrieval_plan", "selected_guidance_chunks"),
        ("working_memory_tiers", "warm", "guidance_chunks"),
        ("relevant_docs",),
        ("recommended_commands",),
        ("recommended_tests",),
        ("top_engineering_notes",),
        ("workstream_context",),
        ("retrieval_plan", "selected_docs"),
        ("retrieval_plan", "selected_tests"),
        ("retrieval_plan", "selected_commands"),
        ("working_memory_tiers", "warm", "docs"),
        ("impact_summary", "guidance_brief"),
        ("impact_summary", "workstreams"),
        ("impact_summary", "diagrams"),
        ("impact_summary", "components"),
        ("active_conflicts",),
        ("runtime", "timings", "operations"),
        ("runtime", "timings", "recent"),
    ],
}
DEFAULT_MIN_ITEMS: dict[tuple[str, ...], int] = {
    ("active_conflicts",): 1,
    ("candidate_workstreams",): 2,
    ("bugs",): 1,
    ("code_neighbors",): 1,
    ("components",): 1,
    ("diagrams",): 1,
    ("docs",): 2,
    ("guidance_brief",): 1,
    ("recommended_commands",): 1,
    ("validation_bundle", "recommended_commands"): 1,
    ("validation_bundle", "strict_gate_commands"): 1,
    ("recommended_tests",): 1,
    ("engineering_notes",): 1,
    ("retrieval_plan", "selected_guidance_chunks"): 1,
    ("working_memory_tiers", "warm", "guidance_chunks"): 1,
    ("impact", "candidate_workstreams"): 2,
    ("impact", "guidance_brief"): 1,
    ("impact", "docs"): 1,
    ("impact", "recommended_commands"): 1,
    ("impact", "recommended_tests"): 1,
    ("impact", "engineering_notes"): 1,
    ("relevant_docs",): 2,
    ("top_engineering_notes",): 1,
    ("impact_summary", "guidance_brief"): 1,
    ("impact_summary", "workstreams"): 1,
    ("runtime", "timings", "operations"): 1,
    ("runtime", "timings", "recent"): 1,
}
DEFAULT_PACKET_MIN_ITEMS: dict[str, dict[tuple[str, ...], int]] = {
    "impact": {
        ("recommended_commands",): 3,
    },
    "governance_slice": {
        ("validation_bundle", "strict_gate_commands"): 2,
        ("governance_obligations", "closeout_docs"): 2,
    },
}


def packet_budget(*, packet_kind: str, packet_state: str) -> dict[str, Any]:
    """Return the effective packet budget for one kind/state pair."""

    base = dict(DEFAULT_PACKET_BUDGETS.get(str(packet_kind or "").strip(), DEFAULT_PACKET_BUDGETS["impact"]))
    multiplier = float(_STATE_BYTE_MULTIPLIERS.get(str(packet_state or "").strip(), 1.0))
    max_bytes = max(2_000, int(base["max_bytes"] * multiplier))
    meta_reserve_bytes = int(
        DEFAULT_PACKET_META_RESERVE_BYTES.get(str(packet_kind or "").strip(), DEFAULT_PACKET_META_RESERVE_BYTES["impact"])
    )
    meta_reserve_tokens = max(150, int(math.ceil(meta_reserve_bytes / ESTIMATED_BYTES_PER_TOKEN)))
    return {
        "packet_kind": str(packet_kind or "").strip(),
        "packet_state": str(packet_state or "").strip(),
        "max_bytes": max_bytes,
        "max_tokens": max(500, int(base["max_tokens"] * multiplier)),
        "meta_reserve_bytes": meta_reserve_bytes,
        "meta_reserve_tokens": meta_reserve_tokens,
        "content_max_bytes": max(1_000, max_bytes - meta_reserve_bytes),
        "content_max_tokens": max(250, int(base["max_tokens"] * multiplier) - meta_reserve_tokens),
        "trim_order": [".".join(path) for path in DEFAULT_TRIM_ORDERS.get(str(packet_kind or "").strip(), [])],
    }


def _json_size_bytes(value: Any) -> int:
    try:
        rendered = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except TypeError:
        rendered = json.dumps(str(value), ensure_ascii=False)
    return len(rendered.encode("utf-8"))


def _section_summary_limit_for_packet(
    *,
    packet_kind: str,
    packet_state: str,
    section_summary_limit: int | None,
) -> int:
    if section_summary_limit is not None:
        return max(1, int(section_summary_limit))
    kind = str(packet_kind or "").strip()
    state = str(packet_state or "").strip()
    if kind == "bootstrap_session":
        if state == "compact" or state.startswith("gated_"):
            return min(SECTION_SUMMARY_LIMIT, 4)
        return min(SECTION_SUMMARY_LIMIT, 6)
    return SECTION_SUMMARY_LIMIT


def estimate_packet_metrics(
    payload: Mapping[str, Any],
    *,
    packet_kind: str,
    packet_state: str,
    budget: Mapping[str, Any] | None = None,
    exclude_sections: Sequence[str] = ("packet_metrics",),
    section_summary_limit: int | None = None,
) -> dict[str, Any]:
    """Estimate serialized size and top-level section sizes for one payload."""

    budget_payload = dict(budget) if isinstance(budget, Mapping) else packet_budget(packet_kind=packet_kind, packet_state=packet_state)
    estimated_bytes = _json_size_bytes(payload)
    estimated_tokens = int(math.ceil(estimated_bytes / ESTIMATED_BYTES_PER_TOKEN))
    largest_limit = _section_summary_limit_for_packet(
        packet_kind=packet_kind,
        packet_state=packet_state,
        section_summary_limit=section_summary_limit,
    )
    section_rows: list[dict[str, Any]] = []
    excluded = {str(token).strip() for token in exclude_sections if str(token).strip()}
    for key, value in payload.items():
        section_name = str(key)
        if section_name in excluded:
            continue
        section_rows.append(
            {
                "section": section_name,
                "estimated_bytes": _json_size_bytes(value),
                "item_count": _item_count(value),
            }
        )
    section_rows.sort(key=lambda row: (-int(row["estimated_bytes"]), str(row["section"])))
    return {
        "packet_kind": str(packet_kind or "").strip(),
        "packet_state": str(packet_state or "").strip(),
        "estimated_bytes": estimated_bytes,
        "estimated_tokens": estimated_tokens,
        "budget_bytes": int(budget_payload.get("max_bytes", 0) or 0),
        "budget_tokens": int(budget_payload.get("max_tokens", 0) or 0),
        "within_budget": estimated_bytes <= int(budget_payload.get("max_bytes", 0) or 0)
        and estimated_tokens <= int(budget_payload.get("max_tokens", 0) or 0),
        "sections": {
            "total": len(section_rows),
            "largest": section_rows[:largest_limit],
        },
    }


def _item_count(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, Mapping):
        return sum(_item_count(item) for item in value.values())
    return 1 if value not in (None, "", [], {}) else 0


def _normalize_trim_order_paths(value: Any) -> list[tuple[str, ...]]:
    if not isinstance(value, list):
        return []
    rows: list[tuple[str, ...]] = []
    seen: set[tuple[str, ...]] = set()
    for item in value:
        if isinstance(item, str):
            path = tuple(segment.strip() for segment in item.split(".") if segment.strip())
        elif isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)):
            path = tuple(str(segment or "").strip() for segment in item if str(segment or "").strip())
        else:
            path = ()
        if not path or path in seen:
            continue
        seen.add(path)
        rows.append(path)
    return rows


def _get_path(payload: Mapping[str, Any], path: Sequence[str]) -> Any:
    current: Any = payload
    for segment in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(segment)
    return current


def _set_path(payload: dict[str, Any], path: Sequence[str], value: Any) -> None:
    current: dict[str, Any] = payload
    for segment in path[:-1]:
        child = current.get(segment)
        if not isinstance(child, dict):
            child = {}
            current[segment] = child
        current = child
    current[path[-1]] = value


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    rows: list[str] = []
    seen: set[str] = set()
    for item in value:
        token = str(item or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _mapping_value(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _history_value(item: Mapping[str, Any]) -> dict[str, Any]:
    history = _mapping_value(item.get("history"))
    if history:
        return history
    metadata = _mapping_value(item.get("metadata"))
    nested = _mapping_value(metadata.get("history"))
    return nested


def _evidence_match_lists(item: Mapping[str, Any]) -> tuple[list[str], list[str], list[str], list[str], list[str]]:
    evidence = _mapping_value(item.get("evidence"))
    relevance = _mapping_value(item.get("relevance"))
    evidence_summary = _mapping_value(item.get("evidence_summary"))
    matched_by = (
        _string_list(item.get("matched_by"))
        or _string_list(relevance.get("matched_by"))
        or _string_list(evidence_summary.get("matched_by"))
    )
    matched_paths = (
        _string_list(item.get("matched_paths"))
        or _string_list(relevance.get("matched_paths"))
        or _string_list(evidence_summary.get("matched_paths"))
        or _string_list(evidence.get("matched_paths"))
    )
    matched_components = (
        _string_list(item.get("matched_components"))
        or _string_list(relevance.get("matched_components"))
        or _string_list(evidence_summary.get("matched_components"))
    )
    matched_workstreams = (
        _string_list(item.get("matched_workstreams"))
        or _string_list(relevance.get("matched_workstreams"))
        or _string_list(evidence_summary.get("matched_workstreams"))
    )
    matched_task_families = (
        _string_list(item.get("matched_task_families"))
        or _string_list(relevance.get("matched_task_families"))
        or _string_list(evidence_summary.get("matched_task_families"))
    )
    return matched_by, matched_paths, matched_components, matched_workstreams, matched_task_families


def _item_diversity_key(item: Mapping[str, Any]) -> str:
    actionability = _mapping_value(item.get("actionability"))
    for token in (
        str(item.get("chunk_id", "")).strip(),
        str(item.get("entity_id", "")).strip(),
        str(item.get("nodeid", "")).strip(),
        str(item.get("path", "")).strip(),
        str(actionability.get("read_path", "")).strip(),
        str(item.get("canonical_source", "")).strip(),
        str(item.get("chunk_path", "")).strip(),
        str(item.get("diagram_id", "")).strip(),
        str(item.get("title", "")).strip(),
    ):
        if token:
            return token
    matched_by, matched_paths, matched_components, matched_workstreams, _matched_task_families = _evidence_match_lists(item)
    for token in [*matched_paths, *matched_components, *matched_workstreams, *matched_by]:
        if token:
            return token
    return ""


def _preserve_anchor_item(item: Mapping[str, Any]) -> bool:
    evidence = _mapping_value(item.get("evidence"))
    relevance = _mapping_value(item.get("relevance"))
    evidence_summary = _mapping_value(item.get("evidence_summary"))
    actionability = _mapping_value(item.get("actionability"))
    match_tier = ""
    for candidate in (
        item.get("match_tier"),
        relevance.get("match_tier"),
        evidence_summary.get("match_tier"),
    ):
        token = str(candidate or "").strip()
        if token:
            match_tier = token
            break
    return (
        match_tier in {"direct_path", "anchored_context"}
        or bool(actionability.get("direct"))
        or (bool(actionability.get("actionable")) and bool(actionability.get("read_path")))
        or bool(evidence.get("strong_signal_count"))
        or bool(item.get("nodeid"))
    )


def _item_signal_surface_count(item: Mapping[str, Any]) -> int:
    actionability = _mapping_value(item.get("actionability"))
    matched_by, matched_paths, matched_components, matched_workstreams, matched_task_families = _evidence_match_lists(item)
    return (
        min(len(matched_by), 4)
        + min(len(matched_paths), 2)
        + min(len(matched_components), 2)
        + min(len(matched_workstreams), 2)
        + min(len(matched_task_families), 2)
        + min(len(_string_list(actionability.get("signals"))), 3)
        + (1 if str(actionability.get("read_path", "")).strip() else 0)
        + (1 if str(item.get("risk_class", "")).strip() else 0)
    )


def _mapping_priority_score(item: Mapping[str, Any]) -> int:
    score = 0
    evidence = _mapping_value(item.get("evidence"))
    relevance = _mapping_value(item.get("relevance"))
    evidence_summary = _mapping_value(item.get("evidence_summary"))
    actionability = _mapping_value(item.get("actionability"))
    history = _history_value(item)
    path_token = canonical_truth_token(str(item.get("path", "")).strip(), repo_root=Path.cwd())
    score += max(
        _int_value(item.get("score")),
        _int_value(relevance.get("score")),
        _int_value(evidence.get("score")),
        _int_value(evidence_summary.get("score")),
    )
    score += max(
        _int_value(evidence.get("strong_signal_count")),
        _int_value(item.get("strong_signal_count")),
    ) * 60
    match_tier = ""
    for candidate in (
        item.get("match_tier"),
        dict(relevance).get("match_tier") if isinstance(relevance, Mapping) else "",
        dict(evidence_summary).get("match_tier") if isinstance(evidence_summary, Mapping) else "",
    ):
        token = str(candidate or "").strip()
        if token:
            match_tier = token
            break
    score += _MATCH_TIER_PRIORITY.get(match_tier, 0)
    matched_by, matched_paths, matched_components, matched_workstreams, matched_task_families = _evidence_match_lists(item)
    score += 22 if "path" in matched_by else 0
    score += 14 if "workstream" in matched_by else 0
    score += 12 if "component" in matched_by else 0
    score += 8 if "task_family" in matched_by else 0
    score += min(len(matched_paths), 2) * 18
    score += min(len(matched_components), 2) * 10
    score += min(len(matched_workstreams), 2) * 12
    score += min(len(matched_task_families), 2) * 6
    if str(item.get("risk_class", "")).strip():
        score += 10
    if bool(actionability.get("actionable")):
        score += 48
    if bool(actionability.get("direct")):
        score += 32
    if str(actionability.get("read_path", "")).strip():
        score += 26
    score += min(len(_string_list(actionability.get("signals"))), 4) * 10
    score += min(_item_signal_surface_count(item), 8) * 11
    if str(item.get("reason", "")).strip():
        score += 34
    if str(item.get("nodeid", "")).strip():
        score += 20
    if str(item.get("test_path", "")).strip():
        score += 12
    if bool(history.get("recent_failure")):
        score += 340
    failure_count = _int_value(history.get("failure_count"))
    if failure_count > 0:
        score += min(160, failure_count * 52)
    if str(history.get("last_failure_utc", "")).strip():
        score += 28
    if isinstance(history.get("sources"), list):
        score += min(36, len([str(token).strip() for token in history.get("sources", []) if str(token).strip()]) * 12)
    if str(item.get("canonical_source", "")).strip():
        score += 18
    if is_component_spec_path(path_token, repo_root=Path.cwd()) or is_component_forensics_path(
        path_token,
        repo_root=Path.cwd(),
    ):
        score += 180
    elif is_runbook_path(path_token, repo_root=Path.cwd()) or path_token in PUBLIC_PRODUCT_RUNBOOK_PATHS:
        score += 164
    elif path_token == "Makefile" or path_token.startswith("mk/"):
        score += 152
    if str(item.get("chunk_path", "")).strip():
        score += 15
    if path_token:
        score += 15
    if _preserve_anchor_item(item):
        score += 18
    base_score = score
    item_bytes = _json_size_bytes(item)
    density_score = int(round((float(base_score) * 256.0) / float(max(1, item_bytes))))
    if density_score >= 140:
        score += 40
    elif density_score >= 95:
        score += 28
    elif density_score >= 60:
        score += 16
    elif density_score >= 35:
        score += 8
    if item_bytes >= 1800 and density_score < 55:
        score -= 32
    elif item_bytes >= 1100 and density_score < 40:
        score -= 18
    if bool(evidence.get("broad_only")) or bool(item.get("broad_only")):
        score -= 140
    return score


def _item_identifier(value: Any) -> str:
    if isinstance(value, Mapping):
        for field in ("chunk_id", "entity_id", "path", "diagram_id", "title", "nodeid"):
            token = str(value.get(field, "")).strip()
            if token:
                return token
    return ""


def _trim_list_once(values: Sequence[Any], *, min_items: int) -> tuple[list[Any], bool, str]:
    if len(values) <= min_items:
        return list(values), False, ""
    updated = list(values)
    remove_index = len(updated) - 1
    if any(isinstance(item, Mapping) for item in updated):
        diversity_counts = Counter(
            key
            for key in (_item_diversity_key(item) for item in updated if isinstance(item, Mapping))
            if key
        )
        protected_anchor_counts = Counter(
            key
            for item in updated
            if isinstance(item, Mapping) and _preserve_anchor_item(item)
            for key in [_item_diversity_key(item)]
            if key
        )
        ranked: list[tuple[int, int, int]] = []
        for index, item in enumerate(updated):
            priority = _mapping_priority_score(item) if isinstance(item, Mapping) else -1
            item_bytes = _json_size_bytes(item) if isinstance(item, Mapping) else 0
            if isinstance(item, Mapping):
                diversity_key = _item_diversity_key(item)
                if diversity_key:
                    if diversity_counts.get(diversity_key, 0) <= 1:
                        priority += 44
                    else:
                        priority -= min(42, (diversity_counts[diversity_key] - 1) * 18)
                    if _preserve_anchor_item(item):
                        if protected_anchor_counts.get(diversity_key, 0) <= 1:
                            priority += 56
                        else:
                            priority += 18
                if item_bytes >= 900 and priority < 260:
                    priority -= min(24, int(item_bytes / 256))
            ranked.append((priority, item_bytes, index))
        ranked.sort(key=lambda row: (row[0], -row[1], -row[2]))
        remove_index = ranked[0][2]
    removed = updated.pop(remove_index)
    return updated, True, _item_identifier(removed)


def _trim_value_once(value: Any, *, min_items: int) -> tuple[Any, bool, str]:
    if isinstance(value, list):
        return _trim_list_once(value, min_items=min_items)
    if isinstance(value, dict):
        updated = copy.deepcopy(value)
        keys = sorted(updated.keys(), key=lambda key: (-_json_size_bytes(updated.get(key)), str(key)))
        for key in keys:
            child, changed, removed = _trim_value_once(updated.get(key), min_items=min_items)
            if changed:
                updated[key] = child
                return updated, True, removed
        return updated, False, ""
    return value, False, ""


def apply_packet_budget(
    payload: Mapping[str, Any],
    *,
    packet_kind: str,
    packet_state: str,
    budget_override: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Trim a payload deterministically until it fits the configured budget."""

    budget = dict(budget_override) if isinstance(budget_override, Mapping) else packet_budget(packet_kind=packet_kind, packet_state=packet_state)
    trimmed = copy.deepcopy(dict(payload))
    initial_metrics = estimate_packet_metrics(trimmed, packet_kind=packet_kind, packet_state=packet_state, budget=budget)
    metrics = dict(initial_metrics)
    steps: list[dict[str, Any]] = []
    trim_paths = _normalize_trim_order_paths(budget.get("trim_order_paths")) or DEFAULT_TRIM_ORDERS.get(
        str(packet_kind or "").strip(),
        [],
    )
    packet_min_items = DEFAULT_PACKET_MIN_ITEMS.get(str(packet_kind or "").strip(), {})
    for path in trim_paths:
        if bool(metrics.get("within_budget")):
            break
        min_items = int(packet_min_items.get(tuple(path), DEFAULT_MIN_ITEMS.get(tuple(path), 0)))
        while not bool(metrics.get("within_budget")):
            current_value = _get_path(trimmed, path)
            before_count = _item_count(current_value)
            updated_value, changed, removed = _trim_value_once(current_value, min_items=min_items)
            if not changed:
                break
            _set_path(trimmed, path, updated_value)
            after_count = _item_count(updated_value)
            step = {
                "section": ".".join(path),
                "before_count": before_count,
                "after_count": after_count,
            }
            if removed:
                step["removed"] = removed
            steps.append(step)
            metrics = estimate_packet_metrics(trimmed, packet_kind=packet_kind, packet_state=packet_state, budget=budget)
            if len(steps) >= 64:
                break
    trim_meta = {
        "applied": bool(steps),
        "truncated": bool(steps),
        "initial_bytes": int(initial_metrics.get("estimated_bytes", 0) or 0),
        "final_bytes": int(metrics.get("estimated_bytes", 0) or 0),
        "initial_tokens": int(initial_metrics.get("estimated_tokens", 0) or 0),
        "final_tokens": int(metrics.get("estimated_tokens", 0) or 0),
        "within_budget_after_trim": bool(metrics.get("within_budget")),
        "step_count": len(steps),
        "steps": steps[:TRIM_STEP_RECORD_LIMIT],
    }
    return trimmed, budget, metrics, trim_meta


__all__ = [
    "DEFAULT_PACKET_BUDGETS",
    "DEFAULT_PACKET_META_RESERVE_BYTES",
    "DEFAULT_TRIM_ORDERS",
    "ESTIMATED_BYTES_PER_TOKEN",
    "SECTION_SUMMARY_LIMIT",
    "TRIM_STEP_RECORD_LIMIT",
    "apply_packet_budget",
    "estimate_packet_metrics",
    "packet_budget",
]
