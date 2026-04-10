"""Backend-agnostic multi-actor reasoning for Odylith cases.

Tribunal is the non-UI reasoning engine that sits beneath Odylith. It does
not render dashboards directly. Instead, it:
- turns delivery-intelligence scopes into decision dossiers;
- runs specialized actors over the same grounded case;
- adjudicates disagreement instead of flattening it into one template;
- emits one short maintainer brief plus an approval-gated correction packet.

The engine keeps a deterministic baseline, but selected cases can now be
refined by an external provider when the provider can cite grounded evidence.
Provider output is advisory, validated against named evidence, and falls back
cleanly to the deterministic path when it cannot be trusted.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.surfaces import dashboard_shell_links
from odylith.runtime.governance import operator_readout
from odylith.runtime.governance import proof_state
from odylith.runtime.reasoning import remediator
from odylith.runtime.governance import workstream_inference

DEFAULT_REASONING_PATH = "odylith/runtime/odylith-reasoning.v4.json"
_ACTOR_POLICY_VERSION = "tribunal-v6"
_CASE_FORM_HEADLINES: dict[str, str] = {
    "ownership_challenge": "Reopen vs successor attribution",
    "trust_downgrade": "Evaluator semantics are still moving",
    "false_coherence": "Cross-surface ownership is not proven yet",
    "semantic_review": "Classify the latest delta before changing the call",
    "executable_fix": "A bounded correction can ship now",
    "insufficient_evidence": "Evidence is still too weak to move history",
    "policy_breach": "A policy boundary still blocks the call",
}
_PROOF_ROUTE_SURFACES: frozenset[str] = frozenset({"atlas", "compass", "radar", "registry", "shell"})
_PROVIDER_FIELD_NAMES: tuple[str, ...] = (
    "leading_explanation",
    "strongest_rival",
    "risk_if_wrong",
    "discriminating_next_check",
    "maintainer_brief",
)
_PROVIDER_ARTIFACT_LABELS: dict[str, str] = {
    "semantic_diff_candidates": "the cited semantic-diff candidate",
    "owned_artifacts": "the cited owned artifact",
    "changed_artifacts": "the cited changed artifact",
}
_PROVIDER_ARTIFACT_LABEL_PRIORITY: dict[str, int] = {
    "semantic_diff_candidates": 0,
    "owned_artifacts": 1,
    "changed_artifacts": 2,
}
_EVALUATOR_CORE_ARTIFACT_PREFIXES: tuple[str, ...] = (
    "src/odylith/runtime/reasoning/tribunal_engine.py",
    "src/odylith/runtime/reasoning/odylith_reasoning.py",
    "src/odylith/runtime/governance/sync_workstream_artifacts.py",
    "src/odylith/runtime/governance/delivery_intelligence_engine.py",
    "src/odylith/runtime/reasoning/remediator.py",
)
_ACTOR_ORDER: tuple[str, ...] = (
    "observer",
    "ownership_resolver",
    "causal_analyst",
    "policy_judge",
    "normative_judge",
    "adversary",
    "counterfactual_analyst",
    "gap_analyst",
    "risk_analyst",
    "prescriber",
)


def _series(values: Sequence[str], *, limit: int = 3) -> str:
    rows = [str(token).strip() for token in values if str(token).strip()][:limit]
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]} and {rows[1]}"
    return f"{', '.join(rows[:-1])}, and {rows[-1]}"

def _readout(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return dict(snapshot.get("operator_readout", {})) if isinstance(snapshot.get("operator_readout"), Mapping) else {}


def _candidate_score_band_key(snapshot: Mapping[str, Any]) -> tuple[int, int, int, int, int, int]:
    readout = _readout(snapshot)
    scores = snapshot.get("scores", {}) if isinstance(snapshot.get("scores"), Mapping) else {}
    scope_type = str(snapshot.get("scope_type", "")).strip().lower()
    scope_type_rank = {"workstream": 0, "component": 1, "diagram": 2}.get(scope_type, 9)
    return (
        scope_type_rank,
        operator_readout.scenario_priority(str(readout.get("primary_scenario", ""))),
        operator_readout.severity_rank(str(readout.get("severity", ""))),
        -int(scores.get("decision_debt", 0) or 0),
        -int(scores.get("governance_lag", 0) or 0),
        -int(scores.get("blast_radius_severity", 0) or 0),
    )


def _candidate_sort_key(snapshot: Mapping[str, Any]) -> tuple[int, int, int, int, int, int, str, str]:
    band = _candidate_score_band_key(snapshot)
    scope_id = str(snapshot.get("scope_id", "")).strip().lower()
    scope_key = str(snapshot.get("scope_key", "")).strip().lower()
    return (*band, scope_id, scope_key)


def _eligible_candidate_snapshots(
    payload: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    scopes = payload.get("scopes", []) if isinstance(payload.get("scopes"), list) else []
    candidates: list[dict[str, Any]] = []
    excluded = {
        "unsupported_scope_type": 0,
        "not_live_actionable": 0,
        "clear_path": 0,
    }
    for snapshot in scopes:
        if not isinstance(snapshot, Mapping):
            continue
        if str(snapshot.get("scope_type", "")).strip() not in {"workstream", "component", "diagram"}:
            excluded["unsupported_scope_type"] += 1
            continue
        diagnostics = snapshot.get("diagnostics", {}) if isinstance(snapshot.get("diagnostics"), Mapping) else {}
        if not bool(diagnostics.get("live_actionable", False)):
            excluded["not_live_actionable"] += 1
            continue
        readout = _readout(snapshot)
        if str(readout.get("primary_scenario", "clear_path")).strip() == "clear_path":
            excluded["clear_path"] += 1
            continue
        candidates.append(dict(snapshot))
    return candidates, excluded


def _candidate_selection(payload: Mapping[str, Any], *, scope_cap: int) -> dict[str, Any]:
    candidates, excluded = _eligible_candidate_snapshots(payload)
    ordered = sorted(candidates, key=_candidate_sort_key)
    all_scopes = payload.get("scopes", []) if isinstance(payload.get("scopes"), list) else []
    total_scope_count = len(all_scopes)
    total_by_type = Counter(
        str(snapshot.get("scope_type", "")).strip() or "unknown"
        for snapshot in all_scopes
        if isinstance(snapshot, Mapping)
    )
    band_counts = Counter(_candidate_score_band_key(snapshot) for snapshot in ordered)
    focused: list[dict[str, Any]] = []
    focused_keys: set[str] = set()
    selection_meta: dict[str, dict[str, Any]] = {}
    covered_scenarios: set[str] = set()

    def _selection_metrics(snapshot: Mapping[str, Any]) -> dict[str, Any]:
        readout = _readout(snapshot)
        diagnostics = snapshot.get("diagnostics", {}) if isinstance(snapshot.get("diagnostics"), Mapping) else {}
        scores = snapshot.get("scores", {}) if isinstance(snapshot.get("scores"), Mapping) else {}
        return {
            "scope_type": str(snapshot.get("scope_type", "")).strip(),
            "scenario": str(readout.get("primary_scenario", "")).strip() or "clear_path",
            "severity": str(readout.get("severity", "")).strip() or "clear",
            "decision_debt": int(scores.get("decision_debt", 0) or 0),
            "governance_lag": int(scores.get("governance_lag", 0) or 0),
            "blast_radius_severity": int(scores.get("blast_radius_severity", 0) or 0),
            "live_reason": str(diagnostics.get("live_reason", "")).strip(),
        }

    def _selection_reason(snapshot: Mapping[str, Any], *, slot: str) -> str:
        metrics = _selection_metrics(snapshot)
        scenario = str(metrics.get("scenario", "clear_path")).replace("_", " ").strip() or "clear path"
        scope_type = str(metrics.get("scope_type", "scope")).strip() or "scope"
        live_reason = str(metrics.get("live_reason", "")).strip()
        band_size = int(band_counts.get(_candidate_score_band_key(snapshot), 0) or 0)
        if slot == "scenario_coverage":
            base = f"Selected as the highest-ranked {scenario} {scope_type} so the queue covers a distinct case class before same-scenario priority fill."
        elif slot == "visible_overflow":
            base = (
                "Still eligible, but hidden by Odylith's default focused inbox because AI effort is currently limited "
                "to a smaller top-ranked focus set."
            )
        else:
            base = "Selected on the priority-fill pass after scenario coverage because it still outranks the remaining eligible cases."
        if live_reason:
            base = f"{base} Live rationale: {live_reason}"
        if band_size > 1:
            base = (
                f"{base} It sits in a {band_size}-scope score band tied on scenario, severity, decision debt, governance lag, and blast radius, "
                "so Tribunal uses explicit scope-id order as the final stable tie-break."
            )
        return base

    for snapshot in ordered:
        if len(focused) >= scope_cap:
            break
        scenario = str(_readout(snapshot).get("primary_scenario", "")).strip() or "clear_path"
        scope_key = str(snapshot.get("scope_key", "")).strip()
        if not scope_key or scenario in covered_scenarios:
            continue
        focused.append(snapshot)
        focused_keys.add(scope_key)
        covered_scenarios.add(scenario)
        selection_meta[scope_key] = {
            "slot": "scenario_coverage",
            "reason": _selection_reason(snapshot, slot="scenario_coverage"),
            "metrics": _selection_metrics(snapshot),
            "score_band_size": int(band_counts.get(_candidate_score_band_key(snapshot), 0) or 0),
            "provider_focus": True,
        }

    for snapshot in ordered:
        if len(focused) >= scope_cap:
            break
        scope_key = str(snapshot.get("scope_key", "")).strip()
        if not scope_key or scope_key in focused_keys:
            continue
        focused.append(snapshot)
        focused_keys.add(scope_key)
        selection_meta[scope_key] = {
            "slot": "priority_fill",
            "reason": _selection_reason(snapshot, slot="priority_fill"),
            "metrics": _selection_metrics(snapshot),
            "score_band_size": int(band_counts.get(_candidate_score_band_key(snapshot), 0) or 0),
            "provider_focus": True,
        }

    for snapshot in ordered:
        scope_key = str(snapshot.get("scope_key", "")).strip()
        if not scope_key or scope_key in selection_meta:
            continue
        selection_meta[scope_key] = {
            "slot": "visible_overflow",
            "reason": _selection_reason(snapshot, slot="visible_overflow"),
            "metrics": _selection_metrics(snapshot),
            "score_band_size": int(band_counts.get(_candidate_score_band_key(snapshot), 0) or 0),
            "provider_focus": False,
        }

    eligible_by_type = Counter(str(snapshot.get("scope_type", "")).strip() for snapshot in ordered)
    eligible_by_scenario = Counter(str(_readout(snapshot).get("primary_scenario", "")).strip() or "clear_path" for snapshot in ordered)
    eligible_by_status = Counter(
        str(
            (
                snapshot.get("diagnostics", {})
                if isinstance(snapshot.get("diagnostics"), Mapping)
                else {}
            ).get("status", "")
        ).strip()
        or "unknown"
        for snapshot in ordered
    )
    focused_by_scenario = Counter(
        str(selection_meta[str(snapshot.get("scope_key", "")).strip()].get("metrics", {}).get("scenario", "")).strip() or "clear_path"
        for snapshot in focused
        if str(snapshot.get("scope_key", "")).strip() in selection_meta
    )
    return {
        "ordered_candidates": ordered,
        "visible_scope_keys": [
            str(snapshot.get("scope_key", "")).strip()
            for snapshot in ordered
            if str(snapshot.get("scope_key", "")).strip()
        ],
        "selected_scope_keys": [
            str(snapshot.get("scope_key", "")).strip()
            for snapshot in focused
            if str(snapshot.get("scope_key", "")).strip()
        ],
        "provider_focus_scope_keys": [
            str(snapshot.get("scope_key", "")).strip()
            for snapshot in focused
            if str(snapshot.get("scope_key", "")).strip()
        ],
        "selection_meta": selection_meta,
        "summary": {
            "total_scope_count": total_scope_count,
            "eligible_scope_count": len(ordered),
            "shown_scope_count": len(ordered),
            "scope_cap": scope_cap,
            "provider_focus_cap": scope_cap,
            "provider_focus_count": len(focused),
            "outside_focus_count": max(0, len(ordered) - len(focused)),
            "truncated": False,
            "truncated_count": 0,
            "total_by_type": dict(sorted(total_by_type.items())),
            "eligible_by_type": dict(sorted(eligible_by_type.items())),
            "eligible_by_status": dict(sorted(eligible_by_status.items())),
            "eligible_by_scenario": dict(sorted(eligible_by_scenario.items())),
            "selected_by_scenario": dict(sorted(focused_by_scenario.items())),
            "provider_focus_by_scenario": dict(sorted(focused_by_scenario.items())),
            "excluded_counts": excluded,
            "selection_strategy": {
                "eligibility_gate": "scope_type in {workstream, component, diagram} and diagnostics.live_actionable and primary_scenario != clear_path",
                "visible_queue": "all eligible cases remain available in ranked order, while the UI may default to a smaller focused inbox",
                "diversity_pass": "provider focus takes one highest-ranked case per scenario before same-scenario priority fill",
                "ranking": [
                    "scope_type",
                    "scenario_priority",
                    "severity",
                    "decision_debt",
                    "governance_lag",
                    "blast_radius_severity",
                    "scope_id",
                ],
                "stable_tie_break": "scope_id then scope_key",
            },
        },
    }


def _candidate_scope_keys(payload: Mapping[str, Any], *, scope_cap: int) -> list[str]:
    return list(_candidate_selection(payload, scope_cap=scope_cap).get("selected_scope_keys", []))


def _normalize_strings(values: Any, *, limit: int | None = None) -> list[str]:
    rows: list[str] = []
    if not isinstance(values, list):
        return rows
    for raw in values:
        token = str(raw or "").strip()
        if not token:
            continue
        rows.append(token)
        if limit is not None and len(rows) >= limit:
            break
    return rows


def _normalize_refs(values: Any, *, require_surface: bool, limit: int = 8) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not isinstance(values, list):
        return rows
    seen: set[tuple[str, str, str, str, str]] = set()
    for raw in values:
        if not isinstance(raw, Mapping):
            continue
        normalized = operator_readout.normalize_proof_ref(raw)
        kind = str(normalized.get("kind", "")).strip()
        value = str(normalized.get("value", "")).strip()
        label = str(normalized.get("label", "")).strip()
        surface = str(normalized.get("surface", "")).strip().lower()
        href = str(normalized.get("href", "")).strip()
        if not kind or not value or not label:
            continue
        if require_surface and not href and surface not in _PROOF_ROUTE_SURFACES:
            continue
        key = (
            surface,
            str(normalized.get("anchor", "")).strip(),
            kind,
            value,
            href,
        )
        if key in seen:
            continue
        seen.add(key)
        rows.append(normalized)
        if len(rows) >= limit:
            break
    return rows


def _proof_route_quality(routes: Sequence[Mapping[str, Any]]) -> str:
    if not routes:
        return "missing"
    if all(
        str(row.get("href", "")).strip()
        or str(row.get("surface", "")).strip().lower() in _PROOF_ROUTE_SURFACES
        for row in routes
        if isinstance(row, Mapping)
    ):
        return "deep-linkable"
    return "partial"


def _semantic_diff_candidates(
    *,
    owned_artifacts: Sequence[str],
    changed_artifacts: Sequence[str],
    limit: int = 4,
) -> list[str]:
    owned = [str(token).strip() for token in owned_artifacts if str(token).strip()]
    changed = [str(token).strip() for token in changed_artifacts if str(token).strip()]
    if not owned:
        return []
    owned_by_lower = {token.lower(): token for token in owned}
    changed_names = {Path(token).name.lower() for token in changed}
    rows: list[str] = []
    for token in changed:
        matched = owned_by_lower.get(token.lower())
        if matched and matched not in rows:
            rows.append(matched)
        if len(rows) >= limit:
            return rows
    for token in owned:
        if Path(token).name.lower() in changed_names and token not in rows:
            rows.append(token)
        if len(rows) >= limit:
            return rows
    if rows:
        return rows[:limit]
    return owned[:limit]


def _evidence_gaps(*, observations: Mapping[str, Any]) -> list[str]:
    gaps: list[str] = []
    if not str(observations.get("latest_explicit_ts_iso", "")).strip():
        gaps.append("No explicit checkpoint timestamp is attached to the case.")
    if not _normalize_strings(observations.get("owned_artifacts"), limit=1):
        gaps.append("No named owned artifacts back the current ownership read.")
    if not bool(observations.get("semantic_diff_ready", False)):
        gaps.append("Semantic diff review is not grounded by named owned artifacts plus a fresh change candidate.")
    if str(observations.get("proof_route_quality", "")).strip() != "deep-linkable":
        gaps.append("No deep-linkable proof route is available for direct operator inspection.")
    return gaps


def _sentence(value: str) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    return token if token.endswith((".", "!", "?")) else f"{token}."


def _date_label(value: str) -> str:
    token = str(value or "").strip()
    if len(token) >= 10 and token[4] == "-" and token[7] == "-":
        return token[:10]
    return token


def _artifact_label(value: str) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    if ":" in token and not token.startswith(("/", "./", "../")):
        suffix = token.split(":", 1)[1].strip()
        return suffix or token
    name = Path(token).name.strip()
    return name or token


def _focus_artifact(observations: Mapping[str, Any]) -> str:
    for key in ("semantic_diff_candidates", "owned_artifacts", "changed_artifacts"):
        values = _normalize_strings(observations.get(key), limit=4)
        if values:
            return _artifact_label(values[0])
    return "latest delta"


def _surface_phrase(observations: Mapping[str, Any], *, limit: int = 4) -> str:
    surfaces = _normalize_strings(observations.get("linked_surfaces"), limit=limit)
    return _series(surfaces, limit=limit) if surfaces else "the linked surfaces"


def _checkpoint_phrase(observations: Mapping[str, Any]) -> str:
    latest = _date_label(str(observations.get("latest_activity_ts_iso", "")).strip())
    explicit = _date_label(str(observations.get("latest_explicit_ts_iso", "")).strip())
    if latest and explicit:
        return f"after the {explicit} checkpoint on {latest}"
    if explicit:
        return f"after the {explicit} checkpoint"
    if latest:
        return f"in the {latest} activity"
    return "in the latest activity"


def _provider_contract_signature(*, config: Any | None, provider: Any | None) -> dict[str, Any]:
    return {
        "mode": str(getattr(config, "mode", "")).strip() if config is not None else "",
        "provider": str(getattr(config, "provider", "")).strip() if config is not None else "",
        "model": str(getattr(config, "model", "")).strip() if config is not None else "",
        "base_url": str(getattr(config, "base_url", "")).strip() if config is not None else "",
        "codex_bin": str(getattr(config, "codex_bin", "")).strip() if config is not None else "",
        "codex_reasoning_effort": str(getattr(config, "codex_reasoning_effort", "")).strip() if config is not None else "",
        "api_key_present": bool(str(getattr(config, "api_key", "")).strip()) if config is not None else False,
        "provider_active": provider is not None,
        "provider_class": provider.__class__.__name__ if provider is not None else "",
    }


def _evidence_fingerprint(
    snapshot: Mapping[str, Any],
    posture: Mapping[str, Any],
    *,
    provider_contract: Mapping[str, Any] | None = None,
) -> str:
    evidence = snapshot.get("evidence_context", {}) if isinstance(snapshot.get("evidence_context"), Mapping) else {}
    diagnostics = snapshot.get("diagnostics", {}) if isinstance(snapshot.get("diagnostics"), Mapping) else {}
    readout = _readout(snapshot)
    payload = {
        "scope_key": str(snapshot.get("scope_key", "")).strip(),
        "scope_type": str(snapshot.get("scope_type", "")).strip(),
        "scope_id": str(snapshot.get("scope_id", "")).strip(),
        "scope_label": str(snapshot.get("scope_label", "")).strip(),
        "posture_mode": str(snapshot.get("posture_mode", "")).strip(),
        "trajectory": str(snapshot.get("trajectory", "")).strip(),
        "confidence": str(snapshot.get("confidence", "")).strip(),
        "scores": dict(snapshot.get("scores", {})) if isinstance(snapshot.get("scores"), Mapping) else {},
        "evidence_context": {
            "latest_event_ts_iso": str(evidence.get("latest_event_ts_iso", "")).strip(),
            "latest_explicit_ts_iso": str(evidence.get("latest_explicit_ts_iso", "")).strip(),
            "linked_workstreams": list(evidence.get("linked_workstreams", [])),
            "linked_components": list(evidence.get("linked_components", [])),
            "linked_diagrams": list(evidence.get("linked_diagrams", [])),
            "linked_surfaces": list(evidence.get("linked_surfaces", [])),
            "code_references": list(evidence.get("code_references", [])),
            "changed_artifacts": list(evidence.get("changed_artifacts", [])),
        },
        "operator_readout": readout,
        "proof_state": dict(snapshot.get("proof_state", {})) if isinstance(snapshot.get("proof_state"), Mapping) else {},
        "proof_state_resolution": dict(snapshot.get("proof_state_resolution", {}))
        if isinstance(snapshot.get("proof_state_resolution"), Mapping)
        else {},
        "claim_guard": dict(snapshot.get("claim_guard", {})) if isinstance(snapshot.get("claim_guard"), Mapping) else {},
        "evidence_refs": _normalize_refs(snapshot.get("evidence_refs", []), require_surface=False, limit=8),
        "proof_routes": _normalize_refs(readout.get("proof_refs", []), require_surface=True, limit=8),
        "diagnostics": {
            "status": str(diagnostics.get("status", "")).strip(),
            "live_reason": str(diagnostics.get("live_reason", "")).strip(),
            "reasoning_state": str(diagnostics.get("reasoning_state", "")).strip(),
            "reasoning_confidence": diagnostics.get("reasoning_confidence", 0),
        },
        "policy_breaches": [
            {
                "id": str(row.get("id", "")).strip(),
                "severity": str(row.get("severity", "")).strip(),
                "summary": str(row.get("summary", "")).strip(),
            }
            for row in posture.get("policy", {}).get("breaches", [])  # type: ignore[union-attr]
            if isinstance(row, Mapping)
        ],
        "clearance": dict(posture.get("clearance", {})) if isinstance(posture.get("clearance"), Mapping) else {},
        "reasoning": dict(posture.get("reasoning", {})) if isinstance(posture.get("reasoning"), Mapping) else {},
        "provider_contract": dict(provider_contract) if isinstance(provider_contract, Mapping) else {},
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _classify_change_mix(paths: Sequence[str]) -> str:
    lowered = [
        workstream_inference.normalize_repo_token(str(path or "")).strip().lower()
        for path in paths
        if str(path or "").strip()
    ]
    if not lowered:
        return "unknown"
    if all(workstream_inference.is_generated_or_global_path(token) for token in lowered):
        return "generated_artifact_churn"
    if all(
        token.startswith(
            (
                "src/odylith/runtime/surfaces/render_",
                "docs/",
                "odylith/radar/radar.html",
                "odylith/radar/backlog-",
                "odylith/radar/standalone-pages.v1.js",
                "odylith/radar/traceability-",
            )
        )
        or token.startswith("odylith/radar/source/")
        for token in lowered
    ):
        return "render_or_doc_drift"
    if any(
        token.startswith(
            (
                "src/odylith/runtime/surfaces/watch_",
                "src/odylith/runtime/governance/delivery_intelligence_engine.py",
                "src/odylith/runtime/reasoning/odylith_reasoning.py",
                "src/odylith/runtime/surfaces/render_tooling_dashboard.py",
                "service-deploy/",
            )
        )
        for token in lowered
    ):
        return "reasoning_or_control_plane_change"
    if any(token.startswith(("odylith/runtime/contracts/", "contracts/", "policies/")) for token in lowered):
        return "policy_or_contract_change"
    return "implementation_change"


def _subject(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    diagnostics = snapshot.get("diagnostics", {}) if isinstance(snapshot.get("diagnostics"), Mapping) else {}
    readout = _readout(snapshot)
    return {
        "type": str(snapshot.get("scope_type", "")).strip(),
        "id": str(snapshot.get("scope_id", "")).strip(),
        "label": str(snapshot.get("scope_label", "")).strip() or str(snapshot.get("scope_id", "")).strip(),
        "scope_key": str(snapshot.get("scope_key", "")).strip(),
        "status": str(diagnostics.get("status", "")).strip() or "unknown",
        "scenario": str(readout.get("primary_scenario", "")).strip(),
        "severity": str(readout.get("severity", "")).strip(),
    }


def _decision_at_stake(subject: Mapping[str, Any], observations: Mapping[str, Any]) -> str:
    scope_id = str(subject.get("id", "")).strip()
    label = str(subject.get("label", scope_id)).strip() or scope_id or "this scope"
    scenario = str(subject.get("scenario", "")).strip()
    status = str(subject.get("status", "")).strip().lower()
    ownership_ready = bool(observations.get("semantic_diff_ready", False))
    focus = _focus_artifact(observations)
    checkpoint = _date_label(str(observations.get("latest_explicit_ts_iso", "")).strip())
    if _is_self_hosting_case(subject, observations):
        if status == "finished":
            return (
                f"Did the {focus} changes after {checkpoint or 'the last checkpoint'} reopen {scope_id or label}, "
                "or are later evaluator edits being attributed back into a finished scope?"
            )
        return f"Are the newest {focus} changes in {label} changing evaluator semantics, or are they only presentation/control-surface churn?"
    if _has_authority_gap(observations):
        return f"Does {label} actually own the cross-surface state Odylith is aggregating, or is shared-surface churn being mistaken for authority?"
    if status == "finished" and scenario in {"unsafe_closeout", "stale_authority"} and ownership_ready:
        return (
            f"Should {scope_id or label} be reopened because {focus} moved after {checkpoint or 'the last checkpoint'}, "
            "or does that newer activity belong to successor work?"
        )
    if status == "finished" and not ownership_ready:
        return f"Is the post-closeout activity on {label} enough to reopen it, or is the ownership evidence still too weak to move history?"
    if _semantic_review_case(subject, observations):
        return f"Does the latest {focus} delta in {label} change reasoning/control semantics, or is it presentation-only noise?"
    if scenario == "cross_surface_conflict":
        return f"Which surface or owner should control {label} now that {focus} moved after the last checkpoint?"
    if scenario == "orphan_activity":
        return f"Which active owner should absorb the recent {focus} activity now landing on {label}?"
    if scenario == "false_priority":
        return f"Should work on {label} continue now, or is a different blocker actually more urgent?"
    return f"What maintainer action on {label} would still change the decision given the current checkpoint and proof?"


def _build_observations(snapshot: Mapping[str, Any], posture: Mapping[str, Any]) -> dict[str, Any]:
    evidence = snapshot.get("evidence_context", {}) if isinstance(snapshot.get("evidence_context"), Mapping) else {}
    diagnostics = snapshot.get("diagnostics", {}) if isinstance(snapshot.get("diagnostics"), Mapping) else {}
    readout = _readout(snapshot)
    code_references = _normalize_strings(evidence.get("code_references"), limit=12)
    changed_artifacts = _normalize_strings(evidence.get("changed_artifacts"), limit=16)
    owned_artifacts = code_references[:]
    semantic_diff_candidates = _semantic_diff_candidates(
        owned_artifacts=owned_artifacts,
        changed_artifacts=changed_artifacts,
        limit=4,
    )
    reasoning = posture.get("reasoning", {}) if isinstance(posture.get("reasoning"), Mapping) else {}
    clearance = posture.get("clearance", {}) if isinstance(posture.get("clearance"), Mapping) else {}
    evidence_refs = _normalize_refs(snapshot.get("evidence_refs", []), require_surface=False, limit=8)
    proof_routes = _normalize_refs(readout.get("proof_refs", []), require_surface=True, limit=8)
    observations = {
        "latest_activity_ts_iso": str(evidence.get("latest_event_ts_iso", "")).strip(),
        "latest_explicit_ts_iso": str(evidence.get("latest_explicit_ts_iso", "")).strip(),
        "linked_workstreams": _normalize_strings(evidence.get("linked_workstreams"), limit=8),
        "linked_components": _normalize_strings(evidence.get("linked_components"), limit=8),
        "linked_diagrams": _normalize_strings(evidence.get("linked_diagrams"), limit=8),
        "linked_surfaces": _normalize_strings(evidence.get("linked_surfaces"), limit=8),
        "code_references": code_references,
        "changed_artifacts": changed_artifacts,
        "owned_artifacts": owned_artifacts,
        "semantic_diff_candidates": semantic_diff_candidates,
        "semantic_diff_ready": bool(owned_artifacts) and bool(changed_artifacts),
        "ownership_evidence_state": "grounded" if owned_artifacts else "insufficient",
        "change_mix": _classify_change_mix([*code_references, *changed_artifacts]),
        "idea_file": str(diagnostics.get("idea_file", "")).strip(),
        "plan_path": str(diagnostics.get("plan_path", "")).strip(),
        "status": str(diagnostics.get("status", "")).strip() or "unknown",
        "live_reason": str(diagnostics.get("live_reason", "")).strip(),
        "reasoning_state": str(reasoning.get("state", "")).strip(),
        "clearance_state": str(clearance.get("state", "")).strip(),
        "render_drift": bool(diagnostics.get("render_drift", False)),
        "proof_state": proof_state.normalize_proof_state(snapshot.get("proof_state", {})),
        "proof_state_resolution": dict(snapshot.get("proof_state_resolution", {}))
        if isinstance(snapshot.get("proof_state_resolution"), Mapping)
        else {},
        "claim_guard": dict(snapshot.get("claim_guard", {})) if isinstance(snapshot.get("claim_guard"), Mapping) else {},
        "policy_breaches": [
            {
                "id": str(row.get("id", "")).strip(),
                "severity": str(row.get("severity", "")).strip(),
                "summary": str(row.get("summary", "")).strip(),
            }
            for row in posture.get("policy", {}).get("breaches", [])  # type: ignore[union-attr]
            if isinstance(row, Mapping)
        ][:8],
    }
    observations["evidence_refs"] = evidence_refs
    observations["proof_routes"] = proof_routes
    observations["proof_refs"] = proof_routes
    observations["proof_route_quality"] = _proof_route_quality(proof_routes)
    observations["evidence_gaps"] = _evidence_gaps(observations=observations)
    return observations


def _actor_memo(*, actor: str, claim: str, evidence: Sequence[str], confidence: float, unknowns: Sequence[str], decision_impact: str, best_next_check: str) -> dict[str, Any]:
    return {
        "actor": actor,
        "claim": str(claim).strip(),
        "evidence": [str(token).strip() for token in evidence if str(token).strip()],
        "confidence": round(float(confidence), 3),
        "unknowns": [str(token).strip() for token in unknowns if str(token).strip()],
        "decision_impact": str(decision_impact).strip(),
        "best_next_check": str(best_next_check).strip(),
    }


def _build_evidence_items(
    *,
    subject: Mapping[str, Any],
    observations: Mapping[str, Any],
    explanation_facts: Sequence[str],
) -> list[dict[str, str]]:
    rows: list[tuple[str, str]] = []

    def _append(tag: str, text: str) -> None:
        token = _sentence(text)
        if token:
            rows.append((tag, token))

    status = str(subject.get("status", "")).strip().lower() or "unknown"
    latest = str(observations.get("latest_activity_ts_iso", "")).strip()
    explicit = str(observations.get("latest_explicit_ts_iso", "")).strip()
    linked_surfaces = _normalize_strings(observations.get("linked_surfaces"), limit=4)
    linked_components = _normalize_strings(observations.get("linked_components"), limit=4)
    owned_artifacts = _normalize_strings(observations.get("owned_artifacts"), limit=4)
    semantic_diff_candidates = _normalize_strings(observations.get("semantic_diff_candidates"), limit=4)
    policy_breaches = observations.get("policy_breaches", []) if isinstance(observations.get("policy_breaches"), list) else []
    evidence_gaps = _normalize_strings(observations.get("evidence_gaps"), limit=4)

    _append("status", f"Status: {status}")
    if latest:
        _append("latest_activity", f"Latest activity: {latest}")
    if explicit:
        _append("latest_explicit", f"Last explicit checkpoint: {explicit}")
    if linked_surfaces:
        _append("linked_surfaces", f"Linked surfaces: {_series(linked_surfaces, limit=4)}")
    if linked_components:
        _append("linked_components", f"Linked components: {_series(linked_components, limit=4)}")
    if owned_artifacts:
        _append("owned_artifacts", f"Named owned artifacts: {_series(owned_artifacts, limit=4)}")
    if semantic_diff_candidates:
        _append("semantic_diff_candidates", f"Semantic diff candidates: {_series(semantic_diff_candidates, limit=4)}")
    _append("change_mix", f"Change mix: {str(observations.get('change_mix', '')).strip() or 'unknown'}")
    _append("proof_route_quality", f"Proof route quality: {str(observations.get('proof_route_quality', '')).strip() or 'missing'}")
    for row in policy_breaches[:2]:
        _append(
            "policy",
            f"Policy breach: {str(row.get('summary', row.get('id', 'policy gap'))).strip() or 'policy gap'}",
        )
    for token in explanation_facts[:3]:
        _append("fact", str(token))
    for token in evidence_gaps[:3]:
        _append("gap", str(token))
    return [
        {
            "id": f"E{index}",
            "tag": tag,
            "text": text,
        }
        for index, (tag, text) in enumerate(rows, start=1)
    ]


def _evidence_citations(
    evidence_items: Sequence[Mapping[str, Any]],
    *,
    tags: Sequence[str],
    limit: int = 3,
) -> list[str]:
    wanted = {str(tag).strip() for tag in tags if str(tag).strip()}
    rows: list[str] = []
    for row in evidence_items:
        if not isinstance(row, Mapping):
            continue
        if str(row.get("tag", "")).strip() not in wanted:
            continue
        identifier = str(row.get("id", "")).strip()
        text = str(row.get("text", "")).strip()
        if not identifier or not text:
            continue
        rows.append(f"[{identifier}] {text}")
        if len(rows) >= limit:
            break
    return rows


def _ownership_ready(observations: Mapping[str, Any]) -> bool:
    return bool(_normalize_strings(observations.get("owned_artifacts"), limit=1))


def _is_self_hosting_case(subject: Mapping[str, Any], observations: Mapping[str, Any]) -> bool:
    _ = subject
    components = {str(token).strip().lower() for token in observations.get("linked_components", []) if str(token).strip()}
    artifacts = [
        str(token).strip().lower()
        for token in [
            *_normalize_strings(observations.get("semantic_diff_candidates"), limit=8),
            *_normalize_strings(observations.get("owned_artifacts"), limit=12),
        ]
        if str(token).strip()
    ]
    return (
        (
            "odylith" in components
            or "platform-cli" in components
            or "tooling-dashboard" in components
        )
        and str(observations.get("change_mix", "")).strip() == "reasoning_or_control_plane_change"
        and any(token.startswith(_EVALUATOR_CORE_ARTIFACT_PREFIXES) for token in artifacts)
    )


def _has_authority_gap(observations: Mapping[str, Any]) -> bool:
    linked_surfaces = _normalize_strings(observations.get("linked_surfaces"), limit=8)
    linked_components = _normalize_strings(observations.get("linked_components"), limit=8)
    return len(linked_surfaces) >= 4 and len(linked_components) >= 2 and not _ownership_ready(observations)


def _semantic_review_case(subject: Mapping[str, Any], observations: Mapping[str, Any]) -> bool:
    _ = subject
    return _ownership_ready(observations) and str(observations.get("change_mix", "")).strip() == "reasoning_or_control_plane_change"


def _bounded_sparse_evidence_bundle_ready(
    subject: Mapping[str, Any],
    observations: Mapping[str, Any],
    *,
    evidence_items: Sequence[Mapping[str, Any]],
) -> bool:
    scope_type = str(subject.get("type", "")).strip().lower()
    if scope_type not in {"component", "diagram"}:
        return False
    if _ownership_ready(observations):
        return False
    linked_context_count = sum(
        len(_normalize_strings(observations.get(key), limit=8))
        for key in ("linked_workstreams", "linked_components", "linked_diagrams", "linked_surfaces")
    )
    evidence_count = sum(
        1
        for row in evidence_items
        if isinstance(row, Mapping) and str(row.get("id", "")).strip()
    )
    return (
        evidence_count >= 4
        and linked_context_count >= 4
        and bool(str(observations.get("latest_activity_ts_iso", "")).strip())
        and bool(_normalize_strings(observations.get("changed_artifacts"), limit=1))
        and bool(_normalize_strings(observations.get("evidence_gaps"), limit=1))
    )


def _provider_gate(
    *,
    provider_available: bool,
    provider_focus: bool,
    focus_cap: int,
    subject: Mapping[str, Any],
    observations: Mapping[str, Any],
    evidence_items: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not provider_available:
        return {
            "eligible": False,
            "reason_code": "provider_unavailable",
            "reason_label": "provider unavailable",
            "reason_detail": "No AI reasoning provider is configured or available for this Odylith refresh.",
        }
    if not provider_focus:
        return {
            "eligible": False,
            "reason_code": "outside_ai_focus",
            "reason_label": "outside AI focus cap",
            "reason_detail": (
                f"This case stays eligible, but provider-backed effort is currently focused on the top {max(1, int(focus_cap))} "
                "cases in Odylith's default focused inbox before the rest of the queue."
            ),
        }
    if bool(observations.get("render_drift", False)):
        return {
            "eligible": False,
            "reason_code": "render_drift",
            "reason_label": "render drift stays deterministic",
            "reason_detail": "Render drift cases stay deterministic because they are handled as bounded executable corrections rather than AI review problems.",
        }
    if str(observations.get("proof_route_quality", "")).strip() != "deep-linkable":
        return {
            "eligible": False,
            "reason_code": "no_deep_linkable_proof",
            "reason_label": "no deep-linkable proof routes",
            "reason_detail": "Provider review is skipped because operators cannot inspect the cited evidence directly through deep-linkable proof routes.",
        }
    if _ownership_ready(observations):
        return {
            "eligible": True,
            "reason_code": "ownership_grounded",
            "reason_label": "owned artifacts ground review",
            "reason_detail": "Named owned artifacts and proof routes provide enough grounding for bounded provider review.",
        }
    if bool(observations.get("policy_breaches")):
        return {
            "eligible": True,
            "reason_code": "policy_boundary",
            "reason_label": "policy boundary review",
            "reason_detail": "Provider review is allowed because the case is bounded by a concrete policy boundary and cited proof.",
        }
    if _is_self_hosting_case(subject, observations):
        return {
            "eligible": True,
            "reason_code": "self_hosting",
            "reason_label": "self-hosting evaluator review",
            "reason_detail": "Provider review is allowed because the case directly concerns evaluator-path semantics with grounded proof.",
        }
    if _has_authority_gap(observations):
        return {
            "eligible": True,
            "reason_code": "authority_gap",
            "reason_label": "authority gap review",
            "reason_detail": "Provider review is allowed because the case is a bounded cross-surface ownership conflict with deep-linkable proof.",
        }
    if _bounded_sparse_evidence_bundle_ready(subject, observations, evidence_items=evidence_items):
        return {
            "eligible": True,
            "reason_code": "bounded_sparse_evidence",
            "reason_label": "bounded sparse-evidence review",
            "reason_detail": "Provider review is allowed because this component/diagram case still has deep-linkable proof and a bounded evidence bundle even though strict ownership evidence is incomplete.",
        }
    owned_artifacts = _normalize_strings(observations.get("owned_artifacts"), limit=2)
    semantic_diff_candidates = _normalize_strings(observations.get("semantic_diff_candidates"), limit=2)
    if not owned_artifacts and not semantic_diff_candidates:
        return {
            "eligible": False,
            "reason_code": "no_owned_or_semantic_diff",
            "reason_label": "no owned artifacts / no semantic diff candidate",
            "reason_detail": "Provider review is skipped because the case has neither named owned artifacts nor a semantic-diff candidate to ground a bounded semantic read.",
        }
    if not owned_artifacts:
        return {
            "eligible": False,
            "reason_code": "no_owned_artifacts",
            "reason_label": "no owned artifacts",
            "reason_detail": "Provider review is skipped because the current ownership read is not bound to named owned artifacts.",
        }
    if not semantic_diff_candidates:
        return {
            "eligible": False,
            "reason_code": "no_semantic_diff_candidate",
            "reason_label": "no semantic diff candidate",
            "reason_detail": "Provider review is skipped because the case has owned artifacts but no named semantic-diff candidate for the newest change.",
        }
    return {
        "eligible": False,
        "reason_code": "insufficient_bounded_evidence",
        "reason_label": "insufficient bounded evidence",
        "reason_detail": "Provider review is skipped because the case is not yet bounded tightly enough for grounded AI assistance.",
    }


def _provider_artifact_label(tag: str) -> str:
    token = str(tag or "").strip()
    return _PROVIDER_ARTIFACT_LABELS.get(token, "the cited artifact")


def _sanitize_provider_text(text: str, *, evidence_items: Sequence[Mapping[str, Any]]) -> str:
    if not text:
        return ""
    path_labels: dict[str, tuple[int, str]] = {}
    for row in evidence_items:
        if not isinstance(row, Mapping):
            continue
        evidence_text = str(row.get("text", "")).strip()
        if not evidence_text:
            continue
        tag = str(row.get("tag", "")).strip()
        label = _provider_artifact_label(tag)
        priority = int(_PROVIDER_ARTIFACT_LABEL_PRIORITY.get(tag, 99))
        for match in operator_readout.RAW_PATH_RE.finditer(evidence_text):
            token = str(match.group(0)).strip()
            if not token:
                continue
            current = path_labels.get(token)
            readable = _artifact_label(token) or label
            if current is None or priority < current[0]:
                path_labels[token] = (priority, readable)

    def _replace(match: Any) -> str:
        token = str(match.group(0)).strip()
        replacement = path_labels.get(token)
        return replacement[1] if replacement is not None else "the cited artifact"

    sanitized = operator_readout.RAW_PATH_RE.sub(_replace, text)
    return " ".join(sanitized.split())


def _validate_provider_finding(
    finding: Mapping[str, Any] | None,
    *,
    evidence_items: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    evidence_ids = {
        str(row.get("id", "")).strip()
        for row in evidence_items
        if isinstance(row, Mapping) and str(row.get("id", "")).strip()
    }
    validated: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    if not isinstance(finding, Mapping):
        return validated, ["provider returned no structured finding"]
    for field in _PROVIDER_FIELD_NAMES:
        raw = finding.get(field)
        if not isinstance(raw, Mapping):
            errors.append(f"{field} must include text plus evidence_ids")
            continue
        text = _sanitize_provider_text(str(raw.get("text", "")).strip(), evidence_items=evidence_items)
        evidence_refs = _normalize_strings(raw.get("evidence_ids"), limit=6)
        if not text:
            errors.append(f"{field} text is empty")
            continue
        if operator_readout.RAW_PATH_RE.search(text):
            errors.append(f"{field} leaked a raw path")
            continue
        if not evidence_refs:
            errors.append(f"{field} omitted evidence citations")
            continue
        invalid_ids = [token for token in evidence_refs if token not in evidence_ids]
        if invalid_ids:
            errors.append(f"{field} cited unknown evidence ids: {', '.join(invalid_ids)}")
            continue
        validated[field] = {
            "text": text,
            "evidence_ids": evidence_refs,
        }
    return validated, errors


def _provider_prompt_payload(
    *,
    dossier: Mapping[str, Any],
    adjudication: Mapping[str, Any],
    actor_memos: Sequence[Mapping[str, Any]],
    evidence_items: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "case_id": str(dossier.get("case_id", "")).strip(),
        "decision_at_stake": str(dossier.get("decision_at_stake", "")).strip(),
        "subject": dict(dossier.get("subject", {})) if isinstance(dossier.get("subject"), Mapping) else {},
        "baseline": dict(dossier.get("baseline", {})) if isinstance(dossier.get("baseline"), Mapping) else {},
        "observations": {
            key: value
            for key, value in dict(dossier.get("observations", {})).items()
            if key
            in {
                "latest_activity_ts_iso",
                "latest_explicit_ts_iso",
                "linked_workstreams",
                "linked_components",
                "linked_surfaces",
                "owned_artifacts",
                "semantic_diff_candidates",
                "ownership_evidence_state",
                "proof_route_quality",
                "evidence_gaps",
            }
        }
        if isinstance(dossier.get("observations"), Mapping)
        else {},
        "deterministic_draft": {
            "leading_explanation": str(adjudication.get("leading_explanation", "")).strip(),
            "strongest_rival": str(adjudication.get("strongest_rival", "")).strip(),
            "risk_if_wrong": str(adjudication.get("risk_if_wrong", "")).strip(),
            "discriminating_next_check": str(adjudication.get("discriminating_next_check", "")).strip(),
        },
        "actor_memos": [
            {
                "actor": str(row.get("actor", "")).strip(),
                "claim": str(row.get("claim", "")).strip(),
                "evidence": [str(token).strip() for token in row.get("evidence", []) if str(token).strip()][:4],
                "unknowns": [str(token).strip() for token in row.get("unknowns", []) if str(token).strip()][:3],
                "best_next_check": str(row.get("best_next_check", "")).strip(),
            }
            for row in actor_memos
            if isinstance(row, Mapping)
        ],
        "evidence_items": [
            {
                "id": str(row.get("id", "")).strip(),
                "tag": str(row.get("tag", "")).strip(),
                "text": str(row.get("text", "")).strip(),
            }
            for row in evidence_items
            if isinstance(row, Mapping)
        ],
        "required_output": {
            "fields": list(_PROVIDER_FIELD_NAMES),
            "citation_rule": "Every field must include evidence_ids drawn only from the provided evidence_items ids.",
        },
    }


def _apply_provider_enrichment(
    *,
    provider: Any | None,
    provider_gate: Mapping[str, Any],
    dossier: Mapping[str, Any],
    adjudication: Mapping[str, Any],
    actor_memos: Sequence[Mapping[str, Any]],
    evidence_items: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], str, dict[str, Any]]:
    gate = dict(provider_gate) if isinstance(provider_gate, Mapping) else {}
    telemetry: dict[str, Any] = {
        "state": "deterministic-only",
        "provider_used": False,
        "provider_validated": False,
        "provider_validation_errors": [],
        "cited_evidence_ids": [],
        "provider_failure_code": "",
        "provider_failure_detail": "",
        "provider_runtime_degraded": False,
        "provider_eligible": bool(gate.get("eligible", False)),
        "provider_gate_reason_code": str(gate.get("reason_code", "")).strip(),
        "provider_gate_reason": str(gate.get("reason_label", "")).strip(),
        "provider_gate_detail": str(gate.get("reason_detail", "")).strip(),
        "deterministic_reason": str(gate.get("reason_label", "")).strip(),
        "deterministic_reason_detail": str(gate.get("reason_detail", "")).strip(),
    }
    if provider is None or not bool(gate.get("eligible", False)):
        return dict(adjudication), "", telemetry

    telemetry["provider_used"] = True
    telemetry["state"] = "deterministic-fallback"
    finding = provider.generate_finding(
        prompt_payload=_provider_prompt_payload(
            dossier=dossier,
            adjudication=adjudication,
            actor_memos=actor_memos,
            evidence_items=evidence_items,
        )
    )
    failure_code = str(getattr(provider, "last_failure_code", "")).strip()
    failure_detail = str(getattr(provider, "last_failure_detail", "")).strip()
    if finding is None and failure_code in {"timeout", "unavailable", "transport_error"}:
        telemetry["provider_failure_code"] = failure_code
        telemetry["provider_failure_detail"] = failure_detail
        telemetry["provider_runtime_degraded"] = True
        telemetry["deterministic_reason"] = "provider unavailable"
        telemetry["deterministic_reason_detail"] = (
            failure_detail
            or "Tribunal kept the deterministic result because the provider was unavailable during this run."
        )
        return dict(adjudication), "", telemetry
    validated, errors = _validate_provider_finding(finding, evidence_items=evidence_items)
    telemetry["provider_validation_errors"] = errors
    if errors or len(validated) != len(_PROVIDER_FIELD_NAMES):
        telemetry["deterministic_reason"] = "provider validation failed"
        telemetry["deterministic_reason_detail"] = "Tribunal kept the deterministic result because the provider output failed grounded-evidence validation."
        return dict(adjudication), "", telemetry

    enriched = dict(adjudication)
    for field in _PROVIDER_FIELD_NAMES:
        if field == "maintainer_brief":
            continue
        enriched[field] = str(validated[field]["text"]).strip()
    telemetry["provider_validated"] = True
    telemetry["state"] = "validated-ai-assisted"
    telemetry["deterministic_reason"] = ""
    telemetry["deterministic_reason_detail"] = ""
    telemetry["cited_evidence_ids"] = sorted(
        {
            token
            for field in _PROVIDER_FIELD_NAMES
            for token in validated[field]["evidence_ids"]
        }
    )
    return enriched, str(validated["maintainer_brief"]["text"]).strip(), telemetry


def _can_reuse_cached_case(
    cached: Mapping[str, Any],
    *,
    fingerprint: str,
    provider: Any | None,
    require_provider_attempt: bool,
) -> bool:
    if str(cached.get("evidence_fingerprint", "")).strip() != str(fingerprint).strip():
        return False
    case = cached.get("case", {}) if isinstance(cached.get("case"), Mapping) else {}
    reasoning_meta = case.get("reasoning", {}) if isinstance(case.get("reasoning"), Mapping) else {}
    if require_provider_attempt and provider is not None and not bool(reasoning_meta.get("provider_used", False)):
        return False
    if provider is not None and bool(reasoning_meta.get("provider_used", False)) and not bool(reasoning_meta.get("provider_validated", False)):
        return False
    return bool(case)


def _rehydrate_cached_case(
    cached_case: Mapping[str, Any],
    *,
    fingerprint: str,
    subject: Mapping[str, Any],
    dossier: Mapping[str, Any],
    rank: int,
    provider_focus: bool,
    provider_gate: Mapping[str, Any],
    selection_meta: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Refresh cached queue state when selection or gate metadata changes.

    Cached deterministic cases can remain valid when the evidence fingerprint is
    unchanged, but queue-facing fields such as focus budget membership,
    selection slot, and deterministic gate reason are derived from the current
    provider-selection pass rather than the prior cached payload.
    """

    case = dict(cached_case)
    reasoning_meta = dict(case.get("reasoning", {})) if isinstance(case.get("reasoning"), Mapping) else {}
    if not bool(reasoning_meta.get("provider_used", False)) and not bool(reasoning_meta.get("provider_validated", False)):
        gate = dict(provider_gate) if isinstance(provider_gate, Mapping) else {}
        reasoning_meta["provider_eligible"] = bool(gate.get("eligible", False))
        reasoning_meta["provider_gate_reason_code"] = str(gate.get("reason_code", "")).strip()
        reasoning_meta["provider_gate_reason"] = str(gate.get("reason_label", "")).strip()
        reasoning_meta["provider_gate_detail"] = str(gate.get("reason_detail", "")).strip()
        reasoning_meta["deterministic_reason"] = str(gate.get("reason_label", "")).strip()
        reasoning_meta["deterministic_reason_detail"] = str(gate.get("reason_detail", "")).strip()
        reasoning_meta["state"] = "deterministic-only"
        case["reasoning"] = reasoning_meta

    packet = dict(case.get("packet", {})) if isinstance(case.get("packet"), Mapping) else {}
    adjudication = dict(case.get("adjudication", {})) if isinstance(case.get("adjudication"), Mapping) else {}
    brief = str(case.get("maintainer_brief", "")).strip()
    observations = dossier.get("observations", {}) if isinstance(dossier.get("observations"), Mapping) else {}
    proof_routes = observations.get("proof_routes", []) if isinstance(observations.get("proof_routes"), list) else []
    queue_row = _case_queue_row(
        subject,
        dossier,
        adjudication,
        brief,
        packet,
        proof_routes,
        rank,
        reasoning_state=str(reasoning_meta.get("state", "deterministic-only")).strip() or "deterministic-only",
        provider_used=bool(reasoning_meta.get("provider_used", False)),
        provider_validated=bool(reasoning_meta.get("provider_validated", False)),
        provider_focus=provider_focus,
        deterministic_reason=str(reasoning_meta.get("deterministic_reason", "")).strip(),
        deterministic_reason_detail=str(reasoning_meta.get("deterministic_reason_detail", "")).strip(),
        selection_meta=selection_meta,
    )
    case["dossier"] = dict(dossier)
    case["evidence_fingerprint"] = str(fingerprint).strip()
    case["queue_row"] = queue_row
    case["proof_reopen"] = dict(queue_row.get("proof_reopen", {})) if isinstance(queue_row.get("proof_reopen"), Mapping) else {}
    case["selection"] = dict(selection_meta) if isinstance(selection_meta, Mapping) else {}
    return case


