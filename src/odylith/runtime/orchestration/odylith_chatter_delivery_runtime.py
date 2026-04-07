from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.governance import operator_readout


_DELIVERY_ARTIFACT_RELATIVE_PATH = Path("odylith/runtime/delivery_intelligence.v4.json")
_DELIVERY_SIGNAL_CACHE: dict[str, tuple[int, dict[str, Any]]] = {}


def _normalize_string(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_token(value: Any) -> str:
    return _normalize_string(value).lower().replace("-", "_").replace(" ", "_")


def _dedupe_strings(values: Sequence[str]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = _normalize_string(raw)
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return _dedupe_strings([str(token) for token in value])
    token = _normalize_string(value)
    return [token] if token else []


def _normalize_surface_list(value: Any) -> list[str]:
    rows: list[str] = []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            if isinstance(item, Mapping):
                rows.append(str(item.get("surface", "")))
            else:
                rows.append(str(item))
    return _dedupe_strings(rows)


def _normalize_proof_refs(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [
        operator_readout.normalize_proof_ref(item)
        for item in value
        if isinstance(item, Mapping)
    ][:4]


def _normalize_operator_readout(raw_readout: Any) -> dict[str, Any]:
    readout = dict(raw_readout) if isinstance(raw_readout, Mapping) else {}
    return {
        "primary_scenario": _normalize_string(readout.get("primary_scenario")) or "clear_path",
        "severity": _normalize_string(readout.get("severity")) or "clear",
        "issue": _normalize_string(readout.get("issue")),
        "action": _normalize_string(readout.get("action")),
        "why_hidden": _normalize_string(readout.get("why_hidden")),
        "requires_approval": bool(readout.get("requires_approval")),
        "proof_refs": _normalize_proof_refs(readout.get("proof_refs")),
    }


def _normalize_scope_signal(raw_scope: Any) -> dict[str, Any]:
    if not isinstance(raw_scope, Mapping):
        return {}
    return {
        "scope_type": _normalize_token(raw_scope.get("scope_type")),
        "scope_id": _normalize_string(raw_scope.get("scope_id")),
        "scope_key": _normalize_string(raw_scope.get("scope_key")),
        "scope_label": (
            _normalize_string(raw_scope.get("scope_label"))
            or _normalize_string(raw_scope.get("scope_id"))
            or _normalize_string(raw_scope.get("scope_key"))
        ),
        "case_refs": _normalize_string_list(raw_scope.get("case_refs")),
        "surfaces": _normalize_surface_list(raw_scope.get("surfaces") or raw_scope.get("surface_contributions")),
        "operator_readout": _normalize_operator_readout(raw_scope.get("operator_readout")),
        "evidence_refs": _normalize_proof_refs(raw_scope.get("evidence_refs")),
    }


def _normalize_case_queue_entry(raw_case: Any) -> dict[str, Any]:
    if not isinstance(raw_case, Mapping):
        return {}
    return {
        "id": _normalize_string(raw_case.get("id")),
        "scope_key": _normalize_string(raw_case.get("scope_key")),
        "headline": _normalize_string(raw_case.get("headline")),
        "brief": _normalize_string(raw_case.get("brief")),
        "systemic_theme_tags": _normalize_string_list(raw_case.get("systemic_theme_tags")),
        "proof_refs": _normalize_proof_refs(raw_case.get("proof_refs")),
    }


def _normalize_systemic_brief(raw_brief: Any) -> dict[str, Any]:
    if not isinstance(raw_brief, Mapping):
        return {}
    return {
        "headline": _normalize_string(raw_brief.get("headline")),
        "summary": _normalize_string(raw_brief.get("summary")),
        "latent_causes": _normalize_string_list(raw_brief.get("latent_causes")),
        "systemic_theme_tags": _normalize_string_list(raw_brief.get("systemic_theme_tags")),
        "proof_refs": _normalize_proof_refs(raw_brief.get("proof_refs")),
    }


def _normalize_tribunal_context_payload(raw_context: Any, *, source: str) -> dict[str, Any]:
    if not isinstance(raw_context, Mapping):
        return {}
    scope_signals = []
    raw_scope_signals = raw_context.get("scope_signals")
    if isinstance(raw_scope_signals, Sequence) and not isinstance(raw_scope_signals, (str, bytes, bytearray)):
        for item in raw_scope_signals:
            row = _normalize_scope_signal(item)
            if row:
                scope_signals.append(row)
    case_queue = []
    raw_case_queue = raw_context.get("case_queue")
    if isinstance(raw_case_queue, Sequence) and not isinstance(raw_case_queue, (str, bytes, bytearray)):
        for item in raw_case_queue:
            row = _normalize_case_queue_entry(item)
            if row:
                case_queue.append(row)
    systemic_brief = _normalize_systemic_brief(raw_context.get("systemic_brief"))
    if not scope_signals and not case_queue and not systemic_brief:
        return {}
    return {
        "scope_signals": scope_signals[:3],
        "case_queue": case_queue[:3],
        "systemic_brief": systemic_brief,
        "source": source,
    }


def delivery_signal_snapshot(repo_root: Path | None) -> dict[str, Any]:
    if repo_root is None:
        return {}
    artifact_path = Path(repo_root).resolve() / _DELIVERY_ARTIFACT_RELATIVE_PATH
    try:
        mtime_ns = artifact_path.stat().st_mtime_ns
    except OSError:
        return {}
    cache_key = str(artifact_path)
    cached = _DELIVERY_SIGNAL_CACHE.get(cache_key)
    if cached is not None and cached[0] == mtime_ns:
        return cached[1]
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    scopes_by_id: dict[tuple[str, str], dict[str, Any]] = {}
    case_queue_by_scope: dict[str, dict[str, Any]] = {}
    if isinstance(payload, Mapping):
        for raw_scope in payload.get("scopes", []) if isinstance(payload.get("scopes"), list) else []:
            if not isinstance(raw_scope, Mapping):
                continue
            scope = _normalize_scope_signal(
                {
                    "scope_type": raw_scope.get("scope_type"),
                    "scope_id": raw_scope.get("scope_id"),
                    "scope_key": raw_scope.get("scope_key"),
                    "scope_label": raw_scope.get("scope_label"),
                    "case_refs": raw_scope.get("case_refs"),
                    "surface_contributions": raw_scope.get("surface_contributions"),
                    "operator_readout": raw_scope.get("operator_readout"),
                    "evidence_refs": (
                        raw_scope.get("evidence_bundle", {}).get("evidence_refs")
                        if isinstance(raw_scope.get("evidence_bundle"), Mapping)
                        else []
                    ),
                }
            )
            scope_type = _normalize_token(scope.get("scope_type"))
            scope_id = _normalize_string(scope.get("scope_id"))
            if scope_type not in {"workstream", "component", "diagram"} or not scope_id:
                continue
            scopes_by_id[(scope_type, scope_id)] = scope
        for raw_case in payload.get("case_queue", []) if isinstance(payload.get("case_queue"), list) else []:
            case_row = _normalize_case_queue_entry(raw_case)
            scope_key = _normalize_string(case_row.get("scope_key"))
            if not scope_key:
                continue
            case_queue_by_scope[scope_key] = case_row
    snapshot = {
        "scopes_by_id": scopes_by_id,
        "case_queue_by_scope": case_queue_by_scope,
        "systemic_brief": _normalize_systemic_brief(payload.get("systemic_brief")) if isinstance(payload, Mapping) else {},
    }
    _DELIVERY_SIGNAL_CACHE[cache_key] = (mtime_ns, snapshot)
    return snapshot


def tribunal_context(
    *,
    context_payload: Mapping[str, Any],
    repo_root: Path | None,
    anchor_artifacts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    for key in ("tribunal_delivery_signals", "tribunal_signals"):
        explicit = context_payload.get(key)
        normalized = _normalize_tribunal_context_payload(
            explicit,
            source=_normalize_string(getattr(explicit, "get", lambda *_args, **_kwargs: "")("source")) or f"context_payload:{key}",
        )
        if normalized:
            return normalized
    if repo_root is None or not anchor_artifacts:
        return {}
    snapshot = delivery_signal_snapshot(repo_root)
    if not snapshot:
        return {}
    scopes: list[dict[str, Any]] = []
    case_queue: list[dict[str, Any]] = []
    for row in anchor_artifacts:
        key = (str(row.get("kind", "")).strip(), str(row.get("id", "")).strip())
        scope = dict(snapshot.get("scopes_by_id", {}).get(key, {}))
        if not scope:
            continue
        scopes.append(scope)
        case_row = dict(snapshot.get("case_queue_by_scope", {}).get(str(scope.get("scope_key", "")), {}))
        if case_row:
            case_queue.append(case_row)
    if not scopes:
        return {}
    return _normalize_tribunal_context_payload(
        {
            "scope_signals": scopes[:3],
            "case_queue": case_queue[:3],
            "systemic_brief": dict(snapshot.get("systemic_brief", {})),
        },
        source="precomputed_delivery_artifact",
    )
