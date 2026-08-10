from __future__ import annotations

from collections.abc import Mapping

import pytest

from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import require_atomic_fact_ledger
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import build_product_intent_envelope
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    product_intent_authority_from_envelope,
)


_SOURCE = (
    "A permit coordinator submits a signed application, verifies the accepted state, and publishes a permit "
    "receipt through Registry API; the product must not expose sealed identity evidence."
)
_FACTS = {
    "product_story": "Permit Review helps a permit coordinator complete one review and see a permit receipt.",
    "state_object": "The primary state object is a signed application.",
    "first_path": (
        "A permit coordinator submits a signed application, verifies the accepted state, and publishes a permit "
        "receipt through Registry API; the product must not expose sealed identity evidence."
    ),
    "proof_boundary": (
        "The first release proves one permit receipt; the product must not expose sealed identity evidence."
    ),
    "human_actors": ["Permit coordinator: submits and verifies the application."],
    "external_systems": ["Registry API - receives the signed application."],
    "non_goals": ["The product must not expose sealed identity evidence."],
}


def test_atomic_fact_ledger_binds_supported_atoms_to_source_and_projection() -> None:
    authority = _authority(facts=_FACTS, source=_SOURCE)
    atoms = authority["atomic_facts"]

    _assert_accepted(atoms, "Permit coordinator", category="actors", field="human_actors")
    _assert_accepted(atoms, "submits a signed application", category="actions", field="first_path")
    _assert_accepted(atoms, "verifies the accepted state", category="states", field="first_path")
    _assert_accepted(atoms, "publishes a permit receipt through Registry API", category="outputs", field="first_path")
    _assert_accepted(atoms, "signed application", category="states", field="state_object")
    _assert_accepted(atoms, "Registry API", category="dependencies", field="external_systems")
    _assert_accepted(
        atoms,
        "must not expose sealed identity evidence",
        category="non_goals",
        field="non_goals",
    )
    require_atomic_fact_ledger(atoms)


def test_atomic_fact_ledger_keeps_unsupported_projection_bounded() -> None:
    facts = {
        **_FACTS,
        "first_path": (
            "A permit coordinator submits a signed application, verifies the accepted state, emails a regulator, "
            "and publishes a permit receipt through Registry API."
        ),
    }

    atoms = _authority(facts=facts, source=_SOURCE)["atomic_facts"]
    email_atom = _atom(atoms, "emails a regulator")

    assert email_atom["custody_state"] == "bounded_interpretation"
    assert email_atom["source_span_ids"] == []
    assert email_atom["source_span_refs"] == []


def test_atomic_fact_ledger_does_not_promote_supporting_evidence_to_product_truth() -> None:
    facts = {
        **_FACTS,
        "external_systems": ["Archive API - optional research integration."],
    }
    source = (
        f"## First Path\n{_SOURCE}\n\n"
        "## Research Notes\nArchive API is a possible future integration."
    )

    atoms = _authority(facts=facts, source=source)["atomic_facts"]
    archive_atom = _atom(atoms, "Archive API")

    assert archive_atom["custody_state"] == "bounded_interpretation"
    assert archive_atom["source_span_ids"] == []


def test_atomic_fact_ledger_excludes_inline_source_metadata_from_prompt_custody() -> None:
    facts = {
        **_FACTS,
        "external_systems": ["Archive API - optional research integration."],
    }
    source = f"{_SOURCE} Source evidence: Archive API supports long-term storage."

    atoms = _authority(facts=facts, source=source)["atomic_facts"]
    archive_atom = _atom(atoms, "Archive API")

    assert archive_atom["custody_state"] == "bounded_interpretation"
    assert archive_atom["source_span_ids"] == []


def test_atomic_fact_ledger_does_not_reverse_source_polarity() -> None:
    source = "A permit coordinator must not publish a permit receipt before review."
    facts = {
        **_FACTS,
        "first_path": "A permit coordinator publishes a permit receipt before review.",
        "proof_boundary": "The first release proves a published permit receipt.",
    }

    atoms = _authority(facts=facts, source=source)["atomic_facts"]
    publish_atom = _atom(atoms, "publishes a permit receipt before review")

    assert publish_atom["polarity"] == "affirmed"
    assert publish_atom["custody_state"] == "bounded_interpretation"


