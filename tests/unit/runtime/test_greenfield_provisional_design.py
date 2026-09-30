"""Structural and custody contracts for source-linked provisional delivery design."""

from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Any

import pytest

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_RELATION_SET_SHA256_KEY,
    AUTHORED_SEMANTICS_KEY,
    GreenfieldAuthoredSemanticsError,
    authored_relation_set_sha256,
    authored_semantics_mapping,
    first_path_relations_from_intent,
    require_relation_authority_parity,
)
from odylith.runtime.domain_intelligence.greenfield_model_atomic_projection import derive_model_atomic_claims
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    build_product_intent_envelope,
    product_facts_payload,
    product_intent_authority_from_envelope,
)
from odylith.runtime.domain_intelligence.greenfield_provisional_design import (
    PROVISIONAL_DESIGN_AUTHORITY_KIND,
    PROVISIONAL_DESIGN_SCHEMA,
    PROVISIONAL_DESIGN_VERSION,
    derive_risk_scope,
    provisional_design_from_intent,
    validate_provisional_design,
)


def _design(*, event_orders: tuple[int, ...] = (1, 2), count: int = 4) -> dict[str, Any]:
    return {
        "version": PROVISIONAL_DESIGN_VERSION,
        "authority_kind": PROVISIONAL_DESIGN_AUTHORITY_KIND,
        "first_run": {
            "event_orders": list(event_orders),
            "rationale": "Propose the fixture execution order without asserting source chronology.",
        },
        "components": [
            {
                "key": f"capability-{index}", "name": f"Capability {index}",
                "responsibility": f"Own proposed responsibility {index}.",
                "supported_event_orders": list(event_orders),
                "verification": f"Verify the boundary outcome for capability {index}.",
                "verification_event_orders": list(event_orders),
            }
            for index in range(count)
        ],
        "workstreams": [
            {
                "key": f"delivery-{index}", "title": f"Deliver capability {index}",
                "problem": f"Users cannot yet rely on capability {index} for this path.",
                "component_keys": [f"capability-{index}"],
                "depends_on": [f"delivery-{index - 1}"] if index else [],
                "deliverable": f"A working capability {index} boundary.",
                "verification": f"Exercise acceptance for delivery {index}.",
                "verification_event_orders": list(event_orders),
            }
            for index in range(count)
        ],
        "exchanges": [{
            "from_component": "capability-0", "to_component": "capability-1",
            "contract": "The selected record and its validation result.",
        }],
        "risk_posture": {
            "status": "no_material_risks_identified",
            "rationale": "This structural fixture carries no product-domain risk claim.",
            "items": [],
        },
    }


