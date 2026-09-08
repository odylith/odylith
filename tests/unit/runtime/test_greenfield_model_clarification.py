"""Focused custody contract for model-selected Greenfield clarification."""

from __future__ import annotations

import hashlib
import json
import os

import pytest

from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_MODEL_PROOF_FD_ENV,
    GreenfieldAuthoringClarification,
    GreenfieldModelAuthoringError,
    author_greenfield_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    GreenfieldClarificationRequired,
    materialize_model_authored_intent,
)
from odylith.runtime.domain_intelligence.greenfield_proposals_cli import (
    _print_greenfield_clarification,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    AdmittingReviewProvider,
    StructuredAuthoringProvider,
    clarification_response,
)
from tests.unit.runtime.test_greenfield_model_path_custody import _source


def _clarification(
    *,
    status: str = "material_ambiguity",
    quotes: tuple[str, ...] = (),
    dimension: str = "first_path",
) -> dict[str, object]:
    return clarification_response(
        question="test-only wording",
        material_dimension=dimension,
        evidence_quotes=quotes,
        consistency_status=status,
    )


def test_missing_information_binds_the_complete_evidence_without_a_model_quote() -> None:
    source = "Create a review workspace, but the first usable task is not specified."
    provider = StructuredAuthoringProvider(_clarification())

    result = author_greenfield_intent(
        evidence_text=source,
        provider=provider,
        clock=lambda: 0.0,
        review_provider_factory=AdmittingReviewProvider,
    )

    assert isinstance(result, GreenfieldAuthoringClarification)
    assert result.required_fields == ("first_path",)
    assert result.consistency_status == "material_ambiguity"
    assert result.consistency_source_spans == (
        {
            "span_id": "authoring:consistency:1",
            "section_key": "ambiguities",
            "row_index": 1,
            "classification": "supporting_evidence",
            "text": source,
            "source_start_byte": 0,
            "source_end_byte": len(source.encode("utf-8")),
            "quote_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        },
    )
    assert provider.calls == 1


def test_missing_information_preserves_unicode_byte_custody() -> None:
    source = "Créer un aperçu δ without a stated first task."

    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(_clarification()),
        clock=lambda: 0.0,
        review_provider_factory=AdmittingReviewProvider,
    )

    span = result.consistency_source_spans[0]
    assert span["source_end_byte"] == len(source.encode("utf-8"))
    assert span["text"].encode("utf-8") == source.encode("utf-8")
    assert span["quote_sha256"] == hashlib.sha256(source.encode("utf-8")).hexdigest()


def test_missing_information_accepts_bounded_evidence_longer_than_a_fact_quote() -> None:
    source = "Describe the missing task. " + ("x" * 3_000)

    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(_clarification()),
        clock=lambda: 0.0,
        review_provider_factory=AdmittingReviewProvider,
    )

    assert result.consistency_source_spans[0]["text"] == source
    assert result.consistency_source_spans[0]["source_end_byte"] == len(source)


def test_missing_information_rejects_a_copied_quote_instead_of_ignoring_it() -> None:
    source = "The first usable task is not specified."
    provider = StructuredAuthoringProvider(
        _clarification(quotes=("The first usable task is not specified.",))
    )

    with pytest.raises(GreenfieldModelAuthoringError, match="attached copied evidence"):
        author_greenfield_intent(
            evidence_text=source,
            provider=provider,
            clock=lambda: 0.0,
            review_provider_factory=AdmittingReviewProvider,
        )
    assert provider.calls == 1


def test_material_contradiction_keeps_two_exact_distinct_source_sides() -> None:
    first = "Keep the record for seven years."
    second = "Delete the record after thirty days."
    source = f"{first} {second}"

    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(
            _clarification(
                status="material_contradiction",
                quotes=(first, second),
                dimension="operational_constraints",
            )
        ),
        clock=lambda: 0.0,
        review_provider_factory=AdmittingReviewProvider,
    )

    assert [span["text"] for span in result.consistency_source_spans] == [
        first,
        second,
    ]
    assert [span["source_start_byte"] for span in result.consistency_source_spans] == [
        0,
        len(first.encode("utf-8")) + 1,
    ]


