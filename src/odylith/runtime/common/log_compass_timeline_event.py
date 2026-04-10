"""Append local decision/implementation timeline events for Compass audits.

This command writes local-only newline-delimited JSON records that are consumed
by the installed Compass renderer and rendered inside the Compass timeline.

Design notes:
- Stream file is append-only and lives under `odylith/compass/runtime/` by default.
- Entries are intentionally concise and operator-readable.
- Validation is fail-closed for required fields and workstream ID format.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.common import host_runtime as host_runtime_contract
from odylith.runtime.governance import component_registry_intelligence as component_registry
from odylith.runtime.governance.proof_state.contract import DEPLOYMENT_TRUTH_FIELDS
from odylith.runtime.governance.proof_state.contract import PROOF_STATUSES
from odylith.runtime.governance.proof_state.contract import WORK_CATEGORIES


_WORKSTREAM_RE = re.compile(r"^B-\d{3,}$")
_KIND_CHOICES: tuple[str, str, str, str] = ("decision", "implementation", "statement", "update")
_KIND_CANONICAL: dict[str, str] = {
    "decision": "decision",
    "implementation": "implementation",
    "statement": "statement",
    "update": "statement",
}
_BOUNDARY_CHOICES: tuple[str, str, str] = ("", "start", "end")
_SOFT_REGISTRY_DIAGNOSTIC_PREFIXES: tuple[str, ...] = (
    "missing catalog path for component inference:",
    "suppressed unresolved idea component tokens:",
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith compass log",
        description="Append a Compass timeline stream event for host-aware audit visibility.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument(
        "--stream",
        default=agent_runtime_contract.AGENT_STREAM_PATH,
        help="Output JSONL stream path (local runtime artifact).",
    )
    parser.add_argument("--kind", required=True, choices=_KIND_CHOICES, help="Event kind.")
    parser.add_argument("--summary", required=True, help="Crisp event summary sentence.")
    parser.add_argument(
        "--workstream",
        action="append",
        default=[],
        help="Linked workstream ID (`B-xxx`). Repeatable.",
    )
    parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        help="Linked artifact path (repeatable).",
    )
    parser.add_argument(
        "--component",
        action="append",
        default=[],
        help="Linked component id/alias (repeatable).",
    )
    parser.add_argument(
        "--manifest",
        default=component_registry.DEFAULT_MANIFEST_PATH,
        help="Component registry manifest path.",
    )
    parser.add_argument(
        "--catalog",
        default=component_registry.DEFAULT_CATALOG_PATH,
        help="Mermaid catalog path for component inference.",
    )
    parser.add_argument(
        "--ideas-root",
        default=component_registry.DEFAULT_IDEAS_ROOT,
        help="Backlog ideas root for impacted-component inference.",
    )
    detected_capabilities = host_runtime_contract.resolve_host_capabilities()
    default_author = str(detected_capabilities.get("model_family", "")).strip() or "agent"
    default_source = str(detected_capabilities.get("host_family", "")).strip() or "agent"
    parser.add_argument("--author", default=default_author, help="Author label in timeline metadata.")
    parser.add_argument("--source", default=default_source, help="Source label in timeline metadata.")
    parser.add_argument(
        "--session-id",
        default="",
        help="Optional session identifier. Defaults to CODEX_THREAD_ID when present.",
    )
    parser.add_argument(
        "--transaction-id",
        default="",
        help="Optional prompt transaction identifier for grouping related events.",
    )
    parser.add_argument(
        "--transaction-seq",
        type=int,
        default=None,
        help="Optional in-transaction sequence number for deterministic ordering.",
    )
    parser.add_argument(
        "--context",
        default="",
        help="Optional prompt/execution context text surfaced in transaction cards.",
    )
    parser.add_argument(
        "--headline-hint",
        default="",
        help="Optional concise transaction headline hint (used when valid and non-generic).",
    )
    parser.add_argument(
        "--transaction-boundary",
        default="",
        choices=_BOUNDARY_CHOICES,
        help="Optional boundary marker (`start` or `end`) for prompt transaction framing.",
    )
    parser.add_argument(
        "--ts-iso",
        default="",
        help="Optional ISO timestamp (defaults to now in local timezone).",
    )
    parser.add_argument("--proof-lane", default="", help="Optional proof lane id for live-proof tracking.")
    parser.add_argument("--proof-fingerprint", default="", help="Optional live failure fingerprint for this event.")
    parser.add_argument("--proof-phase", default="", help="Optional proof frontier or phase label.")
    parser.add_argument("--evidence-tier", default="", help="Optional evidence tier for this event.")
    parser.add_argument("--proof-status", default="", choices=("", *PROOF_STATUSES), help="Optional proof status carried by this event.")
    parser.add_argument("--work-category", default="", choices=("", *WORK_CATEGORIES), help="Optional proof work category for this event.")
    parser.add_argument("--local-head", default="", help="Optional deployment-truth local HEAD.")
    parser.add_argument("--pushed-head", default="", help="Optional deployment-truth pushed branch HEAD.")
    parser.add_argument("--published-source-commit", default="", help="Optional deployment-truth published source commit.")
    parser.add_argument("--runner-fingerprint", default="", help="Optional deployment-truth runner fingerprint.")
    parser.add_argument("--last-live-failing-commit", default="", help="Optional deployment-truth last live failing commit.")
    return parser.parse_args(argv)


def _resolve(repo_root: Path, token: str) -> Path:
    path = Path(str(token or "").strip())
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _normalize_summary(raw: str) -> str:
    return " ".join(str(raw or "").split()).strip()


def _normalize_workstreams(values: Sequence[str]) -> tuple[list[str], list[str]]:
    normalized: list[str] = []
    errors: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = str(raw or "").strip().upper()
        if not token:
            continue
        if not _WORKSTREAM_RE.fullmatch(token):
            errors.append(token)
            continue
        if token in seen:
            continue
        seen.add(token)
        normalized.append(token)
    return normalized, errors


def _normalize_artifact_token(*, repo_root: Path, raw: str) -> str:
    token = str(raw or "").strip()
    if not token:
        return ""
    path = Path(token)
    if path.is_absolute():
        try:
            rel = path.resolve().relative_to(repo_root.resolve())
            return rel.as_posix()
        except ValueError:
            return path.resolve().as_posix()
    if token.startswith("./"):
        return token[2:]
    return token


def _normalize_artifacts(*, repo_root: Path, values: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = _normalize_artifact_token(repo_root=repo_root, raw=raw)
        if not token or token in seen:
            continue
        seen.add(token)
        normalized.append(token)
    return normalized


def _normalize_components(
    *,
    values: Sequence[str],
    alias_to_component: dict[str, str],
) -> tuple[list[str], list[str]]:
    normalized: list[str] = []
    errors: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = component_registry.normalize_component_id(str(raw or ""))
        if not token:
            raw_token = str(raw or "").strip()
            if raw_token:
                errors.append(raw_token)
            continue
        resolved = alias_to_component.get(token)
        if not resolved:
            errors.append(token)
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        normalized.append(resolved)
    return normalized, errors


def _parse_ts(raw: str) -> dt.datetime | None:
    token = str(raw or "").strip()
    if not token:
        return dt.datetime.now().astimezone()
    if token.endswith("Z"):
        token = f"{token[:-1]}+00:00"
    try:
        value = dt.datetime.fromisoformat(token)
    except ValueError:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.datetime.now().astimezone().tzinfo)
    return value.astimezone()


def _canonical_kind(raw: str) -> str | None:
    token = str(raw or "").strip().lower()
    if not token:
        return None
    return _KIND_CANONICAL.get(token)


def append_event(
    *,
    repo_root: Path,
    stream_path: Path,
    kind: str,
    summary: str,
    workstream_values: Sequence[str],
    artifact_values: Sequence[str],
    component_values: Sequence[str],
    author: str = "codex",
    source: str = "codex",
    manifest_path: Path | None = None,
    catalog_path: Path | None = None,
    ideas_root: Path | None = None,
    session_id: str = "",
    transaction_id: str = "",
    transaction_seq: int | None = None,
    context: str = "",
    headline_hint: str = "",
    transaction_boundary: str = "",
    ts_iso: str = "",
    proof_lane: str = "",
    proof_fingerprint: str = "",
    proof_phase: str = "",
    evidence_tier: str = "",
    proof_status: str = "",
    work_category: str = "",
    deployment_truth: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    canonical_kind = _canonical_kind(kind)
    if not canonical_kind:
        choices = ", ".join(_KIND_CHOICES)
        raise ValueError(f"kind must be one of: {choices}")

    normalized_summary = _normalize_summary(summary)
    if not normalized_summary:
        raise ValueError("summary must be non-empty")

    workstreams, ws_errors = _normalize_workstreams(list(workstream_values))
    if ws_errors:
        raise ValueError(f"invalid workstream ids: {', '.join(ws_errors)}")

    ts = _parse_ts(ts_iso)
    if ts is None:
        raise ValueError("ts-iso must be a valid ISO timestamp")
    if transaction_seq is not None and transaction_seq < 0:
        raise ValueError("transaction-seq must be >= 0")

    boundary = str(transaction_boundary or "").strip().lower()
    if boundary not in _BOUNDARY_CHOICES:
        choices = ", ".join(token or "\"\"" for token in _BOUNDARY_CHOICES)
        raise ValueError(f"transaction-boundary must be one of: {choices}")

    artifacts = _normalize_artifacts(repo_root=repo_root, values=list(artifact_values))
    manifest = manifest_path or _resolve(repo_root, component_registry.DEFAULT_MANIFEST_PATH)
    catalog = catalog_path or _resolve(repo_root, component_registry.DEFAULT_CATALOG_PATH)
    ideas = ideas_root or _resolve(repo_root, component_registry.DEFAULT_IDEAS_ROOT)
    components, alias_to_component, diagnostics = component_registry.build_component_index(
        repo_root=repo_root,
        manifest_path=manifest,
        catalog_path=catalog,
        ideas_root=ideas,
    )
    hard_diagnostics = []
    for row in diagnostics:
        token = str(row or "")
        if any(token.startswith(prefix) for prefix in _SOFT_REGISTRY_DIAGNOSTIC_PREFIXES):
            continue
        hard_diagnostics.append(token)
    if hard_diagnostics:
        raise ValueError(f"component registry index invalid: {hard_diagnostics[0]}")

    explicit_components, component_errors = _normalize_components(
        values=list(component_values),
        alias_to_component=alias_to_component,
    )
    if component_errors:
        raise ValueError(f"invalid component ids/aliases: {', '.join(component_errors)}")

    mapped_components, _confidence = component_registry.infer_event_component_mapping(
        summary=normalized_summary,
        workstreams=workstreams,
        artifacts=artifacts,
        explicit_components=explicit_components,
        components=components,
        alias_to_component=alias_to_component,
    )
    meaningful = component_registry.is_meaningful_event(
        workstreams=workstreams,
        artifacts=artifacts,
        summary=normalized_summary,
        kind=canonical_kind,
    )
    if meaningful and not mapped_components:
        raise ValueError(
            "meaningful event requires at least one component mapping; "
            "pass --component or use artifacts/workstreams mapped in component_registry.v1.json"
        )

    resolved_session = _normalize_summary(session_id) or _normalize_summary(os.getenv("CODEX_THREAD_ID", ""))
    resolved_transaction = _normalize_summary(transaction_id)
    resolved_context = _normalize_summary(context)
    resolved_headline_hint = _normalize_summary(headline_hint)
    resolved_proof_lane = _normalize_summary(proof_lane)
    resolved_proof_fingerprint = _normalize_summary(proof_fingerprint)
    resolved_proof_phase = _normalize_summary(proof_phase)
    resolved_evidence_tier = _normalize_summary(evidence_tier)
    resolved_proof_status = _normalize_summary(proof_status)
    resolved_work_category = _normalize_summary(work_category)
    payload: dict[str, object] = {
        "version": "v1",
        "kind": canonical_kind,
        "summary": normalized_summary,
        "ts_iso": ts.isoformat(timespec="seconds"),
        "author": _normalize_summary(author),
        "source": _normalize_summary(source),
        "workstreams": workstreams,
        "artifacts": artifacts,
    }
    if mapped_components:
        payload["components"] = mapped_components
    if resolved_session:
        payload["session_id"] = resolved_session
    if resolved_transaction:
        payload["transaction_id"] = resolved_transaction
    if transaction_seq is not None:
        payload["transaction_seq"] = int(transaction_seq)
    if resolved_context:
        payload["context"] = resolved_context
    if resolved_headline_hint:
        payload["headline_hint"] = resolved_headline_hint
    if boundary:
        payload["transaction_boundary"] = boundary
    if resolved_proof_lane:
        payload["proof_lane"] = resolved_proof_lane
    if resolved_proof_fingerprint:
        payload["proof_fingerprint"] = resolved_proof_fingerprint
    if resolved_proof_phase:
        payload["proof_phase"] = resolved_proof_phase
    if resolved_evidence_tier:
        payload["evidence_tier"] = resolved_evidence_tier
    if resolved_proof_status:
        payload["proof_status"] = resolved_proof_status
    if resolved_work_category:
        payload["work_category"] = resolved_work_category
    raw_truth = dict(deployment_truth) if isinstance(deployment_truth, Mapping) else {}
    normalized_truth = {
        field: _normalize_summary(raw_truth.get(field))
        for field in DEPLOYMENT_TRUTH_FIELDS
    }
    if any(value for value in normalized_truth.values()):
        payload["deployment_truth"] = {
            key: value
            for key, value in normalized_truth.items()
            if value
        }

    line = json.dumps(payload, sort_keys=True)
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    with stream_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{line}\n")

    return payload


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    stream_path = _resolve(repo_root, str(args.stream))
    manifest_token = str(args.manifest).strip()
    manifest_path = (
        component_registry.default_manifest_path(repo_root=repo_root)
        if manifest_token == component_registry.DEFAULT_MANIFEST_PATH
        else _resolve(repo_root, manifest_token)
    )
    try:
        payload = append_event(
            repo_root=repo_root,
            stream_path=stream_path,
            kind=str(args.kind),
            summary=str(args.summary),
            workstream_values=list(args.workstream),
            artifact_values=list(args.artifact),
            component_values=list(args.component),
            author=str(args.author),
            source=str(args.source),
            manifest_path=manifest_path,
            catalog_path=_resolve(repo_root, str(args.catalog)),
            ideas_root=_resolve(repo_root, str(args.ideas_root)),
            session_id=str(args.session_id),
            transaction_id=str(args.transaction_id),
            transaction_seq=args.transaction_seq,
            context=str(args.context),
            headline_hint=str(args.headline_hint),
            transaction_boundary=str(args.transaction_boundary),
            ts_iso=str(args.ts_iso),
            proof_lane=str(args.proof_lane),
            proof_fingerprint=str(args.proof_fingerprint),
            proof_phase=str(args.proof_phase),
            evidence_tier=str(args.evidence_tier),
            proof_status=str(args.proof_status),
            work_category=str(args.work_category),
            deployment_truth={
                "local_head": str(args.local_head),
                "pushed_head": str(args.pushed_head),
                "published_source_commit": str(args.published_source_commit),
                "runner_fingerprint": str(args.runner_fingerprint),
                "last_live_failing_commit": str(args.last_live_failing_commit),
            },
        )
    except ValueError as exc:
        print("compass timeline stream append FAILED")
        print(f"- {exc}")
        return 2

    print("compass timeline stream append passed")
    print(f"- stream: {stream_path}")
    print(f"- kind: {payload['kind']}")
    print(f"- workstreams: {len(payload.get('workstreams', []))}")
    print(f"- artifacts: {len(payload.get('artifacts', []))}")
    print(f"- components: {len(payload.get('components', []))}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
