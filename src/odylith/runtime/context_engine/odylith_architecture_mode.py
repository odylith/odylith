"""Compiled architecture-mode support for the Odylith Context Engine.

Architecture mode should read one deterministic local bundle rather than
reconstructing a shallow audit ad hoc from the wider runtime store. This module
owns:

- topology-domain rules for architecture grounding;
- a compiler-owned architecture bundle written during warmup;
- dossier construction over grounded changed paths using compiled artifacts;
- coverage/confidence scoring and architecture benchmark summaries.
"""

from __future__ import annotations

import datetime as dt
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any, Mapping, Sequence

from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.common import odylith_benchmark_contract
from odylith.runtime.common.consumer_profile import surface_root_path

ARCHITECTURE_BUNDLE_VERSION = "v1"
ARCHITECTURE_BUNDLE_FILENAME = "architecture-bundle.v1.json"
ARCHITECTURE_DOMAIN_FILENAME = "architecture-domains.v1.json"
_DEFAULT_COMPONENT_ALIAS_LIMIT = 8
_DEFAULT_FEATURE_HISTORY_LIMIT = 10
_DEFAULT_VALIDATION_COMMAND_LIMIT = 8
_DEFAULT_ARCHITECTURE_DETAIL_LEVEL = "compact"
_VALID_ARCHITECTURE_DETAIL_LEVELS = frozenset({"full", "compact", "packet"})
_DEFAULT_ARCHITECTURE_BENCHMARK_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "architecture-odylith-self-grounding",
        "match": {
            "paths_any": [
                "src/odylith/runtime/context_engine/odylith_context_engine.py",
                "src/odylith/runtime/context_engine/odylith_context_engine_store.py",
            ],
            "domains_any": ["odylith-context-engine"],
        },
        "expect": {
            "confidence_tier": ["medium", "high"],
            "contract_touchpoints_min": 1,
        },
    },
)
_PROCESS_ARCHITECTURE_BUNDLE_CACHE: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
_PROCESS_ARCHITECTURE_STRUCTURAL_BASE_CACHE: dict[str, dict[str, Any]] = {}
_PROCESS_ARCHITECTURE_STRUCTURAL_CORE_CACHE: dict[str, dict[str, Any]] = {}
_PROCESS_ARCHITECTURE_BENCHMARK_CASES_CACHE: dict[str, tuple[dict[str, Any], list[dict[str, Any]]]] = {}
_PROCESS_ARCHITECTURE_DOMAIN_RULES_CACHE: dict[str, tuple[dict[str, Any], list[dict[str, Any]]]] = {}
_PROCESS_ARCHITECTURE_SOURCE_HASH_CACHE: dict[str, tuple[dict[str, Any], str]] = {}
_PROCESS_ARCHITECTURE_TRACEABILITY_INDEX_CACHE: dict[str, dict[str, Any]] = {}
_PROCESS_ARCHITECTURE_WORKSTREAM_INDEX_CACHE: dict[str, dict[str, Any]] = {}


def _elapsed_ms(started_at: float) -> float:
    return round((time.perf_counter() - started_at) * 1000.0, 3)

TOPOLOGY_DOMAIN_RULES: tuple[dict[str, Any], ...] = (
    {
        "domain_id": "release-install-runtime-boundary",
        "label": "Release / Install Runtime Boundary",
        "summary": "Managed runtime activation and release-owned delivery assets stay grounded against the install contract instead of drifting into unrelated guidance mirrors.",
        "path_prefixes": (
            "src/odylith/install/runtime.py",
            "src/odylith/install/release_assets.py",
            "src/odylith/install/manager.py",
            "odylith/INSTALL_AND_UPGRADE_RUNBOOK.md",
            "odylith/registry/source/components/release/CURRENT_SPEC.md",
        ),
        "components": ("release", "odylith"),
        "required_reads": (
            "odylith/INSTALL_AND_UPGRADE_RUNBOOK.md",
            "odylith/registry/source/components/release/CURRENT_SPEC.md",
            "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
        ),
        "checks": (
            "Keep release publication ownership separate from consumer install semantics and runtime activation behavior.",
            "Treat managed runtime activation, rollback, and repair as install-boundary behavior first, not as commentary or benchmark framing.",
        ),
        "operator_consequences": (
            "If maintainers collapse install runtime, release publication, and chatter-owned guidance into one boundary, repair and rollback decisions become harder to reason about under pressure.",
        ),
        "risk_tier": "moderate",
    },
    {
        "domain_id": "odylith-context-engine",
        "label": "Odylith Context Engine",
        "summary": "Odylith Context Engine accelerates grounded review but never replaces Atlas or topology docs as source of truth.",
        "path_prefixes": (
            "src/odylith/runtime/context_engine/odylith_context_engine.py",
            "src/odylith/runtime/context_engine/odylith_context_engine_store.py",
            "src/odylith/runtime/context_engine/odylith_context_cache.py",
            "odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md",
            "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md",
            "agents-guidelines/TOOLING.MD",
            "agents-guidelines/ARCHITECTURE.MD",
        ),
        "components": ("odylith-context-engine",),
        "required_reads": (
            "agents-guidelines/TOOLING.MD",
            "agents-guidelines/ARCHITECTURE.MD",
            "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md",
            "odylith/atlas/source/odylith-context-and-agent-execution-stack.mmd",
        ),
        "checks": (
            "Treat runtime output as advisory and path-scoped, not as architecture proof.",
            "If runtime packets report watch gaps or full_scan_recommended, fall back to rg plus direct source reads.",
        ),
        "operator_consequences": (
            "If maintainers treat runtime output as proof instead of accelerator guidance, architecture drift will hide behind local convenience.",
        ),
    },
)


def compiler_root(*, repo_root: Path) -> Path:
    return (Path(repo_root).resolve() / ".odylith" / "runtime" / "odylith-compiler").resolve()


def bundle_path(*, repo_root: Path) -> Path:
    return (compiler_root(repo_root=repo_root) / ARCHITECTURE_BUNDLE_FILENAME).resolve()


def topology_domain_path(*, repo_root: Path) -> Path:
    return (
        surface_root_path(repo_root=Path(repo_root).resolve(), key="product_root")
        / "atlas"
        / "source"
        / ARCHITECTURE_DOMAIN_FILENAME
    ).resolve()


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_repo_path(*, repo_root: Path, value: Any) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    root = Path(repo_root).resolve()
    try:
        candidate = Path(token)
        if candidate.is_absolute():
            return candidate.resolve().relative_to(root).as_posix()
    except Exception:
        return token
    return token


def _json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if not isinstance(value, str):
        return {}
    token = value.strip()
    if not token:
        return {}
    try:
        payload = json.loads(token)
    except json.JSONDecodeError:
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def _json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if not isinstance(value, str):
        return []
    token = value.strip()
    if not token:
        return []
    try:
        payload = json.loads(token)
    except json.JSONDecodeError:
        return []
    return list(payload) if isinstance(payload, list) else []


