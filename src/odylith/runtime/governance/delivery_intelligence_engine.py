"""Shared delivery-intelligence engine for installed dashboard surfaces.

This module replaces renderer-local narrative heuristics with one deterministic
posture engine. Renderers may consume the generated runtime artifact or build
it in-memory, but the truth source remains this module's structured scope
snapshots.

Design constraints:
- deterministic posture/scoring remains authoritative;
- optional narration may rewrite cards, but only after validation;
- synthetic workspace activity is supporting evidence and never labeled
  explicit;
- the engine must be safe to run during sync and in isolated renderer tests.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

from odylith.runtime.governance import component_registry_intelligence as registry
from odylith.runtime.governance.delivery import scope_signal_ladder
from odylith.runtime.governance import operator_readout
from odylith.runtime.governance import proof_state
from odylith.runtime.reasoning import odylith_reasoning
from odylith.runtime.common import stable_generated_utc
from odylith.runtime.common.command_surface import display_command
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.reasoning import tribunal_engine
from odylith.runtime.governance import validate_backlog_contract as backlog_contract
from odylith.runtime.governance import workstream_inference

DEFAULT_OUTPUT_PATH = "odylith/runtime/delivery_intelligence.v4.json"
DEFAULT_CONTROL_POSTURE_PATH = "odylith/runtime/control-posture.v4.json"
DEFAULT_ODYLITH_REASONING_PATH = odylith_reasoning.DEFAULT_REASONING_PATH
DEFAULT_MAX_REVIEW_AGE_DAYS = 21
_SCOPE_TYPE_ORDER: tuple[str, ...] = ("grid", "surface", "workstream", "component", "diagram")
_CARD_KEYS: tuple[str, ...] = (
    "executive_thesis",
    "delivery_tension",
    "why_now",
    "blast_radius",
    "next_forcing_function",
)
_EXPLICIT_KINDS: frozenset[str] = frozenset({"decision", "implementation", "statement"})
_OPERATOR_BOUNDARY_COMPONENTS: frozenset[str] = frozenset({
    "platform-cli",
    "services-cli",
})
_PATH_VECTOR_PREFIXES: tuple[tuple[str, str], ...] = (
    ("odylith/runtime/contracts/", "contract"),
    ("contracts/", "contract"),
    ("odylith/registry/source/components/", "spec"),
    ("odylith/registry/source/component_registry.v1.json", "contract"),
    ("odylith/runtime/", "runtime"),
    ("odylith/surfaces/", "spec"),
    ("odylith/", "spec"),
    ("docs/runbooks/", "runbook"),
    ("docs/", "doc"),
    ("src/odylith/runtime/surfaces/render_", "renderer"),
    ("src/odylith/runtime/surfaces/watch_", "runtime"),
    ("src/odylith/runtime/common/log_", "runtime"),
    ("src/odylith/runtime/surfaces/update_", "runtime"),
    ("policies/", "policy"),
    (".github/workflows/", "build_ci"),
    ("mk/", "build_ci"),
    ("service-deploy/", "cli"),
)
_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RAW_PATH_RE = operator_readout.RAW_PATH_RE
_LIVE_WORKSTREAM_STATUSES: frozenset[str] = frozenset({"implementation", "active"})
_EXCLUDED_WORKSTREAM_STATUSES: frozenset[str] = frozenset({"queued", "parked"})


def _resolve(repo_root: Path, token: str) -> Path:
    path = Path(str(token or "").strip())
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _normalize_event_artifacts(values: Iterable[str], *, repo_root: Path | None = None) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = workstream_inference.normalize_repo_token(str(raw or "").strip(), repo_root=repo_root)
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _read_markdown_sections(path: Path) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        match = _SECTION_RE.match(raw)
        if match:
            current = str(match.group(1)).strip()
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(raw)
    return {
        title: " ".join(token.strip() for token in lines if token.strip()).strip()
        for title, lines in sections.items()
    }


def _parse_review_date(value: str) -> dt.date | None:
    token = str(value or "").strip()
    if not _DATE_RE.fullmatch(token):
        return None
    try:
        return dt.date.fromisoformat(token)
    except ValueError:
        return None


def _parse_ts(value: str) -> dt.datetime | None:
    token = str(value or "").strip()
    if not token:
        return None
    try:
        return dt.datetime.fromisoformat(token.replace("Z", "+00:00"))
    except ValueError:
        return None


def _scope_key(scope_type: str, scope_id: str) -> str:
    return f"{scope_type}:{scope_id}"


def _humanize_mode(mode: str) -> str:
    token = str(mode or "").strip().replace("_", " ")
    return token.capitalize() if token else "Unknown"


def _join_labels(values: Sequence[str], *, limit: int = 4) -> str:
    rows = [str(item or "").strip() for item in values if str(item or "").strip()]
    if not rows:
        return ""
    if len(rows) > limit:
        rows = [*rows[:limit], f"+{len(values) - limit} more"]
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]} and {rows[1]}"
    return f"{', '.join(rows[:-1])}, and {rows[-1]}"


def _sanitize_narrative_text(value: str) -> str:
    token = str(value or "").replace("`", "").strip()
    if not token:
        return ""
    token = _RAW_PATH_RE.sub("linked artifacts", token)
    token = re.sub(r"\s+", " ", token).strip()
    token = token.replace("linked artifacts +", "linked artifacts plus ")
    return token


def _surface_list_for_scope(
    *,
    workstreams: Sequence[str],
    diagrams: Sequence[str],
    component_ids: Sequence[str],
    include_operator_surface: bool = False,
) -> list[str]:
    rows = ["Registry"]
    if workstreams:
        rows.extend(["Radar", "Compass"])
    if diagrams:
        rows.append("Atlas")
    if include_operator_surface:
        rows.append("Shell")
    rows.append("Shell")
    deduped: list[str] = []
    seen: set[str] = set()
    for token in rows:
        if token not in seen:
            seen.add(token)
            deduped.append(token)
    return deduped


def _change_vector_from_paths(paths: Sequence[str]) -> dict[str, int]:
    vector = {
        "contract": 0,
        "spec": 0,
        "renderer": 0,
        "runtime": 0,
        "policy": 0,
        "runbook": 0,
        "doc": 0,
        "build_ci": 0,
        "cli": 0,
    }
    for raw in paths:
        token = str(raw or "").strip().lower()
        if not token:
            continue
        matched = False
        for prefix, bucket in _PATH_VECTOR_PREFIXES:
            if token.startswith(prefix):
                vector[bucket] += 1
                matched = True
                break
        if matched:
            continue
        if token.endswith(".md"):
            vector["doc"] += 1
        elif token.endswith(".py"):
            vector["runtime"] += 1
    return vector


def _contract_shift_dominant(change_vector: Mapping[str, int]) -> bool:
    """Return ``True`` when contract/spec movement is the dominant delivery signal.

    Shared governance files can lightly touch contracts/specs while the real
    story is renderer/runtime execution or operator-boundary hardening. Treat a
    scope as a contract shift only when contract/spec pressure clearly exceeds
    the implementation pressure around it.
    """

    contract_pressure = int(change_vector.get("contract", 0) or 0) * 4 + int(change_vector.get("spec", 0) or 0) * 3
    execution_pressure = (
        int(change_vector.get("renderer", 0) or 0) * 3
        + int(change_vector.get("runtime", 0) or 0) * 3
        + int(change_vector.get("build_ci", 0) or 0) * 2
        + int(change_vector.get("doc", 0) or 0)
        + int(change_vector.get("runbook", 0) or 0)
    )
    return contract_pressure >= 10 and contract_pressure > execution_pressure


def _blast_radius_class(
    *,
    change_vector: Mapping[str, int],
    linked_surfaces: Sequence[str],
    linked_workstreams: Sequence[str],
    component_ids: Sequence[str],
) -> tuple[str, int]:
    contract_pressure = int(change_vector.get("contract", 0) or 0) * 4 + int(change_vector.get("spec", 0) or 0) * 3
    execution_pressure = (
        int(change_vector.get("renderer", 0) or 0) * 3
        + int(change_vector.get("runtime", 0) or 0) * 3
        + int(change_vector.get("build_ci", 0) or 0) * 2
        + int(change_vector.get("doc", 0) or 0)
        + int(change_vector.get("runbook", 0) or 0)
    )
    operator_boundary_component = any(str(item).strip().lower() in _OPERATOR_BOUNDARY_COMPONENTS for item in component_ids)
    operator_boundary_pressure = int(change_vector.get("policy", 0) or 0) * 4 + int(change_vector.get("cli", 0) or 0) * 4
    if operator_boundary_component and len(set(component_ids)) <= 2:
        return "operator-boundary", 76
    if operator_boundary_pressure >= 8 and operator_boundary_pressure >= contract_pressure and operator_boundary_pressure >= execution_pressure:
        return "operator-boundary", 76
    if _contract_shift_dominant(change_vector):
        return "contract-level", 85
    if len(set(linked_surfaces)) >= 4 or len(set(linked_workstreams)) >= 2:
        return "cross-surface", 58
    return "local", 24


def _evidence_quality(explicit_count: int, synthetic_count: int) -> str:
    if explicit_count > 0 and synthetic_count > 0:
        return "mixed"
    if explicit_count > 0:
        return "explicit"
    if synthetic_count > 0:
        return "inferred"
    return "none"


def _workstream_concentration(events: Sequence[registry.MappedEvent], linked_workstreams: Sequence[str]) -> int:
    counts: dict[str, int] = {}
    for event in events:
        for ws in event.workstreams:
            counts[ws] = int(counts.get(ws, 0) or 0) + 1
    if not counts:
        return 90 if len(set(linked_workstreams)) <= 1 else 50
    total = sum(counts.values())
    dominant = max(counts.values())
    ratio = dominant / total if total else 0
    if ratio >= 0.8:
        return 92
    if ratio >= 0.6:
        return 74
    if ratio >= 0.4:
        return 56
    return 32


def _governance_lag_score(
    *,
    explicit_count: int,
    synthetic_count: int,
    latest_event: registry.MappedEvent | None,
    latest_explicit: registry.MappedEvent | None,
    status: str,
) -> int:
    status_token = str(status or "").strip().lower()
    if explicit_count == 0 and synthetic_count > 0:
        return 88
    if latest_event and latest_event.kind == "workspace_activity" and explicit_count > 0:
        return 64
    if status_token in {"implementation", "finished"} and explicit_count == 0:
        return 82
    if latest_explicit is None and explicit_count == 0:
        return 52
    return 18 if explicit_count > 0 else 36


def _decision_debt_score(
    *,
    decision_count: int,
    implementation_count: int,
    synthetic_count: int,
    explicit_count: int,
) -> int:
    if implementation_count > 0 and decision_count == 0:
        return 86
    if synthetic_count > 0 and explicit_count == 0:
        return 74
    if explicit_count > 0 and implementation_count == 0 and decision_count > 0:
        return 28
    if decision_count > 0 and implementation_count > 0:
        return 16
    return 48 if explicit_count == 0 else 24


def _closure_readiness_score(
    *,
    decision_count: int,
    implementation_count: int,
    linked_surfaces: Sequence[str],
    runbook_count: int,
    doc_count: int,
    fresh_diagrams: bool,
    evidence_quality: str,
    status: str,
) -> int:
    score = 0
    if decision_count > 0:
        score += 24
    if implementation_count > 0:
        score += 24
    if runbook_count > 0 or doc_count > 0:
        score += 14
    if len(set(linked_surfaces)) >= 4:
        score += 14
    if fresh_diagrams:
        score += 12
    if evidence_quality in {"explicit", "mixed"}:
        score += 8
    if str(status or "").strip().lower() == "implementation":
        score += 8
    return max(0, min(100, score))


def _cross_surface_convergence_score(linked_surfaces: Sequence[str], linked_components: Sequence[str], linked_diagrams: Sequence[str]) -> int:
    score = min(100, len(set(linked_surfaces)) * 20 + len(set(linked_components)) * 3 + len(set(linked_diagrams)) * 4)
    return max(8, score)


def _trajectory_for_mode(mode: str) -> str:
    if mode in {"closure_hardening", "operator_boundary_hardening", "contract_shift"}:
        return "hardening"
    if mode in {"converging", "governance_leading_execution"}:
        return "converging"
    if mode in {"fragmenting", "execution_outrunning_governance"}:
        return "drifting"
    return "stalled"


def _confidence_label(evidence_quality: str, governance_lag: int, explicit_count: int) -> str:
    if evidence_quality == "explicit" and governance_lag <= 30 and explicit_count > 0:
        return "High"
    if evidence_quality == "mixed" or explicit_count > 0:
        return "Medium"
    return "Low"


def _classify_mode(
    *,
    scope_type: str,
    scope_id: str,
    status: str,
    explicit_count: int,
    decision_count: int,
    implementation_count: int,
    synthetic_count: int,
    closure_readiness: int,
    governance_lag: int,
    convergence: int,
    concentration: int,
    blast_radius_class: str,
    control_posture: Mapping[str, Any] | None = None,
    change_vector: Mapping[str, int] | None = None,
) -> str:
    change_vector = change_vector or {}
    status_token = str(status or "").strip().lower()
    contract_shift_dominant = _contract_shift_dominant(change_vector)

    if explicit_count == 0 and synthetic_count > 0:
        return "execution_outrunning_governance"
    if decision_count > 0 and implementation_count == 0:
        return "governance_leading_execution"
    if blast_radius_class == "operator-boundary":
        return "operator_boundary_hardening"
    if closure_readiness >= 78 and decision_count > 0 and implementation_count > 0:
        return "closure_hardening"
    if convergence >= 70 and concentration >= 65:
        return "converging"
    if contract_shift_dominant and explicit_count > 0:
        return "contract_shift"
    if convergence >= 55 and concentration < 55:
        return "fragmenting"
    if governance_lag >= 75 and status_token in {"planning", "implementation"}:
        return "execution_outrunning_governance"
    if explicit_count == 0 and synthetic_count == 0 and blast_radius_class in {"operator-boundary", "contract-level"}:
        return "dormant_but_risky"
    return "converging" if explicit_count > 0 else "dormant_but_risky"


def _why_now_text(*, fallback: str, why_now: str, status: str, primary_workstream: str) -> str:
    raw = str(why_now or "").strip()
    if raw:
        return raw
    token = str(status or "").strip().lower()
    if primary_workstream and token:
        return f"{primary_workstream} is currently in {token}, so unresolved governance ambiguity would affect active delivery immediately."
    return fallback


def _narrative_cards(
    *,
    scope_label: str,
    scope_type: str,
    posture_mode: str,
    why_now: str,
    blast_radius: str,
    next_forcing_function: str,
    linked_surfaces: Sequence[str],
    primary_workstream: str,
    evidence_quality: str,
) -> dict[str, str]:
    surfaces = _join_labels(linked_surfaces) or "linked governance surfaces"
    scope_intro = scope_label if scope_type != "surface" else f"{scope_label} surface"
    cards: dict[str, str]
    if posture_mode == "execution_outrunning_governance":
        cards = {
            "executive_thesis": f"{scope_intro} is moving in execution, but the decision trail is not keeping pace.",
            "delivery_tension": "Change signals are present, yet explicit rationale or implementation checkpoints remain thinner than the delivery surface already being touched.",
            "why_now": why_now,
            "blast_radius": f"If this remains implicit, {blast_radius or surfaces} can look aligned while governance stays weaker than the delivery state it is certifying.",
            "next_forcing_function": next_forcing_function or "Capture the explicit checkpoint that binds the current change to its real workstream before treating it as governed progress.",
        }
    elif posture_mode == "governance_leading_execution":
        cards = {
            "executive_thesis": f"{scope_intro} has explicit direction, but execution has not fully caught up yet.",
            "delivery_tension": "The decision trail is stronger than the implementation evidence, which improves control but leaves delivery momentum unproven.",
            "why_now": why_now,
            "blast_radius": f"Downstream interpretation across {blast_radius or surfaces} depends on turning the current rationale into visible implementation movement.",
            "next_forcing_function": next_forcing_function or "Convert the current decision into implementation evidence or reset the scope back to planning truthfully.",
        }
    elif posture_mode == "contract_shift":
        cards = {
            "executive_thesis": f"{scope_intro} is undergoing a contract-level shift that changes how adjacent surfaces read delivery state.",
            "delivery_tension": "Spec and contract movement increase leverage, but they also raise the cost of stale downstream context or ambiguous checkpointing.",
            "why_now": why_now,
            "blast_radius": f"This contract movement reaches across {blast_radius or surfaces} and can change trust in downstream evidence if it is left underspecified.",
            "next_forcing_function": next_forcing_function or "Lock the updated contract and refresh dependent surfaces before wider execution builds on stale assumptions.",
        }
    elif posture_mode == "operator_boundary_hardening":
        cards = {
            "executive_thesis": f"{scope_intro} is hardening an operator boundary rather than shipping isolated implementation detail.",
            "delivery_tension": "Small ambiguities here multiply across approvals, clearance, operator flow, and policy enforcement paths.",
            "why_now": why_now,
            "blast_radius": f"This boundary affects {blast_radius or surfaces}, so weak wording or missing checkpoints propagate operational confusion quickly.",
            "next_forcing_function": next_forcing_function or "Capture the operator boundary explicitly and align the linked control surfaces before treating it as stable.",
        }
    elif posture_mode == "closure_hardening":
        cards = {
            "executive_thesis": f"{scope_intro} is in closure hardening: execution and explicit checkpoints are largely aligned, but the final evidence posture still matters.",
            "delivery_tension": "The main risk is not raw momentum. It is letting closeout outrun the last reviewed checkpoint, clearance pass, or linked-surface refresh.",
            "why_now": why_now,
            "blast_radius": f"Closure confidence for {blast_radius or surfaces} depends on keeping the last explicit evidence synchronized with the apparent finished state.",
            "next_forcing_function": next_forcing_function or "Refresh the final explicit checkpoint and clear linked surfaces before treating this scope as closed.",
        }
    elif posture_mode == "fragmenting":
        cards = {
            "executive_thesis": f"{scope_intro} is spreading across too many linked paths without enough concentration around one forcing function.",
            "delivery_tension": "Activity is present, but the evidence suggests coordination is diffusing instead of tightening around a coherent delivery track.",
            "why_now": why_now,
            "blast_radius": f"Fragmentation increases coordination cost across {blast_radius or surfaces} and makes it harder to trust any one surface as the canonical readout.",
            "next_forcing_function": next_forcing_function or "Re-anchor this scope to one explicit workstream and one explicit checkpoint before additional changes expand the blast radius.",
        }
    elif posture_mode == "dormant_but_risky":
        cards = {
            "executive_thesis": f"{scope_intro} is quiet right now, but its linked blast radius keeps it operationally risky.",
            "delivery_tension": "Low recent signal can hide stale architecture or governance assumptions that still affect active delivery elsewhere.",
            "why_now": why_now,
            "blast_radius": f"Even without recent movement, {blast_radius or surfaces} still depend on this scope staying current and trustworthy.",
            "next_forcing_function": next_forcing_function or "Review freshness and confirm whether this scope can stay dormant safely or needs an explicit refresh.",
        }
    else:
        cards = {
            "executive_thesis": f"{scope_intro} is converging around a coherent delivery track.",
            "delivery_tension": "The primary risk is maintaining alignment as more linked surfaces refresh around the same scope.",
            "why_now": why_now,
            "blast_radius": f"This convergence now shapes {blast_radius or surfaces}, which will only stay trustworthy if explicit evidence continues to lead interpretation.",
            "next_forcing_function": next_forcing_function or "Preserve explicit checkpoints as the scope moves so convergence does not degrade back into inferred status.",
        }

    if evidence_quality == "inferred":
        cards["delivery_tension"] = f"{cards['delivery_tension']} Right now the signal is still inferred more than explicitly logged."
    return {
        key: _sanitize_narrative_text(cards[key])
        for key in _CARD_KEYS
    }


def _summarize_blast_radius(
    *,
    linked_surfaces: Sequence[str],
    linked_workstreams: Sequence[str],
    linked_components: Sequence[str],
    linked_diagrams: Sequence[str],
) -> str:
    parts: list[str] = []
    if linked_workstreams:
        parts.append(f"workstreams {_join_labels(linked_workstreams, limit=3)}")
    if linked_components:
        parts.append(f"components {_join_labels(linked_components, limit=4)}")
    if linked_diagrams:
        parts.append(f"Atlas diagrams {_join_labels(linked_diagrams, limit=3)}")
    if linked_surfaces:
        parts.append(f"surfaces {_join_labels(linked_surfaces, limit=4)}")
    return _join_labels(parts, limit=4)


def _next_forcing_function(
    *,
    posture_mode: str,
    primary_workstream: str,
    scope_type: str,
    scope_label: str,
) -> str:
    scope_phrase = primary_workstream or scope_label
    if posture_mode == "execution_outrunning_governance":
        return f"Log the explicit Compass checkpoint that binds {scope_phrase} to the current change before calling it governed progress."
    if posture_mode == "governance_leading_execution":
        return f"Turn the current rationale for {scope_phrase} into implementation evidence or keep the scope explicitly in planning."
    if posture_mode == "contract_shift":
        return f"Refresh the contract-adjacent surfaces around {scope_phrase} before additional execution assumes the new boundary is settled."
    if posture_mode == "operator_boundary_hardening":
        return f"Capture the operator boundary for {scope_phrase} explicitly and align approval and clearance semantics across the control surfaces."
    if posture_mode == "closure_hardening":
        return f"Capture the final reviewed checkpoint for {scope_phrase} and clear linked surfaces before closeout."
    if posture_mode == "fragmenting":
        return f"Re-concentrate {scope_phrase} onto one explicit workstream and one next checkpoint before more scope fans out."
    if posture_mode == "dormant_but_risky":
        return f"Decide whether {scope_phrase} needs an explicit refresh or can remain safely dormant without misleading adjacent surfaces."
    return f"Keep explicit checkpoints current as {scope_phrase} continues to converge across linked surfaces."


def _build_evidence_refs(
    *,
    linked_workstreams: Sequence[str],
    linked_components: Sequence[str],
    linked_diagrams: Sequence[str],
    linked_paths: Sequence[str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for token in linked_workstreams[:4]:
        rows.append({"kind": "workstream", "value": token, "label": token})
    for token in linked_components[:6]:
        rows.append({"kind": "component", "value": token, "label": token})
    for token in linked_diagrams[:4]:
        rows.append({"kind": "diagram", "value": token, "label": token})
    for token in linked_paths[:6]:
        rows.append({"kind": "path", "value": token, "label": token})
    return rows


def _snapshot_dict(
    *,
    scope_type: str,
    scope_id: str,
    scope_label: str,
    posture_mode: str,
    trajectory: str,
    confidence: str,
    cards: Mapping[str, str],
    evidence_context: Mapping[str, Any],
    explanation_facts: Sequence[str],
    evidence_refs: Sequence[Mapping[str, str]],
    scores: Mapping[str, int],
    change_vector: Mapping[str, int],
    diagnostics: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "scope_key": _scope_key(scope_type, scope_id),
        "scope_type": scope_type,
        "scope_id": scope_id,
        "scope_label": scope_label,
        "posture_mode": posture_mode,
        "trajectory": trajectory,
        "confidence": confidence,
        "cards": {key: str(cards.get(key, "")).strip() for key in _CARD_KEYS},
        "evidence_context": dict(evidence_context),
        "explanation_facts": [str(item).strip() for item in explanation_facts if str(item).strip()],
        "evidence_refs": [operator_readout.normalize_proof_ref(item) for item in evidence_refs],
        "scores": {key: int(value) for key, value in scores.items()},
        "change_vector": {key: int(value) for key, value in change_vector.items()},
        "diagnostics": dict(diagnostics),
    }


def _load_workstream_contexts(*, ideas_root: Path) -> dict[str, dict[str, Any]]:
    specs, _errors = backlog_contract._validate_idea_specs(ideas_root)
    rows: dict[str, dict[str, Any]] = {}
    for idea_id, spec in specs.items():
        token = registry.normalize_workstream_id(idea_id)
        if not token:
            continue
        sections = _read_markdown_sections(spec.path)
        rows[token] = {
            "idea_id": token,
            "title": str(spec.metadata.get("title", "")).strip() or token,
            "status": str(spec.metadata.get("status", "")).strip().lower(),
            "idea_file": spec.path,
            "why_now": sections.get("Why Now", ""),
            "opportunity": sections.get("Opportunity", ""),
            "founder_pov": sections.get("Product View", sections.get("Founder POV", "")),
        }
    return rows


def _load_catalog(*, repo_root: Path, catalog_path: Path) -> list[dict[str, Any]]:
    payload = _read_json(catalog_path)
    rows = payload.get("diagrams", []) if isinstance(payload.get("diagrams"), list) else []
    cleaned: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, Mapping):
            cleaned.append(dict(row))
    return cleaned


def _load_traceability_rows(*, repo_root: Path, path: Path) -> dict[str, dict[str, Any]]:
    payload = _read_json(path)
    rows = payload.get("workstreams", []) if isinstance(payload.get("workstreams"), list) else []
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        ws_id = registry.normalize_workstream_id(str(row.get("idea_id", "")))
        if not ws_id:
            continue
        result[ws_id] = dict(row)
    return result


def _normalized_workstream_tokens(value: Any) -> set[str]:
    raw_values = value
    if isinstance(raw_values, str):
        raw_values = [token.strip() for token in raw_values.replace(";", ",").split(",") if token.strip()]
    if not isinstance(raw_values, list):
        return set()
    rows: set[str] = set()
    for raw in raw_values:
        token = registry.normalize_workstream_id(str(raw))
        if token:
            rows.add(token)
    return rows


def _successor_workstream_ids(traceability_row: Mapping[str, Any]) -> set[str]:
    rows: set[str] = set()
    for field in ("workstream_reopened_by", "superseded_by", "workstream_merged_into", "workstream_parent"):
        token = registry.normalize_workstream_id(str(traceability_row.get(field, "")))
        if token:
            rows.add(token)
    for field in ("workstream_children", "workstream_split_into"):
        rows.update(_normalized_workstream_tokens(traceability_row.get(field, [])))
    return rows


def _event_outruns_explicit(
    event: registry.MappedEvent | None,
    latest_explicit: registry.MappedEvent | None,
) -> bool:
    if event is None:
        return False
    latest_event_ts = _parse_ts(str(event.ts_iso))
    if latest_event_ts is None:
        return False
    if latest_explicit is None:
        return True
    latest_explicit_ts = _parse_ts(str(latest_explicit.ts_iso))
    if latest_explicit_ts is None:
        return True
    return latest_event_ts > latest_explicit_ts


def _classify_workstream_event_attribution(
    *,
    workstream_id: str,
    successor_workstreams: set[str],
    linked_component_ids: set[str],
    event: registry.MappedEvent,
) -> str:
    event_workstreams = {
        token
        for raw in event.workstreams
        if (token := registry.normalize_workstream_id(str(raw)))
    }
    if workstream_id in event_workstreams:
        return "direct_workstream"
    if successor_workstreams and event_workstreams & successor_workstreams:
        return "successor_lineage"
    if event_workstreams:
        return "other_workstream"
    event_components = {str(token).strip() for token in event.mapped_components if str(token).strip()}
    if event_components & linked_component_ids:
        return "shared_component_only"
    return ""


def _fresh_diagrams_for_scope(diagrams: Sequence[dict[str, Any]], *, max_review_age_days: int) -> bool:
    if not diagrams:
        return False
    today = dt.date.today()
    for row in diagrams:
        reviewed = _parse_review_date(str(row.get("last_reviewed_utc", "")))
        if reviewed is None:
            return False
        if (today - reviewed).days > max_review_age_days:
            return False
    return True


def _build_component_snapshot(
    *,
    repo_root: Path,
    component_id: str,
    entry: registry.ComponentEntry,
    timeline: Sequence[registry.MappedEvent],
    traceability: Mapping[str, Sequence[str]],
    max_review_age_days: int,
    diagram_rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    explicit_events = [event for event in timeline if event.kind in _EXPLICIT_KINDS]
    synthetic_events = [event for event in timeline if event.kind == "workspace_activity"]
    decision_count = sum(1 for event in explicit_events if event.kind == "decision")
    implementation_count = sum(1 for event in explicit_events if event.kind == "implementation")
    latest_event = timeline[0] if timeline else None
    latest_explicit = explicit_events[0] if explicit_events else None
    linked_workstreams = list(entry.workstreams)
    linked_diagrams = list(entry.diagrams)
    linked_components = [component_id]
    linked_surfaces = _surface_list_for_scope(
        workstreams=linked_workstreams,
        diagrams=linked_diagrams,
        component_ids=[component_id],
        include_operator_surface=False,
    )
    linked_paths = _normalize_event_artifacts(
        [*(event.artifacts for event in timeline)] if False else [],
        repo_root=repo_root,
    )
    # Flatten event artifacts after stable dedupe.
    flattened_paths = _normalize_event_artifacts(
        [artifact for event in timeline for artifact in event.artifacts],
        repo_root=repo_root,
    )
    change_vector = _change_vector_from_paths([*flattened_paths, entry.spec_ref, *traceability.get("code_references", [])])
    blast_radius_class, blast_radius_severity = _blast_radius_class(
        change_vector=change_vector,
        linked_surfaces=linked_surfaces,
        linked_workstreams=linked_workstreams,
        component_ids=[component_id],
    )
    evidence_quality = _evidence_quality(len(explicit_events), len(synthetic_events))
    runbook_count = len(traceability.get("runbooks", []))
    doc_count = len(traceability.get("developer_docs", []))
    fresh_diagrams = _fresh_diagrams_for_scope(diagram_rows, max_review_age_days=max_review_age_days)
    governance_lag = _governance_lag_score(
        explicit_count=len(explicit_events),
        synthetic_count=len(synthetic_events),
        latest_event=latest_event,
        latest_explicit=latest_explicit,
        status=entry.status,
    )
    decision_debt = _decision_debt_score(
        decision_count=decision_count,
        implementation_count=implementation_count,
        synthetic_count=len(synthetic_events),
        explicit_count=len(explicit_events),
    )
    concentration = _workstream_concentration(timeline, linked_workstreams)
    convergence = _cross_surface_convergence_score(
        linked_surfaces=linked_surfaces,
        linked_components=linked_components,
        linked_diagrams=linked_diagrams,
    )
    closure_readiness = _closure_readiness_score(
        decision_count=decision_count,
        implementation_count=implementation_count,
        linked_surfaces=linked_surfaces,
        runbook_count=runbook_count,
        doc_count=doc_count,
        fresh_diagrams=fresh_diagrams,
        evidence_quality=evidence_quality,
        status=entry.status,
    )
    posture_mode = _classify_mode(
        scope_type="component",
        scope_id=component_id,
        status=entry.status,
        explicit_count=len(explicit_events),
        decision_count=decision_count,
        implementation_count=implementation_count,
        synthetic_count=len(synthetic_events),
        closure_readiness=closure_readiness,
        governance_lag=governance_lag,
        convergence=convergence,
        concentration=concentration,
        blast_radius_class=blast_radius_class,
        change_vector=change_vector,
    )
    next_move = _next_forcing_function(
        posture_mode=posture_mode,
        primary_workstream=linked_workstreams[0] if linked_workstreams else "",
        scope_type="component",
        scope_label=entry.name or component_id,
    )
    blast_radius = _summarize_blast_radius(
        linked_surfaces=linked_surfaces,
        linked_workstreams=linked_workstreams,
        linked_components=[],
        linked_diagrams=linked_diagrams,
    )
    cards = _narrative_cards(
        scope_label=entry.name or component_id,
        scope_type="component",
        posture_mode=posture_mode,
        why_now=_why_now_text(
            fallback="This matters now because component-level narrative truth is what keeps Registry, Radar, Atlas, Compass, and the shell aligned.",
            why_now="",
            status=entry.status,
            primary_workstream=linked_workstreams[0] if linked_workstreams else "",
        ),
        blast_radius=blast_radius,
        next_forcing_function=next_move,
        linked_surfaces=linked_surfaces,
        primary_workstream=linked_workstreams[0] if linked_workstreams else "",
        evidence_quality=evidence_quality,
    )
    explanation_facts = [
        f"Evidence quality is {evidence_quality}.",
        f"Blast radius class is {blast_radius_class}.",
        f"Linked surfaces: {_join_labels(linked_surfaces)}.",
        f"Linked workstreams: {_join_labels(linked_workstreams) or 'none'}.",
        f"Traceability coverage includes {runbook_count} runbook(s) and {doc_count} developer doc(s).",
    ]
    evidence_context = {
        "basis": evidence_quality,
        "freshness": "current" if latest_event else "quiet",
        "latest_event_ts_iso": str(latest_event.ts_iso if latest_event else ""),
        "latest_signal_kind": str(latest_event.kind if latest_event else ""),
        "latest_explicit_ts_iso": str(latest_explicit.ts_iso if latest_explicit else ""),
        "linked_workstreams": linked_workstreams,
        "linked_components": linked_components,
        "linked_diagrams": linked_diagrams,
        "linked_surfaces": linked_surfaces,
        "blast_radius_class": blast_radius_class,
    }
    return _snapshot_dict(
        scope_type="component",
        scope_id=component_id,
        scope_label=entry.name or component_id,
        posture_mode=posture_mode,
        trajectory=_trajectory_for_mode(posture_mode),
        confidence=_confidence_label(evidence_quality, governance_lag, len(explicit_events)),
        cards=cards,
        evidence_context=evidence_context,
        explanation_facts=explanation_facts,
        evidence_refs=_build_evidence_refs(
            linked_workstreams=linked_workstreams,
            linked_components=[component_id],
            linked_diagrams=linked_diagrams,
            linked_paths=[entry.spec_ref, *traceability.get("runbooks", []), *traceability.get("developer_docs", [])],
        ),
        scores={
            "governance_lag": governance_lag,
            "decision_debt": decision_debt,
            "closure_readiness": closure_readiness,
            "cross_surface_convergence": convergence,
            "workstream_concentration": concentration,
            "blast_radius_severity": blast_radius_severity,
        },
        change_vector=change_vector,
        diagnostics={
            "status": str(entry.status or "").strip().lower(),
            "explicit_count": len(explicit_events),
            "decision_count": decision_count,
            "implementation_count": implementation_count,
            "synthetic_count": len(synthetic_events),
            "fresh_diagrams": fresh_diagrams,
            "runbook_count": runbook_count,
            "developer_doc_count": doc_count,
            "blast_radius_class": blast_radius_class,
        },
    )


def _build_workstream_snapshot(
    *,
    repo_root: Path,
    workstream_id: str,
    context: Mapping[str, Any],
    traceability_row: Mapping[str, Any],
    components: Mapping[str, registry.ComponentEntry],
    mapped_events: Sequence[registry.MappedEvent],
    component_traceability: Mapping[str, Mapping[str, Sequence[str]]],
    max_review_age_days: int,
    diagrams_by_id: Mapping[str, dict[str, Any]],
) -> dict[str, Any]:
    linked_components = registry.component_ids_for_workstream(components=components, workstream_id=workstream_id)
    linked_component_ids = set(linked_components)
    successor_workstreams = sorted(_successor_workstream_ids(traceability_row))
    successor_workstream_ids = set(successor_workstreams)
    related_diagrams = [
        token for token in traceability_row.get("related_diagram_ids", [])
        if registry.normalize_diagram_id(str(token))
    ]
    if not related_diagrams:
        for component_id in linked_components:
            entry = components.get(component_id)
            if entry is not None:
                related_diagrams.extend(entry.diagrams)
    related_diagrams = [token for token in dict.fromkeys(related_diagrams)]
    explicit_events: list[tuple[registry.MappedEvent, str]] = []
    synthetic_events: list[tuple[registry.MappedEvent, str]] = []
    for event in mapped_events:
        attribution = _classify_workstream_event_attribution(
            workstream_id=workstream_id,
            successor_workstreams=successor_workstream_ids,
            linked_component_ids=linked_component_ids,
            event=event,
        )
        if not attribution:
            continue
        if event.kind == "workspace_activity":
            synthetic_events.append((event, attribution))
        elif event.kind in _EXPLICIT_KINDS:
            explicit_events.append((event, attribution))
    explicit_events.sort(key=lambda row: (row[0].ts_iso, row[0].event_index), reverse=True)
    synthetic_events.sort(key=lambda row: (row[0].ts_iso, row[0].event_index), reverse=True)
    all_events = sorted([*explicit_events, *synthetic_events], key=lambda row: (row[0].ts_iso, row[0].event_index), reverse=True)
    latest_event, latest_event_attribution = all_events[0] if all_events else (None, "")
    latest_explicit = explicit_events[0][0] if explicit_events else None
    latest_direct_event = next((event for event, attribution in all_events if attribution == "direct_workstream"), None)
    decision_count = sum(1 for event, _attribution in explicit_events if event.kind == "decision")
    implementation_count = sum(1 for event, _attribution in explicit_events if event.kind == "implementation")
    direct_event_count = sum(1 for _event, attribution in all_events if attribution == "direct_workstream")
    successor_event_count = sum(1 for _event, attribution in all_events if attribution == "successor_lineage")
    other_workstream_event_count = sum(1 for _event, attribution in all_events if attribution == "other_workstream")
    shared_component_event_count = sum(1 for _event, attribution in all_events if attribution == "shared_component_only")
    closeout_signal = "none"
    if _event_outruns_explicit(latest_direct_event, latest_explicit):
        closeout_signal = "direct_activity_drift"
    elif _event_outruns_explicit(latest_event, latest_explicit):
        if latest_event_attribution == "successor_lineage":
            closeout_signal = "suppressed_successor_lineage"
        elif latest_event_attribution == "other_workstream":
            closeout_signal = "suppressed_other_workstream"
        elif latest_event_attribution == "shared_component_only":
            closeout_signal = "suppressed_shared_component_only"
    linked_surfaces = _surface_list_for_scope(
        workstreams=[workstream_id],
        diagrams=related_diagrams,
        component_ids=linked_components,
        include_operator_surface=("shell" in linked_components),
    )
    trace = traceability_row.get("plan_traceability", {}) if isinstance(traceability_row.get("plan_traceability"), Mapping) else {}
    runbook_count = len(trace.get("runbooks", [])) if isinstance(trace.get("runbooks"), list) else 0
    doc_count = len(trace.get("developer_docs", [])) if isinstance(trace.get("developer_docs"), list) else 0
    coverage = traceability_row.get("coverage", {}) if isinstance(traceability_row.get("coverage"), Mapping) else {}
    fresh_diagrams = _fresh_diagrams_for_scope(
        [diagrams_by_id[diagram_id] for diagram_id in related_diagrams if diagram_id in diagrams_by_id],
        max_review_age_days=max_review_age_days,
    )
    trace_code_references = [
        workstream_inference.normalize_repo_token(str(token).strip(), repo_root=repo_root)
        for token in trace.get("code_references", [])
        if isinstance(trace.get("code_references"), list) and str(token).strip()
    ]
    change_paths = [artifact for event, _attribution in all_events for artifact in event.artifacts]
    change_paths.extend(trace_code_references)
    changed_artifacts = _normalize_event_artifacts(change_paths, repo_root=repo_root)
    change_vector = _change_vector_from_paths(change_paths)
    blast_radius_class, blast_radius_severity = _blast_radius_class(
        change_vector=change_vector,
        linked_surfaces=linked_surfaces,
        linked_workstreams=[workstream_id],
        component_ids=linked_components,
    )
    evidence_quality = _evidence_quality(len(explicit_events), len(synthetic_events))
    governance_lag = _governance_lag_score(
        explicit_count=len(explicit_events),
        synthetic_count=len(synthetic_events),
        latest_event=latest_event,
        latest_explicit=latest_explicit,
        status=str(context.get("status", "")),
    )
    decision_debt = _decision_debt_score(
        decision_count=decision_count,
        implementation_count=implementation_count,
        synthetic_count=len(synthetic_events),
        explicit_count=len(explicit_events),
    )
    concentration = _workstream_concentration([event for event, _attribution in all_events], [workstream_id])
    convergence = _cross_surface_convergence_score(
        linked_surfaces=linked_surfaces,
        linked_components=linked_components,
        linked_diagrams=related_diagrams,
    )
    closure_readiness = _closure_readiness_score(
        decision_count=decision_count,
        implementation_count=implementation_count,
        linked_surfaces=linked_surfaces,
        runbook_count=runbook_count,
        doc_count=doc_count,
        fresh_diagrams=fresh_diagrams,
        evidence_quality=evidence_quality,
        status=str(context.get("status", "")),
    )
    posture_mode = _classify_mode(
        scope_type="workstream",
        scope_id=workstream_id,
        status=str(context.get("status", "")),
        explicit_count=len(explicit_events),
        decision_count=decision_count,
        implementation_count=implementation_count,
        synthetic_count=len(synthetic_events),
        closure_readiness=closure_readiness,
        governance_lag=governance_lag,
        convergence=convergence,
        concentration=concentration,
        blast_radius_class=blast_radius_class,
        change_vector=change_vector,
    )
    next_move = _next_forcing_function(
        posture_mode=posture_mode,
        primary_workstream=workstream_id,
        scope_type="workstream",
        scope_label=str(context.get("title", workstream_id)),
    )
    blast_radius = _summarize_blast_radius(
        linked_surfaces=linked_surfaces,
        linked_workstreams=[workstream_id],
        linked_components=linked_components,
        linked_diagrams=related_diagrams,
    )
    cards = _narrative_cards(
        scope_label=str(context.get("title", workstream_id)),
        scope_type="workstream",
        posture_mode=posture_mode,
        why_now=_why_now_text(
            fallback="This matters now because active delivery is already reading this workstream through multiple governance surfaces.",
            why_now=str(context.get("why_now", "")),
            status=str(context.get("status", "")),
            primary_workstream=workstream_id,
        ),
        blast_radius=blast_radius,
        next_forcing_function=next_move,
        linked_surfaces=linked_surfaces,
        primary_workstream=workstream_id,
        evidence_quality=evidence_quality,
    )
    explanation_facts = [
        f"Status is {str(context.get('status', 'unknown')).strip() or 'unknown'}.",
        f"Evidence quality is {evidence_quality}.",
        f"Linked components: {_join_labels(linked_components) or 'none'}.",
        f"Lineage successors: {_join_labels(successor_workstreams) or 'none'}.",
        f"Linked diagrams: {_join_labels(related_diagrams) or 'none'}.",
        f"Traceability coverage includes {int(coverage.get('runbook_count', runbook_count) or runbook_count)} runbook(s), {int(coverage.get('developer_doc_count', doc_count) or doc_count)} developer doc(s), and {int(coverage.get('code_reference_count', 0) or 0)} code reference(s).",
    ]
    evidence_context = {
        "basis": evidence_quality,
        "freshness": "current" if latest_event else "quiet",
        "latest_event_ts_iso": str(latest_event.ts_iso if latest_event else ""),
        "latest_signal_kind": str(latest_event.kind if latest_event else ""),
        "latest_event_attribution": latest_event_attribution,
        "latest_explicit_ts_iso": str(latest_explicit.ts_iso if latest_explicit else ""),
        "latest_direct_event_ts_iso": str(latest_direct_event.ts_iso if latest_direct_event else ""),
        "linked_workstreams": [workstream_id],
        "successor_workstreams": successor_workstreams,
        "linked_components": linked_components,
        "linked_diagrams": related_diagrams,
        "linked_surfaces": linked_surfaces,
        "blast_radius_class": blast_radius_class,
        "code_references": trace_code_references,
        "changed_artifacts": changed_artifacts,
    }
    return _snapshot_dict(
        scope_type="workstream",
        scope_id=workstream_id,
        scope_label=str(context.get("title", workstream_id)),
        posture_mode=posture_mode,
        trajectory=_trajectory_for_mode(posture_mode),
        confidence=_confidence_label(evidence_quality, governance_lag, len(explicit_events)),
        cards=cards,
        evidence_context=evidence_context,
        explanation_facts=explanation_facts,
        evidence_refs=_build_evidence_refs(
            linked_workstreams=[workstream_id],
            linked_components=linked_components,
            linked_diagrams=related_diagrams,
            linked_paths=[str(context.get("idea_file", "")), *trace.get("runbooks", []), *trace.get("developer_docs", [])],
        ),
        scores={
            "governance_lag": governance_lag,
            "decision_debt": decision_debt,
            "closure_readiness": closure_readiness,
            "cross_surface_convergence": convergence,
            "workstream_concentration": concentration,
            "blast_radius_severity": blast_radius_severity,
        },
        change_vector=change_vector,
        diagnostics={
            "status": str(context.get("status", "")).strip().lower(),
            "idea_file": str(context.get("idea_file", "")).strip(),
            "plan_path": workstream_inference.normalize_repo_token(
                str(traceability_row.get("promoted_to_plan", "") or traceability_row.get("plan_path", "")).strip(),
                repo_root=repo_root,
            ),
            "explicit_count": len(explicit_events),
            "decision_count": decision_count,
            "implementation_count": implementation_count,
            "synthetic_count": len(synthetic_events),
            "fresh_diagrams": fresh_diagrams,
            "runbook_count": runbook_count,
            "developer_doc_count": doc_count,
            "blast_radius_class": blast_radius_class,
            "closeout_signal": closeout_signal,
            "latest_event_attribution": latest_event_attribution,
            "direct_event_count": direct_event_count,
            "successor_event_count": successor_event_count,
            "other_workstream_event_count": other_workstream_event_count,
            "shared_component_event_count": shared_component_event_count,
            "render_drift": blast_radius_class == "localized" and change_vector.get("renderer", 0) > 0 and change_vector.get("runtime", 0) == 0,
        },
    )


def _build_diagram_snapshot(
    *,
    row: Mapping[str, Any],
    components: Mapping[str, registry.ComponentEntry],
    mapped_events: Sequence[registry.MappedEvent],
    max_review_age_days: int,
) -> dict[str, Any]:
    diagram_id = registry.normalize_diagram_id(str(row.get("diagram_id", "")))
    component_ids = []
    for component_row in row.get("components", []) if isinstance(row.get("components"), list) else []:
        if not isinstance(component_row, Mapping):
            continue
        component_id = registry.component_id_for_token(
            token=str(component_row.get("name", "")),
            components=components,
        )
        if component_id:
            component_ids.append(component_id)
    component_ids = list(dict.fromkeys(component_ids))
    linked_workstreams = [
        registry.normalize_workstream_id(token)
        for token in row.get("related_workstreams", [])
        if registry.normalize_workstream_id(str(token))
    ]
    linked_workstreams = [token for token in linked_workstreams if token]
    linked_surfaces = _surface_list_for_scope(
        workstreams=linked_workstreams,
        diagrams=[diagram_id],
        component_ids=component_ids,
        include_operator_surface=("shell" in component_ids),
    )
    explicit_events: list[registry.MappedEvent] = []
    synthetic_events: list[registry.MappedEvent] = []
    component_id_set = set(component_ids)
    workstream_set = set(linked_workstreams)
    for event in mapped_events:
        event_components = {str(token).strip() for token in event.mapped_components}
        event_workstreams = {registry.normalize_workstream_id(token) for token in event.workstreams}
        if event_components & component_id_set or event_workstreams & workstream_set:
            if event.kind == "workspace_activity":
                synthetic_events.append(event)
            elif event.kind in _EXPLICIT_KINDS:
                explicit_events.append(event)
    all_events = sorted([*explicit_events, *synthetic_events], key=lambda row: (row.ts_iso, row.event_index), reverse=True)
    latest_event = all_events[0] if all_events else None
    latest_explicit = explicit_events[0] if explicit_events else None
    decision_count = sum(1 for event in explicit_events if event.kind == "decision")
    implementation_count = sum(1 for event in explicit_events if event.kind == "implementation")
    reviewed = _parse_review_date(str(row.get("last_reviewed_utc", "")))
    stale = reviewed is None or (dt.date.today() - reviewed).days > max_review_age_days
    change_vector = _change_vector_from_paths([
        str(row.get("source_mmd", "")),
        *row.get("change_watch_paths", []),
        *row.get("related_code", []),
        *row.get("related_docs", []),
    ])
    blast_radius_class, blast_radius_severity = _blast_radius_class(
        change_vector=change_vector,
        linked_surfaces=linked_surfaces,
        linked_workstreams=linked_workstreams,
        component_ids=component_ids,
    )
    evidence_quality = _evidence_quality(len(explicit_events), len(synthetic_events))
    governance_lag = _governance_lag_score(
        explicit_count=len(explicit_events),
        synthetic_count=len(synthetic_events),
        latest_event=latest_event,
        latest_explicit=latest_explicit,
        status="stale" if stale else "active",
    )
    decision_debt = _decision_debt_score(
        decision_count=decision_count,
        implementation_count=implementation_count,
        synthetic_count=len(synthetic_events),
        explicit_count=len(explicit_events),
    )
    concentration = _workstream_concentration(all_events, linked_workstreams)
    convergence = _cross_surface_convergence_score(
        linked_surfaces=linked_surfaces,
        linked_components=component_ids,
        linked_diagrams=[diagram_id],
    )
    closure_readiness = _closure_readiness_score(
        decision_count=decision_count,
        implementation_count=implementation_count,
        linked_surfaces=linked_surfaces,
        runbook_count=0,
        doc_count=len(row.get("related_docs", [])) if isinstance(row.get("related_docs"), list) else 0,
        fresh_diagrams=not stale,
        evidence_quality=evidence_quality,
        status="active",
    )
    posture_mode = "dormant_but_risky" if stale and not explicit_events else _classify_mode(
        scope_type="diagram",
        scope_id=diagram_id,
        status="active",
        explicit_count=len(explicit_events),
        decision_count=decision_count,
        implementation_count=implementation_count,
        synthetic_count=len(synthetic_events),
        closure_readiness=closure_readiness,
        governance_lag=governance_lag,
        convergence=convergence,
        concentration=concentration,
        blast_radius_class=blast_radius_class,
        change_vector=change_vector,
    )
    next_move = _next_forcing_function(
        posture_mode=posture_mode,
        primary_workstream=linked_workstreams[0] if linked_workstreams else diagram_id,
        scope_type="diagram",
        scope_label=str(row.get("title", diagram_id)),
    )
    why_now = f"Architecture context for {diagram_id} is {'stale' if stale else 'fresh'}, so Atlas is either reinforcing or eroding trust in the delivery story operators are reading elsewhere."
    blast_radius = _summarize_blast_radius(
        linked_surfaces=linked_surfaces,
        linked_workstreams=linked_workstreams,
        linked_components=component_ids,
        linked_diagrams=[diagram_id],
    )
    cards = _narrative_cards(
        scope_label=str(row.get("title", diagram_id)),
        scope_type="diagram",
        posture_mode=posture_mode,
        why_now=why_now,
        blast_radius=blast_radius,
        next_forcing_function=next_move,
        linked_surfaces=linked_surfaces,
        primary_workstream=linked_workstreams[0] if linked_workstreams else "",
        evidence_quality=evidence_quality,
    )
    explanation_facts = [
        f"Atlas freshness is {'stale' if stale else 'fresh'}.",
        f"Linked components: {_join_labels(component_ids) or 'none'}.",
        f"Linked workstreams: {_join_labels(linked_workstreams) or 'none'}.",
        f"Evidence quality is {evidence_quality}.",
    ]
    evidence_context = {
        "basis": evidence_quality,
        "freshness": "stale" if stale else "fresh",
        "latest_event_ts_iso": str(latest_event.ts_iso if latest_event else ""),
        "latest_signal_kind": str(latest_event.kind if latest_event else ""),
        "latest_explicit_ts_iso": str(latest_explicit.ts_iso if latest_explicit else ""),
        "linked_workstreams": linked_workstreams,
        "linked_components": component_ids,
        "linked_diagrams": [diagram_id],
        "linked_surfaces": linked_surfaces,
        "blast_radius_class": blast_radius_class,
    }
    return _snapshot_dict(
        scope_type="diagram",
        scope_id=diagram_id,
        scope_label=str(row.get("title", diagram_id)),
        posture_mode=posture_mode,
        trajectory=_trajectory_for_mode(posture_mode),
        confidence=_confidence_label(evidence_quality, governance_lag, len(explicit_events)),
        cards=cards,
        evidence_context=evidence_context,
        explanation_facts=explanation_facts,
        evidence_refs=_build_evidence_refs(
            linked_workstreams=linked_workstreams,
            linked_components=component_ids,
            linked_diagrams=[diagram_id],
            linked_paths=[str(row.get("source_mmd", "")), *row.get("related_docs", []), *row.get("related_code", [])],
        ),
        scores={
            "governance_lag": governance_lag,
            "decision_debt": decision_debt,
            "closure_readiness": closure_readiness,
            "cross_surface_convergence": convergence,
            "workstream_concentration": concentration,
            "blast_radius_severity": blast_radius_severity,
        },
        change_vector=change_vector,
        diagnostics={
            "status": "active",
            "explicit_count": len(explicit_events),
            "decision_count": decision_count,
            "implementation_count": implementation_count,
            "synthetic_count": len(synthetic_events),
            "fresh_diagrams": not stale,
            "stale_diagram": stale,
            "blast_radius_class": blast_radius_class,
        },
    )


def _aggregate_scope(
    *,
    scope_type: str,
    scope_id: str,
    scope_label: str,
    child_snapshots: Sequence[Mapping[str, Any]],
    control_posture: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not child_snapshots:
        linked_surfaces = [scope_label] if scope_type == "surface" else ["Shell"]
        cards = _narrative_cards(
            scope_label=scope_label,
            scope_type=scope_type,
            posture_mode="dormant_but_risky",
            why_now=f"{scope_label} has too little current evidence to claim strong posture yet.",
            blast_radius=scope_label,
            next_forcing_function=f"Rebuild explicit evidence for {scope_label} before treating the surface as strongly governed.",
            linked_surfaces=linked_surfaces,
            primary_workstream="",
            evidence_quality="none",
        )
        return _snapshot_dict(
            scope_type=scope_type,
            scope_id=scope_id,
            scope_label=scope_label,
            posture_mode="dormant_but_risky",
            trajectory="stalled",
            confidence="Low",
            cards=cards,
            evidence_context={
                "basis": "none",
                "freshness": "quiet",
                "linked_workstreams": [],
                "linked_components": [],
                "linked_diagrams": [],
                "linked_surfaces": linked_surfaces,
                "blast_radius_class": "local",
            },
            explanation_facts=["No child scopes were available for aggregation."],
            evidence_refs=[],
            scores={
                "governance_lag": 50,
                "decision_debt": 40,
                "closure_readiness": 0,
                "cross_surface_convergence": 10,
                "workstream_concentration": 10,
                "blast_radius_severity": 24,
            },
            change_vector={
                "contract": 0,
                "spec": 0,
                "renderer": 0,
                "runtime": 0,
                "policy": 0,
                "runbook": 0,
                "doc": 0,
                "build_ci": 0,
                "cli": 0,
            },
            diagnostics={
                "status": "quiet",
                "explicit_count": 0,
                "decision_count": 0,
                "implementation_count": 0,
                "synthetic_count": 0,
                "blast_radius_class": "local",
            },
        )

    def _avg(score_key: str) -> int:
        values = [int(snapshot.get("scores", {}).get(score_key, 0) or 0) for snapshot in child_snapshots]
        return int(sum(values) / len(values)) if values else 0

    linked_workstreams = list(dict.fromkeys(
        token
        for snapshot in child_snapshots
        for token in snapshot.get("evidence_context", {}).get("linked_workstreams", [])
    ))
    linked_components = list(dict.fromkeys(
        token
        for snapshot in child_snapshots
        for token in snapshot.get("evidence_context", {}).get("linked_components", [])
    ))
    linked_diagrams = list(dict.fromkeys(
        token
        for snapshot in child_snapshots
        for token in snapshot.get("evidence_context", {}).get("linked_diagrams", [])
    ))
    linked_surfaces = list(dict.fromkeys(
        token
        for snapshot in child_snapshots
        for token in snapshot.get("evidence_context", {}).get("linked_surfaces", [])
    ))
    governance_lag = _avg("governance_lag")
    decision_debt = _avg("decision_debt")
    closure_readiness = _avg("closure_readiness")
    convergence = _avg("cross_surface_convergence")
    concentration = _avg("workstream_concentration")
    blast_radius_severity = _avg("blast_radius_severity")
    change_vector = {
        bucket: sum(int(snapshot.get("change_vector", {}).get(bucket, 0) or 0) for snapshot in child_snapshots)
        for bucket in ("contract", "spec", "renderer", "runtime", "policy", "runbook", "doc", "build_ci", "cli")
    }
    synthetic_count = sum(
        1
        for snapshot in child_snapshots
        if str(snapshot.get("evidence_context", {}).get("basis", "")).strip() == "inferred"
    )
    explicit_count = sum(
        1
        for snapshot in child_snapshots
        if str(snapshot.get("evidence_context", {}).get("basis", "")).strip() in {"explicit", "mixed"}
    )
    blast_radius_class, _severity = _blast_radius_class(
        change_vector=change_vector,
        linked_surfaces=linked_surfaces,
        linked_workstreams=linked_workstreams,
        component_ids=linked_components,
    )
    posture_mode = _classify_mode(
        scope_type=scope_type,
        scope_id=scope_id,
        status="implementation" if linked_workstreams else "active",
        explicit_count=explicit_count,
        decision_count=explicit_count,
        implementation_count=explicit_count,
        synthetic_count=synthetic_count,
        closure_readiness=closure_readiness,
        governance_lag=governance_lag,
        convergence=convergence,
        concentration=concentration,
        blast_radius_class=blast_radius_class,
        control_posture=control_posture,
        change_vector=change_vector,
    )
    top_risk = max(child_snapshots, key=lambda snapshot: int(snapshot.get("scores", {}).get("decision_debt", 0) or 0))
    strongest = max(child_snapshots, key=lambda snapshot: int(snapshot.get("scores", {}).get("closure_readiness", 0) or 0))
    why_now = f"{scope_label} now depends on whether the highest-risk scope and the strongest-converging scope are telling the same story across the grid."
    next_move = str(top_risk.get("cards", {}).get("next_forcing_function", "")).strip()
    blast_radius = _summarize_blast_radius(
        linked_surfaces=linked_surfaces or [scope_label],
        linked_workstreams=linked_workstreams,
        linked_components=linked_components,
        linked_diagrams=linked_diagrams,
    )
    cards = _narrative_cards(
        scope_label=scope_label,
        scope_type=scope_type,
        posture_mode=posture_mode,
        why_now=why_now,
        blast_radius=blast_radius,
        next_forcing_function=next_move,
        linked_surfaces=linked_surfaces or [scope_label],
        primary_workstream=linked_workstreams[0] if linked_workstreams else "",
        evidence_quality="mixed" if explicit_count and synthetic_count else ("explicit" if explicit_count else "inferred"),
    )
    if scope_type == "grid":
        cards["executive_thesis"] = (
            f"Delivery governance is currently {_humanize_mode(posture_mode).lower()} around {str(strongest.get('scope_label', strongest.get('scope_id', 'the grid')))} while the highest decision debt remains in {str(top_risk.get('scope_label', top_risk.get('scope_id', 'another scope')))}."
        )
    evidence_context = {
        "basis": "mixed" if explicit_count and synthetic_count else ("explicit" if explicit_count else "inferred"),
        "freshness": "current",
        "linked_workstreams": linked_workstreams,
        "linked_components": linked_components,
        "linked_diagrams": linked_diagrams,
        "linked_surfaces": linked_surfaces or [scope_label],
        "blast_radius_class": blast_radius_class,
        "top_risk_scope": str(top_risk.get("scope_key", "")),
        "strongest_convergence_scope": str(strongest.get("scope_key", "")),
    }
    return _snapshot_dict(
        scope_type=scope_type,
        scope_id=scope_id,
        scope_label=scope_label,
        posture_mode=posture_mode,
        trajectory=_trajectory_for_mode(posture_mode),
        confidence=_confidence_label(evidence_context["basis"], governance_lag, explicit_count),
        cards=cards,
        evidence_context=evidence_context,
        explanation_facts=[
            f"Top risk scope: {str(top_risk.get('scope_label', top_risk.get('scope_id', 'unknown')))}.",
            f"Strongest convergence: {str(strongest.get('scope_label', strongest.get('scope_id', 'unknown')))}.",
            f"Linked surfaces: {_join_labels(linked_surfaces) or 'none'}.",
        ],
        evidence_refs=_build_evidence_refs(
            linked_workstreams=linked_workstreams,
            linked_components=linked_components,
            linked_diagrams=linked_diagrams,
            linked_paths=[],
        ),
        scores={
            "governance_lag": governance_lag,
            "decision_debt": decision_debt,
            "closure_readiness": closure_readiness,
            "cross_surface_convergence": convergence,
            "workstream_concentration": concentration,
            "blast_radius_severity": blast_radius_severity,
        },
        change_vector=change_vector,
        diagnostics={
            "status": "implementation" if linked_workstreams else "active",
            "explicit_count": explicit_count,
            "decision_count": explicit_count,
            "implementation_count": explicit_count,
            "synthetic_count": synthetic_count,
            "blast_radius_class": blast_radius_class,
            "top_risk_scope": str(top_risk.get("scope_key", "")),
            "strongest_convergence_scope": str(strongest.get("scope_key", "")),
            "child_scope_keys": [str(snapshot.get("scope_key", "")).strip() for snapshot in child_snapshots],
        },
    )


def _scope_sort_tuple(snapshot: Mapping[str, Any]) -> tuple[int, int, int, int, int, int]:
    readout = snapshot.get("operator_readout", {}) if isinstance(snapshot.get("operator_readout"), Mapping) else {}
    scores = snapshot.get("scores", {}) if isinstance(snapshot.get("scores"), Mapping) else {}
    scope_signal = snapshot.get("scope_signal", {}) if isinstance(snapshot.get("scope_signal"), Mapping) else {}
    latest_event = ""
    evidence = snapshot.get("evidence_context", {}) if isinstance(snapshot.get("evidence_context"), Mapping) else {}
    latest_event = str(evidence.get("latest_event_ts_iso", "")).strip()
    latest_sort = 0
    parsed = _parse_ts(latest_event)
    if parsed is not None:
        latest_sort = int(parsed.timestamp())
    return (
        -scope_signal_ladder.scope_signal_rank(scope_signal),
        operator_readout.scenario_priority(str(readout.get("primary_scenario", ""))),
        operator_readout.severity_rank(str(readout.get("severity", ""))),
        -int(scores.get("decision_debt", 0) or 0),
        -int(scores.get("governance_lag", 0) or 0),
        -int(scores.get("blast_radius_severity", 0) or 0),
        -latest_sort,
    )


def _linked_scope_keys(snapshot: Mapping[str, Any], scope_lookup: Mapping[str, Mapping[str, Any]]) -> list[str]:
    diagnostics = snapshot.get("diagnostics", {}) if isinstance(snapshot.get("diagnostics"), Mapping) else {}
    keys: list[str] = [
        str(token).strip()
        for token in diagnostics.get("child_scope_keys", [])
        if str(token).strip() and str(token).strip() in scope_lookup
    ]
    evidence = snapshot.get("evidence_context", {}) if isinstance(snapshot.get("evidence_context"), Mapping) else {}
    for workstream in evidence.get("linked_workstreams", []) if isinstance(evidence.get("linked_workstreams"), list) else []:
        token = _scope_key("workstream", str(workstream).strip())
        if token in scope_lookup and token != str(snapshot.get("scope_key", "")):
            keys.append(token)
    for component in evidence.get("linked_components", []) if isinstance(evidence.get("linked_components"), list) else []:
        token = _scope_key("component", str(component).strip())
        if token in scope_lookup and token != str(snapshot.get("scope_key", "")):
            keys.append(token)
    for diagram in evidence.get("linked_diagrams", []) if isinstance(evidence.get("linked_diagrams"), list) else []:
        token = _scope_key("diagram", str(diagram).strip())
        if token in scope_lookup and token != str(snapshot.get("scope_key", "")):
            keys.append(token)
    seen: set[str] = set()
    ordered: list[str] = []
    for token in keys:
        if token not in seen:
            seen.add(token)
            ordered.append(token)
    return ordered


def _proof_routes_for_snapshot(snapshot: Mapping[str, Any], *, scenario: str) -> list[dict[str, str]]:
    workstreams = _snapshot_workstreams(snapshot)
    resolved_proof_state = snapshot.get("proof_state", {}) if isinstance(snapshot.get("proof_state"), Mapping) else {}
    proof_routes = proof_state.build_proof_refs(
        proof_state=resolved_proof_state,
        scope_workstreams=workstreams,
    )
    if proof_routes:
        return [operator_readout.normalize_proof_ref(row) for row in proof_routes if isinstance(row, Mapping)]
    evidence = snapshot.get("evidence_context", {}) if isinstance(snapshot.get("evidence_context"), Mapping) else {}
    workstreams = [str(token).strip() for token in evidence.get("linked_workstreams", []) if str(token).strip()]
    components = [str(token).strip() for token in evidence.get("linked_components", []) if str(token).strip()]
    diagrams = [str(token).strip() for token in evidence.get("linked_diagrams", []) if str(token).strip()]
    scope_label = str(snapshot.get("scope_label", snapshot.get("scope_id", "scope"))).strip()
    routes: list[dict[str, str]] = []
    if scenario == "unsafe_closeout":
        if workstreams:
            routes.append(operator_readout.build_proof_ref(kind="workstream", value=workstreams[0], label=f"{workstreams[0]} timeline audit", surface="compass", anchor="timeline-audit", fact_tag="timeline_audit"))
        routes.append(operator_readout.build_proof_ref(kind="clearance", value=str(snapshot.get("scope_key", "")).strip(), label=f"{scope_label} clearance", surface="shell", anchor="approval-clearance", fact_tag="clearance"))
        if components:
            routes.append(operator_readout.build_proof_ref(kind="component", value=f"component:{components[0]}", label=f"{components[0]} forensic evidence", surface="registry", anchor="forensic-evidence", fact_tag="forensic_evidence"))
    elif scenario == "cross_surface_conflict":
        routes.append(operator_readout.build_proof_ref(kind="policy", value=str(snapshot.get("scope_key", "")).strip(), label=f"{scope_label} policy contradictions", surface="shell", anchor="policy-breaches", fact_tag="policy"))
        if components:
            routes.append(operator_readout.build_proof_ref(kind="component", value=f"component:{components[0]}", label=f"{components[0]} topology", surface="registry", anchor="topology", fact_tag="topology"))
        if workstreams:
            routes.append(operator_readout.build_proof_ref(kind="workstream", value=workstreams[0], label=f"{workstreams[0]} execution trace", surface="radar", anchor="traceability", fact_tag="topology"))
    elif scenario == "orphan_activity":
        if workstreams:
            routes.append(operator_readout.build_proof_ref(kind="workstream", value=workstreams[0], label=f"{workstreams[0]} current workstreams", surface="compass", anchor="current-workstreams", fact_tag="current_workstreams"))
            routes.append(operator_readout.build_proof_ref(kind="workstream", value=workstreams[0], label=f"{workstreams[0]} traceability", surface="radar", anchor="traceability", fact_tag="workstream_spec"))
        if components:
            routes.append(operator_readout.build_proof_ref(kind="component", value=f"component:{components[0]}", label=f"{components[0]} forensic evidence", surface="registry", anchor="forensic-evidence", fact_tag="forensic_evidence"))
    elif scenario == "stale_authority":
        if diagrams:
            routes.append(operator_readout.build_proof_ref(kind="diagram", value=diagrams[0], label=f"{diagrams[0]} freshness", surface="atlas", anchor="freshness", fact_tag="diagram_freshness"))
        routes.append(operator_readout.build_proof_ref(kind="clearance", value=str(snapshot.get("scope_key", "")).strip(), label=f"{scope_label} clearance", surface="shell", anchor="approval-clearance", fact_tag="clearance"))
        if components:
            routes.append(operator_readout.build_proof_ref(kind="component", value=f"component:{components[0]}", label=f"{components[0]} spec", surface="registry", anchor="spec", fact_tag="spec"))
    elif scenario == "false_priority":
        if workstreams:
            routes.append(operator_readout.build_proof_ref(kind="workstream", value=workstreams[0], label=f"{workstreams[0]} current workstreams", surface="compass", anchor="current-workstreams", fact_tag="current_workstreams"))
            routes.append(operator_readout.build_proof_ref(kind="workstream", value=workstreams[0], label=f"{workstreams[0]} warnings", surface="radar", anchor="warnings", fact_tag="warnings"))
        routes.append(operator_readout.build_proof_ref(kind="route", value=str(snapshot.get("scope_key", "")).strip(), label=f"{scope_label} routing", surface="shell", anchor="tab-route", fact_tag="routing"))
    else:
        if workstreams:
            routes.append(operator_readout.build_proof_ref(kind="workstream", value=workstreams[0], label=f"{workstreams[0]} timeline audit", surface="compass", anchor="timeline-audit", fact_tag="timeline_audit"))
        routes.append(operator_readout.build_proof_ref(kind="clearance", value=str(snapshot.get("scope_key", "")).strip(), label=f"{scope_label} clearance", surface="shell", anchor="approval-clearance", fact_tag="clearance"))
    if not routes:
        routes.extend(
            operator_readout.normalize_proof_ref(row)
            for row in snapshot.get("evidence_refs", [])
            if isinstance(row, Mapping)
        )
    seen: set[tuple[str, str, str, str]] = set()
    deduped: list[dict[str, str]] = []
    for row in routes:
        normalized = operator_readout.normalize_proof_ref(row)
        key = (
            normalized.get("surface", ""),
            normalized.get("anchor", ""),
            normalized.get("kind", ""),
            normalized.get("value", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped[:4]


def _build_deterministic_readout(
    *,
    snapshot: Mapping[str, Any],
    scope_lookup: Mapping[str, Mapping[str, Any]],
    control_posture: Mapping[str, Any],
) -> dict[str, Any]:
    scope_label = str(snapshot.get("scope_label", snapshot.get("scope_id", "scope"))).strip() or "Scope"
    diagnostics = snapshot.get("diagnostics", {}) if isinstance(snapshot.get("diagnostics"), Mapping) else {}
    evidence = snapshot.get("evidence_context", {}) if isinstance(snapshot.get("evidence_context"), Mapping) else {}
    scores = snapshot.get("scores", {}) if isinstance(snapshot.get("scores"), Mapping) else {}
    status = str(diagnostics.get("status", "")).strip().lower()
    explicit_count = int(diagnostics.get("explicit_count", 0) or 0)
    decision_count = int(diagnostics.get("decision_count", 0) or 0)
    implementation_count = int(diagnostics.get("implementation_count", 0) or 0)
    synthetic_count = int(diagnostics.get("synthetic_count", 0) or 0)
    freshness = str(evidence.get("freshness", "")).strip().lower()
    basis = str(evidence.get("basis", "")).strip().lower()
    blast_radius_class = str(diagnostics.get("blast_radius_class", evidence.get("blast_radius_class", ""))).strip().lower()
    linked_workstreams = [str(token).strip() for token in evidence.get("linked_workstreams", []) if str(token).strip()]
    primary_workstream = linked_workstreams[0] if linked_workstreams else scope_label
    clearance = control_posture.get("clearance", {}) if isinstance(control_posture.get("clearance"), Mapping) else {}
    clearance_state = str(clearance.get("state", "")).strip().lower()
    policy = control_posture.get("policy", {}) if isinstance(control_posture.get("policy"), Mapping) else {}
    breach_count = len(policy.get("breaches", [])) if isinstance(policy.get("breaches"), list) else 0
    stale_diagram = bool(diagnostics.get("stale_diagram", False))
    closure_readiness = int(scores.get("closure_readiness", 0) or 0)
    governance_lag = int(scores.get("governance_lag", 0) or 0)
    convergence = int(scores.get("cross_surface_convergence", 0) or 0)
    closeout_signal = str(diagnostics.get("closeout_signal", "")).strip().lower()

    candidates: list[tuple[str, str]] = []
    closeout_candidate = False
    if status == "finished":
        closeout_candidate = closeout_signal == "direct_activity_drift"
    elif status == "implementation" and closure_readiness >= 72 and governance_lag >= 36:
        closeout_candidate = True
    if not closeout_candidate and status != "finished":
        closeout_candidate = str(snapshot.get("posture_mode", "")).strip() == "closure_hardening" and clearance_state != "cleared"
    if closeout_candidate:
        severity = "blocker" if status == "finished" or clearance_state in {"pending", "in_progress"} else "watch"
        candidates.append(("unsafe_closeout", severity))
    if basis == "inferred" or (implementation_count > 0 and decision_count == 0) or (synthetic_count > 0 and explicit_count == 0):
        severity = "blocker" if status in {"implementation", "finished"} else "watch"
        candidates.append(("orphan_activity", severity))
    if stale_diagram or freshness == "stale" or (breach_count > 0 and str(snapshot.get("scope_type", "")).strip() in {"surface", "grid"}):
        severity = "blocker" if breach_count > 0 and str(snapshot.get("scope_type", "")).strip() in {"surface", "grid"} else "watch"
        candidates.append(("stale_authority", severity))
    linked_surfaces = evidence.get("linked_surfaces", []) if isinstance(evidence.get("linked_surfaces"), list) else []
    if (
        (blast_radius_class == "cross-surface" and (len(linked_workstreams) >= 2 or breach_count > 0 or str(snapshot.get("scope_type", "")).strip() in {"surface", "grid"}))
        or (len(linked_surfaces) >= 4 and convergence < 62 and explicit_count > 0)
    ):
        severity = "blocker" if governance_lag >= 60 or breach_count > 0 else "watch"
        candidates.append(("cross_surface_conflict", severity))
    if not candidates:
        candidates.append(("clear_path", "clear"))

    linked_keys = _linked_scope_keys(snapshot, scope_lookup)
    linked_rows = [scope_lookup[key] for key in linked_keys if key in scope_lookup]
    linked_risk = min(
        (
            row
            for row in linked_rows
            if isinstance(row.get("operator_readout"), Mapping)
        ),
        key=_scope_sort_tuple,
        default=None,
    )
    if linked_risk is not None:
        linked_readout = linked_risk.get("operator_readout", {}) if isinstance(linked_risk.get("operator_readout"), Mapping) else {}
        current_best = min(candidates, key=lambda item: (operator_readout.scenario_priority(item[0]), operator_readout.severity_rank(item[1])))
        linked_tuple = (
            operator_readout.scenario_priority(str(linked_readout.get("primary_scenario", ""))),
            operator_readout.severity_rank(str(linked_readout.get("severity", ""))),
        )
        if linked_tuple < (
            operator_readout.scenario_priority(current_best[0]),
            operator_readout.severity_rank(current_best[1]),
        ):
            candidates.append(("false_priority", str(linked_readout.get("severity", "watch")).strip() or "watch"))

    primary_scenario, severity = min(
        candidates,
        key=lambda item: (operator_readout.scenario_priority(item[0]), operator_readout.severity_rank(item[1])),
    )
    secondary_scenarios = [
        scenario
        for scenario, _severity in sorted(
            {(scenario, severity) for scenario, severity in candidates if scenario != primary_scenario},
            key=lambda item: (operator_readout.scenario_priority(item[0]), operator_readout.severity_rank(item[1])),
        )
    ][:2]

    if primary_scenario == "unsafe_closeout":
        issue = f"Closeout confidence is ahead of the last trustworthy proof for {scope_label}."
        why_hidden = "The scope can look complete in linked tools while the final checkpoint, clearance pass, or refresh is still behind the apparent finish line."
        action = f"Capture the final reviewed checkpoint for {primary_workstream} and clear linked surfaces before closeout."
        action_kind = "clear_closeout"
        requires_approval = True
    elif primary_scenario == "cross_surface_conflict":
        issue = f"Linked surfaces are telling different stories about {scope_label}."
        why_hidden = "Each tool shows a valid slice, but the contradiction only appears when their scope, authority, and next action are compared together."
        action = f"Resolve the cross-surface contradiction around {primary_workstream} and restate the controlling scope explicitly."
        action_kind = "resolve_conflict"
        requires_approval = True
    elif primary_scenario == "orphan_activity":
        issue = f"Real activity is moving without a bound checkpoint for {scope_label}."
        why_hidden = "There is execution signal here, but not enough explicit rationale or checkpoint binding to trust the state across tools."
        action = f"Capture an explicit checkpoint for {primary_workstream} and bind the active activity to it before treating this as governed progress."
        action_kind = "capture_checkpoint"
        requires_approval = True
    elif primary_scenario == "stale_authority":
        issue = f"Operators are trusting stale authority for {scope_label}."
        why_hidden = "The artifact people are reading as source of truth is older or weaker than the delivery pressure depending on it."
        action = f"Refresh the governing authority for {primary_workstream} and confirm that linked proofs now point at the current source of truth."
        action_kind = "refresh_authority"
        requires_approval = True
    elif primary_scenario == "false_priority":
        linked_label = str(linked_risk.get("scope_label", linked_risk.get("scope_id", "linked scope"))).strip() if linked_risk else "linked scope"
        issue = f"This is not the scope to watch first; {linked_label} is carrying the sharper operator risk."
        why_hidden = "The current panel can look calmer than the real blocker because the sharper failure mode sits in a linked scope."
        action = f"Rebind operator attention to the actual blocker and reconcile {primary_workstream} against that higher-risk scope."
        action_kind = "rebind_scope"
        requires_approval = True
    else:
        issue = "Path is clear. The operator risk is keeping proof fresh, not finding a hidden blocker."
        why_hidden = "Nothing materially hidden is outranking the current checkpoint set."
        action = "Keep the latest checkpoint and proof routes current."
        action_kind = "defer_scope"
        requires_approval = False

    return {
        "primary_scenario": primary_scenario,
        "secondary_scenarios": secondary_scenarios,
        "severity": severity,
        "issue": _sanitize_narrative_text(issue),
        "why_hidden": _sanitize_narrative_text(why_hidden),
        "action": _sanitize_narrative_text(action),
        "action_kind": action_kind,
        "proof_refs": _proof_routes_for_snapshot(snapshot, scenario=primary_scenario),
        "requires_approval": requires_approval,
        "source": "deterministic",
    }


def _apply_operator_readouts(
    *,
    scopes: Sequence[Mapping[str, Any]],
    control_posture: Mapping[str, Any],
    reasoning_payload: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    prepared = [dict(snapshot) for snapshot in scopes]
    scope_lookup = {
        str(snapshot.get("scope_key", "")).strip(): snapshot
        for snapshot in prepared
        if str(snapshot.get("scope_key", "")).strip()
    }
    for snapshot in prepared:
        snapshot["operator_readout"] = _build_deterministic_readout(
            snapshot=snapshot,
            scope_lookup=scope_lookup,
            control_posture=control_posture,
        )
    for snapshot in prepared:
        diagnostics = dict(snapshot.get("diagnostics", {})) if isinstance(snapshot.get("diagnostics"), Mapping) else {}
        diagnostics["reasoning_confidence"] = 0.0
        diagnostics["reasoning_state"] = str((reasoning_payload or {}).get("state", "")).strip()
        snapshot["diagnostics"] = diagnostics
    normalized: list[dict[str, Any]] = []
    for snapshot in prepared:
        clean = dict(snapshot)
        clean.pop("cards", None)
        clean["operator_readout"] = dict(clean.get("operator_readout", {}))
        normalized.append(clean)
    return normalized


def _summary_scope(snapshot: Mapping[str, Any]) -> dict[str, str]:
    readout = snapshot.get("operator_readout", {}) if isinstance(snapshot.get("operator_readout"), Mapping) else {}
    scope_signal = snapshot.get("scope_signal", {}) if isinstance(snapshot.get("scope_signal"), Mapping) else {}
    return {
        "scope_key": str(snapshot.get("scope_key", "")).strip(),
        "scope_label": str(snapshot.get("scope_label", snapshot.get("scope_id", ""))).strip(),
        "primary_scenario": str(readout.get("primary_scenario", "")).strip(),
        "severity": str(readout.get("severity", "")).strip(),
        "action": str(readout.get("action", "")).strip(),
        "scope_signal_rung": str(scope_signal.get("rung", "")).strip(),
        "scope_signal_token": str(scope_signal.get("token", "")).strip(),
    }


def _snapshot_workstreams(snapshot: Mapping[str, Any]) -> list[str]:
    evidence = snapshot.get("evidence_context", {}) if isinstance(snapshot.get("evidence_context"), Mapping) else {}
    rows = [
        str(token).strip()
        for token in evidence.get("linked_workstreams", [])
        if str(token).strip()
    ]
    if str(snapshot.get("scope_type", "")).strip() == "workstream":
        token = str(snapshot.get("scope_id", "")).strip()
        if token:
            rows.insert(0, token)
    return list(dict.fromkeys(rows))


def _snapshot_components(snapshot: Mapping[str, Any]) -> list[str]:
    evidence = snapshot.get("evidence_context", {}) if isinstance(snapshot.get("evidence_context"), Mapping) else {}
    rows = [
        str(token).strip()
        for token in evidence.get("linked_components", [])
        if str(token).strip()
    ]
    if str(snapshot.get("scope_type", "")).strip() == "component":
        token = str(snapshot.get("scope_id", "")).strip()
        if token:
            rows.insert(0, token)
    return list(dict.fromkeys(rows))


def _activity_outruns_explicit(snapshot: Mapping[str, Any]) -> bool:
    evidence = snapshot.get("evidence_context", {}) if isinstance(snapshot.get("evidence_context"), Mapping) else {}
    latest_event = _parse_ts(str(evidence.get("latest_event_ts_iso", "")).strip())
    latest_explicit = _parse_ts(str(evidence.get("latest_explicit_ts_iso", "")).strip())
    if latest_event is None:
        return False
    if latest_explicit is None:
        return True
    return latest_event > latest_explicit


def _scope_matches_posture_row(snapshot: Mapping[str, Any], row: Mapping[str, Any]) -> bool:
    workstreams = set(_snapshot_workstreams(snapshot))
    components = set(_snapshot_components(snapshot))
    row_workstreams = {
        str(token).strip()
        for token in row.get("workstreams", [])
        if str(token).strip()
    }
    singular_workstream = str(row.get("workstream", "")).strip()
    if singular_workstream:
        row_workstreams.add(singular_workstream)
    row_components = {
        str(token).strip()
        for token in row.get("components", [])
        if str(token).strip()
    }
    singular_component = str(row.get("component_id", "")).strip()
    if singular_component:
        row_components.add(singular_component)
    return bool(workstreams & row_workstreams) or bool(components & row_components)


def _scope_has_policy_breach(snapshot: Mapping[str, Any], control_posture: Mapping[str, Any]) -> bool:
    policy = control_posture.get("policy", {}) if isinstance(control_posture.get("policy"), Mapping) else {}
    breaches = policy.get("breaches", []) if isinstance(policy.get("breaches"), list) else []
    return any(isinstance(row, Mapping) and _scope_matches_posture_row(snapshot, row) for row in breaches)


def _scope_has_open_recommendation(snapshot: Mapping[str, Any], control_posture: Mapping[str, Any]) -> bool:
    recommendations = control_posture.get("recommendations", []) if isinstance(control_posture.get("recommendations"), list) else []
    for row in recommendations:
        if not isinstance(row, Mapping):
            continue
        status = str(row.get("status", "")).strip().lower()
        if status == "verified":
            continue
        if _scope_matches_posture_row(snapshot, row):
            return True
    return False


def _derive_leaf_live_actionability(
    *,
    snapshot: Mapping[str, Any],
    control_posture: Mapping[str, Any],
    live_workstreams: frozenset[str],
) -> tuple[bool, str]:
    diagnostics = snapshot.get("diagnostics", {}) if isinstance(snapshot.get("diagnostics"), Mapping) else {}
    readout = snapshot.get("operator_readout", {}) if isinstance(snapshot.get("operator_readout"), Mapping) else {}
    scope_type = str(snapshot.get("scope_type", "")).strip()
    status = str(diagnostics.get("status", "")).strip().lower()
    closeout_signal = str(diagnostics.get("closeout_signal", "")).strip().lower()
    scenario = str(readout.get("primary_scenario", "")).strip()
    if scope_type == "workstream":
        if status in _EXCLUDED_WORKSTREAM_STATUSES:
            return False, ""
        if status in _LIVE_WORKSTREAM_STATUSES:
            return True, f"{status.capitalize()} workstream is still live."
        if status == "finished":
            if _scope_has_open_recommendation(snapshot, control_posture):
                return True, "Finished workstream still has pending recommendation or clearance work."
            if _scope_has_policy_breach(snapshot, control_posture):
                return True, "Finished workstream still carries a linked policy breach."
            if closeout_signal == "direct_activity_drift":
                return True, "Finished workstream has newer directly attributed activity than its last explicit checkpoint."
        return False, ""
    if scope_type in {"component", "diagram"}:
        linked_live = [token for token in _snapshot_workstreams(snapshot) if token in live_workstreams]
        if linked_live and scenario != "clear_path":
            return True, f"Linked to live workstream {_join_labels(linked_live, limit=2)}."
        if _scope_has_open_recommendation(snapshot, control_posture):
            return True, "Linked operator recommendation is still open."
        if _scope_has_policy_breach(snapshot, control_posture):
            return True, "Linked policy breach keeps this scope live."
        if _activity_outruns_explicit(snapshot) and scenario != "clear_path":
            return True, "Newer activity outruns the last explicit checkpoint."
    return False, ""


def _annotate_live_actionability(
    *,
    scopes: Sequence[Mapping[str, Any]],
    control_posture: Mapping[str, Any],
) -> list[dict[str, Any]]:
    prepared = [dict(snapshot) for snapshot in scopes]
    scope_lookup = {
        str(snapshot.get("scope_key", "")).strip(): snapshot
        for snapshot in prepared
        if str(snapshot.get("scope_key", "")).strip()
    }
    live_workstreams: set[str] = set()
    for snapshot in prepared:
        if str(snapshot.get("scope_type", "")).strip() != "workstream":
            continue
        live, reason = _derive_leaf_live_actionability(
            snapshot=snapshot,
            control_posture=control_posture,
            live_workstreams=frozenset(),
        )
        diagnostics = dict(snapshot.get("diagnostics", {})) if isinstance(snapshot.get("diagnostics"), Mapping) else {}
        diagnostics["live_actionable"] = live
        diagnostics["live_reason"] = reason
        snapshot["diagnostics"] = diagnostics
        if live:
            token = str(snapshot.get("scope_id", "")).strip()
            if token:
                live_workstreams.add(token)
    for snapshot in prepared:
        if str(snapshot.get("scope_type", "")).strip() not in {"component", "diagram"}:
            continue
        live, reason = _derive_leaf_live_actionability(
            snapshot=snapshot,
            control_posture=control_posture,
            live_workstreams=frozenset(live_workstreams),
        )
        diagnostics = dict(snapshot.get("diagnostics", {})) if isinstance(snapshot.get("diagnostics"), Mapping) else {}
        diagnostics["live_actionable"] = live
        diagnostics["live_reason"] = reason
        snapshot["diagnostics"] = diagnostics
    for snapshot in prepared:
        scope_type = str(snapshot.get("scope_type", "")).strip()
        if scope_type not in {"surface", "grid"}:
            continue
        diagnostics = dict(snapshot.get("diagnostics", {})) if isinstance(snapshot.get("diagnostics"), Mapping) else {}
        child_keys = [
            str(token).strip()
            for token in diagnostics.get("child_scope_keys", [])
            if str(token).strip()
        ]
        live_children = [
            scope_lookup[token]
            for token in child_keys
            if token in scope_lookup
            and bool(scope_lookup[token].get("diagnostics", {}).get("live_actionable", False))
        ]
        diagnostics["live_actionable"] = bool(live_children)
        diagnostics["live_reason"] = (
            f"Aggregates {len(live_children)} live child scope(s)."
            if live_children
            else ""
        )
        snapshot["diagnostics"] = diagnostics
    return prepared


def _next_surface_label(readout: Mapping[str, Any]) -> str:
    proof_refs = readout.get("proof_refs", []) if isinstance(readout.get("proof_refs"), list) else []
    for row in proof_refs:
        if not isinstance(row, Mapping):
            continue
        label = operator_readout.humanize_operator_readout_token(str(row.get("surface", "")).strip())
        if label:
            return label
    return "Shell"


def _linked_risk_snapshot(snapshot: Mapping[str, Any], scope_lookup: Mapping[str, Mapping[str, Any]]) -> Mapping[str, Any] | None:
    linked_keys = _linked_scope_keys(snapshot, scope_lookup)
    candidates = [
        scope_lookup[token]
        for token in linked_keys
        if token in scope_lookup
        and str(scope_lookup[token].get("operator_readout", {}).get("primary_scenario", "")).strip() != "clear_path"
    ]
    return min(candidates, key=_scope_sort_tuple, default=None)


def _latest_checkpoint_delta_text(snapshot: Mapping[str, Any]) -> str:
    evidence = snapshot.get("evidence_context", {}) if isinstance(snapshot.get("evidence_context"), Mapping) else {}
    latest_event = str(evidence.get("latest_event_ts_iso", "")).strip()
    latest_explicit = str(evidence.get("latest_explicit_ts_iso", "")).strip()
    latest_kind = str(evidence.get("latest_signal_kind", "")).strip().replace("_", " ") or "activity"
    if latest_event and latest_explicit and _activity_outruns_explicit(snapshot):
        return f"Latest {latest_kind} signal at {latest_event} is newer than the last explicit checkpoint at {latest_explicit}."
    if latest_event and not latest_explicit:
        return f"Latest {latest_kind} signal at {latest_event} has no explicit checkpoint behind it."
    if latest_explicit:
        return f"Last explicit checkpoint is {latest_explicit}."
    return ""


def _surface_conflict_text(snapshot: Mapping[str, Any], readout: Mapping[str, Any]) -> str:
    proof_refs = readout.get("proof_refs", []) if isinstance(readout.get("proof_refs"), list) else []
    routed_surfaces = list(
        dict.fromkeys(
            operator_readout.humanize_operator_readout_token(str(row.get("surface", "")).strip())
            for row in proof_refs
            if isinstance(row, Mapping) and str(row.get("surface", "")).strip()
        )
    )
    if len(routed_surfaces) >= 2:
        return f"Authority is split across {routed_surfaces[0]} and {routed_surfaces[1]}."
    evidence = snapshot.get("evidence_context", {}) if isinstance(snapshot.get("evidence_context"), Mapping) else {}
    linked_surfaces = [
        str(token).strip()
        for token in evidence.get("linked_surfaces", [])
        if str(token).strip()
    ]
    if len(linked_surfaces) >= 2:
        return f"Linked surfaces in play: {_join_labels(linked_surfaces, limit=4)}."
    return ""


def _ignored_consequence_text(scenario: str, scope_label: str) -> str:
    if scenario == "unsafe_closeout":
        return f"If ignored, {scope_label} can be closed against stale proof and force re-clearance later."
    if scenario == "cross_surface_conflict":
        return f"If ignored, operators can execute the wrong next action while {scope_label} still looks locally valid on each surface."
    if scenario == "orphan_activity":
        return f"If ignored, maintainers will infer governed progress for {scope_label} from activity that is not actually bound."
    if scenario == "stale_authority":
        return f"If ignored, people will keep trusting obsolete authority for {scope_label}."
    if scenario == "false_priority":
        return f"If ignored, attention stays on {scope_label} while the real blocker worsens elsewhere."
    return f"If ignored, proof freshness for {scope_label} will drift."


def _build_queue_why_now(snapshot: Mapping[str, Any], readout: Mapping[str, Any], live_reason: str) -> str:
    cards = snapshot.get("cards", {}) if isinstance(snapshot.get("cards"), Mapping) else {}
    base = str(cards.get("why_now", "")).strip() or str(live_reason or "").strip()
    delta = _latest_checkpoint_delta_text(snapshot)
    if base and delta and delta not in base:
        return _sanitize_narrative_text(f"{base} {delta}")
    return _sanitize_narrative_text(base or delta or operator_readout.DEFAULT_WHY_NOW_FALLBACK)


def _build_queue_success_check(
    *,
    snapshot: Mapping[str, Any],
    readout: Mapping[str, Any],
    scope_lookup: Mapping[str, Mapping[str, Any]],
) -> str:
    evidence = snapshot.get("evidence_context", {}) if isinstance(snapshot.get("evidence_context"), Mapping) else {}
    scope_label = str(snapshot.get("scope_label", snapshot.get("scope_id", "scope"))).strip() or "scope"
    primary_workstream = next(iter(_snapshot_workstreams(snapshot)), scope_label)
    scenario = str(readout.get("primary_scenario", "")).strip()
    if scenario == "unsafe_closeout":
        return _sanitize_narrative_text(
            f"Clearance is marked cleared and {primary_workstream} has no newer activity than its last explicit checkpoint."
        )
    if scenario == "cross_surface_conflict":
        linked_surfaces = [
            str(token).strip()
            for token in evidence.get("linked_surfaces", [])
            if str(token).strip()
        ]
        return _sanitize_narrative_text(
            f"{_join_labels(linked_surfaces, limit=4) or 'Linked surfaces'} now agree on the controlling scope and next action for {primary_workstream}."
        )
    if scenario == "orphan_activity":
        return _sanitize_narrative_text(
            f"The latest activity for {primary_workstream} is bound to an explicit checkpoint or decision instead of inferred signal alone."
        )
    if scenario == "stale_authority":
        return _sanitize_narrative_text(
            f"The authority artifact for {scope_label} is refreshed and current proof routes now point at it."
        )
    if scenario == "false_priority":
        linked_risk = _linked_risk_snapshot(snapshot, scope_lookup)
        linked_label = str(linked_risk.get("scope_label", "the higher-risk scope")).strip() if linked_risk else "the higher-risk scope"
        return _sanitize_narrative_text(
            f"Operators are redirected to {linked_label} first and {scope_label} no longer outranks that blocker."
        )
    return _sanitize_narrative_text(operator_readout.DEFAULT_SUCCESS_CHECK_FALLBACK)


def _build_queue_proof_highlights(
    *,
    snapshot: Mapping[str, Any],
    readout: Mapping[str, Any],
    scope_lookup: Mapping[str, Mapping[str, Any]],
    control_posture: Mapping[str, Any],
) -> list[str]:
    resolved_proof_state = snapshot.get("proof_state", {}) if isinstance(snapshot.get("proof_state"), Mapping) else {}
    proof_rows = proof_state.proof_highlights(resolved_proof_state)
    if proof_rows:
        return proof_rows[:4]
    scenario = str(readout.get("primary_scenario", "")).strip()
    scope_label = str(snapshot.get("scope_label", snapshot.get("scope_id", "scope"))).strip() or "scope"
    diagnostics = snapshot.get("diagnostics", {}) if isinstance(snapshot.get("diagnostics"), Mapping) else {}
    evidence = snapshot.get("evidence_context", {}) if isinstance(snapshot.get("evidence_context"), Mapping) else {}
    rows: list[str] = []
    delta = _latest_checkpoint_delta_text(snapshot)
    if delta:
        rows.append(delta)
    if scenario == "cross_surface_conflict":
        conflict = _surface_conflict_text(snapshot, readout)
        if conflict:
            rows.append(conflict)
    elif scenario == "orphan_activity":
        basis = str(evidence.get("basis", "")).strip() or "inferred"
        rows.append(
            f"Evidence basis is {basis} with {int(diagnostics.get('explicit_count', 0) or 0)} explicit checkpoint(s) and {int(diagnostics.get('synthetic_count', 0) or 0)} inferred signal(s)."
        )
    elif scenario == "stale_authority":
        freshness = str(evidence.get("freshness", "")).strip() or "unknown"
        rows.append(f"Authority freshness for {scope_label} is {freshness}.")
    elif scenario == "false_priority":
        linked_risk = _linked_risk_snapshot(snapshot, scope_lookup)
        if linked_risk is not None:
            rows.append(
                f"Linked scope {str(linked_risk.get('scope_label', linked_risk.get('scope_id', 'linked scope'))).strip()} currently outranks this scope."
            )
    elif scenario == "unsafe_closeout":
        clearance = control_posture.get("clearance", {}) if isinstance(control_posture.get("clearance"), Mapping) else {}
        clearance_state = str(clearance.get("state", "")).strip().lower()
        if clearance_state:
            rows.append(f"Shell clearance state is {clearance_state}.")
    rows.append(_ignored_consequence_text(scenario, scope_label))
    deduped = [token for token in dict.fromkeys(_sanitize_narrative_text(item) for item in rows) if token]
    return deduped[:3]


def _queue_sort_tuple(snapshot: Mapping[str, Any]) -> tuple[int, int, int, int, int, int, int]:
    scope_type = str(snapshot.get("scope_type", "")).strip()
    scope_type_rank = {"workstream": 0, "component": 1, "diagram": 2}.get(scope_type, 9)
    base = _scope_sort_tuple(snapshot)
    return (*base, scope_type_rank)


def _build_operator_queue(
    *,
    scopes: Sequence[Mapping[str, Any]],
    control_posture: Mapping[str, Any],
    reasoning_payload: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    scope_lookup = {
        str(snapshot.get("scope_key", "")).strip(): snapshot
        for snapshot in scopes
        if str(snapshot.get("scope_key", "")).strip()
    }
    _ = reasoning_payload
    candidates = [
        snapshot
        for snapshot in scopes
        if str(snapshot.get("scope_type", "")).strip() in {"workstream", "component", "diagram"}
        and bool(snapshot.get("diagnostics", {}).get("live_actionable", False))
        and str(snapshot.get("operator_readout", {}).get("primary_scenario", "")).strip() != "clear_path"
    ]
    queue: list[dict[str, Any]] = []
    for rank, snapshot in enumerate(sorted(candidates, key=_queue_sort_tuple), start=1):
        scope_key = str(snapshot.get("scope_key", "")).strip()
        readout = snapshot.get("operator_readout", {}) if isinstance(snapshot.get("operator_readout"), Mapping) else {}
        diagnostics = snapshot.get("diagnostics", {}) if isinstance(snapshot.get("diagnostics"), Mapping) else {}
        queue.append(
            {
                "id": f"oq-{scope_key.replace(':', '-')}",
                "rank": rank,
                "scope_key": scope_key,
                "scope_type": str(snapshot.get("scope_type", "")).strip(),
                "scope_id": str(snapshot.get("scope_id", "")).strip(),
                "scope_label": str(snapshot.get("scope_label", snapshot.get("scope_id", ""))).strip(),
                "primary_scenario": str(readout.get("primary_scenario", "clear_path")).strip() or "clear_path",
                "secondary_scenarios": [
                    str(token).strip()
                    for token in readout.get("secondary_scenarios", [])
                    if str(token).strip()
                ][:2],
                "severity": str(readout.get("severity", "clear")).strip() or "clear",
                "issue": str(readout.get("issue", "")).strip(),
                "why_hidden": str(readout.get("why_hidden", "")).strip(),
                "action": str(readout.get("action", "")).strip(),
                "action_kind": str(readout.get("action_kind", "defer_scope")).strip() or "defer_scope",
                "proof_refs": [
                    operator_readout.normalize_proof_ref(row)
                    for row in readout.get("proof_refs", [])
                    if isinstance(row, Mapping)
                ],
                "proof_state": dict(snapshot.get("proof_state", {})) if isinstance(snapshot.get("proof_state"), Mapping) else {},
                "claim_guard": dict(snapshot.get("claim_guard", {})) if isinstance(snapshot.get("claim_guard"), Mapping) else {},
                "requires_approval": bool(readout.get("requires_approval", True)),
                "source": str(readout.get("source", "deterministic")).strip() or "deterministic",
                "why_now": _build_queue_why_now(snapshot, readout, str(diagnostics.get("live_reason", "")).strip()),
                "success_check": _build_queue_success_check(snapshot=snapshot, readout=readout, scope_lookup=scope_lookup),
                "proof_highlights": [
                    str(token).strip()
                    for token in (
                        _build_queue_proof_highlights(
                            snapshot=snapshot,
                            readout=readout,
                            scope_lookup=scope_lookup,
                            control_posture=control_posture,
                        )
                    )
                    if str(token).strip()
                ][:4],
                "live_reason": str(diagnostics.get("live_reason", "")).strip(),
                "next_surface": _next_surface_label(readout),
            }
        )
    return queue


def _augment_operator_intelligence(
    *,
    scopes: Sequence[Mapping[str, Any]],
    control_posture: Mapping[str, Any],
    reasoning_payload: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    _ = reasoning_payload
    live_scopes = _annotate_live_actionability(scopes=scopes, control_posture=control_posture)
    return [dict(snapshot) for snapshot in live_scopes]


def _attach_case_metadata(
    *,
    scopes: Sequence[Mapping[str, Any]],
    reasoning_payload: Mapping[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    cases_by_scope = tribunal_engine.cases_by_scope_key(reasoning_payload or {})
    case_queue = tribunal_engine.case_queue(reasoning_payload or {})
    systemic_brief = (
        dict(reasoning_payload.get("systemic_brief", {}))
        if isinstance((reasoning_payload or {}).get("systemic_brief"), Mapping)
        else {}
    )
    attached: list[dict[str, Any]] = []
    suppressed_case_scope_keys: set[str] = set()
    for snapshot in scopes:
        clone = dict(snapshot)
        scope_key = str(clone.get("scope_key", "")).strip()
        case = cases_by_scope.get(scope_key, {})
        evidence = clone.get("evidence_context", {}) if isinstance(clone.get("evidence_context"), Mapping) else {}
        readout = clone.get("operator_readout", {}) if isinstance(clone.get("operator_readout"), Mapping) else {}
        clone["case_refs"] = [str(case.get("case_id", "")).strip()] if case else []
        clone["surface_contributions"] = [
            {
                "surface": str(token).strip(),
                "scope_key": scope_key,
            }
            for token in evidence.get("linked_surfaces", [])
            if str(token).strip()
        ][:8]
        clone["evidence_bundle"] = {
            "code_references": [
                str(token).strip()
                for token in evidence.get("code_references", [])
                if str(token).strip()
            ][:12],
            "changed_artifacts": [
                str(token).strip()
                for token in evidence.get("changed_artifacts", [])
                if str(token).strip()
            ][:16],
            "evidence_refs": [
                operator_readout.normalize_proof_ref(item)
                for item in clone.get("evidence_refs", [])
                if isinstance(item, Mapping)
            ][:8],
            "proof_routes": [
                operator_readout.normalize_proof_ref(item)
                for item in readout.get("proof_refs", [])
                if isinstance(item, Mapping)
            ][:8],
        }
        diagnostics = clone.get("diagnostics", {}) if isinstance(clone.get("diagnostics"), Mapping) else {}
        if not bool(diagnostics.get("live_actionable", False)) and str(readout.get("primary_scenario", "")).strip() == "false_priority":
            suppressed_case_scope_keys.add(scope_key)
        attached.append(clone)
    filtered_case_queue = [
        dict(row)
        for row in case_queue
        if str(row.get("scope_key", "")).strip() not in suppressed_case_scope_keys
    ]
    return attached, filtered_case_queue, systemic_brief


def _delivery_reasoning_config(*, repo_root: Path) -> odylith_reasoning.ReasoningConfig:
    """Use deterministic Tribunal fallback for shell refresh/build paths.

    Delivery-intelligence refresh must remain local and predictable even when a
    persisted Tribunal reasoning artifact does not exist yet. Explicit Tribunal
    flows can still opt into provider-backed reasoning separately.
    """

    resolved = odylith_reasoning.reasoning_config_from_env(repo_root=repo_root)
    return odylith_reasoning.ReasoningConfig(
        mode="disabled",
        provider=resolved.provider,
        model=resolved.model,
        base_url=resolved.base_url,
        api_key=resolved.api_key,
        scope_cap=resolved.scope_cap,
        timeout_seconds=resolved.timeout_seconds,
        codex_bin=resolved.codex_bin,
        codex_reasoning_effort=resolved.codex_reasoning_effort,
        claude_bin=resolved.claude_bin,
        claude_reasoning_effort=resolved.claude_reasoning_effort,
        api_key_env=resolved.api_key_env,
        config_source="delivery-deterministic-fallback",
        config_path=resolved.config_path,
    )


def _validate_artifact_payload(payload: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if str(payload.get("version", "")).strip() != "v4":
        errors.append("payload version must be v4")
    scopes = payload.get("scopes", [])
    if not isinstance(scopes, list) or not scopes:
        errors.append("payload must contain scopes")
        return errors
    case_queue = payload.get("case_queue", [])
    if not isinstance(case_queue, list):
        errors.append("payload case_queue must be a list")
    seen: set[str] = set()
    for snapshot in scopes:
        if not isinstance(snapshot, Mapping):
            errors.append("snapshot must be an object")
            continue
        scope_key = str(snapshot.get("scope_key", "")).strip()
        if not scope_key:
            errors.append("snapshot missing scope_key")
        elif scope_key in seen:
            errors.append(f"duplicate scope_key: {scope_key}")
        else:
            seen.add(scope_key)
        readout = snapshot.get("operator_readout", {}) if isinstance(snapshot.get("operator_readout"), Mapping) else {}
        errors.extend(f"{scope_key}: {error}" for error in operator_readout.validate_operator_readout(readout))
        scope_signal = snapshot.get("scope_signal", {}) if isinstance(snapshot.get("scope_signal"), Mapping) else {}
        errors.extend(f"{scope_key}: {error}" for error in scope_signal_ladder.validate_scope_signal(scope_signal))
    return errors


def build_delivery_intelligence_artifact(
    *,
    repo_root: Path,
    max_review_age_days: int = DEFAULT_MAX_REVIEW_AGE_DAYS,
    control_posture_override: Mapping[str, Any] | None = None,
    odylith_reasoning_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo_root = Path(str(repo_root)).expanduser().resolve()
    manifest_path = _resolve(repo_root, registry.DEFAULT_MANIFEST_PATH)
    catalog_path = _resolve(repo_root, registry.DEFAULT_CATALOG_PATH)
    ideas_root = _resolve(repo_root, registry.DEFAULT_IDEAS_ROOT)
    stream_path = _resolve(repo_root, registry.DEFAULT_STREAM_PATH)
    traceability_path = _resolve(repo_root, registry.DEFAULT_TRACEABILITY_GRAPH_PATH)
    control_posture_path = _resolve(repo_root, DEFAULT_CONTROL_POSTURE_PATH)
    odylith_reasoning_path = _resolve(repo_root, DEFAULT_ODYLITH_REASONING_PATH)

    report = registry.build_component_registry_report(
        repo_root=repo_root,
        manifest_path=manifest_path,
        catalog_path=catalog_path,
        ideas_root=ideas_root,
        stream_path=stream_path,
    )
    timelines = registry.build_component_timelines(
        component_index=report.components,
        mapped_events=report.mapped_events,
    )
    component_traceability = registry.build_component_traceability_index(
        repo_root=repo_root,
        components=report.components,
        traceability_graph_path=traceability_path,
    )
    workstream_contexts = _load_workstream_contexts(ideas_root=ideas_root)
    traceability_rows = _load_traceability_rows(repo_root=repo_root, path=traceability_path)
    catalog_rows = _load_catalog(repo_root=repo_root, catalog_path=catalog_path)
    diagrams_by_id = {
        registry.normalize_diagram_id(str(row.get("diagram_id", ""))): row
        for row in catalog_rows
        if registry.normalize_diagram_id(str(row.get("diagram_id", "")))
    }
    control_posture = dict(control_posture_override) if isinstance(control_posture_override, Mapping) else _read_json(control_posture_path)
    if isinstance(odylith_reasoning_override, Mapping):
        odylith_reasoning_payload = dict(odylith_reasoning_override)
    else:
        odylith_reasoning_payload = _read_json(odylith_reasoning_path)

    scopes: list[dict[str, Any]] = []

    for component_id, entry in sorted(report.components.items()):
        component_diagrams = [diagrams_by_id[token] for token in entry.diagrams if token in diagrams_by_id]
        scopes.append(
            _build_component_snapshot(
                repo_root=repo_root,
                component_id=component_id,
                entry=entry,
                timeline=timelines.get(component_id, []),
                traceability=component_traceability.get(component_id, {}),
                max_review_age_days=max_review_age_days,
                diagram_rows=component_diagrams,
            )
        )

    all_workstream_ids = sorted(set([*workstream_contexts.keys(), *traceability_rows.keys()]))
    for workstream_id in all_workstream_ids:
        context = workstream_contexts.get(
            workstream_id,
            {
                "idea_id": workstream_id,
                "title": workstream_id,
                "status": str(traceability_rows.get(workstream_id, {}).get("status", "")).strip().lower(),
                "idea_file": traceability_rows.get(workstream_id, {}).get("idea_file", ""),
                "why_now": "",
                "opportunity": "",
                "founder_pov": "",
            },
        )
        traceability_row = traceability_rows.get(workstream_id, {})
        scopes.append(
            _build_workstream_snapshot(
                repo_root=repo_root,
                workstream_id=workstream_id,
                context=context,
                traceability_row=traceability_row,
                components=report.components,
                mapped_events=report.mapped_events,
                component_traceability=component_traceability,
                max_review_age_days=max_review_age_days,
                diagrams_by_id=diagrams_by_id,
            )
        )

    for row in catalog_rows:
        diagram_id = registry.normalize_diagram_id(str(row.get("diagram_id", "")))
        if not diagram_id:
            continue
        scopes.append(
            _build_diagram_snapshot(
                row=row,
                components=report.components,
                mapped_events=report.mapped_events,
                max_review_age_days=max_review_age_days,
            )
        )

    surface_children = {
        "registry": [snapshot for snapshot in scopes if snapshot.get("scope_type") == "component"],
        "shell": [snapshot for snapshot in scopes if snapshot.get("scope_key") in {
            _scope_key("component", "shell"),
            _scope_key("workstream", "B-038"),
        }],
        "radar": [snapshot for snapshot in scopes if snapshot.get("scope_type") == "workstream"],
        "atlas": [snapshot for snapshot in scopes if snapshot.get("scope_type") == "diagram"],
        "compass": [snapshot for snapshot in scopes if snapshot.get("scope_type") == "workstream"],
    }
    for surface_id, child_rows in surface_children.items():
        scopes.append(
            _aggregate_scope(
                scope_type="surface",
                scope_id=surface_id,
                scope_label=surface_id.capitalize(),
                child_snapshots=child_rows,
                control_posture=control_posture if surface_id == "shell" else None,
            )
        )

    surface_snapshots = [snapshot for snapshot in scopes if snapshot.get("scope_type") == "surface"]
    scopes.append(
        _aggregate_scope(
            scope_type="grid",
            scope_id="governance",
            scope_label="Delivery Governance & Intelligence",
            child_snapshots=surface_snapshots,
            control_posture=control_posture,
        )
    )
    scopes = proof_state.annotate_scopes_with_proof_state(
        repo_root=repo_root,
        scopes=scopes,
    )
    scopes = scope_signal_ladder.annotate_delivery_scope_signals(
        scopes=scopes,
        control_posture=control_posture,
    )

    scopes = _apply_operator_readouts(
        scopes=scopes,
        control_posture=control_posture,
        reasoning_payload=odylith_reasoning_payload,
    )
    scopes = _augment_operator_intelligence(
        scopes=scopes,
        control_posture=control_posture,
        reasoning_payload=odylith_reasoning_payload,
    )
    reasoning_cases = (
        odylith_reasoning_payload.get("cases", [])
        if isinstance(odylith_reasoning_payload, Mapping)
        else []
    )
    reasoning_queue = (
        odylith_reasoning_payload.get("case_queue", [])
        if isinstance(odylith_reasoning_payload, Mapping)
        else []
    )
    if not isinstance(reasoning_cases, list) or not isinstance(reasoning_queue, list) or not reasoning_cases:
        odylith_reasoning_payload = odylith_reasoning.build_reasoning_payload(
            repo_root=repo_root,
            delivery_payload={
                "version": "v4",
                "generated_utc": "",
                "scopes": scopes,
                "indexes": {},
                "summary": {},
                "case_queue": [],
                "systemic_brief": {},
            },
            posture=control_posture,
            previous_payload=odylith_reasoning_payload if isinstance(odylith_reasoning_payload, Mapping) else None,
            config=_delivery_reasoning_config(repo_root=repo_root),
            provider=None,
        )
    scopes, case_queue, systemic_brief = _attach_case_metadata(
        scopes=scopes,
        reasoning_payload=odylith_reasoning_payload,
    )
    scopes.sort(key=lambda snapshot: (_SCOPE_TYPE_ORDER.index(snapshot["scope_type"]), snapshot["scope_id"]))
    indexes = {
        "grid": {"governance": _scope_key("grid", "governance")},
        "surfaces": {
            str(snapshot.get("scope_id", "")): str(snapshot.get("scope_key", ""))
            for snapshot in scopes
            if snapshot.get("scope_type") == "surface"
        },
        "workstreams": {
            str(snapshot.get("scope_id", "")): str(snapshot.get("scope_key", ""))
            for snapshot in scopes
            if snapshot.get("scope_type") == "workstream"
        },
        "components": {
            str(snapshot.get("scope_id", "")): str(snapshot.get("scope_key", ""))
            for snapshot in scopes
            if snapshot.get("scope_type") == "component"
        },
        "diagrams": {
            str(snapshot.get("scope_id", "")): str(snapshot.get("scope_key", ""))
            for snapshot in scopes
            if snapshot.get("scope_type") == "diagram"
        },
        "cases": {
            str(row.get("id", "")).strip(): str(row.get("scope_key", "")).strip()
            for row in case_queue
            if isinstance(row, Mapping) and str(row.get("id", "")).strip()
        },
    }
    grid_scope_key = _scope_key("grid", "governance")
    scope_lookup = {str(snapshot.get("scope_key", "")): snapshot for snapshot in scopes}
    grid_snapshot = scope_lookup.get(grid_scope_key, {})
    comparable = [
        snapshot
        for snapshot in scopes
        if snapshot.get("scope_type") in {"surface", "workstream", "component", "diagram"}
    ]
    highest_severity_snapshot = min(comparable, key=_scope_sort_tuple, default=grid_snapshot)
    highest_risk_snapshot = max(
        comparable,
        key=lambda snapshot: int(snapshot.get("scores", {}).get("decision_debt", 0) or 0),
        default=grid_snapshot,
    )
    payload: dict[str, Any] = {
        "version": "v4",
        "generated_utc": "",
        "scopes": scopes,
        "case_queue": case_queue,
        "indexes": indexes,
        "summary": {
            "grid_scope": grid_scope_key,
            "highest_severity_scope": _summary_scope(highest_severity_snapshot),
            "highest_risk_scope": _summary_scope(highest_risk_snapshot),
            "grid_action": str(grid_snapshot.get("operator_readout", {}).get("action", "")).strip()
            if isinstance(grid_snapshot.get("operator_readout"), Mapping)
            else "",
            "queue_size": len(case_queue),
            "top_queue_item": dict(case_queue[0]) if case_queue else {},
        },
        "systemic_brief": systemic_brief,
    }
    return payload


def validate_delivery_intelligence_artifact(payload: Mapping[str, Any]) -> list[str]:
    """Validate artifact shape and headline-content guardrails."""

    return _validate_artifact_payload(payload)


def load_delivery_intelligence_artifact(
    *,
    repo_root: Path,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Load the runtime artifact or build it on demand when absent.

    Renderers use this to stay functional in isolated tests where sync has not
    yet materialized the runtime JSON.
    """

    target = output_path or _resolve(repo_root, DEFAULT_OUTPUT_PATH)
    payload = _read_json(target)
    if payload and not validate_delivery_intelligence_artifact(payload):
        return payload
    return build_delivery_intelligence_artifact(repo_root=repo_root)


