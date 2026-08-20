"""Compare independent Greenfield source hypotheses by typed citation custody."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_atomic_source_custody import (
    atomic_source_candidates_from_catalog,
    atomic_source_candidates_without_discarded,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_layered_authoring import (
    SEMANTIC_PARTITIONED_AUTHOR_VERSION,
    compile_layered_source_authority,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_parallel_materiality import (
    align_source_policy_kinds_to_materiality,
    assemble_parallel_materiality_assessment,
    require_materiality_source_coverage,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_authoring import (
    compile_source_partitioned_graph,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    semantic_evidence_block_catalog,
    semantic_source_refs_overlap,
)


def source_candidate_discarded_refs(
    candidate: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Return the unique discarded citations declared by one source hypothesis."""

    boundary = _source_boundary(candidate)
    discarded = boundary.get("discarded_evidence")
    if not isinstance(discarded, list) or any(
        not isinstance(row, Mapping) for row in discarded
    ):
        raise ValueError("partitioned source discarded evidence is malformed")
    refs: list[dict[str, Any]] = []
    for row in discarded:
        for ref in _source_refs(
            row, label="partitioned source discarded evidence"
        ):
            value = dict(ref)
            if value not in refs:
                refs.append(value)
    return refs


def independently_confirmed_discarded_refs(
    first: object,
    second: object,
    *,
    evidence_sources: Mapping[str, str],
) -> list[dict[str, Any]]:
    """Return discarded refs only when two hypotheses cite the same exact spans."""

    if not isinstance(first, list) or not isinstance(second, list):
        raise ValueError("independent discarded evidence is malformed")
    if (
        not first
        or len(first) != len(second)
        or any(not isinstance(row, Mapping) for row in (*first, *second))
    ):
        return []
    matched: set[int] = set()
    for left in first:
        matches = [
            index
            for index, right in enumerate(second)
            if semantic_source_refs_overlap(
                left,
                right,
                evidence_sources=evidence_sources,
            )
        ]
        if len(matches) != 1 or matches[0] in matched:
            return []
        matched.add(matches[0])
    return [dict(row) for row in first]


def source_candidate_policy_kind_assignments(
    candidate: Mapping[str, Any],
    *,
    conflict_refs: Sequence[Mapping[str, Any]],
    evidence_sources: Mapping[str, str],
) -> dict[tuple[str, str, int], str | None]:
    """Map exact conflict citations to one typed policy kind per hypothesis."""

    policies = _source_boundary(candidate).get("policies")
    if not isinstance(policies, list) or any(
        not isinstance(policy, Mapping) for policy in policies
    ):
        raise ValueError("partitioned source policies are malformed")
    result: dict[tuple[str, str, int], str | None] = {}
    for conflict_ref in conflict_refs:
        kinds = {
            str(policy.get("policy_kind") or "")
            for policy in policies
            for policy_ref in _source_refs(
                policy, label="partitioned source policy custody"
            )
            if semantic_source_refs_overlap(
                conflict_ref,
                policy_ref,
                evidence_sources=evidence_sources,
            )
        }
        result[source_ref_identity(conflict_ref)] = (
            next(iter(kinds)) if len(kinds) == 1 else None
        )
    return result


