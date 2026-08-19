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
from odylith.runtime.domain_intelligence.greenfield_semantic_source_authoring import (
    SEMANTIC_SOURCE_BOUNDARY_GRAPH_VERSION,
    SEMANTIC_SOURCE_GRAPH_VERSION,
    SEMANTIC_SOURCE_PATH_GRAPH_VERSION,
    SOURCE_ACCESS_MODES,
    SOURCE_BOUNDARY_COLLECTIONS,
    SOURCE_FACT_ID_PREFIXES,
    SOURCE_PATH_COLLECTIONS,
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
                "a human-visible result or decision artifact; condition carries an explicit "
                "source-cited qualifier or non-material missing presentation detail when one "
                "is stated, and is null otherwise"
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
            "never turn an action or system into an actor",
            "keep product/system/output events human-unowned unless the source assigns a human",
            "preserve zero actors or zero states when evidence has none; never invent them",
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
            "discarded_evidence": "superseded or obsolete evidence that is never product truth",
        },
        "custody": [
            "cite every row with the exact evidence-block handle that entails it",
            "preserve every boundary proposition exactly once",
            "put each policy in exactly one exclusive policy_kind",
            "put evidence explicitly designated obsolete or discarded only in discarded_evidence and never in policies",
            "do not turn a generic class named only inside a restriction into a dependency",
            "relations remain empty because deterministic compilation owns boundary edges",
        ],
        "quality": [
            "preserve concrete dependencies and every material policy",
            "preserve dependency exclusivity, access, locality, safety, and evidence conditions",
            "keep discarded evidence absent from every product collection",
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


def completion_graph_prompt(
    *, source: Mapping[str, Any],
    citation_registry: Mapping[str, Mapping[str, Any]],
    edge_object_ids: Mapping[str, tuple[str, ...]], model_budget_seconds: int,
    topology_mode: str,
) -> str:
    """Return the bounded completion contract over admitted source meaning."""

    authoring = semantic_intent_authoring_protocol()
    graph_contract = semantic_intent_authoring_contract()
    contract = {
        "deadline": {"stage_seconds": model_budget_seconds, "retries": 0},
        "authority": (
            "Complete implementation architecture and human-visible governance narratives "
            "over the immutable admitted source graph. Materiality is already settled by an "
            "independent prompt-only authority. Do not reopen, reinterpret, replace, omit, or "
            "add source meaning."
        ),
        "relation_endpoints": graph_contract["relation_contracts"],
        "source_citations": {
            "rule": (
                "Cite only atomic citation IDs from the immutable registry. Each ID resolves to "
                "one already-validated exact source span; never repeat or invent source_ref "
                "objects. Cite at most eight direct spans per object; typed edges own "
                "their own dependency, constraint, exclusion, and implementation evidence."
            ),
            "registry": {
                citation_id: list(row.get("fact_ids", ()))
                for citation_id, row in citation_registry.items()
            },
        },
        "allowed_edge_object_ids": {
            kind: list(values) for kind, values in edge_object_ids.items()
        },
        "implementation_assignments": {
            target: (
                "required exact binding to one or more zero-based internal_systems indices; "
                "the deterministic compiler projects these bindings into implements edges"
            )
            for target in edge_object_ids["implements"]
        },
        "system_topology": _system_topology_contract(topology_mode),
        "mandatory_challenges": authoring["mandatory_challenges"],
        "output_invariant": "one complete implementation-and-narrative object",
        "quality": [
            "author the smallest sufficient set of non-overlapping internal systems",
            "assign every required implementation target in implementation_assignments",
            "give every supporting system both a typed boundary and a consuming result system",
            "bind every implementation edge to an allowed typed source object",
            "write concrete concise narratives grounded only in the typed source graph",
            "every completion citation uses source_citation_ids only",
            "preserve actor, workflow, state, output, dependency, constraint, and non-goal distinctions",
            "produce two measurable success metrics and at least one evidence requirement",
            "report every mandatory self-challenge truthfully",
        ],
        "forbidden": [
            "source-fact changes", "raw prompt recovery", "generic filler",
            "regex or token heuristics", "validator feedback", "retries", "prose repair",
        ],
    }
    return (
        "Act as the bounded Greenfield graph-completion author. Use no tools or files. The "
        "typed source graph and its provider-locked citations are your entire authority. "
        "Return only the complete typed completion object."
        f"\nSOURCE_GRAPH\n{_json(source)}\nCONTRACT\n{_json(contract)}"
    )


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
    "completion_graph_prompt", "source_boundary_prompt", "source_path_prompt",
]