@pytest.mark.parametrize("count", [4, 5])
def test_valid_design_is_copied_without_rewriting_provisional_text(count: int) -> None:
    design = _design(count=count)
    design["components"][0]["responsibility"] = "Preserve café and APIv7 bytes."
    original = deepcopy(design)
    result = validate_provisional_design(design, event_orders=(1, 2))
    assert result == original
    result["components"][0]["supported_event_orders"].clear()
    result["workstreams"][0]["component_keys"].clear()
    result["first_run"]["event_orders"].clear()
    assert design == original


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("version",), "retired"),
        (("authority_kind",), "accepted_fact"),
        (("first_run", "event_orders"), []),
        (("first_run", "event_orders"), [1, 1]),
        (("first_run", "event_orders"), [1, 2, 3]),
        (("first_run", "event_orders"), [True, 2]),
        (("first_run", "rationale"), " "),
        (("components",), []),
        (("components",), _design(count=6)["components"]),
        (("components", 0, "key"), " "),
        (("components", 0, "key"), "x" * 81),
        (("components", 0, "key"), "../escape"),
        (("components", 0, "key"), "component/name"),
        (("components", 0, "key"), "component name"),
        (("components", 1, "key"), " CAPABILITY-0 "),
        (("components", 1, "name"), " capability   0 "),
        (("components", 0, "responsibility"), "\n"),
        (("components", 0, "verification"), "x" * 4001),
        (("components", 0, "supported_event_orders"), []),
        (("components", 0, "supported_event_orders"), [True]),
        (("components", 0, "supported_event_orders"), [1.0]),
        (("components", 0, "supported_event_orders"), [0]),
        (("components", 0, "supported_event_orders"), [33]),
        (("components", 0, "supported_event_orders"), [3]),
        (("components", 0, "supported_event_orders"), [1, 1]),
        (("workstreams",), []),
        (("workstreams",), _design(count=6)["workstreams"]),
        (("workstreams", 1, "key"), " DELIVERY-0 "),
        (("workstreams", 1, "title"), " deliver   capability 0 "),
        (("workstreams", 1, "problem"), " users   cannot yet rely on capability 0 for this path. "),
        (("workstreams", 0, "problem"), ""),
        (("workstreams", 0, "deliverable"), ""),
        (("workstreams", 0, "verification"), None),
        (("workstreams", 0, "component_keys"), []),
        (("workstreams", 0, "component_keys"), ["external"]),
        (("workstreams", 0, "component_keys"), ["capability-0", "capability-0"]),
        (("workstreams", 0, "depends_on"), ["delivery-0"]),
        (("workstreams", 0, "depends_on"), ["unknown"]),
        (("workstreams", 1, "depends_on"), ["delivery-0", "delivery-0"]),
        (("workstreams", 0, "depends_on"), ["delivery-3"]),
        (("exchanges", 0, "from_component"), "external"),
        (("exchanges", 0, "to_component"), "capability-0"),
        (("exchanges", 0, "contract"), "\t"),
    ],
)
def test_invalid_structure_is_rejected(path: tuple[Any, ...], replacement: Any) -> None:
    design = _design()
    target = design
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement
    message = "Greenfield (first run|event orders)" if path[0] == "first_run" else "Greenfield provisional"
    with pytest.raises(ValueError, match=message):
        validate_provisional_design(design, event_orders=(1, 2))


@pytest.mark.parametrize("owner", ["root", "first_run", "components", "workstreams", "exchanges"])
@pytest.mark.parametrize("damage", ["unknown", "missing"])
def test_every_object_shape_is_closed(owner: str, damage: str) -> None:
    design = _design()
    target = design if owner == "root" else design[owner] if owner == "first_run" else design[owner][0]
    if damage == "unknown":
        target["source_fact"] = "Invented authority"
    else:
        target.pop(next(iter(target)))
    with pytest.raises(ValueError):
        validate_provisional_design(design, event_orders=(1, 2))


@pytest.mark.parametrize("orders", [(), (True,), (0,), (1, 1), (33,), "12"])
def test_invalid_source_event_inventory_is_rejected(orders: Any) -> None:
    with pytest.raises(ValueError, match="source-event orders"):
        validate_provisional_design(_design(), event_orders=orders)


def test_every_source_action_and_proposed_component_has_delivery_support() -> None:
    design = _design(event_orders=(1,))
    design["first_run"]["event_orders"] = [1, 2]
    with pytest.raises(ValueError, match="every source action"):
        validate_provisional_design(design, event_orders=(1, 2))
    design = _design()
    design["workstreams"][3]["component_keys"] = ["capability-0"]
    with pytest.raises(ValueError, match="without delivery work"):
        validate_provisional_design(design, event_orders=(1, 2))


def test_verification_coverage_must_reach_every_supported_source_action() -> None:
    design = _design()
    for component in design["components"]:
        component["verification_event_orders"] = [1]
    with pytest.raises(ValueError, match="verify every source action"):
        validate_provisional_design(design, event_orders=(1, 2))

    design = _design()
    for workstream in design["workstreams"]:
        workstream["verification_event_orders"] = [1]
    with pytest.raises(ValueError, match="verify every source action"):
        validate_provisional_design(design, event_orders=(1, 2))


def test_material_risk_posture_requires_closed_design_and_evidence_references() -> None:
    design = _design()
    risk = {
        "key": "record-disclosure",
        "category": "privacy",
        "statement": "A record could be disclosed outside its intended boundary.",
        "trigger": "An unassigned operator requests the record.",
        "mitigation": "Require assignment-scoped authorization.",
        "verification": "Verify an unassigned operator cannot retrieve the record.",
        "scope_paths": [{
            "event_order": 1,
            "component_key": "capability-0",
            "workstream_key": "delivery-0",
        }],
    }
    design["risk_posture"] = {
        "status": "material_risks_identified",
        "rationale": "The proposed record path crosses an access boundary.",
        "items": [risk],
    }
    assert validate_provisional_design(design, event_orders=(1, 2)) == design

    design["risk_posture"]["items"][0]["scope_paths"][0]["component_key"] = "unknown"
    with pytest.raises(ValueError, match="not present in the design graph"):
        validate_provisional_design(design, event_orders=(1, 2))


