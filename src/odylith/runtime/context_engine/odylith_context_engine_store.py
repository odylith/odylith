"""Compiler-backed local projection store for installed maintainer tooling.

This module keeps markdown/JSON source artifacts authoritative while providing
an optional compiled runtime layer for fast local Codex sessions. The store is
local-only, archive-aware, and safe to rebuild at any time.

Design constraints:
- source markdown, JSON contracts, and generated tracked artifacts remain
  authoritative;
- projections must be safe under concurrent Codex sessions sharing one repo;
- cache invalidation is fingerprint-driven and fail-open to reparsing;
- strict standalone validation paths must continue to work without the store.
"""

from __future__ import annotations

import ast
import contextlib
import datetime as dt
from functools import lru_cache
import json
import xml.etree.ElementTree as ET
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
from typing import Any, Callable, Iterable, Mapping, Sequence

from odylith.runtime.governance import agent_governance_intelligence as governance
from odylith.runtime.governance import component_registry_intelligence as component_registry
from odylith.runtime.governance import delivery_intelligence_engine
from odylith.runtime.evaluation import odylith_ablation
from odylith.runtime.context_engine import odylith_architecture_mode
from odylith.runtime.context_engine import odylith_context_engine_code_graph_runtime
from odylith.runtime.context_engine import odylith_control_state
from odylith.runtime.context_engine import odylith_context_engine_engineering_notes_runtime
from odylith.runtime.context_engine import odylith_context_engine_grounding_runtime
from odylith.runtime.context_engine import odylith_context_engine_projection_runtime
from odylith.runtime.context_engine import odylith_context_engine_projection_compiler_runtime
from odylith.runtime.context_engine import odylith_context_engine_session_packet_runtime
from odylith.runtime.context_engine import odylith_context_engine_memory_snapshot_runtime
from odylith.runtime.context_engine import odylith_context_engine_projection_query_runtime
from odylith.runtime.context_engine import odylith_context_engine_hot_path_runtime
from odylith.runtime.context_engine import odylith_context_engine_runtime_learning_runtime
from odylith.runtime.evaluation import odylith_evaluation_ledger
from odylith.runtime.memory import odylith_memory_backend
from odylith.runtime.memory import odylith_projection_bundle
from odylith.runtime.memory import odylith_projection_snapshot
from odylith.runtime.memory import odylith_remote_retrieval
from odylith.runtime.memory import tooling_memory_contracts
from odylith.runtime.context_engine import tooling_context_budgeting
from odylith.runtime.context_engine import tooling_context_packet_builder
from odylith.runtime.context_engine import tooling_context_routing as routing
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.context_engine.projection_contract_versions import projection_contract_version
from odylith.runtime.context_engine import tooling_guidance_catalog
from odylith.runtime.common.command_surface import display_command
from odylith.runtime.common import odylith_benchmark_contract
from odylith.runtime.common.consumer_profile import (
    canonical_truth_token,
    is_component_spec_path,
    surface_root_path,
    truth_path_kind,
    truth_root_tokens,
    truth_root_path,
)
from odylith.runtime.common.casebook_bug_ids import CANONICAL_BUG_HEADERS, LEGACY_BUG_HEADERS
from odylith.runtime.common.product_assets import resolve_product_path
from odylith.runtime.governance import validate_backlog_contract as backlog_contract

STATE_FILENAME = odylith_control_state.STATE_FILENAME
STATE_JS_FILENAME = odylith_control_state.STATE_JS_FILENAME
STATE_JS_GLOBAL_NAME = odylith_control_state.STATE_JS_GLOBAL_NAME
EVENTS_FILENAME = odylith_control_state.EVENTS_FILENAME
TIMINGS_FILENAME = odylith_control_state.TIMINGS_FILENAME
PID_FILENAME = "odylith-context-engine.pid"
STOP_FILENAME = "odylith-context-engine.stop"
SOCKET_FILENAME = "odylith-context-engine.sock"
DAEMON_METADATA_FILENAME = "odylith-context-engine-daemon.json"
DAEMON_USAGE_FILENAME = "odylith-context-engine-daemon-usage.v1.json"
PROOF_SURFACES_FILENAME = "odylith-proof-surfaces.v1.json"
SESSIONS_DIRNAME = "sessions"
BOOTSTRAPS_DIRNAME = "bootstraps"
JUDGMENT_MEMORY_FILENAME = "odylith-judgment-memory.v1.json"
SCHEMA_VERSION = "v6"
_CODEX_HOT_PATH_PROFILE = "codex_hot_path"
_FALLBACK_LOCAL_MEMORY_BACKEND = {
    "provider": "odylith-context-engine",
    "storage": "compiler_projection_snapshot",
    "sparse_recall": "repo_scan_fallback",
    "graph_expansion": "typed_repo_graph",
    "mode": "embedded_local_first",
}
_TARGET_LOCAL_MEMORY_BACKEND = {
    "provider": "odylith-v1-target",
    "storage": "lance_local_columnar",
    "sparse_recall": "tantivy_sparse_recall",
    "graph_expansion": "typed_repo_graph",
    "mode": "embedded_local_first",
}
_FUTURE_SHARED_MEMORY_BACKEND = {
    "provider": "vespa",
    "role": "optional_shared_remote_retrieval",
    "required_for_v1": False,
}
_ODYLITH_SUPPRESSED_PATHS = frozenset({"odylith/registry/source/components/odylith/CURRENT_SPEC.md"})
OPTIMIZATION_EVALUATION_CORPUS = Path("odylith/runtime/source/optimization-evaluation-corpus.v1.json")
_HEADER_RE = re.compile(r"^##\s+(.+?)\s*$")
_TABLE_ROW_RE = re.compile(r"^\|.+\|\s*$")
_WORKSTREAM_ID_RE = re.compile(r"^B-\d{3,}$")
_DIAGRAM_ID_RE = re.compile(r"^D-\d{3,}$")
_BACKLOG_HEADERS = tuple(backlog_contract._INDEX_COLS)
_PLAN_HEADERS = ("Plan", "Status", "Created", "Updated", "Backlog")
_BUG_HEADERS = CANONICAL_BUG_HEADERS
_BUG_LEGACY_HEADERS = LEGACY_BUG_HEADERS
_BUG_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_BUG_METADATA_LINE_RE = re.compile(r"^-?\s*([A-Za-z0-9/() _.-]+):\s*(.*)$")
_BUG_CRITICAL_SEVERITIES = frozenset({"p0", "p1"})
_BUG_TERMINAL_STATUSES = frozenset({"fixed", "closed"})
_BUG_CANONICAL_STATUS_LABELS = {
    "open": "Open",
    "mitigated": "Mitigated",
    "monitoring": "Monitoring",
    "fixed": "Closed",
    "closed": "Closed",
}
_BUG_DETAIL_SECTION_ORDER = (
    "Description",
    "Impact",
    "Root Cause",
    "Solution",
    "Verification",
    "Prevention",
)
_BUG_INTELLIGENCE_CONTEXT_FIELDS = (
    "Detected By",
    "Failure Signature",
    "Trigger Path",
    "Ownership",
    "Timeline",
    "Blast Radius",
    "SLO/SLA Impact",
    "Data Risk",
    "Security/Compliance",
    "Invariant Violated",
)
_BUG_INTELLIGENCE_RECOVERY_FIELDS = (
    "Workaround",
    "Rollback/Forward Fix",
    "Agent Guardrails",
    "Preflight Checks",
    "Regression Tests Added",
    "Monitoring Updates",
    "Version/Build",
    "Config/Flags",
    "Customer Comms",
    "Code References",
    "Runbook References",
    "Fix Commit/PR",
)
_BUG_INTELLIGENCE_ALL_FIELDS = _BUG_INTELLIGENCE_CONTEXT_FIELDS + _BUG_INTELLIGENCE_RECOVERY_FIELDS + (
    "Related Incidents/Bugs",
)
_BUG_INTELLIGENCE_REQUIRED_CRITICAL_FIELDS = (
    "Detected By",
    "Timeline",
    "Blast Radius",
    "SLO/SLA Impact",
    "Data Risk",
    "Security/Compliance",
    "Workaround",
    "Preflight Checks",
    "Regression Tests Added",
    "Monitoring Updates",
    "Version/Build",
    "Config/Flags",
)
_BUG_CORE_FIELD_ORDER = (
    "Status",
    "Created",
    "Fixed",
    "Severity",
    "Reproducibility",
    "Type",
    "Components Affected",
    "Environment(s)",
    "Detected By",
    "Timeline",
    "Blast Radius",
    "SLO/SLA Impact",
    "Data Risk",
    "Security/Compliance",
    "Workaround",
    "Agent Guardrails",
    "Preflight Checks",
    "Regression Tests Added",
    "Monitoring Updates",
    "Related Incidents/Bugs",
    "Version/Build",
    "Config/Flags",
    "Customer Comms",
    "Failure Signature",
    "Trigger Path",
    "Ownership",
    "Invariant Violated",
    "Rollback/Forward Fix",
    "Agent Guardrails",
    "Preflight Checks",
    "Code References",
    "Runbook References",
    "Fix Commit/PR",
)

def _normalize_bug_field_name(field: str) -> str:
    return " ".join(str(field or "").strip().split())

def _normalize_bug_field_key(field: str) -> str:
    return _normalize_bug_field_name(field).casefold()


