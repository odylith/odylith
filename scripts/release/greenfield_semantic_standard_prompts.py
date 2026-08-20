"""Typed prompt contracts for the bounded Greenfield production mechanism."""

from __future__ import annotations

from collections.abc import Mapping
import json
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    semantic_intent_authoring_protocol,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    semantic_intent_authoring_contract,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_completion_partitions import (
    semantic_unassigned_source_dependency_ids,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_layered_authoring import (
    SEMANTIC_COMPLETION_GRAPH_VERSION,
    SEMANTIC_PARTITIONED_AUTHOR_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_authoring import (
    SEMANTIC_SOURCE_BOUNDARY_GRAPH_VERSION,
    SEMANTIC_SOURCE_GRAPH_VERSION,
    SEMANTIC_SOURCE_PATH_GRAPH_VERSION,
    SEMANTIC_SOURCE_PARTITIONED_GRAPH_VERSION,
    SOURCE_ACCESS_MODES,
    SOURCE_BOUNDARY_COLLECTIONS,
    SOURCE_FACT_ID_PREFIXES,
    SOURCE_PATH_COLLECTIONS,
)


def unified_source_graph_prompt(
    *, prompt_text: str, evidence_catalog: Mapping[str, Mapping[str, Any]],
    model_budget_seconds: int,
) -> str:
    """Return one whole-source hypothesis contract without implementation authority."""

    authoring = semantic_intent_authoring_protocol()
    contract = {
        "deadline": {"stage_seconds": model_budget_seconds, "retries": 0},
        "authority": (
            "Author one whole source-entailable graph. Preserve path and boundary meaning in "
            "their exclusive typed collections, but decide neither final materiality nor "
            "implementation architecture. Do not choose between contradictory source claims."
        ),
        "version": SEMANTIC_SOURCE_PARTITIONED_GRAPH_VERSION,
        "path_contract": _source_path_contract(
            evidence_catalog, include_evidence=False
        ),
        "boundary_contract": _source_boundary_contract(
            evidence_catalog, include_evidence=False
        ),
        "evidence_blocks": _provider_catalog(evidence_catalog),
        "citation_contract": (
            "For each semantic proposition, return source_id, the smallest complete exact quote "
            "substring, and its one-based occurrence. Do not reuse one compound citation for "
            "different policy propositions or semantic kinds. Deterministic code validates every "
            "citation against the source bytes."
        ),
        "cross_partition_invariants": [
            "route discarded evidence only to discarded_evidence and nowhere in product truth",
            "put each source proposition in exactly one semantic kind",
            "preserve conflicting ownership claims without silently selecting a winner",
            "never turn a prohibited interaction target into an actor or dependency",
        ],
        "forbidden_mechanisms": authoring["forbidden_mechanisms"],
    }
    return (
        "Act as the independent whole-source Greenfield author. Use no tools, files, retries, "
        "validator feedback, regex, fuzzy matching, token heuristics, architecture guesses, or "
        "prose repair. Return only the complete typed source graph."
        f"\nOPERATOR_PROMPT\n{prompt_text}\nCONTRACT\n{_json(contract)}"
    )


def partitioned_graph_hypothesis_prompt(
    *, prompt_text: str, evidence_catalog: Mapping[str, Mapping[str, Any]],
    model_budget_seconds: int,
) -> str:
    """Return one time-zero source-plus-architecture hypothesis contract."""

    authoring = semantic_intent_authoring_protocol()
    contract = {
        "deadline": {"stage_seconds": model_budget_seconds, "retries": 0},
        "authority": (
            "Author one complete source-entailable graph and one provisional smallest "
            "implementation architecture directly from operator evidence. A separate prompt-only "
            "critic owns materiality; do not predict or replace that decision. The candidate is "
            "admitted only after both independent outputs finish."
        ),
        "version": SEMANTIC_PARTITIONED_AUTHOR_VERSION,
        "source_contract": {
            "version": SEMANTIC_SOURCE_PARTITIONED_GRAPH_VERSION,
            "path": _source_path_contract(evidence_catalog, include_evidence=False),
            "boundary": _source_boundary_contract(
                evidence_catalog, include_evidence=False
            ),
        },
        "completion_contract": {
            "version": SEMANTIC_COMPLETION_GRAPH_VERSION,
            "status": "complete",
            "topology": _system_topology_contract("single_system"),
            "source_fact_ids": (
                "Reference deterministic source IDs derived from ordered collections: identity.0; "
                "actor.N; step.N; state.N; output.N; dependency.N; constraint.N; non-goal.N."
            ),
            "edge_ownership": (
                "Return no implementation edge arrays. After source validation, the deterministic "
                "compiler binds the sole release system to every typed workflow step, state, "
                "visible output, dependency, operating constraint, and non-goal."
            ),
            "outside_boundary": (
                "Describe accepted behavior outside the system responsibility. Never place a "
                "discarded label, superseded evidence, or restriction marker in this field."
            ),
        },
        "evidence_blocks": _provider_catalog(evidence_catalog),
        "citation_contract": (
            "For every proposition and architecture edge, return source_id, the smallest complete "
            "exact quote substring, and its one-based occurrence. Do not reuse one compound "
            "citation across different semantic kinds. Deterministic code validates source bytes."
        ),
        "mandatory_challenges": authoring["mandatory_challenges"],
        "invariants": [
            "route discarded evidence only to discarded_evidence and nowhere in product truth",
            "put each source proposition in exactly one semantic kind",
            "preserve human, product, and system ownership exactly",
            "each actor fact cites every exact source mention used by its owned workflow actions, not only the actor's introduction",
            "preserve every supported workflow, state, output, dependency, constraint, and non-goal",
            "represent every source-described human action and every product or system event that changes state or produces a result as an ordered workflow_step; state and output facts never replace their changing or producing event",
            "a human receiving, seeing, or reviewing a visible output does not by that act produce it; bind produces to the source-entailable product or system event that makes the output visible",
            "author exactly one cohesive result system and no invented adapter",
            "author no governance narratives or quantitative targets",
        ],
        "forbidden_mechanisms": authoring["forbidden_mechanisms"],
    }
    return (
        "Act as one independent full Greenfield graph hypothesis author. Use no tools, files, "
        "retries, validator feedback, regex, fuzzy matching, token heuristics, or prose repair. "
        "Return only the typed source-plus-completion candidate."
        f"\nOPERATOR_PROMPT\n{prompt_text}\nCONTRACT\n{_json(contract)}"
    )


def final_graph_adjudication_prompt(
    *, prompt_text: str, evidence_catalog: Mapping[str, Mapping[str, Any]],
    materiality_hypothesis: Mapping[str, Any], source_hypothesis: Mapping[str, Any],
    discarded_hypothesis: object,
    relation_catalog: Mapping[str, Mapping[str, Any]],
    citation_registry: Mapping[str, Mapping[str, Any]],
    model_budget_seconds: int, topology_mode: str,
    clarification_only: bool = False,
) -> str:
    """Return one compact final relation and architecture adjudication contract."""

    authoring = semantic_intent_authoring_protocol()
    graph_contract = semantic_intent_authoring_contract()
    unassigned_dependency_ids = (
        []
        if clarification_only
        else list(semantic_unassigned_source_dependency_ids(source_hypothesis))
    )
    contract = {
        "deadline": {"stage_seconds": model_budget_seconds, "retries": 0},
        "authority": (
            "Accept the settled prompt-only clarification unchanged; author no facts, relations, "
            "architecture, discarded evidence, replacement question, or field rewrite."
            if clarification_only
            else
            "Treat the prompt-only materiality hypothesis as settled authority, accept it unchanged, "
            "select the exact admitted source relation IDs, and author the smallest sufficient "
            "implementation architecture. Source policy kinds have already been aligned to that "
            "authority by exact citations. Source facts are candidates, not authority: admit only "
            "supported correctly typed facts by exact fact ID and omit unsupported candidates. "
            "Source relations are immutable typed candidates: select them by exact relation ID; "
            "reject the source when a required non-policy fact or relation is missing or wrong rather "
            "than rewriting it."
        ),
        "materiality_field_semantics": authoring["materiality_field_semantics"],
        "materiality_decision_rules": authoring["materiality_decision_rules"],
        "implementation_relation_endpoints": (
            {} if clarification_only else graph_contract["relation_contracts"]
        ),
        "system_topology": (
            {} if clarification_only else _system_topology_contract(topology_mode)
        ),
        "evidence_blocks": _provider_catalog(evidence_catalog),
        "citation_contract": (
            "Return source_id, the smallest complete exact quote substring, and its one-based "
            "occurrence for each discarded proposition. Deterministic code validates every "
            "citation against the source bytes."
        ),
        "citation_registry": {
            citation_id: list(row.get("fact_ids", ()))
            for citation_id, row in citation_registry.items()
        },
        "candidate_relation_catalog": {
            relation_id: {
                "kind": row.get("kind"),
                "subject_id": row.get("subject_id"),
                "object_id": row.get("object_id"),
            }
            for relation_id, row in relation_catalog.items()
        },
        "unassigned_source_dependency_ids": unassigned_dependency_ids,
        "source_dependency_assignment": (
            "A source dependency without a source-assigned consumer is a valid source fact, not a "
            "missing source relation. Every listed dependency ID must be bound by depends_on from "
            "at least one authored internal system. Do not fabricate an identity or workflow-step "
            "source relation."
        ),
        "mandatory_challenges": authoring["mandatory_challenges"],
        "discarded_evidence_semantics": (
            "Evidence explicitly identified as obsolete, superseded, scratch-only, or forbidden "
            "from governed truth is provenance-only discarded evidence. Return its exact handles "
            "only in discarded_source_refs. It is not a product non-goal, operating constraint, "
            "dependency, component boundary, fact, relation, narrative, or architecture input."
        ),
        "final_graph_invariants": (
            [
                "accept the settled prompt-only materiality hypothesis unchanged",
                "return no graph or architecture in clarification-only mode",
                "return no discarded-evidence decision in clarification-only mode",
            ]
            if clarification_only
            else [
                "accept the settled prompt-only materiality hypothesis unchanged; this graph stage cannot reopen or clarify it",
                "treat the source graph as provisional while preserving the settled materiality decision",
                "constraint and non_goal citations have already aligned candidate policy kinds before this stage",
                "resolve evidence_status_misclassification only as materiality clarification; never report it as a rejected source finding",
                "select every supported correctly typed candidate fact and no unsupported candidate",
                "reject only when supported non-policy material meaning is omitted or wrongly typed and candidate selection cannot correct it",
                "select each source-assigned owned_by, changes, produces, depends_on, constrained_by, and excludes edge by exact candidate relation ID",
                "treat unassigned_source_dependency_ids as source-complete facts and bind each through implementation architecture depends_on",
                "for each state transition and visible output, verify the referenced workflow step actually performs that change or production",
                "keep discarded evidence absent from all product facts, relations, narratives, and architecture",
                "author no governance narratives or quantitative targets; deterministic projection owns them",
                "return one cohesive result system in standard mode and no invented adapter"
            ]
        ),
        "forbidden_mechanisms": authoring["forbidden_mechanisms"],
    }
    output_scope = (
        "Return only acceptance of the settled materiality hypothesis."
        if clarification_only
        else (
            "Return only the materiality resolution, admitted fact and relation IDs, "
            "findings, and typed architecture. If a source candidate is materially wrong, "
            "reject it with typed findings; do not reopen materiality."
        )
    )
    return (
        "Act as the independent final Greenfield graph adjudicator. Use no tools, files, "
        "retries, validator feedback, regex, fuzzy matching, token heuristics, or prose repair. "
        + output_scope
        + f"\nOPERATOR_PROMPT\n{prompt_text}"
        + f"\nMATERIALITY_HYPOTHESIS\n{_json(materiality_hypothesis)}"
        + f"\nTYPED_SOURCE_CANDIDATE\n{_json(source_hypothesis)}"
        + f"\nPROVISIONAL_DISCARDED_EVIDENCE\n{_json(discarded_hypothesis)}"
        + f"\nCONTRACT\n{_json(contract)}"
    )


def source_path_prompt(
    *, prompt_text: str, evidence_catalog: Mapping[str, Mapping[str, Any]],
    model_budget_seconds: int,
) -> str:
    """Return the source-path author contract for the parallel first wave."""

    return _source_partition_prompt(
        prompt_text=prompt_text,
        evidence_catalog=evidence_catalog,
        model_budget_seconds=model_budget_seconds,
        role="source-path",
        output_key="source_path",
        partition_contract=_source_path_contract(
            evidence_catalog, include_evidence=False
        ),
    )


def source_boundary_prompt(
    *, prompt_text: str, evidence_catalog: Mapping[str, Mapping[str, Any]],
    model_budget_seconds: int,
) -> str:
    """Return the operating-boundary author contract for the parallel first wave."""

    return _source_partition_prompt(
        prompt_text=prompt_text,
        evidence_catalog=evidence_catalog,
        model_budget_seconds=model_budget_seconds,
        role="source-boundary",
        output_key="source_boundary",
        partition_contract=_source_boundary_contract(
            evidence_catalog, include_evidence=False
        ),
    )


def _source_partition_prompt(
    *,
    prompt_text: str,
    evidence_catalog: Mapping[str, Mapping[str, Any]],
    model_budget_seconds: int,
    role: str,
    output_key: str,
    partition_contract: Mapping[str, Any],
) -> str:
    authoring = semantic_intent_authoring_protocol()
    contract = {
        "deadline": {"stage_seconds": model_budget_seconds, "retries": 0},
        "authority": (
            "Author only the assigned source-entailable partition. Do not decide materiality, "
            "choose between contradictory alternatives, author the sibling partition, or author "
            "implementation architecture and narratives. Omit propositions that require operator "
            "clarification; the independent critic owns that decision."
        ),
        output_key: dict(partition_contract),
        "evidence_blocks": _provider_catalog(evidence_catalog),
        "output_invariant": f"one complete typed {role} partition",
        "forbidden_mechanisms": authoring["forbidden_mechanisms"],
    }
    return (
        f"Act as the independent Greenfield {role} author. Use no tools, files, retries, "
        "validator feedback, regex, fuzzy matching, token heuristics, architecture guesses, or "
        f"prose repair. Return only the typed {role} partition."
        f"\nOPERATOR_PROMPT\n{prompt_text}\nCONTRACT\n{_json(contract)}"
    )


def _source_path_contract(
    evidence_catalog: Mapping[str, Mapping[str, Any]],
    *, include_evidence: bool = True,
) -> dict[str, Any]:
    authoring = semantic_intent_authoring_protocol()
    path_ids = {
        name: SOURCE_FACT_ID_PREFIXES[kind]
        for name, kind in SOURCE_PATH_COLLECTIONS.items()
    }
    contract = {
        "version": SEMANTIC_SOURCE_PATH_GRAPH_VERSION,
        "authority": "Author only source-entailable product and first-path meaning.",
        "path": SOURCE_PATH_COLLECTIONS,
        "deterministic_ids": {
            "rule": (
                "Facts are prefix.<zero-based order within their collection>. Actor owners use "
                "actor fact IDs. Each state object owns either one transition with the exact "
                "zero-based workflow step_index and endpoints, or null when stable. Each visible "
                "output owns one producer with the exact workflow step_index. The deterministic "
                "compiler alone creates changes and produces edges."
            ),
            "source_collection_prefixes": path_ids,
        },
        "semantic_kind_disambiguation": authoring["semantic_kind_disambiguation"],
        "semantic_ontology": {
            "identity": (
                "the product or project being requested; the request to construct that product "
                "defines identity and is not itself an in-product workflow event"
            ),
            "actor": (
                "every explicitly declared human or human role, including roles with no owned "
                "workflow; never invent a responsibility and never treat an action or system as an actor"
            ),
            "workflow_step": "one ordered observable actor or product event after the requested product exists",
            "state_object": (
                "a durable domain entity; transition names its sole changing step and distinct "
                "endpoints, while null means the entity is stable"
            ),
            "visible_output": (
                "a human-visible result or decision artifact produced by one workflow step; "
                "a mutation, completed action, destination, lane membership, input or dependency "
                "data, optional ordering/view condition, and an existing source collection are "
                "not produced outputs. Emit zero visible outputs when the source names no "
                "observable result. condition carries an explicit "
                "source-cited qualifier or non-material missing presentation detail when one is "
                "stated, and is null otherwise"
            ),
        },
        "relation_semantics": {
            "changes": (
                "derived only from a state object's single non-null transition"
            ),
            "produces": (
                "derived only from the visible output's source-supported producer step; a "
                "consumption-only event and intermediate artifact are not separate producers"
            ),
        },
        "custody": [
            "cite each fact and step edge with exact source bytes",
            "put each path fact in exactly one semantically correct collection",
            "author no dependency, policy, discarded evidence, or implementation boundary",
        ],
        "quality": [
            "preserve every supported material fact",
            "preserve every explicitly enumerated role as a separate actor fact even when it owns no workflow",
            "group every contiguous workflow sequence under its one source-supported actor, product, or system owner",
            (
                "attach each state transition and visible-result producer to one exact workflow "
                "step_index on the state or output object"
            ),
            "put exact transition endpoints only on the state object; null means stable",
            "add no unsupported actor, action, state, or output",
            "do not relabel input, dependency, or optional view data as a produced output",
            "never turn an action or system into an actor",
            "keep product/system/output events human-unowned unless the source assigns a human",
            "preserve zero actors, zero states, or zero visible outputs when evidence has none; never invent them",
            (
                "preserve an explicit qualifier or non-material missing presentation detail on "
                "the affected visible output's condition; it is source truth, not an assumption"
            ),
            (
                "evidence explicitly designated for exclusion from governed product truth belongs "
                "only to discarded evidence and is never an in-product workflow step"
            ),
            "do not duplicate one proposition across semantic kinds",
        ],
        "forbidden_mechanisms": authoring["forbidden_mechanisms"],
    }
    if include_evidence:
        contract["evidence_blocks"] = _provider_catalog(evidence_catalog)
    return contract


def _source_boundary_contract(
    evidence_catalog: Mapping[str, Mapping[str, Any]],
    *, include_evidence: bool = True,
) -> dict[str, Any]:
    authoring = semantic_intent_authoring_protocol()
    contract = {
        "version": SEMANTIC_SOURCE_BOUNDARY_GRAPH_VERSION,
        "authority": "Author only source-entailable operating-boundary meaning.",
        "boundary": SOURCE_BOUNDARY_COLLECTIONS,
        "semantic_ontology": {
            "external_system": (
                "a concrete dependency the product actually uses; access_mode records only "
                "an explicitly evidenced interaction and is null when that interaction is "
                "unspecified; consumer is identity for a product-wide dependency or the exact "
                "workflow_step index when one step uses it, and is null when evidence names the "
                "dependency without assigning its consumer; it never records a restriction"
            ),
            "external_system_access_modes": list(SOURCE_ACCESS_MODES),
            "operating_invariant": "a restriction on how an included capability or dependency may operate",
            "excluded_capability": "a capability expressly outside the product delivery boundary",
            "assumption": (
                "a visible non-material interpretation required to proceed; materiality_field "
                "names the one canonical field it interprets"
            ),
            "ambiguity": (
                "the first unresolved material gap or disagreement in source meaning; "
                "materiality_field names the affected canonical field and question asks only "
                "for that missing meaning or which cited alternative governs"
            ),
            "discarded_evidence": "superseded or obsolete evidence that is never product truth",
        },
        "custody": [
            "cite every row with the exact evidence-block handle that entails it",
            "preserve every boundary proposition exactly once",
            "put each policy in exactly one exclusive policy_kind",
            (
                "when source statements prescribe mutually exclusive material meaning, author "
                "one ambiguity with both exact citations and do not preserve the alternatives "
                "as sequential product workflow; record only the first blocking ambiguity"
            ),
            (
                "when a complete action or state mutation has no source-supported observable "
                "result, emit zero visible outputs and one visible_result ambiguity citing the "
                "action; never relabel the action, route, destination, or state as its result"
            ),
            (
                "when a human-facing choice, selection, review, approval, or observation has no "
                "named participant, preserve product-owned source facts and author one role "
                "ambiguity; request phrasing alone is not explicit product automation"
            ),
            (
                "when the source explicitly labels a later statement as the final edit or final "
                "instruction for the same proposition, preserve that statement and route the "
                "superseded draft statement to discarded evidence instead of ambiguity"
            ),
            "put evidence explicitly designated obsolete or discarded only in discarded_evidence and never in policies",
            "do not turn a generic class named only inside a restriction into a dependency",
            "relations remain empty because deterministic compilation owns boundary edges",
        ],
        "quality": [
            "preserve concrete dependencies and every material policy",
            "preserve dependency exclusivity, access, locality, safety, and evidence conditions",
            "keep discarded evidence absent from every product collection",
            "keep material ambiguities out of assumptions and product/path collections",
            "add no unsupported dependency, policy, assumption, ambiguity, or boundary",
            "never duplicate product or first-path meaning as an operating-boundary fact",
            (
                "when one operation is allowed but another is forbidden on the same subject, "
                "encode one operating invariant over the allowed scope; use excluded_capability "
                "only when the capability itself is outside delivery"
            ),
        ],
        "forbidden_mechanisms": authoring["forbidden_mechanisms"],
    }
    if include_evidence:
        contract["evidence_blocks"] = _provider_catalog(evidence_catalog)
    return contract


def _system_topology_contract(topology_mode: str) -> str:
    shared = (
        "Do not choose release_scope and do not author internal-system IDs in depends_on. "
        "The deterministic compiler places every emitted system in the active first-path "
        "release and derives internal topology; omit deferred systems. "
    )
    if topology_mode == "single_system":
        return shared + (
            "Author exactly one cohesive result system, assign every implementation target to "
            "system index 0, and return no supporting systems. External dependencies remain "
            "external typed edges; never invent an internal adapter for them."
        )
    if topology_mode == "adaptive":
        return shared + (
            "internal_systems contains only result-implementing systems addressed by "
            "implementation_assignments. supporting_systems contains only resultless boundary "
            "systems: boundary_links must name at least one allowed typed dependency, constraint, "
            "or exclusion and supporting_consumers.system_indices must contain unique exact "
            "zero-based internal_systems indices."
        )
    raise ValueError("Semantic completion topology mode is unsupported")


def _json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _provider_catalog(
    catalog: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, str]]:
    return {
        ref_id: {"source_id": str(row["source_id"]), "quote": str(row["quote"])}
        for ref_id, row in catalog.items()
    }


__all__ = [
    "final_graph_adjudication_prompt", "partitioned_graph_hypothesis_prompt",
    "source_boundary_prompt", "source_path_prompt",
]