def test_material_risk_scope_can_span_shared_valid_graph_paths() -> None:
    design = _design()
    design["workstreams"][0]["component_keys"] = ["capability-0", "capability-1"]
    design["workstreams"][1]["component_keys"] = ["capability-1", "capability-2"]
    design["risk_posture"] = {
        "status": "material_risks_identified",
        "rationale": "The proposed record path crosses several owned delivery boundaries.",
        "items": [{
            "key": "record-boundary-failure",
            "category": "operational",
            "statement": "A record could cross an incomplete delivery boundary.",
            "trigger": "A partially processed record advances to the next component.",
            "mitigation": "Require each owning workstream to reject incomplete records.",
            "verification": "Verify every named component rejects an incomplete record.",
            "scope_paths": [
                {"event_order": 1, "component_key": "capability-0", "workstream_key": "delivery-0"},
                {"event_order": 2, "component_key": "capability-1", "workstream_key": "delivery-0"},
                {"event_order": 2, "component_key": "capability-2", "workstream_key": "delivery-1"},
            ],
        }],
    }

    assert validate_provisional_design(design, event_orders=(1, 2)) == design


def test_retained_disclosed_v11_risk_shape_is_rejected_fail_closed() -> None:
    design = _design()
    design["risk_posture"] = {
        "status": "material_risks_identified",
        "rationale": "A retained disclosed candidate used three independent scope arrays.",
        "items": [{
            "key": "retained-shape",
            "category": "security",
            "statement": "A material risk affects more than one proposed boundary.",
            "trigger": "The proposed path reaches the affected boundary.",
            "mitigation": "Guard the affected boundary.",
            "verification": "Verify the guard across the affected path.",
            "component_keys": ["capability-0", "capability-1"],
            "workstream_keys": ["delivery-0"],
            "related_event_orders": [1, 2],
        }],
    }

    with pytest.raises(ValueError, match="invalid row fields"):
        validate_provisional_design(design, event_orders=(1, 2))


def test_derived_risk_scope_has_stable_design_order_without_mutating_authored_paths() -> None:
    design = _design()
    design["components"][0]["supported_event_orders"] = [1]
    design["components"][0]["verification_event_orders"] = [1]
    design["components"][1]["supported_event_orders"] = [2]
    design["components"][1]["verification_event_orders"] = [2]
    design["workstreams"][0]["verification_event_orders"] = [1]
    design["workstreams"][1]["verification_event_orders"] = [2]
    design["risk_posture"] = {
        "status": "material_risks_identified",
        "rationale": "The proposed record path crosses two event-bearing boundaries.",
        "items": [{
            "key": "record-boundary-failure",
            "category": "operational",
            "statement": "A record could cross an incomplete delivery boundary.",
            "trigger": "A partially processed record advances to the next component.",
            "mitigation": "Require each owning workstream to reject incomplete records.",
            "verification": "Verify every named component rejects an incomplete record.",
            "scope_paths": [
                {"event_order": 2, "component_key": "capability-1", "workstream_key": "delivery-1"},
                {"event_order": 1, "component_key": "capability-0", "workstream_key": "delivery-0"},
            ],
        }],
    }

    original = deepcopy(design)
    validated = validate_provisional_design(design, event_orders=(1, 2))
    scope = derive_risk_scope(validated, validated["risk_posture"]["items"][0])
    assert scope == {
        "authority_kind": "deterministic_graph_projection",
        "event_orders": [1, 2],
        "component_keys": ["capability-0", "capability-1"],
        "workstream_keys": ["delivery-0", "delivery-1"],
    }
    assert design == original


