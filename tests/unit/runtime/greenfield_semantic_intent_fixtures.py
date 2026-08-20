"""Reusable source-cited Semantic Intent fixtures for v9 authority tests."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    SEMANTIC_INTENT_IR_VERSION,
    SEMANTIC_INTENT_PACKET_VERSION,
    semantic_evidence_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_extension_contract import (
    SEMANTIC_GRAPH_EXTENSION_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    semantic_intent_authoring_contract_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_materiality_contract import (
    SEMANTIC_MATERIALITY_ASSESSMENT_BASIS,
    SEMANTIC_MATERIALITY_ASSESSMENT_VERSION,
    SEMANTIC_REASONING_CAPABILITY_PROFILE,
    semantic_materiality_assessment_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    require_semantic_intent_packet,
    semantic_intent_authority,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_atomic_source_custody import (
    ATOMIC_SOURCE_ADJUDICATION_VERSION,
    ATOMIC_SOURCE_CANDIDATES_VERSION,
    select_atomic_source_claims,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_claims import (
    SEMANTIC_SOURCE_CLAIMS_VERSION,
)


SEMANTIC_PROMPT = (
    "Build a claim desk. "
    "A shift coordinator claims one ready card and receives a claim receipt. "
    "The card moves from ready to claimed. "
    "Read the local duty roster. "
    "Never reassign a card automatically."
)
IDENTITY_EVIDENCE = "Build a claim desk."
PATH_EVIDENCE = "A shift coordinator claims one ready card and receives a claim receipt."
STATE_EVIDENCE = "The card moves from ready to claimed."
DEPENDENCY_EVIDENCE = "Read the local duty roster."
NON_GOAL_EVIDENCE = "Never reassign a card automatically."
CRITIC_RUN_ID = "fixture-materiality-critic-run"
AUTHOR_RUN_ID = "fixture-semantic-author-run"


def semantic_graph_extension_from_intent(
    semantic_intent: dict[str, Any],
) -> dict[str, Any]:
    """Project bounded fixture rows into the node-owned authoring contract."""

    bounded_facts = [
        deepcopy(row)
        for row in semantic_intent["facts"]
        if row["custody"] == "bounded_interpretation"
    ]
    nodes = [
        {
            "fact": row,
            "depends_on": [],
            "implements": [],
            "constrained_by": [],
            "excludes": [],
            "incoming_changes": [],
        }
        for row in bounded_facts
    ]
    nodes_by_id = {node["fact"]["fact_id"]: node for node in nodes}
    for relation in semantic_intent["relations"]:
        if relation["custody"] != "bounded_interpretation":
            continue
        kind = relation["kind"]
        if kind == "changes" and relation["object_id"] in nodes_by_id:
            nodes_by_id[relation["object_id"]]["incoming_changes"].append(
                {
                    "relation_id": relation["relation_id"],
                    "subject_id": relation["subject_id"],
                    "order": relation["order"],
                    "source_refs": deepcopy(relation["source_refs"]),
                }
            )
            continue
        owner = nodes_by_id.get(relation["subject_id"])
        if owner is None or kind not in {
            "depends_on",
            "implements",
            "constrained_by",
            "excludes",
        }:
            raise AssertionError("fixture relation cannot enter the bounded node contract")
        owner[kind].append(
            {
                "relation_id": relation["relation_id"],
                "object_id": relation["object_id"],
                "order": relation["order"],
                "source_refs": deepcopy(relation["source_refs"]),
            }
        )
    return {
        "version": SEMANTIC_GRAPH_EXTENSION_VERSION,
        "status": semantic_intent["status"],
        "clarification": deepcopy(semantic_intent["clarification"]),
        "nodes": nodes,
        "narratives": deepcopy(semantic_intent["narratives"]),
    }


def semantic_materiality_assessment() -> dict[str, Any]:
    """Return a complete prompt-only assessment for the shared fixture graph."""

    evidence_sha256 = semantic_evidence_sha256(
        {"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""}
    )
    contract_sha256 = semantic_intent_authoring_contract_sha256()
    evidence_by_field = {
        "identity": [IDENTITY_EVIDENCE],
        "role": [PATH_EVIDENCE],
        "first_path": [PATH_EVIDENCE],
        "state_object": [STATE_EVIDENCE],
        "visible_result": [PATH_EVIDENCE],
        "dependency": [DEPENDENCY_EVIDENCE],
        "constraint": [DEPENDENCY_EVIDENCE],
        "non_goal": [NON_GOAL_EVIDENCE],
        "component_boundary": [PATH_EVIDENCE, STATE_EVIDENCE],
    }
    source_facts, source_relations = _claim_desk_source_graph()
    return {
        "version": SEMANTIC_MATERIALITY_ASSESSMENT_VERSION,
        "evidence_sha256": evidence_sha256,
        "authoring_contract_sha256": contract_sha256,
        "assessment_basis": SEMANTIC_MATERIALITY_ASSESSMENT_BASIS,
        "decision": "authorize_graph",
        "clarification": {
            "field": "",
            "question": "",
            "source_refs": [],
            "alternatives": [],
        },
        "fields": [
            {
                "field": field,
                "status": "explicit" if field != "component_boundary" else "source_entailable",
                "source_refs": [semantic_ref(quote) for quote in quotes],
                "alternatives": [],
            }
            for field, quotes in evidence_by_field.items()
        ],
        "source_candidates": _source_candidates(source_facts, source_relations),
    }


def semantic_intent_packet() -> dict[str, Any]:
    source_facts, source_relations = _claim_desk_source_graph()
    facts = [
        *source_facts,
        semantic_fact(
            "system.0", "internal_system", "Card Claim Service",
            "Card Claim Service — owns ready-card selection and claimed-card state.",
            0, PATH_EVIDENCE, custody="bounded_interpretation",
            attributes={
                "responsibility": "Own ready-card selection and the claimed-card transition.",
                "component_kind": "service",
                "boundary": "Own card-claim decisions and the ready-to-claimed state change.",
                "outside_boundary": "Receipt delivery and automatic card reassignment.",
                "proof": "Prove that one ready card becomes claimed with its source evidence intact.",
                "risk": "A wrong or stale card could be claimed without reviewable evidence.",
                "release_scope": "first_path_required",
            },
        ),
        semantic_fact(
            "system.1", "internal_system", "Claim Receipt Delivery",
            "Claim Receipt Delivery — owns the visible claim receipt.",
            1, PATH_EVIDENCE, custody="bounded_interpretation",
            attributes={
                "responsibility": "Deliver the claim receipt after a successful card claim.",
                "component_kind": "service",
                "boundary": "Own visible receipt delivery after a successful card claim.",
                "outside_boundary": "Card selection and the decision to claim a card.",
                "proof": "Prove that the visible receipt identifies the successfully claimed card.",
                "risk": "A missing or mismatched receipt could conceal the accepted claim result.",
                "release_scope": "first_path_required",
            },
        ),
    ]
    relations = [
        *source_relations,
        semantic_relation(
            "depends_on", "system.0", "dependency.0", 1, DEPENDENCY_EVIDENCE,
            custody="bounded_interpretation",
        ),
        semantic_relation(
            "depends_on", "system.1", "system.0", 2, PATH_EVIDENCE,
            custody="bounded_interpretation",
        ),
        semantic_relation(
            "implements", "system.0", "step.0", 0, PATH_EVIDENCE,
            custody="bounded_interpretation",
        ),
        semantic_relation(
            "implements", "system.1", "step.1", 1, PATH_EVIDENCE,
            custody="bounded_interpretation",
        ),
        semantic_relation(
            "implements", "system.1", "output.0", 2, PATH_EVIDENCE,
            custody="bounded_interpretation",
        ),
        semantic_relation(
            "implements", "system.0", "state.0", 3, STATE_EVIDENCE,
            custody="bounded_interpretation",
        ),
    ]
    narratives = [
        semantic_narrative("product_story", "Claim Desk helps a shift coordinator claim one ready card and receive a claim receipt.", ["identity.0", "actor.0", "state.0", "output.0"], PATH_EVIDENCE),
        semantic_narrative("problem", "Shift coordinators need a reviewable card-claim path.", ["actor.0", "state.0"], PATH_EVIDENCE),
        semantic_narrative("customer", "The first customer is a shift coordinator.", ["actor.0"], PATH_EVIDENCE),
        semantic_narrative("opportunity", "Make one card claim visible without automatic reassignment.", ["state.0", "non-goal.0"], NON_GOAL_EVIDENCE),
        semantic_narrative("product_view", "A claim desk for claiming one ready card and receiving a claim receipt.", ["identity.0", "step.0", "output.0"], PATH_EVIDENCE),
        semantic_narrative("proof_boundary", "A shift coordinator can claim one ready card and receive a claim receipt.", ["step.0", "step.1", "output.0"], PATH_EVIDENCE),
        semantic_narrative("success_metric", "A claimed card and its receipt are visible.", ["state.0", "output.0"], PATH_EVIDENCE),
        semantic_narrative("success_metric", "The local duty roster is read, and automatic reassignment stays excluded.", ["dependency.0", "non-goal.0"], [DEPENDENCY_EVIDENCE, NON_GOAL_EVIDENCE], order=1),
        semantic_narrative("evidence_requirement", "Retain the claimed-card transition and claim receipt.", ["state.0", "output.0"], PATH_EVIDENCE),
    ]
    evidence_sha256 = semantic_evidence_sha256(
        {"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""}
    )
    contract_sha256 = semantic_intent_authoring_contract_sha256()
    assessment = semantic_materiality_assessment()
    source_candidate_adjudication = _source_candidate_adjudication(
        assessment["source_candidates"], source_facts, source_relations
    )
    return {
        "version": SEMANTIC_INTENT_PACKET_VERSION,
        "evidence_sha256": evidence_sha256,
        "authoring_contract_sha256": contract_sha256,
        "materiality_assessment": assessment,
        "materiality_assessment_sha256": semantic_materiality_assessment_sha256(
            assessment
        ),
        "source_candidate_adjudication": source_candidate_adjudication,
        "critic_run": {
            "capability_profile": SEMANTIC_REASONING_CAPABILITY_PROFILE,
            "critic_run_id": CRITIC_RUN_ID,
            "host_profile": "codex",
            "independent_context": True,
        },
        "author_run": {
            "capability_profile": SEMANTIC_REASONING_CAPABILITY_PROFILE,
            "author_run_id": AUTHOR_RUN_ID,
        },
        "semantic_intent": {
            "version": SEMANTIC_INTENT_IR_VERSION,
            "status": "complete",
            "clarification": {"question": "", "fields": [], "source_refs": []},
            "facts": facts,
            "relations": relations,
            "narratives": narratives,
        },
    }


def _claim_desk_source_graph() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    facts = [
        semantic_fact(
            "identity.0", "identity", "Claim Desk", "Claim Desk", 0, IDENTITY_EVIDENCE,
            attributes={"source_title": "claim desk"},
        ),
        semantic_fact(
            "actor.0", "actor", "Shift coordinator", "Claims a ready card and receives a receipt.",
            0, PATH_EVIDENCE, attributes={"responsibility": "claim a ready card and receive a receipt"},
        ),
        semantic_fact(
            "step.0", "workflow_step", "Claim ready card",
            "Shift coordinator claims one ready card.", 0, PATH_EVIDENCE, owner_kind="actor",
            attributes={"action": "claim", "action_phrase": "claim one ready card", "object": "one ready card"},
        ),
        semantic_fact(
            "step.1", "workflow_step", "Receive receipt",
            "Shift coordinator receives a claim receipt.", 1, PATH_EVIDENCE, owner_kind="actor",
            attributes={"action": "receive", "action_phrase": "receive a claim receipt", "object": "claim receipt"},
        ),
        semantic_fact(
            "state.0", "state_object", "Card", "The card moves from ready to claimed.",
            0, STATE_EVIDENCE,
            attributes={"object": "card"},
            transition={"from_state": "ready", "to_state": "claimed"},
        ),
        semantic_fact(
            "output.0", "visible_output", "Claim receipt", "A claim receipt is visible.",
            0, PATH_EVIDENCE,
        ),
        semantic_fact(
            "dependency.0", "external_system", "Local duty roster",
            "Read the local duty roster.", 0, DEPENDENCY_EVIDENCE,
            attributes={"access_mode": "read-only"},
        ),
        semantic_fact(
            "constraint.0", "operational_constraint", "Read local duty roster",
            "Read the local duty roster.", 0, DEPENDENCY_EVIDENCE,
        ),
        semantic_fact(
            "non-goal.0", "non_goal", "No automatic reassignment",
            "Never reassign a card automatically.", 0, NON_GOAL_EVIDENCE,
        ),
    ]
    relations = [
        semantic_relation("owned_by", "step.0", "actor.0", 0, PATH_EVIDENCE),
        semantic_relation("owned_by", "step.1", "actor.0", 1, PATH_EVIDENCE),
        semantic_relation("changes", "step.0", "state.0", 0, STATE_EVIDENCE),
        semantic_relation("produces", "step.1", "output.0", 0, PATH_EVIDENCE),
        semantic_relation("depends_on", "identity.0", "dependency.0", 0, DEPENDENCY_EVIDENCE),
        semantic_relation("excludes", "identity.0", "non-goal.0", 0, NON_GOAL_EVIDENCE),
    ]
    return facts, relations


def semantic_clarification_packet() -> dict[str, Any]:
    """Return one assessed packet that asks exactly one material question."""

    packet = deepcopy(semantic_intent_packet())
    assessment = packet["materiality_assessment"]
    question = "Should the visible result be a claim receipt or a claim audit view?"
    assessment["decision"] = "clarification_required"
    assessment["clarification"] = {
        "field": "visible_result",
        "question": question,
        "source_refs": [semantic_ref(PATH_EVIDENCE)],
        "alternatives": [],
    }
    assessment["fields"] = [
        row for row in assessment["fields"] if row["field"] != "visible_result"
    ]
    intent = packet["semantic_intent"]
    intent["status"] = "clarification_required"
    intent["clarification"] = {
        "question": question,
        "fields": ["visible_result"],
        "source_refs": [semantic_ref(PATH_EVIDENCE)],
    }
    intent["facts"] = [
        row
        for row in intent["facts"]
        if row["fact_id"] in {"identity.0", "actor.0", "step.0"}
    ]
    intent["relations"] = [
        row
        for row in intent["relations"]
        if row["kind"] == "owned_by" and row["subject_id"] == "step.0"
    ]
    intent["narratives"] = []
    assessment["source_candidates"] = _source_candidates(
        intent["facts"],
        intent["relations"],
    )
    packet["source_candidate_adjudication"] = _source_candidate_adjudication(
        assessment["source_candidates"], intent["facts"], intent["relations"]
    )
    packet["materiality_assessment_sha256"] = semantic_materiality_assessment_sha256(
        assessment
    )
    return packet


def semantic_intent_with_authority() -> dict[str, Any]:
    verified = require_semantic_intent_packet(
        semantic_intent_packet(),
        prompt=SEMANTIC_PROMPT,
    )
    return {
        **verified.product_facts,
        "product_intent_authority": semantic_intent_authority(
            verified,
            prompt=SEMANTIC_PROMPT,
        ),
    }


def rebind_fixture_source_candidates(packet: dict[str, Any]) -> dict[str, Any]:
    """Rebind a deliberately authored graph to critic-owned source candidates."""

    assessment = packet["materiality_assessment"]
    graph = packet["semantic_intent"]
    assessment["source_candidates"] = _source_candidates(
        graph["facts"],
        graph["relations"],
    )
    packet["source_candidate_adjudication"] = _source_candidate_adjudication(
        assessment["source_candidates"], graph["facts"], graph["relations"]
    )
    packet["materiality_assessment_sha256"] = semantic_materiality_assessment_sha256(
        assessment
    )
    return packet


def validated_fixture_source_claims(
    packet: dict[str, Any],
    *,
    prompt: str = SEMANTIC_PROMPT,
    edit_evidence: str = "",
) -> dict[str, Any]:
    """Return fixture claims through the production atomic custody boundary."""

    assessment = packet["materiality_assessment"]
    settled_fields = {row["field"]: row for row in assessment["fields"]}
    _, source_claims = select_atomic_source_claims(
        assessment["source_candidates"],
        packet["source_candidate_adjudication"],
        evidence_sources={
            "operator_prompt": prompt,
            "operator_edit": edit_evidence,
        },
        settled_fields=settled_fields,
    )
    return source_claims


def semantic_ref(quote: str) -> dict[str, Any]:
    return {"source_id": "operator_prompt", "quote": quote, "occurrence": 1}


def semantic_fact(
    fact_id: str,
    kind: str,
    label: str,
    statement: str,
    order: int,
    quote: str | list[str],
    *,
    owner_kind: str = "none",
    custody: str = "source_fact",
    attributes: dict[str, str] | None = None,
    transition: dict[str, str] | None = None,
) -> dict[str, Any]:
    result = {
        "fact_id": fact_id,
        "kind": kind,
        "label": label,
        "statement": statement,
        "order": order,
        "owner_kind": owner_kind,
        "custody": custody,
        "attributes": [
            {"name": name, "value": value}
            for name, value in (attributes or {}).items()
        ],
        "source_refs": [
            semantic_ref(value)
            for value in ([quote] if isinstance(quote, str) else quote)
        ],
    }
    if kind == "state_object":
        result["transition"] = transition
    return result


def semantic_relation(
    kind: str,
    subject_id: str,
    object_id: str,
    order: int,
    quote: str,
    *,
    custody: str = "source_fact",
) -> dict[str, Any]:
    return {
        "relation_id": f"relation.{kind}.{order}",
        "kind": kind,
        "subject_id": subject_id,
        "object_id": object_id,
        "order": order,
        "custody": custody,
        "source_refs": [semantic_ref(quote)],
    }


def _source_candidates(
    facts: list[dict[str, Any]],
    relations: list[dict[str, Any]],
) -> dict[str, Any]:
    refs: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int]] = set()
    for row in [*facts, *relations]:
        if row["custody"] != "source_fact":
            continue
        for source_ref in row["source_refs"]:
            key = (
                str(source_ref["source_id"]),
                str(source_ref["quote"]),
                int(source_ref["occurrence"]),
            )
            if key not in seen:
                seen.add(key)
                refs.append(deepcopy(source_ref))
    return {
        "version": ATOMIC_SOURCE_CANDIDATES_VERSION,
        "candidates": [
            {"candidate_id": f"candidate.{index}", "source_ref": source_ref}
            for index, source_ref in enumerate(refs)
        ],
    }


def _source_claims(
    facts: list[dict[str, Any]],
    relations: list[dict[str, Any]],
) -> dict[str, Any]:
    fact_fields = {
        "identity": "identity",
        "actor": "role",
        "workflow_step": "first_path",
        "state_object": "state_object",
        "visible_output": "visible_result",
        "external_system": "dependency",
        "operational_constraint": "constraint",
        "non_goal": "non_goal",
        "internal_system": "component_boundary",
        "component_responsibility": "component_boundary",
    }
    relation_fields = {
        "owned_by": ["role", "first_path"],
        "changes": ["first_path", "state_object"],
        "produces": ["first_path", "visible_result"],
        "depends_on": ["dependency"],
        "constrained_by": ["constraint"],
        "excludes": ["non_goal"],
        "implements": ["component_boundary", "first_path"],
    }
    return {
        "version": SEMANTIC_SOURCE_CLAIMS_VERSION,
        "facts": [
            {"field": fact_fields[row["kind"]], "fact": deepcopy(row)}
            for row in facts
            if row["custody"] == "source_fact"
        ],
        "relations": [
            {"fields": relation_fields[row["kind"]], "relation": deepcopy(row)}
            for row in relations
            if row["custody"] == "source_fact"
        ],
    }


def _source_candidate_adjudication(
    source_candidates: dict[str, Any],
    facts: list[dict[str, Any]],
    relations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Bind every fixture source row to its exact atomic evidence span."""

    source_facts = [row for row in facts if row["custody"] == "source_fact"]
    source_relations = [row for row in relations if row["custody"] == "source_fact"]
    decisions = []
    for candidate in source_candidates["candidates"]:
        source_ref = candidate["source_ref"]
        fact_ids = [
            row["fact_id"] for row in source_facts if source_ref in row["source_refs"]
        ]
        relation_ids = [
            row["relation_id"]
            for row in source_relations
            if source_ref in row["source_refs"]
        ]
        decisions.append({
            "candidate_id": candidate["candidate_id"],
            "decision": "retain" if fact_ids or relation_ids else "reject_noise",
            "fact_ids": fact_ids,
            "relation_ids": relation_ids,
        })
    return {
        "version": ATOMIC_SOURCE_ADJUDICATION_VERSION,
        "candidate_decisions": decisions,
        "source_claims": _source_claims(facts, relations),
    }


