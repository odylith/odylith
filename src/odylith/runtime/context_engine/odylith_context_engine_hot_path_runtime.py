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
from odylith.runtime.context_engine import odylith_context_engine_hot_path_delivery_runtime
from odylith.runtime.context_engine import odylith_context_engine_hot_path_governance_runtime
from odylith.runtime.context_engine import odylith_context_engine_hot_path_packet_bootstrap_runtime
from odylith.runtime.context_engine import odylith_context_engine_hot_path_packet_core_runtime
from odylith.runtime.context_engine import odylith_context_engine_hot_path_packet_finalize_runtime
from odylith.runtime.context_engine import odylith_context_engine_hot_path_scope_runtime

def bind(host: Any) -> None:
    if isinstance(host, dict):
        for name in _HOST_BIND_NAMES:
            if name in host:
                globals()[name] = host[name]
    else:
        for name in _HOST_BIND_NAMES:
            if hasattr(host, name):
                globals()[name] = getattr(host, name)
    odylith_context_engine_hot_path_scope_runtime.bind(globals())
    odylith_context_engine_hot_path_packet_core_runtime.bind(globals())
    odylith_context_engine_hot_path_packet_bootstrap_runtime.bind(globals())
    odylith_context_engine_hot_path_packet_finalize_runtime.bind(globals())
    odylith_context_engine_hot_path_delivery_runtime.bind(globals())
    odylith_context_engine_hot_path_governance_runtime.bind(globals())

_HOST_BIND_NAMES = (
    'SESSION_STALE_SECONDS',
    '_CODEX_HOT_PATH_PROFILE',
    '_COMPANION_CONTEXT_RULES',
    '_CONTRACT_PATH_PREFIXES',
    '_extract_path_refs',
    '_ENGINEERING_NOTE_KINDS',
    '_HOT_PATH_AUTO_ESCALATION_CONSERVATIVE_FAMILIES',
    '_HOT_PATH_AUTO_ESCALATION_WRITE_FAMILIES',
    '_HOT_PATH_AUTO_SESSION_BRIEF_FAMILIES',
    '_IMPACT_COMMAND_LIMIT_AMBIGUOUS',
    '_IMPACT_COMMAND_LIMIT_BROAD',
    '_IMPACT_COMMAND_LIMIT_DEFAULT',
    '_IMPACT_COMMAND_LIMIT_EXPLICIT',
    '_IMPACT_DOC_LIMIT_AMBIGUOUS',
    '_IMPACT_DOC_LIMIT_BROAD',
    '_IMPACT_DOC_LIMIT_DEFAULT',
    '_IMPACT_DOC_LIMIT_EXPLICIT',
    '_IMPACT_ENGINEERING_NOTES_PER_KIND_LIMIT_AMBIGUOUS',
    '_IMPACT_ENGINEERING_NOTES_PER_KIND_LIMIT_DEFAULT',
    '_IMPACT_ENGINEERING_NOTES_PER_KIND_LIMIT_EXPLICIT',
    '_IMPACT_ENGINEERING_NOTES_TOTAL_LIMIT_AMBIGUOUS',
    '_IMPACT_ENGINEERING_NOTES_TOTAL_LIMIT_BROAD',
    '_IMPACT_ENGINEERING_NOTES_TOTAL_LIMIT_DEFAULT',
    '_IMPACT_ENGINEERING_NOTES_TOTAL_LIMIT_EXPLICIT',
    '_IMPACT_TEST_LIMIT_AMBIGUOUS',
    '_IMPACT_TEST_LIMIT_DEFAULT',
    '_IMPACT_TEST_LIMIT_EXPLICIT',
    '_IMPACT_WORKSTREAM_LIMIT_AMBIGUOUS',
    '_IMPACT_WORKSTREAM_LIMIT_BROAD',
    '_IMPACT_WORKSTREAM_LIMIT_DEFAULT',
    '_IMPACT_WORKSTREAM_LIMIT_EXPLICIT',
    '_PROCESS_GIT_REF_CACHE',
    '_PROCESS_GIT_REF_CACHE_TTL_SECONDS',
    '_PROCESS_PATH_SCOPE_CACHE',
    '_PROCESS_PATH_SIGNAL_PROFILE_CACHE',
    '_SESSION_CLAIM_MODES',
    '_TOPOLOGY_DOMAIN_RULES',
    '_WEAK_SHARED_EXACT_PATHS',
    '_WEAK_SHARED_PREFIXES',
    '_WORKSTREAM_SELECTION_CONFIDENT_SCORE',
    '_WORKSTREAM_SELECTION_GAP_MIN',
    '_cached_projection_rows',
    '_compact_miss_recovery_for_packet',
    '_compact_selection_state_parts',
    '_components_for_paths',
    '_connect',
    '_decode_compact_selected_counts',
    '_encode_compact_selected_counts',
    '_encode_compact_selection_state',
    '_entity_by_kind_id',
    '_entity_from_row',
    '_full_scan_guidance',
    '_json_list',
    '_load_component_match_rows_from_components',
    '_normalize_repo_token',
    '_normalized_string_list',
    '_parse_component_tokens',
    '_path_fingerprint',
    '_payload_workstream_hint',
    '_runtime_enabled',
    '_summarize_entity',
    '_truncate_text',
    '_utc_now',
    '_warm_runtime',
    '_workspace_activity_fingerprint',
    '_workstream_token',
    'bootstraps_root',
    'component_registry',
    'display_command',
    'governance',
    'is_component_spec_path',
    'odylith_context_cache',
    'odylith_context_engine_grounding_runtime',
    'prune_runtime_records',
    'projection_snapshot_path',
    'routing',
    'runtime_request_namespace',
    'sessions_root',
    'tooling_context_budgeting',
    'tooling_memory_contracts',
    'truth_path_kind',
    'truth_root_tokens',
)

def _compact_bug_row_for_governance_packet(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "bug_id": str(row.get("bug_id", "")).strip(),
        "bug_key": str(row.get("bug_key", "")).strip(),
        "title": str(row.get("title", "")).strip(),
        "severity": str(row.get("severity", "")).strip(),
        "status": str(row.get("status", "")).strip(),
        "path": str(row.get("path", "")).strip(),
    }

def _compact_component_entry_for_governance_packet(entry: component_registry.ComponentEntry) -> dict[str, Any]:
    return {
        "component_id": str(entry.component_id).strip(),
        "name": str(entry.name).strip(),
        "kind": str(entry.kind).strip(),
        "qualification": str(entry.qualification).strip(),
        "owner": str(entry.owner).strip(),
        "status": str(entry.status).strip(),
        "path": str(entry.spec_ref).strip(),
        "workstreams": [str(token).strip() for token in entry.workstreams if str(token).strip()],
        "diagrams": [str(token).strip() for token in entry.diagrams if str(token).strip()],
    }

