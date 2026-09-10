"""Result references inherit exact selected-fact custody, never global guesses."""

from __future__ import annotations

import pytest

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    GreenfieldAuthoredSemanticsError,
)
from odylith.runtime.domain_intelligence.greenfield_model_direct_evidence_graph import (
    _terminal_result_fact,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    _intent_from_typed_source_spans,
)
from tests.unit.runtime.test_greenfield_model_path_custody import _response, _source


def _compiled(proof: str, *, metrics: list[str] | None = None):
    source = _source() + "\n" + proof
    response = _response(source)["result"]
    response["facts"]["proof_boundary"] = {"quote": proof, "occurrence": 1}
    if metrics is not None:
        response["facts"]["success_metrics"] = [
            {"quote": quote, "occurrence": 1} for quote in metrics
        ]
    intent, spans, facts = _intent_from_typed_source_spans(
        response["facts"], component_rows=(), evidence_text=source,
        assumptions=[], ambiguities=[],
    )
    return source, intent, spans, facts


def _terminal(*, field="proof_boundary", row=1, occurrence=1, quote="ready list"):
    return {
        "result_fact": {"field": field, "row": row},
        "result_quote": quote,
        "result_occurrence": occurrence,
        "event_order": 1,
    }


def test_result_reference_ignores_repeated_phrase_elsewhere_in_evidence() -> None:
    proof = "A ready list is reviewable"
    source, _, _, facts = _compiled(proof)
    prefix = "Do not export a ready list.\n"
    source = prefix + source
    for fact in facts:
        fact["source_start_byte"] += len(prefix.encode())
        fact["source_end_byte"] += len(prefix.encode())

    result = _terminal_result_fact(_terminal(), selected_facts=facts, evidence_text=source)

    assert result["projection_path"] == "/proof_boundary"
    assert result["terminal_result_source_start_byte"] == source.encode().rindex(b"ready list")
    assert result["terminal_result_projection_start_byte"] == 2


def test_local_occurrence_is_strict_and_utf8_coordinates_remain_exact() -> None:
    proof = "État: ready list; après révision: ready list"
    source, _, _, facts = _compiled(proof)
    result = _terminal_result_fact(
        _terminal(occurrence=2), selected_facts=facts, evidence_text=source,
    )
    assert result["terminal_result_projection_start_byte"] == proof.encode().rindex(b"ready list")
    assert source.encode()[
        result["terminal_result_source_start_byte"]:result["terminal_result_source_end_byte"]
    ] == b"ready list"


@pytest.mark.parametrize("occurrence", [0, -1, True, "1", 2, 99])
def test_invalid_local_occurrence_never_falls_back_to_unique_match(occurrence) -> None:
    source, _, _, facts = _compiled("A ready list is reviewable")
    with pytest.raises(GreenfieldAuthoredSemanticsError):
        _terminal_result_fact(
            _terminal(occurrence=occurrence), selected_facts=facts, evidence_text=source,
        )


@pytest.mark.parametrize("field", ["problem", "title", "state_object", "operational_constraints", "unknown"])
def test_result_reference_cannot_expand_eligible_fact_roles(field: str) -> None:
    source, _, _, facts = _compiled("A ready list is reviewable")
    with pytest.raises(GreenfieldAuthoredSemanticsError):
        _terminal_result_fact(_terminal(field=field), selected_facts=facts, evidence_text=source)


@pytest.mark.parametrize("row", [0, -1, True, "1", 2, 99])
def test_absent_or_invalid_raw_row_cannot_select_another_fact(row) -> None:
    source, _, _, facts = _compiled("A ready list is reviewable")
    with pytest.raises(GreenfieldAuthoredSemanticsError):
        _terminal_result_fact(_terminal(row=row), selected_facts=facts, evidence_text=source)


@pytest.mark.parametrize("row", [1, 2, 3])
def test_duplicate_collapse_preserves_all_raw_row_identities(row: int) -> None:
    first, later = "First ready list is reviewable", "Later ready list is reviewable"
    source, intent, spans, facts = _compiled(
        first + ". " + later, metrics=[first, first, later],
    )
    result = _terminal_result_fact(
        _terminal(field="success_metrics", row=row), selected_facts=facts, evidence_text=source,
    )
    assert intent["success_metrics"] == [first, later]
    assert len([span for span in spans if span["section_key"] == "success_metrics"]) == 2
    assert result["quote"] == (first if row < 3 else later)
    assert result["projection_path"] == ("/success_metrics/0" if row < 3 else "/success_metrics/1")
    assert result["source_field_rows"] == ([1, 2] if row < 3 else [3])


def test_old_global_shape_is_not_a_second_interpretation() -> None:
    source, _, _, facts = _compiled("A ready list is reviewable")
    terminal = _terminal()
    del terminal["result_fact"]
    with pytest.raises(GreenfieldAuthoredSemanticsError):
        _terminal_result_fact(terminal, selected_facts=facts, evidence_text=source)


def test_identical_text_at_distinct_source_locations_is_not_collapsed() -> None:
    quote = "A ready list is reviewable"
    source = _source() + "\n" + quote + "\n" + quote
    response = _response(source)["result"]
    response["facts"]["success_metrics"] = [
        {"quote": quote, "occurrence": occurrence} for occurrence in (1, 2)
    ]
    _, spans, facts = _intent_from_typed_source_spans(
        response["facts"], component_rows=(), evidence_text=source,
        assumptions=[], ambiguities=[],
    )
    result = _terminal_result_fact(
        _terminal(field="success_metrics", row=2), selected_facts=facts, evidence_text=source,
    )
    assert result["source_field_rows"] == [2]
    assert result["terminal_result_source_start_byte"] == source.encode().rindex(b"ready list")
    assert result["projection_path"] == "/success_metrics/1"
    assert len([span for span in spans if span["section_key"] == "success_metrics"]) == 2


def test_result_reference_rechecks_exact_source_bytes() -> None:
    source, _, _, facts = _compiled("A ready list is reviewable")
    with pytest.raises(GreenfieldAuthoredSemanticsError):
        _terminal_result_fact(
            _terminal(), selected_facts=facts, evidence_text=source.replace("ready list", "other list"),
        )