def test_atomic_fact_ledger_binds_positive_dependency_beside_a_prohibition() -> None:
    source = (
        "The first release must retain evidence for seven years, must not auto-approve requests, "
        "and depends on the Registry API."
    )
    facts = {
        **_FACTS,
        "external_systems": ["Registry API"],
        "non_goals": ["must not auto-approve requests"],
    }

    atoms = _authority(facts=facts, source=source)["atomic_facts"]

    dependency = next(
        atom
        for atom in atoms
        if atom["normalized_value"] == "Registry API" and "dependencies" in atom["categories"]
    )
    assert dependency["polarity"] == "affirmed"
    assert dependency["custody_state"] == "accepted_fact"
    assert dependency["source_span_ids"]


def test_atomic_fact_ledger_keeps_internal_system_projections_out_of_dependencies() -> None:
    source = "Route stewards read the forecast service and publish a reopening notice."
    facts = {
        **_FACTS,
        "external_systems": ["forecast service"],
        "internal_systems": ["Forecast Service Read Record"],
    }

    atoms = _authority(facts=facts, source=source)["atomic_facts"]
    dependency_values = {
        atom["normalized_value"]
        for atom in atoms
        if "dependencies" in atom["categories"]
    }

    assert dependency_values == {"forecast service"}
    assert "actions" in _atom(atoms, "Forecast Service Read Record")["categories"]


def test_atomic_fact_ledger_binds_each_required_external_source_subject() -> None:
    source = "The insurer directory and pharmacy status feed are required external sources."
    facts = {
        **_FACTS,
        "external_systems": ["insurer directory", "pharmacy status feed"],
    }

    atoms = _authority(facts=facts, source=source)["atomic_facts"]

    _assert_accepted(atoms, "insurer directory", category="dependencies", field="external_systems")
    _assert_accepted(atoms, "pharmacy status feed", category="dependencies", field="external_systems")


@pytest.mark.parametrize(
    ("source", "systems"),
    (
        (
            "The insurer directory or pharmacy status feed are required external sources.",
            ("insurer directory", "pharmacy status feed"),
        ),
        (
            "The insurer directory, pharmacy status feed, and transcript vendor are required external sources.",
            ("insurer directory", "pharmacy status feed", "transcript vendor"),
        ),
    ),
)
def test_atomic_fact_ledger_binds_required_external_source_lists(
    source: str,
    systems: tuple[str, ...],
) -> None:
    facts = {**_FACTS, "external_systems": list(systems)}

    atoms = _authority(facts=facts, source=source)["atomic_facts"]

    for value in systems:
        _assert_accepted(atoms, value, category="dependencies", field="external_systems")


def test_atomic_fact_ledger_does_not_affirm_coordinated_prohibited_sources() -> None:
    source = "The insurer directory, pharmacy status feed, and transcript vendor are prohibited external sources."
    facts = {
        **_FACTS,
        "external_systems": ["insurer directory", "pharmacy status feed", "transcript vendor"],
    }

    atoms = _authority(facts=facts, source=source)["atomic_facts"]

    for value in facts["external_systems"]:
        atom = _atom(atoms, value)
        assert atom["custody_state"] == "bounded_interpretation"
        assert atom["source_span_ids"] == []


def test_atomic_fact_ledger_keeps_hyphenated_state_labels_affirmed() -> None:
    source = "A stale reading keeps the mission in entry-prohibited state."
    facts = {
        **_FACTS,
        "first_path": source,
        "state_object": "The primary state object is the mission.",
    }

    atoms = _authority(facts=facts, source=source)["atomic_facts"]
    state_atom = _atom(atoms, "entry-prohibited state")

    assert state_atom["polarity"] == "affirmed"
    assert "states" in state_atom["categories"]
    assert state_atom["custody_state"] == "accepted_fact"


def test_atomic_fact_ledger_preserves_complete_sentence_units_outside_first_path() -> None:
    story = "The workspace keeps source input, current state, blockers, handoffs, and proof evidence visible."
    non_goal = "Do not claim adjacent automation, live dependency behavior, or operational scale."
    facts = {**_FACTS, "product_story": story, "non_goals": [non_goal]}
    source = f"## Product Story\n{story}\n\n## Non-goals\n{non_goal}"

    atoms = _authority(facts=facts, source=source)["atomic_facts"]

    assert _atom(atoms, "keeps source input")["normalized_value"] == story.rstrip(".")
    assert _atom(atoms, "Do not claim adjacent automation")["normalized_value"] == non_goal.rstrip(".")
    assert all(row["normalized_value"] not in {"blockers", "handoffs"} for row in atoms)