def source_candidate_material_ambiguity(
    candidate: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Return the one source-authored material ambiguity, if present."""

    ambiguities = _source_boundary(candidate).get("ambiguities")
    if not isinstance(ambiguities, list) or any(
        not isinstance(row, Mapping) for row in ambiguities
    ):
        raise ValueError("partitioned source ambiguities are malformed")
    if not ambiguities:
        return None
    if len(ambiguities) != 1:
        raise ValueError("partitioned source has more than one material ambiguity")
    row = dict(ambiguities[0])
    field = row.get("materiality_field")
    question = row.get("question")
    if not isinstance(field, str) or not field or not isinstance(question, str) or not question:
        raise ValueError("partitioned source material ambiguity is malformed")
    refs = _source_refs(row, label="partitioned source material ambiguity")
    if not refs:
        raise ValueError("partitioned source material ambiguity lacks evidence")
    return {**row, "source_refs": [dict(ref) for ref in refs]}


def independent_source_materiality_observation(
    candidates: Sequence[Mapping[str, Any]],
    *,
    decision: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Return one typed two-source challenge to the critic, if independently proven."""

    if len(candidates) != 2:
        return None
    outcome = decision.get("outcome")
    fields = decision.get("fields")
    if not isinstance(outcome, Mapping) or not isinstance(fields, Mapping):
        raise ValueError("materiality decision is malformed")
    decision_name = str(outcome.get("decision") or "")
    if decision_name == "clarification_required":
        clarification = outcome.get("clarification")
        if not isinstance(clarification, Mapping):
            raise ValueError("materiality clarification is malformed")
        field = str(clarification.get("field") or "")
        presences = [_source_axis_presence(candidate, field) for candidate in candidates]
        independently_ambiguous = all(
            _source_has_field_ambiguity(candidate, field) for candidate in candidates
        )
        if all(value is True for value in presences) and not independently_ambiguous:
            return _materiality_observation(
                status="critic_clarification_disputed",
                field=field,
                presences=presences,
            )
        if set(presences) == {False, True} and not independently_ambiguous:
            return _materiality_observation(
                status="source_axis_disagreement",
                field=field,
                presences=presences,
            )
        return None
    if decision_name != "authorize_graph":
        raise ValueError("materiality decision outcome is unsupported")
    for field in ("visible_result", "role"):
        field_decision = fields.get(field)
        if not isinstance(field_decision, Mapping) or field_decision.get(
            "status"
        ) not in {"explicit", "source_entailable"}:
            continue
        presences = [_source_axis_presence(candidate, field) for candidate in candidates]
        if not all(value is False for value in presences):
            continue
        if field == "role" and not all(
            _source_axis_presence(candidate, "visible_result") is True
            for candidate in candidates
        ):
            continue
        return _materiality_observation(
            status="critic_authorization_disputed",
            field=field,
            presences=presences,
        )
    return None


def source_materiality_candidates(
    source_receipt: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Return the exact candidate graphs preserved by a source-wave receipt."""

    rows = source_receipt.get("hypothesis_candidates")
    if not isinstance(rows, list):
        rows = source_receipt.get("partitioned_candidates")
    if not isinstance(rows, list):
        return []
    candidates: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, Mapping) or not isinstance(
            raw.get("candidate"), Mapping
        ):
            raise ValueError("source hypothesis candidates are malformed")
        candidates.append(dict(raw["candidate"]))
    return candidates


def independently_confirmed_material_ambiguity(
    first: Mapping[str, Any] | None,
    second: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Return one ambiguity only when both source authors name the same field."""

    if first is None or second is None:
        return None
    first_field = first.get("materiality_field")
    if not first_field or second.get("materiality_field") != first_field:
        return None
    first_refs = first.get("source_refs")
    second_refs = second.get("source_refs")
    if (
        not isinstance(first_refs, list)
        or not first_refs
        or not isinstance(second_refs, list)
        or not second_refs
    ):
        raise ValueError("independent source ambiguity custody is malformed")
    return dict(second)


def materiality_handoff_source(
    source_receipt: Mapping[str, Any], *, observation: Mapping[str, Any]
) -> dict[str, Any]:
    """Seal two existing source hypotheses as one reusable materiality handoff."""

    result = dict(source_receipt)
    rows = result.get("hypothesis_candidates")
    if not isinstance(rows, list):
        rows = result.get("partitioned_candidates")
    if not isinstance(rows, list) or len(rows) != 2:
        raise ValueError("materiality handoff requires two source hypotheses")
    result.update(
        validation_status="reusable_source_pair",
        source_pair_dispute="materiality",
        source_candidate_adjudication=None,
        hypothesis_candidates=[dict(row) for row in rows],
        materiality_observation=dict(observation),
    )
    return result


def _materiality_observation(
    *, status: str, field: str, presences: Sequence[bool | None]
) -> dict[str, Any]:
    return {
        "status": status,
        "materiality_field": field,
        "source_axis_presence": list(presences),
        "source_hypothesis_count": len(presences),
    }


def _source_axis_presence(
    candidate: Mapping[str, Any], field: str
) -> bool | None:
    source = candidate.get("source")
    path = source.get("path") if isinstance(source, Mapping) else None
    boundary = source.get("boundary") if isinstance(source, Mapping) else None
    collections = {
        "identity": (path, "identities"),
        "role": (path, "actors"),
        "first_path": (path, "workflow_steps"),
        "state_object": (path, "state_objects"),
        "visible_result": (path, "visible_outputs"),
        "dependency": (boundary, "external_systems"),
    }
    if field in collections:
        owner, name = collections[field]
        rows = owner.get(name) if isinstance(owner, Mapping) else None
        if not isinstance(rows, list):
            raise ValueError("partitioned source material axis is malformed")
        return bool(rows)
    if field in {"constraint", "non_goal"}:
        policies = boundary.get("policies") if isinstance(boundary, Mapping) else None
        if not isinstance(policies, list) or any(
            not isinstance(policy, Mapping) for policy in policies
        ):
            raise ValueError("partitioned source policies are malformed")
        kind = "operating_invariant" if field == "constraint" else "excluded_capability"
        return any(policy.get("policy_kind") == kind for policy in policies)
    if field == "component_boundary":
        return None
    raise ValueError("materiality field is unsupported")


def _source_has_field_ambiguity(
    candidate: Mapping[str, Any], field: str
) -> bool:
    ambiguities = _source_boundary(candidate).get("ambiguities")
    if not isinstance(ambiguities, list) or any(
        not isinstance(row, Mapping) for row in ambiguities
    ):
        raise ValueError("partitioned source ambiguities are malformed")
    return any(row.get("materiality_field") == field for row in ambiguities)


def source_ref_identity(value: Mapping[str, Any]) -> tuple[str, str, int]:
    """Return the exact identity of one source citation."""

    occurrence = value.get("occurrence")
    if (
        not isinstance(occurrence, int)
        or isinstance(occurrence, bool)
        or not value.get("source_id")
        or not value.get("quote")
    ):
        raise ValueError("partitioned source citation is malformed")
    return str(value["source_id"]), str(value["quote"]), occurrence


def admit_source_only_authority(
    candidate: Mapping[str, Any], *, decision: Mapping[str, Any],
    evidence_sources: Mapping[str, str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Admit source-only truth without granting paired completion authority."""

    if candidate.get("version") != SEMANTIC_PARTITIONED_AUTHOR_VERSION:
        raise ValueError("partitioned graph hypothesis uses an unsupported version")
    source_hypothesis = candidate.get("source")
    if not isinstance(source_hypothesis, Mapping):
        raise ValueError("partitioned source hypothesis is malformed")
    admitted_source = align_source_policy_kinds_to_materiality(
        source_hypothesis, decision
    )
    source = compile_source_partitioned_graph(admitted_source)
    require_materiality_source_coverage(
        decision, source, evidence_sources=evidence_sources
    )
    source_candidates = atomic_source_candidates_without_discarded(
        atomic_source_candidates_from_catalog(
            semantic_evidence_block_catalog(evidence_sources)
        ),
        discarded_source_refs=source_candidate_discarded_refs(candidate),
        evidence_sources=evidence_sources,
    )
    assessment = assemble_parallel_materiality_assessment(
        decision,
        source_candidates,
        evidence_sources=evidence_sources,
    )
    authority = compile_layered_source_authority(
        source,
        assessment=assessment,
        evidence_sources=evidence_sources,
    )
    adjudication = authority.get("source_candidate_adjudication")
    if not isinstance(adjudication, Mapping):
        raise ValueError("source-only candidate adjudication is malformed")
    return dict(admitted_source), dict(adjudication)


def _source_boundary(candidate: Mapping[str, Any]) -> Mapping[str, Any]:
    source = candidate.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("partitioned source hypothesis is malformed")
    boundary = source.get("boundary")
    if not isinstance(boundary, Mapping):
        raise ValueError("partitioned source boundary is malformed")
    return boundary


def _source_refs(
    value: Mapping[str, Any], *, label: str
) -> list[Mapping[str, Any]]:
    refs = value.get("source_refs")
    if not isinstance(refs, list) or any(
        not isinstance(ref, Mapping) for ref in refs
    ):
        raise ValueError(f"{label} is malformed")
    return refs


__all__ = [
    "admit_source_only_authority",
    "independent_source_materiality_observation",
    "independently_confirmed_material_ambiguity",
    "independently_confirmed_discarded_refs",
    "materiality_handoff_source",
    "source_candidate_discarded_refs",
    "source_candidate_material_ambiguity",
    "source_candidate_policy_kind_assignments",
    "source_materiality_candidates",
    "source_ref_identity",
]