@pytest.mark.parametrize(
    "scope_paths",
    [
        [],
        [{"event_order": True, "component_key": "capability-0", "workstream_key": "delivery-0"}],
        [{"event_order": 0, "component_key": "capability-0", "workstream_key": "delivery-0"}],
        [{"event_order": 33, "component_key": "capability-0", "workstream_key": "delivery-0"}],
        [{"event_order": 1, "component_key": "unknown", "workstream_key": "delivery-0"}],
        [{"event_order": 1, "component_key": "capability-0", "workstream_key": "unknown"}],
        [{"event_order": 1, "component_key": "capability-0"}],
    ],
)
def test_material_risk_rejects_invalid_or_nonexistent_graph_paths(
    scope_paths: list[dict[str, Any]],
) -> None:
    design = _design()
    design["risk_posture"] = {
        "status": "material_risks_identified",
        "rationale": "The proposed record path crosses an event-bearing boundary.",
        "items": [{
            "key": "record-boundary-failure",
            "category": "operational",
            "statement": "A record could cross an incomplete delivery boundary.",
            "trigger": "A partially processed record advances to the next component.",
            "mitigation": "Require the owning workstream to reject incomplete records.",
            "verification": "Verify the named component rejects an incomplete record.",
            "scope_paths": scope_paths,
        }],
    }

    with pytest.raises(ValueError, match="Greenfield provisional"):
        validate_provisional_design(design, event_orders=(1, 2))


def test_material_risk_rejects_duplicate_graph_path() -> None:
    design = _design()
    path = {"event_order": 1, "component_key": "capability-0", "workstream_key": "delivery-0"}
    design["risk_posture"] = {
        "status": "material_risks_identified",
        "rationale": "The proposed record path crosses one owned delivery boundary.",
        "items": [{
            "key": "record-boundary-failure",
            "category": "operational",
            "statement": "A record could cross an incomplete delivery boundary.",
            "trigger": "A partially processed record advances to the next component.",
            "mitigation": "Require each owning workstream to reject incomplete records.",
            "verification": "Verify every named component rejects an incomplete record.",
            "scope_paths": [path, dict(path)],
        }],
    }

    with pytest.raises(ValueError, match="duplicate graph path"):
        validate_provisional_design(design, event_orders=(1, 2))


@pytest.mark.parametrize("broken_edge", ["component_support", "workstream_ownership", "workstream_verification"])
def test_material_risk_path_must_exist_in_every_graph_layer(broken_edge: str) -> None:
    design = _design()
    path = {"event_order": 2, "component_key": "capability-0", "workstream_key": "delivery-0"}
    if broken_edge == "component_support":
        design["components"][0]["supported_event_orders"] = [1]
        design["components"][0]["verification_event_orders"] = [1]
        design["workstreams"][0]["verification_event_orders"] = [1]
    elif broken_edge == "workstream_ownership":
        path["component_key"] = "capability-1"
    else:
        design["workstreams"][0]["verification_event_orders"] = [1]
    design["risk_posture"] = {
        "status": "material_risks_identified",
        "rationale": "The proposed record path crosses one owned delivery boundary.",
        "items": [{
            "key": "record-boundary-failure",
            "category": "operational",
            "statement": "A record could cross an incomplete delivery boundary.",
            "trigger": "A partially processed record advances.",
            "mitigation": "Reject incomplete records.",
            "verification": "Verify incomplete records are rejected.",
            "scope_paths": [path],
        }],
    }

    with pytest.raises(ValueError, match="not present in the design graph"):
        validate_provisional_design(design, event_orders=(1, 2))


def test_derived_risk_scope_excludes_unrelated_components_and_workstreams() -> None:
    design = _design()
    design["components"][0]["supported_event_orders"] = [1]
    design["components"][0]["verification_event_orders"] = [1]
    design["workstreams"][0]["verification_event_orders"] = [1]
    design["risk_posture"] = {
        "status": "material_risks_identified",
        "rationale": "Only the first delivery path carries this risk.",
        "items": [{
            "key": "record-boundary-failure",
            "category": "operational",
            "statement": "The first delivery path could fail.",
            "trigger": "The first event enters delivery.",
            "mitigation": "Guard the first path.",
            "verification": "Exercise the first path.",
            "scope_paths": [{
                "event_order": 1,
                "component_key": "capability-0",
                "workstream_key": "delivery-0",
            }],
        }],
    }

    validated = validate_provisional_design(design, event_orders=(1, 2))
    scope = derive_risk_scope(validated, validated["risk_posture"]["items"][0])
    assert scope["component_keys"] == ["capability-0"]
    assert scope["workstream_keys"] == ["delivery-0"]