def _architecture_required_reads(
    *,
    topology_domains: Sequence[Mapping[str, Any]],
    component_entities: Sequence[Mapping[str, Any]],
    linked_diagrams: Sequence[Mapping[str, Any]],
) -> list[str]:
    reads: list[str] = []
    for row in topology_domains:
        reads.extend(
            [
                str(path).strip()
                for path in row.get("required_reads", [])
                if str(path).strip()
            ]
        )
    reads.extend(
        str(entity.get("path", "")).strip()
        for entity in component_entities
        if str(entity.get("path", "")).strip()
    )
    reads.extend(
        str(diagram.get("path", "")).strip()
        for diagram in linked_diagrams
        if str(diagram.get("path", "")).strip()
    )
    return _dedupe_strings(reads)

def _dedupe_strings(values: Sequence[str]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = str(raw).strip()
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows

def _normalize_changed_path_list(*, repo_root: Path, values: Sequence[str]) -> list[str]:
    return governance.normalize_changed_paths(repo_root=repo_root, values=values)

def _engineering_note_summary(row: Mapping[str, Any], *, match: Mapping[str, Any] | None = None) -> dict[str, Any]:
    metadata = json.loads(str(row["metadata_json"] or "{}"))
    payload = {
        "note_id": str(row["note_id"]),
        "kind": str(row["note_kind"]),
        "title": str(row["title"]),
        "source_path": str(row["source_path"]),
        "summary": str(row["summary"]),
        "components": _json_list(str(row["components_json"])),
        "workstreams": _json_list(str(row["workstreams_json"])),
    }
    if isinstance(metadata, Mapping):
        for key in ("source_mode", "chunk_id", "chunk_path", "canonical_source", "canonical_section", "manifest_path"):
            value = str(metadata.get(key, "")).strip()
            if value:
                payload[key] = value
    if isinstance(match, Mapping):
        payload["matched_by"] = [str(token) for token in match.get("matched_by", []) if str(token).strip()]
        payload["matched_paths"] = [str(token) for token in match.get("matched_paths", []) if str(token).strip()]
        payload["matched_components"] = [str(token) for token in match.get("matched_components", []) if str(token).strip()]
        payload["matched_workstreams"] = [str(token) for token in match.get("matched_workstreams", []) if str(token).strip()]
        relevance = match.get("relevance", {})
        payload["relevance"] = dict(relevance) if isinstance(relevance, Mapping) else {}
    return payload

def _git_stdout(*, repo_root: Path, args: Sequence[str]) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError:
        return ""
    return str(completed.stdout or "").strip()

def _git_ref_snapshot(*, repo_root: Path) -> dict[str, str]:
    root = Path(repo_root).resolve()
    cache_key = str(root)
    now = time.monotonic()
    cached = _PROCESS_GIT_REF_CACHE.get(cache_key)
    if cached is not None and now - cached[0] <= _PROCESS_GIT_REF_CACHE_TTL_SECONDS:
        return dict(cached[1])
    try:
        branch_completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            check=False,
            text=True,
        )
        head_completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError:
        snapshot = {"branch_name": "", "head_oid": ""}
        _PROCESS_GIT_REF_CACHE[cache_key] = (now, snapshot)
        return dict(snapshot)
    branch_name = str(branch_completed.stdout or "").strip()
    head_oid = str(head_completed.stdout or "").strip()
    snapshot = {
        "branch_name": "" if branch_name == "HEAD" else branch_name,
        "head_oid": head_oid,
    }
    _PROCESS_GIT_REF_CACHE[cache_key] = (now, snapshot)
    return dict(snapshot)

def _git_head_oid(*, repo_root: Path) -> str:
    return str(_git_ref_snapshot(repo_root=repo_root).get("head_oid", "")).strip()

def _git_branch_name(*, repo_root: Path) -> str:
    return str(_git_ref_snapshot(repo_root=repo_root).get("branch_name", "")).strip()

def _path_signal_profile(path: str) -> dict[str, Any]:
    root = Path(".").resolve()
    normalized = _normalize_repo_token(str(path or ""), repo_root=root)
    token = normalized.lower()
    if not token:
        return {"category": "unknown", "weight": 0, "shared": True}
    cache_key = f"{root}:{token}"
    cached = _PROCESS_PATH_SIGNAL_PROFILE_CACHE.get(cache_key)
    if cached is not None:
        return dict(cached)
    truth_roots = truth_root_tokens(repo_root=root)
    if token in _WEAK_SHARED_EXACT_PATHS or token.endswith("/agents.md") or any(
        token.startswith(prefix) for prefix in _WEAK_SHARED_PREFIXES
    ):
        profile = {"category": "shared", "weight": -12, "shared": True}
    elif token == "makefile" or token.startswith("mk/"):
        profile = {"category": "build", "weight": 16, "shared": False}
    elif token.startswith(("src/odylith/", "app/", "services/", "infra/", "bin/", "configs/", "docker/", "policies/")):
        profile = {"category": "implementation", "weight": 18, "shared": False}
    elif token.startswith(_CONTRACT_PATH_PREFIXES):
        profile = {"category": "contract", "weight": 18, "shared": False}
    else:
        path_kind = truth_path_kind(normalized, repo_root=root, truth_roots=truth_roots)
        if path_kind == "component_forensics":
            profile = {"category": "component_forensics", "weight": 8, "shared": False}
        elif path_kind == "component_spec":
            profile = {"category": "component_spec", "weight": 10, "shared": False}
        elif path_kind == "runbook" or token.startswith("docs/runbooks/"):
            profile = {"category": "runbook", "weight": 9, "shared": False}
        elif token.startswith("tests/"):
            profile = {"category": "test", "weight": 6, "shared": False}
        elif token.startswith(("odylith/technical-plans/", "odylith/radar/source/ideas/", "odylith/casebook/bugs/")):
            profile = {"category": "planning", "weight": 5, "shared": False}
        elif token.startswith(("odylith/radar/source/", "docs/")):
            profile = {"category": "doc", "weight": 7, "shared": False}
        else:
            profile = {"category": "other", "weight": 4, "shared": False}
    _PROCESS_PATH_SIGNAL_PROFILE_CACHE[cache_key] = dict(profile)
    return dict(profile)