def semantic_narrative(
    field: str,
    text: str,
    fact_ids: list[str],
    quote: str | list[str],
    *,
    order: int = 0,
) -> dict[str, Any]:
    return {
        "field": field,
        "order": order,
        "text": text,
        "fact_ids": fact_ids,
        "source_refs": [
            semantic_ref(value)
            for value in ([quote] if isinstance(quote, str) else quote)
        ],
    }


def stateless_semantic_intent_packet() -> tuple[dict[str, Any], str]:
    """Return source-entailable actorless and stateless graph evidence."""

    prompt = (
        "Build a signal view. The product presents a signal chart and signal summary "
        "without durable state."
    )
    facts = [
        semantic_fact(
            "identity.0", "identity", "Signal View",
            "Signal View presents a chart and summary without durable state.", 0, prompt,
            attributes={"source_title": "signal view"},
        ),
        semantic_fact(
            "step.0", "workflow_step", "Present signal",
            "The product presents a signal chart and signal summary.", 0, prompt,
            owner_kind="product",
            attributes={
                "action": "present",
                "action_phrase": "present a signal chart and signal summary",
            },
        ),
        semantic_fact(
            "output.0", "visible_output", "Signal chart",
            "A signal chart is visible.", 0, prompt,
        ),
        semantic_fact(
            "output.1", "visible_output", "Signal summary",
            "A signal summary is visible.", 1, prompt,
        ),
        semantic_fact(
            "system.0", "internal_system", "Signal Service",
            "Signal Service owns stateless chart and summary presentation.", 0, prompt,
            custody="bounded_interpretation",
            attributes={
                "responsibility": "Present the two accepted signal outputs without durable state.",
                "component_kind": "service",
                "boundary": "Own signal chart and summary presentation.",
                "outside_boundary": "Durable state and behavior outside the accepted outputs.",
                "proof": "Prove that both accepted outputs are visible without durable state.",
                "risk": "One output could be omitted or persistence could be invented.",
                "release_scope": "first_path_required",
            },
        ),
        semantic_fact(
            "non-goal.0", "non_goal", "No durable state",
            "The signal view has no durable state.", 0, prompt,
        ),
    ]
    relations = [
        semantic_relation("produces", "step.0", "output.0", 0, prompt),
        semantic_relation("produces", "step.0", "output.1", 1, prompt),
        semantic_relation(
            "implements", "system.0", "step.0", 0, prompt,
            custody="bounded_interpretation",
        ),
        semantic_relation(
            "implements", "system.0", "output.0", 1, prompt,
            custody="bounded_interpretation",
        ),
        semantic_relation(
            "implements", "system.0", "output.1", 2, prompt,
            custody="bounded_interpretation",
        ),
        semantic_relation("excludes", "identity.0", "non-goal.0", 0, prompt),
    ]
    narratives = [
        semantic_narrative(
            "product_story",
            "Signal View presents a signal chart and summary without durable state.",
            ["identity.0", "step.0", "output.0", "output.1"], prompt,
        ),
        semantic_narrative(
            "problem", "Two signal outputs need one stateless presentation path.",
            ["identity.0", "output.0", "output.1"], prompt,
        ),
        semantic_narrative(
            "customer", "The product consumer receives both signal outputs.",
            ["output.0", "output.1"], prompt,
        ),
        semantic_narrative(
            "opportunity", "Present both accepted outputs without inventing persistence.",
            ["output.0", "output.1", "non-goal.0"], prompt,
        ),
        semantic_narrative(
            "product_view", "A stateless service presents a signal chart and signal summary.",
            ["system.0", "output.0", "output.1"], prompt,
        ),
        semantic_narrative(
            "proof_boundary", "Both signal outputs are visible and no durable state is created.",
            ["output.0", "output.1", "non-goal.0"], prompt,
        ),
        semantic_narrative(
            "success_metric", "The signal chart is visible.", ["output.0"], prompt,
        ),
        semantic_narrative(
            "success_metric", "The signal summary is visible without durable state.",
            ["output.1", "non-goal.0"], prompt, order=1,
        ),
        semantic_narrative(
            "evidence_requirement", "Verify both outputs and the absence of durable state.",
            ["output.0", "output.1", "non-goal.0"], prompt,
        ),
    ]
    graph = {
        "version": SEMANTIC_INTENT_IR_VERSION,
        "status": "complete",
        "clarification": {"question": "", "fields": [], "source_refs": []},
        "facts": facts,
        "relations": relations,
        "narratives": narratives,
    }
    packet = semantic_intent_packet()
    evidence_sha256 = semantic_evidence_sha256(
        {"operator_prompt": prompt, "operator_edit": ""}
    )
    assessment = deepcopy(packet["materiality_assessment"])
    assessment["evidence_sha256"] = evidence_sha256
    cited_fields = {
        "identity", "role", "first_path", "visible_result", "non_goal",
        "component_boundary",
    }
    for row in assessment["fields"]:
        field = row["field"]
        row["status"] = (
            "source_entailable"
            if field in {"role", "component_boundary"}
            else "explicit"
            if field in cited_fields
            else "nonmaterial_assumption"
        )
        row["source_refs"] = [semantic_ref(prompt)] if field in cited_fields else []
        row["alternatives"] = []
    assessment["source_candidates"] = _source_candidates(facts, relations)
    packet["source_candidate_adjudication"] = _source_candidate_adjudication(
        assessment["source_candidates"], facts, relations
    )
    packet.update(
        {
            "evidence_sha256": evidence_sha256,
            "materiality_assessment": assessment,
            "materiality_assessment_sha256": semantic_materiality_assessment_sha256(
                assessment
            ),
            "semantic_intent": graph,
        }
    )
    return packet, prompt