def test_no_material_risk_posture_requires_an_explicit_empty_reviewed_result() -> None:
    design = _design()
    design["risk_posture"]["items"] = [{"key": "unexpected"}]
    with pytest.raises(ValueError):
        validate_provisional_design(design, event_orders=(1, 2))


def test_duplicate_exchanges_are_rejected_without_banning_distinct_contracts() -> None:
    design = _design()
    duplicate = deepcopy(design["exchanges"][0])
    duplicate["contract"] = "  THE selected record and its validation result. "
    design["exchanges"].append(duplicate)
    with pytest.raises(ValueError, match="duplicate exchange"):
        validate_provisional_design(design, event_orders=(1, 2))
    duplicate["contract"] = "A cancellation acknowledgement."
    assert validate_provisional_design(design, event_orders=(1, 2)) == design


def test_workstreams_may_own_multiple_components_and_exchanges_may_be_empty() -> None:
    design = _design()
    design["workstreams"][0]["component_keys"].append("capability-1")
    design["exchanges"] = []
    assert validate_provisional_design(design, event_orders=(1, 2)) == design


def test_first_run_is_an_explicit_coherent_subset_not_document_order() -> None:
    design = _design(event_orders=(1, 2, 3))
    design["first_run"]["event_orders"] = [2, 3]
    precedence = [{"before_event": 2, "after_event": 3, "constraint_index": 1}]

    assert validate_provisional_design(
        design, event_orders=(1, 2, 3), source_precedence=precedence,
        result_event_order=3,
    ) == design
    assert design["components"][0]["supported_event_orders"] == [1, 2, 3]

    design["first_run"]["event_orders"] = [3, 2]
    with pytest.raises(ValueError):
        validate_provisional_design(
            design, event_orders=(1, 2, 3), source_precedence=precedence,
            result_event_order=3,
        )


def test_first_run_may_select_one_of_two_mutually_exclusive_outcomes() -> None:
    design = _design(event_orders=(1, 2, 3, 4))
    design["first_run"]["event_orders"] = [1, 2, 3]
    precedence = [
        {"before_event": 2, "after_event": 3, "constraint_index": 1},
        {"before_event": 2, "after_event": 4, "constraint_index": 1},
    ]

    assert validate_provisional_design(
        design, event_orders=(1, 2, 3, 4), source_precedence=precedence,
        result_event_order=3,
    ) == design
    assert design["components"][0]["supported_event_orders"] == [1, 2, 3, 4]


def test_first_run_preserves_post_result_actions_and_their_source_precedence() -> None:
    design = _design()
    precedence = [{"before_event": 1, "after_event": 2, "constraint_index": 1}]
    assert validate_provisional_design(
        design, event_orders=(1, 2), source_precedence=precedence, result_event_order=1,
    ) == design
    design["first_run"]["event_orders"] = [2, 1]
    with pytest.raises(ValueError, match="precedence"):
        validate_provisional_design(
            design, event_orders=(1, 2), source_precedence=precedence, result_event_order=1,
        )


def test_model_schema_declares_the_same_closed_authority_boundary() -> None:
    assert set(PROVISIONAL_DESIGN_SCHEMA["required"]) == set(_design())
    assert PROVISIONAL_DESIGN_SCHEMA["additionalProperties"] is False
    properties = PROVISIONAL_DESIGN_SCHEMA["properties"]
    assert properties["version"]["const"] == PROVISIONAL_DESIGN_VERSION
    assert properties["authority_kind"]["const"] == "provisional_design"
    assert properties["first_run"]["additionalProperties"] is False
    assert set(properties["first_run"]["required"]) == set(_design()["first_run"])
    for owner in ("components", "workstreams", "exchanges"):
        row_schema = properties[owner]["items"]
        assert row_schema["additionalProperties"] is False
        assert set(row_schema["required"]) == set(_design()[owner][0])
    assert properties["risk_posture"]["additionalProperties"] is False
    assert set(properties["risk_posture"]["required"]) == set(_design()["risk_posture"])
    assert properties["risk_posture"]["properties"]["items"]["items"][
        "additionalProperties"
    ] is False
    risk_item = properties["risk_posture"]["properties"]["items"]["items"]
    assert set(risk_item["required"]) == {
        "key", "category", "statement", "trigger", "mitigation", "verification",
        "scope_paths",
    }
    assert "component_keys" not in risk_item["properties"]
    assert "workstream_keys" not in risk_item["properties"]
    assert "related_event_orders" not in risk_item["properties"]
    path = risk_item["properties"]["scope_paths"]["items"]
    assert path["additionalProperties"] is False
    assert set(path["required"]) == {"event_order", "component_key", "workstream_key"}