def slice_delivery_intelligence_for_surface(
    *,
    payload: Mapping[str, Any],
    surface: str,
) -> dict[str, Any]:
    """Return a renderer-friendly slice of the shared artifact."""

    scopes = payload.get("scopes", []) if isinstance(payload.get("scopes"), list) else []
    indexes = payload.get("indexes", {}) if isinstance(payload.get("indexes"), Mapping) else {}
    scope_lookup = {
        str(snapshot.get("scope_key", "")): snapshot
        for snapshot in scopes
        if isinstance(snapshot, Mapping)
    }
    result: dict[str, Any] = {
        "version": str(payload.get("version", "v4")),
        "summary": dict(payload.get("summary", {})) if isinstance(payload.get("summary"), Mapping) else {},
        "case_queue": [
            dict(row)
            for row in payload.get("case_queue", [])
            if isinstance(row, Mapping)
        ],
        "systemic_brief": dict(payload.get("systemic_brief", {})) if isinstance(payload.get("systemic_brief"), Mapping) else {},
        "surface_scope": str(indexes.get("surfaces", {}).get(surface, "")) if isinstance(indexes.get("surfaces"), Mapping) else "",
        "grid_scope": str(indexes.get("grid", {}).get("governance", "")) if isinstance(indexes.get("grid"), Mapping) else "",
        "components": {},
        "workstreams": {},
        "diagrams": {},
        "surfaces": {},
    }
    for bucket in ("components", "workstreams", "diagrams", "surfaces"):
        mapping = indexes.get(bucket, {}) if isinstance(indexes.get(bucket), Mapping) else {}
        target: dict[str, Any] = {}
        for scope_id, scope_key in mapping.items():
            snapshot = scope_lookup.get(str(scope_key))
            if snapshot is not None:
                clone = dict(snapshot)
                readout = clone.get("operator_readout", {}) if isinstance(clone.get("operator_readout"), Mapping) else {}
                clone["operator_readout"] = operator_readout.suppress_visible_duplicates(
                    readout=readout,
                    surface=surface,
                )
                target[str(scope_id)] = clone
        result[bucket] = target
    grid_snapshot = scope_lookup.get(result["grid_scope"])
    if grid_snapshot is not None:
        clone = dict(grid_snapshot)
        clone["operator_readout"] = operator_readout.suppress_visible_duplicates(
            readout=clone.get("operator_readout", {}) if isinstance(clone.get("operator_readout"), Mapping) else {},
            surface=surface,
        )
        result["grid"] = clone
    surface_snapshot = scope_lookup.get(result["surface_scope"])
    if surface_snapshot is not None:
        clone = dict(surface_snapshot)
        clone["operator_readout"] = operator_readout.suppress_visible_duplicates(
            readout=clone.get("operator_readout", {}) if isinstance(clone.get("operator_readout"), Mapping) else {},
            surface=surface,
        )
        result["surface"] = clone
    return result


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith sync",
        description="Build or validate the shared delivery-intelligence runtime artifact.",
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--max-review-age-days", type=int, default=DEFAULT_MAX_REVIEW_AGE_DAYS)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    output_path = _resolve(repo_root, args.output)
    payload = build_delivery_intelligence_artifact(
        repo_root=repo_root,
        max_review_age_days=int(args.max_review_age_days),
    )
    payload["generated_utc"] = stable_generated_utc.resolve_for_json_file(
        output_path=output_path,
        payload=payload,
    )
    errors = validate_delivery_intelligence_artifact(payload)
    if errors:
        for error in errors:
            print(error)
        return 1

    rendered = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.check_only:
        if not output_path.is_file():
            print(f"delivery intelligence artifact missing: {output_path}")
            return 2
        existing = output_path.read_text(encoding="utf-8")
        if existing != rendered:
            print("delivery intelligence artifact is stale")
            print(f"run `{display_command('sync', '--repo-root', str(repo_root), '--force')}`")
            return 2
        print("delivery intelligence artifact is current")
        return 0

    wrote_output = odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=output_path,
        content=rendered,
        lock_key=str(output_path),
    )
    if wrote_output:
        print(f"wrote delivery intelligence artifact: {output_path.relative_to(repo_root)}")
    else:
        print("delivery intelligence artifact is current")
    return 0


__all__ = [
    "DEFAULT_OUTPUT_PATH",
    "build_delivery_intelligence_artifact",
    "DEFAULT_CONTROL_POSTURE_PATH",
    "DEFAULT_ODYLITH_REASONING_PATH",
    "load_delivery_intelligence_artifact",
    "slice_delivery_intelligence_for_surface",
    "validate_delivery_intelligence_artifact",
    "main",
]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