_BUG_CORE_FIELD_ORDER_SET = frozenset(_normalize_bug_field_key(name) for name in _BUG_CORE_FIELD_ORDER)
_ARCHIVE_GLOB = "*.md"
_PROCESS_WARM_CACHE_TTL_SECONDS = 300.0
_PROCESS_OPTIMIZATION_SNAPSHOT_CACHE_TTL_SECONDS = 60.0
SESSION_STALE_SECONDS = 60 * 60 * 4
_WORKSTREAM_SELECTION_GAP_MIN = 35
_WORKSTREAM_SELECTION_CONFIDENT_SCORE = 80
_WEAK_SHARED_EXACT_PATHS = {
    "agents.md",
    "odylith/technical-plans/index.md",
    "odylith/radar/source/index.md",
    "odylith/casebook/bugs/index.md",
}
_WEAK_SHARED_PREFIXES = (
    "agents-guidelines/",
    "odylith/radar/source/templates/",
    "docs/services-upgrade/",
)
_FULL_SCAN_ROOTS = (
    "agents-guidelines",
    "docs",
    "scripts",
    "tests",
    "contracts",
    "mk",
    "odylith/radar/source",
    "odylith/technical-plans",
    "odylith/casebook/bugs",
)
_FULL_SCAN_EXCLUDED_GLOBS = (
    "!.git",
    "!.odylith",
    "!odylith/compass/runtime/**",
    "!odylith/runtime/**",
    "!node_modules/**",
)
_TOPOLOGY_DOMAIN_RULES: tuple[dict[str, Any], ...] = odylith_architecture_mode.TOPOLOGY_DOMAIN_RULES
_PROCESS_WARM_CACHE: dict[str, float] = {}
_PROCESS_WARM_CACHE_FINGERPRINTS: dict[str, str] = {}
_PROCESS_PROJECTION_ROWS_CACHE: dict[str, tuple[str, Any]] = {}
_PROCESS_OPTIMIZATION_SNAPSHOT_CACHE: dict[str, tuple[tuple[Any, ...], float, dict[str, Any]]] = {}
_PROCESS_MISS_RECOVERY_INDEX_CACHE: dict[str, tuple[str, dict[str, Any]]] = {}
_PROCESS_PATH_SCOPE_CACHE: dict[str, tuple[str, dict[str, Any]]] = {}
_PROCESS_PATH_SIGNAL_PROFILE_CACHE: dict[str, dict[str, Any]] = {}
_PROCESS_ARCHITECTURE_PACKET_CACHE: dict[str, dict[str, Any]] = {}
_PROCESS_ORCHESTRATION_ADOPTION_SNAPSHOT_CACHE: dict[str, tuple[tuple[Any, ...], float, dict[str, Any]]] = {}
_PROCESS_JUDGMENT_MEMORY_SNAPSHOT_CACHE: dict[str, tuple[tuple[bool, int, int], dict[str, Any]]] = {}
_PROCESS_GIT_REF_CACHE: dict[str, tuple[float, dict[str, str]]] = {}
_PROCESS_PROJECTION_CONNECTION_CACHE: dict[str, tuple[tuple[Any, ...], Any]] = {}
_PROCESS_GIT_REF_CACHE_TTL_SECONDS = 5.0
_ENTITY_KIND_ALIASES: dict[str, str] = {
    "workstream": "workstream",
    "plan": "plan",
    "bug": "bug",
    "decision": "decision",
    "adr": "decision",
    "invariant": "invariant",
    "ownership": "ownership",
    "architecture": "architecture",
    "deployment": "deployment",
    "observability": "observability",
    "pitfall": "pitfall",
    "engineering-standard": "engineering_standard",
    "engineering_standard": "engineering_standard",
    "contract-policy": "contract_policy",
    "contract_policy": "contract_policy",
    "schema-change": "schema_change",
    "schema_change": "schema_change",
    "contract-evolution": "contract_evolution",
    "contract_evolution": "contract_evolution",
    "diagram": "diagram",
    "component": "component",
    "doc": "doc",
    "runbook": "runbook",
    "testing": "testing",
    "tooling-policy": "tooling_policy",
    "tooling_policy": "tooling_policy",
    "workflow": "workflow",
    "entrypoint": "entrypoint",
    "service-guidance": "service_guidance",
    "service_guidance": "service_guidance",
    "testing-playbook": "testing_playbook",
    "testing_playbook": "testing_playbook",
    "guardrail": "guardrail",
    "bug-learning": "bug_learning",
    "bug_learning": "bug_learning",
    "schema-contract": "schema_contract",
    "schema_contract": "schema_contract",
    "make-target": "make_target",
    "make_target": "make_target",
    "code": "code",
    "test": "test",
}
_BASE_PROJECTION_NAMES = (
    "workstreams",
    "plans",
    "bugs",
    "diagrams",
    "components",
    "codex_events",
    "traceability",
    "delivery",
)
_FULL_ONLY_PROJECTION_NAMES = (
    "engineering_graph",
    "code_graph",
    "test_graph",
)
_REASONING_PROJECTION_NAMES = (
    "workstreams",
    "plans",
    "bugs",
    "diagrams",
    "components",
    "codex_events",
    "traceability",
    *_FULL_ONLY_PROJECTION_NAMES,
)
_ENGINEERING_NOTE_KINDS = (
    "decision",
    "invariant",
    "ownership",
    "architecture",
    "deployment",
    "observability",
    "pitfall",
    "engineering_standard",
    "contract_policy",
    "schema_change",
    "contract_evolution",
    "runbook",
    "testing",
    "tooling_policy",
    "workflow",
    "entrypoint",
    "service_guidance",
    "testing_playbook",
    "guardrail",
    "bug_learning",
    "schema_contract",
    "make_target",
)
ENGINEERING_NOTE_KINDS = _ENGINEERING_NOTE_KINDS
_ENGINEERING_NOTE_KIND_SET = frozenset(_ENGINEERING_NOTE_KINDS)
_ENGINEERING_CORE_PATHS: tuple[tuple[str, str], ...] = (
    ("decisions", "agents-guidelines/DECISIONS.MD"),
    ("invariants", "agents-guidelines/INVARIANTS.MD"),
    ("ownership", "agents-guidelines/DATA_OWNERSHIP.MD"),
)
_SECTION_NOTE_SOURCES: tuple[tuple[str, str], ...] = (
    ("architecture", "agents-guidelines/ARCHITECTURE.MD"),
    ("deployment", "agents-guidelines/DEPLOYMENT.MD"),
    ("observability", "agents-guidelines/OBSERVABILITY.MD"),
    ("pitfall", "agents-guidelines/PITFALLS.md"),
    ("engineering_standard", "agents-guidelines/ENGINEERING_STANDARDS.MD"),
    ("contract_policy", "agents-guidelines/contracts/CONTRACTS.md"),
    ("schema_change", "agents-guidelines/SCHEMA_CHANGE_CHECKLIST.MD"),
    ("contract_evolution", "agents-guidelines/CONTRACT_EVOLUTION.MD"),
    ("testing", "agents-guidelines/TESTING.MD"),
    ("tooling_policy", "agents-guidelines/TOOLING.MD"),
    ("workflow", "agents-guidelines/WORKFLOW.md"),
    ("entrypoint", "agents-guidelines/ENTRYPOINTS.MD"),
    ("service_guidance", "agents-guidelines/SERVICES.md"),
    ("testing_playbook", "agents-guidelines/TESTING_PLAYBOOK.MD"),
    ("guardrail", "agents-guidelines/GUARDRAILS.MD"),
)
_GUIDANCE_CHUNK_MANIFEST_PATH = "agents-guidelines/indexable-guidance-chunks.v1.json"
_GUIDANCE_CHUNK_ROOT = "agents-guidelines/indexable"
_MISS_RECOVERY_GENERIC_QUERY_TOKENS = frozenset(
    {
        "agent",
        "agents",
        "backlog",
        "bug",
        "bugs",
        "code",
        "doc",
        "docs",
        "guideline",
        "guidelines",
        "index",
        "json",
        "md",
        "mk",
        "path",
        "paths",
        "plan",
        "py",
        "repo",
        "script",
        "scripts",
        "section",
        "source",
        "spec",
        "specs",
        "test",
        "tests",
        "tmp",
    }
)
_MISS_RECOVERY_ALLOWED_KINDS = (
    "runbook",
    "testing",
    "tooling_policy",
    "workflow",
    "guardrail",
    "architecture",
    "deployment",
    "pitfall",
    "engineering_standard",
    "contract_policy",
    "schema_change",
    "contract_evolution",
    "ownership",
    "service_guidance",
    "testing_playbook",
    "bug_learning",
    "schema_contract",
    "make_target",
    "entrypoint",
    "plan",
    "bug",
    "workstream",
    "component",
    "diagram",
    "test",
    "code",
)
_MISS_RECOVERY_KIND_PRIORITY = {
    "runbook": 0,
    "testing": 0,
    "tooling_policy": 0,
    "workflow": 0,
    "guardrail": 1,
    "architecture": 1,
    "deployment": 1,
    "testing_playbook": 1,
    "contract_policy": 1,
    "schema_change": 1,
    "contract_evolution": 1,
    "ownership": 1,
    "service_guidance": 1,
    "bug_learning": 1,
    "schema_contract": 1,
    "make_target": 1,
    "entrypoint": 1,
    "plan": 2,
    "bug": 2,
    "workstream": 2,
    "component": 2,
    "diagram": 2,
    "test": 3,
    "code": 4,
}
_MISS_RECOVERY_RESULT_LIMIT = 6
_MISS_RECOVERY_DOC_LIMIT = 3
_MISS_RECOVERY_TEST_LIMIT = 2
_ENGINEERING_WATCH_PATHS: tuple[str, ...] = tuple(
    rel_path
    for _label, rel_path in (
        *_ENGINEERING_CORE_PATHS,
        *_SECTION_NOTE_SOURCES,
        ("runbook_index", "agents-guidelines/RUNBOOK_INDEX.MD"),
        ("guidance_chunk_manifest", _GUIDANCE_CHUNK_MANIFEST_PATH),
        ("guidance_chunk_root", _GUIDANCE_CHUNK_ROOT),
    )
)
_PYTHON_GRAPH_ROOTS: tuple[tuple[str, str], ...] = (
    ("scripts", "scripts"),
    ("app", "app"),
    ("infra", "infra"),
    ("tests", "tests"),
    ("service-deploy/service_deploy", "service_deploy"),
)
_CONTRACT_PATH_PREFIXES: tuple[str, ...] = ("contracts/", "odylith/runtime/contracts/")
_CONTRACT_REF_RE = re.compile(
    r"(?:contracts|odylith/runtime/contracts)/[A-Za-z0-9._/-]+\.(?:json|jsonl|schema\.json|md)"
)
_MAKE_TARGET_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.-]*):(?:\s|$)")
_MARKDOWN_CODE_REF_RE = re.compile(r"`([^`]+)`")
_RAW_PATH_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9._/-])"
    r"((?:agents-guidelines|bin|configs|contracts|docker|docs|infra|mk|mocks|monitoring|odylith|app|policies|scripts|services|skills|tests)"
    r"/[A-Za-z0-9._/@:+-]+(?:/[A-Za-z0-9._/@:+-]+)*)"
)
_PYTHON_MODULE_COMMAND_RE = re.compile(r"(?:python|python3)\s+-m\s+([A-Za-z0-9_./-]+)")
_WORKSTREAM_TOKEN_RE = re.compile(r"\bB-\d{3,}\b")
_NOTE_TITLE_WORDS = 12
_PYTEST_LASTFAILED_PATH = ".pytest_cache/v/cache/lastfailed"
_TEST_HISTORY_REPORT_GLOBS: tuple[tuple[str, str], ...] = (
    ("", "junit*.xml"),
    ("", "pytest*.xml"),
    ("", "test-results*.xml"),
    ("reports", "*.xml"),
    ("test-results", "*.xml"),
    (".odylith/runtime/test-results", "*.xml"),
)
_SESSION_CLAIM_MODES = frozenset({"shared", "exclusive"})
_RUNTIME_TIMING_LIMIT = 512
_SESSION_RECORD_RETENTION_LIMIT = 256
_BOOTSTRAP_RECORD_RETENTION_LIMIT = 96
_CORRUPT_DB_BACKUP_LIMIT = 4
_IMPACT_WORKSTREAM_LIMIT_DEFAULT = 5
_IMPACT_WORKSTREAM_LIMIT_BROAD = 3
_IMPACT_WORKSTREAM_LIMIT_AMBIGUOUS = 3
_IMPACT_WORKSTREAM_LIMIT_EXPLICIT = 3
_IMPACT_DOC_LIMIT_DEFAULT = 12
_IMPACT_DOC_LIMIT_BROAD = 6
_IMPACT_DOC_LIMIT_AMBIGUOUS = 8
_IMPACT_DOC_LIMIT_EXPLICIT = 6
_IMPACT_COMMAND_LIMIT_DEFAULT = 8
_IMPACT_COMMAND_LIMIT_BROAD = 4
_IMPACT_COMMAND_LIMIT_AMBIGUOUS = 6
_IMPACT_COMMAND_LIMIT_EXPLICIT = 5
_IMPACT_TEST_LIMIT_DEFAULT = 6
_IMPACT_TEST_LIMIT_AMBIGUOUS = 4
_IMPACT_TEST_LIMIT_EXPLICIT = 4
_IMPACT_ENGINEERING_NOTES_TOTAL_LIMIT_DEFAULT = 12
_IMPACT_ENGINEERING_NOTES_TOTAL_LIMIT_BROAD = 6
_IMPACT_ENGINEERING_NOTES_TOTAL_LIMIT_AMBIGUOUS = 6
_IMPACT_ENGINEERING_NOTES_TOTAL_LIMIT_EXPLICIT = 6
_IMPACT_ENGINEERING_NOTES_PER_KIND_LIMIT_DEFAULT = 2
_IMPACT_ENGINEERING_NOTES_PER_KIND_LIMIT_AMBIGUOUS = 1
_IMPACT_ENGINEERING_NOTES_PER_KIND_LIMIT_EXPLICIT = 1


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _env_truthy(name: str) -> bool:
    token = str(os.environ.get(str(name or "").strip(), "")).strip().lower()
    return token in {"1", "true", "yes", "on", "enabled"}


def runtime_root(*, repo_root: Path) -> Path:
    return odylith_control_state.runtime_root(repo_root=repo_root)


def projection_snapshot_path(*, repo_root: Path) -> Path:
    return odylith_projection_snapshot.snapshot_path(repo_root=repo_root)


def state_path(*, repo_root: Path) -> Path:
    return odylith_control_state.state_path(repo_root=repo_root)


def state_js_path(*, repo_root: Path) -> Path:
    return odylith_control_state.state_js_path(repo_root=repo_root)


def ensure_state_js_probe_asset(*, repo_root: Path) -> Path | None:
    return odylith_control_state.ensure_state_js_probe_asset(repo_root=repo_root)


def events_path(*, repo_root: Path) -> Path:
    return odylith_control_state.events_path(repo_root=repo_root)


def timings_path(*, repo_root: Path) -> Path:
    return odylith_control_state.timings_path(repo_root=repo_root)


def pid_path(*, repo_root: Path) -> Path:
    return (runtime_root(repo_root=repo_root) / PID_FILENAME).resolve()


def daemon_metadata_path(*, repo_root: Path) -> Path:
    return (runtime_root(repo_root=repo_root) / DAEMON_METADATA_FILENAME).resolve()


def stop_path(*, repo_root: Path) -> Path:
    return (runtime_root(repo_root=repo_root) / STOP_FILENAME).resolve()


def socket_path(*, repo_root: Path) -> Path:
    preferred = (runtime_root(repo_root=repo_root) / SOCKET_FILENAME).resolve()
    if len(str(preferred)) < 100:
        return preferred
    token = odylith_context_cache.fingerprint_payload(str(Path(repo_root).resolve()))[:16]
    return (Path(tempfile.gettempdir()) / f"odylith-tooling-{token}.sock").resolve()


def daemon_usage_path(*, repo_root: Path) -> Path:
    return (runtime_root(repo_root=repo_root) / DAEMON_USAGE_FILENAME).resolve()


def proof_surfaces_path(*, repo_root: Path) -> Path:
    return (runtime_root(repo_root=repo_root) / PROOF_SURFACES_FILENAME).resolve()


def sessions_root(*, repo_root: Path) -> Path:
    return (runtime_root(repo_root=repo_root) / SESSIONS_DIRNAME).resolve()


def bootstraps_root(*, repo_root: Path) -> Path:
    return (runtime_root(repo_root=repo_root) / BOOTSTRAPS_DIRNAME).resolve()


def judgment_memory_path(*, repo_root: Path) -> Path:
    return (odylith_memory_backend.local_backend_root(repo_root=repo_root) / JUDGMENT_MEMORY_FILENAME).resolve()


def _load_runtime_proof_surfaces(*, repo_root: Path) -> dict[str, Any]:
    payload = odylith_context_cache.read_json_object(proof_surfaces_path(repo_root=repo_root))
    return dict(payload) if isinstance(payload, Mapping) else {}


def _runtime_proof_section(*, repo_root: Path, section: str) -> dict[str, Any]:
    payload = _load_runtime_proof_surfaces(repo_root=repo_root)
    value = payload.get(section)
    return dict(value) if isinstance(value, Mapping) else {}


