"""Neutral memory contract helpers for Odylith Context Engine packets."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.common.consumer_profile import canonical_truth_token
from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.character import runtime as character_runtime
from odylith.runtime.governance import guidance_behavior_runtime


_ALLOWLIST_SOURCE_PREFIXES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("backlog_markdown", ("odylith/radar/source/",)),
    ("plan_markdown", ("odylith/technical-plans/",)),
    ("bug_markdown", ("odylith/casebook/bugs/",)),
    ("component_registry", ("odylith/registry/source/component_registry.v1.json",)),
    ("component_spec", ("odylith/registry/source/components/",)),
    ("runtime_contract", ("odylith/runtime/contracts/",)),
    ("mermaid_catalog", ("odylith/atlas/source/",)),
    ("delivery_intelligence_artifacts", ("odylith/runtime/",)),
    ("engineering_guidance", ("agents-guidelines/", "docs/runbooks/", "odylith/",)),
    ("python_source", ("src/odylith/", "app/", "services/")),
    ("pytest_source", ("tests/",)),
)
_SENSITIVE_PATH_TOKENS: tuple[str, ...] = (
    "/.env",
    "credentials",
    "credential",
    "secret",
    "token",
    "password",
    "passwd",
    "private_key",
    "private-key",
    "api_key",
    "api-key",
    "bearer",
    "dsn",
    ".pem",
    ".p12",
    ".pfx",
    ".key",
)
_EXECUTION_PROFILE_FIELDS: tuple[str, ...] = (
    "profile",
    "agent_role",
    "selection_mode",
    "delegate_preference",
)


def _mapping_rows(value: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in value] if isinstance(value, list) else []


def _string_rows(value: Any) -> list[str]:
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


def execution_profile_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        profile = dict(value)
        canonical_profile = agent_runtime_contract.canonical_execution_profile(profile.get("profile"))
        if canonical_profile:
            profile["profile"] = canonical_profile
        return profile
    token = str(value or "").strip()
    if not token:
        return {}
    parts = [part.strip() for part in token.split("|")]
    profile = {
        key: part
        for key, part in zip(_EXECUTION_PROFILE_FIELDS, parts, strict=False)
        if part
    }
    canonical_profile = agent_runtime_contract.canonical_execution_profile(profile.get("profile"))
    if canonical_profile:
        profile["profile"] = canonical_profile
    return profile


def compact_execution_profile_mapping(value: Any) -> dict[str, Any]:
    profile = execution_profile_mapping(value)
    return {
        key: token
        for key in _EXECUTION_PROFILE_FIELDS
        if (token := str(profile.get(key, "")).strip())
    }


def encode_execution_profile_token(value: Any) -> str:
    compact = compact_execution_profile_mapping(value)
    if not compact:
        return ""
    ordered = [str(compact.get(key, "")).strip() for key in _EXECUTION_PROFILE_FIELDS]
    while ordered and not ordered[-1]:
        ordered.pop()
    return "|".join(ordered)


def _nested_mapping(payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    return _mapping_value(payload.get(key))


def _nested_rows(payload: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key)
    return _mapping_rows(value)


def _normalize_repo_path(value: Any) -> str:
    return canonical_truth_token(str(value or "").strip().replace("\\", "/"), repo_root=Path.cwd())


def _source_class_for_path(path: Any) -> str:
    token = _normalize_repo_path(path)
    if not token:
        return ""
    for source_class, prefixes in _ALLOWLIST_SOURCE_PREFIXES:
        if any(token == prefix or token.startswith(prefix) for prefix in prefixes):
            return source_class
    return "other"


def _path_is_sensitive(path: Any) -> bool:
    token = "/" + _normalize_repo_path(path).lower().strip("/")
    if not token or token == "/":
        return False
    return any(marker in token for marker in _SENSITIVE_PATH_TOKENS)


def _sanitize_contract_path(path: Any) -> str:
    token = _normalize_repo_path(path)
    source_class = _source_class_for_path(token)
    if not token or source_class == "other" or _path_is_sensitive(token):
        return ""
    return token


def _source_count_rows(paths: Sequence[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for raw_path in paths:
        token = _normalize_repo_path(raw_path)
        if not token:
            continue
        source_class = _source_class_for_path(token) or "other"
        counts[source_class] = counts.get(source_class, 0) + 1
    return {key: counts[key] for key in sorted(counts)}


def _sanitize_contract_docs(rows: Sequence[str], *, limit: int) -> tuple[list[str], dict[str, int]]:
    sanitized: list[str] = []
    seen: set[str] = set()
    counts = {
        "retained_count": 0,
        "redacted_sensitive_count": 0,
        "dropped_non_allowlisted_count": 0,
    }
    for raw_row in rows:
        token = _normalize_repo_path(raw_row)
        if not token or token in seen:
            continue
        seen.add(token)
        if _path_is_sensitive(token):
            counts["redacted_sensitive_count"] += 1
            continue
        safe_path = _sanitize_contract_path(token)
        if not safe_path:
            counts["dropped_non_allowlisted_count"] += 1
            continue
        sanitized.append(safe_path)
        counts["retained_count"] += 1
        if len(sanitized) >= max(1, int(limit)):
            break
    return sanitized, counts


def _guidance_source_path(row: Mapping[str, Any]) -> str:
    actionability = _mapping_value(row.get("actionability"))
    return (
        _normalize_repo_path(actionability.get("read_path"))
        or _normalize_repo_path(row.get("canonical_source"))
        or _normalize_repo_path(row.get("chunk_path"))
    )


def _compact_guidance_source_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    limit: int,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    compacted: list[dict[str, Any]] = []
    counts = {
        "retained_count": 0,
        "redacted_sensitive_count": 0,
        "dropped_non_allowlisted_count": 0,
    }
    for row in rows[: max(1, int(limit))]:
        if not isinstance(row, Mapping):
            continue
        source_path = _guidance_source_path(row)
        source_class = _source_class_for_path(source_path)
        if source_path and _path_is_sensitive(source_path):
            counts["redacted_sensitive_count"] += 1
            safe_path = ""
            source_class = source_class or "other"
        else:
            safe_path = _sanitize_contract_path(source_path)
            if source_path and not safe_path:
                counts["dropped_non_allowlisted_count"] += 1
        actionability = _mapping_value(row.get("actionability"))
        evidence_summary = _mapping_value(row.get("evidence_summary"))
        compact = {
            "chunk_id": str(row.get("chunk_id", "")).strip(),
            "title": str(row.get("title", "")).strip(),
            "read_path": safe_path,
            "source_class": source_class if safe_path else "",
            "match_tier": str(row.get("match_tier", "")).strip(),
            "actionable": bool(actionability.get("actionable")),
            "direct": bool(actionability.get("direct")),
            "score": int(evidence_summary.get("score", 0) or 0),
        }
        compact = {key: value for key, value in compact.items() if value not in ("", [], {}, None, False)}
        if compact:
            compacted.append(compact)
            counts["retained_count"] += 1
    return compacted, counts


def _compact_contract_policy(*, summary_only: bool = False) -> dict[str, Any]:
    if summary_only:
        return {
            "secret_redaction_required": True,
            "provenance_required": True,
            "repo_truth_read_only": True,
        }
    return {
        "allowlisted_source_classes": [source_class for source_class, _prefixes in _ALLOWLIST_SOURCE_PREFIXES],
        "secret_redaction_required": True,
        "provenance_required": True,
        "repo_truth_read_only": True,
    }


def _compact_contract_optimization(
    *,
    packet_metrics: Mapping[str, Any],
    packet_quality: Mapping[str, Any],
    retrieval_plan: Mapping[str, Any],
    adaptive_packet_profile: Mapping[str, Any] | None = None,
    summary_only: bool = False,
) -> dict[str, Any]:
    utility_profile = _mapping_value(packet_quality.get("utility_profile"))
    token_efficiency = _mapping_value(utility_profile.get("token_efficiency"))
    compaction_pressure = _mapping_value(packet_quality.get("compaction_pressure"))
    context_density = _mapping_value(packet_quality.get("context_density"))
    evidence_diversity = _mapping_value(packet_quality.get("evidence_diversity"))
    reasoning_readiness = _mapping_value(packet_quality.get("reasoning_readiness"))
    miss_recovery = _mapping_value(retrieval_plan.get("miss_recovery"))
    adaptive = dict(adaptive_packet_profile) if isinstance(adaptive_packet_profile, Mapping) else {}
    compacted = {
        key: value
        for key, value in {
            "within_budget": bool(packet_metrics.get("within_budget")),
            "estimated_tokens": int(packet_metrics.get("estimated_tokens", 0) or 0),
            "utility_score": int(utility_profile.get("score", 0) or 0),
            "utility_level": str(utility_profile.get("level", "")).strip(),
            "token_efficiency_score": int(token_efficiency.get("score", 0) or 0),
            "token_efficiency_level": str(token_efficiency.get("level", "")).strip(),
            "compaction_pressure": {
                "score": int(compaction_pressure.get("score", 0) or 0),
                "level": str(compaction_pressure.get("level", "")).strip(),
            }
            if compaction_pressure
            else {},
            "context_density": {
                "score": int(context_density.get("score", 0) or 0),
                "level": str(context_density.get("level", "")).strip(),
            }
            if context_density
            else {},
            "evidence_diversity": {
                "score": int(evidence_diversity.get("score", 0) or 0),
                "level": str(evidence_diversity.get("level", "")).strip(),
                "domain_count": int(evidence_diversity.get("domain_count", 0) or 0),
            }
            if evidence_diversity
            else {},
            "reasoning_readiness": {
                "score": int(reasoning_readiness.get("score", 0) or 0),
                "level": str(reasoning_readiness.get("level", "")).strip(),
                "mode": str(reasoning_readiness.get("mode", "")).strip(),
                "deep_reasoning_ready": bool(reasoning_readiness.get("deep_reasoning_ready")),
            }
            if reasoning_readiness
            else {},
            "miss_recovery": {
                "active": bool(miss_recovery.get("active")),
                "applied": bool(miss_recovery.get("applied")),
                "mode": str(miss_recovery.get("mode", "")).strip(),
            }
            if miss_recovery
            else {},
            "packet_strategy": str(adaptive.get("packet_strategy", "")).strip(),
            "budget_mode": str(adaptive.get("budget_mode", "")).strip(),
            "retrieval_focus": str(adaptive.get("retrieval_focus", "")).strip(),
            "speed_mode": str(adaptive.get("speed_mode", "")).strip(),
            "reliability": str(adaptive.get("reliability", "")).strip(),
            "selection_bias": str(adaptive.get("selection_bias", "")).strip(),
            "budget_scale": float(adaptive.get("budget_scale", 0.0) or 0.0),
        }.items()
        if value not in ("", [], {}, None, 0, False)
    }
    if not summary_only:
        return compacted
    miss_recovery = _mapping_value(compacted.get("miss_recovery"))
    return {
        key: value
        for key, value in {
            "within_budget": bool(compacted.get("within_budget")),
            "utility_level": str(compacted.get("utility_level", "")).strip(),
            "token_efficiency_level": str(compacted.get("token_efficiency_level", "")).strip(),
            "context_density_level": str(_mapping_value(compacted.get("context_density")).get("level", "")).strip(),
            "reasoning_readiness_level": str(_mapping_value(compacted.get("reasoning_readiness")).get("level", "")).strip(),
            "packet_strategy": str(compacted.get("packet_strategy", "")).strip(),
            "budget_mode": str(compacted.get("budget_mode", "")).strip(),
            "speed_mode": str(compacted.get("speed_mode", "")).strip(),
            "reliability": str(compacted.get("reliability", "")).strip(),
            "miss_recovery": {
                "active": bool(miss_recovery.get("active")),
                "applied": bool(miss_recovery.get("applied")),
                "mode": str(miss_recovery.get("mode", "")).strip(),
            }
            if miss_recovery
            else {},
        }.items()
        if value not in ("", [], {}, None, False)
    }


def _row_limit(*, packet_kind: str, packet_state: str, compact: int, full: int) -> int:
    if str(packet_kind or "").strip() != "bootstrap_session":
        return full
    if str(packet_state or "").strip().startswith("gated_"):
        return compact
    return max(compact, full - 1)


def _compact_test_rows(rows: Sequence[Mapping[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    compacted: list[dict[str, Any]] = []
    for row in rows[: max(1, int(limit))]:
        if not isinstance(row, Mapping):
            continue
        compact: dict[str, Any] = {}
        for key in ("path", "nodeid", "reason"):
            token = str(row.get(key, "")).strip()
            if token:
                compact[key] = token
        if compact:
            compacted.append(compact)
    return compacted


def _compact_workstream_rows(rows: Sequence[Mapping[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    compacted: list[dict[str, Any]] = []
    for row in rows[: max(1, int(limit))]:
        if not isinstance(row, Mapping):
            continue
        compact: dict[str, Any] = {}
        for key in ("entity_id", "title", "rank", "status"):
            value = row.get(key)
            if value in (None, "", [], {}):
                continue
            compact[key] = value
        if compact:
            compacted.append(compact)
    return compacted


def _compact_component_rows(rows: Sequence[Mapping[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    compacted: list[dict[str, Any]] = []
    for row in rows[: max(1, int(limit))]:
        if not isinstance(row, Mapping):
            continue
        compact: dict[str, Any] = {}
        for key in ("entity_id", "title", "path", "owner"):
            token = str(row.get(key, "")).strip()
            if token:
                compact[key] = token
        if compact:
            compacted.append(compact)
    return compacted


def _compact_diagram_rows(rows: Sequence[Mapping[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    compacted: list[dict[str, Any]] = []
    for row in rows[: max(1, int(limit))]:
        if not isinstance(row, Mapping):
            continue
        compact: dict[str, Any] = {}
        for key in ("diagram_id", "title", "source_mmd", "needs_render"):
            value = row.get(key)
            if value in (None, "", [], {}):
                continue
            compact[key] = value
        if compact:
            compacted.append(compact)
    return compacted


def _compact_guidance_rows(rows: Sequence[Mapping[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    return _compact_guidance_source_rows(rows, limit=limit)[0]


def _retained_components(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = _nested_rows(payload, "components")
    if rows:
        return rows
    impact_summary = _nested_mapping(payload, "impact_summary")
    rows = _mapping_rows(impact_summary.get("components"))
    if rows:
        return rows
    impact = _nested_mapping(payload, "impact")
    return _mapping_rows(impact.get("components"))


def _retained_diagrams(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = _nested_rows(payload, "diagrams")
    if rows:
        return rows
    impact_summary = _nested_mapping(payload, "impact_summary")
    rows = _mapping_rows(impact_summary.get("diagrams"))
    if rows:
        return rows
    impact = _nested_mapping(payload, "impact")
    return _mapping_rows(impact.get("diagrams"))


def _retained_workstreams(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    selection = _nested_mapping(payload, "workstream_selection")
    selected = _mapping_value(selection.get("selected_workstream"))
    if str(selected.get("entity_id", "")).strip():
        return [selected]
    rows = _nested_rows(payload, "candidate_workstreams")
    if rows:
        return rows
    rows = _nested_rows(payload, "workstreams")
    if rows:
        return rows
    impact_summary = _nested_mapping(payload, "impact_summary")
    rows = _mapping_rows(impact_summary.get("workstreams"))
    if rows:
        return rows
    impact = _nested_mapping(payload, "impact")
    rows = _mapping_rows(impact.get("candidate_workstreams"))
    if rows:
        return rows
    return _mapping_rows(impact.get("workstreams"))


def _retained_docs(payload: Mapping[str, Any]) -> list[str]:
    for key in ("docs", "relevant_docs"):
        rows = _string_rows(payload.get(key))
        if rows:
            return rows
    impact_summary = _nested_mapping(payload, "impact_summary")
    rows = _string_rows(impact_summary.get("docs"))
    if rows:
        return rows
    impact = _nested_mapping(payload, "impact")
    return _string_rows(impact.get("docs"))


def _retained_tests(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = _nested_rows(payload, "recommended_tests")
    if rows:
        return rows
    impact_summary = _nested_mapping(payload, "impact_summary")
    rows = _mapping_rows(impact_summary.get("recommended_tests"))
    if rows:
        return rows
    impact = _nested_mapping(payload, "impact")
    return _mapping_rows(impact.get("recommended_tests"))


def _retained_commands(payload: Mapping[str, Any]) -> list[str]:
    rows = _string_rows(payload.get("recommended_commands"))
    if rows:
        return rows
    impact_summary = _nested_mapping(payload, "impact_summary")
    rows = _string_rows(impact_summary.get("recommended_commands"))
    if rows:
        return rows
    impact = _nested_mapping(payload, "impact")
    return _string_rows(impact.get("recommended_commands"))


def _retained_guidance(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    retrieval_plan = _nested_mapping(payload, "retrieval_plan")
    rows = _mapping_rows(retrieval_plan.get("selected_guidance_chunks"))
    if rows:
        return rows
    rows = _nested_rows(payload, "guidance_brief")
    if rows:
        return rows
    impact_summary = _nested_mapping(payload, "impact_summary")
    rows = _mapping_rows(impact_summary.get("guidance_brief"))
    if rows:
        return rows
    impact = _nested_mapping(payload, "impact")
    rows = _mapping_rows(impact.get("guidance_brief"))
    if rows:
        return rows
    warm = _nested_mapping(_nested_mapping(payload, "working_memory_tiers"), "warm")
    return _mapping_rows(warm.get("guidance_chunks"))


def _compact_packet_budget(packet_budget: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in {
            "max_bytes": int(packet_budget.get("max_bytes", 0) or 0),
            "max_tokens": int(packet_budget.get("max_tokens", 0) or 0),
        }.items()
        if value > 0
    }


def _compact_packet_metrics(packet_metrics: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in {
            "estimated_bytes": int(packet_metrics.get("estimated_bytes", 0) or 0),
            "estimated_tokens": int(packet_metrics.get("estimated_tokens", 0) or 0),
            "within_budget": bool(packet_metrics.get("within_budget")),
        }.items()
        if value not in ("", [], {}, None)
    }


def _compact_packet_quality(packet_quality: Mapping[str, Any]) -> dict[str, Any]:
    utility_profile = _mapping_value(packet_quality.get("utility_profile"))
    intent_profile = _mapping_value(packet_quality.get("intent_profile"))
    context_density = _mapping_value(packet_quality.get("context_density"))
    evidence_diversity = _mapping_value(packet_quality.get("evidence_diversity"))
    reasoning_readiness = _mapping_value(packet_quality.get("reasoning_readiness"))
    return {
        key: value
        for key, value in {
            "context_richness": str(packet_quality.get("context_richness", "")).strip(),
            "accuracy_posture": str(packet_quality.get("accuracy_posture", "")).strip(),
            "routing_confidence": str(packet_quality.get("routing_confidence", "")).strip(),
            "anchor_quality": str(packet_quality.get("anchor_quality", "")).strip(),
            "guidance_coverage": str(packet_quality.get("guidance_coverage", "")).strip(),
            "ambiguity_class": str(packet_quality.get("ambiguity_class", "")).strip(),
            "reasoning_bias": str(packet_quality.get("reasoning_bias", "")).strip(),
            "parallelism_hint": str(packet_quality.get("parallelism_hint", "")).strip(),
            "native_spawn_ready": bool(packet_quality.get("native_spawn_ready")),
            "evidence_quality": _mapping_value(packet_quality.get("evidence_quality")),
            "actionability": _mapping_value(packet_quality.get("actionability")),
            "validation_pressure": _mapping_value(packet_quality.get("validation_pressure")),
            "context_density": {
                "score": int(context_density.get("score", 0) or 0),
                "level": str(context_density.get("level", "")).strip(),
                "density_per_1k_tokens": float(context_density.get("density_per_1k_tokens", 0.0) or 0.0),
            }
            if context_density
            else {},
            "evidence_diversity": {
                "score": int(evidence_diversity.get("score", 0) or 0),
                "level": str(evidence_diversity.get("level", "")).strip(),
                "domain_count": int(evidence_diversity.get("domain_count", 0) or 0),
                "duplicate_guidance_count": int(evidence_diversity.get("duplicate_guidance_count", 0) or 0),
            }
            if evidence_diversity
            else {},
            "reasoning_readiness": {
                "score": int(reasoning_readiness.get("score", 0) or 0),
                "level": str(reasoning_readiness.get("level", "")).strip(),
                "mode": str(reasoning_readiness.get("mode", "")).strip(),
                "deep_reasoning_ready": bool(reasoning_readiness.get("deep_reasoning_ready")),
            }
            if reasoning_readiness
            else {},
            "utility_profile": {
                "score": int(utility_profile.get("score", 0) or 0),
                "level": str(utility_profile.get("level", "")).strip(),
                "retained_signal_count": int(utility_profile.get("retained_signal_count", 0) or 0),
                "density_per_1k_tokens": float(utility_profile.get("density_per_1k_tokens", 0.0) or 0.0),
                "token_efficiency": _mapping_value(utility_profile.get("token_efficiency")),
            }
            if utility_profile
            else {},
            "intent_profile": intent_profile,
        }.items()
        if value not in ("", [], {}, None)
    }


def _compact_execution_signals(
    execution_signals: Mapping[str, Any],
    *,
    summary_only: bool,
) -> dict[str, Any]:
    compacted: dict[str, Any] = {}
    for signal_key, signal_value in execution_signals.items():
        signal_mapping = _mapping_value(signal_value)
        if not signal_mapping:
            continue
        if summary_only:
            compact_signal = {
                key: value
                for key, value in {
                    "score": int(signal_mapping.get("score", 0) or 0),
                    "level": str(signal_mapping.get("level", "")).strip(),
                }.items()
                if value not in ("", [], {}, None, 0)
            }
        else:
            compact_signal = {
                subkey: subvalue
                for subkey, subvalue in signal_mapping.items()
                if subvalue not in ("", [], {}, None, False, 0)
            }
        if compact_signal:
            compacted[str(signal_key).strip()] = compact_signal
    return compacted


def _hot_path_summary_only_contract(
    *,
    packet_kind: str,
    payload: Mapping[str, Any],
) -> bool:
    delivery_profile = agent_runtime_contract.canonical_delivery_profile(payload.get("delivery_profile"))
    if delivery_profile != agent_runtime_contract.AGENT_HOT_PATH_PROFILE:
        return False
    return str(packet_kind or "").strip() in {"impact", "session_brief", "bootstrap_session"}


def _compact_routing_handoff(
    routing_handoff: Mapping[str, Any],
    *,
    packet_kind: str,
    packet_state: str,
    summary_only_override: bool = False,
) -> dict[str, Any]:
    handoff_quality = _mapping_value(routing_handoff.get("packet_quality"))
    execution_profile = execution_profile_mapping(
        routing_handoff.get("odylith_execution_profile") or routing_handoff.get("execution_profile")
    )
    execution_signals = _mapping_value(execution_profile.get("signals"))
    execution_constraints = _mapping_value(execution_profile.get("constraints"))
    execution_signals = _mapping_value(execution_profile.get("signals"))
    summary_only = summary_only_override or (
        str(packet_kind or "").strip() == "bootstrap_session" and str(packet_state or "").strip().startswith("gated_")
    )
    return {
        key: value
        for key, value in {
            "routing_confidence": str(routing_handoff.get("routing_confidence", "")).strip(),
            "actionability_level": str(routing_handoff.get("actionability_level", "")).strip(),
            "grounding": _mapping_value(routing_handoff.get("grounding")),
            "packet_quality": {
                "evidence_quality": _mapping_value(handoff_quality.get("evidence_quality")),
                "context_density": {
                    "score": int(_mapping_value(handoff_quality.get("context_density")).get("score", 0) or 0),
                    "level": str(_mapping_value(handoff_quality.get("context_density")).get("level", "")).strip(),
                }
                if _mapping_value(handoff_quality.get("context_density"))
                else {},
                "reasoning_readiness": {
                    "score": int(_mapping_value(handoff_quality.get("reasoning_readiness")).get("score", 0) or 0),
                    "level": str(_mapping_value(handoff_quality.get("reasoning_readiness")).get("level", "")).strip(),
                    "mode": str(_mapping_value(handoff_quality.get("reasoning_readiness")).get("mode", "")).strip(),
                }
                if _mapping_value(handoff_quality.get("reasoning_readiness"))
                else {},
                "utility_profile": {
                    "score": int(_mapping_value(handoff_quality.get("utility_profile")).get("score", 0) or 0),
                    "level": str(_mapping_value(handoff_quality.get("utility_profile")).get("level", "")).strip(),
                }
                if _mapping_value(handoff_quality.get("utility_profile"))
                else {},
                "intent_profile": {
                    "family": str(_mapping_value(handoff_quality.get("intent_profile")).get("family", "")).strip(),
                    "mode": str(_mapping_value(handoff_quality.get("intent_profile")).get("mode", "")).strip(),
                }
                if _mapping_value(handoff_quality.get("intent_profile"))
                else {},
                "reasoning_bias": str(handoff_quality.get("reasoning_bias", "")).strip(),
            }
            if handoff_quality
            else {},
            "validation": _mapping_value(routing_handoff.get("validation")),
            "parallelism": _mapping_value(routing_handoff.get("parallelism")),
            "optimization": _mapping_value(routing_handoff.get("optimization")),
            "risk": _mapping_value(routing_handoff.get("risk")),
            "utility": _mapping_value(routing_handoff.get("utility")),
            "intent": _mapping_value(routing_handoff.get("intent")),
            "odylith_execution_profile": {
                key: value
                for key, value in {
                    "profile": str(execution_profile.get("profile", "")).strip(),
                    "model": str(execution_profile.get("model", "")).strip(),
                    "reasoning_effort": str(execution_profile.get("reasoning_effort", "")).strip(),
                    "agent_role": str(execution_profile.get("agent_role", "")).strip(),
                    "selection_mode": str(execution_profile.get("selection_mode", "")).strip(),
                    "delegate_preference": str(execution_profile.get("delegate_preference", "")).strip(),
                    "source": str(execution_profile.get("source", "")).strip(),
                    "confidence": {
                        "score": int(_mapping_value(execution_profile.get("confidence")).get("score", 0) or 0),
                        "level": str(_mapping_value(execution_profile.get("confidence")).get("level", "")).strip(),
                    }
                    if _mapping_value(execution_profile.get("confidence"))
                    else {},
                    "constraints": {
                        subkey: subvalue
                        for subkey, subvalue in {
                            "route_ready": bool(execution_constraints.get("route_ready")),
                            "narrowing_required": bool(execution_constraints.get("narrowing_required")),
                            "spawn_worthiness": int(execution_constraints.get("spawn_worthiness", 0) or 0),
                            "merge_burden": int(execution_constraints.get("merge_burden", 0) or 0),
                            "reasoning_mode": str(execution_constraints.get("reasoning_mode", "")).strip(),
                            "context_density_score": int(execution_constraints.get("context_density_score", 0) or 0),
                            "reasoning_readiness_score": int(
                                execution_constraints.get("reasoning_readiness_score", 0) or 0
                            ),
                        }.items()
                        if subvalue not in ("", [], {}, None, 0)
                    }
                    if execution_constraints
                    else {},
                    "signals": _compact_execution_signals(execution_signals, summary_only=summary_only),
                }.items()
                if value not in ("", [], {}, None)
            }
            if execution_profile
            else {},
            "route_ready": bool(routing_handoff.get("route_ready")),
            "native_spawn_ready": bool(routing_handoff.get("native_spawn_ready")),
            "narrowing_required": bool(routing_handoff.get("narrowing_required")),
        }.items()
        if value not in ("", [], {}, None)
    }


def build_context_packet(
    *,
    packet_kind: str,
    packet_state: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    retrieval_plan = _nested_mapping(payload, "retrieval_plan")
    working_memory = _nested_mapping(payload, "working_memory_tiers")
    packet_budget = _nested_mapping(payload, "packet_budget")
    packet_metrics = _nested_mapping(payload, "packet_metrics")
    packet_quality = _nested_mapping(payload, "packet_quality")
    routing_handoff = _nested_mapping(payload, "routing_handoff")
    adaptive_packet_profile = _nested_mapping(payload, "adaptive_packet_profile")
    truncation = _nested_mapping(payload, "truncation")
    packet_budget_truncation = _nested_mapping(truncation, "packet_budget")
    limit = _row_limit(packet_kind=packet_kind, packet_state=packet_state, compact=1, full=3)
    bootstrap_contract = str(packet_kind or "").strip() == "bootstrap_session"
    trimmed_packet = bool(packet_budget_truncation.get("truncated")) or bool(packet_budget_truncation.get("applied"))
    budget_pressure = (
        int(packet_budget.get("max_bytes", 0) or 0) > 0
        and (
            not bool(packet_metrics.get("within_budget", True))
            or int(packet_metrics.get("estimated_bytes", 0) or 0) > int(packet_budget.get("max_bytes", 0) or 0)
        )
    )
    summary_only = (
        str(packet_state or "").strip().startswith("gated_")
        or (bootstrap_contract and (trimmed_packet or budget_pressure))
        or _hot_path_summary_only_contract(packet_kind=packet_kind, payload=payload)
    )
    optimization = _compact_contract_optimization(
        packet_metrics=packet_metrics,
        packet_quality=packet_quality,
        retrieval_plan=retrieval_plan,
        adaptive_packet_profile=adaptive_packet_profile,
        summary_only=summary_only,
    )
    execution_profile = execution_profile_mapping(
        routing_handoff.get("odylith_execution_profile") or routing_handoff.get("execution_profile")
    )
    guidance_behavior_summary = guidance_behavior_runtime.summary_from_sources(
        payload,
        limit=max(limit, 6),
    )
    character_summary = character_runtime.summary_from_sources(
        payload,
        limit=max(limit, 6),
    )
    contract_policy = _compact_contract_policy(summary_only=summary_only)
    if summary_only:
        selected_counts = _mapping_value(retrieval_plan.get("selected_counts"))
        summary_anchor_limit = max(limit, 2) if str(packet_state or "").strip().startswith("gated_") else limit
        miss_recovery = _mapping_value(retrieval_plan.get("miss_recovery"))
        return {
            "contract": "context_packet.v1",
            "version": "v1",
            "engine": {
                "name": "odylith-context-engine",
                "product_layer": "memory_retrieval",
            },
            "packet_kind": str(packet_kind or "").strip(),
            "packet_state": str(packet_state or "").strip(),
            **({"guidance_behavior_summary": guidance_behavior_summary} if guidance_behavior_summary else {}),
            **({"character_summary": character_summary} if character_summary else {}),
            "selection_state": str(payload.get("selection_state", "")).strip()
            or str(retrieval_plan.get("selection_state", "")).strip(),
            "full_scan_recommended": bool(payload.get("full_scan_recommended")),
            "full_scan_reason": str(payload.get("full_scan_reason", "")).strip(),
            "anchors": {
                "changed_paths": _string_rows(payload.get("changed_paths"))[:summary_anchor_limit],
                "explicit_paths": _string_rows(payload.get("explicit_paths"))[:summary_anchor_limit],
                "anchor_quality": str(retrieval_plan.get("anchor_quality", "")).strip()
                or str(packet_quality.get("anchor_quality", "")).strip(),
                "has_non_shared_anchor": bool(retrieval_plan.get("has_non_shared_anchor")),
            },
            "retrieval_plan": {
                "selected_domains": _string_rows(retrieval_plan.get("selected_domains"))[: max(limit, 4)],
                "guidance_coverage": str(retrieval_plan.get("guidance_coverage", "")).strip(),
                "evidence_consensus": str(retrieval_plan.get("evidence_consensus", "")).strip(),
                "precision_score": int(retrieval_plan.get("precision_score", 0) or 0),
                "ambiguity_class": str(retrieval_plan.get("ambiguity_class", "")).strip(),
                "selected_counts": {
                    "docs": int(selected_counts.get("docs", 0) or 0),
                    "tests": int(selected_counts.get("tests", 0) or 0),
                    "commands": int(selected_counts.get("commands", 0) or 0),
                    "guidance": int(selected_counts.get("guidance", 0) or 0),
                },
                "miss_recovery": {
                    "active": bool(miss_recovery.get("active")),
                    "applied": bool(miss_recovery.get("applied")),
                    "mode": str(miss_recovery.get("mode", "")).strip(),
                }
                if miss_recovery
                else {},
            },
            "packet_budget": _compact_packet_budget(packet_budget),
            "packet_quality": {
                key: value
                for key, value in {
                    "context_richness": str(packet_quality.get("context_richness", "")).strip(),
                    "accuracy_posture": str(packet_quality.get("accuracy_posture", "")).strip(),
                    "routing_confidence": str(packet_quality.get("routing_confidence", "")).strip(),
                    "intent_family": str(_mapping_value(packet_quality.get("intent_profile")).get("family", "")).strip(),
                    "context_density_level": str(_mapping_value(packet_quality.get("context_density")).get("level", "")).strip(),
                    "reasoning_readiness_level": str(_mapping_value(packet_quality.get("reasoning_readiness")).get("level", "")).strip(),
                }.items()
                if value not in ("", [], {}, None)
            },
            "route": {
                key: value
                for key, value in {
                    "route_ready": bool(routing_handoff.get("route_ready")),
                    "narrowing_required": bool(routing_handoff.get("narrowing_required")),
                    "reasoning_bias": str(routing_handoff.get("reasoning_bias", "")).strip()
                    or str(packet_quality.get("reasoning_bias", "")).strip(),
                    "parallelism_hint": str(routing_handoff.get("parallelism_hint", "")).strip()
                    or str(packet_quality.get("parallelism_hint", "")).strip(),
                }.items()
                if value not in ("", [], {}, None, False)
            },
            "execution_profile": {
                key: value
                for key, value in {
                    "profile": str(execution_profile.get("profile", "")).strip(),
                    "model": str(execution_profile.get("model", "")).strip(),
                    "reasoning_effort": str(execution_profile.get("reasoning_effort", "")).strip(),
                    "agent_role": str(execution_profile.get("agent_role", "")).strip(),
                    "selection_mode": str(execution_profile.get("selection_mode", "")).strip(),
                    "delegate_preference": str(execution_profile.get("delegate_preference", "")).strip(),
                    "source": str(execution_profile.get("source", "")).strip(),
                }.items()
                if value not in ("", [], {}, None)
            },
            "provenance_summary": {
                key: value
                for key, value in {
                    "retained_doc_count": int(selected_counts.get("docs", 0) or 0),
                    "retained_guidance_count": int(selected_counts.get("guidance", 0) or 0),
                }.items()
                if value not in ("", [], {}, None, 0)
            },
            "optimization": optimization,
            "security_posture": contract_policy,
        }
    workstreams = _retained_workstreams(payload)
    components = _retained_components(payload)
    diagrams = _retained_diagrams(payload)
    docs = _retained_docs(payload)
    sanitized_docs, doc_safety = _sanitize_contract_docs(docs, limit=limit)
    tests = _retained_tests(payload)
    commands = _retained_commands(payload)
    guidance = _retained_guidance(payload)
    compact_guidance, guidance_safety = _compact_guidance_source_rows(guidance, limit=limit)
    miss_recovery = _mapping_value(retrieval_plan.get("miss_recovery"))
    hot = _nested_mapping(working_memory, "hot")
    warm = _nested_mapping(working_memory, "warm")
    cold = _nested_mapping(working_memory, "cold")
    scratch = _nested_mapping(working_memory, "scratch")
    component_paths = [
        _normalize_repo_path(row.get("path", ""))
        for row in components
        if isinstance(row, Mapping) and _normalize_repo_path(row.get("path", ""))
    ]
    diagram_paths = [
        _normalize_repo_path(row.get("source_mmd", ""))
        for row in diagrams
        if isinstance(row, Mapping) and _normalize_repo_path(row.get("source_mmd", ""))
    ]
    test_paths = [
        _normalize_repo_path(row.get("path", ""))
        for row in tests
        if isinstance(row, Mapping) and _normalize_repo_path(row.get("path", ""))
    ]
    provenance_summary = {
        "source_classes": _source_count_rows([*sanitized_docs, *component_paths, *diagram_paths, *test_paths]),
        "retained_doc_count": doc_safety["retained_count"],
        "retained_guidance_count": guidance_safety["retained_count"],
        "redacted_sensitive_count": doc_safety["redacted_sensitive_count"] + guidance_safety["redacted_sensitive_count"],
        "dropped_non_allowlisted_count": doc_safety["dropped_non_allowlisted_count"] + guidance_safety["dropped_non_allowlisted_count"],
    }
    execution_signals = _mapping_value(execution_profile.get("signals"))
    compact_provenance_summary = (
        {
            key: value
            for key, value in provenance_summary.items()
            if key in {"retained_doc_count", "retained_guidance_count", "redacted_sensitive_count"}
            and value not in ("", [], {}, None, 0)
        }
        if summary_only
        else {
            key: value
            for key, value in provenance_summary.items()
            if value not in ("", [], {}, None, 0)
        }
    )
    return {
        "contract": "context_packet.v1",
        "version": "v1",
        "engine": {
            "name": "odylith-context-engine",
            "product_layer": "memory_retrieval",
            "storage_mode": "local_derived",
        },
        "packet_kind": str(packet_kind or "").strip(),
        "packet_state": str(packet_state or "").strip(),
        **({"guidance_behavior_summary": guidance_behavior_summary} if guidance_behavior_summary else {}),
        **({"character_summary": character_summary} if character_summary else {}),
        "selection_state": str(payload.get("selection_state", "")).strip()
        or str(retrieval_plan.get("selection_state", "")).strip(),
        "full_scan_recommended": bool(payload.get("full_scan_recommended")),
        "full_scan_reason": str(payload.get("full_scan_reason", "")).strip(),
        "anchors": {
            "changed_paths": _string_rows(payload.get("changed_paths"))[:limit],
            "explicit_paths": _string_rows(payload.get("explicit_paths"))[:limit],
            "anchor_quality": str(retrieval_plan.get("anchor_quality", "")).strip()
            or str(packet_quality.get("anchor_quality", "")).strip(),
            "has_non_shared_anchor": bool(retrieval_plan.get("has_non_shared_anchor")),
            "shared_anchor_paths": _string_rows(retrieval_plan.get("shared_anchor_paths"))[:limit],
        },
        "selection": {
            "workstream_ids": [str(row.get("entity_id", "")).strip() for row in workstreams[:limit] if str(row.get("entity_id", "")).strip()],
            "component_ids": [str(row.get("entity_id", "")).strip() for row in components[:limit] if str(row.get("entity_id", "")).strip()],
            "diagram_ids": [str(row.get("diagram_id", "")).strip() for row in diagrams[:limit] if str(row.get("diagram_id", "")).strip()],
        },
        "retrieval_plan": {
            key: value
            for key, value in {
                "selected_domains": _string_rows(retrieval_plan.get("selected_domains"))[: max(limit, 4)],
                "guidance_coverage": str(retrieval_plan.get("guidance_coverage", "")).strip(),
                "evidence_consensus": str(retrieval_plan.get("evidence_consensus", "")).strip(),
                "precision_score": int(retrieval_plan.get("precision_score", 0) or 0),
                "ambiguity_class": str(retrieval_plan.get("ambiguity_class", "")).strip(),
                "selected_counts": {
                    "docs": len(sanitized_docs),
                    "tests": len(tests),
                    "commands": len(commands),
                    "guidance": len(compact_guidance),
                },
                "miss_recovery": {
                    "active": bool(miss_recovery.get("active")),
                    "applied": bool(miss_recovery.get("applied")),
                    "mode": str(miss_recovery.get("mode", "")).strip(),
                    "query_count": len(_string_rows(miss_recovery.get("queries"))),
                }
                if miss_recovery
                else {},
            }.items()
            if value not in ("", [], {}, None)
        },
        "working_memory": {
            "cold": {
                "source_count": len(_string_rows(cold.get("sources"))),
            },
            "warm": {
                "doc_count": len(_string_rows(warm.get("docs"))),
                "guidance_count": len(_mapping_rows(warm.get("guidance_chunks"))),
                "workstream_count": len(_mapping_rows(warm.get("workstreams"))),
            },
            "hot": {
                "changed_paths": _string_rows(hot.get("changed_paths"))[:limit],
                "command_count": len(_string_rows(hot.get("recommended_commands"))),
                "test_count": len(_mapping_rows(hot.get("recommended_tests"))),
            },
            "scratch": {
                "session_id": str(scratch.get("session_id", "")).strip(),
                "selection_state": str(scratch.get("selection_state", "")).strip(),
            },
        },
        "packet_budget": _compact_packet_budget(packet_budget),
        "packet_metrics": _compact_packet_metrics(packet_metrics),
        "packet_quality": {
            key: value
            for key, value in {
                "context_richness": str(packet_quality.get("context_richness", "")).strip(),
                "accuracy_posture": str(packet_quality.get("accuracy_posture", "")).strip(),
                "routing_confidence": str(packet_quality.get("routing_confidence", "")).strip(),
                "utility_score": int(_mapping_value(packet_quality.get("utility_profile")).get("score", 0) or 0),
                "intent_family": str(_mapping_value(packet_quality.get("intent_profile")).get("family", "")).strip(),
                "intent_mode": str(_mapping_value(packet_quality.get("intent_profile")).get("mode", "")).strip(),
                "context_density_level": str(_mapping_value(packet_quality.get("context_density")).get("level", "")).strip(),
                "reasoning_readiness_level": str(_mapping_value(packet_quality.get("reasoning_readiness")).get("level", "")).strip(),
            }.items()
            if value not in ("", [], {}, None, 0)
        },
        "route": {
            key: value
            for key, value in {
                "route_ready": bool(routing_handoff.get("route_ready")),
                "native_spawn_ready": bool(routing_handoff.get("native_spawn_ready")),
                "narrowing_required": bool(routing_handoff.get("narrowing_required")),
                "reasoning_bias": str(routing_handoff.get("reasoning_bias", "")).strip()
                or str(packet_quality.get("reasoning_bias", "")).strip(),
                "parallelism_hint": str(routing_handoff.get("parallelism_hint", "")).strip()
                or str(packet_quality.get("parallelism_hint", "")).strip(),
            }.items()
            if value not in ("", [], {}, None, False)
        },
        "execution_profile": {
            key: value
            for key, value in {
                "profile": str(execution_profile.get("profile", "")).strip(),
                "model": str(execution_profile.get("model", "")).strip(),
                "reasoning_effort": str(execution_profile.get("reasoning_effort", "")).strip(),
                "agent_role": str(execution_profile.get("agent_role", "")).strip(),
                "selection_mode": str(execution_profile.get("selection_mode", "")).strip(),
                "delegate_preference": str(execution_profile.get("delegate_preference", "")).strip(),
                "signals": {
                    signal_key: {
                        subkey: subvalue
                        for subkey, subvalue in _mapping_value(signal_value).items()
                        if subvalue not in ("", [], {}, None, False, 0)
                    }
                    for signal_key, signal_value in execution_signals.items()
                    if _mapping_value(signal_value)
                }
                if execution_signals
                else {},
            }.items()
            if value not in ("", [], {}, None)
        },
        "provenance_summary": compact_provenance_summary,
        "optimization": optimization,
        "security_posture": contract_policy,
    }


def build_evidence_pack(
    *,
    packet_kind: str,
    packet_state: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    retrieval_plan = _nested_mapping(payload, "retrieval_plan")
    packet_budget = _nested_mapping(payload, "packet_budget")
    packet_metrics = _nested_mapping(payload, "packet_metrics")
    packet_quality = _nested_mapping(payload, "packet_quality")
    routing_handoff = _nested_mapping(payload, "routing_handoff")
    adaptive_packet_profile = _nested_mapping(payload, "adaptive_packet_profile")
    runtime_payload = _nested_mapping(payload, "runtime")
    truncation = _nested_mapping(payload, "truncation")
    packet_budget_truncation = _nested_mapping(truncation, "packet_budget")
    selection_state = str(payload.get("selection_state", "")).strip()
    limit = _row_limit(packet_kind=packet_kind, packet_state=packet_state, compact=1, full=3)
    bootstrap_contract = str(packet_kind or "").strip() == "bootstrap_session"
    trimmed_packet = bool(packet_budget_truncation.get("truncated")) or bool(packet_budget_truncation.get("applied"))
    budget_pressure = (
        int(packet_budget.get("max_bytes", 0) or 0) > 0
        and (
            not bool(packet_metrics.get("within_budget", True))
            or int(packet_metrics.get("estimated_bytes", 0) or 0) > int(packet_budget.get("max_bytes", 0) or 0)
        )
    )
    summary_only = (
        str(packet_state or "").strip().startswith("gated_")
        or (bootstrap_contract and (trimmed_packet or budget_pressure))
        or _hot_path_summary_only_contract(packet_kind=packet_kind, payload=payload)
    )
    workstreams = _retained_workstreams(payload)
    components = _retained_components(payload)
    diagrams = _retained_diagrams(payload)
    docs = _retained_docs(payload)
    sanitized_docs, doc_safety = _sanitize_contract_docs(docs, limit=limit)
    tests = _retained_tests(payload)
    commands = _retained_commands(payload)
    guidance = _retained_guidance(payload)
    compact_guidance, guidance_safety = _compact_guidance_source_rows(guidance, limit=limit)
    compact_quality = _compact_packet_quality(packet_quality)
    compact_handoff = _compact_routing_handoff(
        routing_handoff,
        packet_kind=packet_kind,
        packet_state=packet_state,
        summary_only_override=summary_only,
    )
    evidence_summary = {
        "guidance_coverage": str(retrieval_plan.get("guidance_coverage", "")).strip()
        or str(packet_quality.get("guidance_coverage", "")).strip(),
        "evidence_consensus": str(retrieval_plan.get("evidence_consensus", "")).strip(),
        "precision_score": int(retrieval_plan.get("precision_score", 0) or 0),
        "ambiguity_class": str(retrieval_plan.get("ambiguity_class", "")).strip()
        or str(packet_quality.get("ambiguity_class", "")).strip(),
        "selected_domain_count": len(_string_rows(retrieval_plan.get("selected_domains"))),
        "retained_signal_count": int(_mapping_value(packet_quality.get("utility_profile")).get("retained_signal_count", 0) or 0),
        "budget_bytes": int(packet_budget.get("max_bytes", 0) or 0),
        "estimated_bytes": int(packet_metrics.get("estimated_bytes", 0) or 0),
    }
    component_paths = [
        _normalize_repo_path(row.get("path", ""))
        for row in components
        if isinstance(row, Mapping) and _normalize_repo_path(row.get("path", ""))
    ]
    diagram_paths = [
        _normalize_repo_path(row.get("source_mmd", ""))
        for row in diagrams
        if isinstance(row, Mapping) and _normalize_repo_path(row.get("source_mmd", ""))
    ]
    test_paths = [
        _normalize_repo_path(row.get("path", ""))
        for row in tests
        if isinstance(row, Mapping) and _normalize_repo_path(row.get("path", ""))
    ]
    provenance_summary = {
        "source_classes": _source_count_rows([*sanitized_docs, *component_paths, *diagram_paths, *test_paths]),
        "retained_doc_count": doc_safety["retained_count"],
        "retained_guidance_count": guidance_safety["retained_count"],
        "redacted_sensitive_count": doc_safety["redacted_sensitive_count"] + guidance_safety["redacted_sensitive_count"],
        "dropped_non_allowlisted_count": doc_safety["dropped_non_allowlisted_count"] + guidance_safety["dropped_non_allowlisted_count"],
    }
    optimization = _compact_contract_optimization(
        packet_metrics=packet_metrics,
        packet_quality=packet_quality,
        retrieval_plan=retrieval_plan,
        adaptive_packet_profile=adaptive_packet_profile,
        summary_only=summary_only,
    )
    guidance_behavior_summary = guidance_behavior_runtime.summary_from_sources(
        payload,
        limit=max(limit, 6),
    )
    character_summary = character_runtime.summary_from_sources(
        payload,
        limit=max(limit, 6),
    )
    contract_policy = _compact_contract_policy(summary_only=summary_only)
    if summary_only:
        return {
            "contract": "evidence_pack.v1",
            "version": "v1",
            "packet_kind": str(packet_kind or "").strip(),
            "packet_state": str(packet_state or "").strip(),
            **({"guidance_behavior_summary": guidance_behavior_summary} if guidance_behavior_summary else {}),
            **({"character_summary": character_summary} if character_summary else {}),
            "selection_state": selection_state,
            "full_scan_recommended": bool(payload.get("full_scan_recommended")),
            "full_scan_reason": str(payload.get("full_scan_reason", "")).strip(),
            "provenance": {
                "engine": "odylith-context-engine",
                "product_layer": "memory_retrieval",
                "canonical_truth": "repo_tracked",
                "redacted_sensitive_count": int(provenance_summary.get("redacted_sensitive_count", 0) or 0),
            },
            "anchors": {
                "changed_paths": _string_rows(payload.get("changed_paths"))[:limit],
                "explicit_paths": _string_rows(payload.get("explicit_paths"))[:limit],
                "workstream_ids": [str(row.get("entity_id", "")).strip() for row in workstreams[:limit] if str(row.get("entity_id", "")).strip()],
            },
            "evidence_summary": {
                key: value
                for key, value in evidence_summary.items()
                if key in {"guidance_coverage", "evidence_consensus", "precision_score", "ambiguity_class", "selected_domain_count"}
                and value not in ("", [], {}, None, 0)
            },
            "routing_handoff": {
                key: value
                for key, value in compact_handoff.items()
                if key in {"grounding", "packet_quality", "intent", "route_ready", "narrowing_required"}
                and value not in ("", [], {}, None)
            },
            "optimization": optimization,
            "security_posture": contract_policy,
        }
    return {
        "contract": "evidence_pack.v1",
        "version": "v1",
        "packet_kind": str(packet_kind or "").strip(),
        "packet_state": str(packet_state or "").strip(),
        **({"guidance_behavior_summary": guidance_behavior_summary} if guidance_behavior_summary else {}),
        **({"character_summary": character_summary} if character_summary else {}),
        "selection_state": selection_state,
        "full_scan_recommended": bool(payload.get("full_scan_recommended")),
        "full_scan_reason": str(payload.get("full_scan_reason", "")).strip(),
        "provenance": {
            "engine": "odylith-context-engine",
            "product_layer": "memory_retrieval",
            "canonical_truth": "repo_tracked",
            "projection_fingerprint": str(runtime_payload.get("projection_fingerprint", "")).strip(),
            "projection_scope": str(runtime_payload.get("projection_scope", "")).strip(),
            "updated_utc": str(runtime_payload.get("updated_utc", "")).strip(),
            "source_classes": dict(provenance_summary.get("source_classes", {})),
            "redacted_sensitive_count": int(provenance_summary.get("redacted_sensitive_count", 0) or 0),
            "dropped_non_allowlisted_count": int(provenance_summary.get("dropped_non_allowlisted_count", 0) or 0),
        },
        "anchors": {
            "changed_paths": _string_rows(payload.get("changed_paths"))[:limit],
            "explicit_paths": _string_rows(payload.get("explicit_paths"))[:limit],
            "workstream_ids": [str(row.get("entity_id", "")).strip() for row in workstreams[:limit] if str(row.get("entity_id", "")).strip()],
            "component_ids": [str(row.get("entity_id", "")).strip() for row in components[:limit] if str(row.get("entity_id", "")).strip()],
            "diagram_ids": [str(row.get("diagram_id", "")).strip() for row in diagrams[:limit] if str(row.get("diagram_id", "")).strip()],
        },
        "documents": [] if summary_only else sanitized_docs[:limit],
        "tests": [] if summary_only else _compact_test_rows(tests, limit=limit),
        "commands": [] if summary_only else commands[:limit],
        "guidance": [] if summary_only else compact_guidance,
        "entities": {
            "workstream_ids": [str(row.get("entity_id", "")).strip() for row in workstreams[:limit] if str(row.get("entity_id", "")).strip()],
            "component_ids": []
            if summary_only
            else [str(row.get("entity_id", "")).strip() for row in components[:limit] if str(row.get("entity_id", "")).strip()],
            "diagram_ids": []
            if summary_only
            else [str(row.get("diagram_id", "")).strip() for row in diagrams[:limit] if str(row.get("diagram_id", "")).strip()],
        },
        "evidence_summary": {key: value for key, value in evidence_summary.items() if value not in ("", [], {}, None, 0)},
        "packet_metrics": _compact_packet_metrics(packet_metrics),
        "routing_handoff": compact_handoff,
        "optimization": optimization,
        "security_posture": contract_policy,
    }


__all__ = [
    "build_context_packet",
    "build_evidence_pack",
    "compact_execution_profile_mapping",
    "encode_execution_profile_token",
    "execution_profile_mapping",
]