@pytest.mark.parametrize(
    "quotes",
    [
        ("Keep the record for seven years.",),
        ("Keep the record for seven years.", "Archive it after thirty days."),
        ("Keep the record for seven years.  ", "Delete the record after thirty days."),
        ("Keep the record for seven years.", "Keep the record for seven years."),
    ],
    ids=("missing-side", "false-side", "whitespace-altered", "duplicate-side"),
)
def test_material_contradiction_rejects_incomplete_or_inexact_sides(
    quotes: tuple[str, ...],
) -> None:
    source = "Keep the record for seven years. Delete the record after thirty days."
    provider = StructuredAuthoringProvider(
        _clarification(
            status="material_contradiction",
            quotes=quotes,
            dimension="operational_constraints",
        )
    )

    with pytest.raises(GreenfieldModelAuthoringError):
        author_greenfield_intent(
            evidence_text=source,
            provider=provider,
            clock=lambda: 0.0,
            review_provider_factory=AdmittingReviewProvider,
        )
    assert provider.calls == 1


def test_material_dimension_schema_distinguishes_path_from_product_boundary() -> None:
    provider = StructuredAuthoringProvider(_clarification())
    author_greenfield_intent(
        evidence_text="Create a product without a stated task.",
        provider=provider,
        clock=lambda: 0.0,
        review_provider_factory=AdmittingReviewProvider,
    )

    request = provider.requests[0]
    result_schema = request.output_schema["properties"]["result"]["anyOf"][1]
    description = result_schema["properties"]["clarification"]["properties"][
        "material_dimension"
    ]["description"]
    assert "first_path" in description and "actor, task, or result" in description
    assert "product_boundary" in description and "responsibility or scope limit" in description