def _confidence_components(
    *,
    observations: Mapping[str, Any],
    actor_memos: Sequence[Mapping[str, Any]],
    provider_used: bool,
    provider_validated: bool,
) -> dict[str, float]:
    evidence_present = float(
        sum(
            1
            for token in (
                bool(str(observations.get("latest_activity_ts_iso", "")).strip()),
                bool(str(observations.get("latest_explicit_ts_iso", "")).strip()),
                bool(_normalize_strings(observations.get("owned_artifacts"), limit=1)),
                bool(_normalize_strings(observations.get("changed_artifacts"), limit=1)),
            )
            if token
        )
    ) / 4.0
    proof_quality = {
        "deep-linkable": 1.0,
        "partial": 0.55,
        "missing": 0.15,
    }.get(str(observations.get("proof_route_quality", "")).strip(), 0.25)
    ownership_clarity = 1.0 if _ownership_ready(observations) else 0.2
    actor_disagreement = any(
        row.get("unknowns")
        for row in actor_memos
        if isinstance(row, Mapping)
    )
    contradiction_strength = max(
        0.2,
        1.0 - (0.18 * len(_normalize_strings(observations.get("evidence_gaps"), limit=4))) - (0.12 if actor_disagreement else 0.0),
    )
    provider_validation = 1.0 if provider_validated else 0.3 if provider_used else 0.55
    return {
        "evidence_completeness": round(evidence_present, 3),
        "proof_route_quality": round(proof_quality, 3),
        "ownership_clarity": round(ownership_clarity, 3),
        "contradiction_strength": round(contradiction_strength, 3),
        "provider_validation": round(provider_validation, 3),
    }