def test_atomic_fact_ledger_rejects_adjacency_without_entailment() -> None:
    envelope = _envelope(facts=_FACTS, source=_SOURCE)
    authority = product_intent_authority_from_envelope(
        envelope,
        structured_intent_path="candidate-intent.json",
        markdown_source_path="operator-prompt.txt",
    )
    atoms = authority["atomic_facts"]
    bounded = _atom(atoms, "Permit Review helps")
    accepted = next(row for row in atoms if row["custody_state"] == "accepted_fact")
    tampered = [dict(row) for row in atoms]
    index = atoms.index(bounded)
    tampered[index] = {
        **bounded,
        "custody_state": "accepted_fact",
        "entailment_relationship": "ordered_source_entailment",
        "source_span_ids": [accepted["source_span_ids"][0]],
        "source_span_refs": [accepted["source_span_refs"][0]],
    }

    with pytest.raises(ValueError, match="source entailment custody"):
        require_atomic_fact_ledger(tampered, source_spans=envelope["source_evidence"]["spans"])


def test_atomic_fact_ledger_rejects_tampered_source_hash_and_atom_id() -> None:
    envelope = _envelope(facts=_FACTS, source=_SOURCE)
    atoms = envelope["custody_ledger"]["atomic_facts"]
    accepted = next(row for row in atoms if row["custody_state"] == "accepted_fact")
    accepted_index = atoms.index(accepted)
    tampered_hash = [dict(row) for row in atoms]
    tampered_hash[accepted_index] = {
        **accepted,
        "source_span_refs": [{**accepted["source_span_refs"][0], "text_sha256": "0" * 64}],
    }

    with pytest.raises(ValueError, match="source entailment custody"):
        require_atomic_fact_ledger(
            tampered_hash,
            source_spans=envelope["source_evidence"]["spans"],
            facts=envelope["product_facts"],
        )

    tampered_id = [dict(row) for row in atoms]
    tampered_id[accepted_index] = {**accepted, "atom_id": "AF-0000000000000000"}

    with pytest.raises(ValueError, match="invalid atom id"):
        require_atomic_fact_ledger(tampered_id, facts=envelope["product_facts"])


def test_atomic_fact_ledger_rejects_projection_not_present_in_canonical_facts() -> None:
    envelope = _envelope(facts=_FACTS, source=_SOURCE)
    atoms = envelope["custody_ledger"]["atomic_facts"]
    accepted = next(row for row in atoms if row["custody_state"] == "accepted_fact")
    accepted_index = atoms.index(accepted)
    tampered = [dict(row) for row in atoms]
    tampered[accepted_index] = {
        **accepted,
        "projection_links": [
            {
                **accepted["projection_links"][0],
                "field": "assumptions",
                "path": "/assumptions/0/units/0",
            }
        ],
    }

    with pytest.raises(ValueError, match="canonical projection"):
        require_atomic_fact_ledger(tampered, facts=envelope["product_facts"])


def _authority(*, facts: Mapping[str, object], source: str) -> dict[str, object]:
    envelope = _envelope(facts=facts, source=source)
    return product_intent_authority_from_envelope(
        envelope,
        structured_intent_path="candidate-intent.json",
        markdown_source_path="operator-prompt.txt",
    )


def _envelope(*, facts: Mapping[str, object], source: str) -> dict[str, object]:
    staged_source = source if source.lstrip().startswith("#") else f"# Operator prompt evidence\n\n{source}"
    return build_product_intent_envelope(
        facts,
        source_text=staged_source,
        source_path="operator-prompt.txt",
        source_format="operator_prompt",
    )


def _atom(atoms: list[dict[str, object]], value: str) -> dict[str, object]:
    return next(row for row in atoms if value.casefold() in str(row["normalized_value"]).casefold())


def _assert_accepted(
    atoms: list[dict[str, object]],
    value: str,
    *,
    category: str,
    field: str,
) -> None:
    atom = next(
        row
        for row in atoms
        if value.casefold() in str(row["normalized_value"]).casefold()
        and category in row["categories"]
        and any(link["field"] == field for link in row["projection_links"])
    )
    assert atom["custody_state"] == "accepted_fact"
    assert category in atom["categories"]
    assert atom["source_span_ids"]
    assert atom["source_span_refs"]
    assert any(link["field"] == field for link in atom["projection_links"])