def test_one_call_clarification_retains_exact_source_and_only_author_role(
    tmp_path, monkeypatch,
) -> None:
    source = "Create a workspace without a stated first task."
    response = _clarification()
    provider = StructuredAuthoringProvider(response)
    observation = tmp_path / "observation.json"
    descriptor = os.open(observation, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    monkeypatch.setenv(GREENFIELD_MODEL_PROOF_FD_ENV, str(descriptor))
    ticks = iter((0.0, 28.0))
    try:
        result = author_greenfield_intent(
            evidence_text=source, provider=provider, clock=lambda: next(ticks, 28.0),
            review_provider_factory=AdmittingReviewProvider,
        )
    finally:
        os.close(descriptor)

    assert isinstance(result, GreenfieldAuthoringClarification)
    assert result.required_fields == ("first_path",)
    assert result.consistency_source_spans[0]["text"] == source
    assert result.elapsed_seconds == 28.0
    assert result.semantic_model_call_count == provider.calls == 1
    assert provider.requests[0].timeout_seconds == 55.0
    retained = json.loads(observation.read_text())
    assert retained["semantic_model_call_count"] == 1
    assert retained["response"] == response
    assert retained["initial_authoring"]["request_role"] == "initial_authoring"
    assert "source_review" not in retained
    assert "initial_response" not in retained
    assert "facts" not in retained["response"]["result"]


def test_author_contradiction_uses_exact_two_side_validation():
    first = "Send review notices automatically."
    second = "Never send review notices."
    source = f"{first} {second}"
    provider = StructuredAuthoringProvider(_clarification(
        status="material_contradiction", quotes=(first, second),
        dimension="operational_constraints",
    ))
    result = author_greenfield_intent(evidence_text=source, provider=provider, clock=lambda: 0.0, review_provider_factory=AdmittingReviewProvider)

    assert isinstance(result, GreenfieldAuthoringClarification)
    assert [span["text"] for span in result.consistency_source_spans] == [first, second]
    assert provider.calls == 1


@pytest.mark.parametrize("mutation", [
    "extra-field", "mixed-corrections", "wrong-status", "invalid-dimension",
    "copied-ambiguity-quote", "missing-contradiction-side", "legacy-corrections",
])
def test_clarification_rejects_invalid_outcome_without_another_call(mutation):
    response = _clarification()
    result = response["result"]
    if mutation == "extra-field":
        result["facts"] = {}
    elif mutation == "mixed-corrections":
        result["corrections"] = []
    elif mutation == "wrong-status":
        result["status"] = "authored"
    elif mutation == "invalid-dimension":
        result["clarification"]["material_dimension"] = "invented"
    elif mutation == "copied-ambiguity-quote":
        result["consistency"]["evidence_quotes"] = [{"quote": _source(), "occurrence": 1}]
    elif mutation == "missing-contradiction-side":
        result["consistency"]["status"] = "material_contradiction"
    else:
        response = {"corrections": []}
    provider = StructuredAuthoringProvider(response)
    with pytest.raises(GreenfieldModelAuthoringError):
        author_greenfield_intent(evidence_text=_source(), provider=provider, clock=lambda: 0.0, review_provider_factory=AdmittingReviewProvider)
    assert provider.calls == 1


def test_clarification_cannot_extend_the_shared_deadline():
    provider = StructuredAuthoringProvider(_clarification())
    ticks = iter((0.0, 55.001))
    with pytest.raises(GreenfieldModelAuthoringError, match="exceeded"):
        author_greenfield_intent(
            evidence_text="The first task is unspecified.", provider=provider,
            clock=lambda: next(ticks, 55.001),
            review_provider_factory=AdmittingReviewProvider,
        )
    assert provider.calls == 1


@pytest.mark.parametrize("claims", [
    ("Fern Desk must send review notices automatically.", "Fern Desk must never send review notices."),
    ("Keep the record for seven years.", "Delete the record after thirty days."),
    ('Keep the label "Révision δ".\nPreserve the original.', 'Never keep the label "Révision δ".'),
])
def test_contradiction_handoff_presents_exact_claims_and_one_choice_question(
    tmp_path, capsys, claims,
):
    source = " ".join(claims)
    provider = StructuredAuthoringProvider(_clarification(
        status="material_contradiction", quotes=claims, dimension="product_boundary",
    ))
    receipt = {}
    with pytest.raises(GreenfieldClarificationRequired) as captured:
        materialize_model_authored_intent(
            prompt=source, repo_root=tmp_path, authoring_provider=provider,
            authoring_receipt=receipt,
            review_provider_factory=AdmittingReviewProvider,
        )
    exc = captured.value
    question = "Which of these conflicting requirements should this project follow?"
    assert exc.question == question
    assert receipt["semantic_model_call_count"] == 1
    assert [span["text"] for span in receipt["consistency_assessment"]["source_spans"]] == list(claims)
    assert list(tmp_path.iterdir()) == []

    _print_greenfield_clarification(exc, as_json=False)
    output = capsys.readouterr().out
    expected_claims = "\n".join(f"- {json.dumps(claim, ensure_ascii=False)}" for claim in claims)
    assert f"Conflicting requirements from your request:\n{expected_claims}\n{question}\n" in output
    _print_greenfield_clarification(exc, as_json=True)
    payload = json.loads(capsys.readouterr().out)
    assert payload["clarification"]["question"] == question
    assert payload["clarification"]["consistency_assessment"] == receipt["consistency_assessment"]
    assert set(payload) == {"mode", "clarification"}


def test_missing_path_handoff_preserves_question_without_conflicting_claims(
    tmp_path, capsys,
):
    with pytest.raises(GreenfieldClarificationRequired) as captured:
        materialize_model_authored_intent(
            prompt="Create a product without a stated first workflow.",
            repo_root=tmp_path, authoring_provider=StructuredAuthoringProvider(_clarification()),
            review_provider_factory=AdmittingReviewProvider,
        )
    _print_greenfield_clarification(captured.value, as_json=False)
    output = capsys.readouterr().out
    assert "Who uses this product first, what complete task do they finish, and what result do they see?" in output
    assert "Conflicting requirements" not in output
    assert list(tmp_path.iterdir()) == []