def _score_confidence(
    *,
    observations: Mapping[str, Any],
    actor_memos: Sequence[Mapping[str, Any]],
    provider_used: bool,
    provider_validated: bool,
) -> tuple[float, dict[str, float]]:
    components = _confidence_components(
        observations=observations,
        actor_memos=actor_memos,
        provider_used=provider_used,
        provider_validated=provider_validated,
    )
    score = (
        0.12
        + (0.3 * components["evidence_completeness"])
        + (0.2 * components["proof_route_quality"])
        + (0.2 * components["ownership_clarity"])
        + (0.12 * components["contradiction_strength"])
        + (0.06 * components["provider_validation"])
    )
    return round(min(0.95, max(0.25, score)), 3), components


def _observer_memo(subject: Mapping[str, Any], observations: Mapping[str, Any], evidence_items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    label = str(subject.get("label", subject.get("id", ""))).strip()
    linked_surfaces = _normalize_strings(observations.get("linked_surfaces"), limit=6)
    claim = f"{label} is currently being read through {', '.join(linked_surfaces) or 'the linked Odylith surfaces'}."
    return _actor_memo(
        actor="observer",
        claim=claim,
        evidence=_evidence_citations(
            evidence_items,
            tags=("latest_activity", "latest_explicit", "linked_surfaces", "fact"),
            limit=4,
        ),
        confidence=0.88,
        unknowns=[],
        decision_impact="Frames the live state before causal or policy judgment.",
        best_next_check="Confirm the newest meaningful activity and the last explicit checkpoint still match the current dossier.",
    )


def _ownership_memo(subject: Mapping[str, Any], observations: Mapping[str, Any], evidence_items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    scope_id = str(subject.get("id", "")).strip() or str(subject.get("label", "")).strip() or "this scope"
    label = str(subject.get("label", scope_id)).strip() or scope_id
    status = str(subject.get("status", "")).strip().lower()
    change_mix = str(observations.get("change_mix", "")).strip()
    evidence_gaps = _normalize_strings(observations.get("evidence_gaps"), limit=3)
    focus = _focus_artifact(observations)
    if not _ownership_ready(observations):
        claim = f"{label} does not currently carry named owned artifacts, so ownership is still inferential rather than evidenced."
        best_next_check = "Bind the case to named owned artifacts or explicit owner evidence before prescribing semantic diff review."
    elif status == "finished":
        claim = f"The newest {focus} change may still be real, but the maintainer first has to decide whether it belongs to finished {label} or to successor work."
        best_next_check = f"Compare the {focus} delta against {scope_id}'s owned artifacts before reopening the workstream."
    elif change_mix == "reasoning_or_control_plane_change":
        claim = f"The live ownership question is centered on {focus}, which looks closer to active control-plane change than to incidental renderer drift."
        best_next_check = "Separate causal control-plane change from incidental UI churn before rebinding ownership."
    else:
        claim = f"Ownership still appears anchored to {label}, but the decisive evidence is now the {focus} delta rather than the broader surface noise."
        best_next_check = "Confirm whether nearby shared-surface work should absorb any of the current activity before moving ownership."
    return _actor_memo(
        actor="ownership_resolver",
        claim=claim,
        evidence=_evidence_citations(
            evidence_items,
            tags=("status", "owned_artifacts", "semantic_diff_candidates", "change_mix", "linked_surfaces"),
            limit=4,
        ),
        confidence=0.74 if _ownership_ready(observations) else 0.48,
        unknowns=evidence_gaps or ["Whether nearby shared-surface work should absorb some of the current activity."],
        decision_impact="Changes whether the maintainer should reopen, rebind, or trust the current scope attribution.",
        best_next_check=best_next_check,
    )


def _causal_memo(subject: Mapping[str, Any], observations: Mapping[str, Any], evidence_items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    label = str(subject.get("label", subject.get("id", ""))).strip() or "this scope"
    status = str(subject.get("status", "")).strip().lower()
    latest = str(observations.get("latest_activity_ts_iso", "")).strip()
    explicit = str(observations.get("latest_explicit_ts_iso", "")).strip()
    focus = _focus_artifact(observations)
    if _is_self_hosting_case(subject, observations):
        claim = f"{label} is live because {focus} still sits on Odylith's evaluator path, so the queue is being graded with moving semantics."
    elif _has_authority_gap(observations):
        claim = f"{label} is live because Odylith is aggregating {_surface_phrase(observations)} without enough named ownership to make that cross-surface story authoritative."
    elif _semantic_review_case(subject, observations):
        claim = f"{label} is live because the decisive delta sits in {focus}, and the case stays unresolved until that change is classified as semantic or presentation-only."
    elif status == "finished" and latest and explicit and latest > explicit:
        claim = f"{label} is being kept live because activity continued after the last explicit checkpoint, and the newest {focus} delta may belong to newer work rather than the closed scope."
    elif not explicit:
        claim = f"{label} is live because the current evidence bundle has activity but no explicit checkpoint to anchor it."
    else:
        claim = f"{label} is live because the current evidence bundle still contains unresolved contradictions around {focus} and the last trustworthy checkpoint."
    return _actor_memo(
        actor="causal_analyst",
        claim=claim,
        evidence=_evidence_citations(
            evidence_items,
            tags=("latest_activity", "latest_explicit", "change_mix", "proof_route_quality", "fact"),
            limit=4,
        ),
        confidence=0.78,
        unknowns=["Whether the causal signal is direct or still partially explained by shared-surface churn."],
        decision_impact="Determines whether the case is about closeout drift, authority drift, or evaluator trust.",
        best_next_check="Identify the smallest artifact or decision delta that still explains why the case is live.",
    )


def _policy_memo(subject: Mapping[str, Any], observations: Mapping[str, Any], evidence_items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    label = str(subject.get("label", subject.get("id", ""))).strip() or "this scope"
    status = str(subject.get("status", "")).strip().lower()
    breaches = observations.get("policy_breaches", []) if isinstance(observations.get("policy_breaches"), list) else []
    if _is_self_hosting_case(subject, observations):
        claim = "Evaluator-changing scopes must downgrade trust until reasoning semantics are checked explicitly."
    elif _has_authority_gap(observations):
        claim = "Authority claims must be backed by named ownership evidence before the scope can be treated as trustworthy."
    elif status == "finished":
        claim = f"Finished work like {label} should not absorb unrelated follow-on churn without a new explicit owner or checkpoint."
    elif breaches:
        claim = "A policy breach is still open in the current evidence bundle."
    else:
        claim = "No explicit hard policy breach dominates the case, but governance proof is still incomplete."
    return _actor_memo(
        actor="policy_judge",
        claim=claim,
        evidence=_evidence_citations(
            evidence_items,
            tags=("policy", "proof_route_quality", "gap"),
            limit=3,
        ),
        confidence=0.74,
        unknowns=[],
        decision_impact="Separates a hard-stop or trust-downgrade case from a softer normative warning.",
        best_next_check="Confirm whether the current state violates a hard boundary or only a strong maintainer norm.",
    )


def _normative_memo(subject: Mapping[str, Any], observations: Mapping[str, Any], evidence_items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    label = str(subject.get("label", subject.get("id", ""))).strip() or "this scope"
    if _is_self_hosting_case(subject, observations):
        claim = "A strong platform maintainer should not treat self-hosted evaluator output as stable while the judgment path is still changing."
    elif _has_authority_gap(observations):
        claim = "A strong platform maintainer should reject visual cross-surface coherence when the named authority story is still incomplete."
    else:
        claim = f"A strong platform maintainer should not act on {label} until ownership, authority, and proof all point at the same story."
    return _actor_memo(
        actor="normative_judge",
        claim=claim,
        evidence=_evidence_citations(
            evidence_items,
            tags=("proof_route_quality", "gap", "status"),
            limit=3,
        ),
        confidence=0.7,
        unknowns=[],
        decision_impact="Defines the maintainer bar even when the repo has not encoded every rule as policy yet.",
        best_next_check="Ask whether the current decision would still look acceptable if another maintainer reviewed the same evidence cold.",
    )


def _adversary_memo(subject: Mapping[str, Any], observations: Mapping[str, Any], evidence_items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    label = str(subject.get("label", subject.get("id", ""))).strip() or "this scope"
    focus = _focus_artifact(observations)
    if _is_self_hosting_case(subject, observations):
        claim = f"The current self-hosting warning weakens sharply if {focus} only changes presentation or orchestration and leaves evaluator semantics untouched."
    elif _has_authority_gap(observations):
        claim = f"The authority-gap story may be overstated if {focus} already anchors ownership and Odylith is merely narrating that coherence poorly."
    elif _semantic_review_case(subject, observations):
        claim = f"The warning may be overstated if {focus} is presentation-only and does not change the maintainer decision that downstream surfaces depend on."
    elif not _ownership_ready(observations):
        claim = f"The current diagnosis could still be wrong because the newest activity is not yet bound to owned artifacts for {label}."
    else:
        claim = f"The current diagnosis could still be wrong if the newest {focus} activity genuinely belongs to {label} and is not just shared-surface churn."
    return _actor_memo(
        actor="adversary",
        claim=claim,
        evidence=_evidence_citations(
            evidence_items,
            tags=("change_mix", "owned_artifacts", "gap"),
            limit=3,
        ),
        confidence=0.62,
        unknowns=["Whether the rival explanation survives semantic diff review."],
        decision_impact="Prevents the maintainer from over-trusting the first explanation.",
        best_next_check="Run the one semantic check that would collapse the rival explanation if the current diagnosis is actually right.",
    )


def _counterfactual_memo(subject: Mapping[str, Any], observations: Mapping[str, Any], evidence_items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    focus = _focus_artifact(observations)
    if _is_self_hosting_case(subject, observations):
        claim = f"If {focus} does not touch evaluator semantics, the case should drop from trust downgrade to routine implementation tracking."
    elif _has_authority_gap(observations):
        claim = "If Odylith can name the unresolved ownership authorities concretely, the current authority warning should collapse materially."
    elif not _ownership_ready(observations):
        claim = "If the case gains named owned artifacts and a fresh semantic-diff candidate, the reopen question becomes materially more answerable."
    else:
        claim = f"If {focus} is rebound to another scope or shown to be presentation-only, the current warning should lose most of its force."
    return _actor_memo(
        actor="counterfactual_analyst",
        claim=claim,
        evidence=_evidence_citations(
            evidence_items,
            tags=("semantic_diff_candidates", "gap", "proof_route_quality"),
            limit=3,
        ),
        confidence=0.66,
        unknowns=[],
        decision_impact="Shows what evidence would actually make the case disappear.",
        best_next_check="Test the one change in assumptions that would most decisively shrink the case.",
    )


def _gap_memo(subject: Mapping[str, Any], observations: Mapping[str, Any], evidence_items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    _ = subject
    gaps = _normalize_strings(observations.get("evidence_gaps"), limit=4)
    claim = gaps[0] if gaps else "Evidence quality is bounded mainly by residual semantic ownership uncertainty."
    return _actor_memo(
        actor="gap_analyst",
        claim=claim,
        evidence=_evidence_citations(
            evidence_items,
            tags=("gap",),
            limit=4,
        ),
        confidence=0.71,
        unknowns=gaps,
        decision_impact="Caps how assertive the final brief can be.",
        best_next_check="Fill the highest-leverage missing evidence item before escalating the case further.",
    )


def _risk_memo(subject: Mapping[str, Any], observations: Mapping[str, Any], evidence_items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    label = str(subject.get("label", subject.get("id", ""))).strip() or "this scope"
    focus = _focus_artifact(observations)
    if _is_self_hosting_case(subject, observations):
        claim = f"If this read is wrong, maintainers will either over-downgrade queue trust or let {focus} change evaluator behavior without noticing."
    elif _has_authority_gap(observations):
        claim = "If this read is wrong, cross-surface coherence will be accepted before the underlying authority is real."
    elif _semantic_review_case(subject, observations):
        claim = f"If this read is wrong, maintainers will reopen {label} on a presentation-only delta or ignore a semantic change that still belongs in the case."
    elif not _ownership_ready(observations):
        claim = f"If this read is wrong, maintainers can reopen or dismiss {label} on inference rather than owned evidence."
    else:
        claim = f"If this read is wrong, maintainers can reopen the wrong history or close {label} against stale evidence."
    return _actor_memo(
        actor="risk_analyst",
        claim=claim,
        evidence=_evidence_citations(
            evidence_items,
            tags=("owned_artifacts", "gap", "proof_route_quality"),
            limit=3,
        ),
        confidence=0.8,
        unknowns=[],
        decision_impact="Defines the cost of trusting the wrong story.",
        best_next_check="Choose the next action that most reduces the cost-of-being-wrong, not just the cost-of-doing-work.",
    )


def _prescriber_memo(subject: Mapping[str, Any], observations: Mapping[str, Any], evidence_items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    scope_id = str(subject.get("id", "")).strip() or str(subject.get("label", "")).strip() or "this scope"
    label = str(subject.get("label", scope_id)).strip() or scope_id
    focus = _focus_artifact(observations)
    explicit = _date_label(str(observations.get("latest_explicit_ts_iso", "")).strip())
    if _is_self_hosting_case(subject, observations):
        claim = f"Classify the latest {focus} delta as evaluator-semantic or presentation-only before trusting queue guidance derived from {label}."
    elif _has_authority_gap(observations):
        claim = f"Name the owner behind {focus} before treating {label} as authoritative across {_surface_phrase(observations)}."
    elif not _ownership_ready(observations):
        claim = "Evidence is insufficient for semantic diff review; first bind the case to named owned artifacts or explicit ownership evidence."
    elif str(subject.get("status", "")).strip().lower() == "finished":
        claim = f"Decide whether the {focus} change after {explicit or 'the last checkpoint'} reopens {scope_id} or belongs to newer work before moving lifecycle state."
    elif _semantic_review_case(subject, observations):
        claim = f"Classify the latest {focus} delta as semantic or presentation-only before changing the maintainer decision on {label}."
    else:
        claim = f"Run the smallest check on {focus} that can still change the current maintainer decision on {label}."
    return _actor_memo(
        actor="prescriber",
        claim=claim,
        evidence=_evidence_citations(
            evidence_items,
            tags=("semantic_diff_candidates", "owned_artifacts", "gap"),
            limit=3,
        ),
        confidence=0.84,
        unknowns=[],
        decision_impact="Provides the single highest-leverage next move for the maintainer.",
        best_next_check=claim,
    )


def _adjudicate(
    *,
    case_id: str,
    subject: Mapping[str, Any],
    observations: Mapping[str, Any],
    actor_memos: Sequence[Mapping[str, Any]],
    confidence: float,
) -> dict[str, Any]:
    memo_by_actor = {
        str(row.get("actor", "")).strip(): row
        for row in actor_memos
        if isinstance(row, Mapping) and str(row.get("actor", "")).strip()
    }
    leading = memo_by_actor.get("causal_analyst", {})
    rival = memo_by_actor.get("adversary", {})
    prescriber = memo_by_actor.get("prescriber", {})
    risk = memo_by_actor.get("risk_analyst", {})
    disagreement = bool(_normalize_strings(observations.get("evidence_gaps"), limit=1))
    if _is_self_hosting_case(subject, observations):
        form = "trust_downgrade"
        systemic_tags = ["self_hosting", "trust", "evaluator"]
    elif _has_authority_gap(observations):
        form = "false_coherence"
        systemic_tags = ["authority", "ownership_gap", "cross_surface"]
    elif str(observations.get("render_drift", False)).strip().lower() == "true":
        form = "executable_fix"
        systemic_tags = ["render_drift", "generated_artifacts"]
    elif observations.get("policy_breaches"):
        form = "policy_breach"
        systemic_tags = ["policy"]
    elif str(subject.get("status", "")).strip().lower() == "finished" and _ownership_ready(observations):
        form = "ownership_challenge"
        systemic_tags = ["ownership", "attribution", "closeout"]
    elif _semantic_review_case(subject, observations):
        form = "semantic_review"
        systemic_tags = ["semantic_change", "control_plane", "active_scope"]
    else:
        form = "insufficient_evidence"
        systemic_tags = ["insufficient_evidence", "ownership_gap"]
    confidence_level = "strong" if confidence >= 0.8 else "moderate" if confidence >= 0.6 else "weak"
    actor_names = [name for name in _ACTOR_ORDER if name in memo_by_actor]
    editor_actors = [
        name
        for name in (
            "causal_analyst",
            "ownership_resolver",
            "adversary",
            "gap_analyst",
            "risk_analyst",
            "prescriber",
        )
        if name in memo_by_actor
    ]
    return {
        "outcome_id": f"outcome-{case_id}",
        "form": form,
        "confidence": round(confidence, 3),
        "confidence_level": confidence_level,
        "leading_explanation": str(leading.get("claim", "")).strip(),
        "strongest_rival": str(rival.get("claim", "")).strip(),
        "risk_if_wrong": str(risk.get("claim", "")).strip(),
        "discriminating_next_check": str(prescriber.get("claim", "")).strip(),
        "systemic_theme_tags": systemic_tags,
        "actor_disagreement": disagreement,
        "actor_influence": {
            "form": {
                "actors": actor_names,
                "summary": f"Form `{form}` is derived from the full actor roster over the current dossier, not from a single memo.",
            },
            "confidence": {
                "actors": actor_names,
                "summary": "Confidence combines dossier quality with the full actor contest, including unknowns and contradiction pressure.",
            },
            "editor_output": {
                "actors": editor_actors,
                "summary": "The editor brief is built from the leading explanation, rival, risk, evidence-gap, ownership, and next-check actors.",
            },
            "field_influencers": {
                "leading_explanation": [
                    name
                    for name in ("observer", "ownership_resolver", "causal_analyst")
                    if name in memo_by_actor
                ],
                "strongest_rival": [
                    name
                    for name in ("adversary", "counterfactual_analyst")
                    if name in memo_by_actor
                ],
                "risk_if_wrong": [
                    name
                    for name in ("risk_analyst", "policy_judge", "normative_judge")
                    if name in memo_by_actor
                ],
                "discriminating_next_check": [
                    name
                    for name in ("prescriber", "gap_analyst")
                    if name in memo_by_actor
                ],
            },
        },
    }


def _editorial_headline(form: str, subject: Mapping[str, Any], observations: Mapping[str, Any]) -> str:
    scope_id = str(subject.get("id", "")).strip()
    label = str(subject.get("label", scope_id)).strip() or scope_id or "This scope"
    focus = _focus_artifact(observations)
    if form == "semantic_review":
        return f"Classify {focus} before changing the call"
    if form == "ownership_challenge":
        return "Decide whether this belongs to successor work"
    if form == "trust_downgrade":
        return f"{focus} is still moving the evaluator"
    if form == "false_coherence":
        return "Cross-surface ownership is not proven yet"
    if form == "executable_fix":
        return f"{focus} is bounded enough to correct now"
    if form == "policy_breach":
        return "A policy boundary still blocks the call"
    if form == "insufficient_evidence":
        return f"Evidence on {label} is still too weak to act"
    return _CASE_FORM_HEADLINES.get(form, "Maintainer decision needs review")


def _build_editor_brief(subject: Mapping[str, Any], dossier: Mapping[str, Any], adjudication: Mapping[str, Any], actor_memos: Sequence[Mapping[str, Any]]) -> str:
    memo_by_actor = {
        str(row.get("actor", "")).strip(): row
        for row in actor_memos
        if isinstance(row, Mapping) and str(row.get("actor", "")).strip()
    }
    scope_id = str(subject.get("id", "")).strip()
    label = str(subject.get("label", scope_id)).strip() or scope_id or "This scope"
    status = str(subject.get("status", "")).strip().lower()
    observations = dossier.get("observations", {}) if isinstance(dossier.get("observations"), Mapping) else {}
    form = str(adjudication.get("form", "")).strip()
    focus = _focus_artifact(observations)
    checkpoint = _checkpoint_phrase(observations)
    surfaces = _surface_phrase(observations)
    opening = ""
    follow = ""
    if form == "trust_downgrade":
        if status == "finished":
            opening = f"{scope_id or label} is still marked finished, but {focus} changed {checkpoint} and still appears on Odylith's evaluator path."
        else:
            opening = f"{label} still has live evaluator-path movement in {focus} {checkpoint}, so Odylith is grading with semantics that are not yet stable."
        follow = "Treat the current queue output as provisional until the evaluator-path delta stops moving."
    elif form == "false_coherence":
        opening = f"{label} looks coherent across {surfaces}, but Odylith still cannot show enough named ownership to make that cross-surface story authoritative."
        follow = "Do not treat shared-surface churn as authoritative ownership until a concrete owner is named."
    elif form == "ownership_challenge":
        opening = f"{scope_id or label} stayed closed, yet the newest {focus} delta landed {checkpoint}, so the reopen decision depends on whether that activity still belongs to this finished scope."
        follow = "Use successor attribution rather than recency alone before rewriting workstream history."
    elif form == "semantic_review":
        opening = f"{label} now hinges on whether {focus} changed reasoning/control behavior rather than presentation."
        follow = "Keep the maintainer call provisional until that delta is classified."
    elif form == "executable_fix":
        opening = f"{label} has a bounded render drift that is specific enough to correct directly."
        follow = "This one is specific enough to move from diagnosis into a deterministic correction path."
    elif form == "policy_breach":
        opening = f"{label} is blocked less by implementation churn than by a still-open policy boundary in the current evidence bundle."
        follow = "Clear the policy boundary before trusting any implementation-side signal."
    else:
        opening = f"{label} still needs review, but the missing evidence is more decisive than the visible surface activity."
        follow = "Do not let weak ownership evidence harden into a semantic conclusion."
    rival = str(memo_by_actor.get("adversary", {}).get("claim", "")).strip()
    gap = str(memo_by_actor.get("gap_analyst", {}).get("claim", "")).strip()
    risk = str(memo_by_actor.get("risk_analyst", {}).get("claim", "")).strip()
    prescriber = str(memo_by_actor.get("prescriber", {}).get("claim", "")).strip()
    support = ""
    if form == "insufficient_evidence" and gap:
        support = gap
    elif rival:
        support = f"Strongest rival: {rival}"
    elif risk:
        support = risk
    parts = [_sentence(opening)]
    if support:
        parts.append(_sentence(support))
    parts.append(_sentence(follow))
    if prescriber and prescriber not in follow:
        parts.append(_sentence(prescriber))
    return " ".join(part for part in parts if part)


def _case_queue_row(
    subject: Mapping[str, Any],
    dossier: Mapping[str, Any],
    adjudication: Mapping[str, Any],
    brief: str,
    packet: Mapping[str, Any],
    proof_routes: Sequence[Mapping[str, Any]],
    rank: int,
    *,
    reasoning_state: str,
    provider_used: bool,
    provider_validated: bool,
    provider_focus: bool,
    deterministic_reason: str,
    deterministic_reason_detail: str,
    selection_meta: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    form = str(adjudication.get("form", "")).strip()
    mode = str(packet.get("execution_mode", "manual")).strip() or "manual"
    selection = dict(selection_meta) if isinstance(selection_meta, Mapping) else {}
    resolved_proof_state = (
        proof_state.normalize_proof_state(dossier.get("observations", {}).get("proof_state", {}))
        if isinstance(dossier.get("observations"), Mapping)
        else {}
    )
    proof_reopen = proof_state.proof_reopen_signal(resolved_proof_state)
    action_label = {
        "deterministic": "Approve and apply",
        "ai_engine": "Send to AI engine",
        "hybrid": "Review proposed fix",
        "manual": "Review manually",
    }.get(mode, "Review manually")
    return {
        "id": str(dossier.get("case_id", "")).strip(),
        "rank": rank,
        "scope_key": str(subject.get("scope_key", "")).strip(),
        "scope_type": str(subject.get("type", "")).strip(),
        "scope_id": str(subject.get("id", "")).strip(),
        "scope_label": str(subject.get("label", "")).strip(),
        "headline": _editorial_headline(form, subject, dossier.get("observations", {}) if isinstance(dossier.get("observations"), Mapping) else {}),
        "decision_at_stake": str(dossier.get("decision_at_stake", "")).strip(),
        "brief": brief,
        "packet_mode": mode,
        "reasoning_state": str(reasoning_state or "deterministic-only").strip() or "deterministic-only",
        "provider_used": bool(provider_used),
        "provider_validated": bool(provider_validated),
        "provider_focus": bool(provider_focus),
        "deterministic_reason": str(deterministic_reason or "").strip(),
        "deterministic_reason_detail": str(deterministic_reason_detail or "").strip(),
        "action_label": action_label,
        "confidence": float(adjudication.get("confidence", 0.0) or 0.0),
        "confidence_factors": dict(adjudication.get("confidence_factors", {})) if isinstance(adjudication.get("confidence_factors"), Mapping) else {},
        "systemic_theme_tags": _normalize_strings(adjudication.get("systemic_theme_tags"), limit=4),
        "proof_routes": [operator_readout.normalize_proof_ref(row) for row in proof_routes],
        "proof_refs": [operator_readout.normalize_proof_ref(row) for row in proof_routes],
        "proof_state": resolved_proof_state,
        "proof_state_resolution": dict(dossier.get("observations", {}).get("proof_state_resolution", {}))
        if isinstance(dossier.get("observations"), Mapping) and isinstance(dossier.get("observations", {}).get("proof_state_resolution"), Mapping)
        else {},
        "claim_guard": dict(dossier.get("observations", {}).get("claim_guard", {}))
        if isinstance(dossier.get("observations"), Mapping) and isinstance(dossier.get("observations", {}).get("claim_guard"), Mapping)
        else {},
        "proof_reopen": proof_reopen,
        "selection_slot": str(selection.get("slot", "")).strip(),
        "selection_reason": str(selection.get("reason", "")).strip(),
        "selection_metrics": dict(selection.get("metrics", {})) if isinstance(selection.get("metrics"), Mapping) else {},
        "selection_score_band_size": int(selection.get("score_band_size", 0) or 0),
    }


def _build_systemic_brief(case_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    themes: dict[str, int] = {}
    for row in case_rows:
        for tag in row.get("systemic_theme_tags", []) if isinstance(row.get("systemic_theme_tags"), list) else []:
            token = str(tag or "").strip()
            if not token:
                continue
            themes[token] = int(themes.get(token, 0) or 0) + 1
    dominant = sorted(themes.items(), key=lambda item: (-item[1], item[0]))[:3]
    if not dominant:
        return {
            "headline": "No systemic theme dominates the current queue.",
            "summary": "Tribunal is currently dealing with isolated cases rather than one repeated latent cause.",
            "latent_causes": [],
            "leverage_actions": [],
        }
    latent = [token.replace("_", " ") for token, _count in dominant]
    return {
        "headline": "A small number of latent causes explain most of the active queue.",
        "summary": "Tribunal collapses repeated case noise into a few shared causes before it asks the maintainer to act.",
        "latent_causes": latent,
        "leverage_actions": [
            "Start with the highest-confidence case that also carries a reusable packet or discriminating check.",
            "Downgrade trust in cases that still depend on unresolved ownership or authority ambiguity.",
        ],
    }


def build_tribunal_payload(
    *,
    repo_root: Path,
    delivery_payload: Mapping[str, Any],
    posture: Mapping[str, Any],
    previous_payload: Mapping[str, Any] | None = None,
    config: Any | None = None,
    provider: Any | None = None,
) -> dict[str, Any]:
    """Build the Tribunal outcome artifact from delivery scopes and Odylith posture."""

    scope_cap = max(1, int(getattr(config, "scope_cap", 6) if config is not None else 6))
    provider_name = str(getattr(config, "provider", "")).strip() if config is not None else ""
    model_name = str(getattr(config, "model", "")).strip() if config is not None else ""
    provider_contract = _provider_contract_signature(config=config, provider=provider)
    scope_lookup = dashboard_shell_links.scope_lookup(delivery_payload)
    previous_cache = {}
    if isinstance(previous_payload, Mapping) and str(previous_payload.get("actor_policy_version", "")).strip() == _ACTOR_POLICY_VERSION:
        for row in previous_payload.get("cache", []) if isinstance(previous_payload.get("cache"), list) else []:
            if not isinstance(row, Mapping):
                continue
            scope_key = str(row.get("scope_key", "")).strip()
            fingerprint = str(row.get("evidence_fingerprint", "")).strip()
            case = dict(row.get("case", {})) if isinstance(row.get("case"), Mapping) else {}
            if scope_key and fingerprint and case:
                previous_cache[scope_key] = {
                    "evidence_fingerprint": fingerprint,
                    "case": case,
                }
    candidate_selection = _candidate_selection(delivery_payload, scope_cap=scope_cap)
    visible_scope_keys = list(candidate_selection.get("visible_scope_keys", []))
    provider_focus_scope_keys = {
        str(token).strip()
        for token in candidate_selection.get("provider_focus_scope_keys", [])
        if str(token).strip()
    }
    selection_meta_by_scope = (
        dict(candidate_selection.get("selection_meta", {}))
        if isinstance(candidate_selection.get("selection_meta"), Mapping)
        else {}
    )
    selection_summary = (
        dict(candidate_selection.get("summary", {}))
        if isinstance(candidate_selection.get("summary"), Mapping)
        else {}
    )
    cases: list[dict[str, Any]] = []
    case_queue: list[dict[str, Any]] = []
    cache_rows: list[dict[str, Any]] = []
    reused_count = 0
    generated_count = 0
    provider_attempted_count = 0
    provider_validated_count = 0
    provider_runtime_failure_code = ""
    provider_runtime_failure_detail = ""
    for rank, scope_key in enumerate(visible_scope_keys, start=1):
        snapshot = scope_lookup.get(scope_key, {})
        subject = _subject(snapshot)
        subject["scope_key"] = scope_key
        observations = _build_observations(snapshot, posture)
        readout = _readout(snapshot)
        decision_at_stake = _decision_at_stake(subject, observations)
        dossier = {
            "case_id": f"case-{scope_key.replace(':', '-')}",
            "subject": subject,
            "decision_at_stake": decision_at_stake,
            "observations": observations,
            "baseline": {
                "primary_scenario": str(readout.get("primary_scenario", subject.get("scenario", ""))).strip(),
                "severity": str(readout.get("severity", subject.get("severity", ""))).strip(),
            },
            "evidence_quality": str(snapshot.get("confidence", "")).strip() or "unknown",
        }
        explanation_facts = _normalize_strings(snapshot.get("explanation_facts"), limit=6)
        evidence_items = _build_evidence_items(
            subject=subject,
            observations=observations,
            explanation_facts=explanation_facts,
        )
        dossier["evidence_items"] = evidence_items
        provider_focus = scope_key in provider_focus_scope_keys
        provider_gate = _provider_gate(
            provider_available=provider is not None,
            provider_focus=provider_focus,
            focus_cap=scope_cap,
            subject=subject,
            observations=observations,
            evidence_items=evidence_items,
        )
        if provider is not None and provider_runtime_failure_code:
            provider_gate = {
                "eligible": False,
                "reason_code": f"provider-runtime-{provider_runtime_failure_code}",
                "reason_label": "provider unavailable",
                "reason_detail": (
                    (
                        "An earlier provider failure in this Tribunal run disabled provider enrichment for the remaining cases. "
                        f"{provider_runtime_failure_detail}"
                    ).strip()
                    if provider_runtime_failure_detail
                    else "An earlier provider failure in this Tribunal run disabled provider enrichment for the remaining cases."
                ),
            }
        fingerprint = _evidence_fingerprint(snapshot, posture, provider_contract=provider_contract)
        cached = previous_cache.get(scope_key)
        if cached and _can_reuse_cached_case(
            cached,
            fingerprint=fingerprint,
            provider=provider,
            require_provider_attempt=bool(provider_gate.get("eligible", False)),
        ):
            case = _rehydrate_cached_case(
                dict(cached.get("case", {})),
                fingerprint=fingerprint,
                subject=subject,
                dossier=dossier,
                rank=rank,
                provider_focus=provider_focus,
                provider_gate=provider_gate,
                selection_meta=selection_meta_by_scope.get(scope_key, {}),
            )
            cases.append(case)
            case_queue.extend(
                [dict(case.get("queue_row", {}))] if isinstance(case.get("queue_row"), Mapping) else []
            )
            cache_rows.append(
                {
                    "scope_key": scope_key,
                    "evidence_fingerprint": fingerprint,
                    "case": case,
                }
            )
            reasoning_meta = case.get("reasoning", {}) if isinstance(case.get("reasoning"), Mapping) else {}
            if bool(reasoning_meta.get("provider_used", False)):
                provider_attempted_count += 1
            if bool(reasoning_meta.get("provider_validated", False)):
                provider_validated_count += 1
            reused_count += 1
            continue
        actor_memos = [
            _observer_memo(subject, observations, evidence_items),
            _ownership_memo(subject, observations, evidence_items),
            _causal_memo(subject, observations, evidence_items),
            _policy_memo(subject, observations, evidence_items),
            _normative_memo(subject, observations, evidence_items),
            _adversary_memo(subject, observations, evidence_items),
            _counterfactual_memo(subject, observations, evidence_items),
            _gap_memo(subject, observations, evidence_items),
            _risk_memo(subject, observations, evidence_items),
            _prescriber_memo(subject, observations, evidence_items),
        ]
        adjudication = _adjudicate(
            case_id=str(dossier.get("case_id", "")).strip(),
            subject=subject,
            observations=observations,
            actor_memos=actor_memos,
            confidence=0.0,
        )
        adjudication, _provider_brief, reasoning_meta = _apply_provider_enrichment(
            provider=provider,
            provider_gate=provider_gate,
            dossier=dossier,
            adjudication=adjudication,
            actor_memos=actor_memos,
            evidence_items=evidence_items,
        )
        provider_attempted_count += int(bool(reasoning_meta.get("provider_used", False)))
        provider_validated_count += int(bool(reasoning_meta.get("provider_validated", False)))
        failure_code = str(reasoning_meta.get("provider_failure_code", "")).strip()
        failure_detail = str(reasoning_meta.get("provider_failure_detail", "")).strip()
        if not provider_runtime_failure_code and failure_code in {"timeout", "unavailable", "transport_error"}:
            provider_runtime_failure_code = failure_code
            provider_runtime_failure_detail = failure_detail
        confidence, confidence_factors = _score_confidence(
            observations=observations,
            actor_memos=actor_memos,
            provider_used=bool(reasoning_meta.get("provider_used", False)),
            provider_validated=bool(reasoning_meta.get("provider_validated", False)),
        )
        final_adjudication = _adjudicate(
            case_id=str(dossier.get("case_id", "")).strip(),
            subject=subject,
            observations=observations,
            actor_memos=actor_memos,
            confidence=confidence,
        )
        for field in ("leading_explanation", "strongest_rival", "risk_if_wrong", "discriminating_next_check"):
            if str(adjudication.get(field, "")).strip():
                final_adjudication[field] = str(adjudication.get(field, "")).strip()
        final_adjudication["confidence_factors"] = confidence_factors
        reasoning_meta["actor_influence"] = dict(final_adjudication.get("actor_influence", {}))
        observations["reasoning_state"] = str(reasoning_meta.get("state", "deterministic-only")).strip() or "deterministic-only"
        dossier["observations"] = observations
        prescriber = next((row for row in actor_memos if str(row.get("actor", "")).strip() == "prescriber"), {})
        packet = remediator.compile_correction_packet(
            repo_root=repo_root,
            dossier=dossier,
            adjudication=final_adjudication,
            prescriber=prescriber,
        )
        brief = _build_editor_brief(subject, dossier, final_adjudication, actor_memos)
        queue_row = _case_queue_row(
            subject,
            dossier,
            final_adjudication,
            brief,
            packet,
            observations.get("proof_routes", []) if isinstance(observations.get("proof_routes"), list) else [],
            rank,
            reasoning_state=str(reasoning_meta.get("state", "deterministic-only")).strip() or "deterministic-only",
            provider_used=bool(reasoning_meta.get("provider_used", False)),
            provider_validated=bool(reasoning_meta.get("provider_validated", False)),
            provider_focus=provider_focus,
            deterministic_reason=str(reasoning_meta.get("deterministic_reason", "")).strip(),
            deterministic_reason_detail=str(reasoning_meta.get("deterministic_reason_detail", "")).strip(),
            selection_meta=selection_meta_by_scope.get(scope_key, {}),
        )
        case = {
            "case_id": str(dossier.get("case_id", "")).strip(),
            "scope_key": scope_key,
            "evidence_fingerprint": fingerprint,
            "dossier": dossier,
            "actor_memos": actor_memos,
            "adjudication": final_adjudication,
            "maintainer_brief": brief,
            "reasoning": reasoning_meta,
            "packet": packet,
            "queue_row": queue_row,
            "proof_state": proof_state.normalize_proof_state(snapshot.get("proof_state", {})),
            "proof_state_resolution": dict(snapshot.get("proof_state_resolution", {}))
            if isinstance(snapshot.get("proof_state_resolution"), Mapping)
            else {},
            "claim_guard": dict(snapshot.get("claim_guard", {})) if isinstance(snapshot.get("claim_guard"), Mapping) else {},
            "proof_reopen": dict(queue_row.get("proof_reopen", {})) if isinstance(queue_row.get("proof_reopen"), Mapping) else {},
            "selection": dict(selection_meta_by_scope.get(scope_key, {})),
        }
        cases.append(case)
        case_queue.append(queue_row)
        cache_rows.append(
            {
                "scope_key": scope_key,
                "evidence_fingerprint": fingerprint,
                "case": case,
            }
        )
        generated_count += 1

    systemic_brief = _build_systemic_brief(case_queue)
    provider_validation_errors = sorted(
        {
            str(error).strip()
            for case in cases
            if isinstance(case, Mapping)
            for error in (
                case.get("reasoning", {}).get("provider_validation_errors", [])
                if isinstance(case.get("reasoning"), Mapping)
                and isinstance(case.get("reasoning", {}).get("provider_validation_errors", []), list)
                else []
            )
            if str(error).strip()
        }
    )
    state = "deterministic-only"
    degraded_reason = "ai-provider-disabled"
    if provider is not None:
        state = "hybrid" if provider_validated_count else "ready"
        if provider_validated_count or not provider_attempted_count:
            degraded_reason = ""
        elif provider_runtime_failure_code == "timeout":
            degraded_reason = "ai-provider-timeout"
        elif provider_runtime_failure_code in {"unavailable", "transport_error"}:
            degraded_reason = "ai-provider-unavailable"
        else:
            degraded_reason = "ai-validation-failed"
    return {
        "version": "v4",
        "generated_ts_iso": "",
        "state": state,
        "provider": provider_name,
        "model": model_name,
        "degraded_reason": degraded_reason,
        "provider_runtime_failure_code": provider_runtime_failure_code,
        "provider_runtime_failure_detail": provider_runtime_failure_detail,
        "provider_used": bool(provider_attempted_count),
        "provider_validated": bool(provider_validated_count),
        "provider_attempted_count": provider_attempted_count,
        "provider_validated_count": provider_validated_count,
        "provider_validation_errors": provider_validation_errors,
        "actor_policy_version": _ACTOR_POLICY_VERSION,
        "selection_summary": selection_summary,
        "cases": cases,
        "case_queue": case_queue,
        "findings": case_queue,
        "systemic_brief": systemic_brief,
        "cache": cache_rows,
        "stats": {
            "candidate_count": int(selection_summary.get("eligible_scope_count", len(visible_scope_keys)) or 0),
            "shown_scope_count": len(visible_scope_keys),
            "truncated_count": int(selection_summary.get("truncated_count", 0) or 0),
            "provider_focus_count": int(selection_summary.get("provider_focus_count", len(provider_focus_scope_keys)) or 0),
            "outside_focus_count": int(selection_summary.get("outside_focus_count", 0) or 0),
            "reused_count": reused_count,
            "generated_count": generated_count,
            "provider_attempted_count": provider_attempted_count,
            "provider_validated_count": provider_validated_count,
            "ai_case_count": provider_validated_count,
        },
    }


def cases_by_scope_key(payload: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("scope_key", "")).strip(): dict(row)
        for row in payload.get("cases", [])
        if isinstance(row, Mapping) and str(row.get("scope_key", "")).strip()
    }
def case_queue(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in payload.get("case_queue", [])
        if isinstance(row, Mapping)
    ]


def packet_summaries(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in payload.get("cases", []) if isinstance(payload.get("cases"), list) else []:
        if not isinstance(case, Mapping):
            continue
        packet = case.get("packet", {})
        if isinstance(packet, Mapping):
            rows.append(remediator.packet_summary(packet))
    return rows


__all__ = [
    "DEFAULT_REASONING_PATH",
    "build_tribunal_payload",
    "case_queue",
    "cases_by_scope_key",
    "packet_summaries",
]