def _persist_runtime_proof_section(
    *,
    repo_root: Path,
    section: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    existing = _load_runtime_proof_surfaces(repo_root=root)
    document = {
        "contract": "odylith_proof_surfaces.v1",
        "version": "v1",
        "updated_utc": _utc_now(),
    }
    for key, value in existing.items():
        if key in {"contract", "version", "updated_utc"}:
            continue
        if isinstance(value, Mapping):
            document[key] = dict(value)
    section_payload = dict(payload)
    section_payload.setdefault("recorded_utc", _utc_now())
    document[section] = section_payload
    odylith_context_cache.write_json_if_changed(
        repo_root=root,
        path=proof_surfaces_path(repo_root=root),
        payload=document,
        lock_key=str(proof_surfaces_path(repo_root=root)),
    )
    return section_payload


def _memory_backend_proof_signature(
    *,
    state: Mapping[str, Any],
    backend_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "projection_fingerprint": str(state.get("projection_fingerprint", "")).strip(),
        "projection_scope": str(state.get("projection_scope", "")).strip(),
        "manifest_projection_fingerprint": str(backend_manifest.get("projection_fingerprint", "")).strip(),
        "document_count": int(backend_manifest.get("document_count", 0) or 0),
        "edge_count": int(backend_manifest.get("edge_count", 0) or 0),
    }


def _architecture_evaluation_proof_signature(
    *,
    repo_root: Path,
    corpus: Mapping[str, Any],
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    state = read_runtime_state(repo_root=root)
    architecture_bundle = odylith_architecture_mode.load_architecture_bundle(repo_root=root)
    architecture_cases = odylith_benchmark_contract.architecture_benchmark_scenarios(corpus)
    case_ids = [
        str(row.get("case_id", "")).strip()
        for row in architecture_cases
        if str(row.get("case_id", "")).strip()
    ]
    return {
        "projection_fingerprint": str(state.get("projection_fingerprint", "")).strip(),
        "projection_scope": str(state.get("projection_scope", "")).strip(),
        "corpus_fingerprint": odylith_context_cache.fingerprint_paths(
            [optimization_evaluation_corpus_path(repo_root=root)]
        ),
        "case_ids": case_ids,
        "bundle_signature": odylith_architecture_mode._architecture_bundle_signature(  # noqa: SLF001
            repo_root=root,
            bundle=architecture_bundle,
        ),
        "mermaid_drift_hash": _architecture_bundle_mermaid_signature_hash(
            repo_root=root,
            bundle=architecture_bundle,
        ),
    }


def _memory_backend_sticky_snapshot_compatible(
    *,
    live_signature: Mapping[str, Any],
    sticky_signature: Mapping[str, Any],
    observed_backend: Mapping[str, Any],
    sticky_backend: Mapping[str, Any],
) -> bool:
    if dict(sticky_signature) == dict(live_signature):
        return True
    observed_provider = str(observed_backend.get("provider", "")).strip()
    observed_storage = str(observed_backend.get("storage", "")).strip()
    observed_sparse_recall = str(observed_backend.get("sparse_recall", "")).strip()
    sticky_provider = str(sticky_backend.get("provider", "")).strip()
    sticky_storage = str(sticky_backend.get("storage", "")).strip()
    sticky_sparse_recall = str(sticky_backend.get("sparse_recall", "")).strip()
    live_scope = str(live_signature.get("projection_scope", "")).strip() or "default"
    sticky_scope = str(sticky_signature.get("projection_scope", "")).strip() or "default"
    live_doc_count = int(live_signature.get("document_count", 0) or 0)
    sticky_doc_count = int(sticky_signature.get("document_count", 0) or 0)
    live_edge_count = int(live_signature.get("edge_count", 0) or 0)
    sticky_edge_count = int(sticky_signature.get("edge_count", 0) or 0)
    return bool(
        (
            observed_provider == _FALLBACK_LOCAL_MEMORY_BACKEND["provider"]
            or (
                observed_storage == _FALLBACK_LOCAL_MEMORY_BACKEND["storage"]
                and observed_sparse_recall == _FALLBACK_LOCAL_MEMORY_BACKEND["sparse_recall"]
            )
        )
        and sticky_provider == "odylith_memory_backend"
        and sticky_storage == _TARGET_LOCAL_MEMORY_BACKEND["storage"]
        and sticky_sparse_recall == _TARGET_LOCAL_MEMORY_BACKEND["sparse_recall"]
        and odylith_memory_backend.projection_scope_satisfies(
            available_scope=sticky_scope,
            requested_scope=live_scope,
        )
        and sticky_doc_count >= live_doc_count
        and sticky_edge_count >= live_edge_count
    )


def _architecture_evaluation_signature_stable_axes(signature: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "corpus_fingerprint": str(signature.get("corpus_fingerprint", "")).strip(),
        "case_ids": [str(token).strip() for token in signature.get("case_ids", []) if str(token).strip()]
        if isinstance(signature.get("case_ids"), list)
        else [],
    }


def _architecture_evaluation_signatures_compatible(
    live_signature: Mapping[str, Any],
    sticky_signature: Mapping[str, Any],
) -> bool:
    return bool(
        _architecture_evaluation_signature_stable_axes(live_signature)
        and _architecture_evaluation_signature_stable_axes(live_signature)
        == _architecture_evaluation_signature_stable_axes(sticky_signature)
    )


def _architecture_evaluation_snapshot_strength(snapshot: Mapping[str, Any]) -> tuple[int, int, float, float]:
    return (
        int(snapshot.get("covered_case_count", 0) or 0),
        int(snapshot.get("satisfied_case_count", 0) or 0),
        float(snapshot.get("coverage_rate", 0.0) or 0.0),
        float(snapshot.get("satisfaction_rate", 0.0) or 0.0),
    )


def _sticky_snapshot_from_section(
    *,
    repo_root: Path,
    section: str,
    live_snapshot: Mapping[str, Any],
    valid_when: Callable[[Mapping[str, Any]], bool],
) -> dict[str, Any]:
    live = dict(live_snapshot)
    if valid_when(live):
        return live
    sticky = _runtime_proof_section(repo_root=repo_root, section=section)
    if valid_when(sticky):
        merged = dict(sticky)
        merged.setdefault("status", "active")
        merged["evidence_source"] = "sticky_snapshot"
        merged["live_window_empty"] = True
        return merged
    return live


def workspace_daemon_key(*, repo_root: Path) -> str:
    return odylith_context_cache.fingerprint_payload(str(Path(repo_root).resolve()))[:16]


def runtime_request_namespace(
    *,
    repo_root: Path,
    command: str = "",
    changed_paths: Sequence[str] = (),
    session_id: str = "",
    claimed_paths: Sequence[str] = (),
    working_tree_scope: str = "repo",
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    scope_token = str(working_tree_scope or "repo").strip().lower() or "repo"
    normalized_changed = _normalize_changed_path_list(repo_root=root, values=changed_paths)
    normalized_claimed = _normalize_changed_path_list(repo_root=root, values=claimed_paths)
    normalized_session = re.sub(r"[^A-Za-z0-9._-]+", "-", str(session_id or "").strip()).strip("-")
    namespace_payload = {
        "command": str(command or "").strip().lower(),
        "working_tree_scope": scope_token,
        "session_id": normalized_session,
        "changed_paths": normalized_changed,
        "claimed_paths": normalized_claimed,
    }
    request_namespace = odylith_context_cache.fingerprint_payload(namespace_payload)[:16]
    session_namespaced = bool(normalized_session or normalized_claimed or scope_token == "session")
    return {
        "workspace_key": workspace_daemon_key(repo_root=root),
        "request_namespace": request_namespace,
        "session_namespaced": session_namespaced,
        "session_namespace": request_namespace if session_namespaced else "",
        "working_tree_scope": scope_token,
        "session_id_present": bool(normalized_session),
        "claim_path_count": len(normalized_claimed),
        "changed_path_count": len(normalized_changed),
    }


def runtime_request_namespace_from_payload(
    *,
    repo_root: Path,
    command: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    return runtime_request_namespace(
        repo_root=repo_root,
        command=command,
        changed_paths=payload.get("paths", []) if isinstance(payload.get("paths"), list) else (),
        session_id=str(payload.get("session_id", "")).strip(),
        claimed_paths=payload.get("claim_paths", []) if isinstance(payload.get("claim_paths"), list) else (),
        working_tree_scope=str(payload.get("working_tree_scope", "repo")).strip() or "repo",
    )


def _runtime_daemon_pid(*, repo_root: Path) -> int:
    path = pid_path(repo_root=repo_root)
    if not path.is_file():
        return 0
    try:
        return max(0, int(path.read_text(encoding="utf-8").strip() or 0))
    except (OSError, ValueError):
        return 0


def _read_runtime_daemon_metadata(*, repo_root: Path) -> dict[str, Any]:
    path = daemon_metadata_path(repo_root=repo_root)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, Mapping):
        return {}
    try:
        pid = max(0, int(payload.get("pid", 0) or 0))
    except (TypeError, ValueError):
        pid = 0
    return {
        "pid": pid,
        "auth_token": str(payload.get("auth_token", "")).strip(),
        "spawn_reason": str(payload.get("spawn_reason", "")).strip(),
        "started_utc": str(payload.get("started_utc", "")).strip(),
    }


def _runtime_daemon_pid_alive(pid: int) -> bool:
    if int(pid or 0) <= 0:
        return False
    try:
        os.kill(int(pid), 0)
    except OSError:
        return False
    return True


def _runtime_daemon_owner_pid(*, repo_root: Path) -> int:
    pid = _runtime_daemon_pid(repo_root=repo_root)
    if pid > 0:
        return pid
    metadata_pid = int(_read_runtime_daemon_metadata(repo_root=repo_root).get("pid", 0) or 0)
    return metadata_pid if metadata_pid > 0 else 0


def _normalize_loopback_host(value: Any) -> str:
    token = str(value or "").strip().lower()
    if not token:
        return "127.0.0.1"
    if token in {"127.0.0.1", "localhost", "::1"}:
        return token
    return ""


def runtime_daemon_transport(*, repo_root: Path) -> dict[str, Any] | None:
    root = Path(repo_root).resolve()
    owner_pid = _runtime_daemon_owner_pid(repo_root=root)
    if not _runtime_daemon_pid_alive(owner_pid):
        return None
    runtime_socket = socket_path(repo_root=root)
    try:
        if runtime_socket.is_socket():
            return {
                "transport": "unix",
                "path": str(runtime_socket),
                "pid": owner_pid,
            }
    except OSError:
        return None
    if not runtime_socket.is_file():
        return None
    try:
        payload = json.loads(runtime_socket.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, Mapping):
        return None
    transport = str(payload.get("transport", "")).strip().lower()
    if transport != "tcp":
        return None
    host = _normalize_loopback_host(payload.get("host", ""))
    if not host:
        return None
    try:
        port = int(payload.get("port", 0) or 0)
    except (TypeError, ValueError):
        return None
    try:
        transport_pid = int(payload.get("pid", 0) or 0)
    except (TypeError, ValueError):
        transport_pid = 0
    if port <= 0:
        return None
    if transport_pid > 0 and transport_pid != owner_pid:
        return None
    return {
        "transport": "tcp",
        "host": host,
        "port": port,
        "pid": owner_pid,
    }


def request_runtime_daemon(
    *,
    repo_root: Path,
    command: str,
    payload: Mapping[str, Any] | None = None,
    required: bool = False,
    timeout_seconds: float = 5.0,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    root = Path(repo_root).resolve()
    daemon_metadata = _read_runtime_daemon_metadata(repo_root=root)
    transport = runtime_daemon_transport(repo_root=root)
    if transport is None:
        if required:
            raise RuntimeError("odylith context engine daemon unavailable")
        return None
    started_at = time.perf_counter()
    command_token = str(command or "").strip()
    request_payload = dict(payload or {})
    session_scope = runtime_request_namespace_from_payload(
        repo_root=root,
        command=command_token,
        payload=request_payload,
    )
    if str(transport.get("transport", "")).strip() == "tcp":
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connect_target: Any = (
            str(transport.get("host", "")).strip() or "127.0.0.1",
            int(transport.get("port", 0) or 0),
        )
    else:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connect_target = str(transport.get("path", "")).strip() or str(socket_path(repo_root=root))
    sock.settimeout(timeout_seconds)
    try:
        sock.connect(connect_target)
        rendered = json.dumps(
            {
                "command": command_token,
                "payload": request_payload,
                **({"auth_token": str(daemon_metadata.get("auth_token", "")).strip()} if str(daemon_metadata.get("auth_token", "")).strip() else {}),
            },
            sort_keys=True,
        ).encode("utf-8") + b"\n"
        sock.sendall(rendered)
        sock.shutdown(socket.SHUT_WR)
        chunks: list[bytes] = []
        while True:
            data = sock.recv(65536)
            if not data:
                break
            chunks.append(data)
    except OSError as exc:
        if required:
            raise RuntimeError("odylith context engine daemon request failed") from exc
        return None
    finally:
        with contextlib.suppress(OSError):
            sock.close()
    if not chunks:
        if required:
            raise RuntimeError("odylith context engine daemon returned no response")
        return None
    try:
        response = json.loads(b"".join(chunks).decode("utf-8"))
    except json.JSONDecodeError as exc:
        if required:
            raise RuntimeError("odylith context engine daemon returned invalid JSON") from exc
        return None
    if not isinstance(response, Mapping):
        if required:
            raise RuntimeError("odylith context engine daemon returned an invalid payload")
        return None
    if not bool(response.get("ok", False)):
        message = str(response.get("error", "")).strip() or "odylith context engine daemon request failed"
        if required:
            raise RuntimeError(message)
        return None
    daemon_payload = response.get("payload", {})
    runtime_execution = {
        "source": "workspace_daemon",
        "transport": str(transport.get("transport", "")).strip() or "unknown",
        "workspace_daemon_reused": True,
        "workspace_key": str(session_scope.get("workspace_key", "")).strip(),
        "request_namespace": str(session_scope.get("request_namespace", "")).strip(),
        "session_namespaced": bool(session_scope.get("session_namespaced")),
        "session_namespace": str(session_scope.get("session_namespace", "")).strip(),
        "working_tree_scope": str(session_scope.get("working_tree_scope", "")).strip(),
        "session_id_present": bool(session_scope.get("session_id_present")),
        "claim_path_count": int(session_scope.get("claim_path_count", 0) or 0),
        "changed_path_count": int(session_scope.get("changed_path_count", 0) or 0),
    }
    record_runtime_timing(
        repo_root=root,
        category="daemon",
        operation=command_token or "request",
        duration_ms=(time.perf_counter() - started_at) * 1000.0,
        metadata={
            "required": bool(required),
            "transport": str(runtime_execution["transport"]),
            "authenticated": bool(str(daemon_metadata.get("auth_token", "")).strip()),
            "workspace_daemon_reused": True,
            "session_namespaced": bool(runtime_execution["session_namespaced"]),
            "session_namespace": str(runtime_execution["session_namespace"]),
            "request_namespace": str(runtime_execution["request_namespace"]),
        },
    )
    return (
        dict(daemon_payload) if isinstance(daemon_payload, Mapping) else {"value": daemon_payload},
        runtime_execution,
    )


def read_runtime_daemon_usage(*, repo_root: Path) -> dict[str, Any]:
    payload = odylith_context_cache.read_json_object(daemon_usage_path(repo_root=repo_root))
    if not payload:
        return {}
    command_counts = {
        str(key).strip(): int(value or 0)
        for key, value in dict(payload.get("command_counts", {})).items()
        if str(key).strip()
    } if isinstance(payload.get("command_counts"), Mapping) else {}
    recent_namespaces = [
        str(token).strip()
        for token in payload.get("recent_session_namespaces", [])
        if str(token).strip()
    ] if isinstance(payload.get("recent_session_namespaces"), list) else []
    seen_namespaces = [
        str(token).strip()
        for token in payload.get("seen_session_namespaces", [])
        if str(token).strip()
    ] if isinstance(payload.get("seen_session_namespaces"), list) else []
    return {
        "workspace_key": str(payload.get("workspace_key", "")).strip(),
        "request_count": int(payload.get("request_count", 0) or 0),
        "session_scoped_request_count": int(payload.get("session_scoped_request_count", 0) or 0),
        "unique_session_namespace_count": int(payload.get("unique_session_namespace_count", 0) or 0),
        "last_command": str(payload.get("last_command", "")).strip(),
        "last_request_utc": str(payload.get("last_request_utc", "")).strip(),
        "last_session_namespace": str(payload.get("last_session_namespace", "")).strip(),
        "last_working_tree_scope": str(payload.get("last_working_tree_scope", "")).strip(),
        "recent_session_namespaces": recent_namespaces[:8],
        "seen_session_namespaces": seen_namespaces[:64],
        "command_counts": command_counts,
    }


def record_runtime_daemon_usage(
    *,
    repo_root: Path,
    command: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    target = daemon_usage_path(repo_root=root)
    target.parent.mkdir(parents=True, exist_ok=True)
    scope = runtime_request_namespace_from_payload(
        repo_root=root,
        command=command,
        payload=payload,
    )
    with odylith_context_cache.advisory_lock(repo_root=root, key=str(target)):
        existing = read_runtime_daemon_usage(repo_root=root)
        command_counts = dict(existing.get("command_counts", {})) if isinstance(existing.get("command_counts"), Mapping) else {}
        command_token = str(command or "").strip() or "request"
        command_counts[command_token] = int(command_counts.get(command_token, 0) or 0) + 1
        recent_namespaces = [
            token
            for token in existing.get("recent_session_namespaces", [])
            if str(token).strip()
        ] if isinstance(existing.get("recent_session_namespaces"), list) else []
        seen_namespaces = [
            token
            for token in existing.get("seen_session_namespaces", [])
            if str(token).strip()
        ] if isinstance(existing.get("seen_session_namespaces"), list) else []
        session_namespace = str(scope.get("session_namespace", "")).strip()
        if session_namespace:
            recent_namespaces = [session_namespace, *[token for token in recent_namespaces if token != session_namespace]][:8]
            if session_namespace not in seen_namespaces:
                seen_namespaces = [session_namespace, *seen_namespaces][:64]
        updated_payload = {
            "workspace_key": str(scope.get("workspace_key", "")).strip() or workspace_daemon_key(repo_root=root),
            "request_count": int(existing.get("request_count", 0) or 0) + 1,
            "session_scoped_request_count": int(existing.get("session_scoped_request_count", 0) or 0)
            + (1 if bool(scope.get("session_namespaced")) else 0),
            "unique_session_namespace_count": len(seen_namespaces),
            "last_command": command_token,
            "last_request_utc": _utc_now(),
            "last_session_namespace": session_namespace,
            "last_working_tree_scope": str(scope.get("working_tree_scope", "")).strip(),
            "recent_session_namespaces": recent_namespaces,
            "seen_session_namespaces": seen_namespaces,
            "command_counts": command_counts,
        }
        rendered = json.dumps(updated_payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        current = target.read_text(encoding="utf-8") if target.is_file() else ""
        if current != rendered:
            target.write_text(rendered, encoding="utf-8")
    return updated_payload


def _safe_unlink(path: Path) -> bool:
    try:
        path.unlink()
    except FileNotFoundError:
        return False
    except OSError:
        return False
    return True


def _record_sort_timestamp(*, payload: Mapping[str, Any], key: str, path: Path) -> float:
    parsed = _parse_iso_utc(str(payload.get(key, "")).strip())
    if parsed is not None:
        return parsed.timestamp()
    try:
        return float(path.stat().st_mtime)
    except OSError:
        return 0.0


def prune_runtime_records(*, repo_root: Path) -> dict[str, int]:
    """Prune stale/invalid runtime records and keep local state bounded."""

    root = Path(repo_root).resolve()
    summary = {
        "active_sessions": 0,
        "stale_sessions_pruned": 0,
        "invalid_sessions_pruned": 0,
        "session_retention_pruned": 0,
        "bootstrap_packets": 0,
        "invalid_bootstraps_pruned": 0,
        "bootstrap_retention_pruned": 0,
    }

    sessions_dir = sessions_root(repo_root=root)
    if sessions_dir.is_dir():
        valid_sessions: list[tuple[Path, dict[str, Any]]] = []
        now = dt.datetime.now(dt.timezone.utc)
        with odylith_context_cache.advisory_lock(repo_root=root, key=str(sessions_dir)):
            for path in sorted(sessions_dir.glob("*.json")):
                payload = odylith_context_cache.read_json_object(path)
                if not payload:
                    if _safe_unlink(path):
                        summary["invalid_sessions_pruned"] += 1
                    continue
                if _is_session_expired(payload, now=now):
                    if _safe_unlink(path):
                        summary["stale_sessions_pruned"] += 1
                    continue
                valid_sessions.append((path, payload))
            valid_sessions.sort(
                key=lambda item: _record_sort_timestamp(payload=item[1], key="updated_utc", path=item[0]),
                reverse=True,
            )
            for path, _payload in valid_sessions[_SESSION_RECORD_RETENTION_LIMIT:]:
                if _safe_unlink(path):
                    summary["session_retention_pruned"] += 1
        summary["active_sessions"] = max(
            0,
            len(valid_sessions) - summary["session_retention_pruned"],
        )

    bootstraps_dir = bootstraps_root(repo_root=root)
    if bootstraps_dir.is_dir():
        valid_bootstraps: list[tuple[Path, dict[str, Any]]] = []
        with odylith_context_cache.advisory_lock(repo_root=root, key=str(bootstraps_dir)):
            for path in sorted(bootstraps_dir.glob("*.json")):
                payload = odylith_context_cache.read_json_object(path)
                if not payload:
                    if _safe_unlink(path):
                        summary["invalid_bootstraps_pruned"] += 1
                    continue
                valid_bootstraps.append((path, payload))
            valid_bootstraps.sort(
                key=lambda item: _record_sort_timestamp(payload=item[1], key="bootstrapped_at", path=item[0]),
                reverse=True,
            )
            for path, _payload in valid_bootstraps[_BOOTSTRAP_RECORD_RETENTION_LIMIT:]:
                if _safe_unlink(path):
                    summary["bootstrap_retention_pruned"] += 1
        summary["bootstrap_packets"] = max(
            0,
            len(valid_bootstraps) - summary["bootstrap_retention_pruned"],
        )

    return summary


def _projection_names_for_scope(scope: str) -> tuple[str, ...]:
    token = str(scope or "default").strip().lower()
    if token == "full":
        return (*_BASE_PROJECTION_NAMES, *_FULL_ONLY_PROJECTION_NAMES)
    if token == "reasoning":
        return _REASONING_PROJECTION_NAMES
    return _BASE_PROJECTION_NAMES


def _watchdog_available() -> bool:
    try:
        import watchdog.observers  # type: ignore  # pragma: no cover
    except ImportError:  # pragma: no cover - optional dependency
        return False
    return True


def git_fsmonitor_status(*, repo_root: Path) -> dict[str, Any]:
    """Return availability and activation status for Git's fsmonitor daemon."""

    root = Path(repo_root).resolve()
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "fsmonitor--daemon", "status"],
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError:
        return {
            "supported": False,
            "active": False,
            "detail": "",
            "returncode": 127,
        }
    detail = "\n".join(
        token
        for token in (
            str(completed.stdout or "").strip(),
            str(completed.stderr or "").strip(),
        )
        if token
    ).strip()
    normalized = detail.lower()
    supported = "fsmonitor-daemon" in normalized and "not a git command" not in normalized
    active = supported and " is watching " in normalized
    return {
        "supported": supported,
        "active": active,
        "detail": detail,
        "returncode": int(completed.returncode),
    }


def bootstrap_git_fsmonitor(*, repo_root: Path) -> dict[str, Any]:
    """Start Git fsmonitor when supported, keeping the operation local-only."""

    root = Path(repo_root).resolve()
    before = git_fsmonitor_status(repo_root=root)
    if not bool(before.get("supported")):
        return {
            "supported": False,
            "active": False,
            "started": False,
            "status": "unsupported",
            "detail": str(before.get("detail", "")).strip(),
        }
    if bool(before.get("active")):
        return {
            "supported": True,
            "active": True,
            "started": False,
            "status": "already-active",
            "detail": str(before.get("detail", "")).strip(),
        }
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "fsmonitor--daemon", "start"],
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError as exc:
        return {
            "supported": True,
            "active": False,
            "started": False,
            "status": "failed",
            "detail": str(exc),
        }
    after = git_fsmonitor_status(repo_root=root)
    if bool(after.get("active")):
        detail = str(after.get("detail", "")).strip() or str(completed.stdout or "").strip()
        return {
            "supported": True,
            "active": True,
            "started": True,
            "status": "started",
            "detail": detail,
        }
    detail = "\n".join(
        token
        for token in (
            str(completed.stdout or "").strip(),
            str(completed.stderr or "").strip(),
            str(after.get("detail", "")).strip(),
        )
        if token
    ).strip()
    return {
        "supported": True,
        "active": False,
        "started": False,
        "status": "failed",
        "detail": detail,
    }


def watcher_backend_report(*, repo_root: Path) -> dict[str, Any]:
    """Describe watcher capability and the best local backend currently usable."""

    root = Path(repo_root).resolve()
    watchman_available = bool(shutil.which("watchman"))
    watchdog_available = _watchdog_available()
    git_fsmonitor = git_fsmonitor_status(repo_root=root)
    preferred = "poll"
    if watchman_available:
        preferred = "watchman"
    elif watchdog_available:
        preferred = "watchdog"
    elif bool(git_fsmonitor.get("active")):
        preferred = "git-fsmonitor"
    best_bootstrappable = "watchman" if watchman_available else "watchdog" if watchdog_available else "git-fsmonitor" if bool(git_fsmonitor.get("supported")) else "poll"
    bootstrap_recommended = preferred == "poll" and best_bootstrappable == "git-fsmonitor"
    return {
        "watchman_available": watchman_available,
        "watchdog_available": watchdog_available,
        "git_fsmonitor_supported": bool(git_fsmonitor.get("supported")),
        "git_fsmonitor_active": bool(git_fsmonitor.get("active")),
        "git_fsmonitor_detail": str(git_fsmonitor.get("detail", "")).strip(),
        "preferred_backend": preferred,
        "best_bootstrappable_backend": best_bootstrappable,
        "bootstrap_recommended": bootstrap_recommended,
    }


def preferred_watcher_backend(*, repo_root: Path | None = None) -> str:
    """Return the preferred local invalidation backend available in this env."""

    if shutil.which("watchman"):
        return "watchman"
    if _watchdog_available():
        return "watchdog"
    if repo_root is not None and bool(git_fsmonitor_status(repo_root=Path(repo_root).resolve()).get("active")):
        return "git-fsmonitor"
    return "poll"


def watch_targets(*, repo_root: Path) -> tuple[str, ...]:
    """Return the canonical repo-relative inputs that should invalidate projections."""

    _ = Path(repo_root).resolve()
    ordered = (
        "odylith/radar/source/INDEX.md",
        "odylith/radar/source/archive",
        "odylith/radar/source/ideas",
        "odylith/technical-plans/INDEX.md",
        "odylith/technical-plans/archive",
        "odylith/casebook/bugs/INDEX.md",
        "odylith/casebook/bugs/archive",
        component_registry.DEFAULT_MANIFEST_PATH,
        component_registry.DEFAULT_CATALOG_PATH,
        component_registry.DEFAULT_IDEAS_ROOT,
        component_registry.DEFAULT_STREAM_PATH,
        component_registry.DEFAULT_TRACEABILITY_GRAPH_PATH,
        "odylith/compass/runtime/codex-stream.v1.jsonl",
        delivery_intelligence_engine.DEFAULT_OUTPUT_PATH,
        *_ENGINEERING_WATCH_PATHS,
        "docs/runbooks",
        "scripts",
        "app",
        "infra",
        "tests",
        "contracts",
        "mk",
        "service-deploy/service_deploy",
    )
    seen: set[str] = set()
    rows: list[str] = []
    for raw in ordered:
        token = Path(str(raw).strip()).as_posix().strip("/")
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return tuple(rows)


def read_runtime_state(*, repo_root: Path) -> dict[str, Any]:
    return odylith_control_state.read_state(repo_root=repo_root)


def write_runtime_state(*, repo_root: Path, payload: Mapping[str, Any]) -> None:
    odylith_control_state.write_state(repo_root=repo_root, payload=payload)


def append_runtime_event(*, repo_root: Path, event_type: str, payload: Mapping[str, Any]) -> None:
    odylith_control_state.append_event(
        repo_root=repo_root,
        event_type=str(event_type).strip() or "projection_update",
        payload=dict(payload),
        version=SCHEMA_VERSION,
        ts_iso=_utc_now(),
    )


def record_runtime_timing(
    *,
    repo_root: Path,
    category: str,
    operation: str,
    duration_ms: float,
    metadata: Mapping[str, Any] | None = None,
) -> None:
    ts_iso = _utc_now()
    odylith_control_state.append_timing(
        repo_root=Path(repo_root).resolve(),
        row={
            "timing_id": odylith_context_cache.fingerprint_payload(
                {
                    "ts_iso": ts_iso,
                    "pid": os.getpid(),
                    "category": str(category or "").strip(),
                    "operation": str(operation or "").strip(),
                    "duration_ms": round(float(duration_ms or 0.0), 3),
                    "metadata": dict(metadata or {}),
                }
            ),
            "ts_iso": ts_iso,
            "category": str(category or "").strip() or "runtime",
            "operation": str(operation or "").strip() or "unknown",
            "duration_ms": round(float(duration_ms or 0.0), 3),
            "metadata": dict(metadata or {}),
        },
        retention_limit=_RUNTIME_TIMING_LIMIT,
    )



load_runtime_timing_summary = odylith_context_engine_runtime_learning_runtime.load_runtime_timing_summary

load_odylith_drawer_history = odylith_context_engine_runtime_learning_runtime.load_odylith_drawer_history

_optimization_level_from_rate = odylith_context_engine_runtime_learning_runtime._optimization_level_from_rate

_sorted_count_map = odylith_context_engine_runtime_learning_runtime._sorted_count_map

optimization_evaluation_corpus_path = odylith_context_engine_runtime_learning_runtime.optimization_evaluation_corpus_path

_normalized_string_list = odylith_context_engine_runtime_learning_runtime._normalized_string_list

_truncate_text = odylith_context_engine_runtime_learning_runtime._truncate_text

_safe_file_size = odylith_context_engine_runtime_learning_runtime._safe_file_size

_table_row_count = odylith_context_engine_runtime_learning_runtime._table_row_count

_odylith_switch_snapshot = odylith_context_engine_runtime_learning_runtime._odylith_switch_snapshot

_odylith_ablation_active = odylith_context_engine_runtime_learning_runtime._odylith_ablation_active

_memory_area_entry = odylith_context_engine_runtime_learning_runtime._memory_area_entry

_memory_area_label_list = odylith_context_engine_runtime_learning_runtime._memory_area_label_list

_memory_areas_headline = odylith_context_engine_runtime_learning_runtime._memory_areas_headline

_judgment_memory_headline = odylith_context_engine_runtime_learning_runtime._judgment_memory_headline

_memory_snapshot_status_from_counts = odylith_context_engine_runtime_learning_runtime._memory_snapshot_status_from_counts

_freshness_bucket_for_age_hours = odylith_context_engine_runtime_learning_runtime._freshness_bucket_for_age_hours

_freshness_payload = odylith_context_engine_runtime_learning_runtime._freshness_payload

_latest_updated_utc = odylith_context_engine_runtime_learning_runtime._latest_updated_utc

_relative_repo_path = odylith_context_engine_runtime_learning_runtime._relative_repo_path

_humanize_slug = odylith_context_engine_runtime_learning_runtime._humanize_slug

_workstream_token = odylith_context_engine_runtime_learning_runtime._workstream_token

_compact_selection_state_parts = odylith_context_engine_runtime_learning_runtime._compact_selection_state_parts

_encode_compact_selection_state = odylith_context_engine_runtime_learning_runtime._encode_compact_selection_state

_decode_compact_selected_counts = odylith_context_engine_runtime_learning_runtime._decode_compact_selected_counts

_encode_compact_selected_counts = odylith_context_engine_runtime_learning_runtime._encode_compact_selected_counts

_payload_workstream_hint = odylith_context_engine_runtime_learning_runtime._payload_workstream_hint

_payload_packet_kind = odylith_context_engine_runtime_learning_runtime._payload_packet_kind

_judgment_memory_item = odylith_context_engine_runtime_learning_runtime._judgment_memory_item

_judgment_memory_area = odylith_context_engine_runtime_learning_runtime._judgment_memory_area

_provenance_item = odylith_context_engine_runtime_learning_runtime._provenance_item

_derive_retrieval_memory_state = odylith_context_engine_runtime_learning_runtime._derive_retrieval_memory_state

_load_latest_benchmark_report_snapshot = odylith_context_engine_runtime_learning_runtime._load_latest_benchmark_report_snapshot

_build_judgment_memory_snapshot = odylith_context_engine_runtime_learning_runtime._build_judgment_memory_snapshot

_build_memory_areas_snapshot = odylith_context_engine_runtime_learning_runtime._build_memory_areas_snapshot

_odylith_disabled_memory_snapshot = odylith_context_engine_runtime_learning_runtime._odylith_disabled_memory_snapshot

_odylith_disabled_optimization_snapshot = odylith_context_engine_runtime_learning_runtime._odylith_disabled_optimization_snapshot

_odylith_disabled_evaluation_snapshot = odylith_context_engine_runtime_learning_runtime._odylith_disabled_evaluation_snapshot

_rebuild_component_entry = odylith_context_engine_runtime_learning_runtime._rebuild_component_entry

_apply_odylith_component_index_ablation = odylith_context_engine_runtime_learning_runtime._apply_odylith_component_index_ablation

_apply_odylith_registry_snapshot_ablation = odylith_context_engine_runtime_learning_runtime._apply_odylith_registry_snapshot_ablation

_odylith_runtime_entity_suppressed = odylith_context_engine_runtime_learning_runtime._odylith_runtime_entity_suppressed

_odylith_query_targets_disabled = odylith_context_engine_runtime_learning_runtime._odylith_query_targets_disabled

_filter_odylith_search_results = odylith_context_engine_runtime_learning_runtime._filter_odylith_search_results

load_runtime_memory_snapshot = odylith_context_engine_runtime_learning_runtime.load_runtime_memory_snapshot

_load_recent_bootstrap_packets = odylith_context_engine_runtime_learning_runtime._load_recent_bootstrap_packets

_packet_summary_from_bootstrap_payload = odylith_context_engine_runtime_learning_runtime._packet_summary_from_bootstrap_payload

_repo_paths_overlap = odylith_context_engine_runtime_learning_runtime._repo_paths_overlap

_file_cache_signature = odylith_context_engine_runtime_learning_runtime._file_cache_signature

_judgment_memory_snapshot_cached = odylith_context_engine_runtime_learning_runtime._judgment_memory_snapshot_cached

_load_judgment_workstream_hint = odylith_context_engine_runtime_learning_runtime._load_judgment_workstream_hint

_repo_scan_degraded_reason = odylith_context_engine_runtime_learning_runtime._repo_scan_degraded_reason

_governance_runtime_first_snapshot = odylith_context_engine_runtime_learning_runtime._governance_runtime_first_snapshot

_packet_benchmark_summary_for_runtime_packet = odylith_context_engine_runtime_learning_runtime._packet_benchmark_summary_for_runtime_packet

_expected_token_set = odylith_context_engine_runtime_learning_runtime._expected_token_set

_packet_matches_evaluation_case = odylith_context_engine_runtime_learning_runtime._packet_matches_evaluation_case

_packet_satisfies_evaluation_expectations = odylith_context_engine_runtime_learning_runtime._packet_satisfies_evaluation_expectations

_architecture_timing_matches_evaluation_case = odylith_context_engine_runtime_learning_runtime._architecture_timing_matches_evaluation_case

_architecture_timing_satisfies_evaluation_expectations = odylith_context_engine_runtime_learning_runtime._architecture_timing_satisfies_evaluation_expectations

_architecture_evaluation_snapshot = odylith_context_engine_runtime_learning_runtime._architecture_evaluation_snapshot

orchestration_decision_ledgers_root = odylith_context_engine_runtime_learning_runtime.orchestration_decision_ledgers_root

_orchestration_adoption_snapshot_cache_signature = odylith_context_engine_runtime_learning_runtime._orchestration_adoption_snapshot_cache_signature

load_orchestration_adoption_snapshot = odylith_context_engine_runtime_learning_runtime.load_orchestration_adoption_snapshot

persist_orchestration_adoption_snapshot = odylith_context_engine_runtime_learning_runtime.persist_orchestration_adoption_snapshot

load_runtime_optimization_snapshot = odylith_context_engine_runtime_learning_runtime.load_runtime_optimization_snapshot



def load_runtime_evaluation_snapshot(
    *,
    repo_root: Path,
    bootstrap_limit: int = 24,
) -> dict[str, Any]:
    return odylith_context_engine_memory_snapshot_runtime.load_runtime_evaluation_snapshot(repo_root=repo_root, bootstrap_limit=bootstrap_limit)



class _ProjectionCursor:
    def __init__(self, rows: Sequence[Mapping[str, Any]]) -> None:
        self._rows = [dict(row) for row in rows if isinstance(row, Mapping)]

    def fetchall(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self._rows]

    def fetchone(self) -> dict[str, Any] | None:
        return dict(self._rows[0]) if self._rows else None


_ProjectionConnection = odylith_context_engine_projection_query_runtime._ProjectionConnection



_projection_snapshot_cache_signature = odylith_context_engine_projection_query_runtime._projection_snapshot_cache_signature



_connect = odylith_context_engine_projection_query_runtime._connect



_path_fingerprint = odylith_context_engine_projection_query_runtime._path_fingerprint



_test_history_report_inputs = odylith_context_engine_projection_query_runtime._test_history_report_inputs



_workspace_activity_fingerprint = odylith_context_engine_projection_query_runtime._workspace_activity_fingerprint



_radar_source_root = odylith_context_engine_projection_query_runtime._radar_source_root



_technical_plans_root = odylith_context_engine_projection_query_runtime._technical_plans_root



_casebook_bugs_root = odylith_context_engine_projection_query_runtime._casebook_bugs_root



_component_specs_root = odylith_context_engine_projection_query_runtime._component_specs_root



_component_registry_path = odylith_context_engine_projection_query_runtime._component_registry_path



_product_root = odylith_context_engine_projection_query_runtime._product_root



_atlas_catalog_path = odylith_context_engine_projection_query_runtime._atlas_catalog_path



_compass_stream_path = odylith_context_engine_projection_query_runtime._compass_stream_path



_traceability_graph_path = odylith_context_engine_projection_query_runtime._traceability_graph_path



_projected_input_fingerprints = odylith_context_engine_projection_query_runtime._projected_input_fingerprints



projection_input_fingerprint = odylith_context_engine_projection_query_runtime.projection_input_fingerprint



_archive_files = odylith_context_engine_projection_query_runtime._archive_files



_collect_markdown_sections = odylith_context_engine_projection_query_runtime._collect_markdown_sections



_parse_markdown_table = odylith_context_engine_projection_query_runtime._parse_markdown_table



_parse_link_target = odylith_context_engine_projection_query_runtime._parse_link_target



_load_idea_specs = odylith_context_engine_projection_query_runtime._load_idea_specs



_load_backlog_projection = odylith_context_engine_projection_query_runtime._load_backlog_projection



_load_plan_projection = odylith_context_engine_projection_query_runtime._load_plan_projection



_load_bug_projection = odylith_context_engine_projection_query_runtime._load_bug_projection



_normalize_bug_projection_rows = odylith_context_engine_projection_query_runtime._normalize_bug_projection_rows



_normalize_bug_link_target = odylith_context_engine_projection_query_runtime._normalize_bug_link_target



_is_bug_placeholder_row = odylith_context_engine_projection_query_runtime._is_bug_placeholder_row



_safe_json = odylith_context_engine_projection_query_runtime._safe_json



_raw_text = odylith_context_engine_projection_query_runtime._raw_text



_load_codex_event_projection = odylith_context_engine_projection_query_runtime._load_codex_event_projection



_load_traceability_projection = odylith_context_engine_projection_query_runtime._load_traceability_projection



_load_diagram_projection = odylith_context_engine_projection_query_runtime._load_diagram_projection



_looks_like_repo_path = odylith_context_engine_projection_query_runtime._looks_like_repo_path



_extract_path_refs = odylith_context_engine_projection_query_runtime._extract_path_refs



_extract_workstream_refs = odylith_context_engine_projection_query_runtime._extract_workstream_refs



_first_summary = odylith_context_engine_projection_query_runtime._first_summary



_note_title = odylith_context_engine_projection_query_runtime._note_title



_string_list = odylith_context_engine_projection_query_runtime._string_list



_parse_markdown_fields = odylith_context_engine_projection_query_runtime._parse_markdown_fields



_trim_multiline_lines = odylith_context_engine_projection_query_runtime._trim_multiline_lines



_join_bug_field_lines = odylith_context_engine_projection_query_runtime._join_bug_field_lines



_parse_bug_entry_fields = odylith_context_engine_projection_query_runtime._parse_bug_entry_fields



_bug_archive_bucket_from_link_target = odylith_context_engine_projection_query_runtime._bug_archive_bucket_from_link_target



canonicalize_bug_status = odylith_context_engine_projection_query_runtime.canonicalize_bug_status



_bug_is_open = odylith_context_engine_projection_query_runtime._bug_is_open



_ordered_bug_detail_sections = odylith_context_engine_projection_query_runtime._ordered_bug_detail_sections



_bug_summary_from_fields = odylith_context_engine_projection_query_runtime._bug_summary_from_fields



_component_rows_from_index = odylith_context_engine_projection_query_runtime._component_rows_from_index



_build_bug_reference_lookup = odylith_context_engine_projection_query_runtime._build_bug_reference_lookup



_related_bug_refs_from_text = odylith_context_engine_projection_query_runtime._related_bug_refs_from_text



_classify_bug_path_refs = odylith_context_engine_projection_query_runtime._classify_bug_path_refs



_component_matches_for_bug_paths = odylith_context_engine_projection_query_runtime._component_matches_for_bug_paths



_diagram_refs_for_bug_components = odylith_context_engine_projection_query_runtime._diagram_refs_for_bug_components



_bug_intelligence_coverage = odylith_context_engine_projection_query_runtime._bug_intelligence_coverage



_split_bug_guidance_items = odylith_context_engine_projection_query_runtime._split_bug_guidance_items



_bug_agent_guidance = odylith_context_engine_projection_query_runtime._bug_agent_guidance



_load_component_match_rows_from_components = odylith_context_engine_projection_query_runtime._load_component_match_rows_from_components



_load_component_match_rows = odylith_context_engine_projection_query_runtime._load_component_match_rows



_components_for_paths = odylith_context_engine_projection_query_runtime._components_for_paths



_load_adr_notes = odylith_context_engine_projection_query_runtime._load_adr_notes



_load_invariant_notes = odylith_context_engine_projection_query_runtime._load_invariant_notes



_load_data_ownership_notes = odylith_context_engine_projection_query_runtime._load_data_ownership_notes



_load_section_bullet_notes = odylith_context_engine_projection_query_runtime._load_section_bullet_notes



_markdown_title = odylith_context_engine_projection_query_runtime._markdown_title



_load_guidance_chunk_notes = odylith_context_engine_projection_query_runtime._load_guidance_chunk_notes



_load_runbook_notes = odylith_context_engine_projection_query_runtime._load_runbook_notes


_projection_state_row = odylith_context_engine_projection_query_runtime._projection_state_row



_empty_projection_tables = odylith_context_engine_projection_query_runtime._empty_projection_tables



warm_projections = odylith_context_engine_projection_query_runtime.warm_projections



_runtime_enabled = odylith_context_engine_projection_query_runtime._runtime_enabled



_warm_runtime = odylith_context_engine_projection_query_runtime._warm_runtime



_projection_cache_signature = odylith_context_engine_projection_query_runtime._projection_cache_signature



_cached_projection_rows = odylith_context_engine_projection_query_runtime._cached_projection_rows



clear_runtime_process_caches = odylith_context_engine_projection_query_runtime.clear_runtime_process_caches



prime_reasoning_projection_cache = odylith_context_engine_projection_query_runtime.prime_reasoning_projection_cache



_path_signature = odylith_context_engine_projection_query_runtime._path_signature



_architecture_bundle_mermaid_signature_hash = odylith_context_engine_projection_query_runtime._architecture_bundle_mermaid_signature_hash



_bootstraps_signature = odylith_context_engine_projection_query_runtime._bootstraps_signature



_runtime_optimization_cache_signature = odylith_context_engine_projection_query_runtime._runtime_optimization_cache_signature



_merge_search_results = odylith_context_engine_projection_query_runtime._merge_search_results



_repair_odylith_backend = odylith_context_engine_projection_query_runtime._repair_odylith_backend



_search_row_from_entity = odylith_context_engine_projection_query_runtime._search_row_from_entity



search_entities_payload = odylith_context_engine_projection_query_runtime.search_entities_payload



search_entities = odylith_context_engine_projection_query_runtime.search_entities



_miss_recovery_query_tokens = odylith_context_engine_projection_query_runtime._miss_recovery_query_tokens



_build_miss_recovery_queries = odylith_context_engine_projection_query_runtime._build_miss_recovery_queries



_repo_scan_inferred_kind = odylith_context_engine_projection_query_runtime._repo_scan_inferred_kind



_repo_scan_recovery_rows = odylith_context_engine_projection_query_runtime._repo_scan_recovery_rows



_recovery_search_payload = odylith_context_engine_projection_query_runtime._recovery_search_payload



_recovery_search_rows = odylith_context_engine_projection_query_runtime._recovery_search_rows



_recovery_note_like_kind = odylith_context_engine_projection_query_runtime._recovery_note_like_kind



_miss_recovery_projection_path_kind = odylith_context_engine_projection_query_runtime._miss_recovery_projection_path_kind



_miss_recovery_projection_terms = odylith_context_engine_projection_query_runtime._miss_recovery_projection_terms



_cached_miss_recovery_projection_index = odylith_context_engine_projection_query_runtime._cached_miss_recovery_projection_index



_projection_miss_recovery_rows = odylith_context_engine_projection_query_runtime._projection_miss_recovery_rows



_compact_miss_recovery_result = odylith_context_engine_projection_query_runtime._compact_miss_recovery_result



_compact_miss_recovery_for_packet = odylith_context_engine_projection_query_runtime._compact_miss_recovery_for_packet



_collect_retrieval_miss_recovery = odylith_context_engine_projection_query_runtime._collect_retrieval_miss_recovery



_normalize_entity_kind = odylith_context_engine_projection_query_runtime._normalize_entity_kind



_normalize_repo_token = odylith_context_engine_projection_query_runtime._normalize_repo_token



_resolve_moved_plan_token = odylith_context_engine_projection_query_runtime._resolve_moved_plan_token



_available_full_scan_roots = odylith_context_engine_projection_query_runtime._available_full_scan_roots



_full_scan_terms = odylith_context_engine_projection_query_runtime._full_scan_terms



_full_scan_reason_message = odylith_context_engine_projection_query_runtime._full_scan_reason_message



_full_scan_commands = odylith_context_engine_projection_query_runtime._full_scan_commands



_run_full_scan = odylith_context_engine_projection_query_runtime._run_full_scan



_full_scan_guidance = odylith_context_engine_projection_query_runtime._full_scan_guidance



_json_list = odylith_context_engine_projection_query_runtime._json_list



_json_dict = odylith_context_engine_projection_query_runtime._json_dict



_context_lookup_key = odylith_context_engine_projection_query_runtime._context_lookup_key



_context_lookup_aliases = odylith_context_engine_projection_query_runtime._context_lookup_aliases



_workstream_lookup_aliases = odylith_context_engine_projection_query_runtime._workstream_lookup_aliases



_component_lookup_aliases = odylith_context_engine_projection_query_runtime._component_lookup_aliases



_plan_lookup_aliases = odylith_context_engine_projection_query_runtime._plan_lookup_aliases



_parse_component_tokens = odylith_context_engine_projection_query_runtime._parse_component_tokens



_load_schema_contract_notes = odylith_context_engine_projection_query_runtime._load_schema_contract_notes



_load_make_target_notes = odylith_context_engine_projection_query_runtime._load_make_target_notes



_load_bug_learning_notes = odylith_context_engine_projection_query_runtime._load_bug_learning_notes



_load_engineering_notes = odylith_context_engine_projection_query_runtime._load_engineering_notes



_python_module_name = odylith_context_engine_projection_query_runtime._python_module_name



_collect_python_module_index = odylith_context_engine_projection_query_runtime._collect_python_module_index



_resolve_from_import = odylith_context_engine_projection_query_runtime._resolve_from_import



_extract_marker_names = odylith_context_engine_projection_query_runtime._extract_marker_names



_parse_python_artifact = odylith_context_engine_projection_query_runtime._parse_python_artifact



_module_command_to_path = odylith_context_engine_projection_query_runtime._module_command_to_path



_relation_for_target_path = odylith_context_engine_projection_query_runtime._relation_for_target_path



_load_make_artifacts = odylith_context_engine_projection_query_runtime._load_make_artifacts



_doc_source_paths = odylith_context_engine_projection_query_runtime._doc_source_paths



_load_doc_relationship_edges = odylith_context_engine_projection_query_runtime._load_doc_relationship_edges



_load_traceability_doc_code_edges_from_rows = odylith_context_engine_projection_query_runtime._load_traceability_doc_code_edges_from_rows



_load_traceability_doc_code_edges = odylith_context_engine_projection_query_runtime._load_traceability_doc_code_edges



_merge_edge_metadata_values = odylith_context_engine_projection_query_runtime._merge_edge_metadata_values



_merge_edge_metadata = odylith_context_engine_projection_query_runtime._merge_edge_metadata



_dedupe_code_edges = odylith_context_engine_projection_query_runtime._dedupe_code_edges



_load_code_graph = odylith_context_engine_projection_query_runtime._load_code_graph



_module_index_from_code_artifacts_rows = odylith_context_engine_projection_query_runtime._module_index_from_code_artifacts_rows



_module_index_from_code_artifacts = odylith_context_engine_projection_query_runtime._module_index_from_code_artifacts



_iter_test_functions = odylith_context_engine_projection_query_runtime._iter_test_functions



_path_mtime_iso = odylith_context_engine_projection_query_runtime._path_mtime_iso



_read_pytest_lastfailed = odylith_context_engine_projection_query_runtime._read_pytest_lastfailed



_candidate_test_report_paths = odylith_context_engine_projection_query_runtime._candidate_test_report_paths



_node_id_from_junit_case = odylith_context_engine_projection_query_runtime._node_id_from_junit_case



_read_junit_failures = odylith_context_engine_projection_query_runtime._read_junit_failures



_merge_test_history_rows = odylith_context_engine_projection_query_runtime._merge_test_history_rows



_load_test_history = odylith_context_engine_projection_query_runtime._load_test_history



_load_test_graph = odylith_context_engine_projection_query_runtime._load_test_graph


_summarize_entity = odylith_context_engine_projection_query_runtime._summarize_entity



_entity_from_row = odylith_context_engine_projection_query_runtime._entity_from_row



_entity_by_kind_id = odylith_context_engine_projection_query_runtime._entity_by_kind_id



_entity_by_path = odylith_context_engine_projection_query_runtime._entity_by_path



_unique_entity_by_path_alias = odylith_context_engine_projection_query_runtime._unique_entity_by_path_alias



_projection_exact_search_results = odylith_context_engine_projection_query_runtime._projection_exact_search_results



_repo_scan_candidate_search_results = odylith_context_engine_projection_query_runtime._repo_scan_candidate_search_results



_resolve_context_entity = odylith_context_engine_projection_query_runtime._resolve_context_entity



_relation_rows = odylith_context_engine_projection_query_runtime._relation_rows



_related_entities = odylith_context_engine_projection_query_runtime._related_entities



_recent_context_events = odylith_context_engine_projection_query_runtime._recent_context_events



_delivery_context_rows = odylith_context_engine_projection_query_runtime._delivery_context_rows



load_context_dossier = odylith_context_engine_projection_query_runtime.load_context_dossier



load_backlog_rows = odylith_context_engine_projection_query_runtime.load_backlog_rows



_markdown_section_bodies = odylith_context_engine_projection_query_runtime._markdown_section_bodies



load_backlog_list = odylith_context_engine_projection_query_runtime.load_backlog_list



def _runtime_backlog_detail_rows(
    *,
    repo_root: Path,
) -> dict[str, dict[str, Any]]:
    _refresh_runtime_helper_bindings()
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
    _refresh_runtime_helper_bindings()
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
    detail_level: str = "full",
) -> dict[str, Any] | None:
    _refresh_runtime_helper_bindings()
    root = Path(repo_root).resolve()
    token = str(workstream_id or "").strip().upper()
    normalized_detail_level = str(detail_level or "full").strip().lower() or "full"
    if not _WORKSTREAM_ID_RE.fullmatch(token):
        return None
    del runtime_mode
    if not _odylith_ablation_active(repo_root=root):
        try:
            runtime_detail = _runtime_backlog_detail(repo_root=root, workstream_id=token)
        except RuntimeError:
            runtime_detail = None
        if runtime_detail is not None:
            if normalized_detail_level == "grounding_light":
                return {
                    "idea_id": str(runtime_detail.get("idea_id", "")).strip().upper(),
                    "idea_file": str(runtime_detail.get("idea_file", "")).strip(),
                    "metadata": dict(runtime_detail.get("metadata", {}))
                    if isinstance(runtime_detail.get("metadata"), Mapping)
                    else {},
                    "promoted_to_plan": str(runtime_detail.get("promoted_to_plan", "")).strip(),
                }
            return runtime_detail
    spec = _load_idea_specs(repo_root=root).get(token)
    if spec is None:
        return None
    metadata = dict(spec.metadata)
    if str(metadata.get("promoted_to_plan", "")).strip():
        metadata["promoted_to_plan"] = _normalize_repo_token(str(metadata.get("promoted_to_plan", "")).strip(), repo_root=root)
    if normalized_detail_level == "grounding_light":
        return {
            "idea_id": token,
            "idea_file": str(spec.path.relative_to(root)) if spec.path.is_relative_to(root) else str(spec.path),
            "metadata": metadata,
            "promoted_to_plan": str(metadata.get("promoted_to_plan", "")).strip(),
        }
    raw_text = _raw_text(spec.path)
    return {
        "idea_id": token,
        "idea_file": str(spec.path.relative_to(root)) if spec.path.is_relative_to(root) else str(spec.path),
        "metadata": metadata,
        "sections": _markdown_section_bodies(raw_text),
        "search_body": raw_text,
        "promoted_to_plan": str(metadata.get("promoted_to_plan", "")).strip(),
    }



load_backlog_document = odylith_context_engine_projection_query_runtime.load_backlog_document



load_plan_rows = odylith_context_engine_projection_query_runtime.load_plan_rows



load_bug_rows = odylith_context_engine_projection_query_runtime.load_bug_rows



load_bug_snapshot = odylith_context_engine_projection_query_runtime.load_bug_snapshot



_component_entry_from_runtime_row = odylith_context_engine_projection_query_runtime._component_entry_from_runtime_row



load_component_index = odylith_context_engine_projection_query_runtime.load_component_index



load_registry_list = odylith_context_engine_projection_query_runtime.load_registry_list



load_component_registry_snapshot = odylith_context_engine_projection_query_runtime.load_component_registry_snapshot



load_registry_detail = odylith_context_engine_projection_query_runtime.load_registry_detail



def load_delivery_surface_payload(
    *,
    repo_root: Path,
    surface: str,
    runtime_mode: str = "auto",
    buckets: Sequence[str] | None = None,
    include_shell_snapshots: bool = True,
) -> dict[str, Any]:
    requested_buckets = {
        str(token or "").strip().lower()
        for token in (buckets or [])
        if str(token or "").strip()
    }
    root = Path(repo_root).resolve()
    surface_token = str(surface).strip().lower()
    odylith_switch = _odylith_switch_snapshot(repo_root=root)
    payload: dict[str, Any] = {}
    if _warm_runtime(repo_root=root, runtime_mode=runtime_mode, reason="delivery_surface"):
        connection = _connect(root)
        try:
            row = connection.execute(
                "SELECT payload_json FROM delivery_surfaces WHERE surface = ?",
                (surface_token,),
            ).fetchone()
            if row is not None:
                raw_payload = json.loads(str(row["payload_json"]))
                payload = dict(raw_payload) if isinstance(raw_payload, Mapping) else {}
        finally:
            connection.close()
    if not payload:
        try:
            artifact_payload = delivery_intelligence_engine.load_delivery_intelligence_artifact(repo_root=root)
        except Exception:
            artifact_payload = {}
        sliced = delivery_intelligence_engine.slice_delivery_intelligence_for_surface(
            payload=artifact_payload,
            surface=surface_token,
        )
        payload = dict(sliced) if isinstance(sliced, Mapping) else {}
    if requested_buckets:
        for bucket in (
            "summary",
            "case_queue",
            "systemic_brief",
            "surface_scope",
            "grid_scope",
            "components",
            "workstreams",
            "diagrams",
            "surfaces",
            "grid",
            "surface",
        ):
            if bucket in requested_buckets:
                continue
            payload.pop(bucket, None)
    if surface_token == "shell":
        payload["odylith_switch"] = odylith_switch
        payload["orchestration_adoption_snapshot"] = load_orchestration_adoption_snapshot(repo_root=root)
    if surface_token == "shell" and include_shell_snapshots:
        if not bool(odylith_switch.get("enabled", True)):
            payload.pop("memory_snapshot", None)
            payload.pop("optimization_snapshot", None)
            payload.pop("evaluation_snapshot", None)
            payload.pop("odylith_drawer_history", None)
            return payload
        optimization_snapshot = (
            dict(payload.get("optimization_snapshot", {}))
            if isinstance(payload.get("optimization_snapshot"), Mapping)
            else load_runtime_optimization_snapshot(repo_root=root)
        )
        evaluation_snapshot = (
            dict(payload.get("evaluation_snapshot", {}))
            if isinstance(payload.get("evaluation_snapshot"), Mapping)
            else load_runtime_evaluation_snapshot(repo_root=root)
        )
        payload["optimization_snapshot"] = optimization_snapshot
        payload["evaluation_snapshot"] = evaluation_snapshot
        if "memory_snapshot" not in payload:
            payload["memory_snapshot"] = load_runtime_memory_snapshot(
                repo_root=root,
                optimization_snapshot=optimization_snapshot,
                evaluation_snapshot=evaluation_snapshot,
            )
        payload["odylith_drawer_history"] = load_odylith_drawer_history(repo_root=root)
    return payload


_compact_bug_row_for_governance_packet = odylith_context_engine_hot_path_runtime._compact_bug_row_for_governance_packet



_compact_component_entry_for_governance_packet = odylith_context_engine_hot_path_runtime._compact_component_entry_for_governance_packet



_governance_surface_refs = odylith_context_engine_hot_path_runtime._governance_surface_refs



_governance_closeout_docs = odylith_context_engine_hot_path_runtime._governance_closeout_docs



_bounded_explicit_governance_closeout_docs = odylith_context_engine_hot_path_runtime._bounded_explicit_governance_closeout_docs



_governance_state_actions = odylith_context_engine_hot_path_runtime._governance_state_actions



_governance_requires_architecture_audit = odylith_context_engine_hot_path_runtime._governance_requires_architecture_audit



_governance_diagram_catalog_companions = odylith_context_engine_hot_path_runtime._governance_diagram_catalog_companions



_COMPANION_CONTEXT_RULES: tuple[dict[str, Any], ...] = (
    {
        "match_paths": ("src/odylith/install/agents.py",),
        "paths": (
            "odylith/AGENTS.md",
            "odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md",
            "odylith/skills/subagent-orchestrator/SKILL.md",
        ),
    },
    {
        "match_paths": (
            "src/odylith/runtime/surfaces/render_tooling_dashboard.py",
            "src/odylith/runtime/surfaces/compass_dashboard_shell.py",
            "tests/integration/runtime/test_surface_browser_smoke.py",
        ),
        "paths": (
            "odylith/index.html",
            "odylith/compass/compass.html",
        ),
    },
    {
        "match_prefixes": ("src/odylith/install/",),
        "paths": (
            "src/odylith/install/manager.py",
            "odylith/INSTALL_AND_UPGRADE_RUNBOOK.md",
            "odylith/registry/source/components/release/CURRENT_SPEC.md",
        ),
    },
    {
        "match_paths": (
            "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
            "src/odylith/runtime/evaluation/odylith_benchmark_graphs.py",
        ),
        "paths": (
            "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
            "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
            "README.md",
            "docs/benchmarks/README.md",
        ),
    },
    {
        "match_prefixes": ("src/odylith/runtime/surfaces/compass_",),
        "paths": (
            "odylith/registry/source/components/compass/CURRENT_SPEC.md",
            "odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md",
        ),
    },
    {
        "match_paths": ("odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd",),
        "paths": (
            "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
            "README.md",
            "odylith/MAINTAINER_RELEASE_RUNBOOK.md",
        ),
    },
)


_companion_context_paths_for_normalized_changed_paths = odylith_context_engine_hot_path_runtime._companion_context_paths_for_normalized_changed_paths



_companion_context_paths = odylith_context_engine_hot_path_runtime._companion_context_paths



_governance_hot_path_docs = odylith_context_engine_hot_path_runtime._governance_hot_path_docs



_governance_explicit_slice_grounded = odylith_context_engine_hot_path_runtime._governance_explicit_slice_grounded



_governance_can_skip_runtime_warmup = odylith_context_engine_hot_path_runtime._governance_can_skip_runtime_warmup



build_governance_slice = odylith_context_engine_hot_path_runtime.build_governance_slice



select_impacted_diagrams = odylith_context_engine_hot_path_runtime.select_impacted_diagrams



_path_touches_watch = odylith_context_engine_hot_path_runtime._path_touches_watch



_normalized_watch_path = odylith_context_engine_hot_path_runtime._normalized_watch_path



_architecture_rule_matches_path = odylith_context_engine_hot_path_runtime._architecture_rule_matches_path



_collect_topology_domains = odylith_context_engine_hot_path_runtime._collect_topology_domains



_component_matches_changed_path = odylith_context_engine_hot_path_runtime._component_matches_changed_path



_load_architecture_diagrams = odylith_context_engine_hot_path_runtime._load_architecture_diagrams



_collect_diagram_watch_gaps = odylith_context_engine_hot_path_runtime._collect_diagram_watch_gaps



_architecture_required_reads = odylith_context_engine_hot_path_runtime._architecture_required_reads



_dedupe_strings = odylith_context_engine_hot_path_runtime._dedupe_strings



_normalize_changed_path_list = odylith_context_engine_hot_path_runtime._normalize_changed_path_list



_engineering_note_summary = odylith_context_engine_hot_path_runtime._engineering_note_summary



_git_stdout = odylith_context_engine_hot_path_runtime._git_stdout



_git_ref_snapshot = odylith_context_engine_hot_path_runtime._git_ref_snapshot



_git_head_oid = odylith_context_engine_hot_path_runtime._git_head_oid



_git_branch_name = odylith_context_engine_hot_path_runtime._git_branch_name



_path_signal_profile = odylith_context_engine_hot_path_runtime._path_signal_profile



_path_match_type = odylith_context_engine_hot_path_runtime._path_match_type



_normalized_path_match_type = odylith_context_engine_hot_path_runtime._normalized_path_match_type



_split_csv_tokens = odylith_context_engine_hot_path_runtime._split_csv_tokens



_base_workstream_candidate = odylith_context_engine_hot_path_runtime._base_workstream_candidate



_shared_path_weight = odylith_context_engine_hot_path_runtime._shared_path_weight



_add_workstream_path_evidence = odylith_context_engine_hot_path_runtime._add_workstream_path_evidence



_add_workstream_component_evidence = odylith_context_engine_hot_path_runtime._add_workstream_component_evidence



_add_workstream_diagram_evidence = odylith_context_engine_hot_path_runtime._add_workstream_diagram_evidence



_summarize_workstream_evidence = odylith_context_engine_hot_path_runtime._summarize_workstream_evidence



_workstream_lineage_tokens = odylith_context_engine_hot_path_runtime._workstream_lineage_tokens



_workstream_candidates_share_evidence = odylith_context_engine_hot_path_runtime._workstream_candidates_share_evidence



_apply_workstream_successor_bonus = odylith_context_engine_hot_path_runtime._apply_workstream_successor_bonus



_finalize_workstream_candidates = odylith_context_engine_hot_path_runtime._finalize_workstream_candidates



_workstream_evidence_score = odylith_context_engine_hot_path_runtime._workstream_evidence_score



_workstream_signal_counter = odylith_context_engine_hot_path_runtime._workstream_signal_counter



_workstream_has_exact_path_signal = odylith_context_engine_hot_path_runtime._workstream_has_exact_path_signal



_workstream_has_path_signal = odylith_context_engine_hot_path_runtime._workstream_has_path_signal



_workstream_lineage_neighbor_ids = odylith_context_engine_hot_path_runtime._workstream_lineage_neighbor_ids



_rerank_workstream_candidates = odylith_context_engine_hot_path_runtime._rerank_workstream_candidates



_prune_low_precision_workstream_candidates = odylith_context_engine_hot_path_runtime._prune_low_precision_workstream_candidates



_path_profiles = odylith_context_engine_hot_path_runtime._path_profiles



_broad_shared_only_input = odylith_context_engine_hot_path_runtime._broad_shared_only_input



_limit_strings = odylith_context_engine_hot_path_runtime._limit_strings



_limit_mappings = odylith_context_engine_hot_path_runtime._limit_mappings



_truncate_text_for_packet = odylith_context_engine_hot_path_runtime._truncate_text_for_packet



_compact_component_row_for_packet = odylith_context_engine_hot_path_runtime._compact_component_row_for_packet



_compact_diagram_row_for_packet = odylith_context_engine_hot_path_runtime._compact_diagram_row_for_packet



_compact_test_row_for_packet = odylith_context_engine_hot_path_runtime._compact_test_row_for_packet



_compact_engineering_note_row_for_packet = odylith_context_engine_hot_path_runtime._compact_engineering_note_row_for_packet



_compact_engineering_notes = odylith_context_engine_hot_path_runtime._compact_engineering_notes



_compact_budget_meta_for_summary = odylith_context_engine_hot_path_runtime._compact_budget_meta_for_summary



_compact_packet_metrics_for_summary = odylith_context_engine_hot_path_runtime._compact_packet_metrics_for_summary



_compact_truncation_for_summary = odylith_context_engine_hot_path_runtime._compact_truncation_for_summary



_compact_runtime_timing_rows_for_packet = odylith_context_engine_hot_path_runtime._compact_runtime_timing_rows_for_packet



_impact_packet_state = odylith_context_engine_hot_path_runtime._impact_packet_state



_impact_budget_profile = odylith_context_engine_hot_path_runtime._impact_budget_profile



_component_grounded_selection_none = odylith_context_engine_hot_path_runtime._component_grounded_selection_none



_hot_path_can_stay_fail_closed_without_full_scan = odylith_context_engine_hot_path_runtime._hot_path_can_stay_fail_closed_without_full_scan



_impact_summary_payload = odylith_context_engine_hot_path_runtime._impact_summary_payload



_delivery_profile_hot_path = odylith_context_engine_hot_path_runtime._delivery_profile_hot_path



_elapsed_stage_ms = odylith_context_engine_hot_path_runtime._elapsed_stage_ms



_compact_stage_timings = odylith_context_engine_hot_path_runtime._compact_stage_timings



_normalize_family_hint = odylith_context_engine_hot_path_runtime._normalize_family_hint



_impact_family_profile = odylith_context_engine_hot_path_runtime._impact_family_profile



_HOT_PATH_AUTO_ESCALATION_CONSERVATIVE_FAMILIES = frozenset(
    {
        "architecture",
        "broad_shared_scope",
        "exact_path_ambiguity",
        "retrieval_miss_recovery",
    }
)
_HOT_PATH_AUTO_ESCALATION_ARCHITECTURE_FAMILIES = frozenset(
    {"architecture", "broad_shared_scope", "docs_code_closeout", "governed_surface_sync"}
)
_HOT_PATH_AUTO_SESSION_BRIEF_FAMILIES = frozenset(
    {
        "cross_file_feature",
        "docs_code_closeout",
        "explicit_workstream",
        "governed_surface_sync",
        "merge_heavy_change",
        "orchestration_feedback",
        "orchestration_intelligence",
        "validation_heavy_fix",
    }
)
_HOT_PATH_AUTO_ESCALATION_WRITE_FAMILIES = frozenset(
    {
        "cross_file_feature",
        "docs_code_closeout",
        "exact_anchor_recall",
        "explicit_workstream",
        "governed_surface_sync",
        "merge_heavy_change",
        "orchestration_feedback",
        "orchestration_intelligence",
        "validation_heavy_fix",
    }
)
_HOT_PATH_SUMMARY_ONLY_FALLBACK_FAMILIES = frozenset(
    {
        "broad_shared_scope",
        "dashboard_surface",
        "exact_path_ambiguity",
        "retrieval_miss_recovery",
    }
)


_hot_path_dashboard_surface_like = odylith_context_engine_hot_path_runtime._hot_path_dashboard_surface_like



_hot_path_routing_confidence_rank = odylith_context_engine_hot_path_runtime._hot_path_routing_confidence_rank



_hot_path_packet_rank = odylith_context_engine_hot_path_runtime._hot_path_packet_rank



_hot_path_auto_escalation_trigger = odylith_context_engine_hot_path_runtime._hot_path_auto_escalation_trigger



_hot_path_can_hold_local_narrowing_without_full_scan = odylith_context_engine_hot_path_runtime._hot_path_can_hold_local_narrowing_without_full_scan



_compact_hot_path_auto_escalation = odylith_context_engine_hot_path_runtime._compact_hot_path_auto_escalation


_hot_path_selected_validation_count = odylith_context_engine_hot_path_runtime._hot_path_selected_validation_count



_hot_path_route_ready = odylith_context_engine_hot_path_runtime._hot_path_route_ready



_hot_path_full_scan_recommended = odylith_context_engine_hot_path_runtime._hot_path_full_scan_recommended



_hot_path_full_scan_reason = odylith_context_engine_hot_path_runtime._hot_path_full_scan_reason



_hot_path_routing_confidence = odylith_context_engine_hot_path_runtime._hot_path_routing_confidence



_should_escalate_hot_path_to_session_brief = odylith_context_engine_hot_path_runtime._should_escalate_hot_path_to_session_brief



_fallback_scan_payload = odylith_context_engine_hot_path_runtime._fallback_scan_payload



_compact_hot_path_session_payload = odylith_context_engine_hot_path_runtime._compact_hot_path_session_payload



_compact_hot_path_workstream_context = odylith_context_engine_hot_path_runtime._compact_hot_path_workstream_context



_compact_hot_path_active_conflicts = odylith_context_engine_hot_path_runtime._compact_hot_path_active_conflicts



_hot_path_keep_architecture_audit = odylith_context_engine_hot_path_runtime._hot_path_keep_architecture_audit



_hot_path_workstream_selection = odylith_context_engine_hot_path_runtime._hot_path_workstream_selection



_compact_hot_path_workstream_selection = odylith_context_engine_hot_path_runtime._compact_hot_path_workstream_selection



_compact_hot_path_retrieval_plan = odylith_context_engine_hot_path_runtime._compact_hot_path_retrieval_plan



_compact_hot_path_packet_quality = odylith_context_engine_hot_path_runtime._compact_hot_path_packet_quality



_compact_hot_path_intent = odylith_context_engine_hot_path_runtime._compact_hot_path_intent



_hot_path_signal_score = odylith_context_engine_hot_path_runtime._hot_path_signal_score



_hot_path_synthesized_execution_profile = odylith_context_engine_hot_path_runtime._hot_path_synthesized_execution_profile



_hot_path_recomputed_readiness = odylith_context_engine_hot_path_runtime._hot_path_recomputed_readiness



_compact_hot_path_routing_handoff = odylith_context_engine_hot_path_runtime._compact_hot_path_routing_handoff



_compact_hot_path_route_execution_profile = odylith_context_engine_hot_path_runtime._compact_hot_path_route_execution_profile



_encode_hot_path_execution_profile = odylith_context_engine_hot_path_runtime._encode_hot_path_execution_profile



_decode_hot_path_execution_profile = odylith_context_engine_hot_path_runtime._decode_hot_path_execution_profile



_hot_path_execution_profile_runtime_fields = odylith_context_engine_hot_path_runtime._hot_path_execution_profile_runtime_fields



_compact_hot_path_payload_within_budget = odylith_context_engine_hot_path_runtime._compact_hot_path_payload_within_budget



_synthesized_hot_path_execution_profile_from_context_packet = odylith_context_engine_hot_path_runtime._synthesized_hot_path_execution_profile_from_context_packet



_governance_closeout_doc_count = odylith_context_engine_hot_path_runtime._governance_closeout_doc_count



_trim_common_hot_path_context_packet = odylith_context_engine_hot_path_runtime._trim_common_hot_path_context_packet



_compact_hot_path_narrowing_guidance = odylith_context_engine_hot_path_runtime._compact_hot_path_narrowing_guidance



_source_hot_path_within_budget = odylith_context_engine_hot_path_runtime._source_hot_path_within_budget



_fast_finalize_compact_hot_path_packet = odylith_context_engine_hot_path_runtime._fast_finalize_compact_hot_path_packet



_compact_hot_path_packet_metrics = odylith_context_engine_hot_path_runtime._compact_hot_path_packet_metrics



_drop_redundant_hot_path_routing_handoff = odylith_context_engine_hot_path_runtime._drop_redundant_hot_path_routing_handoff



_compact_hot_path_fallback_scan = odylith_context_engine_hot_path_runtime._compact_hot_path_fallback_scan



_compact_governance_validation_bundle_for_hot_path = odylith_context_engine_hot_path_runtime._compact_governance_validation_bundle_for_hot_path



_compact_hot_path_surface_reason_token = odylith_context_engine_hot_path_runtime._compact_hot_path_surface_reason_token



_compact_governance_obligations_for_hot_path = odylith_context_engine_hot_path_runtime._compact_governance_obligations_for_hot_path



_compact_governance_surface_refs_for_hot_path = odylith_context_engine_hot_path_runtime._compact_governance_surface_refs_for_hot_path



_compact_governance_signal_for_hot_path = odylith_context_engine_hot_path_runtime._compact_governance_signal_for_hot_path



_embedded_governance_signal = odylith_context_engine_hot_path_runtime._embedded_governance_signal



_hot_path_validation_bundle = odylith_context_engine_hot_path_runtime._hot_path_validation_bundle



_hot_path_governance_obligations = odylith_context_engine_hot_path_runtime._hot_path_governance_obligations



_validation_bundle_command_count = odylith_context_engine_hot_path_runtime._validation_bundle_command_count



_governance_obligation_count = odylith_context_engine_hot_path_runtime._governance_obligation_count



_compact_hot_path_runtime_packet = odylith_context_engine_hot_path_runtime._compact_hot_path_runtime_packet



_hot_path_payload_is_compact = odylith_context_engine_hot_path_runtime._hot_path_payload_is_compact



_update_compact_hot_path_runtime_packet = odylith_context_engine_hot_path_runtime._update_compact_hot_path_runtime_packet



_trim_route_ready_hot_path_prompt_payload = odylith_context_engine_hot_path_runtime._trim_route_ready_hot_path_prompt_payload



_compact_workstream_metadata_for_packet = odylith_context_engine_hot_path_runtime._compact_workstream_metadata_for_packet



_compact_workstream_evidence_for_packet = odylith_context_engine_hot_path_runtime._compact_workstream_evidence_for_packet



_compact_workstream_row_for_packet = odylith_context_engine_hot_path_runtime._compact_workstream_row_for_packet



_compact_workstream_reference_for_packet = odylith_context_engine_hot_path_runtime._compact_workstream_reference_for_packet



_compact_workstream_selection_for_packet = odylith_context_engine_hot_path_runtime._compact_workstream_selection_for_packet



_compact_bootstrap_workstream_selection = odylith_context_engine_hot_path_runtime._compact_bootstrap_workstream_selection



_compact_neighbor_row_for_packet = odylith_context_engine_hot_path_runtime._compact_neighbor_row_for_packet



_prioritized_neighbor_rows = odylith_context_engine_hot_path_runtime._prioritized_neighbor_rows



_compact_code_neighbors_for_packet = odylith_context_engine_hot_path_runtime._compact_code_neighbors_for_packet



_compact_architecture_audit_for_packet = odylith_context_engine_hot_path_runtime._compact_architecture_audit_for_packet



_compact_packet_level_architecture_audit = odylith_context_engine_hot_path_runtime._compact_packet_level_architecture_audit



_workstream_selection = odylith_context_engine_hot_path_runtime._workstream_selection



_bug_excerpt = odylith_context_engine_hot_path_runtime._bug_excerpt



_session_record_path = odylith_context_engine_hot_path_runtime._session_record_path



_bootstrap_record_path = odylith_context_engine_hot_path_runtime._bootstrap_record_path



_parse_iso_utc = odylith_context_engine_hot_path_runtime._parse_iso_utc



_normalize_claim_mode = odylith_context_engine_hot_path_runtime._normalize_claim_mode



_lease_expires_utc = odylith_context_engine_hot_path_runtime._lease_expires_utc



_is_session_expired = odylith_context_engine_hot_path_runtime._is_session_expired



_load_session_state = odylith_context_engine_hot_path_runtime._load_session_state



_resolve_changed_path_scope_context = odylith_context_engine_hot_path_runtime._resolve_changed_path_scope_context



_claim_sets = odylith_context_engine_hot_path_runtime._claim_sets



list_session_states = odylith_context_engine_hot_path_runtime.list_session_states



register_session_state = odylith_context_engine_hot_path_runtime.register_session_state



_collect_impacted_components = odylith_context_engine_hot_path_runtime._collect_impacted_components



def _collect_impacted_workstreams(
    connection: Any,
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    component_ids: Sequence[str],
    diagram_ids: Sequence[str],
    return_diagnostics: bool = False,
) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], dict[str, Any]]:
    _refresh_runtime_helper_bindings()
    return odylith_context_engine_hot_path_runtime._collect_impacted_workstreams(
        connection,
        repo_root=repo_root,
        changed_paths=changed_paths,
        component_ids=component_ids,
        diagram_ids=diagram_ids,
        return_diagnostics=return_diagnostics,
    )



_engineering_note_match = odylith_context_engine_hot_path_runtime._engineering_note_match



_collect_relevant_notes = odylith_context_engine_hot_path_runtime._collect_relevant_notes



_collect_relevant_bugs = odylith_context_engine_hot_path_runtime._collect_relevant_bugs



_collect_code_neighbors = odylith_context_engine_hot_path_runtime._collect_code_neighbors



def _collect_recommended_tests(
    connection: Any,
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    code_neighbors: Mapping[str, Sequence[Mapping[str, Any]]],
    limit: int,
) -> list[dict[str, Any]]:
    _refresh_runtime_helper_bindings()
    return odylith_context_engine_hot_path_runtime._collect_recommended_tests(
        connection,
        repo_root=repo_root,
        changed_paths=changed_paths,
        code_neighbors=code_neighbors,
        limit=limit,
    )



_collect_component_validation_commands = odylith_context_engine_hot_path_runtime._collect_component_validation_commands



_recommended_validation_commands = odylith_context_engine_hot_path_runtime._recommended_validation_commands



_is_governance_sync_command = odylith_context_engine_hot_path_runtime._is_governance_sync_command



_workstream_status_rank = odylith_context_engine_hot_path_runtime._workstream_status_rank



_workstream_rank_tuple = odylith_context_engine_hot_path_runtime._workstream_rank_tuple



_condense_delivery_scope = odylith_context_engine_hot_path_runtime._condense_delivery_scope



def _compact_context_dossier(
    dossier: Mapping[str, Any],
    *,
    relation_limit_per_kind: int = 4,
    event_limit: int = 5,
    delivery_limit: int = 3,
) -> dict[str, Any]:
    if not bool(dossier.get("resolved")):
        return {
            "resolved": False,
            "lookup": dict(dossier.get("lookup", {})) if isinstance(dossier.get("lookup"), Mapping) else {},
            "candidate_matches": dossier.get("matches", [])[:3] if isinstance(dossier.get("matches"), list) else [],
            "full_scan_recommended": bool(dossier.get("full_scan_recommended")),
            "full_scan_reason": str(dossier.get("full_scan_reason", "")).strip(),
            "fallback_scan": dict(dossier.get("fallback_scan", {}))
            if isinstance(dossier.get("fallback_scan"), Mapping)
            else {},
        }
    related = dossier.get("related_entities", {})
    entity_payload = dict(dossier.get("entity", {})) if isinstance(dossier.get("entity"), Mapping) else {}
    compact_entity = {
        key: value
        for key, value in {
            "entity_id": str(entity_payload.get("entity_id", "")).strip(),
            "title": str(entity_payload.get("title", "")).strip(),
            "status": str(entity_payload.get("status", "")).strip(),
            "priority": str(entity_payload.get("priority", "")).strip(),
            "owner": str(entity_payload.get("owner", "")).strip(),
            "workstream_type": str(entity_payload.get("workstream_type", "")).strip(),
            "plan_ref": str(entity_payload.get("plan_ref", "")).strip(),
            "diagram_id_count": len(entity_payload.get("related_diagram_ids", []))
            if isinstance(entity_payload.get("related_diagram_ids"), list)
            else 0,
            "child_count": len(entity_payload.get("workstream_children", []))
            if isinstance(entity_payload.get("workstream_children"), list)
            else 0,
            "dependency_count": len(entity_payload.get("workstream_depends_on", []))
            if isinstance(entity_payload.get("workstream_depends_on"), list)
            else 0,
        }.items()
        if value not in ("", [], {}, None, 0)
    }
    def _compact_related_row(row: Mapping[str, Any]) -> dict[str, Any]:
        compact = {
            key: value
            for key, value in {
                "entity_id": str(row.get("entity_id", "")).strip(),
                "title": str(row.get("title", "")).strip(),
                "status": str(row.get("status", "")).strip(),
            }.items()
            if value not in ("", [], {}, None)
        }
        path = str(row.get("path", "")).strip()
        entity_id = str(row.get("entity_id", "")).strip()
        if path and path != entity_id:
            compact["path"] = path
        return compact

    compact_related = {}
    if isinstance(related, Mapping):
        for kind, rows in related.items():
            if isinstance(rows, list):
                compact_rows = [
                    _compact_related_row(row)
                    for row in rows[: max(1, int(relation_limit_per_kind))]
                    if isinstance(row, Mapping)
                ]
                if compact_rows:
                    compact_related[str(kind)] = compact_rows
    events = dossier.get("recent_codex_events", [])
    compact_events = []
    if isinstance(events, list):
        for row in events[: max(1, int(event_limit))]:
            if not isinstance(row, Mapping):
                continue
            compact_events.append(
                {
                    "ts_iso": str(row.get("ts_iso", "")).strip(),
                    "kind": str(row.get("kind", "")).strip(),
                    "summary": str(row.get("summary", "")).strip(),
                    "workstreams": [str(token).strip() for token in row.get("workstreams", []) if str(token).strip()][:2]
                    if isinstance(row.get("workstreams"), list) and row.get("workstreams")
                    else [],
                    "components": [str(token).strip() for token in row.get("components", []) if str(token).strip()][:2]
                    if isinstance(row.get("components"), list) and row.get("components")
                    else [],
                }
            )
    scopes = dossier.get("delivery_scopes", [])
    compact_scopes = []
    if isinstance(scopes, list):
        compact_scopes = [_condense_delivery_scope(scope) for scope in scopes[: max(1, int(delivery_limit))] if isinstance(scope, Mapping)]
    relations = dossier.get("relations", [])
    relation_count = len(relations) if isinstance(relations, list) else 0
    return {
        "resolved": True,
        "entity": compact_entity,
        "lookup": dict(dossier.get("lookup", {})) if isinstance(dossier.get("lookup"), Mapping) else {},
        "related_entities": compact_related,
        "recent_codex_events": compact_events,
        "delivery_scope_summaries": compact_scopes,
        "relation_count": relation_count,
        "candidate_matches": dossier.get("matches", [])[:3] if isinstance(dossier.get("matches"), list) else [],
        "full_scan_recommended": bool(dossier.get("full_scan_recommended")),
        "full_scan_reason": str(dossier.get("full_scan_reason", "")).strip(),
    }


def compact_context_dossier_for_delivery(
    dossier: Mapping[str, Any],
    *,
    relation_limit_per_kind: int = 2,
    event_limit: int = 2,
    delivery_limit: int = 1,
) -> dict[str, Any]:
    return _compact_context_dossier(
        dossier,
        relation_limit_per_kind=max(1, int(relation_limit_per_kind)),
        event_limit=max(1, int(event_limit)),
        delivery_limit=max(1, int(delivery_limit)),
    )


def build_impact_report(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    use_working_tree: bool = False,
    working_tree_scope: str = "repo",
    session_id: str = "",
    claimed_paths: Sequence[str] = (),
    runtime_mode: str = "auto",
    test_limit: int = 12,
    intent: str = "",
    delivery_profile: str = "full",
    family_hint: str = "",
    workstream_hint: str = "",
    validation_command_hints: Sequence[str] = (),
    retain_hot_path_internal_context: bool = False,
    guidance_catalog_snapshot: Mapping[str, Any] | None = None,
    optimization_snapshot: Mapping[str, Any] | None = None,
    skip_runtime_warmup: bool = False,
    finalize_packet: bool = True,
) -> dict[str, Any]:
    _refresh_runtime_helper_bindings()
    return odylith_context_engine_grounding_runtime.build_impact_report(
        repo_root=repo_root,
        changed_paths=changed_paths,
        use_working_tree=use_working_tree,
        working_tree_scope=working_tree_scope,
        session_id=session_id,
        claimed_paths=claimed_paths,
        runtime_mode=runtime_mode,
        test_limit=test_limit,
        intent=intent,
        delivery_profile=delivery_profile,
        family_hint=family_hint,
        workstream_hint=workstream_hint,
        validation_command_hints=validation_command_hints,
        retain_hot_path_internal_context=retain_hot_path_internal_context,
        guidance_catalog_snapshot=guidance_catalog_snapshot,
        optimization_snapshot=optimization_snapshot,
        skip_runtime_warmup=skip_runtime_warmup,
        finalize_packet=finalize_packet,
    )


def build_architecture_audit(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    use_working_tree: bool = False,
    working_tree_scope: str = "repo",
    session_id: str = "",
    claimed_paths: Sequence[str] = (),
    runtime_mode: str = "auto",
    detail_level: str = "compact",
) -> dict[str, Any]:
    _refresh_runtime_helper_bindings()
    return odylith_context_engine_session_packet_runtime.build_architecture_audit(repo_root=repo_root, changed_paths=changed_paths, use_working_tree=use_working_tree, working_tree_scope=working_tree_scope, session_id=session_id, claimed_paths=claimed_paths, runtime_mode=runtime_mode, detail_level=detail_level)



def _session_conflicts(
    *,
    current_session_id: str,
    workstream: str,
    changed_paths: Sequence[str],
    generated_surfaces: Sequence[str],
    session_rows: Sequence[Mapping[str, Any]],
    claim_mode: str,
    current_branch_name: str,
    current_head_oid: str,
) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    for row in session_rows:
        session_id = str(row.get("session_id", "")).strip()
        if not session_id or session_id == current_session_id:
            continue
        other_paths = [str(token).strip() for token in row.get("claimed_paths", []) if str(token).strip()]
        shared_paths = sorted(
            {
                path_ref
                for path_ref in changed_paths
                for other in other_paths
                if _path_touches_watch(changed_path=path_ref, watch_path=other)
                or _path_touches_watch(changed_path=other, watch_path=path_ref)
            }
        )
        shared_surfaces = sorted(
            set(generated_surfaces).intersection(set(str(token).strip() for token in row.get("claimed_surfaces", [])))
        )
        other_workstreams = {
            str(token).strip().upper()
            for token in row.get("claimed_workstreams", [])
            if str(token).strip()
        } if isinstance(row.get("claimed_workstreams"), list) else set()
        same_workstream = bool(workstream and workstream in other_workstreams)
        if not (same_workstream or shared_paths or shared_surfaces):
            continue
        other_claim_mode = _normalize_claim_mode(str(row.get("claim_mode", "")).strip())
        exclusive_involved = "exclusive" in {claim_mode, other_claim_mode}
        other_branch_name = str(row.get("branch_name", "")).strip()
        other_head_oid = str(row.get("head_oid", "")).strip()
        repo_context_mismatch = bool(
            (current_head_oid and other_head_oid and current_head_oid != other_head_oid)
            or (current_branch_name and other_branch_name and current_branch_name != other_branch_name)
        )
        if shared_paths or shared_surfaces:
            severity = "high" if exclusive_involved else "medium"
        elif same_workstream:
            severity = "medium" if exclusive_involved else "low"
        else:
            severity = "low"
        if repo_context_mismatch:
            severity = {"high": "medium", "medium": "low", "low": "low"}.get(severity, severity)
        conflicts.append(
            {
                "session_id": session_id,
                "workstream": str(row.get("workstream", "")).strip().upper(),
                "intent": str(row.get("intent", "")).strip(),
                "claim_mode": other_claim_mode,
                "severity": severity,
                "shared_paths": shared_paths,
                "shared_surfaces": shared_surfaces,
                "same_workstream": same_workstream,
                "repo_context_mismatch": repo_context_mismatch,
                "branch_name": other_branch_name,
                "head_oid": other_head_oid,
                "lease_expires_utc": str(row.get("lease_expires_utc", "")).strip(),
                "updated_utc": str(row.get("updated_utc", "")).strip(),
            }
        )
    return conflicts


def _bootstrap_relevant_docs(
    docs: Sequence[str],
    *,
    guidance_rows: Sequence[Mapping[str, Any]],
    limit: int,
) -> list[str]:
    guidance_refs: set[str] = set()
    for row in guidance_rows:
        if not isinstance(row, Mapping):
            continue
        for key in ("canonical_source", "chunk_path"):
            token = str(row.get(key, "")).strip()
            if token:
                guidance_refs.add(token)
        actionability = dict(row.get("actionability", {})) if isinstance(row.get("actionability"), Mapping) else {}
        read_path = str(actionability.get("read_path", "")).strip()
        if read_path:
            guidance_refs.add(read_path)
    scored: list[tuple[tuple[int, int], str]] = []
    for index, raw_doc in enumerate(docs):
        doc = str(raw_doc).strip()
        if not doc:
            continue
        score = 0
        if is_component_spec_path(doc, repo_root=Path.cwd()):
            score += 120
        if doc.startswith("docs/runbooks/"):
            score += 95
        if doc.startswith("agents-guidelines/") and not doc.startswith("agents-guidelines/indexable/"):
            score += 28
        if doc not in guidance_refs:
            score += 42
        if doc in guidance_refs:
            score -= 36
        if doc.startswith("agents-guidelines/indexable/"):
            score -= 24
        scored.append(((-score, index), doc))
    scored.sort(key=lambda item: item[0])
    return _dedupe_strings([doc for _score, doc in scored])[: max(1, int(limit))]


def build_session_brief(
    *,
    repo_root: Path,
    changed_paths: Sequence[str] = (),
    use_working_tree: bool = False,
    working_tree_scope: str = "session",
    runtime_mode: str = "auto",
    session_id: str = "",
    workstream: str = "",
    generated_surfaces: Sequence[str] = (),
    intent: str = "",
    claim_mode: str = "shared",
    claimed_paths: Sequence[str] = (),
    lease_seconds: int = 15 * 60,
    delivery_profile: str = "full",
    family_hint: str = "",
    validation_command_hints: Sequence[str] = (),
    impact_override: Mapping[str, Any] | None = None,
    retain_impact_internal_context: bool | None = None,
    skip_impact_runtime_warmup: bool = False,
) -> dict[str, Any]:
    _refresh_runtime_helper_bindings()
    return odylith_context_engine_session_packet_runtime.build_session_brief(repo_root=repo_root, changed_paths=changed_paths, use_working_tree=use_working_tree, working_tree_scope=working_tree_scope, runtime_mode=runtime_mode, session_id=session_id, workstream=workstream, generated_surfaces=generated_surfaces, intent=intent, claim_mode=claim_mode, claimed_paths=claimed_paths, lease_seconds=lease_seconds, delivery_profile=delivery_profile, family_hint=family_hint, validation_command_hints=validation_command_hints, impact_override=impact_override, retain_impact_internal_context=retain_impact_internal_context, skip_impact_runtime_warmup=skip_impact_runtime_warmup)



def build_session_bootstrap(
    *,
    repo_root: Path,
    changed_paths: Sequence[str] = (),
    use_working_tree: bool = False,
    working_tree_scope: str = "session",
    runtime_mode: str = "auto",
    session_id: str = "",
    workstream: str = "",
    generated_surfaces: Sequence[str] = (),
    intent: str = "",
    claim_mode: str = "shared",
    claimed_paths: Sequence[str] = (),
    lease_seconds: int = 15 * 60,
    doc_limit: int = 8,
    command_limit: int = 10,
    test_limit: int = 8,
    delivery_profile: str = "full",
    family_hint: str = "",
    validation_command_hints: Sequence[str] = (),
    retain_impact_internal_context: bool | None = None,
    skip_impact_runtime_warmup: bool = False,
) -> dict[str, Any]:
    _refresh_runtime_helper_bindings()
    return odylith_context_engine_session_packet_runtime.build_session_bootstrap(repo_root=repo_root, changed_paths=changed_paths, use_working_tree=use_working_tree, working_tree_scope=working_tree_scope, runtime_mode=runtime_mode, session_id=session_id, workstream=workstream, generated_surfaces=generated_surfaces, intent=intent, claim_mode=claim_mode, claimed_paths=claimed_paths, lease_seconds=lease_seconds, doc_limit=doc_limit, command_limit=command_limit, test_limit=test_limit, delivery_profile=delivery_profile, family_hint=family_hint, validation_command_hints=validation_command_hints, retain_impact_internal_context=retain_impact_internal_context, skip_impact_runtime_warmup=skip_impact_runtime_warmup)



def build_adaptive_coding_packet(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    use_working_tree: bool = False,
    working_tree_scope: str = "repo",
    session_id: str = "",
    claimed_paths: Sequence[str] = (),
    runtime_mode: str = "auto",
    intent: str = "",
    family_hint: str = "",
    workstream_hint: str = "",
    validation_command_hints: Sequence[str] = (),
) -> dict[str, Any]:
    _refresh_runtime_helper_bindings()
    return odylith_context_engine_session_packet_runtime.build_adaptive_coding_packet(repo_root=repo_root, changed_paths=changed_paths, use_working_tree=use_working_tree, working_tree_scope=working_tree_scope, session_id=session_id, claimed_paths=claimed_paths, runtime_mode=runtime_mode, intent=intent, family_hint=family_hint, workstream_hint=workstream_hint, validation_command_hints=validation_command_hints)



def _local_runtime_execution_summary(
    *,
    repo_root: Path,
    command: str,
    changed_paths: Sequence[str],
    session_id: str,
    claimed_paths: Sequence[str],
    working_tree_scope: str,
) -> dict[str, Any]:
    scope = runtime_request_namespace(
        repo_root=repo_root,
        command=command,
        changed_paths=changed_paths,
        session_id=session_id,
        claimed_paths=claimed_paths,
        working_tree_scope=working_tree_scope,
    )
    return {
        "source": "local_process",
        "transport": "local",
        "workspace_daemon_reused": False,
        "workspace_key": str(scope.get("workspace_key", "")).strip(),
        "request_namespace": str(scope.get("request_namespace", "")).strip(),
        "session_namespaced": bool(scope.get("session_namespaced")),
        "session_namespace": str(scope.get("session_namespace", "")).strip(),
        "working_tree_scope": str(scope.get("working_tree_scope", "")).strip(),
        "session_id_present": bool(scope.get("session_id_present")),
        "claim_path_count": int(scope.get("claim_path_count", 0) or 0),
        "changed_path_count": int(scope.get("changed_path_count", 0) or 0),
        "mixed_local_fallback": False,
    }


def build_adaptive_coding_packet_reusing_daemon(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    use_working_tree: bool = False,
    working_tree_scope: str = "repo",
    session_id: str = "",
    claimed_paths: Sequence[str] = (),
    runtime_mode: str = "auto",
    intent: str = "",
    family_hint: str = "",
    workstream_hint: str = "",
    validation_command_hints: Sequence[str] = (),
) -> dict[str, Any]:
    _refresh_runtime_helper_bindings()
    return odylith_context_engine_session_packet_runtime.build_adaptive_coding_packet_reusing_daemon(repo_root=repo_root, changed_paths=changed_paths, use_working_tree=use_working_tree, working_tree_scope=working_tree_scope, session_id=session_id, claimed_paths=claimed_paths, runtime_mode=runtime_mode, intent=intent, family_hint=family_hint, workstream_hint=workstream_hint, validation_command_hints=validation_command_hints)


def _refresh_runtime_helper_bindings() -> None:
    odylith_context_engine_session_packet_runtime.bind(globals())
    odylith_context_engine_memory_snapshot_runtime.bind(globals())
    odylith_context_engine_projection_query_runtime.bind(globals())
    odylith_context_engine_hot_path_runtime.bind(globals())
    odylith_context_engine_runtime_learning_runtime.bind(globals())


_refresh_runtime_helper_bindings()

__all__ = [
    "ENGINEERING_NOTE_KINDS",
    "SCHEMA_VERSION",
    "append_runtime_event",
    "bootstraps_root",
    "build_adaptive_coding_packet",
    "build_adaptive_coding_packet_reusing_daemon",
    "build_architecture_audit",
    "build_governance_slice",
    "build_impact_report",
    "build_session_bootstrap",
    "build_session_brief",
    "compact_context_dossier_for_delivery",
    "daemon_usage_path",
    "ensure_state_js_probe_asset",
    "events_path",
    "git_fsmonitor_status",
    "list_session_states",
    "load_context_dossier",
    "load_backlog_detail",
    "load_backlog_document",
    "load_backlog_list",
    "load_backlog_rows",
    "load_bug_rows",
    "load_bug_snapshot",
    "bootstrap_git_fsmonitor",
    "load_component_index",
    "load_component_registry_snapshot",
    "load_delivery_surface_payload",
    "load_orchestration_adoption_snapshot",
    "load_plan_rows",
    "load_registry_detail",
    "load_registry_list",
    "load_runtime_memory_snapshot",
    "load_runtime_evaluation_snapshot",
    "load_runtime_timing_summary",
    "load_runtime_optimization_snapshot",
    "optimization_evaluation_corpus_path",
    "pid_path",
    "proof_surfaces_path",
    "preferred_watcher_backend",
    "persist_orchestration_adoption_snapshot",
    "prime_reasoning_projection_cache",
    "projection_snapshot_path",
    "projection_input_fingerprint",
    "prune_runtime_records",
    "read_runtime_daemon_usage",
    "record_runtime_timing",
    "record_runtime_daemon_usage",
    "register_session_state",
    "read_runtime_state",
    "request_runtime_daemon",
    "runtime_root",
    "runtime_daemon_transport",
    "runtime_request_namespace",
    "runtime_request_namespace_from_payload",
    "search_entities",
    "search_entities_payload",
    "select_impacted_diagrams",
    "sessions_root",
    "socket_path",
    "state_path",
    "stop_path",
    "watcher_backend_report",
    "watch_targets",
    "warm_projections",
    "write_runtime_state",
]
