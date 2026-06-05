"""Differentiate overlapping greenfield component contracts before writes."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common.value_coercion import dedupe_strings
from odylith.runtime.domain_intelligence import greenfield_component_contract_targets as contract_targets
from odylith.runtime.domain_intelligence.greenfield_actor_terms import starts_with_generic_actor_label
from odylith.runtime.domain_intelligence.greenfield_component_axes import (
    ComponentAxis,
    derive_component_axis,
)
from odylith.runtime.domain_intelligence.greenfield_component_contract import (
    boundary_from_contract,
    dependencies_from_contract,
    interfaces_from_contract,
    responsibility_from_contract,
    risks_from_contract,
    validation_from_contract,
)
from odylith.runtime.domain_intelligence.greenfield_component_contract_quality import (
    normalize_contract,
    public_prose_quality_issues,
    rendered_component_spec_quality_issues,
)
from odylith.runtime.domain_intelligence.greenfield_component_semantic_contract import (
    derive_component_semantic_contract,
)
from odylith.runtime.domain_intelligence.greenfield_component_term_index import ordered_domain_terms
from odylith.runtime.domain_intelligence.greenfield_component_terms import (
    domain_terms,
    enrich_owned_state_from_io,
    natural_phrase,
    split_contract_clauses,
)
from odylith.runtime.domain_intelligence.greenfield_component_term_windows import literal_label_compounds
from odylith.runtime.domain_intelligence.greenfield_component_term_windows import nearby_domain_terms
from odylith.runtime.domain_intelligence.greenfield_rows import dict_rows
from odylith.runtime.domain_intelligence.greenfield_text import clean_artifact_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import visible_words
from odylith.runtime.governance.component_spec_rendering import build_component_spec


_FALLBACK_NOISE_TERMS = {
    "behavior",
    "candidate",
    "component",
    "first",
    "greenfield",
    "local",
    "odylith",
    "owned",
    "owns",
    "path",
    "planned",
    "product",
    "proof",
    "rationale",
    "record",
    "release",
    "relevant",
    "service",
    "state",
    "surface",
    "support",
    "supports",
    "system",
    "workspace",
}

_GENERATED_CONTRACT_MARKERS = (
    "accepted first-path input",
    "blocked-case evidence links",
    "command or event result",
    "component proof",
    "comparison display",
    "current decision summary",
    "role-appropriate status views",
    "role-specific actor visibility",
    "status timeline",
    "representative input covering",
    "required inputs",
)


def differentiate_component_contracts(proposal: dict[str, Any], *, max_passes: int = 5) -> bool:
    """Repair interchangeable generated component contracts before quality gates run."""

    components = dict_rows(proposal.get("components"))
    if len(components) < 2:
        return False
    changed = False
    for _pass in range(max_passes):
        targets = _contract_repair_targets(components, proposal=proposal)
        rows_by_label, indexes_by_label = _component_lookup(components)
        issues = rendered_component_spec_quality_issues(
            _render_component_specs(proposal),
            project_title=_project_title(proposal),
        )
        targets = [
            *targets,
            *contract_targets.repair_targets_from_spec_issues(
                issues,
                rows_by_label=rows_by_label,
                indexes_by_label=indexes_by_label,
            ),
        ]
        if not targets:
            return changed
        before = _contract_fingerprint(components)
        for target in targets:
            _repair_row(
                target.row,
                proposal=proposal,
                sibling=target.sibling,
                previous_label=_adjacent_label(components, target.index - 1),
                next_label=_adjacent_label(components, target.index + 1),
            )
        changed |= before != _contract_fingerprint(components)
        if before == _contract_fingerprint(components):
            break
    return changed


def component_spec_preflight_issues(proposal: Mapping[str, Any]) -> list[str]:
    """Return operator-safe spec quality issues for the repaired proposal."""

    specs = _render_component_specs(proposal)
    if not specs:
        return []
    raw_issues = rendered_component_spec_quality_issues(specs, project_title=_project_title(proposal))
    return contract_targets.operator_component_spec_issues(raw_issues)


def _contract_repair_targets(
    rows: Sequence[dict[str, Any]],
    *,
    proposal: Mapping[str, Any],
) -> list[contract_targets.RepairTarget]:
    targets: list[contract_targets.RepairTarget] = []
    for index, row in enumerate(rows):
        contract = row.get("component_contract")
        if isinstance(contract, Mapping) and (
            _contract_needs_repair(contract) or _contract_misses_local_axis(row=row, contract=contract, proposal=proposal)
        ):
            sibling = rows[index + 1] if index + 1 < len(rows) else (rows[index - 1] if index else None)
            targets.append(contract_targets.RepairTarget(index=index, row=row, sibling=sibling))
    return targets


def _contract_needs_repair(contract: Mapping[str, Any]) -> bool:
    if public_prose_quality_issues(contract):
        return True
    values = text_values(contract)
    if any(_starts_with_generic_actor(value) for value in values):
        return True
    joined = " ".join(values).casefold()
    return any(
        marker in joined
        for marker in (
            *_GENERATED_CONTRACT_MARKERS,
            "representative input covering",
            "component proof",
            "accepted first-path input and state object",
        )
    )


def _contract_misses_local_axis(*, row: Mapping[str, Any], contract: Mapping[str, Any], proposal: Mapping[str, Any]) -> bool:
    axis = _axis_for(row=row, proposal=proposal)
    if axis.key.startswith("fallback_"):
        return False
    label_text = _component_label(row, 0)
    description_text = _clean(row.get("source_system_description"))
    local_score = _axis_local_score(axis, label_text=label_text, description_text=description_text)
    if local_score < 24:
        return False
    contract_text = " ".join(text_values(contract))
    expected_hits = min(4, max(2, _trigger_hits(axis.triggers, label_text)))
    if _trigger_hits(axis.triggers, contract_text) < expected_hits:
        return True
    expected_terms = _axis_distinctive_terms(axis)
    if expected_terms:
        actual_terms = set(ordered_domain_terms(contract_text))
        required_terms = min(5, max(3, len(expected_terms) // 4))
        if len(expected_terms & actual_terms) < required_terms:
            return True
    return False


def _starts_with_generic_actor(value: str) -> bool:
    return starts_with_generic_actor_label(_clean(value))


def _axis_distinctive_terms(axis: ComponentAxis) -> set[str]:
    """Return ownership terms that must survive contract rendering for this axis."""

    terms = set(
        ordered_domain_terms(
            " ".join(
                [
                    axis.owned_state,
                    axis.accepted_inputs,
                    axis.produced_outputs,
                    axis.states_or_transitions,
                    " ".join(axis.local_proof),
                ]
            )
        )
    )
    return {
        term
        for term in terms
        if term
        not in {
            "accepted",
            "actor",
            "blocker",
            "boundary",
            "context",
            "downstream",
            "handoff",
            "input",
            "local",
            "marker",
            "output",
            "proof",
            "record",
            "reference",
            "result",
            "state",
            "status",
            "upstream",
            "validation",
        }
    }


def _render_component_specs(proposal: Mapping[str, Any]) -> dict[str, str]:
    rows = dict_rows(proposal.get("components"))
    specs: dict[str, str] = {}
    for index, row in enumerate(rows):
        label = _component_label(row, index)
        specs[label] = build_component_spec(
            component_id=_clean(row.get("component_id")) or _slug(label),
            label=label,
            path=_clean(row.get("intended_path")) or _clean(row.get("path")),
            kind=_clean(row.get("kind")) or "service",
            status=_clean(row.get("status")) or "planned",
            sources=tuple(text_values(row.get("evidence_tier")) or ("user_intent",)),
            workstreams=tuple(text_values(row.get("workstreams"))),
            diagrams=tuple(text_values(row.get("diagrams"))),
            responsibility=_clean(row.get("responsibility")),
            boundary=_clean(row.get("boundary")),
            dependencies=tuple(text_values(row.get("dependencies"))),
            interfaces=tuple(text_values(row.get("interfaces"))),
            validation=tuple(text_values(row.get("validation"))),
            risks=tuple(text_values(row.get("risks"))),
            qualification=_clean(row.get("qualification")) or "candidate",
            component_contract=row.get("component_contract") if isinstance(row.get("component_contract"), Mapping) else None,
        )
    return specs


def _repair_row(
    row: dict[str, Any],
    *,
    proposal: Mapping[str, Any],
    sibling: Mapping[str, Any] | None,
    previous_label: str,
    next_label: str,
) -> None:
    label = _component_label(row, 0)
    sibling_label = _component_label(sibling, 0) if isinstance(sibling, Mapping) else ""
    axis = _axis_for(row=row, proposal=proposal)
    sibling_axis = _axis_for(row=sibling, proposal=proposal) if isinstance(sibling, Mapping) else None
    title_state = f"{_project_title(proposal)} state" if _project_title(proposal) else "accepted state"
    state_label = _state_label(_proposal_text(proposal, "state_object", "intent.state_object"), fallback=title_state)
    upstream = previous_label or "accepted first-path input"
    downstream = next_label or "release proof review"
    outside = _outside_boundary(axis=axis, sibling_axis=sibling_axis, sibling_label=sibling_label)
    previous_contract = row.get("component_contract") if isinstance(row.get("component_contract"), Mapping) else {}
    axis_payload = _axis_payload(
        axis=axis,
        row=row,
        label=label,
        state_label=state_label,
        outside=outside,
        sibling_label=sibling_label,
        upstream=upstream,
        downstream=downstream,
    )
    semantic_contract = derive_component_semantic_contract(
        row,
        proposal=proposal,
        sibling=sibling,
        previous_label=previous_label,
        next_label=next_label,
        state_label=state_label,
    )
    contract = normalize_contract(
        _contract_payload(
            axis_payload,
            semantic_contract,
            axis=axis,
            local_score=_axis_local_score(
                axis,
                label_text=label,
                description_text=_clean(row.get("source_system_description")),
            ),
        )
    )
    row["component_contract"] = contract
    _sync_generated_component_fields(row, label=label, contract=contract, previous_contract=previous_contract)


def _axis_for(*, row: Mapping[str, Any] | None, proposal: Mapping[str, Any]) -> ComponentAxis:
    if not isinstance(row, Mapping):
        return _fallback_axis("sibling", _proposal_context(proposal))
    label_text = _component_label(row, 0)
    description_text = _clean(row.get("source_system_description"))
    axis = derive_component_axis(
        label_text=label_text,
        context_text=" ".join(
            text
            for text in (
                description_text,
                _proposal_context(proposal),
            )
            if text
        ),
    )
    if axis is not None:
        return axis
    return _fallback_axis(
        label_text,
        _fallback_context(row=row, proposal=proposal),
        focus=_focus_phrase(_scrub_generated_context(_clean(row.get("source_system_description")))),
    )


def _fallback_axis(label: str, context: str, *, focus: str = "") -> ComponentAxis:
    label_terms = domain_terms(label, noise_terms=_FALLBACK_NOISE_TERMS)
    context_terms = domain_terms(context, noise_terms=_FALLBACK_NOISE_TERMS)
    nearby_terms = nearby_domain_terms(label_terms, context, noise_terms=_FALLBACK_NOISE_TERMS)
    extra_terms = _unique_terms(
        [
            *[term for term in nearby_terms if term not in label_terms],
            *[term for term in context_terms if term not in label_terms],
        ]
    )
    primary = " ".join(label_terms[:4]) or _clean(label).casefold() or "component"
    secondary = focus or natural_phrase(extra_terms[:4]) or natural_phrase(context_terms[:4]) or "local result context"
    input_focus = natural_phrase(extra_terms[4:7]) or secondary
    output_focus = natural_phrase(extra_terms[7:10]) or secondary
    states = ", ".join(_unique_terms([*extra_terms[:5], "blocked", "validated", "handed-off"])[:7])
    return ComponentAxis(
        key=f"fallback_{_slug(primary)}",
        triggers=(),
        owned_state=f"{primary} state, {secondary}, local blockers, and recovery context",
        accepted_inputs=f"{primary} input, {input_focus} context, authorized actor, prior state, and validation notes",
        produced_outputs=f"{primary} result, {output_focus} update, blocked-state explanation, and next-step context",
        states_or_transitions=states,
        outside_boundary="sibling product responsibilities, upstream source truth, and release approval",
        local_proof=(
            f"{primary} input proves {secondary} before another step depends on it.",
            f"Invalid {input_focus} context blocks the {primary} result.",
            f"{primary} recovery context stays visible when {output_focus} changes.",
        ),
        unique_failure=f"{primary} can look complete while required {secondary} is missing, stale, or assigned to the wrong boundary.",
    )


def _contract_payload(
    axis_payload: Mapping[str, Any],
    semantic_contract: Any,
    *,
    axis: ComponentAxis,
    local_score: int,
) -> Mapping[str, Any]:
    _ = (axis, local_score)
    if not _semantic_contract_is_strong(semantic_contract):
        return axis_payload
    semantic_fields = dict(semantic_contract.fields)
    semantic_fields["owned_state"] = enrich_owned_state_from_io(
        semantic_fields.get("owned_state"),
        semantic_fields,
        noise_terms=_FALLBACK_NOISE_TERMS,
    )
    semantic_fields["outside_boundary"] = _join_contract_clauses(
        axis_payload.get("outside_boundary"),
        semantic_fields.get("outside_boundary"),
    )
    return semantic_fields


def _axis_payload(
    *,
    axis: ComponentAxis,
    row: Mapping[str, Any],
    label: str,
    state_label: str,
    outside: str,
    sibling_label: str,
    upstream: str,
    downstream: str,
) -> dict[str, Any]:
    label_focus = literal_label_compounds(label, noise_terms=_FALLBACK_NOISE_TERMS)
    owned_state = _join_contract_clauses(", ".join(label_focus[:3]), f"{axis.owned_state} for {state_label}")
    accepted_inputs = axis.accepted_inputs
    produced_outputs = axis.produced_outputs
    local_proof = _local_proof(axis=axis, label=label, sibling_label=sibling_label)
    unique_failure = axis.unique_failure
    return {
        "owned_state": owned_state,
        "accepted_inputs": accepted_inputs,
        "produced_outputs": produced_outputs,
        "states_or_transitions": axis.states_or_transitions,
        "outside_boundary": outside,
        "local_proof": local_proof,
        "upstream_truth": upstream,
        "downstream_consumers": downstream,
        "unique_failure": unique_failure,
    }


def _semantic_contract_is_strong(semantic_contract: Any) -> bool:
    local_terms = getattr(semantic_contract, "local_terms", ())
    confidence = int(getattr(semantic_contract, "confidence", 0) or 0)
    return confidence >= 8 and len(tuple(local_terms)) >= 3


def _join_contract_clauses(*values: Any) -> str:
    clauses: list[str] = []
    for value in values:
        clauses.extend(_clean_contract_clause(clause) for clause in split_contract_clauses(value))
    clauses = [clause for clause in clauses if clause]
    return natural_phrase(_unique_terms(clauses))


def _outside_boundary(*, axis: ComponentAxis, sibling_axis: ComponentAxis | None, sibling_label: str) -> str:
    outside = _clean_contract_clause(axis.outside_boundary)
    if sibling_axis:
        sibling_focus = _clean_contract_clause(sibling_axis.owned_state.split(" for ", 1)[0])
        sibling_name = f" owned by {sibling_label}" if sibling_label else ""
        outside = _join_contract_clauses(outside, f"{sibling_focus}{sibling_name}" if sibling_focus else "")
    return outside


def _clean_contract_clause(value: Any) -> str:
    text = _clean(value)
    text = re.sub(r"\bresponsibilities\s+not\s+named\s+by\s+(?:this\s+)?component\s+boundary\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:guide|guides|guided|guiding)\s+(?:the\s+)?first\s+path\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:capture|captures|captured|capturing)\s+allowed\s+commands?\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:expose|exposes|exposed|exposing)\s+blocked\s+states?\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:local\s+)?blockers?\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\brecovery\s+context\s+owned\s+elsewhere\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\brecovery\s+context\s+owned\s+by\s+[^,;]+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bowns?\s+required\s+blocked-case\s+link\s+confirmed\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bmaintains?\s+[a-z0-9 -]*\bcore\s+unit\s+protocol\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bmutation\s+of\s+(?:original|upstream)\s+(?:input\s+)?facts\b", "original input facts", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcombines?\s+(?=reference|range|ranges|data|input|inputs)\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bsilent\s+overwrite\s+of\s+another\s+component\s+result(?:\s+state)?\b", "another component result", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*;\s*", "; ", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"(?:,\s*){2,}", ", ", text)
    text = re.sub(r"^\s*(?:(?:and|or)\b\s*|,|;)+\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*(?:(?:and|or)\b\s*|,|;)+\s*$", "", text, flags=re.IGNORECASE)
    return _clean(text).strip(" .,;")


def _local_proof(*, axis: ComponentAxis, label: str, sibling_label: str) -> list[str]:
    proofs = list(axis.local_proof)
    if sibling_label:
        proofs.append(f"{label} refuses {sibling_label} ownership while preserving its own local proof.")
    return proofs


def _sync_generated_component_fields(
    row: dict[str, Any],
    *,
    label: str,
    contract: Mapping[str, Any],
    previous_contract: Mapping[str, Any],
) -> None:
    if _weak_text(row.get("responsibility")) or _reuses_contract_text(row.get("responsibility"), previous_contract):
        row["responsibility"] = responsibility_from_contract(label, contract)
    if _weak_text(row.get("boundary")) or _reuses_contract_text(row.get("boundary"), previous_contract):
        row["boundary"] = boundary_from_contract(label, contract)
    if _weak_sequence(row.get("interfaces")) or _sequence_reuses_contract_text(row.get("interfaces"), previous_contract):
        row["interfaces"] = interfaces_from_contract(contract)
    if _weak_sequence(row.get("dependencies")) or _sequence_reuses_contract_text(row.get("dependencies"), previous_contract):
        row["dependencies"] = dependencies_from_contract(contract)
    if _weak_sequence(row.get("validation")) or _sequence_reuses_contract_text(row.get("validation"), previous_contract):
        row["validation"] = validation_from_contract(contract)
    if _weak_sequence(row.get("risks")) or _sequence_reuses_contract_text(row.get("risks"), previous_contract):
        row["risks"] = risks_from_contract(label, contract)


def _component_lookup(rows: Sequence[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    rows_by_label: dict[str, dict[str, Any]] = {}
    indexes_by_label: dict[str, int] = {}
    for index, row in enumerate(rows):
        label = _component_label(row, index)
        rows_by_label[label] = row
        indexes_by_label[label] = index
    return rows_by_label, indexes_by_label


def _component_label(row: Mapping[str, Any] | None, index: int) -> str:
    if not isinstance(row, Mapping):
        return ""
    return _clean(row.get("label")) or _clean(row.get("name")) or _clean(row.get("component_id")) or f"Component {index + 1}"


def _adjacent_label(rows: Sequence[Mapping[str, Any]], index: int) -> str:
    if index < 0 or index >= len(rows):
        return ""
    return _component_label(rows[index], index)


def _contract_fingerprint(rows: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    return tuple(str(row.get("component_contract", "")) for row in rows)


def _project_title(proposal: Mapping[str, Any]) -> str:
    return _proposal_text(proposal, "title", "intent.title")


def _proposal_context(proposal: Mapping[str, Any]) -> str:
    return " ".join(
        _proposal_text(proposal, key)
        for key in (
            "title",
            "intent.title",
            "state_object",
            "intent.state_object",
            "first_path",
            "intent.first_path",
            "proof_boundary",
            "intent.proof_boundary",
            "external_systems",
            "intent.external_systems",
        )
    )


def _fallback_context(*, row: Mapping[str, Any], proposal: Mapping[str, Any]) -> str:
    return " ".join(
        text
        for text in (
            _component_label(row, 0),
            _scrub_generated_context(_clean(row.get("source_system_description"))),
            _proposal_context(proposal),
        )
        if text
    )


def _axis_local_score(axis: ComponentAxis, *, label_text: str, description_text: str) -> int:
    label_hits = _trigger_hits(axis.triggers, label_text)
    description_hits = _trigger_hits(axis.triggers, description_text)
    return label_hits * 12 + description_hits * 8


def _trigger_hits(triggers: Sequence[str], text: str) -> int:
    tokens = tuple(word.casefold() for word in visible_words(text))
    hits = 0
    for trigger in triggers:
        normalized = trigger.casefold()
        if any(token == normalized or token.startswith(normalized) for token in tokens):
            hits += 1
    return hits


def _scrub_generated_context(value: str) -> str:
    text = _clean(value)
    text = re.sub(r"\bRationale:\s*supports\s+the\s+accepted\s+first\s+path\s+and\s+proof\s+boundary\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bRelevant\s+behavior:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*Owns\s+[^.]+[.]\s*", "", text, flags=re.IGNORECASE)
    return _clean(text)


def _focus_phrase(context: str) -> str:
    text = _clean(context).strip(" .")
    text = re.sub(r"^[A-Z][A-Za-z0-9 ]{2,80}\s+[-–—]\s*", "", text)
    text = re.sub(
        r"^(?:accepts?|captures?|checks?|coordinates?|creates?|displays?|evaluates?|helps?|imports?|keeps?|"
        r"maintains?|normalizes?|owns?|presents?|records?|renders?|routes?|shows?|stores?|tracks?|validates?)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    first = re.split(r"[.;]", text, maxsplit=1)[0].strip(" .")
    return first if 4 <= len(first.split()) <= 18 else ""


def _unique_terms(values: Sequence[str]) -> list[str]:
    return dedupe_strings([_clean(value).casefold() for value in values])


def _proposal_text(proposal: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        current: Any = proposal
        for part in key.split("."):
            if not isinstance(current, Mapping):
                current = None
                break
            current = current.get(part)
        text = _clean(current)
        if text:
            return text
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    for key in keys:
        text = _clean(intent.get(key))
        if text:
            return text
    return ""


def _state_label(value: str, *, fallback: str) -> str:
    text = _clean(value)
    if not text:
        return fallback
    first = re.split(r"[.;]", text, maxsplit=1)[0].strip(" .")
    match = re.search(
        r"^(?:a|an|the)\s+(?P<label>.+?)\s+(?:tracks|records|stores|moves|captures|keeps|contains)\b",
        first,
        re.IGNORECASE,
    )
    if match:
        return _clean(match.group("label")).strip(" .") or fallback
    return first if len(first.split()) <= 10 else fallback


def _weak_text(value: Any) -> bool:
    text = _clean(value).casefold()
    if not text:
        return True
    return any(
        marker in text
        for marker in (
            "representative input covering",
            "first implementation plan",
            "accepted first path",
            "required inputs, rejected or blocked cases",
            "handoff boundaries for the confirmed first path",
            "valid transition, invalid input rejection",
            "responsibility and keeps it tied",
            "accepted inputs, produced outputs",
            "local refusal evidence",
            "validation evidence, and local handoff decisions",
            "owns combines reference ranges",
            "combines reference ranges with",
            "component proof",
        )
    )


def _weak_sequence(value: Any) -> bool:
    return _weak_text(" ".join(text_values(value)))


def _sequence_reuses_contract_text(value: Any, contract: Mapping[str, Any]) -> bool:
    return _reuses_contract_text(" ".join(text_values(value)), contract)


def _reuses_contract_text(value: Any, contract: Mapping[str, Any]) -> bool:
    text = _clean(value).casefold()
    if not text or not isinstance(contract, Mapping):
        return False
    for candidate in text_values(contract):
        marker = _contract_marker(candidate)
        if marker and marker in text:
            return True
    return False


def _contract_marker(value: str) -> str:
    text = _clean(value).casefold()
    for marker in _GENERATED_CONTRACT_MARKERS:
        if marker in text:
            return marker
    return ""


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _clean(value).casefold()).strip("-") or "component"


def _clean(value: Any) -> str:
    return clean_artifact_text(value)


__all__ = [
    "component_spec_preflight_issues",
    "differentiate_component_contracts",
]