def _enveloped_intent() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    intent: dict[str, Any] = {
        "title": "Desk", "product_story": "A person needs a visible result",
        "state_object": "result", "first_path": "Desk shows result",
        "proof_boundary": "Verify the visible result",
    }
    source = "\n".join(intent.values())
    spans, facts = [], []
    cursor = 0
    for index, (field, quote) in enumerate(intent.items(), start=1):
        size = len(quote.encode("utf-8"))
        fact = {
            "fact_index": index, "field": field, "quote": quote,
            "source_start_byte": cursor, "source_end_byte": cursor + size,
            "projection_path": f"/{field}",
            "projection_start_byte": 0, "projection_end_byte": size,
        }
        facts.append(fact)
        spans.append({
            "span_id": f"source:{field}", "section_key": field, "row_index": 1,
            "classification": "product_claim", "text": quote,
            "quote_sha256": hashlib.sha256(quote.encode()).hexdigest(),
            **{key: fact[key] for key in (
                "source_start_byte", "source_end_byte", "projection_path",
                "projection_start_byte", "projection_end_byte",
            )},
        })
        cursor += size + 1
    path_fact = next(row for row in facts if row["field"] == "first_path")
    state_fact = next(row for row in facts if row["field"] == "state_object")
    relation = {
        "order": 1, "source_start_byte": path_fact["source_start_byte"],
        "source_end_byte": path_fact["source_end_byte"],
        "event_start_byte": 0, "event_end_byte": len(intent["first_path"]),
        "actor_kind": "product", "actor_fact_path": "/title", "actor_fact_quote": "Desk",
        "owner_system_path": "/title", "owner_system_quote": "Desk",
        "event_quote": intent["first_path"], "action_verb_quote": "shows",
        "target_quote": "result", "visible_result_quote": "result",
    }
    context = {
        "context_kind": "state_object", "fact_path": "/state_object", "fact_quote": "result",
        "source_start_byte": state_fact["source_start_byte"],
        "source_end_byte": state_fact["source_end_byte"], "first_path_event_order": 0,
    }
    intent[AUTHORED_SEMANTICS_KEY] = authored_semantics_mapping(
        [relation], first_path_context_relations=[context],
        provisional_design=_design(event_orders=(1,)),
        source_precedence=[],
    )
    terminal_fact = {
        **path_fact, "terminal_result_quote": "result",
        "terminal_result_source_start_byte": path_fact["source_start_byte"] + 11,
        "terminal_result_projection_start_byte": 11,
    }
    claims = derive_model_atomic_claims(
        intent=intent, selected_facts=facts, first_path_relations=[relation],
        terminal_result_fact=terminal_fact,
    )
    envelope = build_product_intent_envelope(
        intent, source_text=source, source_path="evidence.md", source_format="typed_envelope_json",
        canonical_candidate_sha256="a" * 64,
        authored_source_spans=spans, authored_atomic_claims=claims,
        authored_source_sha256=hashlib.sha256(source.encode()).hexdigest(),
    )
    authority = product_intent_authority_from_envelope(
        envelope, structured_intent_path="candidate-intent.json", markdown_source_path="evidence.md",
    )
    return intent, envelope, authority