def _path_match_type(*, changed_path: str, target_path: str) -> str:
    changed = _normalize_repo_token(str(changed_path or ""), repo_root=Path("."))
    target = _normalize_repo_token(str(target_path or ""), repo_root=Path("."))
    return _normalized_path_match_type(changed_path=changed, target_path=target)

def _normalized_path_match_type(*, changed_path: str, target_path: str) -> str:
    changed = _normalized_watch_path(str(changed_path or ""))
    target = _normalized_watch_path(str(target_path or ""))
    if not changed or not target:
        return ""
    if changed == target:
        return "exact"
    if _path_touches_watch(changed_path=changed, watch_path=target):
        return "watch"
    return ""

def _split_csv_tokens(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text or text.lower() == "none":
        return []
    return [token.strip().upper() for token in text.split(",") if token.strip()]

def _base_workstream_candidate(entity: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(entity.get("metadata", {})) if isinstance(entity.get("metadata"), Mapping) else {}
    workstream_type = str(metadata.get("workstream_type", "")).strip().lower() or "standalone"
    workstream_parent = str(metadata.get("workstream_parent", "")).strip().upper()
    workstream_children = _split_csv_tokens(metadata.get("workstream_children", ""))
    return {
        "kind": "workstream",
        "entity_id": str(entity.get("entity_id", "")).strip().upper(),
        "title": str(entity.get("title", "")).strip(),
        "path": str(entity.get("path", "")).strip(),
        "status": str(entity.get("status", "")).strip(),
        "workstream_type": workstream_type,
        "workstream_parent": workstream_parent,
        "workstream_children": workstream_children,
        "metadata": metadata,
        "evidence": {
            "score": 0,
            "matched_paths": [],
            "matched_components": [],
            "matched_diagrams": [],
            "path_signal_counts": {},
            "counters": {},
            "strong_signal_count": 0,
            "weak_signal_count": 0,
            "broad_shared_signal_count": 0,
            "non_shared_signal_count": 0,
            "broad_only": True,
            "overshadowed_by_child": False,
            "summary": "",
        },
    }

def _shared_path_weight(source_kind: str, match_type: str) -> int:
    shared_weights = {
        ("direct", "exact"): 20,
        ("direct", "watch"): 12,
        ("trace_code", "exact"): 18,
        ("trace_code", "watch"): 10,
        ("trace_doc", "exact"): 10,
        ("trace_doc", "watch"): 6,
        ("trace_runbook", "exact"): 8,
        ("trace_runbook", "watch"): 5,
    }
    return int(shared_weights.get((source_kind, match_type), 4))

def _add_workstream_path_evidence(
    candidate: dict[str, Any],
    *,
    changed_path: str,
    target_path: str,
    source_kind: str,
    match_type: str,
) -> None:
    evidence = candidate["evidence"]
    profile = _path_signal_profile(changed_path)
    category = str(profile["category"])
    counters = evidence["counters"]
    counters_key = f"{source_kind}_{match_type}"
    counters[counters_key] = int(counters.get(counters_key, 0) or 0) + 1
    signal_counts = evidence["path_signal_counts"]
    signal_counts[category] = int(signal_counts.get(category, 0) or 0) + 1
    matched_paths = evidence["matched_paths"]
    if changed_path not in matched_paths:
        matched_paths.append(changed_path)
    direct_weights = {
        ("direct", "exact"): 140,
        ("direct", "watch"): 110,
        ("trace_code", "exact"): 125,
        ("trace_code", "watch"): 95,
        ("trace_doc", "exact"): 70,
        ("trace_doc", "watch"): 55,
        ("trace_runbook", "exact"): 65,
        ("trace_runbook", "watch"): 50,
    }
    base_weight = (
        _shared_path_weight(source_kind, match_type)
        if bool(profile["shared"])
        else int(direct_weights.get((source_kind, match_type), 40))
    )
    evidence["score"] += base_weight + int(profile["weight"])
    if ((source_kind in {"direct", "trace_code"} and not bool(profile["shared"])) or category in {"implementation", "contract", "build"}):
        evidence["strong_signal_count"] += 1
    else:
        evidence["weak_signal_count"] += 1
    if bool(profile["shared"]):
        evidence["broad_shared_signal_count"] += 1
    else:
        evidence["non_shared_signal_count"] += 1
        evidence["broad_only"] = False

def _add_workstream_component_evidence(candidate: dict[str, Any], *, component_id: str) -> None:
    evidence = candidate["evidence"]
    if component_id not in evidence["matched_components"]:
        evidence["matched_components"].append(component_id)
        evidence["score"] += 36
        evidence["weak_signal_count"] += 1

def _add_workstream_diagram_evidence(candidate: dict[str, Any], *, diagram_id: str) -> None:
    evidence = candidate["evidence"]
    if diagram_id not in evidence["matched_diagrams"]:
        evidence["matched_diagrams"].append(diagram_id)
        evidence["score"] += 22
        evidence["weak_signal_count"] += 1

def _summarize_workstream_evidence(candidate: Mapping[str, Any]) -> str:
    evidence = candidate.get("evidence", {})
    if not isinstance(evidence, Mapping):
        return ""
    counters = dict(evidence.get("counters", {})) if isinstance(evidence.get("counters"), Mapping) else {}
    parts: list[str] = []
    direct_hits = int(counters.get("direct_exact", 0) or 0) + int(counters.get("direct_watch", 0) or 0)
    trace_code_hits = int(counters.get("trace_code_exact", 0) or 0) + int(counters.get("trace_code_watch", 0) or 0)
    trace_doc_hits = int(counters.get("trace_doc_exact", 0) or 0) + int(counters.get("trace_doc_watch", 0) or 0)
    trace_runbook_hits = int(counters.get("trace_runbook_exact", 0) or 0) + int(counters.get("trace_runbook_watch", 0) or 0)
    if direct_hits:
        parts.append(f"{direct_hits} direct workstream path hit(s)")
    if trace_code_hits:
        parts.append(f"{trace_code_hits} code traceability hit(s)")
    if trace_doc_hits:
        parts.append(f"{trace_doc_hits} developer-doc traceability hit(s)")
    if trace_runbook_hits:
        parts.append(f"{trace_runbook_hits} runbook traceability hit(s)")
    matched_components = evidence.get("matched_components", [])
    if isinstance(matched_components, list) and matched_components:
        parts.append(f"{len(matched_components)} component link(s)")
    matched_diagrams = evidence.get("matched_diagrams", [])
    if isinstance(matched_diagrams, list) and matched_diagrams:
        parts.append(f"{len(matched_diagrams)} diagram link(s)")
    if bool(evidence.get("broad_only")):
        parts.append("only broad shared-path evidence")
    if bool(evidence.get("overshadowed_by_child")):
        parts.append("umbrella signal downgraded because child workstream evidence is narrower")
    if bool(evidence.get("lineage_successor_bonus")):
        parts.append("successor lineage outranked an older reopened workstream with equivalent evidence")
    if bool(evidence.get("lineage_predecessor_downgraded")):
        parts.append("older reopened workstream downgraded in favor of successor lineage")
    return "; ".join(parts)

def _workstream_lineage_tokens(candidate: Mapping[str, Any], *keys: str) -> set[str]:
    metadata = candidate.get("metadata", {})
    if not isinstance(metadata, Mapping):
        return set()
    values: set[str] = set()
    for key in keys:
        values.update(_split_csv_tokens(metadata.get(key, "")))
    return values

def _workstream_candidates_share_evidence(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_evidence = left.get("evidence", {})
    right_evidence = right.get("evidence", {})
    if not isinstance(left_evidence, Mapping) or not isinstance(right_evidence, Mapping):
        return False
    shared_paths = set(left_evidence.get("matched_paths", [])) & set(right_evidence.get("matched_paths", []))
    shared_components = set(left_evidence.get("matched_components", [])) & set(right_evidence.get("matched_components", []))
    shared_diagrams = set(left_evidence.get("matched_diagrams", [])) & set(right_evidence.get("matched_diagrams", []))
    return bool(shared_paths or shared_components or shared_diagrams)

def _apply_workstream_successor_bonus(
    *,
    successor: dict[str, Any],
    predecessor: dict[str, Any],
) -> None:
    successor_evidence = successor.get("evidence", {})
    predecessor_evidence = predecessor.get("evidence", {})
    if not isinstance(successor_evidence, dict) or not isinstance(predecessor_evidence, dict):
        return
    if int(successor_evidence.get("strong_signal_count", 0) or 0) <= 0:
        return
    if int(predecessor_evidence.get("strong_signal_count", 0) or 0) <= 0:
        return
    if int(successor_evidence.get("score", 0) or 0) < int(predecessor_evidence.get("score", 0) or 0) - 12:
        return
    if not _workstream_candidates_share_evidence(successor, predecessor):
        return
    successor_evidence["score"] = int(successor_evidence.get("score", 0) or 0) + 28
    predecessor_evidence["score"] = int(predecessor_evidence.get("score", 0) or 0) - 12
    successor_evidence["lineage_successor_bonus"] = True
    predecessor_evidence["lineage_predecessor_downgraded"] = True

def _finalize_workstream_candidates(candidates: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [dict(candidate) for candidate in candidates]
    by_id = {str(row.get("entity_id", "")).strip().upper(): row for row in rows}
    for row in rows:
        evidence = row.get("evidence", {})
        if not isinstance(evidence, Mapping):
            continue
        workstream_type = str(row.get("workstream_type", "")).strip().lower()
        strong_signals = int(evidence.get("strong_signal_count", 0) or 0)
        if workstream_type == "child" and strong_signals:
            evidence["score"] = int(evidence.get("score", 0) or 0) + 12
        if workstream_type == "umbrella":
            evidence["score"] = int(evidence.get("score", 0) or 0) - 8
            child_ids = [token for token in row.get("workstream_children", []) if str(token).strip()]
            if any(
                int(dict(by_id.get(child_id, {})).get("evidence", {}).get("strong_signal_count", 0) or 0) > 0
                for child_id in child_ids
            ):
                evidence["score"] = int(evidence.get("score", 0) or 0) - 60
                evidence["overshadowed_by_child"] = True
        if bool(evidence.get("broad_only")) and int(evidence.get("strong_signal_count", 0) or 0) == 0:
            evidence["score"] = int(evidence.get("score", 0) or 0) - 80
    processed_pairs: set[tuple[str, str]] = set()
    for row in rows:
        row_id = str(row.get("entity_id", "")).strip().upper()
        if not row_id:
            continue
        predecessor_ids = _workstream_lineage_tokens(row, "workstream_reopens", "supersedes")
        for predecessor_id in predecessor_ids:
            pair = (row_id, predecessor_id)
            if pair in processed_pairs:
                continue
            predecessor = by_id.get(predecessor_id)
            if predecessor is None:
                continue
            _apply_workstream_successor_bonus(successor=row, predecessor=predecessor)
            processed_pairs.add(pair)
        successor_ids = _workstream_lineage_tokens(row, "workstream_reopened_by", "superseded_by")
        for successor_id in successor_ids:
            pair = (successor_id, row_id)
            if pair in processed_pairs:
                continue
            successor = by_id.get(successor_id)
            if successor is None:
                continue
            _apply_workstream_successor_bonus(successor=successor, predecessor=row)
            processed_pairs.add(pair)
    for row in rows:
        evidence = row.get("evidence", {})
        if not isinstance(evidence, Mapping):
            continue
        evidence["summary"] = _summarize_workstream_evidence(row)
    rows.sort(
        key=lambda row: (
            -int(dict(row.get("evidence", {})).get("score", 0) or 0),
            -int(dict(row.get("evidence", {})).get("strong_signal_count", 0) or 0),
            _workstream_status_rank(str(row.get("status", ""))),
            str(row.get("entity_id", "")),
        )
    )
    for index, row in enumerate(rows, start=1):
        evidence = row.get("evidence", {})
        if isinstance(evidence, Mapping):
            matched_paths = evidence.get("matched_paths", [])
            if isinstance(matched_paths, list):
                evidence["matched_paths"] = matched_paths[:12]
            matched_components = evidence.get("matched_components", [])
            if isinstance(matched_components, list):
                evidence["matched_components"] = matched_components[:8]
            matched_diagrams = evidence.get("matched_diagrams", [])
            if isinstance(matched_diagrams, list):
                evidence["matched_diagrams"] = matched_diagrams[:8]
        row["rank"] = index
    return rows

def _workstream_evidence_score(row: Mapping[str, Any]) -> int:
    evidence = row.get("evidence", {})
    if not isinstance(evidence, Mapping):
        return 0
    return int(evidence.get("score", 0) or 0)

def _workstream_signal_counter(row: Mapping[str, Any], *keys: str) -> int:
    evidence = row.get("evidence", {})
    counters = dict(evidence.get("counters", {})) if isinstance(evidence, Mapping) and isinstance(evidence.get("counters"), Mapping) else {}
    return sum(int(counters.get(key, 0) or 0) for key in keys)

def _workstream_has_exact_path_signal(row: Mapping[str, Any]) -> bool:
    return _workstream_signal_counter(row, "direct_exact", "trace_code_exact") > 0

def _workstream_has_path_signal(row: Mapping[str, Any]) -> bool:
    return _workstream_signal_counter(
        row,
        "direct_exact",
        "direct_watch",
        "trace_code_exact",
        "trace_code_watch",
        "trace_doc_exact",
        "trace_doc_watch",
        "trace_runbook_exact",
        "trace_runbook_watch",
    ) > 0

def _workstream_lineage_neighbor_ids(row: Mapping[str, Any]) -> set[str]:
    values = {
        str(row.get("workstream_parent", "")).strip().upper(),
        *[str(token).strip().upper() for token in row.get("workstream_children", []) if str(token).strip()],
    }
    values.update(_workstream_lineage_tokens(row, "workstream_reopens", "workstream_reopened_by", "supersedes", "superseded_by"))
    return {token for token in values if token}

def _rerank_workstream_candidates(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    reranked = [dict(row) for row in rows]
    reranked.sort(
        key=lambda row: (
            -_workstream_evidence_score(row),
            -int(dict(row.get("evidence", {})).get("strong_signal_count", 0) or 0),
            _workstream_status_rank(str(row.get("status", ""))),
            str(row.get("entity_id", "")),
        )
    )
    for index, row in enumerate(reranked, start=1):
        row["rank"] = index
    return reranked

def _prune_low_precision_workstream_candidates(candidates: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [dict(candidate) for candidate in candidates]
    if len(rows) <= 3:
        return rows
    strong_rows = [
        row
        for row in rows
        if int(dict(row.get("evidence", {})).get("strong_signal_count", 0) or 0) > 0
        and not bool(dict(row.get("evidence", {})).get("broad_only"))
    ]
    if not strong_rows:
        positive_rows = [row for row in rows if _workstream_evidence_score(row) > 0]
        return _rerank_workstream_candidates(positive_rows or rows)
    top_strong_score = max(_workstream_evidence_score(row) for row in strong_rows)
    exact_rows = [row for row in strong_rows if _workstream_has_exact_path_signal(row)]
    kept_ids: set[str] = set()
    if exact_rows:
        threshold = max(_WORKSTREAM_SELECTION_CONFIDENT_SCORE, top_strong_score - 80)
        for row in exact_rows:
            if _workstream_evidence_score(row) >= threshold:
                kept_ids.add(str(row.get("entity_id", "")).strip().upper())
        if not kept_ids:
            kept_ids.add(str(exact_rows[0].get("entity_id", "")).strip().upper())
    else:
        threshold = max(_WORKSTREAM_SELECTION_CONFIDENT_SCORE, top_strong_score - 48)
        for row in strong_rows:
            if _workstream_evidence_score(row) >= threshold and _workstream_has_path_signal(row):
                kept_ids.add(str(row.get("entity_id", "")).strip().upper())
        if not kept_ids and strong_rows:
            kept_ids.add(str(strong_rows[0].get("entity_id", "")).strip().upper())
    if kept_ids:
        changed = True
        while changed:
            changed = False
            for row in rows:
                row_id = str(row.get("entity_id", "")).strip().upper()
                if not row_id or row_id in kept_ids:
                    continue
                if _workstream_lineage_neighbor_ids(row).intersection(kept_ids):
                    kept_ids.add(row_id)
                    changed = True
        filtered = [row for row in rows if str(row.get("entity_id", "")).strip().upper() in kept_ids]
        if filtered:
            rows = filtered
    positive_rows = [row for row in rows if _workstream_evidence_score(row) > 0]
    return _rerank_workstream_candidates(positive_rows or rows)

def _path_profiles(changed_paths: Sequence[str]) -> list[dict[str, Any]]:
    return [_path_signal_profile(path_ref) for path_ref in changed_paths if str(path_ref).strip()]

def _broad_shared_only_input(changed_paths: Sequence[str]) -> bool:
    profiles = _path_profiles(changed_paths)
    return bool(profiles) and all(bool(profile.get("shared")) for profile in profiles)

def _limit_strings(values: Sequence[str], *, limit: int) -> tuple[list[str], dict[str, Any]]:
    normalized = [str(token).strip() for token in values if str(token).strip()]
    limited = normalized[: max(1, int(limit))]
    return limited, {
        "total": len(normalized),
        "returned": len(limited),
        "truncated": len(limited) < len(normalized),
    }

def _limit_mappings(values: Sequence[Mapping[str, Any]], *, limit: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    normalized = [dict(row) for row in values if isinstance(row, Mapping)]
    limited = normalized[: max(1, int(limit))]
    return limited, {
        "total": len(normalized),
        "returned": len(limited),
        "truncated": len(limited) < len(normalized),
    }

def _truncate_text_for_packet(text: str, *, max_chars: int = 220) -> str:
    normalized = " ".join(str(text or "").strip().split())
    if len(normalized) <= max_chars:
        return normalized
    clipped = normalized[: max(0, max_chars - 1)].rstrip()
    return f"{clipped}…"

def _compact_component_row_for_packet(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "entity_id": str(row.get("entity_id", "")).strip(),
        "title": str(row.get("title", "")).strip(),
        "path": str(row.get("path", "")).strip(),
    }

def _compact_diagram_row_for_packet(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "diagram_id": str(row.get("diagram_id", "")).strip(),
        "title": str(row.get("title", "")).strip(),
        "source_mmd": str(row.get("source_mmd", "")).strip(),
    }

def _compact_test_row_for_packet(row: Mapping[str, Any]) -> dict[str, Any]:
    compact = {
        "path": str(row.get("path", row.get("test_path", ""))).strip(),
        "test_path": str(row.get("test_path", row.get("path", ""))).strip(),
        "nodeid": str(row.get("nodeid", "")).strip(),
        "reason": _truncate_text_for_packet(str(row.get("reason", "")).strip(), max_chars=160),
    }
    metadata = row.get("metadata", {})
    history = row.get("history", {})
    if not isinstance(history, Mapping) and isinstance(metadata, Mapping):
        history = metadata.get("history", {})
    if isinstance(history, Mapping) and (
        bool(history.get("recent_failure"))
        or int(history.get("failure_count", 0) or 0) > 0
        or str(history.get("last_failure_utc", "")).strip()
    ):
        compact["history"] = {
            "recent_failure": bool(history.get("recent_failure")),
            "failure_count": int(history.get("failure_count", 0) or 0),
            "last_failure_utc": str(history.get("last_failure_utc", "")).strip(),
            "sources": [
                str(token).strip()
                for token in history.get("sources", [])[:3]
                if str(token).strip()
            ]
            if isinstance(history.get("sources"), list)
            else [],
        }
    return {
        key: value
        for key, value in compact.items()
        if value not in ("", [], {}, None)
    }

def _compact_engineering_note_row_for_packet(row: Mapping[str, Any]) -> dict[str, Any]:
    compact = {
        "note_id": str(row.get("note_id", "")).strip(),
        "kind": str(row.get("kind", row.get("note_kind", ""))).strip(),
        "title": str(row.get("title", "")).strip(),
        "source_path": str(row.get("source_path", "")).strip(),
        "summary": _truncate_text_for_packet(str(row.get("summary", "")).strip(), max_chars=180),
        "components": [
            str(token).strip()
            for token in row.get("components", [])[:3]
            if str(token).strip()
        ]
        if isinstance(row.get("components"), list)
        else [],
        "workstreams": [
            str(token).strip()
            for token in row.get("workstreams", [])[:3]
            if str(token).strip()
        ]
        if isinstance(row.get("workstreams"), list)
        else [],
        "matched_by": [
            str(token).strip()
            for token in row.get("matched_by", [])[:3]
            if str(token).strip()
        ]
        if isinstance(row.get("matched_by"), list)
        else [],
        "matched_paths": [
            str(token).strip()
            for token in row.get("matched_paths", [])[:2]
            if str(token).strip()
        ]
        if isinstance(row.get("matched_paths"), list)
        else [],
    }
    relevance = row.get("relevance", {})
    if isinstance(relevance, Mapping):
        relevance_summary = {
            "exact_path_hits": int(relevance.get("exact_path_hits", 0) or 0),
            "component_hits": int(relevance.get("component_hits", 0) or 0),
            "workstream_hits": int(relevance.get("workstream_hits", 0) or 0),
        }
        if any(bool(value) for value in relevance_summary.values()):
            compact["relevance"] = relevance_summary
    metadata = row.get("metadata", {})
    source_mode = str(row.get("source_mode", "")).strip()
    chunk_path = str(row.get("chunk_path", "")).strip()
    chunk_id = str(row.get("chunk_id", "")).strip()
    canonical_source = str(row.get("canonical_source", "")).strip()
    canonical_section = str(row.get("canonical_section", "")).strip()
    task_families = (
        [str(token).strip() for token in row.get("task_families", [])[:3] if str(token).strip()]
        if isinstance(row.get("task_families"), list)
        else []
    )
    if isinstance(metadata, Mapping):
        if not source_mode:
            source_mode = str(metadata.get("source_mode", "")).strip()
        if not chunk_path:
            chunk_path = str(metadata.get("chunk_path", "")).strip()
        if not chunk_id:
            chunk_id = str(metadata.get("chunk_id", "")).strip()
        if not canonical_source:
            canonical_source = str(metadata.get("canonical_source", "")).strip()
        if not canonical_section:
            canonical_section = str(metadata.get("canonical_section", "")).strip()
        if not task_families and isinstance(metadata.get("task_families"), list):
            task_families = [
                str(token).strip()
                for token in metadata.get("task_families", [])[:3]
                if str(token).strip()
            ]
        if source_mode == "guidance_chunk":
            compact["source_mode"] = "guidance_chunk"
            compact["chunk_path"] = chunk_path
            compact["guidance_chunk"] = {
                "chunk_id": chunk_id,
                "canonical_source": canonical_source,
                "canonical_section": canonical_section,
                "risk_class": str(metadata.get("risk_class", row.get("risk_class", ""))).strip(),
            }
            compact["chunk_id"] = chunk_id
            compact["canonical_source"] = canonical_source
            if task_families:
                compact["task_families"] = task_families
        elif str(metadata.get("schema_id", "")).strip():
            compact["schema_id"] = str(metadata.get("schema_id", "")).strip()
    elif source_mode == "guidance_chunk":
        compact["source_mode"] = "guidance_chunk"
        compact["chunk_path"] = chunk_path
        compact["chunk_id"] = chunk_id
        compact["canonical_source"] = canonical_source
        if task_families:
            compact["task_families"] = task_families
        compact["guidance_chunk"] = {
            "chunk_id": chunk_id,
            "canonical_source": canonical_source,
            "canonical_section": canonical_section,
            "risk_class": str(row.get("risk_class", "")).strip(),
        }
    return {
        key: value
        for key, value in compact.items()
        if value not in ("", [], {}, None)
    }

def _compact_engineering_notes(
    notes: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    total_limit: int,
    per_kind_limit: int,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    budget = max(1, int(total_limit))
    per_kind = max(1, int(per_kind_limit))
    compact: dict[str, list[dict[str, Any]]] = {}
    per_kind_meta: dict[str, dict[str, Any]] = {}
    total_source = 0
    total_returned = 0
    for kind in _ENGINEERING_NOTE_KINDS:
        rows = notes.get(kind, [])
        if not isinstance(rows, list) or not rows:
            continue
        total_source += len(rows)
        if budget <= 0:
            per_kind_meta[kind] = {"total": len(rows), "returned": 0, "truncated": True}
            continue
        allowed = min(per_kind, budget)
        selected = [_compact_engineering_note_row_for_packet(row) for row in rows[:allowed] if isinstance(row, Mapping)]
        if selected:
            compact[kind] = selected
            total_returned += len(selected)
            budget -= len(selected)
        per_kind_meta[kind] = {
            "total": len(rows),
            "returned": len(selected),
            "truncated": len(selected) < len(rows),
        }
    return compact, {
        "total": total_source,
        "returned": total_returned,
        "truncated": total_returned < total_source,
        "per_kind": per_kind_meta,
    }

def _compact_budget_meta_for_summary(budget: Mapping[str, Any]) -> dict[str, Any]:
    keep = (
        "packet_kind",
        "packet_state",
        "max_bytes",
        "max_tokens",
        "content_max_bytes",
        "content_max_tokens",
        "meta_reserve_bytes",
        "meta_reserve_tokens",
    )
    return {
        key: budget.get(key)
        for key in keep
        if budget.get(key) not in (None, "", [], {})
    }

def _compact_packet_metrics_for_summary(metrics: Mapping[str, Any]) -> dict[str, Any]:
    compact = {
        "estimated_bytes": int(metrics.get("estimated_bytes", 0) or 0),
        "estimated_tokens": int(metrics.get("estimated_tokens", 0) or 0),
        "budget_bytes": int(metrics.get("budget_bytes", 0) or 0),
        "budget_tokens": int(metrics.get("budget_tokens", 0) or 0),
        "within_budget": bool(metrics.get("within_budget")),
    }
    sections = metrics.get("sections", {})
    if isinstance(sections, Mapping):
        compact["sections"] = {
            "total": int(sections.get("total", 0) or 0),
            "largest": [
                {
                    "section": str(row.get("section", "")).strip(),
                    "estimated_bytes": int(row.get("estimated_bytes", 0) or 0),
                    "item_count": int(row.get("item_count", 0) or 0),
                }
                for row in sections.get("largest", [])
                if isinstance(row, Mapping) and str(row.get("section", "")).strip()
            ][:4]
            if isinstance(sections.get("largest"), list)
            else [],
        }
    return compact

def _compact_truncation_for_summary(truncation: Mapping[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for key in ("candidate_workstreams", "docs", "recommended_commands", "recommended_tests", "engineering_notes"):
        row = truncation.get(key)
        if not isinstance(row, Mapping):
            continue
        summary[key] = {
            "total": int(row.get("total", 0) or 0),
            "returned": int(row.get("returned", 0) or 0),
            "truncated": bool(row.get("truncated")),
        }
    packet_budget = truncation.get("packet_budget")
    if isinstance(packet_budget, Mapping):
        summary["packet_budget"] = {
            "applied": bool(packet_budget.get("applied")),
            "truncated": bool(packet_budget.get("truncated")),
            "step_count": int(packet_budget.get("step_count", 0) or 0),
            "within_budget_after_finalize": bool(packet_budget.get("within_budget_after_finalize")),
        }
    return summary

def _compact_runtime_timing_rows_for_packet(
    rows: Sequence[Mapping[str, Any]] | Mapping[str, Any],
    *,
    limit: int = 6,
) -> dict[str, Any]:
    recent_rows = rows.get("recent", []) if isinstance(rows, Mapping) else rows
    operations = rows.get("operations", []) if isinstance(rows, Mapping) else []
    compact: list[dict[str, Any]] = []
    for row in recent_rows[: max(1, int(limit))] if isinstance(recent_rows, list) else []:
        if not isinstance(row, Mapping):
            continue
        compact.append(
            {
                "category": str(row.get("category", "")).strip(),
                "operation": str(row.get("operation", "")).strip(),
                "duration_ms": round(float(row.get("duration_ms", 0.0) or 0.0), 3),
                "recorded_utc": str(row.get("recorded_utc", row.get("ts_iso", ""))).strip(),
            }
        )
    return {
        "recent": compact,
        "operations": [
            {
                "category": str(row.get("category", "")).strip(),
                "operation": str(row.get("operation", "")).strip(),
                "count": int(row.get("count", 0) or 0),
                "latest_ms": round(float(row.get("latest_ms", 0.0) or 0.0), 3),
                "avg_ms": round(float(row.get("avg_ms", 0.0) or 0.0), 3),
            }
            for row in operations[: max(1, int(limit // 2 or 1))]
            if isinstance(row, Mapping)
        ]
        if isinstance(operations, list)
        else [],
        "operation_count": len(operations) if isinstance(operations, list) else 0,
    }

def _impact_packet_state(*, shared_only: bool, selection_state: str) -> str:
    if shared_only:
        return "gated_broad_scope"
    if selection_state == "explicit":
        return "compact"
    if selection_state in {"ambiguous", "none"}:
        return "gated_ambiguous"
    return "compact"

def _impact_budget_profile(*, shared_only: bool, selection_state: str) -> dict[str, int]:
    if shared_only:
        return {
            "workstreams": _IMPACT_WORKSTREAM_LIMIT_BROAD,
            "docs": _IMPACT_DOC_LIMIT_BROAD,
            "commands": _IMPACT_COMMAND_LIMIT_BROAD,
            "tests": _IMPACT_TEST_LIMIT_DEFAULT,
            "notes_total": _IMPACT_ENGINEERING_NOTES_TOTAL_LIMIT_BROAD,
            "notes_per_kind": _IMPACT_ENGINEERING_NOTES_PER_KIND_LIMIT_DEFAULT,
        }
    if selection_state == "explicit":
        return {
            "workstreams": _IMPACT_WORKSTREAM_LIMIT_EXPLICIT,
            "docs": _IMPACT_DOC_LIMIT_EXPLICIT,
            "commands": _IMPACT_COMMAND_LIMIT_EXPLICIT,
            "tests": _IMPACT_TEST_LIMIT_EXPLICIT,
            "notes_total": _IMPACT_ENGINEERING_NOTES_TOTAL_LIMIT_EXPLICIT,
            "notes_per_kind": _IMPACT_ENGINEERING_NOTES_PER_KIND_LIMIT_EXPLICIT,
        }
    if selection_state in {"ambiguous", "none"}:
        return {
            "workstreams": _IMPACT_WORKSTREAM_LIMIT_AMBIGUOUS,
            "docs": _IMPACT_DOC_LIMIT_AMBIGUOUS,
            "commands": _IMPACT_COMMAND_LIMIT_AMBIGUOUS,
            "tests": _IMPACT_TEST_LIMIT_AMBIGUOUS,
            "notes_total": _IMPACT_ENGINEERING_NOTES_TOTAL_LIMIT_AMBIGUOUS,
            "notes_per_kind": _IMPACT_ENGINEERING_NOTES_PER_KIND_LIMIT_AMBIGUOUS,
        }
    return {
        "workstreams": _IMPACT_WORKSTREAM_LIMIT_DEFAULT,
        "docs": _IMPACT_DOC_LIMIT_DEFAULT,
        "commands": _IMPACT_COMMAND_LIMIT_DEFAULT,
        "tests": _IMPACT_TEST_LIMIT_DEFAULT,
        "notes_total": _IMPACT_ENGINEERING_NOTES_TOTAL_LIMIT_DEFAULT,
        "notes_per_kind": _IMPACT_ENGINEERING_NOTES_PER_KIND_LIMIT_DEFAULT,
    }

def _component_grounded_selection_none(
    *,
    shared_only_input: bool,
    selection_state: str,
    components: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
    docs: Sequence[str],
    tests: Sequence[Mapping[str, Any]],
    recommended_commands: Sequence[str],
) -> bool:
    if shared_only_input or str(selection_state or "").strip() != "none":
        return False
    return bool(
        any(isinstance(row, Mapping) for row in components)
        or any(isinstance(row, Mapping) for row in diagrams)
        or any(str(token).strip() for token in docs)
        or any(isinstance(row, Mapping) for row in tests)
        or any(str(token).strip() for token in recommended_commands)
    )

def _hot_path_can_stay_fail_closed_without_full_scan(
    *,
    family_hint: str,
    changed_paths: Sequence[str],
    explicit_paths: Sequence[str],
    selection_state: str,
    shared_only_input: bool,
    working_tree_scope_degraded: bool,
) -> bool:
    if working_tree_scope_degraded:
        return False
    family = _normalize_family_hint(family_hint)
    normalized_changed = _normalized_string_list(changed_paths)
    normalized_explicit = _normalized_string_list(explicit_paths)
    exact_path_grounded = bool(normalized_changed) and (
        not normalized_explicit or normalized_changed == normalized_explicit
    )
    if family in {"broad_shared_scope", "architecture"}:
        return shared_only_input and exact_path_grounded and len(normalized_changed) <= 4
    if family == "exact_path_ambiguity":
        return (
            not shared_only_input
            and exact_path_grounded
            and len(normalized_changed) <= 2
            and str(selection_state or "").strip() in {"ambiguous", "none"}
        )
    return False

_PACKET_EXPORTS = (
    "_compact_hot_path_active_conflicts", "_hot_path_keep_architecture_audit", "_hot_path_workstream_selection",
    "_compact_hot_path_workstream_selection", "_compact_hot_path_retrieval_plan", "_compact_hot_path_packet_quality",
    "_compact_hot_path_intent", "_hot_path_signal_score", "_hot_path_synthesized_execution_profile",
    "_hot_path_recomputed_readiness", "_compact_hot_path_routing_handoff", "_compact_hot_path_route_execution_profile",
    "_encode_hot_path_execution_profile", "_decode_hot_path_execution_profile", "_hot_path_execution_profile_runtime_fields",
    "_compact_hot_path_payload_within_budget", "_synthesized_hot_path_execution_profile_from_context_packet",
    "_governance_closeout_doc_count", "_trim_common_hot_path_context_packet", "_compact_hot_path_narrowing_guidance",
    "_source_hot_path_within_budget", "_fast_finalize_compact_hot_path_packet", "_compact_hot_path_packet_metrics",
    "_drop_redundant_hot_path_routing_handoff", "_compact_hot_path_fallback_scan",
    "_compact_governance_validation_bundle_for_hot_path", "_compact_hot_path_surface_reason_token",
    "_compact_governance_obligations_for_hot_path", "_compact_governance_surface_refs_for_hot_path",
    "_compact_governance_signal_for_hot_path", "_embedded_governance_signal", "_hot_path_validation_bundle",
    "_hot_path_governance_obligations", "_validation_bundle_command_count", "_governance_obligation_count",
    "_compact_hot_path_runtime_packet", "_hot_path_payload_is_compact", "_update_compact_hot_path_runtime_packet",
    "_trim_route_ready_hot_path_prompt_payload", "_compact_workstream_metadata_for_packet",
    "_compact_workstream_evidence_for_packet", "_compact_workstream_row_for_packet",
    "_compact_workstream_reference_for_packet", "_compact_workstream_selection_for_packet",
    "_compact_bootstrap_workstream_selection", "_compact_neighbor_row_for_packet", "_prioritized_neighbor_rows",
)

_SCOPE_EXPORTS = (
    "_compact_architecture_audit_for_packet", "_compact_packet_level_architecture_audit", "_workstream_selection",
    "_bug_excerpt", "_session_record_path", "_bootstrap_record_path", "_parse_iso_utc", "_normalize_claim_mode",
    "_lease_expires_utc", "_is_session_expired", "_load_session_state", "_resolve_changed_path_scope_context",
    "_claim_sets", "list_session_states", "register_session_state", "_collect_impacted_components",
    "_collect_impacted_workstreams", "_engineering_note_match", "_collect_relevant_notes",
    "_collect_relevant_bugs", "_collect_code_neighbors", "_collect_recommended_tests",
)

_GOVERNANCE_EXPORTS = (
    "_governance_surface_refs", "_governance_closeout_docs", "_bounded_explicit_governance_closeout_docs",
    "_governance_state_actions", "_governance_requires_architecture_audit", "_governance_diagram_catalog_companions",
    "_companion_context_paths_for_normalized_changed_paths", "_companion_context_paths", "_governance_hot_path_docs",
    "_governance_explicit_slice_grounded", "_governance_can_skip_runtime_warmup", "build_governance_slice",
    "select_impacted_diagrams", "_path_touches_watch",
    "_normalized_watch_path", "_architecture_rule_matches_path", "_collect_topology_domains",
    "_component_matches_changed_path", "_load_architecture_diagrams", "_collect_diagram_watch_gaps",
)

_DELIVERY_EXPORTS = (
    "_impact_summary_payload", "_delivery_profile_hot_path", "_elapsed_stage_ms", "_compact_stage_timings",
    "_normalize_family_hint", "_impact_family_profile", "_hot_path_dashboard_surface_like",
    "_hot_path_routing_confidence_rank", "_hot_path_packet_rank", "_hot_path_auto_escalation_trigger",
    "_hot_path_can_hold_local_narrowing_without_full_scan", "_compact_hot_path_auto_escalation",
    "_hot_path_selected_validation_count", "_hot_path_route_ready", "_hot_path_full_scan_recommended",
    "_hot_path_full_scan_reason", "_hot_path_routing_confidence", "_should_escalate_hot_path_to_session_brief",
    "_fallback_scan_payload", "_compact_hot_path_session_payload", "_compact_hot_path_workstream_context",
    "_compact_code_neighbors_for_packet", "_collect_component_validation_commands", "_recommended_validation_commands",
    "_is_governance_sync_command", "_workstream_status_rank", "_workstream_rank_tuple", "_condense_delivery_scope",
)

for _module, _names in (
    (odylith_context_engine_hot_path_packet_core_runtime, _PACKET_EXPORTS[:25]),
    (odylith_context_engine_hot_path_packet_bootstrap_runtime, _PACKET_EXPORTS[25:35]),
    (odylith_context_engine_hot_path_packet_finalize_runtime, _PACKET_EXPORTS[35:]),
    (odylith_context_engine_hot_path_scope_runtime, _SCOPE_EXPORTS),
    (odylith_context_engine_hot_path_governance_runtime, _GOVERNANCE_EXPORTS),
    (odylith_context_engine_hot_path_delivery_runtime, _DELIVERY_EXPORTS),
):
    globals().update({name: getattr(_module, name) for name in _names})

del _module
del _names
