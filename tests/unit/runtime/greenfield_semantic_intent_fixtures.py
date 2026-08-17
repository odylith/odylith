"""Reusable source-cited Semantic Intent fixtures for v8 authority tests."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    SEMANTIC_INTENT_IR_VERSION,
    SEMANTIC_INTENT_PACKET_VERSION,
    semantic_evidence_sha256,
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
    return {
        "version": SEMANTIC_MATERIALITY_ASSESSMENT_VERSION,
        "evidence_sha256": evidence_sha256,
        "authoring_contract_sha256": contract_sha256,
        "assessment_basis": SEMANTIC_MATERIALITY_ASSESSMENT_BASIS,
        "decision": "authorize_graph",
        "clarification": {"field": "", "question": ""},
        "fields": [
            {
                "field": field,
                "status": "explicit" if field != "component_boundary" else "source_entailable",
                "source_refs": [semantic_ref(quote) for quote in quotes],
                "alternatives": [],
            }
            for field, quotes in evidence_by_field.items()
        ],
    }


def semantic_intent_packet() -> dict[str, Any]:
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
            attributes={"object": "card", "from_state": "ready", "to_state": "claimed"},
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
        semantic_relation("owned_by", "step.0", "actor.0", 0, PATH_EVIDENCE),
        semantic_relation("owned_by", "step.1", "actor.0", 1, PATH_EVIDENCE),
        semantic_relation("changes", "step.0", "state.0", 0, STATE_EVIDENCE),
        semantic_relation("produces", "step.1", "output.0", 0, PATH_EVIDENCE),
        semantic_relation("depends_on", "identity.0", "dependency.0", 0, DEPENDENCY_EVIDENCE),
        semantic_relation("depends_on", "system.0", "dependency.0", 1, DEPENDENCY_EVIDENCE),
        semantic_relation("depends_on", "system.1", "system.0", 2, PATH_EVIDENCE),
        semantic_relation("excludes", "identity.0", "non-goal.0", 0, NON_GOAL_EVIDENCE),
        semantic_relation("implements", "system.0", "step.0", 0, PATH_EVIDENCE),
        semantic_relation("implements", "system.1", "step.1", 1, PATH_EVIDENCE),
        semantic_relation("implements", "system.1", "output.0", 2, PATH_EVIDENCE),
        semantic_relation("implements", "system.0", "state.0", 3, STATE_EVIDENCE),
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
    return {
        "version": SEMANTIC_INTENT_PACKET_VERSION,
        "evidence_sha256": evidence_sha256,
        "authoring_contract_sha256": contract_sha256,
        "materiality_assessment": assessment,
        "materiality_assessment_sha256": semantic_materiality_assessment_sha256(
            assessment
        ),
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


def semantic_clarification_packet() -> dict[str, Any]:
    """Return one assessed packet that asks exactly one material question."""

    packet = deepcopy(semantic_intent_packet())
    assessment = packet["materiality_assessment"]
    question = "Should the visible result be a claim receipt or a claim audit view?"
    assessment["decision"] = "clarification_required"
    assessment["clarification"] = {
        "field": "visible_result",
        "question": question,
    }
    visible_result = next(
        row for row in assessment["fields"] if row["field"] == "visible_result"
    )
    visible_result["status"] = "materially_unresolved"
    visible_result["alternatives"] = ["claim receipt", "claim audit view"]
    packet["materiality_assessment_sha256"] = semantic_materiality_assessment_sha256(
        assessment
    )

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
) -> dict[str, Any]:
    return {
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


def semantic_relation(
    kind: str,
    subject_id: str,
    object_id: str,
    order: int,
    quote: str,
) -> dict[str, Any]:
    return {
        "relation_id": f"relation.{kind}.{order}",
        "kind": kind,
        "subject_id": subject_id,
        "object_id": object_id,
        "order": order,
        "source_refs": [semantic_ref(quote)],
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
        semantic_relation("implements", "system.0", "step.0", 0, prompt),
        semantic_relation("implements", "system.0", "output.0", 1, prompt),
        semantic_relation("implements", "system.0", "output.1", 2, prompt),
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
