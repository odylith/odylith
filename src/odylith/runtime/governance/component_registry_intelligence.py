"""Shared component-registry intelligence for Registry/Registry governance paths.

This module centralizes component inventory normalization and agent-stream
component-mapping logic so renderer, validator, timeline logger, and sync
orchestration do not drift. Registry forensic evidence is intentionally sourced
from two paths:

- explicit Compass timeline events for durable decision/implementation
  narratives; and
- synthetic recent workspace activity for meaningful, component-mapped local
  changes that have not yet been written into Compass.

Key contracts:
- First-class inventory source of truth is curated/reviewed manifest entries.
- Candidate extraction from catalog/ideas/stream is explicit and non-promoting.
- Meaningful activity is inferred from non-generated artifact paths and/or
  explicit workstream linkage.
- Component mapping confidence uses deterministic precedence:
  explicit/artifact > workstream > summary token matches.
- Synthetic workspace activity remains forensic-only; it must not replace
  explicit Compass narrative capture or pollute requirements-trace sync.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import parse_qs, urlparse

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.common.consumer_profile import is_component_forensics_path
from odylith.runtime.common.consumer_profile import truth_root_path
from odylith.runtime.common.guidance_paths import has_project_guidance
from odylith.runtime.governance import validate_backlog_contract as backlog_contract
from odylith.runtime.governance import workstream_inference
from odylith.runtime.governance.component_registry_path_aliases import equivalent_component_artifact_tokens
from odylith.runtime.governance.component_registry_review_policy import (
    catalog_component_requests_inventory_review,
)

DEFAULT_MANIFEST_PATH = "odylith/registry/source/component_registry.v1.json"
DEFAULT_CATALOG_PATH = "odylith/atlas/source/catalog/diagrams.v1.json"
DEFAULT_IDEAS_ROOT = "odylith/radar/source/ideas"
DEFAULT_STREAM_PATH = agent_runtime_contract.AGENT_STREAM_PATH
DEFAULT_TRACEABILITY_GRAPH_PATH = "odylith/radar/traceability-graph.v1.json"
DEFAULT_WORKSPACE_ACTIVITY_WINDOW_HOURS = 48


def default_manifest_path(*, repo_root: Path) -> Path:
    root = Path(repo_root).resolve()
    return truth_root_path(repo_root=root, key="component_registry")


def _is_source_product_repo(repo_root: Path) -> bool:
    root = Path(repo_root).resolve()
    return (root / "src" / "odylith").is_dir()

_COMPONENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_WORKSTREAM_ID_RE = re.compile(r"^B-\d{3,}$")
_DIAGRAM_ID_RE = re.compile(r"^D-\d{3,}$")
_CODE_SPAN_RE = re.compile(r"`([^`]+)`")
_TOKEN_SPLIT_RE = re.compile(r"[\n,;|]")
_WORD_GAP_RE = re.compile(r"[^a-z0-9]+")
_FEATURE_HISTORY_ENTRY_RE = re.compile(r"^\s*-\s*(\d{4}-\d{2}-\d{2})\s*:\s*(.+?)\s*$")
_FEATURE_HISTORY_PLAN_REF_RE = re.compile(r"\[(B-\d{3,})\]\(([^)]+)\)")
_FEATURE_HISTORY_PLAN_ROUTE_RE = re.compile(r"(?:^|.*/)?odylith/radar/radar\.html$", re.I)
_FEATURE_HISTORY_PLAN_ROUTE_VERSION = "radar-html-v1"
_PRODUCT_LAYER_NORMALIZATION_VERSION = "consumer-distro-suffix-v1"
_RADAR_IDEA_CONTRACT_VERSION = "v0.1.11"
_COMPONENT_INDEX_CACHE_VERSION = "v2"
_COMPONENT_REPORT_CACHE_VERSION = "v4"
_SKILL_TRIGGER_HEADING_RE = re.compile(r"^###\s+(.+?)\s*$", re.I)
_SKILL_TRIGGER_ITEM_RE = re.compile(r"^\s*-\s*`([^`]+)`\s*$")
_SKILL_TRIGGER_PHRASE_RE = re.compile(r'^\s*-\s*"([^"]+)"\s*$')
_SKILL_TRIGGER_INLINE_RE = re.compile(r"^\s*-\s*Trigger phrases:\s*(.+?)\s*$", re.I)

_COMPONENT_CATEGORIES: frozenset[str] = frozenset(
    {
        "data",
        "governance_engine",
        "governance_surface",
        "control_gate",
        "infrastructure",
    }
)
_COMPONENT_QUALIFICATIONS: frozenset[str] = frozenset(
    {
        "candidate",
        "curated",
    }
)
_PRODUCT_LAYERS: frozenset[str] = frozenset(
    {
        "shell_host",
        "evidence_surface",
        "memory_retrieval",
        "intelligence",
        "agent_execution",
        "cli_bootstrap",
        "optional_remote_control_plane",
        "consumer_distro",
    }
)
_FIRST_CLASS_QUALIFICATIONS: frozenset[str] = frozenset({"candidate", "curated"})
_GOVERNANCE_NON_MEANINGFUL_SUMMARY_PREFIXES: tuple[str, ...] = (
    "phase advanced:",
    "plan binding:",
)
_FORENSIC_ONLY_KINDS: frozenset[str] = frozenset({"workspace_activity"})


@dataclass(frozen=True)
class ComponentEntry:
    """Normalized component inventory entry."""

    component_id: str
    name: str
    kind: str
    category: str
    qualification: str
    aliases: list[str]
    path_prefixes: list[str]
    workstreams: list[str]
    diagrams: list[str]
    owner: str
    status: str
    what_it_is: str
    why_tracked: str
    spec_ref: str
    sources: list[str]
    subcomponents: list[str] = field(default_factory=list)
    product_layer: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ComponentSpecSnapshot:
    """Canonical spec snapshot rendered in Registry detail views."""

    title: str
    last_updated: str
    feature_history: list[dict[str, Any]]
    markdown: str
    skill_trigger_tiers: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    skill_trigger_structure: str = "legacy"
    validation_playbook_commands: list[dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class MappedEvent:
    """Agent-stream event with derived component linkage metadata."""

    event_index: int
    ts_iso: str
    kind: str
    summary: str
    workstreams: list[str]
    artifacts: list[str]
    explicit_components: list[str]
    mapped_components: list[str]
    confidence: str
    meaningful: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ComponentForensicCoverage:
    """Summarize whether a tracked component has usable forensic evidence.

    The Registry renderer needs a mechanically-derived answer to two operator
    questions:

    - does this component currently have forensic coverage; and
    - if not, which evidence channels are empty?

    Coverage is intentionally split between live evidence channels and the
    documented baseline preserved in each living component spec.

    Live evidence channels remain the first-class answer for "is this
    component actively represented in forensics right now?":

    - explicit Compass timeline events;
    - synthetic recent workspace path matches; and
    - mapped workstream-linked evidence from any timeline event.

    When those channels are empty, Registry can still distinguish a component
    with dated spec history from one with no usable forensic baseline at all.
    """

    status: str
    timeline_event_count: int
    explicit_event_count: int
    recent_path_match_count: int
    mapped_workstream_evidence_count: int
    spec_history_event_count: int
    empty_reasons: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ComponentRegistryReport:
    """End-to-end component mapping report from inventory + stream."""

    components: dict[str, ComponentEntry]
    mapped_events: list[MappedEvent]
    unmapped_meaningful_events: list[MappedEvent]
    candidate_queue: list[dict[str, str]]
    forensic_coverage: dict[str, ComponentForensicCoverage]
    diagnostics: list[str]

    def as_dict(self) -> dict[str, Any]:
        timelines = build_component_timelines(
            component_index=self.components,
            mapped_events=self.mapped_events,
        )
        return {
            "components": [
                self.components[key].as_dict()
                for key in sorted(self.components)
            ],
            "mapped_events": [row.as_dict() for row in self.mapped_events],
            "events": [row.as_dict() for row in self.mapped_events],
            "unmapped_meaningful_events": [row.as_dict() for row in self.unmapped_meaningful_events],
            "component_timelines": {
                key: [row.as_dict() for row in rows]
                for key, rows in timelines.items()
            },
            "forensic_coverage": {
                key: self.forensic_coverage[key].as_dict()
                for key in sorted(self.forensic_coverage)
            },
            "diagnostics": list(self.diagnostics),
            "counts": {
                "components": len(self.components),
                "events": len(self.mapped_events),
                "meaningful_events": sum(1 for row in self.mapped_events if row.meaningful),
                "mapped_meaningful_events": sum(
                    1
                    for row in self.mapped_events
                    if row.meaningful and bool(row.mapped_components)
                ),
                "unmapped_meaningful_events": len(self.unmapped_meaningful_events),
                "candidate_queue": len(self.candidate_queue),
                "forensic_coverage_present": sum(
                    1
                    for row in self.forensic_coverage.values()
                    if row.status == "forensic_coverage_present"
                ),
                "baseline_forensic_only": sum(
                    1
                    for row in self.forensic_coverage.values()
                    if row.status == "baseline_forensic_only"
                ),
                "tracked_but_evidence_empty": sum(
                    1
                    for row in self.forensic_coverage.values()
                    if row.status == "tracked_but_evidence_empty"
                ),
            },
            "candidate_queue": list(self.candidate_queue),
        }


def _component_entry_from_payload(payload: Mapping[str, Any]) -> ComponentEntry:
    return ComponentEntry(
        component_id=str(payload.get("component_id", "")).strip(),
        name=str(payload.get("name", "")).strip(),
        kind=str(payload.get("kind", "")).strip(),
        category=str(payload.get("category", "")).strip(),
        qualification=str(payload.get("qualification", "")).strip(),
        aliases=[str(token) for token in payload.get("aliases", [])] if isinstance(payload.get("aliases"), list) else [],
        path_prefixes=[str(token) for token in payload.get("path_prefixes", [])] if isinstance(payload.get("path_prefixes"), list) else [],
        workstreams=[str(token) for token in payload.get("workstreams", [])] if isinstance(payload.get("workstreams"), list) else [],
        diagrams=[str(token) for token in payload.get("diagrams", [])] if isinstance(payload.get("diagrams"), list) else [],
        owner=str(payload.get("owner", "")).strip(),
        status=str(payload.get("status", "")).strip(),
        what_it_is=str(payload.get("what_it_is", "")).strip(),
        why_tracked=str(payload.get("why_tracked", "")).strip(),
        spec_ref=str(payload.get("spec_ref", "")).strip(),
        sources=[str(token) for token in payload.get("sources", [])] if isinstance(payload.get("sources"), list) else [],
        subcomponents=[str(token) for token in payload.get("subcomponents", [])] if isinstance(payload.get("subcomponents"), list) else [],
        product_layer=str(payload.get("product_layer", "")).strip(),
    )


def _cached_component_index_payload(
    *,
    repo_root: Path,
    manifest_path: Path,
    catalog_path: Path,
    ideas_root: Path,
    include_idea_candidates: bool,
) -> tuple[Path, str]:
    key = odylith_context_cache.fingerprint_payload(
        {
            "component_index_cache_version": _COMPONENT_INDEX_CACHE_VERSION,
            "feature_history_plan_route_version": _FEATURE_HISTORY_PLAN_ROUTE_VERSION,
            "product_layer_normalization_version": _PRODUCT_LAYER_NORMALIZATION_VERSION,
            "radar_idea_contract_version": _RADAR_IDEA_CONTRACT_VERSION,
            "manifest": odylith_context_cache.path_signature(manifest_path),
            "catalog": odylith_context_cache.path_signature(catalog_path),
            "ideas": odylith_context_cache.fingerprint_tree(ideas_root, glob="*.md"),
            "manifest_spec_refs": _manifest_spec_ref_signatures(
                repo_root=repo_root,
                manifest_path=manifest_path,
            ),
            "include_idea_candidates": bool(include_idea_candidates),
        }
    )
    cache_file = odylith_context_cache.cache_path(
        repo_root=repo_root,
        namespace="registry/component-index",
        key="component-index",
    )
    return cache_file, key


def _resolve(repo_root: Path, token: str) -> Path:
    path = Path(str(token or "").strip())
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _manifest_spec_ref_signatures(*, repo_root: Path, manifest_path: Path) -> list[dict[str, Any]]:
    """Return existence/signature data for manifest-linked component specs.

    Component-index and component-report caches must invalidate when a manifest
    `spec_ref` file is created, removed, or changed, otherwise validators can
    keep serving stale "spec_ref missing" diagnostics after the file lands.
    """

    if not manifest_path.is_file():
        return []
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(payload, Mapping):
        return []
    components = payload.get("components", [])
    if not isinstance(components, list):
        return []
    signatures: list[dict[str, Any]] = []
    for raw in components:
        if not isinstance(raw, Mapping):
            continue
        spec_ref = str(raw.get("spec_ref", "")).strip()
        if not spec_ref:
            continue
        resolved = _resolve(repo_root, spec_ref)
        exists = resolved.is_file()
        try:
            repo_path = resolved.relative_to(repo_root).as_posix()
        except ValueError:
            repo_path = str(resolved)
        signatures.append(
            {
                "component_id": normalize_component_id(str(raw.get("component_id", "")).strip()) or spec_ref,
                "spec_ref": spec_ref,
                "resolved_path": repo_path,
                "exists": exists,
                "signature": odylith_context_cache.path_signature(resolved) if exists else "missing",
            }
        )
    return signatures


def _slugify(token: str) -> str:
    lowered = str(token or "").strip().lower()
    if not lowered:
        return ""
    collapsed = _WORD_GAP_RE.sub("-", lowered).strip("-")
    return collapsed


def normalize_component_id(value: str) -> str:
    token = _slugify(value)
    if not token:
        return ""
    if _COMPONENT_ID_RE.fullmatch(token):
        return token
    return ""


def normalize_workstream_id(value: str) -> str:
    token = str(value or "").strip().upper()
    if _WORKSTREAM_ID_RE.fullmatch(token):
        return token
    return ""


def normalize_diagram_id(value: str) -> str:
    token = str(value or "").strip().upper()
    if _DIAGRAM_ID_RE.fullmatch(token):
        return token
    return ""


def _dedupe_stable(values: Iterable[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = str(raw or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def _append_unique(target: list[str], value: str) -> None:
    token = str(value or "").strip()
    if not token or token in target:
        return
    target.append(token)


def _extend_unique(target: list[str], values: Iterable[str]) -> None:
    for value in values:
        _append_unique(target, str(value or ""))


def _normalize_taxonomy_token(value: str) -> str:
    return _slugify(value).replace("-", "_")


def _default_category_for_kind(kind: str) -> str:
    token = _normalize_taxonomy_token(kind)
    if token == "composite":
        return "governance_surface"
    if token == "system":
        return "infrastructure"
    if token in {"runtime", "platform", "engine", "application", "service"}:
        return "governance_engine"
    if token in {"tool", "cli", "gate", "policy", "validator"}:
        return "control_gate"
    if token in {"data", "topic", "stream", "dataset"}:
        return "data"
    return "governance_engine"


def normalize_component_category(value: str, *, fallback_kind: str = "") -> str:
    token = _normalize_taxonomy_token(value)
    alias_map: dict[str, str] = {
        "application": "governance_engine",
        "platform_runtime": "governance_engine",
        "tooling": "control_gate",
    }
    token = alias_map.get(token, token)
    if token in _COMPONENT_CATEGORIES:
        return token
    if fallback_kind:
        return _default_category_for_kind(fallback_kind)
    return ""


def normalize_component_qualification(value: str) -> str:
    token = _normalize_taxonomy_token(value)
    if token in _COMPONENT_QUALIFICATIONS:
        return token
    if token in {"manual", "manifest"}:
        return "curated"
    return ""


def normalize_product_layer(value: str) -> str:
    token = _normalize_taxonomy_token(value)
    if token in _PRODUCT_LAYERS:
        return token
    if token.endswith("_distro") and re.fullmatch(r"[a-z0-9][a-z0-9_]*_distro", token):
        return "consumer_distro"
    return ""


def _default_component_qualification(*, status: str, sources: Iterable[str]) -> str:
    source_set = {str(token or "").strip().lower() for token in sources if str(token or "").strip()}
    if "manifest" in source_set and str(status or "").strip().lower() not in {"candidate"}:
        return "curated"
    if "reviewed_candidate" in source_set or "manifest_candidate" in source_set:
        return "candidate"
    return "curated"


def _normalize_path(repo_root: Path, token: str) -> str:
    normalized = workstream_inference.normalize_repo_token(str(token or "").strip(), repo_root=repo_root)
    return normalized.lstrip("./")


def _path_matches_prefix(path_token: str, prefix_token: str) -> bool:
    left = workstream_inference.normalize_repo_token(path_token)
    right = workstream_inference.normalize_repo_token(prefix_token)
    if not left or not right:
        return False
    if left == right:
        return True
    return left.startswith(f"{right}/")


def _is_manifest_component_object(raw: Any) -> bool:
    return isinstance(raw, Mapping)


def _normalize_list_of_strings(values: Any) -> list[str]:
    rows: list[str] = []
    if isinstance(values, list):
        for item in values:
            token = str(item or "").strip()
            if token:
                rows.append(token)
    return rows


def _make_entry(
    *,
    component_id: str,
    name: str,
    kind: str,
    category: str,
    qualification: str,
    aliases: Iterable[str],
    path_prefixes: Iterable[str],
    workstreams: Iterable[str],
    diagrams: Iterable[str],
    owner: str,
    status: str,
    what_it_is: str,
    why_tracked: str,
    spec_ref: str,
    sources: Iterable[str],
    subcomponents: Iterable[str] = (),
    product_layer: str = "",
) -> ComponentEntry:
    source_list = _dedupe_stable(sources)
    kind_token = str(kind or "").strip() or "inferred"
    status_token = str(status or "").strip() or "inferred"
    category_token = normalize_component_category(category, fallback_kind=kind_token)
    qualification_token = (
        normalize_component_qualification(qualification)
        or _default_component_qualification(status=status_token, sources=source_list)
    )
    product_layer_token = normalize_product_layer(product_layer)
    return ComponentEntry(
        component_id=component_id,
        name=str(name or "").strip() or component_id,
        kind=kind_token,
        category=category_token,
        qualification=qualification_token,
        aliases=_dedupe_stable(aliases),
        path_prefixes=_dedupe_stable(path_prefixes),
        workstreams=_dedupe_stable(workstreams),
        diagrams=_dedupe_stable(diagrams),
        owner=str(owner or "").strip() or "unknown",
        status=status_token,
        what_it_is=str(what_it_is or "").strip(),
        why_tracked=str(why_tracked or "").strip(),
        spec_ref=str(spec_ref or "").strip(),
        sources=source_list,
        subcomponents=_dedupe_stable(subcomponents),
        product_layer=product_layer_token,
    )


def _entry_to_mutable(entry: ComponentEntry) -> dict[str, Any]:
    return {
        "component_id": entry.component_id,
        "name": entry.name,
        "kind": entry.kind,
        "category": entry.category,
        "qualification": entry.qualification,
        "aliases": list(entry.aliases),
        "path_prefixes": list(entry.path_prefixes),
        "workstreams": list(entry.workstreams),
        "diagrams": list(entry.diagrams),
        "owner": entry.owner,
        "status": entry.status,
        "what_it_is": entry.what_it_is,
        "why_tracked": entry.why_tracked,
        "spec_ref": entry.spec_ref,
        "sources": list(entry.sources),
        "subcomponents": list(entry.subcomponents),
        "product_layer": entry.product_layer,
    }


def _mapped_event_from_payload(payload: Mapping[str, Any]) -> MappedEvent:
    return MappedEvent(
        event_index=int(payload.get("event_index", 0) or 0),
        ts_iso=str(payload.get("ts_iso", "")).strip(),
        kind=str(payload.get("kind", "")).strip(),
        summary=str(payload.get("summary", "")).strip(),
        workstreams=[str(item).strip() for item in payload.get("workstreams", []) if str(item).strip()],
        artifacts=[str(item).strip() for item in payload.get("artifacts", []) if str(item).strip()],
        explicit_components=[
            str(item).strip()
            for item in payload.get("explicit_components", [])
            if str(item).strip()
        ],
        mapped_components=[
            str(item).strip()
            for item in payload.get("mapped_components", [])
            if str(item).strip()
        ],
        confidence=str(payload.get("confidence", "")).strip(),
        meaningful=bool(payload.get("meaningful")),
    )


def _coverage_from_payload(payload: Mapping[str, Any]) -> ComponentForensicCoverage:
    return ComponentForensicCoverage(
        status=str(payload.get("status", "")).strip(),
        timeline_event_count=int(payload.get("timeline_event_count", 0) or 0),
        explicit_event_count=int(payload.get("explicit_event_count", 0) or 0),
        recent_path_match_count=int(payload.get("recent_path_match_count", 0) or 0),
        mapped_workstream_evidence_count=int(payload.get("mapped_workstream_evidence_count", 0) or 0),
        spec_history_event_count=int(payload.get("spec_history_event_count", 0) or 0),
        empty_reasons=[str(item).strip() for item in payload.get("empty_reasons", []) if str(item).strip()],
    )


def _component_registry_report_from_payload(payload: Mapping[str, Any]) -> ComponentRegistryReport:
    components = {
        row.component_id: row
        for row in (
            _component_entry_from_payload(item)
            for item in payload.get("components", [])
            if isinstance(item, Mapping)
        )
        if row.component_id
    }
    raw_mapped_events = payload.get("mapped_events", payload.get("events", []))
    mapped_events = [
        _mapped_event_from_payload(item)
        for item in raw_mapped_events
        if isinstance(item, Mapping)
    ]
    unmapped = [
        _mapped_event_from_payload(item)
        for item in payload.get("unmapped_meaningful_events", [])
        if isinstance(item, Mapping)
    ]
    candidate_queue = [
        dict(item)
        for item in payload.get("candidate_queue", [])
        if isinstance(item, Mapping)
    ]
    forensic = {
        str(component_id): _coverage_from_payload(item)
        for component_id, item in payload.get("forensic_coverage", {}).items()
        if str(component_id).strip() and isinstance(item, Mapping)
    } if isinstance(payload.get("forensic_coverage"), Mapping) else {}
    diagnostics = [str(item) for item in payload.get("diagnostics", [])]
    return ComponentRegistryReport(
        components=components,
        mapped_events=mapped_events,
        unmapped_meaningful_events=unmapped,
        candidate_queue=candidate_queue,
        forensic_coverage=forensic,
        diagnostics=diagnostics,
    )


def _cached_component_registry_report_payload(
    *,
    repo_root: Path,
    manifest_path: Path,
    catalog_path: Path,
    ideas_root: Path,
    stream_path: Path,
    workspace_activity_window_hours: int,
) -> tuple[Path, str]:
    cache_file = odylith_context_cache.cache_path(
        repo_root=repo_root,
        namespace="registry/component-report",
        key="component-report",
    )
    from odylith.runtime.governance import agent_governance_intelligence as governance

    workspace_activity = []
    for raw in governance.collect_git_changed_paths(repo_root=repo_root):
        normalized = _normalize_path(repo_root, str(raw or ""))
        if not normalized or not is_meaningful_workspace_artifact(normalized, repo_root=repo_root):
            continue
        workspace_activity.append(
            {
                "path": normalized,
                "signature": odylith_context_cache.path_signature((repo_root / normalized).resolve()),
            }
        )
    fingerprint = odylith_context_cache.fingerprint_payload(
        {
            "component_report_cache_version": _COMPONENT_REPORT_CACHE_VERSION,
            "feature_history_plan_route_version": _FEATURE_HISTORY_PLAN_ROUTE_VERSION,
            "product_layer_normalization_version": _PRODUCT_LAYER_NORMALIZATION_VERSION,
            "radar_idea_contract_version": _RADAR_IDEA_CONTRACT_VERSION,
            "manifest": odylith_context_cache.path_signature(manifest_path),
            "catalog": odylith_context_cache.path_signature(catalog_path),
            "ideas": odylith_context_cache.fingerprint_tree(ideas_root, glob="*.md"),
            "stream": odylith_context_cache.path_signature(stream_path),
            "manifest_spec_refs": _manifest_spec_ref_signatures(
                repo_root=repo_root,
                manifest_path=manifest_path,
            ),
            "workspace_activity_window_hours": int(workspace_activity_window_hours),
            "workspace_activity": workspace_activity,
        }
    )
    return cache_file, fingerprint


def _parse_manifest(
    *,
    repo_root: Path,
    manifest_path: Path,
) -> tuple[dict[str, ComponentEntry], dict[str, str], list[str]]:
    errors: list[str] = []
    alias_to_component: dict[str, str] = {}
    by_component: dict[str, ComponentEntry] = {}
    pending_subcomponents: dict[str, list[str]] = {}

    if not manifest_path.is_file():
        errors.append(f"missing component manifest: {manifest_path}")
        return by_component, alias_to_component, errors

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid component manifest json `{manifest_path}`: {exc}")
        return by_component, alias_to_component, errors

    if not isinstance(payload, Mapping):
        errors.append(f"component manifest must be an object: {manifest_path}")
        return by_component, alias_to_component, errors

    components = payload.get("components", [])
    if not isinstance(components, list):
        errors.append(f"`components` must be a list in {manifest_path}")
        return by_component, alias_to_component, errors

    known_workstream_ids = _known_workstream_ids(repo_root=repo_root)

    for idx, raw in enumerate(components):
        context = f"{manifest_path}: components[{idx}]"
        if not _is_manifest_component_object(raw):
            errors.append(f"{context} must be an object")
            continue

        component_id = normalize_component_id(str(raw.get("component_id", "")))
        if not component_id:
            errors.append(f"{context}: invalid `component_id`")
            continue
        if component_id in by_component:
            errors.append(f"{context}: duplicate component_id `{component_id}`")
            continue

        name = str(raw.get("name", "")).strip()
        if not name:
            errors.append(f"{context}: missing non-empty `name`")
            continue

        kind = str(raw.get("kind", "")).strip()
        raw_category = str(raw.get("category", "")).strip()
        raw_qualification = str(raw.get("qualification", "")).strip()
        owner = str(raw.get("owner", "")).strip()
        status = str(raw.get("status", "")).strip()
        what_it_is = str(raw.get("what_it_is", "")).strip()
        why_tracked = str(raw.get("why_tracked", "")).strip()
        raw_spec_ref = str(raw.get("spec_ref", "")).strip()

        category = normalize_component_category(raw_category, fallback_kind=kind)
        raw_category_token = _normalize_taxonomy_token(raw_category)
        if raw_category and normalize_component_category(raw_category) not in _COMPONENT_CATEGORIES:
            errors.append(f"{context}: invalid category `{raw_category}`")
            continue
        if raw_category_token == "uncategorized":
            errors.append(f"{context}: `uncategorized` is not allowed for first-class components")
            continue

        qualification = normalize_component_qualification(raw_qualification)
        if raw_qualification and not qualification:
            errors.append(f"{context}: invalid qualification `{raw_qualification}`")
            continue
        if not qualification:
            qualification = "curated"
        if qualification not in _FIRST_CLASS_QUALIFICATIONS:
            errors.append(
                f"{context}: first-class qualification must be one of "
                f"{sorted(_FIRST_CLASS_QUALIFICATIONS)}"
            )
            continue
        if not what_it_is:
            errors.append(f"{context}: missing non-empty `what_it_is`")
            continue
        if not why_tracked:
            errors.append(f"{context}: missing non-empty `why_tracked`")
            continue
        if not raw_spec_ref:
            errors.append(f"{context}: missing non-empty `spec_ref`")
            continue
        spec_ref = _normalize_path(repo_root, raw_spec_ref)
        if not spec_ref:
            errors.append(f"{context}: invalid `spec_ref` path `{raw_spec_ref}`")
            continue
        spec_path = (repo_root / spec_ref).resolve()
        try:
            spec_path.relative_to(repo_root)
        except ValueError:
            errors.append(f"{context}: `spec_ref` must resolve inside repository `{raw_spec_ref}`")
            continue
        if not spec_path.is_file():
            errors.append(f"{context}: `spec_ref` does not exist `{spec_ref}`")
            continue
        spec_snapshot = load_component_spec_snapshot(spec_path=spec_path)
        if not spec_snapshot.feature_history:
            errors.append(
                f"{context}: `spec_ref` must contain `## Feature History` with dated entries "
                "(format: `- YYYY-MM-DD: summary (Plan: [B-###](odylith/radar/radar.html?view=plan&workstream=B-###))`)."
            )
            continue
        allow_upstream_product_provenance = (
            not _is_source_product_repo(repo_root)
            and str(raw.get("owner", "")).strip().lower() == "product"
        )
        feature_history_errors: list[str] = []
        for history_entry in spec_snapshot.feature_history:
            summary = str(history_entry.get("summary", "")).strip()
            date = str(history_entry.get("date", "")).strip() or "unknown-date"
            plan_refs = history_entry.get("plan_refs", [])
            valid_plan_refs = [row for row in plan_refs if isinstance(row, Mapping) and bool(row.get("valid"))]
            if not valid_plan_refs:
                if allow_upstream_product_provenance:
                    continue
                feature_history_errors.append(
                    f"{context}: feature history entry `{date}: {summary}` must include "
                    "a canonical rendered plan route `(Plan: [B-###](odylith/radar/radar.html?view=plan&workstream=B-###))`."
                )
                continue
            for plan_ref in valid_plan_refs:
                resolved_path = (
                    Path(str(plan_ref.get("resolved_path", "")).strip())
                    if str(plan_ref.get("resolved_path", "")).strip()
                    else None
                )
                repo_path = str(plan_ref.get("repo_path", "")).strip()
                workstream_id = normalize_workstream_id(str(plan_ref.get("workstream_id", "")).strip())
                if not repo_path:
                    feature_history_errors.append(
                        f"{context}: feature history entry `{date}: {summary}` has an invalid rendered plan link."
                    )
                    continue
                if resolved_path is None:
                    feature_history_errors.append(
                        f"{context}: feature history entry `{date}: {summary}` points to missing plan page `{repo_path}`."
                    )
                    continue
                try:
                    resolved_path.relative_to(repo_root)
                except ValueError:
                    feature_history_errors.append(
                        f"{context}: feature history entry `{date}: {summary}` must point inside repository plan pages."
                    )
                    continue
                if repo_path.startswith("odylith/radar/radar.html?view=plan&workstream="):
                    if not workstream_id or workstream_id not in known_workstream_ids:
                        if allow_upstream_product_provenance:
                            continue
                        feature_history_errors.append(
                            f"{context}: feature history entry `{date}: {summary}` points to unknown workstream `{workstream_id or 'unknown'}`."
                        )
                        continue
                    if resolved_path.is_file():
                        continue
                    # Single-entrypoint Radar plan routes remain valid before the
                    # generated HTML is rendered, as long as the referenced
                    # source-of-truth workstream exists.
                    continue
                if not resolved_path.is_file():
                    feature_history_errors.append(
                        f"{context}: feature history entry `{date}: {summary}` points to missing plan page `{repo_path}`."
                    )
                    continue
        if feature_history_errors:
            errors.extend(feature_history_errors)
            continue

        raw_product_layer = str(raw.get("product_layer", "")).strip()
        product_layer = normalize_product_layer(raw_product_layer)
        if raw_product_layer and not product_layer:
            errors.append(f"{context}: invalid product_layer `{raw_product_layer}`")
            continue

        aliases = _dedupe_stable(
            [
                component_id,
                normalize_component_id(name),
            ]
        )
        for token in _normalize_list_of_strings(raw.get("aliases", [])):
            normalized = normalize_component_id(token)
            if not normalized:
                errors.append(f"{context}: invalid alias `{token}`")
                continue
            _append_unique(aliases, normalized)

        path_prefixes: list[str] = []
        for token in _normalize_list_of_strings(raw.get("path_prefixes", [])):
            normalized = _normalize_path(repo_root, token)
            if not normalized:
                errors.append(f"{context}: invalid path prefix `{token}`")
                continue
            _append_unique(path_prefixes, normalized)

        workstreams: list[str] = []
        for token in _normalize_list_of_strings(raw.get("workstreams", [])):
            normalized = normalize_workstream_id(token)
            if not normalized:
                errors.append(f"{context}: invalid workstream id `{token}`")
                continue
            _append_unique(workstreams, normalized)

        diagrams: list[str] = []
        for token in _normalize_list_of_strings(raw.get("diagrams", [])):
            normalized = normalize_diagram_id(token)
            if not normalized:
                errors.append(f"{context}: invalid diagram id `{token}`")
                continue
            _append_unique(diagrams, normalized)

        subcomponents: list[str] = []
        for token in _normalize_list_of_strings(raw.get("subcomponents", [])):
            normalized = normalize_component_id(token)
            if not normalized:
                errors.append(f"{context}: invalid subcomponent `{token}`")
                continue
            _append_unique(subcomponents, normalized)

        entry = _make_entry(
            component_id=component_id,
            name=name,
            kind=kind,
            category=category,
            qualification=qualification,
            aliases=aliases,
            path_prefixes=path_prefixes,
            workstreams=workstreams,
            diagrams=diagrams,
            owner=owner,
            status=status,
            what_it_is=what_it_is,
            why_tracked=why_tracked,
            spec_ref=spec_ref,
            sources=("manifest",),
            subcomponents=subcomponents,
            product_layer=product_layer,
        )
        by_component[component_id] = entry
        pending_subcomponents[component_id] = subcomponents

        for alias in entry.aliases:
            owner_component = alias_to_component.get(alias)
            if owner_component and owner_component != component_id:
                errors.append(
                    f"{context}: alias collision `{alias}` with `{owner_component}`"
                )
                continue
            alias_to_component[alias] = component_id

    for component_id, subcomponents in pending_subcomponents.items():
        for child_id in subcomponents:
            if child_id == component_id:
                errors.append(f"{manifest_path}: component `{component_id}` cannot list itself in `subcomponents`")
                continue
            if child_id not in by_component:
                errors.append(
                    f"{manifest_path}: component `{component_id}` references unknown subcomponent `{child_id}`"
                )

    return by_component, alias_to_component, errors


def _extract_section_lines_from_lines(*, lines: Sequence[str], section: str) -> list[str]:
    target = section.strip().lower()
    capture = False
    rows: list[str] = []
    for line in lines:
        if line.startswith("## "):
            current = line[3:].strip().lower()
            if capture and current != target:
                break
            capture = current == target
            continue
        if capture:
            rows.append(line)
    return rows


def _extract_section_lines(path: Path, section: str) -> list[str]:
    return _extract_section_lines_from_lines(
        lines=path.read_text(encoding="utf-8").splitlines(),
        section=section,
    )


def _first_heading(lines: Sequence[str]) -> str:
    for line in lines:
        token = str(line or "").strip()
        if token.startswith("# "):
            return token[2:].strip()
    return ""


def _extract_last_updated(lines: Sequence[str]) -> str:
    for line in lines:
        token = str(line or "").strip()
        if token.lower().startswith("last updated:"):
            return token.split(":", 1)[1].strip()
    return ""


_REPO_ROOT_RELATIVE_PREFIXES: tuple[str, ...] = (
    "odylith/",
    "src/",
    "docs/",
    "odylith/runtime/contracts/",
    "contracts/",
    "tests/",
    "agents-guidelines/",
    "skills/",
    "scr" + "ipts/",
    "mk/",
    "infra/",
    "services/",
    "app/",
    ".odylith/",
)


def _resolve_spec_relative_link(*, repo_root: Path, spec_path: Path, href: str) -> Path | None:
    token = str(href or "").strip()
    if not token:
        return None
    parsed = urlparse(token)
    path_token = parsed.path or token
    if re.match(r"^[a-z][a-z0-9+.-]*:", token, flags=re.I):
        return None
    candidate = Path(path_token)
    if candidate.is_absolute():
        return candidate.resolve()
    normalized = candidate.as_posix().lstrip("./")
    if any(normalized.startswith(prefix) for prefix in _REPO_ROOT_RELATIVE_PREFIXES):
        return (repo_root / normalized).resolve()
    return (spec_path.parent / candidate).resolve()


def _extract_feature_history_plan_route(href: str) -> tuple[str, str]:
    token = str(href or "").strip()
    if not token:
        return "", ""
    parsed = urlparse(token)
    if not _FEATURE_HISTORY_PLAN_ROUTE_RE.search(parsed.path):
        return "", ""
    query = parse_qs(parsed.query)
    workstream_id = normalize_workstream_id(str((query.get("workstream") or [""])[0]).strip())
    view = str((query.get("view") or [""])[0]).strip().lower()
    if not workstream_id or view != "plan":
        return "", ""
    return f"odylith/radar/radar.html?view=plan&workstream={workstream_id}", workstream_id


def _extract_feature_history_plan_refs(*, spec_path: Path, summary: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    repo_root = next(
        (
            candidate
            for candidate in (spec_path.parent, *spec_path.parents)
            if (candidate / ".git").exists()
            or has_project_guidance(repo_root=candidate)
            or (candidate / "odylith").is_dir()
        ),
        spec_path.parent,
    )
    for match in _FEATURE_HISTORY_PLAN_REF_RE.finditer(str(summary or "")):
        label = normalize_workstream_id(str(match.group(1) or "").strip())
        href = str(match.group(2) or "").strip()
        repo_path, href_workstream = _extract_feature_history_plan_route(href)
        resolved = _resolve_spec_relative_link(repo_root=repo_root, spec_path=spec_path, href=href)
        rows.append(
            {
                "workstream_id": label,
                "href": href,
                "resolved_path": str(resolved) if resolved is not None else "",
                "repo_path": repo_path,
                "valid": bool(label and href_workstream and label == href_workstream),
            }
        )
    return rows


def _known_workstream_ids(*, repo_root: Path) -> set[str]:
    """Return normalized workstream ids from the source backlog specs.

    Canonical feature-history plan links now target the single Radar route
    `odylith/radar/radar.html?view=plan&workstream=B-###`. The route remains
    valid even before the generated Radar HTML exists on disk, so component-spec
    validation must confirm the workstream target from source-of-truth backlog
    specs instead of treating the query route like a per-plan HTML file.
    """

    ideas_root = _resolve(repo_root, DEFAULT_IDEAS_ROOT)
    idea_specs, _idea_errors = backlog_contract._validate_idea_specs(ideas_root)
    return {
        normalized
        for raw in idea_specs
        if (normalized := normalize_workstream_id(str(raw or "").strip()))
    }


def _normalize_skill_trigger_phrase(text: str) -> str:
    token = str(text or "").strip().strip('"').strip("'")
    return token


def _append_skill_trigger_phrase(*, target: dict[str, Any], phrase: str) -> None:
    token = _normalize_skill_trigger_phrase(phrase)
    if not token:
        return
    phrases = target.setdefault("trigger_phrases", [])
    if not isinstance(phrases, list):
        phrases = []
        target["trigger_phrases"] = phrases
    if token in phrases:
        return
    phrases.append(token)


def extract_skill_trigger_tiers_from_markdown(markdown: str) -> tuple[dict[str, list[dict[str, Any]]], str]:
    """Parse `## Skill Triggers` into structured baseline/deep tiers.

    Supported authoring format:
    - `## Skill Triggers`
    - optional `### Baseline` / `### Deep` headings
    - per-skill bullets: `- `skill-name``
    - trigger phrase bullets under each skill.
    """

    lines = str(markdown or "").replace("\r\n", "\n").split("\n")
    section_lines = _extract_section_lines_from_lines(lines=lines, section="Skill Triggers")
    tiers: dict[str, list[dict[str, Any]]] = {"baseline": [], "deep": []}
    if not section_lines:
        return tiers, "legacy"

    current_tier = "baseline"
    structure = "legacy"
    current_skill: dict[str, Any] | None = None
    trigger_phrase_mode = False

    for raw in section_lines:
        token = str(raw or "").strip()
        if not token:
            trigger_phrase_mode = False
            continue

        heading_match = _SKILL_TRIGGER_HEADING_RE.fullmatch(token)
        if heading_match is not None:
            heading = str(heading_match.group(1) or "").strip().lower()
            if heading.startswith("baseline"):
                current_tier = "baseline"
                structure = "tiered"
                current_skill = None
                trigger_phrase_mode = False
                continue
            if heading.startswith("deep"):
                current_tier = "deep"
                structure = "tiered"
                current_skill = None
                trigger_phrase_mode = False
                continue
            continue

        item_match = _SKILL_TRIGGER_ITEM_RE.fullmatch(token)
        if item_match is not None:
            skill_name = str(item_match.group(1) or "").strip()
            if not skill_name:
                continue
            current_skill = {
                "skill": skill_name,
                "trigger_phrases": [],
            }
            tiers.setdefault(current_tier, []).append(current_skill)
            trigger_phrase_mode = False
            continue

        if current_skill is None:
            continue

        inline_match = _SKILL_TRIGGER_INLINE_RE.fullmatch(token)
        if inline_match is not None:
            inline_chunk = str(inline_match.group(1) or "").strip()
            quoted = re.findall(r'"([^"]+)"', inline_chunk)
            if quoted:
                for phrase in quoted:
                    _append_skill_trigger_phrase(target=current_skill, phrase=phrase)
            else:
                for piece in inline_chunk.split(","):
                    _append_skill_trigger_phrase(target=current_skill, phrase=piece)
            trigger_phrase_mode = True
            continue

        if token.lower() == "- trigger phrases:":
            trigger_phrase_mode = True
            continue

        phrase_match = _SKILL_TRIGGER_PHRASE_RE.fullmatch(token)
        if phrase_match is not None and trigger_phrase_mode:
            _append_skill_trigger_phrase(target=current_skill, phrase=str(phrase_match.group(1) or ""))
            continue

    for tier in ("baseline", "deep"):
        rows = tiers.get(tier, [])
        normalized_rows: list[dict[str, Any]] = []
        for row in rows:
            skill = str(row.get("skill", "")).strip()
            if not skill:
                continue
            phrases_raw = row.get("trigger_phrases", [])
            phrases = [
                _normalize_skill_trigger_phrase(item)
                for item in (phrases_raw if isinstance(phrases_raw, list) else [])
            ]
            phrases = [item for item in phrases if item]
            normalized_rows.append(
                {
                    "skill": skill,
                    "trigger_phrases": list(dict.fromkeys(phrases)),
                }
            )
        tiers[tier] = normalized_rows

    return tiers, structure


def extract_validation_playbook_from_markdown(markdown: str) -> list[dict[str, str]]:
    """Parse `## Validation Playbook` commands in author order.

    Supported authoring format:
    - `## Validation Playbook`
    - optional `### ...` subgroup headings such as `Fast Path` / `Strict Gate`
    - bullet items containing a backticked command
    - optional prose after the command is preserved as `description`
    """

    lines = str(markdown or "").replace("\r\n", "\n").split("\n")
    section_lines = _extract_section_lines_from_lines(lines=lines, section="Validation Playbook")
    if not section_lines:
        return []

    current_group = "default"
    commands: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for raw in section_lines:
        token = str(raw or "").strip()
        if not token:
            continue

        heading_match = _SKILL_TRIGGER_HEADING_RE.fullmatch(token)
        if heading_match is not None:
            current_group = str(heading_match.group(1) or "").strip() or "default"
            continue

        if not token.startswith("- "):
            continue

        body = token[2:].strip()
        code_match = _CODE_SPAN_RE.search(body)
        if code_match is None:
            continue
        command = str(code_match.group(1) or "").strip()
        if not command:
            continue
        description = body.replace(f"`{command}`", "", 1).strip(" :-")
        dedupe_key = (current_group, command)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        commands.append(
            {
                "group": current_group,
                "command": command,
                "description": description,
            }
        )
    return commands


def load_component_spec_snapshot(*, spec_path: Path) -> ComponentSpecSnapshot:
    """Load spec markdown and parse title/last-updated/feature-history fields."""

    text = spec_path.read_text(encoding="utf-8") if spec_path.is_file() else ""
    lines = text.splitlines()
    feature_lines = _extract_section_lines_from_lines(lines=lines, section="Feature History")
    feature_history: list[dict[str, str]] = []
    for line in feature_lines:
        match = _FEATURE_HISTORY_ENTRY_RE.match(str(line or "").strip())
        if not match:
            continue
        summary = str(match.group(2) or "").strip()
        feature_history.append(
            {
                "date": str(match.group(1) or "").strip(),
                "summary": summary,
                "plan_refs": _extract_feature_history_plan_refs(spec_path=spec_path, summary=summary),
            }
        )
    trigger_tiers, trigger_structure = extract_skill_trigger_tiers_from_markdown(text)
    validation_playbook_commands = extract_validation_playbook_from_markdown(text)
    return ComponentSpecSnapshot(
        title=_first_heading(lines),
        last_updated=_extract_last_updated(lines),
        feature_history=feature_history,
        markdown=text,
        skill_trigger_tiers=trigger_tiers,
        skill_trigger_structure=trigger_structure,
        validation_playbook_commands=validation_playbook_commands,
    )


def _extract_component_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for match in _CODE_SPAN_RE.finditer(text):
        token = str(match.group(1) or "").strip()
        if token:
            tokens.append(token)

    cleaned = _CODE_SPAN_RE.sub("", text)
    for chunk in _TOKEN_SPLIT_RE.split(cleaned):
        token = str(chunk or "").strip().strip("- ")
        if token:
            tokens.append(token)

    deduped: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return deduped


def _resolve_component_token(
    *,
    repo_root: Path,
    token: str,
    alias_to_component: Mapping[str, str],
    mutable_components: Mapping[str, dict[str, Any]],
) -> str:
    raw = str(token or "").strip()
    if not raw:
        return ""

    normalized = normalize_component_id(raw)
    if normalized and normalized in alias_to_component:
        return str(alias_to_component[normalized])

    path_token = _normalize_path(repo_root, raw)
    if path_token:
        matched: list[str] = []
        for component_id, row in mutable_components.items():
            prefixes = row.get("path_prefixes", [])
            if not isinstance(prefixes, (list, tuple, set)):
                continue
            if any(_path_matches_prefix(path_token, str(prefix)) for prefix in prefixes):
                matched.append(component_id)
        if len(matched) == 1:
            return matched[0]

    return ""


def build_component_index(
    *,
    repo_root: Path,
    manifest_path: Path,
    catalog_path: Path,
    ideas_root: Path,
    include_idea_candidates: bool = False,
) -> tuple[dict[str, ComponentEntry], dict[str, str], list[str]]:
    """Build first-class component inventory from manifest with contextual linking.

    Catalog and idea tokens are used to enrich known components with additional
    workstream/diagram source metadata, but unresolved tokens are *not* promoted
    into first-class inventory entries.
    """

    cache_file, fingerprint = _cached_component_index_payload(
        repo_root=repo_root,
        manifest_path=manifest_path,
        catalog_path=catalog_path,
        ideas_root=ideas_root,
        include_idea_candidates=include_idea_candidates,
    )
    cached = odylith_context_cache.read_json_object(cache_file)
    if (
        cached.get("version") == _COMPONENT_INDEX_CACHE_VERSION
        and str(cached.get("fingerprint", "")).strip() == fingerprint
        and isinstance(cached.get("components"), list)
        and isinstance(cached.get("alias_to_component"), Mapping)
        and isinstance(cached.get("diagnostics"), list)
    ):
        by_component = {
            row.component_id: row
            for row in (
                _component_entry_from_payload(payload)
                for payload in cached.get("components", [])
                if isinstance(payload, Mapping)
            )
            if row.component_id
        }
        alias_lookup = {
            str(key): str(value)
            for key, value in cached.get("alias_to_component", {}).items()
            if str(key).strip() and str(value).strip()
        }
        diagnostics = [str(item) for item in cached.get("diagnostics", [])]
        return by_component, alias_lookup, diagnostics

    base_components, alias_to_component, diagnostics = _parse_manifest(
        repo_root=repo_root,
        manifest_path=manifest_path,
    )
    mutable_components: dict[str, dict[str, Any]] = {
        key: _entry_to_mutable(value)
        for key, value in base_components.items()
    }

    if include_idea_candidates:
        diagnostics.append(
            "include_idea_candidates is deprecated: candidate promotion requires manifest review."
        )

    if catalog_path.is_file():
        try:
            catalog_payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            diagnostics.append(f"invalid catalog json `{catalog_path}`: {exc}")
            catalog_payload = {}

        diagrams = catalog_payload.get("diagrams", []) if isinstance(catalog_payload, Mapping) else []
        if isinstance(diagrams, list):
            for idx, raw_diagram in enumerate(diagrams):
                if not isinstance(raw_diagram, Mapping):
                    continue
                diagram_id = normalize_diagram_id(str(raw_diagram.get("diagram_id", "")))
                if not diagram_id:
                    continue

                diagram_workstreams: list[str] = []
                for raw_ws in raw_diagram.get("related_workstreams", []) or []:
                    normalized_ws = normalize_workstream_id(str(raw_ws or ""))
                    if normalized_ws:
                        _append_unique(diagram_workstreams, normalized_ws)

                components = raw_diagram.get("components", [])
                if not isinstance(components, list):
                    diagnostics.append(
                        f"{catalog_path}: diagrams[{idx}].components must be a list when present"
                    )
                    continue

                for raw_component in components:
                    if not isinstance(raw_component, Mapping):
                        continue
                    name = str(raw_component.get("name", "")).strip()
                    if not name:
                        continue
                    resolved = _resolve_component_token(
                        repo_root=repo_root,
                        token=name,
                        alias_to_component=alias_to_component,
                        mutable_components=mutable_components,
                    )
                    if not resolved:
                        continue
                    row = mutable_components[resolved]
                    _append_unique(row.setdefault("diagrams", []), diagram_id)
                    _extend_unique(row.setdefault("workstreams", []), diagram_workstreams)
                    _append_unique(row.setdefault("sources", []), "catalog")
    else:
        diagnostics.append(f"missing catalog path for component inference: {catalog_path}")

    idea_specs, idea_errors = backlog_contract._validate_idea_specs(ideas_root)
    for err in idea_errors:
        diagnostics.append(f"idea-parse: {err}")
    suppressed_idea_token_count = 0
    for idea_id, spec in idea_specs.items():
        section_lines = _extract_section_lines(spec.path, "Impacted Components")
        section_text = "\n".join(section_lines)
        if not section_text.strip():
            continue
        tokens = _extract_component_tokens(section_text)

        related_diagrams = [
            normalize_diagram_id(token)
            for token in str(spec.metadata.get("related_diagram_ids", "")).replace(";", ",").split(",")
        ]
        related_diagrams = [token for token in related_diagrams if token]

        for token in tokens:
            resolved = _resolve_component_token(
                repo_root=repo_root,
                token=token,
                alias_to_component=alias_to_component,
                mutable_components=mutable_components,
            )
            if not resolved:
                suppressed_idea_token_count += 1
                continue
            if not resolved:
                continue

            row = mutable_components[resolved]
            _append_unique(row.setdefault("workstreams", []), idea_id)
            _extend_unique(row.setdefault("diagrams", []), related_diagrams)
            _append_unique(row.setdefault("sources", []), "idea_specs")

    if suppressed_idea_token_count > 0:
        diagnostics.append(
            f"suppressed unresolved idea component tokens: {suppressed_idea_token_count}"
        )

    by_component: dict[str, ComponentEntry] = {}
    for component_id, row in mutable_components.items():
        by_component[component_id] = _make_entry(
            component_id=component_id,
            name=str(row.get("name", "")).strip() or component_id,
            kind=str(row.get("kind", "")).strip() or "inferred",
            category=str(row.get("category", "")).strip(),
            qualification=str(row.get("qualification", "")).strip(),
            aliases=row.get("aliases", ()) if isinstance(row.get("aliases"), (list, tuple, set)) else (),
            path_prefixes=row.get("path_prefixes", ()) if isinstance(row.get("path_prefixes"), (list, tuple, set)) else (),
            workstreams=row.get("workstreams", ()) if isinstance(row.get("workstreams"), (list, tuple, set)) else (),
            diagrams=row.get("diagrams", ()) if isinstance(row.get("diagrams"), (list, tuple, set)) else (),
            owner=str(row.get("owner", "")).strip() or "unknown",
            status=str(row.get("status", "")).strip() or "active",
            what_it_is=str(row.get("what_it_is", "")).strip(),
            why_tracked=str(row.get("why_tracked", "")).strip(),
            spec_ref=str(row.get("spec_ref", "")).strip(),
            sources=row.get("sources", ()) if isinstance(row.get("sources"), (list, tuple, set)) else (),
            subcomponents=row.get("subcomponents", ()) if isinstance(row.get("subcomponents"), (list, tuple, set)) else (),
            product_layer=str(row.get("product_layer", "")).strip(),
        )

    alias_lookup: dict[str, str] = {}
    for component_id, entry in by_component.items():
        for alias in entry.aliases:
            if not alias:
                continue
            owner = alias_lookup.get(alias)
            if owner and owner != component_id:
                diagnostics.append(
                    f"alias collision after merge `{alias}` between `{owner}` and `{component_id}`"
                )
                continue
            alias_lookup[alias] = component_id

    diagnostics = sorted(set(diagnostics))
    odylith_context_cache.write_json_if_changed(
        repo_root=repo_root,
        path=cache_file,
        payload={
            "version": _COMPONENT_INDEX_CACHE_VERSION,
            "fingerprint": fingerprint,
            "components": [by_component[key].as_dict() for key in sorted(by_component)],
            "alias_to_component": dict(sorted(alias_lookup.items())),
            "diagnostics": diagnostics,
        },
        lock_key=str(cache_file),
    )
    return by_component, alias_lookup, diagnostics


def _append_candidate_signal(
    *,
    queue: dict[tuple[str, str], dict[str, str]],
    token: str,
    source: str,
    context: str,
) -> None:
    normalized = normalize_component_id(token) or _slugify(token)
    if not normalized:
        return
    key = (source, normalized)
    row = queue.get(key)
    if row is None:
        row = {
            "token": normalized,
            "source": str(source).strip() or "unknown",
            "context": str(context or "").strip(),
        }
        queue[key] = row
        return
    existing = str(row.get("context", "")).strip()
    incoming = str(context or "").strip()
    if not incoming or incoming == existing:
        return
    row["context"] = f"{existing}; {incoming}" if existing else incoming


def build_candidate_component_queue(
    *,
    repo_root: Path,
    catalog_path: Path,
    ideas_root: Path,
    stream_path: Path,
    alias_to_component: Mapping[str, str],
) -> list[dict[str, str]]:
    """Return unresolved component-like tokens for operator review.

    This queue is explicitly advisory and never auto-promotes tokens into
    first-class inventory.
    """

    queue: dict[tuple[str, str], dict[str, str]] = {}

    if catalog_path.is_file():
        try:
            payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        diagrams = payload.get("diagrams", []) if isinstance(payload, Mapping) else []
        if isinstance(diagrams, list):
            for raw_diagram in diagrams:
                if not isinstance(raw_diagram, Mapping):
                    continue
                diagram_id = normalize_diagram_id(str(raw_diagram.get("diagram_id", ""))) or "diagram"
                components = raw_diagram.get("components", [])
                if not isinstance(components, list):
                    continue
                for raw_component in components:
                    if not isinstance(raw_component, Mapping):
                        continue
                    if not catalog_component_requests_inventory_review(raw_component):
                        continue
                    token = str(raw_component.get("name", "")).strip()
                    if not token:
                        continue
                    normalized = normalize_component_id(token)
                    if normalized and normalized in alias_to_component:
                        continue
                    _append_candidate_signal(
                        queue=queue,
                        token=token,
                        source="catalog",
                        context=f"{diagram_id}",
                    )

    idea_specs, _idea_errors = backlog_contract._validate_idea_specs(ideas_root)
    for idea_id, spec in idea_specs.items():
        section_lines = _extract_section_lines(spec.path, "Impacted Components")
        section_text = "\n".join(section_lines)
        if not section_text.strip():
            continue
        for token in _extract_component_tokens(section_text):
            normalized = normalize_component_id(token)
            if normalized and normalized in alias_to_component:
                continue
            _append_candidate_signal(
                queue=queue,
                token=token,
                source="idea_specs",
                context=idea_id,
            )

    if stream_path.is_file():
        for idx, raw_line in enumerate(stream_path.read_text(encoding="utf-8").splitlines(), start=1):
            line = str(raw_line or "").strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, Mapping):
                continue
            explicit_components = _collect_event_explicit_components(raw_values=payload.get("components", []))
            for token in explicit_components:
                if token in alias_to_component:
                    continue
                _append_candidate_signal(
                    queue=queue,
                    token=token,
                    source="agent_stream",
                    context=f"line:{idx}",
                )

    return [
        queue[key]
        for key in sorted(queue, key=lambda item: (item[0], item[1]))
    ]


def _collect_event_workstreams(raw_values: Any) -> list[str]:
    rows: list[str] = []
    if isinstance(raw_values, list):
        for item in raw_values:
            normalized = normalize_workstream_id(str(item or ""))
            if normalized:
                rows.append(normalized)
    return sorted(set(rows))


def _collect_event_artifacts(*, repo_root: Path, raw_values: Any) -> list[str]:
    rows: list[str] = []
    if isinstance(raw_values, list):
        for item in raw_values:
            token = _normalize_path(repo_root, str(item or ""))
            if token:
                rows.append(token)
    return sorted(set(rows))


def _collect_event_explicit_components(*, raw_values: Any) -> list[str]:
    values: list[str] = []
    if isinstance(raw_values, list):
        for item in raw_values:
            token = str(item or "").strip()
            if token:
                values.append(token)
    elif isinstance(raw_values, str):
        token = str(raw_values or "").strip()
        if token:
            values.append(token)
    normalized: list[str] = []
    seen: set[str] = set()
    for token in values:
        normalized_token = normalize_component_id(token)
        if not normalized_token or normalized_token in seen:
            continue
        seen.add(normalized_token)
        normalized.append(normalized_token)
    return normalized


def is_meaningful_event(
    *,
    workstreams: Sequence[str],
    artifacts: Sequence[str],
    summary: str = "",
    kind: str = "",
) -> bool:
    summary_token = str(summary or "").strip().lower()
    if any(summary_token.startswith(prefix) for prefix in _GOVERNANCE_NON_MEANINGFUL_SUMMARY_PREFIXES):
        return False
    if any(normalize_workstream_id(token) for token in workstreams):
        return True
    for token in artifacts:
        if not workstream_inference.is_generated_or_global_path(str(token)):
            return True
    return False


def _match_by_explicit(
    *,
    explicit_components: Sequence[str],
    alias_to_component: Mapping[str, str],
) -> set[str]:
    matched: set[str] = set()
    for token in explicit_components:
        normalized = normalize_component_id(token)
        if not normalized:
            continue
        component_id = alias_to_component.get(normalized)
        if component_id:
            matched.add(component_id)
    return matched


def _match_by_artifact(
    *,
    artifacts: Sequence[str],
    components: Mapping[str, ComponentEntry],
) -> set[str]:
    matched: set[str] = set()
    for artifact in artifacts:
        artifact_tokens = equivalent_component_artifact_tokens(str(artifact or ""))
        if not artifact_tokens:
            continue
        for component_id, entry in components.items():
            artifact_refs = [*entry.path_prefixes, str(entry.spec_ref or "").strip()]
            if any(
                _path_matches_prefix(token, prefix)
                for token in artifact_tokens
                for prefix in artifact_refs
                if str(prefix or "").strip()
            ):
                matched.add(component_id)
    return matched


def _match_by_workstream(
    *,
    workstreams: Sequence[str],
    components: Mapping[str, ComponentEntry],
) -> set[str]:
    target = {normalize_workstream_id(token) for token in workstreams}
    target.discard("")
    matched: set[str] = set()
    if not target:
        return matched
    for component_id, entry in components.items():
        if any(token in target for token in entry.workstreams):
            matched.add(component_id)
    return matched


def _match_by_summary(
    *,
    summary: str,
    alias_to_component: Mapping[str, str],
) -> set[str]:
    token = _WORD_GAP_RE.sub(" ", str(summary or "").lower()).strip()
    if not token:
        return set()

    matched: set[str] = set()
    for alias, component_id in alias_to_component.items():
        alias_token = str(alias or "").replace("-", " ").replace("_", " ").strip()
        if len(alias_token) < 4:
            continue
        if alias_token in token:
            matched.add(component_id)
    return matched


def infer_event_component_mapping(
    *,
    summary: str,
    workstreams: Sequence[str],
    artifacts: Sequence[str],
    explicit_components: Sequence[str],
    components: Mapping[str, ComponentEntry],
    alias_to_component: Mapping[str, str],
) -> tuple[list[str], str]:
    """Infer component linkage for a single event with confidence classification."""

    explicit_match = _match_by_explicit(
        explicit_components=explicit_components,
        alias_to_component=alias_to_component,
    )
    artifact_match = _match_by_artifact(
        artifacts=artifacts,
        components=components,
    )
    workstream_match = _match_by_workstream(
        workstreams=workstreams,
        components=components,
    )
    summary_match = _match_by_summary(
        summary=summary,
        alias_to_component=alias_to_component,
    )

    all_matches = sorted(explicit_match | artifact_match | workstream_match | summary_match)
    if not all_matches:
        return [], "none"
    if explicit_match or artifact_match:
        return all_matches, "high"
    if workstream_match:
        return all_matches, "medium"
    return all_matches, "low"


def map_stream_events(
    *,
    repo_root: Path,
    stream_path: Path,
    components: Mapping[str, ComponentEntry],
    alias_to_component: Mapping[str, str],
) -> tuple[list[MappedEvent], list[str]]:
    """Map agent-stream events to components with confidence metadata."""

    diagnostics: list[str] = []
    rows: list[MappedEvent] = []
    if not stream_path.is_file():
        diagnostics.append(f"missing stream path: {stream_path}")
        return rows, diagnostics

    for idx, raw_line in enumerate(stream_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = str(raw_line or "").strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            diagnostics.append(f"{stream_path}: invalid json at line {idx}")
            continue
        if not isinstance(payload, Mapping):
            diagnostics.append(f"{stream_path}: non-object event at line {idx}")
            continue

        summary = str(payload.get("summary", "")).strip()
        kind = str(payload.get("kind", "")).strip()
        ts_iso = str(payload.get("ts_iso", "")).strip()
        workstreams = _collect_event_workstreams(payload.get("workstreams", []))
        artifacts = _collect_event_artifacts(repo_root=repo_root, raw_values=payload.get("artifacts", []))
        explicit_components = _collect_event_explicit_components(raw_values=payload.get("components", []))

        mapped_components, confidence = infer_event_component_mapping(
            summary=summary,
            workstreams=workstreams,
            artifacts=artifacts,
            explicit_components=explicit_components,
            components=components,
            alias_to_component=alias_to_component,
        )
        meaningful = is_meaningful_event(
            workstreams=workstreams,
            artifacts=artifacts,
            summary=summary,
            kind=kind,
        )
        rows.append(
            MappedEvent(
                event_index=idx,
                ts_iso=ts_iso,
                kind=kind,
                summary=summary,
                workstreams=workstreams,
                artifacts=artifacts,
                explicit_components=explicit_components,
                mapped_components=mapped_components,
                confidence=confidence,
                meaningful=meaningful,
            )
        )

    return rows, diagnostics


_RETIRED_SURFACE_MARKER = "sen" "tinel"


def _normalize_workspace_activity_path(*, repo_root: Path, token: str) -> str:
    normalized = workstream_inference.normalize_repo_token(str(token or "").strip(), repo_root=repo_root)
    normalized = normalized.lstrip("./")
    if _RETIRED_SURFACE_MARKER in normalized.lower():
        return ""
    return normalized


def _stable_missing_workspace_activity_when(*, repo_root: Path, path: Path, now: dt.datetime) -> dt.datetime:
    """Return a deterministic timestamp for deleted/renamed workspace artifacts.

    Missing paths still represent live worktree activity, but using wall-clock
    ``now`` makes repeated check-only validations drift forever on identical
    dirty worktrees. Anchor the synthetic timestamp to the nearest existing
    ancestor directory so reruns stay stable until the worktree changes again.
    """

    repo_root_resolved = repo_root.resolve()
    candidate = path.resolve().parent
    while True:
        if candidate.exists():
            try:
                return dt.datetime.fromtimestamp(candidate.stat().st_mtime, tz=dt.timezone.utc)
            except OSError:
                break
        if candidate == repo_root_resolved or candidate.parent == candidate:
            break
        candidate = candidate.parent
    try:
        return dt.datetime.fromtimestamp(repo_root_resolved.stat().st_mtime, tz=dt.timezone.utc)
    except OSError:
        return now.astimezone(dt.timezone.utc)


def is_meaningful_workspace_artifact(path: str, *, repo_root: Path | None = None) -> bool:
    """Return ``True`` when a changed path should count as forensic component evidence.

    Generated dashboard HTML, runtime snapshots, and global coordination
    artifacts should not create synthetic Registry timeline rows.
    """

    token = workstream_inference.normalize_repo_token(path).lstrip("./").lower()
    if not token:
        return False
    if workstream_inference.is_generated_or_global_path(token):
        return False
    root = Path(str(repo_root)).resolve() if repo_root is not None else None
    if root is not None and is_component_forensics_path(token, repo_root=root):
        return False
    if token.startswith("odylith/radar/source/ui/"):
        return False
    return True


def is_requirements_trace_event(event: MappedEvent) -> bool:
    """Return ``True`` when an event belongs in component requirements trace sync."""

    kind = str(event.kind or "").strip().lower()
    if kind in _FORENSIC_ONLY_KINDS:
        return False
    return True


def _collect_recent_workspace_paths(
    *,
    repo_root: Path,
    window_hours: int,
    now: dt.datetime,
) -> list[tuple[str, str]]:
    """Collect meaningful changed paths from the active worktree within the time window.

    The shared git-path collector lives in agent governance intelligence. It is
    imported lazily here to avoid a module-import cycle because that module also
    depends on Registry intelligence.
    """

    from odylith.runtime.governance import agent_governance_intelligence as governance

    cutoff = now - dt.timedelta(hours=max(0, int(window_hours)))
    rows: list[tuple[str, str]] = []
    for raw in governance.collect_git_changed_paths(repo_root=repo_root):
        token = _normalize_workspace_activity_path(repo_root=repo_root, token=raw)
        if not token or not is_meaningful_workspace_artifact(token, repo_root=repo_root):
            continue
        path = (repo_root / token).resolve()
        if path.exists():
            when = dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.timezone.utc)
        else:
            when = _stable_missing_workspace_activity_when(
                repo_root=repo_root,
                path=path,
                now=now,
            )
        when_local = when.astimezone()
        if when_local < cutoff:
            continue
        rows.append((token, when_local.isoformat(timespec="seconds")))
    return rows


def build_workspace_activity_events(
    *,
    repo_root: Path,
    components: Mapping[str, ComponentEntry],
    stream_event_count: int,
    window_hours: int = DEFAULT_WORKSPACE_ACTIVITY_WINDOW_HOURS,
    now: dt.datetime | None = None,
) -> list[MappedEvent]:
    """Synthesize recent workspace-activity evidence rows for mapped components.

    These rows are grouped per component so Registry surfaces recent work even
    when operators have not yet logged a Compass narrative event.
    """

    current = (now or dt.datetime.now().astimezone()).astimezone()
    changed_paths = _collect_recent_workspace_paths(
        repo_root=repo_root,
        window_hours=window_hours,
        now=current,
    )
    if not changed_paths:
        return []

    per_component: dict[str, dict[str, Any]] = {}
    for path_token, ts_iso in changed_paths:
        matched = _match_by_artifact(artifacts=[path_token], components=components)
        if not matched:
            continue
        for component_id in matched:
            row = per_component.setdefault(
                component_id,
                {
                    "artifacts": [],
                    "ts_iso": "",
                },
            )
            artifacts = row["artifacts"]
            if path_token not in artifacts:
                artifacts.append(path_token)
            if not row["ts_iso"] or str(ts_iso) > str(row["ts_iso"]):
                row["ts_iso"] = ts_iso

    rows: list[MappedEvent] = []
    next_index = int(stream_event_count)
    for component_id in sorted(per_component):
        event_data = per_component[component_id]
        artifacts = list(event_data.get("artifacts", []))
        if not artifacts:
            continue
        next_index += 1
        preview = ", ".join(artifacts[:2])
        more = len(artifacts) - 2
        if more > 0:
            preview = f"{preview} +{more} more"
        rows.append(
            MappedEvent(
                event_index=next_index,
                ts_iso=str(event_data.get("ts_iso", "")).strip() or current.isoformat(timespec="seconds"),
                kind="workspace_activity",
                summary=f"Recent workspace activity across tracked paths: {preview}",
                workstreams=[],
                artifacts=artifacts,
                explicit_components=[],
                mapped_components=[component_id],
                confidence="high",
                meaningful=True,
            )
        )
    return rows


def build_component_timelines(
    *,
    component_index: Mapping[str, ComponentEntry],
    mapped_events: Sequence[MappedEvent],
) -> dict[str, list[MappedEvent]]:
    """Group mapped events by component in descending chronological order."""

    grouped: dict[str, list[MappedEvent]] = {key: [] for key in component_index}
    seen: dict[str, set[tuple[str, str, str]]] = {key: set() for key in component_index}

    ordered_events = sorted(
        mapped_events,
        key=lambda row: (str(row.ts_iso or ""), int(row.event_index or 0)),
        reverse=True,
    )

    for row in ordered_events:
        for component_id in row.mapped_components:
            if component_id not in grouped:
                grouped[component_id] = []
                seen[component_id] = set()
            key = (str(row.ts_iso), str(row.kind), str(row.summary))
            if key in seen[component_id]:
                continue
            seen[component_id].add(key)
            grouped[component_id].append(row)

    return grouped


def build_component_forensic_coverage(
    *,
    component_index: Mapping[str, ComponentEntry],
    mapped_events: Sequence[MappedEvent],
    repo_root: Path | None = None,
    spec_snapshots: Mapping[str, ComponentSpecSnapshot] | None = None,
) -> dict[str, ComponentForensicCoverage]:
    """Summarize forensic evidence presence for each tracked component.

    Registry treats three evidence channels as first-class for component
    forensics:

    - explicit Compass events (`kind != workspace_activity`);
    - recent tracked path matches (`kind == workspace_activity`);
    - mapped workstream-linked evidence (`event.workstreams` non-empty).

    Live coverage remains authoritative. When live channels are empty but the
    component spec carries dated `Feature History`, Registry marks the component
    as `baseline_forensic_only` so operators can distinguish "documented but
    currently quiet" from "no usable forensic baseline".
    """

    timelines = build_component_timelines(
        component_index=component_index,
        mapped_events=mapped_events,
    )
    root = Path(str(repo_root)).expanduser().resolve() if repo_root is not None else None
    coverage: dict[str, ComponentForensicCoverage] = {}
    for component_id in component_index:
        entry = component_index[component_id]
        events = list(timelines.get(component_id, []))
        explicit_event_count = sum(1 for event in events if str(event.kind or "").strip().lower() != "workspace_activity")
        recent_path_match_count = sum(1 for event in events if str(event.kind or "").strip().lower() == "workspace_activity")
        mapped_workstream_evidence_count = sum(1 for event in events if event.workstreams)
        snapshot = spec_snapshots.get(component_id) if isinstance(spec_snapshots, Mapping) else None
        if not isinstance(snapshot, ComponentSpecSnapshot) and root is not None and entry.spec_ref:
            spec_path = _resolve(root, entry.spec_ref)
            if spec_path.is_file():
                snapshot = load_component_spec_snapshot(spec_path=spec_path)
        spec_history_event_count = (
            len(snapshot.feature_history)
            if isinstance(snapshot, ComponentSpecSnapshot)
            else 0
        )
        has_live_evidence = bool(events)
        if has_live_evidence:
            status = "forensic_coverage_present"
        elif spec_history_event_count > 0:
            status = "baseline_forensic_only"
        else:
            status = "tracked_but_evidence_empty"
        empty_reasons: list[str] = []
        if not has_live_evidence:
            if explicit_event_count == 0:
                empty_reasons.append("no_explicit_event")
            if recent_path_match_count == 0:
                empty_reasons.append("no_recent_path_match")
            if mapped_workstream_evidence_count == 0:
                empty_reasons.append("no_mapped_workstream_evidence")
        coverage[component_id] = ComponentForensicCoverage(
            status=status,
            timeline_event_count=len(events) if events else spec_history_event_count,
            explicit_event_count=explicit_event_count,
            recent_path_match_count=recent_path_match_count,
            mapped_workstream_evidence_count=mapped_workstream_evidence_count,
            spec_history_event_count=spec_history_event_count,
            empty_reasons=empty_reasons,
        )
    return coverage


def build_component_registry_report(
    *,
    repo_root: Path,
    manifest_path: Path | None = None,
    catalog_path: Path | None = None,
    ideas_root: Path | None = None,
    stream_path: Path | None = None,
    workspace_activity_window_hours: int = DEFAULT_WORKSPACE_ACTIVITY_WINDOW_HOURS,
) -> ComponentRegistryReport:
    """Build end-to-end component-registry report for renderer/validator/gov payloads."""

    manifest = manifest_path or default_manifest_path(repo_root=repo_root)
    catalog = catalog_path or _resolve(repo_root, DEFAULT_CATALOG_PATH)
    ideas = ideas_root or _resolve(repo_root, DEFAULT_IDEAS_ROOT)
    stream = stream_path or _resolve(repo_root, DEFAULT_STREAM_PATH)
    cache_file, fingerprint = _cached_component_registry_report_payload(
        repo_root=repo_root,
        manifest_path=manifest,
        catalog_path=catalog,
        ideas_root=ideas,
        stream_path=stream,
        workspace_activity_window_hours=workspace_activity_window_hours,
    )
    cached = odylith_context_cache.read_json_object(cache_file)
    if (
        cached.get("version") == _COMPONENT_REPORT_CACHE_VERSION
        and str(cached.get("fingerprint", "")).strip() == fingerprint
        and isinstance(cached.get("report"), Mapping)
    ):
        return _component_registry_report_from_payload(cached.get("report", {}))

    components, alias_to_component, diagnostics = build_component_index(
        repo_root=repo_root,
        manifest_path=manifest,
        catalog_path=catalog,
        ideas_root=ideas,
    )
    mapped_events, mapping_diagnostics = map_stream_events(
        repo_root=repo_root,
        stream_path=stream,
        components=components,
        alias_to_component=alias_to_component,
    )
    workspace_events = build_workspace_activity_events(
        repo_root=repo_root,
        components=components,
        stream_event_count=len(mapped_events),
        window_hours=workspace_activity_window_hours,
    )
    mapped_events = [*mapped_events, *workspace_events]
    diagnostics = sorted(set([*diagnostics, *mapping_diagnostics]))
    candidate_queue = build_candidate_component_queue(
        repo_root=repo_root,
        catalog_path=catalog,
        ideas_root=ideas,
        stream_path=stream,
        alias_to_component=alias_to_component,
    )
    if candidate_queue:
        diagnostics.append(f"candidate components pending review: {len(candidate_queue)}")
        diagnostics = sorted(set(diagnostics))

    unmapped_meaningful = [
        row
        for row in mapped_events
        if row.meaningful and not row.mapped_components
    ]
    forensic_coverage = build_component_forensic_coverage(
        component_index=components,
        mapped_events=mapped_events,
        repo_root=repo_root,
    )

    report = ComponentRegistryReport(
        components=components,
        mapped_events=mapped_events,
        unmapped_meaningful_events=unmapped_meaningful,
        candidate_queue=candidate_queue,
        forensic_coverage=forensic_coverage,
        diagnostics=diagnostics,
    )
    odylith_context_cache.write_json_if_changed(
        repo_root=repo_root,
        path=cache_file,
        payload={
            "version": _COMPONENT_REPORT_CACHE_VERSION,
            "fingerprint": fingerprint,
            "report": report.as_dict(),
        },
        lock_key=str(cache_file),
    )
    return report


def _load_backlog_status_by_workstream(*, ideas_root: Path) -> dict[str, str]:
    idea_specs, _errors = backlog_contract._validate_idea_specs(ideas_root)
    status_by_workstream: dict[str, str] = {}
    for idea_id, spec in idea_specs.items():
        normalized = normalize_workstream_id(idea_id)
        status = str(spec.metadata.get("status", "")).strip().lower()
        if normalized and status:
            status_by_workstream[normalized] = status
    return status_by_workstream


def evaluate_deep_skill_policy(
    *,
    repo_root: Path,
    components: Mapping[str, ComponentEntry],
    mapped_events: Sequence[MappedEvent],
    ideas_root: Path | None = None,
    target_components: Sequence[str] = (),
    active_statuses: Sequence[str] = ("planning", "implementation"),
    min_meaningful_events: int = 1,
    min_gate_count: int = 2,
) -> list[dict[str, Any]]:
    """Evaluate deep-skill requirements using risk/churn/workflow gates.

    Results are returned for every target component so validators and Odylith
    posture builders can decide whether findings are advisory or fail-closed.
    """

    normalized_targets = {
        normalize_component_id(token)
        for token in target_components
        if normalize_component_id(token)
    }
    if not normalized_targets:
        return []

    root = Path(str(repo_root)).expanduser().resolve()
    ideas = ideas_root or _resolve(root, DEFAULT_IDEAS_ROOT)
    status_by_workstream = _load_backlog_status_by_workstream(ideas_root=ideas)
    active_status_tokens = {str(token or "").strip().lower() for token in active_statuses if str(token or "").strip()}

    meaningful_event_count_by_component: dict[str, int] = {}
    for row in mapped_events:
        if not row.meaningful:
            continue
        for component_id in row.mapped_components:
            meaningful_event_count_by_component[component_id] = int(
                meaningful_event_count_by_component.get(component_id, 0) or 0
            ) + 1

    results: list[dict[str, Any]] = []
    for component_id in sorted(normalized_targets):
        entry = components.get(component_id)
        if entry is None:
            results.append(
                {
                    "component_id": component_id,
                    "exists": False,
                    "required": False,
                    "gates": {"risk": False, "churn": False, "workflow": False},
                    "gate_count": 0,
                    "meaningful_event_count": 0,
                    "baseline_skill_count": 0,
                    "deep_skill_count": 0,
                    "trigger_structure": "missing",
                    "missing": ["component_missing"],
                }
            )
            continue

        spec_path = _resolve(root, entry.spec_ref) if entry.spec_ref else None
        spec_snapshot = (
            load_component_spec_snapshot(spec_path=spec_path)
            if spec_path is not None and spec_path.is_file()
            else ComponentSpecSnapshot(
                title="",
                last_updated="",
                feature_history=[],
                markdown="",
                skill_trigger_tiers={"baseline": [], "deep": []},
                skill_trigger_structure="missing",
                validation_playbook_commands=[],
            )
        )

        baseline_skills = spec_snapshot.skill_trigger_tiers.get("baseline", [])
        deep_skills = spec_snapshot.skill_trigger_tiers.get("deep", [])
        meaningful_count = int(meaningful_event_count_by_component.get(component_id, 0) or 0)
        workflow_gate = any(
            str(status_by_workstream.get(normalize_workstream_id(workstream), "")).strip().lower()
            in active_status_tokens
            for workstream in entry.workstreams
        )
        gates = {
            "risk": True,
            "churn": meaningful_count >= max(0, int(min_meaningful_events)),
            "workflow": workflow_gate,
        }
        gate_count = sum(1 for value in gates.values() if value)
        required = gate_count >= max(1, int(min_gate_count))
        missing: list[str] = []
        if not baseline_skills:
            missing.append("baseline_skills_missing")
        if spec_snapshot.skill_trigger_structure != "tiered":
            missing.append("trigger_structure_not_tiered")
        if required and not deep_skills:
            missing.append("deep_skills_missing")

        results.append(
            {
                "component_id": component_id,
                "exists": True,
                "required": required,
                "gates": gates,
                "gate_count": gate_count,
                "meaningful_event_count": meaningful_count,
                "baseline_skill_count": len(baseline_skills),
                "deep_skill_count": len(deep_skills),
                "trigger_structure": spec_snapshot.skill_trigger_structure,
                "missing": missing,
            }
        )

    return results


def component_ids_for_workstream(
    *,
    components: Mapping[str, ComponentEntry],
    workstream_id: str,
) -> list[str]:
    """Return sorted component IDs linked to a given workstream."""

    token = normalize_workstream_id(workstream_id)
    if not token:
        return []
    rows = [
        component_id
        for component_id, entry in components.items()
        if token in entry.workstreams
    ]
    return sorted(set(rows))


def component_id_for_token(
    *,
    token: str,
    components: Mapping[str, ComponentEntry],
) -> str:
    """Resolve best-effort component token to known component ID."""

    normalized = normalize_component_id(token)
    if not normalized:
        return ""

    if normalized in components:
        return normalized

    for component_id, entry in components.items():
        if normalized in entry.aliases:
            return component_id
    return ""


def build_component_traceability_index(
    *,
    repo_root: Path,
    components: Mapping[str, ComponentEntry],
    traceability_graph_path: Path | None = None,
) -> dict[str, dict[str, list[str]]]:
    """Aggregate plan traceability triad paths by component-linked workstreams."""

    rows: dict[str, dict[str, list[str]]] = {
        component_id: {
            "runbooks": [],
            "developer_docs": [],
            "code_references": [],
        }
        for component_id in components
    }
    graph_path = traceability_graph_path or _resolve(repo_root, DEFAULT_TRACEABILITY_GRAPH_PATH)
    if not graph_path.is_file():
        return rows

    try:
        payload = json.loads(graph_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return rows
    if not isinstance(payload, Mapping):
        return rows

    workstream_traceability: dict[str, dict[str, list[str]]] = {}
    for raw in payload.get("workstreams", []) if isinstance(payload.get("workstreams", []), list) else []:
        if not isinstance(raw, Mapping):
            continue
        idea_id = normalize_workstream_id(str(raw.get("idea_id", "")))
        if not idea_id:
            continue
        trace = raw.get("plan_traceability", {})
        if not isinstance(trace, Mapping):
            continue
        workstream_traceability[idea_id] = {
            "runbooks": [],
            "developer_docs": [],
            "code_references": [],
        }
        for bucket in ("runbooks", "developer_docs", "code_references"):
            values = trace.get(bucket, [])
            if not isinstance(values, list):
                continue
            normalized_values = [
                _normalize_path(repo_root, str(token or ""))
                for token in values
            ]
            _extend_unique(
                workstream_traceability[idea_id][bucket],
                [token for token in normalized_values if token],
            )

    for component_id, entry in components.items():
        target = rows.setdefault(
            component_id,
            {"runbooks": [], "developer_docs": [], "code_references": []},
        )
        for workstream_id in entry.workstreams:
            source = workstream_traceability.get(normalize_workstream_id(workstream_id))
            if not source:
                continue
            for bucket in ("runbooks", "developer_docs", "code_references"):
                _extend_unique(target[bucket], source.get(bucket, []))

    return rows


__all__ = [
    "build_candidate_component_queue",
    "build_component_forensic_coverage",
    "ComponentEntry",
    "ComponentForensicCoverage",
    "ComponentRegistryReport",
    "ComponentSpecSnapshot",
    "DEFAULT_CATALOG_PATH",
    "DEFAULT_IDEAS_ROOT",
    "DEFAULT_MANIFEST_PATH",
    "DEFAULT_STREAM_PATH",
    "DEFAULT_TRACEABILITY_GRAPH_PATH",
    "MappedEvent",
    "build_component_index",
    "build_component_registry_report",
    "build_component_traceability_index",
    "build_component_timelines",
    "component_id_for_token",
    "component_ids_for_workstream",
    "infer_event_component_mapping",
    "is_meaningful_event",
    "map_stream_events",
    "load_component_spec_snapshot",
    "extract_validation_playbook_from_markdown",
    "extract_skill_trigger_tiers_from_markdown",
    "evaluate_deep_skill_policy",
    "normalize_component_id",
    "normalize_component_category",
    "normalize_component_qualification",
    "normalize_diagram_id",
    "normalize_workstream_id",
]