def test_design_uses_existing_semantic_hash_without_entering_source_facts_or_atoms() -> None:
    intent, envelope, authority = _enveloped_intent()
    design = provisional_design_from_intent(intent)
    semantics = intent[AUTHORED_SEMANTICS_KEY]
    expected = authored_relation_set_sha256(
        semantics["first_path_relations"], semantics["component_responsibility_relations"],
        first_path_context_relations=semantics["first_path_context_relations"],
        provisional_design=design,
        source_precedence=semantics["source_precedence"],
    )
    assert authority[AUTHORED_RELATION_SET_SHA256_KEY] == expected
    assert envelope["custody_ledger"][AUTHORED_RELATION_SET_SHA256_KEY] == expected
    assert require_relation_authority_parity(intent, authority) == first_path_relations_from_intent(intent)
    assert envelope["product_facts"] == product_facts_payload(intent)
    assert "provisional_design" not in envelope["product_facts"]
    assert all("Capability" not in row["normalized_value"] for row in envelope["custody_ledger"]["atomic_facts"])
    design["components"][0]["name"] = "Different proposed ownership"
    assert provisional_design_from_intent(intent)["components"][0]["name"] == "Capability 0"
    mutated = deepcopy(intent)
    mutated[AUTHORED_SEMANTICS_KEY]["provisional_design"] = design
    assert product_facts_payload(mutated) == product_facts_payload(intent)
    with pytest.raises(GreenfieldAuthoredSemanticsError, match="do not match sealed"):
        require_relation_authority_parity(mutated, authority)


@pytest.mark.parametrize(
    ("owner", "field", "replacement"),
    [
        ("components", "responsibility", "A different proposed responsibility."),
        ("components", "verification", "A different boundary check."),
        ("workstreams", "deliverable", "A different proposed deliverable."),
        ("workstreams", "verification", "A different delivery acceptance."),
        ("exchanges", "contract", "A different internal exchange contract."),
    ],
)
def test_each_design_section_is_bound_without_changing_source_authority(
    owner: str, field: str, replacement: str,
) -> None:
    intent, envelope, authority = _enveloped_intent()
    changed = deepcopy(intent)
    changed[AUTHORED_SEMANTICS_KEY]["provisional_design"][owner][0][field] = replacement
    assert provisional_design_from_intent(changed)[owner][0][field] == replacement
    assert product_facts_payload(changed) == envelope["product_facts"]
    with pytest.raises(GreenfieldAuthoredSemanticsError, match="do not match sealed"):
        require_relation_authority_parity(changed, authority)


def test_first_run_rationale_is_sealed_without_becoming_a_source_fact() -> None:
    intent, envelope, authority = _enveloped_intent()
    changed = deepcopy(intent)
    changed[AUTHORED_SEMANTICS_KEY]["provisional_design"]["first_run"]["rationale"] = (
        "A different proposed execution rationale."
    )

    assert product_facts_payload(changed) == envelope["product_facts"]
    with pytest.raises(GreenfieldAuthoredSemanticsError, match="do not match sealed"):
        require_relation_authority_parity(changed, authority)


def test_valid_design_never_replaces_source_actor_validation() -> None:
    intent, _, _ = _enveloped_intent()
    original_design = provisional_design_from_intent(intent)
    intent["title"] = "A different source actor"
    assert validate_provisional_design(original_design, event_orders=(1,)) == original_design
    with pytest.raises(GreenfieldAuthoredSemanticsError, match="unbound first-path actor"):
        provisional_design_from_intent(intent)


@pytest.mark.parametrize("damage", ["missing", "retired", "unbound_event"])
def test_authored_carrier_requires_current_complete_design(damage: str) -> None:
    intent, _, _ = _enveloped_intent()
    semantics = intent[AUTHORED_SEMANTICS_KEY]
    if damage == "missing":
        semantics.pop("provisional_design")
    elif damage == "retired":
        semantics["version"] = "odylith.greenfield.authored-semantics.v13"
    else:
        semantics["provisional_design"]["components"][0]["supported_event_orders"] = [2]
    with pytest.raises(ValueError):
        provisional_design_from_intent(intent)


def test_hash_requires_design_for_every_authored_contract_but_keeps_empty_case() -> None:
    assert len(authored_relation_set_sha256(())) == 64
    intent, _, _ = _enveloped_intent()
    relations = intent[AUTHORED_SEMANTICS_KEY]["first_path_relations"]
    with pytest.raises(ValueError, match="provisional design"):
        authored_relation_set_sha256(relations)
    with pytest.raises(GreenfieldAuthoredSemanticsError, match="requires source relations"):
        authored_relation_set_sha256((), provisional_design=_design())
    with pytest.raises(ValueError):
        authored_semantics_mapping(relations, provisional_design=None)