def _dedupe_strings(values: Sequence[Any]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = str(raw or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _normalize_detail_level(value: Any) -> str:
    token = str(value or "").strip().lower()
    if token in _VALID_ARCHITECTURE_DETAIL_LEVELS:
        return token
    return _DEFAULT_ARCHITECTURE_DETAIL_LEVEL


@lru_cache(maxsize=16384)
def _normalized_watch_path(value: str) -> str:
    token = str(value or "").strip().replace("\\", "/")
    while token.startswith("./"):
        token = token[2:]
    while "//" in token:
        token = token.replace("//", "/")
    return token.rstrip("/")


def _path_touches_watch(*, changed_path: str, watch_path: str) -> bool:
    changed = _normalized_watch_path(str(changed_path))
    watch = _normalized_watch_path(str(watch_path))
    return changed == watch or changed.startswith(f"{watch}/") or watch.startswith(f"{changed}/")


def _normalize_component_specs(
    *,
    repo_root: Path,
    tables: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    specs: dict[str, dict[str, Any]] = {}
    for row in tables.get("component_specs", []):
        if not isinstance(row, Mapping):
            continue
        component_id = str(row.get("component_id", "")).strip()
        if not component_id:
            continue
        feature_history = [
            dict(item)
            for item in _json_list(row.get("feature_history_json"))
            if isinstance(item, Mapping)
        ][:_DEFAULT_FEATURE_HISTORY_LIMIT]
        validation_commands = []
        for command in _json_list(row.get("validation_playbook_commands_json"))[:_DEFAULT_VALIDATION_COMMAND_LIMIT]:
            if not isinstance(command, Mapping):
                continue
            validation_commands.append(
                {
                    "command": str(command.get("command", "")).strip(),
                    "description": str(command.get("description", "")).strip(),
                    "group": str(command.get("group", "")).strip(),
                }
            )
        specs[component_id] = {
            "title": str(row.get("title", "")).strip(),
            "last_updated": str(row.get("last_updated", "")).strip(),
            "feature_history": feature_history,
            "validation_commands": validation_commands,
        }
    return specs


def _normalize_component_traceability(
    *,
    repo_root: Path,
    tables: Mapping[str, Any],
) -> dict[str, dict[str, list[str]]]:
    results: dict[str, dict[str, list[str]]] = {}
    for row in tables.get("component_traceability", []):
        if not isinstance(row, Mapping):
            continue
        component_id = str(row.get("component_id", "")).strip()
        bucket = str(row.get("bucket", "")).strip()
        path = _normalize_repo_path(repo_root=repo_root, value=row.get("path"))
        if not component_id or not bucket or not path:
            continue
        results.setdefault(component_id, {}).setdefault(bucket, [])
        if path not in results[component_id][bucket]:
            results[component_id][bucket].append(path)
    return results


def _normalize_components(
    *,
    repo_root: Path,
    tables: Mapping[str, Any],
) -> list[dict[str, Any]]:
    specs = _normalize_component_specs(repo_root=repo_root, tables=tables)
    traceability = _normalize_component_traceability(repo_root=repo_root, tables=tables)
    rows: list[dict[str, Any]] = []
    for row in tables.get("components", []):
        if not isinstance(row, Mapping):
            continue
        component_id = str(row.get("component_id", "")).strip()
        if not component_id:
            continue
        metadata = _json_dict(row.get("metadata_json"))
        spec = specs.get(component_id, {})
        aliases = _dedupe_strings((_json_list(row.get("aliases_json")) or metadata.get("aliases", []))[:_DEFAULT_COMPONENT_ALIAS_LIMIT])
        diagrams = _dedupe_strings(_json_list(row.get("diagrams_json")) or metadata.get("diagrams", []))
        workstreams = _dedupe_strings(_json_list(row.get("workstreams_json")) or metadata.get("workstreams", []))
        path_prefixes = _dedupe_strings(metadata.get("path_prefixes", [])) if isinstance(metadata.get("path_prefixes"), list) else []
        rows.append(
            {
                "component_id": component_id,
                "title": str(row.get("name", "")).strip() or str(spec.get("title", "")).strip() or component_id,
                "path": _normalize_repo_path(repo_root=repo_root, value=row.get("spec_ref") or metadata.get("spec_ref"))
                or (path_prefixes[0] if path_prefixes else ""),
                "owner": str(row.get("owner", "")).strip() or str(metadata.get("owner", "")).strip(),
                "status": str(row.get("status", "")).strip() or str(metadata.get("status", "")).strip(),
                "spec_ref": _normalize_repo_path(repo_root=repo_root, value=row.get("spec_ref") or metadata.get("spec_ref")),
                "product_layer": str(metadata.get("product_layer", "")).strip(),
                "path_prefixes": path_prefixes,
                "aliases": aliases,
                "diagrams": diagrams,
                "workstreams": workstreams,
                "what_it_is": str(metadata.get("what_it_is", "")).strip(),
                "why_tracked": str(metadata.get("why_tracked", "")).strip(),
                "traceability": traceability.get(component_id, {}),
                "feature_history": list(spec.get("feature_history", [])),
                "validation_commands": list(spec.get("validation_commands", [])),
            }
        )
    return rows


def _normalize_diagrams(
    *,
    repo_root: Path,
    tables: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    watch_map: dict[str, list[str]] = {}
    for row in tables.get("diagram_watch_paths", []):
        if not isinstance(row, Mapping):
            continue
        diagram_id = str(row.get("diagram_id", "")).strip()
        watch_path = _normalize_repo_path(repo_root=repo_root, value=row.get("watch_path"))
        if diagram_id and watch_path:
            watch_map.setdefault(diagram_id, []).append(watch_path)
    for row in tables.get("diagrams", []):
        if not isinstance(row, Mapping):
            continue
        diagram_id = str(row.get("diagram_id", "")).strip()
        if not diagram_id:
            continue
        metadata = _json_dict(row.get("metadata_json"))
        source_mmd = _normalize_repo_path(repo_root=repo_root, value=row.get("source_mmd") or metadata.get("source_mmd"))
        rows.append(
            {
                "diagram_id": diagram_id,
                "title": str(row.get("title", "")).strip() or str(metadata.get("title", "")).strip(),
                "summary": str(row.get("summary", "")).strip() or str(metadata.get("summary", "")).strip(),
                "owner": str(row.get("owner", "")).strip() or str(metadata.get("owner", "")).strip(),
                "path": source_mmd,
                "source_mmd": source_mmd,
                "source_mmd_hash": str(row.get("source_mmd_hash", "")).strip(),
                "source_svg": _normalize_repo_path(repo_root=repo_root, value=row.get("source_svg") or metadata.get("source_svg")),
                "source_png": _normalize_repo_path(repo_root=repo_root, value=row.get("source_png") or metadata.get("source_png")),
                "watch_paths": _dedupe_strings(watch_map.get(diagram_id, []) or metadata.get("change_watch_paths", [])),
                "related_component_ids": _dedupe_strings(metadata.get("related_component_ids", [])),
                "related_docs": _dedupe_strings(
                    _normalize_repo_path(repo_root=repo_root, value=item) for item in metadata.get("related_docs", [])
                ),
                "related_workstreams": _dedupe_strings(metadata.get("related_workstreams", [])),
            }
        )
    return rows


def _normalize_workstreams(
    *,
    repo_root: Path,
    tables: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in tables.get("workstreams", []):
        if not isinstance(row, Mapping):
            continue
        workstream_id = str(row.get("idea_id", "")).strip().upper()
        if not workstream_id:
            continue
        rows.append(
            {
                "workstream_id": workstream_id,
                "title": str(row.get("title", "")).strip(),
                "status": str(row.get("status", "")).strip(),
                "priority": str(row.get("priority", "")).strip(),
                "source_path": _normalize_repo_path(repo_root=repo_root, value=row.get("source_path")),
                "idea_file": _normalize_repo_path(repo_root=repo_root, value=row.get("idea_file")),
                "promoted_to_plan": _normalize_repo_path(repo_root=repo_root, value=row.get("promoted_to_plan")),
            }
        )
    return rows


def _normalize_bugs(
    *,
    repo_root: Path,
    tables: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in tables.get("bugs", []):
        if not isinstance(row, Mapping):
            continue
        bug_key = str(row.get("bug_key", "")).strip()
        if not bug_key:
            continue
        rows.append(
            {
                "bug_id": str(row.get("bug_id", "")).strip(),
                "bug_key": bug_key,
                "title": str(row.get("title", "")).strip(),
                "status": str(row.get("status", "")).strip(),
                "severity": str(row.get("severity", "")).strip(),
                "source_path": _normalize_repo_path(repo_root=repo_root, value=row.get("source_path")),
                "components": str(row.get("components", "")).strip(),
                "search_body": str(row.get("search_body", "")).strip(),
            }
        )
    return rows


def _normalize_engineering_notes(
    *,
    repo_root: Path,
    tables: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in tables.get("engineering_notes", []):
        if not isinstance(row, Mapping):
            continue
        rows.append(
            {
                "note_id": str(row.get("note_id", "")).strip(),
                "kind": str(row.get("kind", "")).strip(),
                "title": str(row.get("title", "")).strip(),
                "source_path": _normalize_repo_path(repo_root=repo_root, value=row.get("source_path")),
                "summary": str(row.get("summary", "")).strip(),
                "tags": _dedupe_strings(_json_list(row.get("tags_json"))),
            }
        )
    return rows


def _normalize_tests(
    *,
    repo_root: Path,
    tables: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in tables.get("test_cases", []):
        if not isinstance(row, Mapping):
            continue
        rows.append(
            {
                "test_id": str(row.get("test_id", "")).strip(),
                "test_path": _normalize_repo_path(repo_root=repo_root, value=row.get("test_path")),
                "test_name": str(row.get("test_name", "")).strip(),
                "node_id": str(row.get("node_id", "")).strip(),
                "target_paths": _dedupe_strings(
                    _normalize_repo_path(repo_root=repo_root, value=item)
                    for item in _json_list(row.get("target_paths_json"))
                ),
            }
        )
    return rows


def _normalize_code_contracts(
    *,
    repo_root: Path,
    tables: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in tables.get("code_artifacts", []):
        if not isinstance(row, Mapping):
            continue
        path = _normalize_repo_path(repo_root=repo_root, value=row.get("path"))
        if not path:
            continue
        refs = _dedupe_strings(
            _normalize_repo_path(repo_root=repo_root, value=item)
            for item in _json_list(row.get("contract_refs_json"))
        )
        if not refs:
            continue
        rows.append({"path": path, "contract_refs": refs})
    return rows


def _normalize_traceability_edges(
    *,
    repo_root: Path,
    tables: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in tables.get("traceability_edges", []):
        if not isinstance(row, Mapping):
            continue
        rows.append(
            {
                "source_kind": str(row.get("source_kind", "")).strip(),
                "source_id": str(row.get("source_id", "")).strip(),
                "source_path": _normalize_repo_path(repo_root=repo_root, value=row.get("source_path")),
                "relation": str(row.get("relation", "")).strip(),
                "target_kind": str(row.get("target_kind", "")).strip(),
                "target_id": _normalize_repo_path(repo_root=repo_root, value=row.get("target_id")),
            }
        )
    return rows


def build_architecture_bundle(
    *,
    repo_root: Path,
    tables: Mapping[str, Any],
    projection_fingerprint: str,
    projection_scope: str,
    input_fingerprint: str,
    source: str = "projection_snapshot_compile",
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    compiler = compiler_root(repo_root=root)
    compiler.mkdir(parents=True, exist_ok=True)
    topology_domain_rules = _load_topology_domain_rules(repo_root=root)
    payload = {
        "version": ARCHITECTURE_BUNDLE_VERSION,
        "compiled_utc": _utc_now(),
        "ready": True,
        "source": str(source).strip() or "projection_snapshot_compile",
        "projection_fingerprint": str(projection_fingerprint).strip(),
        "projection_scope": str(projection_scope).strip().lower() or "default",
        "input_fingerprint": str(input_fingerprint).strip(),
        "topology_domains": [dict(rule) for rule in topology_domain_rules],
        "components": _normalize_components(repo_root=root, tables=tables),
        "diagrams": _normalize_diagrams(repo_root=root, tables=tables),
        "workstreams": _normalize_workstreams(repo_root=root, tables=tables),
        "bugs": _normalize_bugs(repo_root=root, tables=tables),
        "engineering_notes": _normalize_engineering_notes(repo_root=root, tables=tables),
        "tests": _normalize_tests(repo_root=root, tables=tables),
        "code_contracts": _normalize_code_contracts(repo_root=root, tables=tables),
        "traceability_edges": _normalize_traceability_edges(repo_root=root, tables=tables),
    }
    payload["counts"] = {
        "components": len(payload["components"]),
        "diagrams": len(payload["diagrams"]),
        "workstreams": len(payload["workstreams"]),
        "bugs": len(payload["bugs"]),
        "engineering_notes": len(payload["engineering_notes"]),
        "tests": len(payload["tests"]),
        "code_contracts": len(payload["code_contracts"]),
        "traceability_edges": len(payload["traceability_edges"]),
    }
    odylith_context_cache.write_json_if_changed(
        repo_root=root,
        path=bundle_path(repo_root=root),
        payload=payload,
        lock_key=str(bundle_path(repo_root=root)),
    )
    return payload


def load_architecture_bundle(*, repo_root: Path) -> dict[str, Any]:
    target = bundle_path(repo_root=repo_root)
    cache_key = str(target)
    signature = odylith_context_cache.path_signature(target)
    cached = _PROCESS_ARCHITECTURE_BUNDLE_CACHE.get(cache_key)
    if cached is not None and cached[0] == signature:
        return dict(cached[1])
    payload = odylith_context_cache.read_json_object(target)
    _PROCESS_ARCHITECTURE_BUNDLE_CACHE[cache_key] = (signature, dict(payload))
    return payload


def _architecture_bundle_signature(*, repo_root: Path, bundle: Mapping[str, Any]) -> str:
    target = bundle_path(repo_root=repo_root)
    return odylith_context_cache.fingerprint_payload(
        {
            "path": str(target),
            "signature": odylith_context_cache.path_signature(target),
            "version": str(bundle.get("version", "")).strip(),
            "projection_fingerprint": str(bundle.get("projection_fingerprint", "")).strip(),
            "input_fingerprint": str(bundle.get("input_fingerprint", "")).strip(),
            "record_counts": dict(bundle.get("record_counts", {})) if isinstance(bundle.get("record_counts"), Mapping) else {},
        }
    )


def _current_source_mmd_hash(path: Path) -> str:
    target = Path(path).resolve()
    cache_key = str(target)
    signature = odylith_context_cache.path_signature(target)
    cached = _PROCESS_ARCHITECTURE_SOURCE_HASH_CACHE.get(cache_key)
    if cached is not None and cached[0] == signature:
        return str(cached[1])
    fingerprint = odylith_context_cache.fingerprint_paths([target]) if target.is_file() else ""
    _PROCESS_ARCHITECTURE_SOURCE_HASH_CACHE[cache_key] = (signature, fingerprint)
    return fingerprint


def _load_topology_domain_rules(*, repo_root: Path) -> list[dict[str, Any]]:
    target = topology_domain_path(repo_root=repo_root)
    cache_key = str(target)
    signature = odylith_context_cache.path_signature(target)
    cached = _PROCESS_ARCHITECTURE_DOMAIN_RULES_CACHE.get(cache_key)
    if cached is not None and cached[0] == signature:
        return [dict(row) for row in cached[1]]
    payload = odylith_context_cache.read_json_object(target) if target.is_file() else {}
    raw_domains = payload.get("domains", []) if isinstance(payload, Mapping) else []
    domains = (
        [dict(row) for row in raw_domains if isinstance(row, Mapping)]
        if isinstance(raw_domains, list) and raw_domains
        else [dict(row) for row in TOPOLOGY_DOMAIN_RULES]
    )
    _PROCESS_ARCHITECTURE_DOMAIN_RULES_CACHE[cache_key] = (signature, [dict(row) for row in domains])
    return domains


def _load_architecture_benchmark_cases(*, repo_root: Path) -> list[dict[str, Any]]:
    corpus_path = surface_root_path(repo_root=repo_root, key="product_root") / "runtime" / "source" / "optimization-evaluation-corpus.v1.json"
    cache_key = str(corpus_path.resolve())
    signature = odylith_context_cache.path_signature(corpus_path)
    cached = _PROCESS_ARCHITECTURE_BENCHMARK_CASES_CACHE.get(cache_key)
    if cached is not None and cached[0] == signature:
        return [dict(row) for row in cached[1]]
    corpus = odylith_context_cache.read_json_object(corpus_path)
    cases = odylith_benchmark_contract.architecture_benchmark_scenarios(corpus)
    if not cases:
        cases = [dict(row) for row in _DEFAULT_ARCHITECTURE_BENCHMARK_CASES]
    _PROCESS_ARCHITECTURE_BENCHMARK_CASES_CACHE[cache_key] = (signature, [dict(row) for row in cases])
    return cases


def _architecture_benchmark_cases_hash(*, repo_root: Path) -> str:
    corpus_path = surface_root_path(repo_root=repo_root, key="product_root") / "runtime" / "source" / "optimization-evaluation-corpus.v1.json"
    if corpus_path.is_file():
        return odylith_context_cache.fingerprint_paths([corpus_path])
    return "default"


def _path_watch_candidates(changed_paths: Sequence[str]) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for raw in changed_paths:
        token = Path(str(raw or "").strip()).as_posix().strip()
        if not token:
            continue
        current = Path(token)
        for candidate in (current, *current.parents):
            candidate_token = candidate.as_posix().strip()
            if not candidate_token or candidate_token == "." or candidate_token in seen:
                continue
            seen.add(candidate_token)
            candidates.append(candidate_token)
    return candidates


def _traceability_edge_index(
    *,
    repo_root: Path,
    bundle: Mapping[str, Any],
) -> dict[str, Any]:
    bundle_signature = _architecture_bundle_signature(repo_root=repo_root, bundle=bundle)
    cached = _PROCESS_ARCHITECTURE_TRACEABILITY_INDEX_CACHE.get(bundle_signature)
    if cached is not None:
        return cached
    by_source_id: dict[str, list[dict[str, Any]]] = {}
    by_target_id: dict[str, list[dict[str, Any]]] = {}
    by_source_path: dict[str, list[dict[str, Any]]] = {}
    for raw in bundle.get("traceability_edges", []):
        if not isinstance(raw, Mapping):
            continue
        edge = dict(raw)
        source_id = str(edge.get("source_id", "")).strip()
        target_id = str(edge.get("target_id", "")).strip()
        source_path = Path(str(edge.get("source_path", "")).strip()).as_posix().strip()
        if source_id:
            by_source_id.setdefault(source_id, []).append(edge)
        if target_id:
            by_target_id.setdefault(target_id, []).append(edge)
        if source_path:
            by_source_path.setdefault(source_path, []).append(edge)
    payload = {
        "by_source_id": by_source_id,
        "by_target_id": by_target_id,
        "by_source_path": by_source_path,
    }
    _PROCESS_ARCHITECTURE_TRACEABILITY_INDEX_CACHE[bundle_signature] = payload
    return payload


def _workstream_index(
    *,
    repo_root: Path,
    bundle: Mapping[str, Any],
) -> dict[str, Any]:
    bundle_signature = _architecture_bundle_signature(repo_root=repo_root, bundle=bundle)
    cached = _PROCESS_ARCHITECTURE_WORKSTREAM_INDEX_CACHE.get(bundle_signature)
    if cached is not None:
        return cached
    by_id: dict[str, dict[str, Any]] = {}
    by_watch_path: dict[str, list[dict[str, Any]]] = {}
    for raw in bundle.get("workstreams", []):
        if not isinstance(raw, Mapping):
            continue
        row = dict(raw)
        workstream_id = str(row.get("workstream_id", "")).strip().upper()
        if workstream_id:
            by_id[workstream_id] = row
        for path_field in ("source_path", "idea_file", "promoted_to_plan"):
            token = Path(str(row.get(path_field, "")).strip()).as_posix().strip()
            if token:
                by_watch_path.setdefault(token, []).append(row)
    payload = {
        "by_id": by_id,
        "by_watch_path": by_watch_path,
    }
    _PROCESS_ARCHITECTURE_WORKSTREAM_INDEX_CACHE[bundle_signature] = payload
    return payload


def _relevant_traceability_edges(
    *,
    repo_root: Path,
    bundle: Mapping[str, Any],
    changed_paths: Sequence[str],
    seed_tokens: Sequence[str],
) -> list[dict[str, Any]]:
    index = _traceability_edge_index(repo_root=repo_root, bundle=bundle)
    candidates: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str, str, str, str]] = set()

    def add_rows(rows: Sequence[Mapping[str, Any]]) -> None:
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            edge = dict(row)
            edge_key = (
                str(edge.get("source_kind", "")).strip(),
                str(edge.get("source_id", "")).strip(),
                str(edge.get("target_kind", "")).strip(),
                str(edge.get("target_id", "")).strip(),
                Path(str(edge.get("source_path", "")).strip()).as_posix().strip(),
            )
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)
            candidates.append(edge)

    for token in {str(item).strip() for item in seed_tokens if str(item).strip()}:
        add_rows(index.get("by_source_id", {}).get(token, []))
        add_rows(index.get("by_target_id", {}).get(token, []))
    for candidate in _path_watch_candidates(changed_paths):
        add_rows(index.get("by_source_path", {}).get(candidate, []))
    return candidates


def prime_architecture_projection_cache(*, repo_root: Path) -> None:
    root = Path(repo_root).resolve()
    bundle = load_architecture_bundle(repo_root=root)
    if not bool(bundle.get("ready")):
        return
    _load_architecture_benchmark_cases(repo_root=root)
    _traceability_edge_index(repo_root=root, bundle=bundle)
    _workstream_index(repo_root=root, bundle=bundle)


def _cached_architecture_structural_base(
    *,
    repo_root: Path,
    bundle: Mapping[str, Any],
    changed_paths: Sequence[str],
) -> dict[str, Any]:
    bundle_signature = _architecture_bundle_signature(repo_root=repo_root, bundle=bundle)
    normalized_paths = [str(token).strip() for token in changed_paths if str(token).strip()]
    cache_key = odylith_context_cache.fingerprint_payload(
        {
            "bundle_signature": bundle_signature,
            "changed_paths": normalized_paths,
        }
    )
    cached = _PROCESS_ARCHITECTURE_STRUCTURAL_BASE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    components = [dict(row) for row in bundle.get("components", []) if isinstance(row, Mapping)]
    diagrams = [dict(row) for row in bundle.get("diagrams", []) if isinstance(row, Mapping)]
    workstreams = [dict(row) for row in bundle.get("workstreams", []) if isinstance(row, Mapping)]
    code_contracts = [dict(row) for row in bundle.get("code_contracts", []) if isinstance(row, Mapping)]

    matched_components = _match_components(components=components, changed_paths=normalized_paths)
    topology_domains = _collect_topology_domains(
        changed_paths=normalized_paths,
        component_ids=[str(row.get("component_id", "")).strip() for row in matched_components],
        topology_domain_rules=[dict(row) for row in TOPOLOGY_DOMAIN_RULES],
    )
    direct_diagrams, _covered_paths = _match_diagrams(diagrams=diagrams, changed_paths=normalized_paths)
    component_diagrams = _component_related_diagrams(matched_components=matched_components, diagrams=diagrams)
    linked_diagrams = _merge_diagram_sets(direct_diagrams=direct_diagrams, component_diagrams=component_diagrams)
    diagram_watch_gaps = _collect_diagram_watch_gaps(
        changed_paths=normalized_paths,
        linked_diagrams=linked_diagrams,
        matched_components=matched_components,
    )
    contract_touchpoints = _contract_touchpoints(
        repo_root=repo_root,
        changed_paths=normalized_paths,
        topology_domains=topology_domains,
        matched_components=matched_components,
        diagrams=linked_diagrams,
        code_contracts=code_contracts,
    )
    related_workstreams = _related_workstreams(
        repo_root=repo_root,
        bundle=bundle,
        changed_paths=normalized_paths,
        matched_components=matched_components,
        linked_diagrams=linked_diagrams,
        workstreams=workstreams,
    )
    coverage = _coverage_summary(
        changed_paths=normalized_paths,
        topology_domains=topology_domains,
        matched_components=matched_components,
        linked_diagrams=linked_diagrams,
        contract_touchpoints=contract_touchpoints,
        diagram_watch_gaps=diagram_watch_gaps,
    )
    full_scan_reason = ""
    if diagram_watch_gaps:
        full_scan_reason = "diagram_watch_gap"
    elif not matched_components and not topology_domains and not linked_diagrams:
        full_scan_reason = "topology_unmapped"
    elif str(coverage.get("confidence_tier", "")).strip() == "low" and int(coverage.get("unresolved_edge_count", 0) or 0) > 0:
        full_scan_reason = "coverage_weak"
    include_domain_required_reads = bool(matched_components or linked_diagrams) or any(
        str(path).strip().startswith("src/")
        for path in normalized_paths
        if str(path).strip()
    )
    required_reads = _dedupe_strings(
        [
            *(
                [
                    str(path).strip()
                    for domain in topology_domains
                    for path in domain.get("required_reads", [])
                    if str(path).strip()
                ]
                if include_domain_required_reads
                else []
            ),
            *[
                str(component.get("spec_ref", "")).strip()
                for component in matched_components
                if str(component.get("spec_ref", "")).strip()
            ],
            *[
                str(path.get("path", "")).strip()
                for path in contract_touchpoints
                if str(path.get("kind", "")).strip() in {"developer_doc", "runbook", "component_spec", "diagram_related_doc"}
                and (include_domain_required_reads or str(path.get("source", "")).strip() != "topology_domain")
                and str(path.get("path", "")).strip()
            ],
            *[
                str(diagram.get("path", "")).strip()
                for diagram in linked_diagrams
                if str(diagram.get("path", "")).strip()
            ],
        ]
    )
    required_reads = _prune_secondary_diagram_required_reads(
        changed_paths=normalized_paths,
        matched_components=matched_components,
        topology_domains=topology_domains,
        linked_diagrams=linked_diagrams,
        required_reads=required_reads,
    )
    operator_consequences = _operator_consequences(
        topology_domains=topology_domains,
        matched_components=matched_components,
        historical_bugs=[],
    )
    payload = {
        "matched_components": [dict(row) for row in matched_components],
        "topology_domains": [dict(row) for row in topology_domains],
        "linked_diagrams": [dict(row) for row in linked_diagrams],
        "diagram_watch_gaps": [dict(row) for row in diagram_watch_gaps],
        "contract_touchpoints": [dict(row) for row in contract_touchpoints],
        "related_workstreams": [dict(row) for row in related_workstreams],
        "coverage": dict(coverage),
        "required_reads": list(required_reads),
        "operator_consequences": [dict(row) for row in operator_consequences],
        "full_scan_reason": full_scan_reason,
    }
    _PROCESS_ARCHITECTURE_STRUCTURAL_BASE_CACHE[cache_key] = payload
    return payload


def _architecture_mermaid_drift_hash(
    *,
    repo_root: Path,
    linked_diagrams: Sequence[Mapping[str, Any]],
) -> str:
    root = Path(repo_root).resolve()
    rows: list[dict[str, str]] = []
    for diagram in linked_diagrams:
        source_mmd = _normalize_repo_path(repo_root=root, value=diagram.get("source_mmd"))
        if not source_mmd:
            continue
        rows.append(
            {
                "diagram_id": str(diagram.get("diagram_id", "")).strip(),
                "source_mmd": source_mmd,
                "bundle_hash": str(diagram.get("source_mmd_hash", "")).strip(),
                "current_hash": _current_source_mmd_hash(root / source_mmd),
            }
        )
    rows.sort(key=lambda row: (row["diagram_id"], row["source_mmd"]))
    return odylith_context_cache.fingerprint_payload(rows or [{"diagram_id": "", "source_mmd": "", "bundle_hash": "", "current_hash": ""}])


def _cached_architecture_structural_core(
    *,
    repo_root: Path,
    bundle: Mapping[str, Any],
    changed_paths: Sequence[str],
    tests: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    structural_base = _cached_architecture_structural_base(
        repo_root=repo_root,
        bundle=bundle,
        changed_paths=changed_paths,
    )
    matched_components = [dict(row) for row in structural_base.get("matched_components", []) if isinstance(row, Mapping)]
    topology_domains = [dict(row) for row in structural_base.get("topology_domains", []) if isinstance(row, Mapping)]
    linked_diagrams = [dict(row) for row in structural_base.get("linked_diagrams", []) if isinstance(row, Mapping)]
    diagram_watch_gaps = [dict(row) for row in structural_base.get("diagram_watch_gaps", []) if isinstance(row, Mapping)]
    contract_touchpoints = [dict(row) for row in structural_base.get("contract_touchpoints", []) if isinstance(row, Mapping)]
    related_workstreams = [dict(row) for row in structural_base.get("related_workstreams", []) if isinstance(row, Mapping)]
    coverage = dict(structural_base.get("coverage", {})) if isinstance(structural_base.get("coverage"), Mapping) else {}
    full_scan_reason = str(structural_base.get("full_scan_reason", "")).strip()
    required_reads = [
        str(token).strip()
        for token in structural_base.get("required_reads", [])
        if str(token).strip()
    ] if isinstance(structural_base.get("required_reads"), list) else []
    operator_consequences = [
        dict(row) for row in structural_base.get("operator_consequences", []) if isinstance(row, Mapping)
    ]
    cache_key = odylith_context_cache.fingerprint_payload(
        {
            "bundle_signature": _architecture_bundle_signature(repo_root=repo_root, bundle=bundle),
            "changed_paths": [str(token).strip() for token in changed_paths if str(token).strip()],
            "mermaid_drift_hash": _architecture_mermaid_drift_hash(
                repo_root=repo_root,
                linked_diagrams=linked_diagrams,
            ),
            "benchmark_cases_hash": _architecture_benchmark_cases_hash(repo_root=repo_root),
        }
    )
    cached = _PROCESS_ARCHITECTURE_STRUCTURAL_CORE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    validation_obligations = _validation_obligations(
        repo_root=repo_root,
        changed_paths=changed_paths,
        topology_domains=topology_domains,
        linked_diagrams=linked_diagrams,
        matched_components=matched_components,
        tests=tests,
    )
    traceability_seed_tokens = _dedupe_strings(
        [
            *changed_paths,
            *[str(row.get("domain_id", "")).strip() for row in topology_domains if str(row.get("domain_id", "")).strip()],
            *[str(row.get("component_id", "")).strip() for row in matched_components if str(row.get("component_id", "")).strip()],
            *[str(row.get("diagram_id", "")).strip() for row in linked_diagrams if str(row.get("diagram_id", "")).strip()],
            *[str(row.get("path", "")).strip() for row in contract_touchpoints if str(row.get("path", "")).strip()],
            *[str(row.get("workstream_id", "")).strip().upper() for row in related_workstreams if str(row.get("workstream_id", "")).strip()],
            *[str(row.get("summary", "")).strip() for row in validation_obligations if str(row.get("summary", "")).strip()],
        ]
    )
    relevant_traceability_edges = _relevant_traceability_edges(
        repo_root=repo_root,
        bundle=bundle,
        changed_paths=changed_paths,
        seed_tokens=traceability_seed_tokens,
    )
    authority_graph = _authority_graph(
        changed_paths=changed_paths,
        topology_domains=topology_domains,
        matched_components=matched_components,
        linked_diagrams=linked_diagrams,
        contract_touchpoints=contract_touchpoints,
        related_workstreams=related_workstreams,
        historical_bugs=[],
        historical_notes=[],
        historical_adrs=[],
        historical_runbooks=[],
        validation_obligations=validation_obligations,
        traceability_edges=relevant_traceability_edges,
    )
    coverage = _enrich_coverage_with_authority_graph(
        coverage=coverage,
        changed_paths=changed_paths,
        authority_graph=authority_graph,
    )
    full_scan_recommended = bool(full_scan_reason)
    payload = {
        "matched_components": matched_components,
        "topology_domains": topology_domains,
        "linked_diagrams": linked_diagrams,
        "diagram_watch_gaps": diagram_watch_gaps,
        "contract_touchpoints": contract_touchpoints,
        "related_workstreams": related_workstreams,
        "coverage": dict(coverage),
        "required_reads": list(required_reads),
        "operator_consequences": operator_consequences,
        "validation_obligations": [dict(row) for row in validation_obligations],
        "authority_graph": dict(authority_graph),
        "authority_chain": _authority_chain(authority_graph=authority_graph),
        "blast_radius": _blast_radius(
            matched_components=matched_components,
            linked_diagrams=linked_diagrams,
            contract_touchpoints=contract_touchpoints,
            related_workstreams=related_workstreams,
            historical_bugs=[],
            authority_graph=authority_graph,
        ),
        "unresolved_questions": _unresolved_questions(
            changed_paths=changed_paths,
            matched_components=matched_components,
            contract_touchpoints=contract_touchpoints,
            diagram_watch_gaps=diagram_watch_gaps,
            coverage=coverage,
        ),
        "full_scan_reason": full_scan_reason,
        "full_scan_recommended": full_scan_recommended,
        "execution_hint": _execution_hint(
            topology_domains=topology_domains,
            coverage=coverage,
            full_scan_recommended=full_scan_recommended,
        ),
        "benchmark_summary": _architecture_benchmark_summary(
            repo_root=repo_root,
            changed_paths=changed_paths,
            topology_domains=topology_domains,
            coverage=coverage,
            contract_touchpoints=contract_touchpoints,
            full_scan_recommended=full_scan_recommended,
        ),
    }
    _PROCESS_ARCHITECTURE_STRUCTURAL_CORE_CACHE[cache_key] = payload
    return payload


def _match_components(*, components: Sequence[Mapping[str, Any]], changed_paths: Sequence[str]) -> list[dict[str, Any]]:
    matched: list[dict[str, Any]] = []
    for component in components:
        prefixes = component.get("path_prefixes", [])
        spec_ref = str(component.get("spec_ref", "")).strip()
        prefix_match = isinstance(prefixes, list) and any(
            _path_touches_watch(changed_path=changed_path, watch_path=str(prefix).strip())
            for changed_path in changed_paths
            for prefix in prefixes
            if str(prefix).strip()
        )
        spec_match = bool(spec_ref) and any(
            _path_touches_watch(changed_path=changed_path, watch_path=spec_ref)
            for changed_path in changed_paths
        )
        if prefix_match or spec_match:
            matched.append(dict(component))
    normalized_paths = {str(path).strip() for path in changed_paths if str(path).strip()}
    touches_install_runtime_boundary = any(
        path in {
            "src/odylith/install/runtime.py",
            "src/odylith/install/release_assets.py",
            "src/odylith/install/manager.py",
        }
        for path in normalized_paths
    )
    touches_chatter_install_guidance = any(
        path in {
            "src/odylith/install/agents.py",
            "AGENTS.md",
            "odylith/AGENTS.md",
            "odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md",
            "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
            "docs/benchmarks/README.md",
            "docs/benchmarks/REVIEWER_GUIDE.md",
            "odylith/runtime/source/optimization-evaluation-corpus.v1.json",
        }
        for path in normalized_paths
    )
    if touches_install_runtime_boundary and not touches_chatter_install_guidance:
        matched = [
            row
            for row in matched
            if str(row.get("component_id", "")).strip() != "odylith-chatter"
        ]
    matched.sort(key=lambda row: (str(row.get("component_id", "")).strip(), str(row.get("title", "")).strip()))
    return matched


def _match_diagrams(*, diagrams: Sequence[Mapping[str, Any]], changed_paths: Sequence[str]) -> tuple[list[dict[str, Any]], list[str]]:
    matched: list[dict[str, Any]] = []
    covered_paths: set[str] = set()
    for diagram in diagrams:
        watch_paths = [
            *(
                [str(token).strip() for token in diagram.get("watch_paths", []) if str(token).strip()]
                if isinstance(diagram.get("watch_paths"), list)
                else []
            ),
            str(diagram.get("source_mmd", "")).strip(),
            str(diagram.get("path", "")).strip(),
        ]
        matched_paths = [
            str(path).strip()
            for path in changed_paths
            if any(_path_touches_watch(changed_path=str(path).strip(), watch_path=str(watch).strip()) for watch in watch_paths)
        ]
        if not matched_paths:
            continue
        row = dict(diagram)
        row["matched_paths"] = _dedupe_strings(matched_paths)
        matched.append(row)
        covered_paths.update(row["matched_paths"])
    matched.sort(key=lambda row: str(row.get("diagram_id", "")).strip())
    return matched, sorted(covered_paths)


def _collect_topology_domains(
    *,
    changed_paths: Sequence[str],
    component_ids: Sequence[str],
    topology_domain_rules: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    normalized_components = {str(token).strip() for token in component_ids if str(token).strip()}
    rows: list[dict[str, Any]] = []
    for rule in topology_domain_rules:
        matched_paths = [
            str(path).strip()
            for path in changed_paths
            if str(path).strip()
            and any(
                _path_touches_watch(changed_path=str(path).strip(), watch_path=str(watch_path).strip())
                for watch_path in rule.get("path_prefixes", ())
            )
        ]
        matched_components = [
            str(component_id).strip()
            for component_id in rule.get("components", ())
            if str(component_id).strip() in normalized_components
        ]
        if not matched_paths and not matched_components:
            continue
        rows.append(
            {
                "domain_id": str(rule.get("domain_id", "")).strip(),
                "label": str(rule.get("label", "")).strip(),
                "summary": str(rule.get("summary", "")).strip(),
                "risk_tier": str(rule.get("risk_tier", "")).strip().lower(),
                "matched_paths": _dedupe_strings(matched_paths),
                "matched_components": _dedupe_strings(matched_components),
                "required_reads": _dedupe_strings(rule.get("required_reads", ())),
                "checks": _dedupe_strings(rule.get("checks", ())),
                "operator_consequences": _dedupe_strings(rule.get("operator_consequences", ())),
            }
        )
    return rows


def _component_related_diagrams(
    *,
    matched_components: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    related_ids = {
        str(diagram_id).strip()
        for component in matched_components
        for diagram_id in component.get("diagrams", [])
        if str(diagram_id).strip()
    }
    rows: list[dict[str, Any]] = []
    for diagram in diagrams:
        diagram_id = str(diagram.get("diagram_id", "")).strip()
        if diagram_id and diagram_id in related_ids:
            row = dict(diagram)
            row.setdefault("matched_paths", [])
            rows.append(row)
    rows.sort(key=lambda row: str(row.get("diagram_id", "")).strip())
    return rows


def _merge_diagram_sets(
    *,
    direct_diagrams: Sequence[Mapping[str, Any]],
    component_diagrams: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for row in [*direct_diagrams, *component_diagrams]:
        if not isinstance(row, Mapping):
            continue
        diagram_id = str(row.get("diagram_id", "")).strip()
        if not diagram_id:
            continue
        current = dict(merged.get(diagram_id, {}))
        for key, value in dict(row).items():
            if key == "matched_paths":
                current[key] = _dedupe_strings([*current.get(key, []), *value]) if isinstance(value, list) else current.get(key, [])
            elif key not in current or current[key] in ("", [], {}, None):
                current[key] = value
        relation = "component_link"
        if any(str(item.get("diagram_id", "")).strip() == diagram_id for item in direct_diagrams) and any(
            str(item.get("diagram_id", "")).strip() == diagram_id for item in component_diagrams
        ):
            relation = "direct_and_component_link"
        elif any(str(item.get("diagram_id", "")).strip() == diagram_id for item in direct_diagrams):
            relation = "direct"
        current["relation"] = relation
        merged[diagram_id] = current
    return [merged[key] for key in sorted(merged)]


def _collect_diagram_watch_gaps(
    *,
    changed_paths: Sequence[str],
    linked_diagrams: Sequence[Mapping[str, Any]],
    matched_components: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    covered = {
        str(path).strip()
        for diagram in linked_diagrams
        for path in diagram.get("matched_paths", [])
        if str(path).strip()
    }
    gaps: list[dict[str, Any]] = []
    for changed_path in changed_paths:
        token = str(changed_path).strip()
        if not token or token in covered:
            continue
        component_ids = [
            str(component.get("component_id", "")).strip()
            for component in matched_components
            if any(
                _path_touches_watch(changed_path=token, watch_path=str(prefix).strip())
                for prefix in component.get("path_prefixes", [])
                if str(prefix).strip()
            )
        ]
        if not component_ids:
            continue
        linked_diagram_ids = _dedupe_strings(
            [
                str(diagram.get("diagram_id", "")).strip()
                for diagram in linked_diagrams
                if set(component_ids).intersection(set(diagram.get("related_component_ids", [])))
            ]
        )
        gaps.append(
            {
                "path": token,
                "component_ids": _dedupe_strings(component_ids),
                "linked_diagram_ids": linked_diagram_ids,
            }
        )
    return gaps


def _contract_touchpoints(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    topology_domains: Sequence[Mapping[str, Any]],
    matched_components: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
    code_contracts: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    def _touchpoint_kind(path: str) -> str:
        token = str(path).strip()
        if token.endswith("CURRENT_SPEC.md"):
            return "component_spec"
        if token.endswith(".mmd") or "/atlas/source/" in token:
            return "diagram_related_doc"
        if "RUNBOOK" in token or token.startswith("docs/runbooks/"):
            return "runbook"
        return "developer_doc"

    normalized_changed_paths = [str(path).strip() for path in changed_paths if str(path).strip()]
    doc_only_changed_paths = bool(normalized_changed_paths) and all(
        path == "README.md"
        or path == "odylith/MAINTAINER_RELEASE_RUNBOOK.md"
        or path.startswith(
            (
                "odylith/atlas/source/",
                "odylith/registry/source/components/",
                "docs/benchmarks/",
            )
        )
        for path in normalized_changed_paths
    )
    has_direct_diagram_match = any(
        any(str(path).strip() for path in diagram.get("matched_paths", []))
        for diagram in diagrams
        if isinstance(diagram, Mapping)
    )

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for domain in topology_domains:
        domain_id = str(domain.get("domain_id", "")).strip()
        for path in domain.get("required_reads", []):
            token = _normalize_repo_path(repo_root=repo_root, value=path)
            if not token or token in seen:
                continue
            seen.add(token)
            rows.append(
                {
                    "path": token,
                    "kind": _touchpoint_kind(token),
                    "source": "topology_domain",
                    "domain_id": domain_id,
                }
            )
    for component in matched_components:
        component_id = str(component.get("component_id", "")).strip()
        traceability = dict(component.get("traceability", {})) if isinstance(component.get("traceability"), Mapping) else {}
        for bucket_name, relation in (("developer_docs", "developer_doc"), ("runbooks", "runbook")):
            for path in traceability.get(bucket_name, []):
                token = _normalize_repo_path(repo_root=repo_root, value=path)
                if not token or token in seen:
                    continue
                seen.add(token)
                rows.append(
                    {
                        "path": token,
                        "kind": relation,
                        "source": "component_traceability",
                        "component_id": component_id,
                    }
                )
        spec_ref = _normalize_repo_path(repo_root=repo_root, value=component.get("spec_ref"))
        if spec_ref and spec_ref not in seen:
            seen.add(spec_ref)
            rows.append(
                {
                    "path": spec_ref,
                    "kind": "component_spec",
                    "source": "component_spec",
                    "component_id": component_id,
                }
            )
    for diagram in diagrams:
        if (
            doc_only_changed_paths
            and has_direct_diagram_match
            and not any(str(path).strip() for path in diagram.get("matched_paths", []))
        ):
            continue
        for path in diagram.get("related_docs", []):
            token = _normalize_repo_path(repo_root=repo_root, value=path)
            if not token or token in seen:
                continue
            seen.add(token)
            rows.append(
                {
                    "path": token,
                    "kind": "diagram_related_doc",
                    "source": "diagram_metadata",
                    "diagram_id": str(diagram.get("diagram_id", "")).strip(),
                }
            )
    for row in code_contracts:
        if not isinstance(row, Mapping):
            continue
        code_path = _normalize_repo_path(repo_root=repo_root, value=row.get("path"))
        if not code_path:
            continue
        if not any(_path_touches_watch(changed_path=path, watch_path=code_path) for path in changed_paths):
            continue
        for ref in row.get("contract_refs", []):
            token = _normalize_repo_path(repo_root=repo_root, value=ref)
            if not token or token in seen:
                continue
            seen.add(token)
            rows.append(
                {
                    "path": token,
                    "kind": "code_contract_ref",
                    "source": "code_artifact",
                    "from_path": code_path,
                }
            )
    rows.sort(key=lambda item: (str(item.get("kind", "")).strip(), str(item.get("path", "")).strip()))
    return rows


def _prune_secondary_diagram_required_reads(
    *,
    changed_paths: Sequence[str],
    matched_components: Sequence[Mapping[str, Any]],
    topology_domains: Sequence[Mapping[str, Any]],
    linked_diagrams: Sequence[Mapping[str, Any]],
    required_reads: Sequence[str],
) -> list[str]:
    normalized_paths = [str(token).strip() for token in changed_paths if str(token).strip()]
    if not normalized_paths:
        return _dedupe_strings(required_reads)
    doc_only_changed_paths = all(
        path == "README.md"
        or path == "odylith/MAINTAINER_RELEASE_RUNBOOK.md"
        or path.startswith(
            (
                "odylith/atlas/source/",
                "odylith/registry/source/components/",
                "docs/benchmarks/",
            )
        )
        for path in normalized_paths
    )
    diagram_only_slice = (
        bool(linked_diagrams)
        and not topology_domains
        and doc_only_changed_paths
        and not any(path.startswith("odylith/maintainer/") for path in normalized_paths)
    )
    if not diagram_only_slice:
        return _dedupe_strings(required_reads)
    normalized_required_reads = _dedupe_strings(required_reads)
    secondary_diagram_paths = {
        str(diagram.get("path", "")).strip()
        for diagram in linked_diagrams
        if isinstance(diagram, Mapping)
        and not any(str(path).strip() for path in diagram.get("matched_paths", []))
        and str(diagram.get("path", "")).strip()
    }
    if secondary_diagram_paths:
        normalized_required_reads = [
            token for token in normalized_required_reads if token not in secondary_diagram_paths
        ]
    has_public_release_contract = any(
        token in normalized_required_reads
        for token in ("README.md", "odylith/MAINTAINER_RELEASE_RUNBOOK.md")
    )
    has_component_spec = any(token.endswith("CURRENT_SPEC.md") for token in normalized_required_reads)
    if not has_public_release_contract or not has_component_spec:
        return normalized_required_reads
    filtered_required_reads = [
        token
        for token in normalized_required_reads
        if not token.startswith("odylith/maintainer/agents-guidelines/")
    ]
    component_specs = [token for token in filtered_required_reads if token.endswith("CURRENT_SPEC.md")]
    umbrella_component_specs = {
        "odylith/registry/source/components/atlas/CURRENT_SPEC.md",
        "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
    }
    has_specific_component_spec = any(token not in umbrella_component_specs for token in component_specs)
    if has_specific_component_spec:
        filtered_required_reads = [
            token for token in filtered_required_reads if token not in umbrella_component_specs
        ]
    return filtered_required_reads or normalized_required_reads


def _historical_bugs(
    *,
    changed_paths: Sequence[str],
    matched_components: Sequence[Mapping[str, Any]],
    bugs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    component_tokens = {
        str(component.get("component_id", "")).strip().lower()
        for component in matched_components
        if str(component.get("component_id", "")).strip()
    }
    component_aliases = {
        str(alias).strip().lower()
        for component in matched_components
        for alias in component.get("aliases", [])
        if str(alias).strip()
    }
    rows: list[tuple[int, dict[str, Any]]] = []
    for bug in bugs:
        search_body = str(bug.get("search_body", "")).lower()
        components_text = str(bug.get("components", "")).lower()
        score = 0
        matched_paths: list[str] = []
        for changed_path in changed_paths:
            token = str(changed_path).strip()
            if token and token.lower() in search_body:
                score += 4
                matched_paths.append(token)
        if component_tokens and any(token in search_body or token in components_text for token in component_tokens):
            score += 3
        if component_aliases and any(token in search_body or token in components_text for token in component_aliases):
            score += 2
        if score <= 0:
            continue
        rows.append(
            (
                -score,
                {
                    "bug_id": str(bug.get("bug_id", "")).strip(),
                    "bug_key": str(bug.get("bug_key", "")).strip(),
                    "title": str(bug.get("title", "")).strip(),
                    "status": str(bug.get("status", "")).strip(),
                    "severity": str(bug.get("severity", "")).strip(),
                    "matched_paths": _dedupe_strings(matched_paths),
                },
            )
        )
    rows.sort(key=lambda item: (item[0], str(item[1].get("bug_id", "") or item[1].get("bug_key", "")).strip()))
    return [row for _score, row in rows[:6]]


def _historical_notes(
    *,
    changed_paths: Sequence[str],
    matched_components: Sequence[Mapping[str, Any]],
    engineering_notes: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    component_tokens = {
        str(component.get("component_id", "")).strip().lower()
        for component in matched_components
        if str(component.get("component_id", "")).strip()
    }
    rows: list[tuple[int, dict[str, Any]]] = []
    for note in engineering_notes:
        tags = {str(token).strip().lower() for token in note.get("tags", []) if str(token).strip()}
        kind = str(note.get("kind", "")).strip().lower()
        if kind in {"decision", "adr"} or "adr" in tags:
            continue
        source_path = str(note.get("source_path", "")).strip()
        title = str(note.get("title", "")).strip()
        summary = str(note.get("summary", "")).strip()
        text = f"{source_path} {title} {summary}".lower()
        score = 0
        if source_path and any(_path_touches_watch(changed_path=changed_path, watch_path=source_path) for changed_path in changed_paths):
            score += 4
        if component_tokens and any(token in text for token in component_tokens):
            score += 2
        if {"architecture", "decision", "adr"}.intersection(tags):
            score += 1
        if score <= 0:
            continue
        rows.append(
            (
                -score,
                {
                    "note_id": str(note.get("note_id", "")).strip(),
                    "kind": str(note.get("kind", "")).strip(),
                    "title": title,
                    "source_path": source_path,
                    "summary": summary,
                },
            )
        )
    rows.sort(key=lambda item: (item[0], str(item[1].get("note_id", "")).strip()))
    return [row for _score, row in rows[:6]]


def _historical_adrs(
    *,
    changed_paths: Sequence[str],
    matched_components: Sequence[Mapping[str, Any]],
    engineering_notes: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    component_tokens = {
        str(component.get("component_id", "")).strip().lower()
        for component in matched_components
        if str(component.get("component_id", "")).strip()
    }
    rows: list[tuple[int, dict[str, Any]]] = []
    for note in engineering_notes:
        tags = {str(token).strip().lower() for token in note.get("tags", []) if str(token).strip()}
        kind = str(note.get("kind", "")).strip().lower()
        if kind not in {"decision", "adr"} and not {"architecture", "decision", "adr"}.intersection(tags):
            continue
        source_path = str(note.get("source_path", "")).strip()
        title = str(note.get("title", "")).strip()
        summary = str(note.get("summary", "")).strip()
        text = f"{source_path} {title} {summary}".lower()
        score = 1
        if source_path and any(
            _path_touches_watch(changed_path=changed_path, watch_path=source_path) for changed_path in changed_paths
        ):
            score += 4
        if component_tokens and any(token in text for token in component_tokens):
            score += 2
        rows.append(
            (
                -score,
                {
                    "note_id": str(note.get("note_id", "")).strip(),
                    "kind": str(note.get("kind", "")).strip(),
                    "title": title,
                    "source_path": source_path,
                    "summary": summary,
                },
            )
        )
    rows.sort(key=lambda item: (item[0], str(item[1].get("note_id", "")).strip()))
    return [row for _score, row in rows[:4]]


def _related_workstreams(
    *,
    repo_root: Path,
    bundle: Mapping[str, Any],
    changed_paths: Sequence[str],
    matched_components: Sequence[Mapping[str, Any]],
    linked_diagrams: Sequence[Mapping[str, Any]],
    workstreams: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    candidate_ids = {
        str(workstream_id).strip().upper()
        for component in matched_components
        for workstream_id in component.get("workstreams", [])
        if str(workstream_id).strip()
    }
    candidate_ids.update(
        str(workstream_id).strip().upper()
        for diagram in linked_diagrams
        for workstream_id in diagram.get("related_workstreams", [])
        if str(workstream_id).strip()
    )
    rows: list[dict[str, Any]] = []
    matched_ids: set[str] = set()
    index = _workstream_index(repo_root=repo_root, bundle=bundle)
    indexed_rows: list[dict[str, Any]] = []
    seen_rows: set[str] = set()
    for workstream_id in sorted(candidate_ids):
        workstream = dict(index.get("by_id", {}).get(workstream_id, {}))
        if not workstream:
            continue
        seen_rows.add(workstream_id)
        indexed_rows.append(workstream)
    for candidate in _path_watch_candidates(changed_paths):
        for workstream in index.get("by_watch_path", {}).get(candidate, []):
            if not isinstance(workstream, Mapping):
                continue
            workstream_id = str(workstream.get("workstream_id", "")).strip().upper()
            if not workstream_id or workstream_id in seen_rows:
                continue
            seen_rows.add(workstream_id)
            indexed_rows.append(dict(workstream))
    if not indexed_rows:
        indexed_rows = [dict(row) for row in workstreams if isinstance(row, Mapping)]
    for workstream in indexed_rows:
        workstream_id = str(workstream.get("workstream_id", "")).strip().upper()
        if not workstream_id:
            continue
        if workstream_id not in candidate_ids and not any(
            _path_touches_watch(changed_path=path, watch_path=str(workstream.get("source_path", "")).strip())
            or _path_touches_watch(changed_path=path, watch_path=str(workstream.get("idea_file", "")).strip())
            or _path_touches_watch(changed_path=path, watch_path=str(workstream.get("promoted_to_plan", "")).strip())
            for path in changed_paths
        ):
            continue
        rows.append(
            {
                "workstream_id": workstream_id,
                "title": str(workstream.get("title", "")).strip(),
                "status": str(workstream.get("status", "")).strip(),
                "priority": str(workstream.get("priority", "")).strip(),
            }
        )
        matched_ids.add(workstream_id)
    for workstream_id in sorted(candidate_ids.difference(matched_ids)):
        rows.append(
            {
                "workstream_id": workstream_id,
                "title": "",
                "status": "referenced",
                "priority": "",
            }
        )
    rows.sort(key=lambda item: (item["workstream_id"], item["title"]))
    return rows[:10]


def _historical_runbooks(
    *,
    topology_domains: Sequence[Mapping[str, Any]],
    contract_touchpoints: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for domain in topology_domains:
        domain_id = str(domain.get("domain_id", "")).strip()
        for path in domain.get("required_reads", []):
            token = str(path).strip()
            if not token.startswith("docs/runbooks/") or token in seen:
                continue
            seen.add(token)
            rows.append(
                {
                    "path": token,
                    "source": "topology_required_read",
                    "component_id": "",
                    "domain_id": domain_id,
                }
            )
    for touchpoint in contract_touchpoints:
        if str(touchpoint.get("kind", "")).strip() != "runbook":
            continue
        path = str(touchpoint.get("path", "")).strip()
        if not path or path in seen:
            continue
        seen.add(path)
        rows.append(
            {
                "path": path,
                "source": str(touchpoint.get("source", "")).strip(),
                "component_id": str(touchpoint.get("component_id", "")).strip(),
            }
        )
    rows.sort(key=lambda row: (str(row.get("path", "")).strip(), str(row.get("source", "")).strip()))
    return rows[:6]


def _validation_obligations(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    topology_domains: Sequence[Mapping[str, Any]],
    linked_diagrams: Sequence[Mapping[str, Any]],
    matched_components: Sequence[Mapping[str, Any]],
    tests: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for domain in topology_domains:
        for check in domain.get("checks", []):
            token = str(check).strip()
            if not token:
                continue
            key = f"topology:{token}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            rows.append(
                {
                    "kind": "topology_check",
                    "summary": token,
                    "domain_id": str(domain.get("domain_id", "")).strip(),
                }
            )
    for diagram in linked_diagrams:
        source_mmd = _normalize_repo_path(repo_root=repo_root, value=diagram.get("source_mmd"))
        current_hash = ""
        if source_mmd:
            path = Path(repo_root).resolve() / source_mmd
            current_hash = _current_source_mmd_hash(path)
        needs_render = bool(current_hash and current_hash != str(diagram.get("source_mmd_hash", "")).strip())
        if needs_render or any(_path_touches_watch(changed_path=path, watch_path=source_mmd) for path in changed_paths):
            key = f"diagram:{diagram.get('diagram_id', '')}"
            if key not in seen_keys:
                seen_keys.add(key)
                rows.append(
                    {
                        "kind": "diagram_review",
                        "summary": f"Review and re-render {str(diagram.get('diagram_id', '')).strip()} if the architecture slice changes its depicted boundary.",
                        "diagram_id": str(diagram.get("diagram_id", "")).strip(),
                        "path": source_mmd,
                        "needs_render": needs_render,
                    }
                )
    for component in matched_components:
        component_id = str(component.get("component_id", "")).strip()
        for command in component.get("validation_commands", []):
            if not isinstance(command, Mapping):
                continue
            token = str(command.get("command", "")).strip()
            if not token:
                continue
            key = f"command:{token}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            rows.append(
                {
                    "kind": "validation_command",
                    "summary": token,
                    "component_id": component_id,
                    "group": str(command.get("group", "")).strip(),
                }
            )
    for test in tests:
        target_paths = test.get("target_paths", [])
        if not isinstance(target_paths, list) or not target_paths:
            continue
        if not any(_path_touches_watch(changed_path=path, watch_path=target) for path in changed_paths for target in target_paths):
            continue
        test_path = _normalize_repo_path(repo_root=repo_root, value=test.get("test_path"))
        if not test_path:
            continue
        key = f"test:{test_path}:{test.get('test_name', '')}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        rows.append(
            {
                "kind": "test",
                "summary": str(test.get("node_id", "")).strip() or test_path,
                "test_path": test_path,
            }
        )
    return rows[:16]


def _operator_consequences(
    *,
    topology_domains: Sequence[Mapping[str, Any]],
    matched_components: Sequence[Mapping[str, Any]],
    historical_bugs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for domain in topology_domains:
        for consequence in domain.get("operator_consequences", []):
            token = str(consequence).strip()
            if not token or token in seen:
                continue
            seen.add(token)
            rows.append(
                {
                    "source": "topology_domain",
                    "domain_id": str(domain.get("domain_id", "")).strip(),
                    "summary": token,
                }
            )
    for component in matched_components:
        token = str(component.get("why_tracked", "")).strip()
        if token and token not in seen:
            seen.add(token)
            rows.append(
                {
                    "source": "component",
                    "component_id": str(component.get("component_id", "")).strip(),
                    "summary": token,
                }
            )
    for bug in historical_bugs[:2]:
        bug_id = str(bug.get("bug_id", "")).strip()
        token = " ".join(
            item for item in (bug_id, str(bug.get("title", "")).strip()) if item
        ).strip()
        if token and token not in seen:
            seen.add(token)
            rows.append(
                {
                    "source": "bug_history",
                    "bug_id": bug_id,
                    "bug_key": str(bug.get("bug_key", "")).strip(),
                    "summary": f"Similar failure already existed: {token}.",
                }
            )
    return rows[:8]


def _coverage_summary(
    *,
    changed_paths: Sequence[str],
    topology_domains: Sequence[Mapping[str, Any]],
    matched_components: Sequence[Mapping[str, Any]],
    linked_diagrams: Sequence[Mapping[str, Any]],
    contract_touchpoints: Sequence[Mapping[str, Any]],
    diagram_watch_gaps: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    total_paths = max(1, len(changed_paths))
    grounded_path_count = 0
    contract_covered_paths: set[str] = set()
    domain_covered_paths = {
        str(path).strip()
        for domain in topology_domains
        for path in domain.get("matched_paths", [])
        if str(path).strip()
    }
    diagram_covered_paths = {
        str(path).strip()
        for diagram in linked_diagrams
        for path in diagram.get("matched_paths", [])
        if str(path).strip()
    }
    for changed_path in changed_paths:
        component_for_path = [
            component
            for component in matched_components
            if any(
                _path_touches_watch(changed_path=changed_path, watch_path=str(prefix).strip())
                for prefix in component.get("path_prefixes", [])
                if str(prefix).strip()
            )
        ]
        path_grounded = (
            bool(component_for_path)
            or str(changed_path).strip() in domain_covered_paths
            or str(changed_path).strip() in diagram_covered_paths
        )
        if path_grounded:
            grounded_path_count += 1
        if any(
            str(path.get("from_path", "")).strip()
            and _path_touches_watch(changed_path=changed_path, watch_path=str(path.get("from_path", "")).strip())
            for path in contract_touchpoints
            if isinstance(path, Mapping)
        ) or any(
            str(path.get("path", "")).strip()
            and _path_touches_watch(changed_path=changed_path, watch_path=str(path.get("path", "")).strip())
            for path in contract_touchpoints
            if isinstance(path, Mapping)
        ) or any(
            str(component.get("spec_ref", "")).strip()
            or any(
                str(token).strip()
                for bucket in dict(component.get("traceability", {})).values()
                if isinstance(bucket, list)
                for token in bucket
            )
            for component in component_for_path
            if isinstance(component, Mapping)
        ) or str(changed_path).strip() in domain_covered_paths:
            contract_covered_paths.add(str(changed_path).strip())
    ownership_covered = sum(1 for component in matched_components if str(component.get("owner", "")).strip())
    unresolved_edge_count = sum(
        1
        for path in changed_paths
        if str(path).strip()
        and str(path).strip() not in domain_covered_paths
        and not any(_path_touches_watch(changed_path=path, watch_path=str(prefix).strip()) for component in matched_components for prefix in component.get("path_prefixes", []))
        and str(path).strip() not in diagram_covered_paths
    )
    unresolved_edge_count += len(diagram_watch_gaps)
    path_ratio = round(grounded_path_count / total_paths, 3)
    diagram_ratio = round(len(diagram_covered_paths) / total_paths, 3)
    contract_ratio = round(len(contract_covered_paths) / total_paths, 3)
    ownership_ratio = round(
        ownership_covered / max(1, len(matched_components)),
        3,
    )
    score = int(
        round(
            (
                (path_ratio * 35.0)
                + (diagram_ratio * 20.0)
                + (contract_ratio * 20.0)
                + (ownership_ratio * 15.0)
                + (0 if diagram_watch_gaps else 10.0)
            )
        )
    )
    if unresolved_edge_count > 0 or diagram_watch_gaps or path_ratio < 0.5:
        confidence_tier = "low"
    elif contract_ratio < 0.5 or diagram_ratio < 0.5 or ownership_ratio < 0.75:
        confidence_tier = "medium"
    else:
        confidence_tier = "high"
    return {
        "path_coverage": {
            "matched": grounded_path_count,
            "total": total_paths,
            "ratio": path_ratio,
        },
        "diagram_coverage": {
            "matched": len(diagram_covered_paths),
            "total": total_paths,
            "ratio": diagram_ratio,
        },
        "contract_coverage": {
            "matched": len(contract_covered_paths),
            "total": total_paths,
            "ratio": contract_ratio,
        },
        "ownership_coverage": {
            "matched_components": ownership_covered,
            "total_components": len(matched_components),
            "ratio": ownership_ratio,
        },
        "unresolved_edge_count": unresolved_edge_count,
        "score": max(0, min(100, score)),
        "confidence_tier": confidence_tier,
    }


def _authority_chain(
    *,
    authority_graph: Mapping[str, Any],
) -> list[dict[str, Any]]:
    nodes = {
        (str(row.get("kind", "")).strip(), str(row.get("id", "")).strip()): dict(row)
        for row in authority_graph.get("nodes", [])
        if isinstance(row, Mapping)
        and str(row.get("kind", "")).strip()
        and str(row.get("id", "")).strip()
    }
    priority = {
        "grounded_to_component": 0,
        "governs_component": 1,
        "governs_path": 2,
        "documented_by_diagram": 3,
        "touches_contract": 4,
        "validated_by": 5,
        "owned_by_workstream": 6,
        "architectural_decision": 7,
        "historical_runbook": 8,
        "historical_incident": 9,
        "historical_note": 10,
        "reviewed_by": 11,
        "watched_by_diagram": 12,
        "touches_related_doc": 13,
        "related_to": 14,
    }
    rows: list[dict[str, Any]] = []
    edges = [
        dict(row)
        for row in authority_graph.get("edges", [])
        if isinstance(row, Mapping)
    ]
    edges.sort(
        key=lambda row: (
            priority.get(str(row.get("relation", "")).strip(), 99),
            str(row.get("source_kind", "")).strip(),
            str(row.get("source_id", "")).strip(),
            str(row.get("target_kind", "")).strip(),
            str(row.get("target_id", "")).strip(),
        )
    )
    for edge in edges:
        source_key = (str(edge.get("source_kind", "")).strip(), str(edge.get("source_id", "")).strip())
        target_key = (str(edge.get("target_kind", "")).strip(), str(edge.get("target_id", "")).strip())
        source_node = nodes.get(source_key, {})
        target_node = nodes.get(target_key, {})
        rows.append(
            {
                "kind": "authority_edge",
                "relation": str(edge.get("relation", "")).strip(),
                "source_kind": source_key[0],
                "source_id": source_key[1],
                "source_label": str(source_node.get("label", "")).strip() or source_key[1],
                "target_kind": target_key[0],
                "target_id": target_key[1],
                "target_label": str(target_node.get("label", "")).strip() or target_key[1],
                "why": str(edge.get("source", "")).strip() or "authority_graph",
            }
        )
    return rows[:20]


def _blast_radius(
    *,
    matched_components: Sequence[Mapping[str, Any]],
    linked_diagrams: Sequence[Mapping[str, Any]],
    contract_touchpoints: Sequence[Mapping[str, Any]],
    related_workstreams: Sequence[Mapping[str, Any]],
    historical_bugs: Sequence[Mapping[str, Any]],
    authority_graph: Mapping[str, Any],
) -> dict[str, Any]:
    node_rows = [
        dict(row)
        for row in authority_graph.get("nodes", [])
        if isinstance(row, Mapping)
    ]
    edge_rows = [
        dict(row)
        for row in authority_graph.get("edges", [])
        if isinstance(row, Mapping)
    ]
    node_kind_counts: dict[str, int] = {}
    for row in node_rows:
        kind = str(row.get("kind", "")).strip()
        if not kind:
            continue
        node_kind_counts[kind] = node_kind_counts.get(kind, 0) + 1
    docs = _dedupe_strings(
        str(row.get("path", "")).strip()
        for row in contract_touchpoints
        if str(row.get("kind", "")).strip() in {"developer_doc", "runbook", "component_spec", "diagram_related_doc"}
    )
    return {
        "component_ids": _dedupe_strings(component.get("component_id", "") for component in matched_components),
        "diagram_ids": _dedupe_strings(diagram.get("diagram_id", "") for diagram in linked_diagrams),
        "workstream_ids": _dedupe_strings(row.get("workstream_id", "") for row in related_workstreams),
        "doc_paths": docs[:12],
        "bug_keys": _dedupe_strings(row.get("bug_key", "") for row in historical_bugs),
        "counts": {
            "components": len(matched_components),
            "diagrams": len(linked_diagrams),
            "docs": len(docs),
            "workstreams": len(related_workstreams),
            "bugs": len(historical_bugs),
            "graph_nodes": len(node_rows),
            "graph_edges": len(edge_rows),
            "graph_traceability_edges": int(dict(authority_graph.get("counts", {})).get("traceability_edges", 0) or 0)
            if isinstance(authority_graph.get("counts"), Mapping)
            else 0,
            "runbooks": node_kind_counts.get("runbook", 0),
            "adrs": node_kind_counts.get("adr", 0),
            "validation_nodes": sum(
                count
                for kind, count in node_kind_counts.items()
                if kind in {"validation_command", "test", "diagram_review", "topology_check"}
            ),
        },
        "graph_kind_counts": node_kind_counts,
    }


def _compact_authority_graph(
    authority_graph: Mapping[str, Any],
    *,
    node_limit: int,
    edge_limit: int,
) -> dict[str, Any]:
    counts = dict(authority_graph.get("counts", {})) if isinstance(authority_graph.get("counts"), Mapping) else {}
    focus_nodes = []
    if int(node_limit) > 0:
        for row in authority_graph.get("nodes", []):
            if not isinstance(row, Mapping):
                continue
            focus_nodes.append(
                {
                    "kind": str(row.get("kind", "")).strip(),
                    "id": str(row.get("id", "")).strip(),
                    "label": str(row.get("label", "")).strip(),
                    "path": str(row.get("path", "")).strip(),
                }
            )
            if len(focus_nodes) >= int(node_limit):
                break
    focus_edges = []
    if int(edge_limit) > 0:
        for row in authority_graph.get("edges", []):
            if not isinstance(row, Mapping):
                continue
            focus_edges.append(
                {
                    "source_kind": str(row.get("source_kind", "")).strip(),
                    "source_id": str(row.get("source_id", "")).strip(),
                    "target_kind": str(row.get("target_kind", "")).strip(),
                    "target_id": str(row.get("target_id", "")).strip(),
                    "relation": str(row.get("relation", "")).strip(),
                    "source": str(row.get("source", "")).strip(),
                }
            )
            if len(focus_edges) >= int(edge_limit):
                break
    return {
        "counts": counts,
        "focus_nodes": focus_nodes,
        "focus_edges": focus_edges,
    }


def _compact_historical_bucket(
    rows: Sequence[Mapping[str, Any]],
    *,
    limit: int,
    fields: Sequence[str],
) -> list[dict[str, Any]]:
    compacted: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        compacted.append(
            {
                field: row.get(field)
                for field in fields
                if row.get(field) not in (None, "", [], {})
            }
        )
        if len(compacted) >= max(1, int(limit)):
            break
    return compacted


def _compact_architecture_dossier(
    dossier: Mapping[str, Any],
    *,
    detail_level: str,
) -> dict[str, Any]:
    level = _normalize_detail_level(detail_level)
    packet_mode = level == "packet"
    domain_limit = 2 if packet_mode else 3
    component_limit = 2 if packet_mode else 2
    diagram_limit = 2 if packet_mode else 2
    required_read_limit = 3 if packet_mode else 4
    touchpoint_limit = 0 if packet_mode else 4
    obligation_limit = 0 if packet_mode else 4
    consequence_limit = 0 if packet_mode else 3
    authority_chain_limit = 0 if packet_mode else 4
    historical_limit = 1 if packet_mode else 2

    topology_domains = []
    for row in dossier.get("topology_domains", []):
        if not isinstance(row, Mapping):
            continue
        compact_domain = {
            "domain_id": str(row.get("domain_id", "")).strip(),
            "label": str(row.get("label", "")).strip(),
            "matched_paths": _dedupe_strings(row.get("matched_paths", []))[:1 if packet_mode else 2]
            if isinstance(row.get("matched_paths"), list)
            else [],
            "matched_components": _dedupe_strings(row.get("matched_components", []))[: (2 if packet_mode else 3)]
            if isinstance(row.get("matched_components"), list)
            else [],
            "check_count": len(row.get("checks", [])) if isinstance(row.get("checks"), list) else 0,
            "operator_consequence_count": len(row.get("operator_consequences", []))
            if isinstance(row.get("operator_consequences"), list)
            else 0,
        }
        if not packet_mode:
            compact_domain["summary"] = str(row.get("summary", "")).strip()
            compact_domain["required_reads"] = _dedupe_strings(row.get("required_reads", []))[:2] if isinstance(
                row.get("required_reads"),
                list,
            ) else []
        topology_domains.append(compact_domain)
        if len(topology_domains) >= domain_limit:
            break

    linked_components = []
    for row in dossier.get("linked_components", []):
        if not isinstance(row, Mapping):
            continue
        compact_component = {
            "component_id": str(row.get("component_id", "")).strip(),
            "title": str(row.get("title", "")).strip(),
        }
        if not packet_mode:
            compact_component["path"] = str(row.get("path", "")).strip()
            compact_component["diagram_ids"] = _dedupe_strings(row.get("diagrams", []))[:3] if isinstance(
                row.get("diagrams"),
                list,
            ) else []
            compact_component["workstream_ids"] = _dedupe_strings(row.get("workstreams", []))[:3] if isinstance(
                row.get("workstreams"),
                list,
            ) else []
        linked_components.append(compact_component)
        if len(linked_components) >= component_limit:
            break

    linked_diagrams = []
    for row in dossier.get("linked_diagrams", []):
        if not isinstance(row, Mapping):
            continue
        compact_diagram = {
            "diagram_id": str(row.get("diagram_id", "")).strip(),
            "relation": str(row.get("relation", "")).strip(),
            "matched_paths": _dedupe_strings(row.get("matched_paths", []))[:1]
            if isinstance(row.get("matched_paths"), list)
            else [],
        }
        if not packet_mode:
            compact_diagram["title"] = str(row.get("title", "")).strip()
        linked_diagrams.append(compact_diagram)
        if len(linked_diagrams) >= diagram_limit:
            break

    blast_radius = dict(dossier.get("blast_radius", {})) if isinstance(dossier.get("blast_radius"), Mapping) else {}
    if packet_mode:
        blast_radius = {
            "counts": dict(blast_radius.get("counts", {})) if isinstance(blast_radius.get("counts"), Mapping) else {},
        }
    else:
        blast_radius["component_ids"] = _dedupe_strings(blast_radius.get("component_ids", []))[:2]
        blast_radius["diagram_ids"] = _dedupe_strings(blast_radius.get("diagram_ids", []))[:2]
        blast_radius["workstream_ids"] = _dedupe_strings(blast_radius.get("workstream_ids", []))[:2]
        blast_radius["doc_paths"] = _dedupe_strings(blast_radius.get("doc_paths", []))[:2]
        blast_radius["bug_keys"] = _dedupe_strings(blast_radius.get("bug_keys", []))[:2]

    historical = dict(dossier.get("historical_evidence", {})) if isinstance(dossier.get("historical_evidence"), Mapping) else {}
    compact_historical = {
        "bug_count": len(historical.get("bugs", [])) if isinstance(historical.get("bugs"), list) else 0,
        "runbook_count": len(historical.get("runbooks", [])) if isinstance(historical.get("runbooks"), list) else 0,
        "adr_count": len(historical.get("adrs", [])) if isinstance(historical.get("adrs"), list) else 0,
        "note_count": len(historical.get("notes", [])) if isinstance(historical.get("notes"), list) else 0,
        "workstream_count": len(historical.get("workstreams", [])) if isinstance(historical.get("workstreams"), list) else 0,
    }
    if not packet_mode:
        compact_historical["bugs"] = _compact_historical_bucket(
            historical.get("bugs", []) if isinstance(historical.get("bugs"), list) else [],
            limit=historical_limit,
            fields=("bug_key", "title", "status"),
        )
        compact_historical["runbooks"] = _compact_historical_bucket(
            historical.get("runbooks", []) if isinstance(historical.get("runbooks"), list) else [],
            limit=historical_limit,
            fields=("path", "component_id"),
        )
        compact_historical["adrs"] = _compact_historical_bucket(
            historical.get("adrs", []) if isinstance(historical.get("adrs"), list) else [],
            limit=historical_limit,
            fields=("note_id", "title", "source_path"),
        )
        compact_historical["notes"] = _compact_historical_bucket(
            historical.get("notes", []) if isinstance(historical.get("notes"), list) else [],
            limit=historical_limit,
            fields=("note_id", "title", "source_path"),
        )
        compact_historical["workstreams"] = _compact_historical_bucket(
            historical.get("workstreams", []) if isinstance(historical.get("workstreams"), list) else [],
            limit=historical_limit,
            fields=("workstream_id", "title", "status", "priority"),
        )

    compacted = {
        "resolved": bool(dossier.get("resolved")),
        "detail_level": level,
        "changed_paths": _dedupe_strings(dossier.get("changed_paths", []))[: (2 if packet_mode else 4)]
        if isinstance(dossier.get("changed_paths"), list)
        else [],
        "explicit_paths": _dedupe_strings(dossier.get("explicit_paths", []))[: (2 if packet_mode else 4)]
        if isinstance(dossier.get("explicit_paths"), list)
        else [],
        "repo_dirty_paths": _dedupe_strings(dossier.get("repo_dirty_paths", []))[:2]
        if isinstance(dossier.get("repo_dirty_paths"), list)
        else [],
        "scoped_working_tree_paths": _dedupe_strings(dossier.get("scoped_working_tree_paths", []))[:2]
        if isinstance(dossier.get("scoped_working_tree_paths"), list)
        else [],
        "working_tree_scope": str(dossier.get("working_tree_scope", "")).strip(),
        "working_tree_scope_degraded": bool(dossier.get("working_tree_scope_degraded")),
        "topology_domains": topology_domains,
        "linked_components": linked_components,
        "linked_diagrams": linked_diagrams,
        "linked_component_count": len(dossier.get("linked_components", [])) if isinstance(dossier.get("linked_components"), list) else 0,
        "linked_diagram_count": len(dossier.get("linked_diagrams", [])) if isinstance(dossier.get("linked_diagrams"), list) else 0,
        "required_read_count": len(dossier.get("required_reads", [])) if isinstance(dossier.get("required_reads"), list) else 0,
        "required_reads": _dedupe_strings(dossier.get("required_reads", []))[:required_read_limit]
        if isinstance(dossier.get("required_reads"), list)
        else [],
        "diagram_watch_gap_count": len(dossier.get("diagram_watch_gaps", []))
        if isinstance(dossier.get("diagram_watch_gaps"), list)
        else 0,
        "diagram_watch_gaps": _compact_historical_bucket(
            dossier.get("diagram_watch_gaps", []) if isinstance(dossier.get("diagram_watch_gaps"), list) else [],
            limit=historical_limit,
            fields=("path", "component_ids", "linked_diagram_ids"),
        ),
        "authority_graph": _compact_authority_graph(
            dict(dossier.get("authority_graph", {})) if isinstance(dossier.get("authority_graph"), Mapping) else {},
            node_limit=0 if packet_mode else 8,
            edge_limit=0 if packet_mode else 10,
        ),
        "blast_radius": blast_radius,
        "operator_consequences": _compact_historical_bucket(
            dossier.get("operator_consequences", []) if isinstance(dossier.get("operator_consequences"), list) else [],
            limit=consequence_limit,
            fields=("source", "summary"),
        ),
        "contract_touchpoints": _compact_historical_bucket(
            dossier.get("contract_touchpoints", []) if isinstance(dossier.get("contract_touchpoints"), list) else [],
            limit=touchpoint_limit,
            fields=("path", "kind", "source", "diagram_id"),
        ),
        "validation_obligations": _compact_historical_bucket(
            dossier.get("validation_obligations", []) if isinstance(dossier.get("validation_obligations"), list) else [],
            limit=obligation_limit,
            fields=("kind", "summary", "path", "test_path"),
        ),
        "operator_consequence_count": len(dossier.get("operator_consequences", []))
        if isinstance(dossier.get("operator_consequences"), list)
        else 0,
        "contract_touchpoint_count": len(dossier.get("contract_touchpoints", []))
        if isinstance(dossier.get("contract_touchpoints"), list)
        else 0,
        "validation_obligation_count": len(dossier.get("validation_obligations", []))
        if isinstance(dossier.get("validation_obligations"), list)
        else 0,
        "historical_evidence": compact_historical,
        "coverage": dict(dossier.get("coverage", {})) if isinstance(dossier.get("coverage"), Mapping) else {},
        "benchmark_summary": dict(dossier.get("benchmark_summary", {})) if isinstance(dossier.get("benchmark_summary"), Mapping) else {},
        "execution_hint": dict(dossier.get("execution_hint", {})) if isinstance(dossier.get("execution_hint"), Mapping) else {},
        "unresolved_questions": _dedupe_strings(dossier.get("unresolved_questions", []))[: (2 if packet_mode else 4)]
        if isinstance(dossier.get("unresolved_questions"), list)
        else [],
        "unresolved_question_count": len(dossier.get("unresolved_questions", []))
        if isinstance(dossier.get("unresolved_questions"), list)
        else 0,
        "full_scan_recommended": bool(dossier.get("full_scan_recommended")),
        "full_scan_reason": str(dossier.get("full_scan_reason", "")).strip(),
    }
    raw_required_reads = (
        _dedupe_strings(dossier.get("required_reads", []))
        if isinstance(dossier.get("required_reads"), list)
        else []
    )
    if packet_mode:
        preferred_required_reads = [
            token
            for token in raw_required_reads
            if token
            and token not in compacted["changed_paths"]
            and not str(token).strip().startswith(("src/", "tests/"))
        ]
        if preferred_required_reads:
            raw_required_reads = preferred_required_reads
    compacted["required_reads"] = raw_required_reads[:required_read_limit]
    compacted["required_read_count"] = len(
        dossier.get("required_reads", [])
        if isinstance(dossier.get("required_reads"), list)
        else raw_required_reads
    )
    if packet_mode:
        compacted.pop("repo_dirty_paths", None)
        compacted.pop("scoped_working_tree_paths", None)
        compacted.pop("diagram_watch_gaps", None)
        compacted.pop("operator_consequences", None)
        compacted.pop("contract_touchpoints", None)
        compacted.pop("validation_obligations", None)
        compacted.pop("unresolved_questions", None)
    if authority_chain_limit > 0:
        compacted["authority_chain"] = _compact_historical_bucket(
            dossier.get("authority_chain", []) if isinstance(dossier.get("authority_chain"), list) else [],
            limit=authority_chain_limit,
            fields=("kind", "relation", "source_label", "target_label", "why"),
        )
    return compacted


def _unresolved_questions(
    *,
    changed_paths: Sequence[str],
    matched_components: Sequence[Mapping[str, Any]],
    contract_touchpoints: Sequence[Mapping[str, Any]],
    diagram_watch_gaps: Sequence[Mapping[str, Any]],
    coverage: Mapping[str, Any],
) -> list[str]:
    rows: list[str] = []
    if diagram_watch_gaps:
        for gap in diagram_watch_gaps[:4]:
            rows.append(
                f"Which Atlas diagram should watch `{str(gap.get('path', '')).strip()}` so this slice is not architecturally invisible?"
            )
    if not matched_components:
        rows.append("Which component actually owns these paths? Architecture mode could not ground them to a component.")
    if not contract_touchpoints:
        rows.append("Which contract, spec, or runbook is authoritative for this slice? No contract touchpoints were grounded.")
    if str(coverage.get("confidence_tier", "")).strip() == "low":
        rows.append("Coverage is too weak to trust this dossier alone. What additional raw source reads are mandatory before changing code?")
    if not rows and changed_paths:
        rows.append("What concrete architectural invariant would be violated if this change were implemented incorrectly?")
    return rows[:8]


def _graph_node(
    *,
    kind: str,
    node_id: str,
    label: str,
    path: str = "",
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "kind": str(kind).strip(),
        "id": str(node_id).strip(),
        "label": str(label).strip() or str(node_id).strip(),
    }
    if str(path).strip():
        payload["path"] = str(path).strip()
    if isinstance(metadata, Mapping) and metadata:
        payload["metadata"] = dict(metadata)
    return payload


def _graph_edge(
    *,
    source_kind: str,
    source_id: str,
    target_kind: str,
    target_id: str,
    relation: str,
    source: str,
) -> dict[str, Any]:
    return {
        "source_kind": str(source_kind).strip(),
        "source_id": str(source_id).strip(),
        "target_kind": str(target_kind).strip(),
        "target_id": str(target_id).strip(),
        "relation": str(relation).strip(),
        "source": str(source).strip(),
    }


def _authority_graph(
    *,
    changed_paths: Sequence[str],
    topology_domains: Sequence[Mapping[str, Any]],
    matched_components: Sequence[Mapping[str, Any]],
    linked_diagrams: Sequence[Mapping[str, Any]],
    contract_touchpoints: Sequence[Mapping[str, Any]],
    related_workstreams: Sequence[Mapping[str, Any]],
    historical_bugs: Sequence[Mapping[str, Any]],
    historical_notes: Sequence[Mapping[str, Any]],
    historical_adrs: Sequence[Mapping[str, Any]],
    historical_runbooks: Sequence[Mapping[str, Any]],
    validation_obligations: Sequence[Mapping[str, Any]],
    traceability_edges: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    nodes: dict[tuple[str, str], dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str, str, str, str]] = set()

    def add_node(*, kind: str, node_id: str, label: str, path: str = "", metadata: Mapping[str, Any] | None = None) -> None:
        key = (str(kind).strip(), str(node_id).strip())
        if not key[0] or not key[1]:
            return
        if key not in nodes:
            nodes[key] = _graph_node(kind=key[0], node_id=key[1], label=label, path=path, metadata=metadata)

    def add_edge(*, source_kind: str, source_id: str, target_kind: str, target_id: str, relation: str, source: str) -> None:
        key = (
            str(source_kind).strip(),
            str(source_id).strip(),
            str(target_kind).strip(),
            str(target_id).strip(),
            str(relation).strip(),
        )
        if not all(key):
            return
        if key in seen_edges:
            return
        seen_edges.add(key)
        edges.append(
            _graph_edge(
                source_kind=key[0],
                source_id=key[1],
                target_kind=key[2],
                target_id=key[3],
                relation=key[4],
                source=source,
            )
        )

    component_ids = {
        str(component.get("component_id", "")).strip()
        for component in matched_components
        if str(component.get("component_id", "")).strip()
    }
    diagram_ids = {
        str(diagram.get("diagram_id", "")).strip()
        for diagram in linked_diagrams
        if str(diagram.get("diagram_id", "")).strip()
    }
    contract_paths = {
        str(row.get("path", "")).strip()
        for row in contract_touchpoints
        if str(row.get("path", "")).strip()
    }
    domain_component_specs: dict[str, list[str]] = {}
    workstream_ids = {
        str(row.get("workstream_id", "")).strip().upper()
        for row in related_workstreams
        if str(row.get("workstream_id", "")).strip()
    }

    for changed_path in changed_paths:
        token = str(changed_path).strip()
        add_node(kind="path", node_id=token, label=token, path=token)
    for domain in topology_domains:
        domain_id = str(domain.get("domain_id", "")).strip()
        add_node(kind="topology_domain", node_id=domain_id, label=str(domain.get("label", "")).strip(), metadata={"summary": str(domain.get("summary", "")).strip()})
        for matched_path in domain.get("matched_paths", []):
            token = str(matched_path).strip()
            add_node(kind="path", node_id=token, label=token, path=token)
            add_edge(
                source_kind="topology_domain",
                source_id=domain_id,
                target_kind="path",
                target_id=token,
                relation="governs_path",
                source="topology_domain_rule",
            )
        for component_id in domain.get("matched_components", []):
            token = str(component_id).strip()
            add_node(kind="component", node_id=token, label=token)
            add_edge(
                source_kind="topology_domain",
                source_id=domain_id,
                target_kind="component",
                target_id=token,
                relation="governs_component",
                source="topology_domain_rule",
            )
    for component in matched_components:
        component_id = str(component.get("component_id", "")).strip()
        add_node(
            kind="component",
            node_id=component_id,
            label=str(component.get("title", "")).strip() or component_id,
            path=str(component.get("spec_ref", "")).strip(),
            metadata={"owner": str(component.get("owner", "")).strip(), "product_layer": str(component.get("product_layer", "")).strip()},
        )
        for changed_path in changed_paths:
            token = str(changed_path).strip()
            if any(
                _path_touches_watch(changed_path=token, watch_path=str(prefix).strip())
                for prefix in component.get("path_prefixes", [])
                if str(prefix).strip()
            ):
                add_node(kind="path", node_id=token, label=token, path=token)
                add_edge(
                    source_kind="path",
                    source_id=token,
                    target_kind="component",
                    target_id=component_id,
                    relation="grounded_to_component",
                    source="component_path_prefix",
                )
        for diagram_id in component.get("diagrams", []):
            token = str(diagram_id).strip()
            if token and token in diagram_ids:
                add_node(kind="diagram", node_id=token, label=token)
                add_edge(
                    source_kind="component",
                    source_id=component_id,
                    target_kind="diagram",
                    target_id=token,
                    relation="documented_by_diagram",
                    source="component_metadata",
                )
        for workstream_id in component.get("workstreams", []):
            token = str(workstream_id).strip().upper()
            if token and token in workstream_ids:
                add_node(kind="workstream", node_id=token, label=token)
                add_edge(
                    source_kind="component",
                    source_id=component_id,
                    target_kind="workstream",
                    target_id=token,
                    relation="owned_by_workstream",
                    source="component_metadata",
                )
    for diagram in linked_diagrams:
        diagram_id = str(diagram.get("diagram_id", "")).strip()
        add_node(
            kind="diagram",
            node_id=diagram_id,
            label=str(diagram.get("title", "")).strip() or diagram_id,
            path=str(diagram.get("path", "")).strip(),
            metadata={"relation": str(diagram.get("relation", "")).strip()},
        )
        for matched_path in diagram.get("matched_paths", []):
            token = str(matched_path).strip()
            add_node(kind="path", node_id=token, label=token, path=token)
            add_edge(
                source_kind="path",
                source_id=token,
                target_kind="diagram",
                target_id=diagram_id,
                relation="watched_by_diagram",
                source="diagram_watch_paths",
            )
    for touchpoint in contract_touchpoints:
        path = str(touchpoint.get("path", "")).strip()
        kind = str(touchpoint.get("kind", "")).strip() or "document"
        add_node(kind=kind, node_id=path, label=path, path=path, metadata={"source": str(touchpoint.get("source", "")).strip()})
        component_id = str(touchpoint.get("component_id", "")).strip()
        diagram_id = str(touchpoint.get("diagram_id", "")).strip()
        domain_id = str(touchpoint.get("domain_id", "")).strip()
        if kind == "component_spec" and domain_id:
            domain_component_specs.setdefault(domain_id, [])
            if path and path not in domain_component_specs[domain_id]:
                domain_component_specs[domain_id].append(path)
        if component_id:
            add_edge(
                source_kind="component",
                source_id=component_id,
                target_kind=kind,
                target_id=path,
                relation="touches_contract",
                source=str(touchpoint.get("source", "")).strip() or "contract_touchpoint",
            )
        if diagram_id:
            add_edge(
                source_kind="diagram",
                source_id=diagram_id,
                target_kind=kind,
                target_id=path,
                relation="touches_related_doc",
                source=str(touchpoint.get("source", "")).strip() or "diagram_touchpoint",
            )
    for runbook in historical_runbooks:
        path = str(runbook.get("path", "")).strip()
        add_node(kind="runbook", node_id=path, label=path, path=path)
        component_id = str(runbook.get("component_id", "")).strip()
        if component_id:
            add_edge(
                source_kind="component",
                source_id=component_id,
                target_kind="runbook",
                target_id=path,
                relation="historical_runbook",
                source=str(runbook.get("source", "")).strip() or "contract_touchpoint",
            )
    for workstream in related_workstreams:
        workstream_id = str(workstream.get("workstream_id", "")).strip().upper()
        add_node(kind="workstream", node_id=workstream_id, label=str(workstream.get("title", "")).strip() or workstream_id)
    for bug in historical_bugs:
        bug_key = str(bug.get("bug_key", "")).strip()
        bug_id = str(bug.get("bug_id", "")).strip()
        bug_node_id = bug_id or bug_key
        bug_label = " ".join(token for token in (bug_id, str(bug.get("title", "")).strip() or bug_key) if token).strip()
        add_node(kind="bug", node_id=bug_node_id, label=bug_label or bug_node_id)
        for component_id in component_ids:
            add_edge(
                source_kind="component",
                source_id=component_id,
                target_kind="bug",
                target_id=bug_node_id,
                relation="historical_incident",
                source="bug_history",
            )
    for note in historical_notes:
        note_id = str(note.get("note_id", "")).strip()
        add_node(kind="note", node_id=note_id, label=str(note.get("title", "")).strip() or note_id, path=str(note.get("source_path", "")).strip())
        for component_id in component_ids:
            add_edge(
                source_kind="component",
                source_id=component_id,
                target_kind="note",
                target_id=note_id,
                relation="historical_note",
                source="engineering_note",
            )
    for note in historical_adrs:
        note_id = str(note.get("note_id", "")).strip()
        add_node(kind="adr", node_id=note_id, label=str(note.get("title", "")).strip() or note_id, path=str(note.get("source_path", "")).strip())
        for component_id in component_ids:
            add_edge(
                source_kind="component",
                source_id=component_id,
                target_kind="adr",
                target_id=note_id,
                relation="architectural_decision",
                source="engineering_note",
            )
    for obligation in validation_obligations:
        obligation_id = str(obligation.get("summary", "")).strip()
        obligation_kind = str(obligation.get("kind", "")).strip() or "validation"
        add_node(kind=obligation_kind, node_id=obligation_id, label=obligation_id, path=str(obligation.get("path", "")).strip())
        component_id = str(obligation.get("component_id", "")).strip()
        diagram_id = str(obligation.get("diagram_id", "")).strip()
        if component_id:
            add_edge(
                source_kind="component",
                source_id=component_id,
                target_kind=obligation_kind,
                target_id=obligation_id,
                relation="validated_by",
                source="validation_obligation",
            )
        if diagram_id:
            add_edge(
                source_kind="diagram",
                source_id=diagram_id,
                target_kind=obligation_kind,
                target_id=obligation_id,
                relation="reviewed_by",
                source="validation_obligation",
            )

    seed_tokens = {token for _kind, token in nodes}
    traceability_count = 0
    for edge in traceability_edges:
        source_kind = str(edge.get("source_kind", "")).strip() or "artifact"
        source_id = str(edge.get("source_id", "")).strip() or str(edge.get("source_path", "")).strip()
        target_kind = str(edge.get("target_kind", "")).strip() or "artifact"
        target_id = str(edge.get("target_id", "")).strip()
        source_path = str(edge.get("source_path", "")).strip()
        if not source_id or not target_id:
            continue
        if (
            source_id not in seed_tokens
            and target_id not in seed_tokens
            and source_path not in seed_tokens
            and not any(_path_touches_watch(changed_path=path, watch_path=source_path) for path in changed_paths if source_path)
        ):
            continue
        add_node(kind=source_kind, node_id=source_id, label=source_id, path=source_path)
        add_node(kind=target_kind, node_id=target_id, label=target_id, path=target_id if "/" in target_id else "")
        add_edge(
            source_kind=source_kind,
            source_id=source_id,
            target_kind=target_kind,
            target_id=target_id,
            relation=str(edge.get("relation", "")).strip() or "related_to",
            source="traceability_edge",
        )
        traceability_count += 1

    for domain in topology_domains:
        domain_id = str(domain.get("domain_id", "")).strip()
        component_spec_paths = domain_component_specs.get(domain_id, [])
        if not component_spec_paths:
            continue
        for matched_path in domain.get("matched_paths", []):
            token = str(matched_path).strip()
            if not token:
                continue
            has_component_grounding = any(
                str(edge.get("source_kind", "")).strip() == "path"
                and str(edge.get("source_id", "")).strip() == token
                and str(edge.get("target_kind", "")).strip() == "component"
                for edge in edges
            )
            has_traceability_support = any(
                str(edge.get("source", "")).strip() == "traceability_edge"
                and (
                    (
                        str(edge.get("source_kind", "")).strip() == "path"
                        and str(edge.get("source_id", "")).strip() == token
                    )
                    or (
                        str(edge.get("target_kind", "")).strip() == "path"
                        and str(edge.get("target_id", "")).strip() == token
                    )
                )
                for edge in edges
            )
            if has_component_grounding or has_traceability_support:
                continue
            for spec_path in component_spec_paths:
                add_node(
                    kind="component_spec",
                    node_id=spec_path,
                    label=spec_path,
                    path=spec_path,
                    metadata={"source": "topology_domain"},
                )
                previous_edge_count = len(edges)
                add_edge(
                    source_kind="path",
                    source_id=token,
                    target_kind="component_spec",
                    target_id=spec_path,
                    relation="documented_by_spec",
                    source="topology_domain_traceability",
                )
                if len(edges) > previous_edge_count:
                    traceability_count += 1
                break

    node_rows = list(nodes.values())
    node_rows.sort(key=lambda row: (str(row.get("kind", "")).strip(), str(row.get("id", "")).strip()))
    edges.sort(
        key=lambda row: (
            str(row.get("source_kind", "")).strip(),
            str(row.get("source_id", "")).strip(),
            str(row.get("relation", "")).strip(),
            str(row.get("target_kind", "")).strip(),
            str(row.get("target_id", "")).strip(),
        )
    )
    return {
        "nodes": node_rows[:40],
        "edges": edges[:64],
        "counts": {
            "nodes": len(node_rows),
            "edges": len(edges),
            "traceability_edges": traceability_count,
        },
    }


def _enrich_coverage_with_authority_graph(
    *,
    coverage: Mapping[str, Any],
    changed_paths: Sequence[str],
    authority_graph: Mapping[str, Any],
) -> dict[str, Any]:
    path_support: dict[str, int] = {str(path).strip(): 0 for path in changed_paths if str(path).strip()}
    for edge in authority_graph.get("edges", []):
        if not isinstance(edge, Mapping):
            continue
        source_kind = str(edge.get("source_kind", "")).strip()
        source_id = str(edge.get("source_id", "")).strip()
        target_kind = str(edge.get("target_kind", "")).strip()
        target_id = str(edge.get("target_id", "")).strip()
        if source_kind == "path" and source_id in path_support and target_kind != "path":
            path_support[source_id] += 1
        if target_kind == "path" and target_id in path_support and source_kind != "path":
            path_support[target_id] += 1
    total_paths = max(1, len(path_support))
    supported_paths = sum(1 for count in path_support.values() if count > 0)
    support_ratio = round(supported_paths / total_paths, 3)
    enriched = dict(coverage)
    enriched["authority_graph_coverage"] = {
        "matched_paths": supported_paths,
        "total_paths": total_paths,
        "ratio": support_ratio,
        "traceability_edges": int(dict(authority_graph.get("counts", {})).get("traceability_edges", 0) or 0)
        if isinstance(authority_graph.get("counts"), Mapping)
        else 0,
    }
    enriched["score"] = max(
        0,
        min(
            100,
            int(
                round(
                    float(enriched.get("score", 0) or 0)
                    + min(8.0, (support_ratio * 5.0) + min(3.0, float(enriched["authority_graph_coverage"]["traceability_edges"]) / 4.0))
                )
            ),
        ),
    )
    return enriched


def _execution_hint(
    *,
    topology_domains: Sequence[Mapping[str, Any]],
    coverage: Mapping[str, Any],
    full_scan_recommended: bool,
) -> dict[str, Any]:
    high_risk = any(str(row.get("risk_tier", "")).strip().lower() == "high" for row in topology_domains)
    confidence_tier = str(coverage.get("confidence_tier", "")).strip()
    unresolved_edge_count = int(coverage.get("unresolved_edge_count", 0) or 0)
    if high_risk and (full_scan_recommended or confidence_tier == "low" or unresolved_edge_count > 0):
        return {
            "mode": "local_only",
            "model": "gpt-5.4",
            "reasoning_effort": "high",
            "fanout": "no_fanout",
            "risk_tier": "high",
            "why": "High-risk architecture slice with incomplete coverage should stay local and fully grounded.",
        }
    if high_risk:
        return {
            "mode": "local_or_single_leaf",
            "model": "gpt-5.4",
            "reasoning_effort": "high",
            "fanout": "bounded_single_leaf_only",
            "risk_tier": "high",
            "why": "High-risk architecture slice is grounded enough for deeper reasoning, but delegation should stay tightly bounded.",
        }
    if confidence_tier == "high":
        return {
            "mode": "bounded_analysis",
            "model": "gpt-5.4-mini",
            "reasoning_effort": "medium",
            "fanout": "optional",
            "risk_tier": "moderate",
            "why": "Coverage is strong and the slice is not in a highest-risk topology domain.",
        }
    return {
        "mode": "local_grounding_first",
        "model": "gpt-5.4-mini",
        "reasoning_effort": "medium",
        "fanout": "no_fanout",
        "risk_tier": "moderate",
        "why": "Coverage is partial; narrow and ground further before delegation.",
    }


def _architecture_benchmark_summary(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    topology_domains: Sequence[Mapping[str, Any]],
    coverage: Mapping[str, Any],
    contract_touchpoints: Sequence[Mapping[str, Any]],
    full_scan_recommended: bool,
) -> dict[str, Any]:
    cases = _load_architecture_benchmark_cases(repo_root=repo_root)
    changed = {str(path).strip() for path in changed_paths if str(path).strip()}
    domains = {str(row.get("domain_id", "")).strip() for row in topology_domains if str(row.get("domain_id", "")).strip()}
    matched_case_ids: list[str] = []
    drift_case_ids: list[str] = []
    satisfied_case_count = 0
    for case in cases:
        match_spec = dict(case.get("match", {})) if isinstance(case.get("match"), Mapping) else {}
        paths_any = {str(token).strip() for token in match_spec.get("paths_any", []) if str(token).strip()} if isinstance(match_spec.get("paths_any"), list) else set()
        paths_all = {str(token).strip() for token in match_spec.get("paths_all", []) if str(token).strip()} if isinstance(match_spec.get("paths_all"), list) else set()
        domains_any = {str(token).strip() for token in match_spec.get("domains_any", []) if str(token).strip()} if isinstance(match_spec.get("domains_any"), list) else set()
        if paths_all and not paths_all.issubset(changed):
            continue
        if paths_any and not changed.intersection(paths_any):
            continue
        if domains_any and not domains.intersection(domains_any):
            continue
        case_id = str(case.get("case_id", "")).strip()
        if case_id:
            matched_case_ids.append(case_id)
        expect = dict(case.get("expect", {})) if isinstance(case.get("expect"), Mapping) else {}
        ok = True
        expected_confidence = {str(token).strip() for token in expect.get("confidence_tier", []) if str(token).strip()} if isinstance(expect.get("confidence_tier"), list) else {str(expect.get("confidence_tier", "")).strip()} if str(expect.get("confidence_tier", "")).strip() else set()
        if expected_confidence and str(coverage.get("confidence_tier", "")).strip() not in expected_confidence:
            ok = False
        if "full_scan_recommended" in expect and bool(expect.get("full_scan_recommended")) != bool(full_scan_recommended):
            ok = False
        if "contract_touchpoints_min" in expect and len(contract_touchpoints) < int(expect.get("contract_touchpoints_min", 0) or 0):
            ok = False
        if ok:
            satisfied_case_count += 1
        elif case_id:
            drift_case_ids.append(case_id)
    return {
        "matched_case_count": len(matched_case_ids),
        "satisfied_case_count": satisfied_case_count,
        "matched_case_ids": matched_case_ids,
        "drift_case_ids": drift_case_ids,
    }


def build_architecture_dossier(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    explicit_paths: Sequence[str] = (),
    repo_dirty_paths: Sequence[str] = (),
    scoped_working_tree_paths: Sequence[str] = (),
    working_tree_scope: str = "",
    working_tree_scope_degraded: bool = False,
    detail_level: str = _DEFAULT_ARCHITECTURE_DETAIL_LEVEL,
) -> dict[str, Any]:
    detail = _normalize_detail_level(detail_level)
    root = Path(repo_root).resolve()
    stage_timings: dict[str, float] = {}
    stage_started = time.perf_counter()
    bundle = load_architecture_bundle(repo_root=root)
    stage_timings["bundle_load"] = _elapsed_ms(stage_started)
    if not bool(bundle.get("ready")):
        payload = {
            "resolved": False,
            "changed_paths": [str(token).strip() for token in changed_paths if str(token).strip()],
            "explicit_paths": [str(token).strip() for token in explicit_paths if str(token).strip()],
            "repo_dirty_paths": [str(token).strip() for token in repo_dirty_paths if str(token).strip()],
            "scoped_working_tree_paths": [str(token).strip() for token in scoped_working_tree_paths if str(token).strip()],
            "working_tree_scope": str(working_tree_scope or "").strip(),
            "working_tree_scope_degraded": bool(working_tree_scope_degraded),
            "topology_domains": [],
            "linked_components": [],
            "linked_diagrams": [],
            "required_reads": [],
            "diagram_watch_gaps": [],
            "authority_chain": [],
            "blast_radius": {"counts": {}},
            "operator_consequences": [],
            "contract_touchpoints": [],
            "validation_obligations": [],
            "historical_evidence": {"bugs": [], "runbooks": [], "adrs": [], "notes": [], "workstreams": []},
            "coverage": {
                "path_coverage": {"matched": 0, "total": max(1, len(changed_paths)), "ratio": 0.0},
                "diagram_coverage": {"matched": 0, "total": max(1, len(changed_paths)), "ratio": 0.0},
                "contract_coverage": {"matched": 0, "total": max(1, len(changed_paths)), "ratio": 0.0},
                "ownership_coverage": {"matched_components": 0, "total_components": 0, "ratio": 0.0},
                "authority_graph_coverage": {"matched_paths": 0, "total_paths": max(1, len(changed_paths)), "ratio": 0.0, "traceability_edges": 0},
                "unresolved_edge_count": len([token for token in changed_paths if str(token).strip()]),
                "score": 0,
                "confidence_tier": "low",
            },
            "benchmark_summary": {
                "matched_case_count": 0,
                "satisfied_case_count": 0,
                "matched_case_ids": [],
                "drift_case_ids": [],
            },
            "execution_hint": {
                "mode": "local_only",
                "model": "gpt-5.4",
                "reasoning_effort": "high",
                "fanout": "no_fanout",
                "risk_tier": "high",
                "why": "Architecture bundle is unavailable, so the slice cannot be trusted without direct source reads.",
            },
            "unresolved_questions": [
                "Why is the compiled architecture bundle unavailable for this repo slice?",
            ],
            "full_scan_recommended": True,
            "full_scan_reason": "architecture_bundle_unavailable",
        }
        payload["_stage_timings"] = dict(stage_timings)
        if detail == "full":
            return payload
        compacted = _compact_architecture_dossier(payload, detail_level=detail)
        compacted["_stage_timings"] = dict(stage_timings)
        return compacted

    normalized_paths = [str(token).strip() for token in changed_paths if str(token).strip()]
    bugs = [dict(row) for row in bundle.get("bugs", []) if isinstance(row, Mapping)]
    engineering_notes = [dict(row) for row in bundle.get("engineering_notes", []) if isinstance(row, Mapping)]
    tests = [dict(row) for row in bundle.get("tests", []) if isinstance(row, Mapping)]
    stage_started = time.perf_counter()
    structural_core = _cached_architecture_structural_core(
        repo_root=root,
        bundle=bundle,
        changed_paths=normalized_paths,
        tests=tests,
    )
    matched_components = [dict(row) for row in structural_core.get("matched_components", []) if isinstance(row, Mapping)]
    topology_domains = [dict(row) for row in structural_core.get("topology_domains", []) if isinstance(row, Mapping)]
    linked_diagrams = [dict(row) for row in structural_core.get("linked_diagrams", []) if isinstance(row, Mapping)]
    diagram_watch_gaps = [dict(row) for row in structural_core.get("diagram_watch_gaps", []) if isinstance(row, Mapping)]
    contract_touchpoints = [dict(row) for row in structural_core.get("contract_touchpoints", []) if isinstance(row, Mapping)]
    related_workstreams = [dict(row) for row in structural_core.get("related_workstreams", []) if isinstance(row, Mapping)]
    coverage = dict(structural_core.get("coverage", {})) if isinstance(structural_core.get("coverage"), Mapping) else {}
    full_scan_reason = str(structural_core.get("full_scan_reason", "")).strip()
    required_reads = [
        str(token).strip()
        for token in structural_core.get("required_reads", [])
        if str(token).strip()
    ] if isinstance(structural_core.get("required_reads"), list) else []
    operator_consequences = [
        dict(row) for row in structural_core.get("operator_consequences", []) if isinstance(row, Mapping)
    ]
    validation_obligations = [
        dict(row) for row in structural_core.get("validation_obligations", []) if isinstance(row, Mapping)
    ]
    unresolved_questions = _dedupe_strings(structural_core.get("unresolved_questions", []))
    full_scan_recommended = bool(structural_core.get("full_scan_recommended"))
    execution_hint = (
        dict(structural_core.get("execution_hint", {}))
        if isinstance(structural_core.get("execution_hint"), Mapping)
        else {}
    )
    benchmark_summary = (
        dict(structural_core.get("benchmark_summary", {}))
        if isinstance(structural_core.get("benchmark_summary"), Mapping)
        else {}
    )
    stage_timings["structural_core"] = _elapsed_ms(stage_started)

    historical_bugs: list[dict[str, Any]] = []
    historical_notes: list[dict[str, Any]] = []
    historical_adrs: list[dict[str, Any]] = []
    historical_runbooks: list[dict[str, Any]] = []
    authority_graph = (
        dict(structural_core.get("authority_graph", {}))
        if isinstance(structural_core.get("authority_graph"), Mapping)
        else {}
    )
    authority_chain = (
        [dict(row) for row in structural_core.get("authority_chain", []) if isinstance(row, Mapping)]
        if detail != "packet"
        else []
    )
    blast_radius = (
        dict(structural_core.get("blast_radius", {}))
        if isinstance(structural_core.get("blast_radius"), Mapping)
        else {"counts": {}}
    )

    if detail != "packet":
        stage_started = time.perf_counter()
        historical_adrs = _historical_adrs(
            changed_paths=normalized_paths,
            matched_components=matched_components,
            engineering_notes=engineering_notes,
        )
        historical_runbooks = _historical_runbooks(
            topology_domains=topology_domains,
            contract_touchpoints=contract_touchpoints,
        )
        stage_timings["lazy_expansion"] = _elapsed_ms(stage_started)
        blast_counts = dict(blast_radius.get("counts", {})) if isinstance(blast_radius.get("counts"), Mapping) else {}
        blast_counts["runbooks"] = max(int(blast_counts.get("runbooks", 0) or 0), len(historical_runbooks))
        blast_counts["adrs"] = max(int(blast_counts.get("adrs", 0) or 0), len(historical_adrs))
        blast_radius["counts"] = blast_counts

    if detail == "full":
        stage_started = time.perf_counter()
        historical_bugs = _historical_bugs(
            changed_paths=normalized_paths,
            matched_components=matched_components,
            bugs=bugs,
        )
        historical_notes = _historical_notes(
            changed_paths=normalized_paths,
            matched_components=matched_components,
            engineering_notes=engineering_notes,
        )
        operator_consequences = _operator_consequences(
            topology_domains=topology_domains,
            matched_components=matched_components,
            historical_bugs=historical_bugs,
        )
        traceability_seed_tokens = _dedupe_strings(
            [
                *normalized_paths,
                *[str(row.get("domain_id", "")).strip() for row in topology_domains if str(row.get("domain_id", "")).strip()],
                *[str(row.get("component_id", "")).strip() for row in matched_components if str(row.get("component_id", "")).strip()],
                *[str(row.get("diagram_id", "")).strip() for row in linked_diagrams if str(row.get("diagram_id", "")).strip()],
                *[str(row.get("path", "")).strip() for row in contract_touchpoints if str(row.get("path", "")).strip()],
                *[str(row.get("workstream_id", "")).strip().upper() for row in related_workstreams if str(row.get("workstream_id", "")).strip()],
                *[str(row.get("summary", "")).strip() for row in validation_obligations if str(row.get("summary", "")).strip()],
            ]
        )
        relevant_traceability_edges = _relevant_traceability_edges(
            repo_root=root,
            bundle=bundle,
            changed_paths=normalized_paths,
            seed_tokens=traceability_seed_tokens,
        )
        authority_graph = _authority_graph(
            changed_paths=normalized_paths,
            topology_domains=topology_domains,
            matched_components=matched_components,
            linked_diagrams=linked_diagrams,
            contract_touchpoints=contract_touchpoints,
            related_workstreams=related_workstreams,
            historical_bugs=historical_bugs,
            historical_notes=historical_notes,
            historical_adrs=historical_adrs,
            historical_runbooks=historical_runbooks,
            validation_obligations=validation_obligations,
            traceability_edges=relevant_traceability_edges,
        )
        authority_chain = _authority_chain(
            authority_graph=authority_graph,
        ) if detail != "packet" else []
        blast_radius = _blast_radius(
            matched_components=matched_components,
            linked_diagrams=linked_diagrams,
            contract_touchpoints=contract_touchpoints,
            related_workstreams=related_workstreams,
            historical_bugs=historical_bugs,
            authority_graph=authority_graph,
        )
        stage_timings["deep_history_expansion"] = _elapsed_ms(stage_started)

    payload = {
        "resolved": True,
        "changed_paths": normalized_paths,
        "explicit_paths": [str(token).strip() for token in explicit_paths if str(token).strip()],
        "repo_dirty_paths": [str(token).strip() for token in repo_dirty_paths if str(token).strip()],
        "scoped_working_tree_paths": [str(token).strip() for token in scoped_working_tree_paths if str(token).strip()],
        "working_tree_scope": str(working_tree_scope or "").strip(),
        "working_tree_scope_degraded": bool(working_tree_scope_degraded),
        "topology_domains": topology_domains,
        "linked_components": matched_components,
        "linked_diagrams": linked_diagrams,
        "required_reads": required_reads,
        "diagram_watch_gaps": diagram_watch_gaps,
        "authority_graph": authority_graph,
        "authority_chain": authority_chain,
        "blast_radius": blast_radius,
        "operator_consequences": operator_consequences,
        "contract_touchpoints": contract_touchpoints,
        "validation_obligations": validation_obligations,
        "historical_evidence": {
            "bugs": historical_bugs,
            "runbooks": historical_runbooks,
            "adrs": historical_adrs,
            "notes": historical_notes,
            "workstreams": related_workstreams,
        },
        "coverage": coverage,
        "benchmark_summary": benchmark_summary,
        "execution_hint": execution_hint,
        "unresolved_questions": unresolved_questions,
        "full_scan_recommended": full_scan_recommended,
        "full_scan_reason": full_scan_reason,
        "_stage_timings": stage_timings,
    }
    if detail == "full":
        return payload
    compacted = _compact_architecture_dossier(payload, detail_level=detail)
    compacted["_stage_timings"] = dict(stage_timings)
    return compacted


__all__ = [
    "ARCHITECTURE_BUNDLE_FILENAME",
    "ARCHITECTURE_BUNDLE_VERSION",
    "TOPOLOGY_DOMAIN_RULES",
    "build_architecture_bundle",
    "build_architecture_dossier",
    "bundle_path",
    "compiler_root",
    "load_architecture_bundle",
    "prime_architecture_projection_cache",
]
