from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    build_product_intent_envelope,
)
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_fields import (
    prompt_field_mapping,
)
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_interpretation import (
    structured_prompt_facts,
)
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization import (
    combined_prompt_evidence_source,
)


_CORPUS_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures/greenfield-release-corpus/retired-1ba7-v3-final-holdout-regressions.v1.json"
)
_CORPUS = json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))
_TARGET_CASE_IDS = frozenset(
    {"gfhi-002", "gfhi-008", "gfhi-012", "gfhi-015", "gfhi-017", "gfhi-018"}
)
_CASES = {
    row["case_id"]: row
    for row in _CORPUS["cases"]
    if row["case_id"] in _TARGET_CASE_IDS
}
_ANNOTATIONS = {
    row["case_id"]: row
    for row in _CORPUS["annotations"]
    if row["case_id"] in _TARGET_CASE_IDS
}
_ATOMIC_CATEGORIES = (
    "actors",
    "actions",
    "states",
    "outputs",
    "constraints",
    "dependencies",
    "non_goals",
)


@pytest.mark.parametrize("case_id", sorted(_TARGET_CASE_IDS))
def test_retired_prompt_atoms_keep_operator_source_custody(case_id: str) -> None:
    prompt = str(_CASES[case_id]["prompt"])
    annotation = _ANNOTATIONS[case_id]
    envelope = build_product_intent_envelope(
        _facts_from_annotation(annotation),
        source_text=combined_prompt_evidence_source(prompt=prompt, edit_evidence=""),
        source_format="operator_prompt",
    )

    spans = envelope["source_evidence"]["spans"]
    assert any(
        span["section_key"].endswith("operator_prompt_evidence")
        and span["classification"] == "supporting_evidence"
        for span in spans
    )

    atoms = envelope["custody_ledger"]["atomic_facts"]
    for category in _ATOMIC_CATEGORIES:
        for expected in annotation[category]:
            atom = _accepted_atom(atoms, category=category, value=expected["value"])
            assert atom["source_span_ids"]
            assert atom["source_span_refs"]
            if expected.get("expected_polarity") == "prohibited":
                assert atom["polarity"] == "prohibited"


def test_retired_structured_aliases_compose_existing_typed_fields() -> None:
    markdown = prompt_field_mapping(_CASES["gfhi-008"]["prompt"])
    structured = structured_prompt_facts(_CASES["gfhi-008"]["prompt"])

    assert markdown["actor"] == "release clerk"
    assert markdown["state"] == "prepared -> reviewed."
    assert markdown["constraint"] == "read-only."
    assert structured.actor == "release clerk"
    assert structured.first_path_contract is not None
    assert structured.first_path_contract.complete is True

    mixed = prompt_field_mapping(_CASES["gfhi-018"]["prompt"])
    structured_mixed = structured_prompt_facts(_CASES["gfhi-018"]["prompt"])

    assert mixed["actor"] == "index steward"
    assert mixed["action"] == "choose one candidate heading and accept it"
    assert mixed["state"] == "candidate to accepted"
    assert mixed["visible result"] == "acceptance glyph"
    assert mixed["constraint"] == "no remote lookup; no automatic rewrite"
    assert mixed["research note"] == str(_CASES["gfhi-018"]["prompt"]).split(
        "Research note:", maxsplit=1
    )[1].strip()
    assert structured_mixed.actor == "index steward"
    assert structured_mixed.first_path_contract is not None
    assert structured_mixed.first_path_contract.complete is True


def test_markdown_state_change_and_boundary_aliases_remain_typed() -> None:
    mapping = prompt_field_mapping(_CASES["gfhi-002"]["prompt"])

    assert mapping["state"] == "one intake card goes from ready to claimed."
    assert mapping["constraint"] == "do not reassign cards automatically."


def _facts_from_annotation(annotation: Mapping[str, object]) -> dict[str, object]:
    values = {
        category: [str(row["value"]) for row in _rows(annotation.get(category))]
        for category in _ATOMIC_CATEGORIES
    }
    output = values["outputs"][0]
    return {
        "product_story": output,
        "state_object": values["states"][0],
        "first_path": values["actions"][0],
        "proof_boundary": output,
        "human_actors": values["actors"],
        "external_systems": values["dependencies"],
        "operational_constraints": values["constraints"],
        "non_goals": values["non_goals"],
    }


def _accepted_atom(
    atoms: Sequence[Mapping[str, object]],
    *,
    category: str,
    value: str,
) -> Mapping[str, object]:
    expected = value.casefold().strip(" .")
    return next(
        atom
        for atom in atoms
        if category in atom["categories"]
        and atom["custody_state"] == "accepted_fact"
        and str(atom["normalized_value"]).casefold().strip(" .") == expected
    )


def _rows(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(row for row in value if isinstance(row, Mapping))
