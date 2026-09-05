from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import sys

import pytest

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import greenfield_semantic_release_score as score_module
from greenfield_matrix_corpus_provenance import GreenfieldCaseProvenance
from greenfield_matrix_statistics import release_slice_contract
from greenfield_matrix_statistics import release_slice_minimum_sample_contract
from greenfield_matrix_statistics import release_statistical_confidence_contract
from greenfield_matrix_types import GreenfieldArtifactCounts
from greenfield_matrix_types import GreenfieldMatrixResult
from greenfield_matrix_types import GreenfieldQualityVerdict
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase
from greenfield_preconfirm_matrix_cases import case_evidence
from greenfield_relation_fidelity import RELATION_FIDELITY_ANNOTATION_VERSION
from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import append_atomic_source_spans
from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import atomic_fact_ledger_hash
from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import build_atomic_fact_ledger
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import combined_prompt_evidence_source
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_SEMANTICS_VERSION,
    authored_relation_set_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID,
    get_greenfield_model_profile,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    greenfield_operating_envelope_receipt,
)


TEST_CONFIDENCE = {
    **release_statistical_confidence_contract(),
    "atomic_semantic_fidelity": 0.2,
    "relation_fidelity": 0.2,
    "clarification_identity": 0.2,
    "unnecessary_question_rate_ceiling": 0.8,
    "overall_case_success": 0.2,
    "worst_slice_success": 0.2,
}
FLOORS = {
    "atomic_semantic_fidelity": 0.2,
    "relation_fidelity": 0.2,
    "clarification_identity": 0.2,
    "unnecessary_question_rate_ceiling": 0.8,
    "overall_case_success": 0.2,
    "worst_slice_success": 0.2,
    "release_slice_minimum_samples": release_slice_minimum_sample_contract(),
    "statistical_confidence": TEST_CONFIDENCE,
}
EXACT_RELEASE_FLOORS = {
    "atomic_semantic_fidelity": 1.0,
    "relation_fidelity": 1.0,
    "clarification_identity": 1.0,
    "unnecessary_question_rate_ceiling": 0.0,
    "overall_case_success": 1.0,
    "worst_slice_success": 1.0,
    "release_slice_minimum_samples": release_slice_minimum_sample_contract(),
    "statistical_confidence": release_statistical_confidence_contract(),
}
FIRST_PATH = (
    "Operator submits one signed permit to Registry API and reviews the accepted permit receipt"
)
PROMPT = f"Permit Desk supports this path: {FIRST_PATH}."
_RUNTIME_REQUIRE_ATOMIC_LEDGER = score_module.require_atomic_fact_ledger


@pytest.fixture(autouse=True)
def _isolate_structural_scoring_from_runtime_ledger_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(score_module, "require_atomic_fact_ledger", lambda *_args, **_kwargs: None)


def test_structural_release_passes_exact_commit_and_clarification() -> None:
    commit = _case("commit", expectation="transaction_committed")
    clarify = _case("clarify", expectation="clarification_required")

    report = score_module.evaluate_semantic_release(
        cases=(commit, clarify),
        annotations={
            "commit": _commit_annotation(),
            "clarify": _clarification_annotation(),
        },
        results=(_commit_result(commit), _clarification_result(clarify)),
        floors=FLOORS,
    )

    assert report["passed"] is True
    assert report["p0_count"] == 0
    assert report["metrics"]["atomic_semantic_fidelity"]["rate"] == 1.0
    assert report["metrics"]["clarification_identity"]["rate"] == 1.0
    assert report["overall_case_success"]["confidence_interval_95"]["method"] == "wilson"
    assert len(report["normalized_semantic_digests"]["commit"]) == 64


def test_structural_release_accepts_the_runtime_authored_atomic_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        score_module,
        "require_atomic_fact_ledger",
        _RUNTIME_REQUIRE_ATOMIC_LEDGER,
    )
    case = _case("runtime-schema", expectation="transaction_committed")
    evidence = combined_prompt_evidence_source(prompt=case.prompt, edit_evidence="")
    quote = "Operator"
    quote_bytes = quote.encode("utf-8")
    start = evidence.encode("utf-8").index(quote_bytes)
    claim = {
        "field": "human_actors",
        "category": "actors",
        "polarity": "affirmed",
        "source_start_byte": start,
        "source_end_byte": start + len(quote_bytes),
        "quote": quote,
        "quote_sha256": hashlib.sha256(quote_bytes).hexdigest(),
        "projection_path": "/human_actors/0",
        "projection_start_byte": 0,
        "projection_end_byte": len(quote_bytes),
        "projection_value_sha256": hashlib.sha256(quote_bytes).hexdigest(),
        "relation_order": 1,
        "relation_role": "actor_fact_quote",
    }
    spans: list[dict[str, object]] = []
    append_atomic_source_spans(spans, authored_atomic_claims=[claim])
    ledger = build_atomic_fact_ledger(
        facts={"human_actors": [quote]},
        spans=spans,
        authored_atomic_claims=[claim],
    )
    result = _commit_result(case, atoms=ledger)
    annotation = _commit_annotation()
    annotation["atoms"][0]["source"] = {
        "source_id": "operator_evidence",
        "start_byte": start,
        "end_byte": start + len(quote_bytes),
        "quote_sha256": hashlib.sha256(quote_bytes).hexdigest(),
    }

    report = score_module.evaluate_semantic_release(
        cases=(case,),
        annotations={case.case_id: annotation},
        results=(result,),
        floors=FLOORS,
        _include_model_profiles=False,
        _allow_not_applicable_metrics=True,
    )

    assert report["passed"] is True


@pytest.mark.parametrize(
    ("damage", "expected_p0"),
    (
        ("category", "expected_atomic_fact_missing"),
        ("polarity", "expected_atomic_fact_missing"),
        ("source", "expected_atomic_fact_missing"),
        ("projection", "expected_atomic_fact_missing"),
    ),
)
def test_structural_release_rejects_mismatched_atom_identity(
    damage: str,
    expected_p0: str,
) -> None:
    case = _case(f"wrong-{damage}", expectation="transaction_committed")
    result = _commit_result(case)
    atom = result.evidence["preconfirm_dry_run"]["semantic_snapshot"]["atomic_facts"][0]
    if damage == "category":
        atom["categories"] = ["outputs"]
    elif damage == "polarity":
        atom["polarity"] = "required"
    elif damage == "source":
        atom["source_span_refs"][0]["source_start_byte"] += 1
    else:
        atom["projection_links"][0]["relation_role"] = "target_quote"
    _refresh_hash(result)

    report = score_module.evaluate_semantic_release(
        cases=(case,),
        annotations={case.case_id: _commit_annotation()},
        results=(result,),
        floors=FLOORS,
    )

    assert report["passed"] is False
    assert {row["category"] for row in report["p0_findings"]} == {
        expected_p0,
        "unexpected_atomic_fact",
    }
    assert case.case_id not in report["normalized_semantic_digests"]


def test_structural_release_rejects_invalid_or_hash_mismatched_custody(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case("invalid-ledger", expectation="transaction_committed")
    result = _commit_result(case)

    def _reject(*_args: object, **_kwargs: object) -> None:
        raise ValueError("malformed")

    monkeypatch.setattr(score_module, "require_atomic_fact_ledger", _reject)
    report = score_module.evaluate_semantic_release(
        cases=(case,),
        annotations={case.case_id: _commit_annotation()},
        results=(result,),
        floors=FLOORS,
    )

    assert report["p0_findings"] == [
        {"case_id": "invalid-ledger", "category": "atomic_custody_invalid"}
    ]


def test_reference_only_annotations_do_not_change_equivalence_or_score() -> None:
    prompt = f"{PROMPT} Auditor observes the receipt."
    case = _case("reference", expectation="transaction_committed", prompt=prompt)
    annotation = _commit_annotation(prompt=prompt)
    reference = _expected_atom(
        prompt=prompt,
        quote="Auditor",
        role="reference_only",
        relation_order=0,
        relation_role="",
    )
    reference["id"] = "reference-actor"
    annotation["atoms"].append(reference)
    actual_reference = _actual_atom(
        prompt=prompt,
        quote="Auditor",
        relation_order=0,
        relation_role="",
    )
    result = _commit_result(case, atoms=[_actual_atom(prompt=prompt), actual_reference])

    report = score_module.evaluate_semantic_release(
        cases=(case,),
        annotations={case.case_id: annotation},
        results=(result,),
        floors=FLOORS,
        _include_model_profiles=False,
        _allow_not_applicable_metrics=True,
    )

    assert report["passed"] is True
    assert report["metrics"]["atomic_semantic_fidelity"] == {
        "name": "atomic_semantic_fidelity",
        "status": "measured",
        "numerator": 1,
        "denominator": 1,
        "rate": 1.0,
        "confidence_interval_95": {
            "method": "wilson",
            "lower": 0.206549,
            "upper": 1.0,
            "inference_scope": (
                "descriptive fixed-corpus score interval; not a population user-utility claim"
            ),
        },
    }


def test_unannotated_extra_atom_is_a_p0() -> None:
    prompt = f"{PROMPT} Auditor observes the receipt."
    case = _case("extra", expectation="transaction_committed", prompt=prompt)
    result = _commit_result(
        case,
        atoms=[_actual_atom(prompt=prompt), _actual_atom(prompt=prompt, quote="Auditor")],
    )

    report = score_module.evaluate_semantic_release(
        cases=(case,),
        annotations={case.case_id: _commit_annotation(prompt=prompt)},
        results=(result,),
        floors=FLOORS,
    )

    assert {row["category"] for row in report["p0_findings"]} == {"unexpected_atomic_fact"}


def test_clarification_requires_exact_field_and_product_question() -> None:
    case = _case("clarify", expectation="clarification_required")
    result = _clarification_result(case)
    result.evidence["clarification"]["question"] = "What should happen first?"

    report = score_module.evaluate_semantic_release(
        cases=(case,),
        annotations={case.case_id: _clarification_annotation()},
        results=(result,),
        floors=FLOORS,
    )

    assert report["passed"] is False
    assert report["case_outcomes"][0]["failed_dimensions"] == ["clarification_identity"]


def test_structural_release_rejects_duplicate_result_ids() -> None:
    case = _case("duplicate", expectation="transaction_committed")
    result = _commit_result(case)

    report = score_module.evaluate_semantic_release(
        cases=(case,),
        annotations={case.case_id: _commit_annotation()},
        results=(result, result),
        floors=FLOORS,
    )

    assert report["passed"] is False
    assert report["duplicate_result_ids"] == ["duplicate"]


def test_release_slices_ignore_spoofed_case_tags() -> None:
    case = replace(
        _case("tag-spoof", expectation="transaction_committed"),
        tags=("complexity:high", "model-profile:forged-profile"),
    )

    report = score_module.evaluate_semantic_release(
        cases=(case,),
        annotations={case.case_id: _commit_annotation()},
        results=(_commit_result(case),),
        floors=FLOORS,
        _include_model_profiles=False,
        _allow_not_applicable_metrics=True,
    )

    assert report["passed"] is True
    assert report["case_outcomes"][0]["release_slices"] == {
        "complexity_band": "bounded",
        "evidence_format": "operator_prompt",
        "model_profile": STANDARD_PROFILE_ID,
    }


def test_release_rejects_annotation_complexity_that_disagrees_with_sealed_receipt() -> None:
    case = _case("complexity-mismatch", expectation="transaction_committed")
    annotation = _commit_annotation()
    annotation["complexity"]["actors"] += 1

    report = score_module.evaluate_semantic_release(
        cases=(case,),
        annotations={case.case_id: annotation},
        results=(_commit_result(case),),
        floors=FLOORS,
    )

    assert report["passed"] is False
    assert any(
        "annotated complexity does not match the sealed operating-envelope dimensions" in issue
        for issue in report["release_evidence_issues"]
    )


@pytest.mark.parametrize(
    ("damage", "expected_issue"),
    (
        ("missing_envelope", "lacks a sealed operating-envelope receipt"),
        ("unknown_profile", "claims an unknown model profile"),
        (
            "mismatched_dimension",
            "annotated complexity does not match the sealed operating-envelope dimensions",
        ),
    ),
)
def test_release_evidence_fails_closed_on_missing_unknown_or_mismatched_slices(
    damage: str,
    expected_issue: str,
) -> None:
    case = _case(f"release-{damage}", expectation="transaction_committed")
    result = _commit_result(case)
    snapshot = result.evidence["preconfirm_dry_run"]["semantic_snapshot"]
    if damage == "missing_envelope":
        snapshot.pop("operating_envelope")
    elif damage == "unknown_profile":
        result.evidence["model_profile"]["profile_id"] = "invented-profile"
    else:
        snapshot["operating_envelope"]["complexity"]["dimensions"]["actors"] += 1

    report = score_module.evaluate_semantic_release(
        cases=(case,),
        annotations={case.case_id: _commit_annotation()},
        results=(result,),
        floors=FLOORS,
        _allow_not_applicable_metrics=True,
    )

    assert report["passed"] is False
    assert any(expected_issue in issue for issue in report["release_evidence_issues"])


def test_release_required_slices_fail_closed_on_missing_coverage() -> None:
    case = _case("one-slice", expectation="transaction_committed")

    report = score_module.evaluate_semantic_release(
        cases=(case,),
        annotations={case.case_id: _commit_annotation()},
        results=(_commit_result(case),),
        floors=FLOORS,
        release_required_slices=release_slice_contract(),
        _allow_not_applicable_metrics=True,
    )

    assert report["passed"] is False
    assert {
        issue.split(" coverage:", 1)[0]
        for issue in report["release_coverage_issues"]
        if "lacks" in issue
    } == {
        "release evidence lacks complexity_band",
        "release evidence lacks evidence_format",
        "release evidence lacks model_profile",
    }
    assert {
        issue for issue in report["release_coverage_issues"]
        if "requires at least 4" in issue
    } == {
        "release evidence has 1 sample(s) for complexity_band `bounded`; requires at least 4",
        "release evidence has 1 sample(s) for evidence_format `operator_prompt`; requires at least 4",
        f"release evidence has 1 sample(s) for model_profile `{STANDARD_PROFILE_ID}`; requires at least 4",
    }


def test_semantic_release_rejects_a_softened_frozen_slice_sample_contract() -> None:
    case = _case("softened-samples", expectation="transaction_committed")
    floors = deepcopy(FLOORS)
    floors["release_slice_minimum_samples"]["complexity_band"]["bounded"] = 1

    report = score_module.evaluate_semantic_release(
        cases=(case,),
        annotations={case.case_id: _commit_annotation()},
        results=(_commit_result(case),),
        floors=floors,
        release_required_slices=release_slice_contract(),
        _include_model_profiles=False,
        _allow_not_applicable_metrics=True,
    )

    assert report["release_minimum_sample_contract_issues"] == [
        "release slice minimum samples must match the published contract"
    ]
    assert report["passed"] is False


def test_worst_complexity_slice_failure_cannot_hide_behind_aggregate() -> None:
    bounded = _case("bounded", expectation="transaction_committed")
    moderate = _case("moderate", expectation="transaction_committed")
    moderate_facts = {
        "state_object": "One permit decision",
        "first_path": moderate.prompt,
        "human_actors": [f"Actor {index}" for index in range(5)],
        "operational_constraints": [f"Boundary {index}" for index in range(3)],
    }
    moderate_result = _commit_result(moderate, facts=moderate_facts)
    moderate_result = replace(
        moderate_result,
        status="failed",
        quality=GreenfieldQualityVerdict(False, ("failed",), {}, {}, 0, ()),
    )
    moderate_annotation = _commit_annotation()
    moderate_annotation["complexity"] = deepcopy(
        moderate_result.evidence["preconfirm_dry_run"]["semantic_snapshot"]["operating_envelope"]
        ["complexity"]["dimensions"]
    )
    floors = {**FLOORS, "overall_case_success": 0.5, "worst_slice_success": 0.9}

    report = score_module.evaluate_semantic_release(
        cases=(bounded, moderate),
        annotations={
            bounded.case_id: _commit_annotation(),
            moderate.case_id: moderate_annotation,
        },
        results=(_commit_result(bounded), moderate_result),
        floors=floors,
        _include_model_profiles=False,
        _allow_not_applicable_metrics=True,
    )

    moderate_slice = next(
        row
        for row in report["slices"]
        if row["dimension"] == "complexity_band" and row["value"] == "moderate"
    )
    worst_check = next(
        row
        for row in report["acceptance_checks"]
        if row["name"] == "worst_slice_success"
    )
    assert report["overall_case_success"]["rate"] == 0.5
    assert moderate_slice["point_estimate"] == 0.0
    assert worst_check["status"] == "failed"
    assert report["passed"] is False


@pytest.mark.parametrize(
    ("dimension", "failed_value"),
    (
        ("source_family", "family-failed"),
        ("input_style", "pasted_brief"),
        ("evidence_format", "operator_prompt_with_edit_evidence"),
    ),
)
def test_frozen_domain_and_evidence_type_failures_cannot_hide_behind_aggregate(
    dimension: str,
    failed_value: str,
) -> None:
    passed_case = _case("slice-passed", expectation="transaction_committed")
    failed_case = _case("slice-failed", expectation="transaction_committed")
    if dimension == "source_family":
        passed_case = replace(
            passed_case,
            provenance=GreenfieldCaseProvenance(source_family="family-passed"),
        )
        failed_case = replace(
            failed_case,
            provenance=GreenfieldCaseProvenance(source_family=failed_value),
        )
    elif dimension == "input_style":
        passed_case = replace(passed_case, input_style="direct_request")
        failed_case = replace(failed_case, input_style=failed_value)
    else:
        failed_case = replace(
            failed_case,
            confirmed_intent_markdown="Keep the accepted receipt visible for review.",
        )

    passed_result = _commit_result(passed_case)
    failed_result = replace(
        _commit_result(failed_case),
        status="failed",
        quality=GreenfieldQualityVerdict(False, ("failed",), {}, {}, 0, ()),
    )
    annotations = {
        passed_case.case_id: _commit_annotation(prompt=passed_case.prompt),
        failed_case.case_id: _commit_annotation(prompt=failed_case.prompt),
    }
    for case, result in ((passed_case, passed_result), (failed_case, failed_result)):
        annotations[case.case_id]["complexity"] = deepcopy(
            result.evidence["preconfirm_dry_run"]["semantic_snapshot"]
            ["operating_envelope"]["complexity"]["dimensions"]
        )

    report = score_module.evaluate_semantic_release(
        cases=(passed_case, failed_case),
        annotations=annotations,
        results=(passed_result, failed_result),
        floors={**FLOORS, "overall_case_success": 0.5, "worst_slice_success": 0.9},
        _include_model_profiles=False,
        _allow_not_applicable_metrics=True,
    )

    failed_slice = next(
        row
        for row in report["slices"]
        if row["dimension"] == dimension and row["value"] == failed_value
    )
    assert report["overall_case_success"]["rate"] == 0.5
    assert failed_slice["point_estimate"] == 0.0
    assert report["worst_slice"]["point_estimate"] == 0.0
    assert report["passed"] is False


def _case(
    case_id: str,
    *,
    expectation: str,
    prompt: str = PROMPT,
) -> GreenfieldMatrixCase:
    return GreenfieldMatrixCase(
        case_id=case_id,
        name=case_id,
        prompt=prompt,
        required_terms=("fixture",),
        expectation=expectation,
        input_style="direct_request",
        input_style_declared=True,
        tags=("complexity:bounded", f"model-profile:{STANDARD_PROFILE_ID}"),
    )


def _link(
    quote: str,
    *,
    field: str = "human_actors",
    path: str = "/human_actors/0",
    projection_value: str | None = None,
    projection_occurrence: int = 0,
    relation_order: int = 0,
    relation_role: str = "",
) -> dict[str, object]:
    value = projection_value if projection_value is not None else quote
    encoded = quote.encode("utf-8")
    value_bytes = value.encode("utf-8")
    projection_start = 0
    for _ in range(projection_occurrence + 1):
        projection_start = value_bytes.index(encoded, projection_start)
        if _ < projection_occurrence:
            projection_start += len(encoded)
    return {
        "field": field,
        "path": path,
        "value_sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
        "projection_start_byte": projection_start,
        "projection_end_byte": projection_start + len(encoded),
        "relation_order": relation_order,
        "relation_role": relation_role,
    }


def _span(
    prompt: str,
    quote: str,
    *,
    edit_evidence: str = "",
    occurrence: int = 0,
) -> tuple[int, int, str]:
    prompt_bytes = combined_prompt_evidence_source(
        prompt=prompt,
        edit_evidence=edit_evidence,
    ).encode("utf-8")
    quote_bytes = quote.encode("utf-8")
    start = 0
    for _ in range(occurrence + 1):
        start = prompt_bytes.index(quote_bytes, start)
        if _ < occurrence:
            start += len(quote_bytes)
    return start, start + len(quote_bytes), hashlib.sha256(quote_bytes).hexdigest()


def _expected_atom(
    *,
    prompt: str = PROMPT,
    quote: str = "Operator",
    role: str = "scored",
    field: str = "human_actors",
    path: str = "/human_actors/0",
    projection_value: str | None = None,
    source_occurrence: int = 0,
    projection_occurrence: int = 0,
    relation_order: int = 1,
    relation_role: str = "actor_fact_quote",
    category: str = "actors",
) -> dict[str, object]:
    start, end, digest = _span(prompt, quote, occurrence=source_occurrence)
    return {
        "id": f"{field}-{relation_order}-{relation_role or 'fact'}",
        "category": category,
        "evaluation_role": role,
        "materiality": "material",
        "expected_custody": "accepted_fact",
        "expected_polarity": "affirmed",
        "source": {
            "source_id": "operator_evidence",
            "start_byte": start,
            "end_byte": end,
            "quote_sha256": digest,
        },
        "projection_links": [
            _link(
                quote,
                field=field,
                path=path,
                projection_value=projection_value,
                projection_occurrence=projection_occurrence,
                relation_order=relation_order,
                relation_role=relation_role,
            )
        ],
    }


def _actual_atom(
    *,
    prompt: str = PROMPT,
    quote: str = "Operator",
    field: str = "human_actors",
    path: str = "/human_actors/0",
    projection_value: str | None = None,
    source_occurrence: int = 0,
    projection_occurrence: int = 0,
    relation_order: int = 1,
    relation_role: str = "actor_fact_quote",
    category: str = "actors",
) -> dict[str, object]:
    start, end, digest = _span(prompt, quote, occurrence=source_occurrence)
    return {
        "atom_id": f"fixture-{field}-{relation_order}-{relation_role or 'fact'}",
        "categories": [category],
        "normalized_value": quote,
        "polarity": "affirmed",
        "custody_state": "accepted_fact",
        "entailment_relationship": "exact_source_span",
        "source_span_ids": ["fixture-span"],
        "source_span_refs": [
            {
                "span_id": "fixture-span",
                "classification": "product_claim",
                "text_sha256": digest,
                "source_start_byte": start,
                "source_end_byte": end,
            }
        ],
        "projection_links": [
            _link(
                quote,
                field=field,
                path=path,
                projection_value=projection_value,
                projection_occurrence=projection_occurrence,
                relation_order=relation_order,
                relation_role=relation_role,
            )
        ],
    }


def _baseline_expected_atoms(prompt: str) -> list[dict[str, object]]:
    return [
        _expected_atom(prompt=prompt),
        _expected_atom(
            prompt=prompt,
            quote="submits",
            role="reference_only",
            field="first_path",
            path="/first_path",
            projection_value=FIRST_PATH,
            relation_order=1,
            relation_role="action_verb_quote",
            category="actions",
        ),
        _expected_atom(
            prompt=prompt,
            quote="one signed permit",
            role="reference_only",
            field="first_path",
            path="/first_path",
            projection_value=FIRST_PATH,
            relation_order=1,
            relation_role="target_quote",
            category="actions",
        ),
        _expected_atom(
            prompt=prompt,
            quote="Permit Desk",
            role="reference_only",
            field="title",
            path="/title",
            relation_order=0,
            relation_role="",
            category="dependencies",
        ),
        _expected_atom(
            prompt=prompt,
            quote="accepted permit receipt",
            role="reference_only",
            field="first_path",
            path="/first_path",
            projection_value=FIRST_PATH,
            relation_order=1,
            relation_role="visible_result_quote",
            category="outputs",
        ),
    ]


def _baseline_actual_atoms(prompt: str) -> list[dict[str, object]]:
    return [
        _actual_atom(prompt=prompt),
        _actual_atom(
            prompt=prompt,
            quote="submits",
            field="first_path",
            path="/first_path",
            projection_value=FIRST_PATH,
            relation_order=1,
            relation_role="action_verb_quote",
            category="actions",
        ),
        _actual_atom(
            prompt=prompt,
            quote="one signed permit",
            field="first_path",
            path="/first_path",
            projection_value=FIRST_PATH,
            relation_order=1,
            relation_role="target_quote",
            category="actions",
        ),
        _actual_atom(
            prompt=prompt,
            quote="Permit Desk",
            field="title",
            path="/title",
            relation_order=0,
            relation_role="",
            category="dependencies",
        ),
        _actual_atom(
            prompt=prompt,
            quote="accepted permit receipt",
            field="first_path",
            path="/first_path",
            projection_value=FIRST_PATH,
            relation_order=1,
            relation_role="visible_result_quote",
            category="outputs",
        ),
    ]


def _relation_annotation(prompt: str) -> dict[str, object]:
    source_start, source_end, event_sha = _span(prompt, FIRST_PATH)
    return {
        "version": RELATION_FIDELITY_ANNOTATION_VERSION,
        "first_path_events": [
            {
                "order": 1,
                "source_start_byte": source_start,
                "source_end_byte": source_end,
                "event_start_byte": 0,
                "event_end_byte": len(FIRST_PATH.encode("utf-8")),
                "event_sha256": event_sha,
                "actor_kind": "human",
                "actor_fact_path": "/human_actors/0",
                "actor_fact_sha256": hashlib.sha256(b"Operator").hexdigest(),
                "product_owner_path": "",
                "product_owner_sha256": "",
                "action_verb_sha256": hashlib.sha256(b"submits").hexdigest(),
                "target_sha256": hashlib.sha256(b"one signed permit").hexdigest(),
                "visible_result_sha256": hashlib.sha256(
                    b"accepted permit receipt"
                ).hexdigest(),
            }
        ],
        "context_relations": [],
        "component_responsibility_relations": [
            {
                "responsibility_path": "/first_path",
                "responsibility_sha256": hashlib.sha256(
                    b"accepted permit receipt"
                ).hexdigest(),
                "product_owner_path": "/title",
                "product_owner_sha256": hashlib.sha256(b"Permit Desk").hexdigest(),
                "first_path_event_order": 1,
                "responsibility_source": "terminal_visible_result",
            }
        ],
    }


def _commit_annotation(*, prompt: str = PROMPT) -> dict[str, object]:
    return {
        "expected_outcome": "commit",
        "expected_clarification": None,
        "complexity": _complexity(prompt),
        "atoms": _baseline_expected_atoms(prompt),
        "relation_fidelity": _relation_annotation(prompt),
    }


def _clarification_annotation() -> dict[str, object]:
    return {
        "expected_outcome": "clarify",
        "expected_clarification": {
            "field": "first_path",
            "question": "What is the first complete task and visible result?",
        },
        "complexity": _complexity(PROMPT),
        "atoms": [],
        "relation_fidelity": None,
    }


def _commit_result(
    case: GreenfieldMatrixCase,
    *,
    atoms: list[dict[str, object]] | None = None,
    facts: dict[str, object] | None = None,
) -> GreenfieldMatrixResult:
    ledger = deepcopy(
        _baseline_actual_atoms(case.prompt) if atoms is None else atoms
    )
    sealed_facts = facts or {
        "title": "Permit Desk",
        "first_path": FIRST_PATH,
        "human_actors": ["Operator"],
    }
    operating_envelope = _operating_envelope(case, facts=sealed_facts)
    semantics = _authored_semantics(case, facts=sealed_facts)
    return GreenfieldMatrixResult(
        name=case.name,
        status="passed",
        create_seconds=1.0,
        counts=GreenfieldArtifactCounts(),
        quality=GreenfieldQualityVerdict(True, (), {}, {}, 10, ()),
        evidence={
            "case": case_evidence(case),
            "preconfirm_dry_run": {
                "semantic_snapshot": {
                    "facts": {
                        **sealed_facts,
                    },
                    "atomic_facts": ledger,
                    "atomic_custody_sha256": atomic_fact_ledger_hash(ledger),
                    "operating_envelope": operating_envelope,
                    "authored_semantics": semantics,
                    "authored_relation_set_sha256": authored_relation_set_sha256(
                        semantics["first_path_relations"],
                        semantics["component_responsibility_relations"],
                        first_path_context_relations=semantics[
                            "first_path_context_relations"
                        ],
                    ),
                },
            },
            "model_profile": _model_result_evidence(STANDARD_PROFILE_ID),
        },
    )


def _authored_semantics(
    case: GreenfieldMatrixCase,
    *,
    facts: dict[str, object],
) -> dict[str, object]:
    first_path = str(facts.get("first_path") or "")
    actor = str(next(iter(facts.get("human_actors", ())), ""))
    title = str(facts.get("title") or "")
    source_start, source_end, _digest = _span(
        case.prompt,
        first_path,
        edit_evidence=str(case.confirmed_intent_markdown or ""),
    )
    visible_result = (
        "accepted permit receipt"
        if "accepted permit receipt" in first_path
        else first_path
    )
    relations = [
        {
            "order": 1,
            "source_start_byte": source_start,
            "source_end_byte": source_end,
            "event_start_byte": 0,
            "event_end_byte": len(first_path.encode("utf-8")),
            "actor_kind": "human",
            "actor_fact_path": "/human_actors/0",
            "actor_fact_quote": actor,
            "owner_system_path": "",
            "owner_system_quote": "",
            "event_quote": first_path,
            "action_verb_quote": "submits",
            "target_quote": "one signed permit",
            "visible_result_quote": visible_result,
        }
    ]
    components = [
        {
            "responsibility_path": "/first_path",
            "responsibility_quote": visible_result,
            "owner_system_path": "/title",
            "owner_system_quote": title,
            "first_path_event_order": 1,
            "responsibility_source": "terminal_visible_result",
        }
    ]
    return {
        "version": AUTHORED_SEMANTICS_VERSION,
        "first_path_relations": relations,
        "first_path_context_relations": [],
        "component_responsibility_relations": components,
    }


def _refresh_hash(result: GreenfieldMatrixResult) -> None:
    snapshot = result.evidence["preconfirm_dry_run"]["semantic_snapshot"]
    snapshot["atomic_custody_sha256"] = atomic_fact_ledger_hash(snapshot["atomic_facts"])


def _clarification_result(case: GreenfieldMatrixCase) -> GreenfieldMatrixResult:
    return GreenfieldMatrixResult(
        name=case.name,
        status="passed",
        create_seconds=0.1,
        counts=GreenfieldArtifactCounts(),
        quality=GreenfieldQualityVerdict(True, (), {}, {}, 10, ()),
        evidence={
            "case": case_evidence(case),
            "clarification": {
                "mode": "clarification_required",
                "question": "What is the first complete task and visible result?",
                "required_fields": ["first_path"],
            },
            "model_profile": _model_result_evidence(STANDARD_PROFILE_ID),
        },
    )


def _complexity(prompt: str) -> dict[str, int]:
    evidence = combined_prompt_evidence_source(prompt=prompt, edit_evidence="")
    return {
        "evidence_bytes": len(evidence.encode("utf-8")),
        "documents": 1,
        "actors": 1,
        "state_objects": 0,
        "paths": 1,
        "external_systems": 0,
        "internal_systems": 0,
        "contradictions": 0,
        "ambiguities": 0,
        "safety_boundaries": 0,
        "success_metrics": 0,
        "evidence_requirements": 0,
        "component_responsibilities": 0,
        "assumptions": 0,
        "non_goals": 0,
    }


def _operating_envelope(
    case: GreenfieldMatrixCase,
    *,
    facts: dict[str, object],
) -> dict[str, object]:
    profile = get_greenfield_model_profile(STANDARD_PROFILE_ID)
    edit_evidence = str(case.confirmed_intent_markdown or "")
    evidence = combined_prompt_evidence_source(
        prompt=case.prompt,
        edit_evidence=edit_evidence,
    )
    return greenfield_operating_envelope_receipt(
        facts=facts,
        source_format=(
            "operator_prompt_with_edit_evidence"
            if edit_evidence
            else "operator_prompt"
        ),
        source_size_bytes=len(evidence.encode("utf-8")),
        source_document_count=2 if edit_evidence else 1,
        model_authoring={
            "profile_id": profile.profile_id,
            "provider": profile.provider,
            "model": profile.model,
            "reasoning_effort": profile.reasoning_effort,
            "effective_timeout_seconds": profile.model_timeout_seconds,
            "authoring_tier": profile.repair_tier,
        },
    )


def _model_result_evidence(profile_id: str) -> dict[str, object]:
    profile = get_greenfield_model_profile(profile_id)
    return {
        "profile_id": profile_id,
        "status": "passed",
        "issues": [],
        "observed": {
            "profile_id": profile_id,
            "provider": profile.provider,
            "model": profile.model,
            "reasoning_effort": profile.reasoning_effort,
            "effective_timeout_seconds": profile.model_timeout_seconds,
            "authoring_tier": profile.repair_tier,
        },
    }


def _rich_relation_bundle(
    case_id: str,
) -> tuple[GreenfieldMatrixCase, dict[str, object], GreenfieldMatrixResult]:
    event_specs = (
        (
            "Reviewer submits one permit",
            "human",
            "Reviewer",
            "/human_actors/0",
            "",
            "submits",
            "one permit",
            "",
        ),
        (
            "Registry API and Archive API supply the prior state",
            "external_system",
            "Registry API",
            "/external_systems/0",
            "",
            "supply",
            "prior state",
            "",
        ),
        (
            "Record Engine and Backup Engine record the approved state and show the accepted receipt",
            "product",
            "Record Engine",
            "/internal_systems/0",
            "Record Engine",
            "record",
            "approved state",
            "accepted receipt",
        ),
    )
    first_path = "; ".join(spec[0] for spec in event_specs)
    prompt = (
        f"Permit Relay supports this path: {first_path}. "
        "Retain the accepted receipt. Record the accepted receipt."
    )
    case = _case(case_id, expectation="transaction_committed", prompt=prompt)
    facts: dict[str, object] = {
        "title": "Permit Relay",
        "product_story": "Permit Relay preserves one reviewed decision.",
        "state_object": "prior state",
        "first_path": first_path,
        "proof_boundary": "One accepted receipt is visible.",
        "human_actors": ["Reviewer"],
        "external_systems": ["Registry API", "Archive API"],
        "internal_systems": ["Record Engine", "Backup Engine"],
        "operational_constraints": ["Retain the accepted receipt"],
        "component_responsibilities": ["Record the accepted receipt"],
    }
    atom_specs = (
        ("Reviewer", "scored", "human_actors", "/human_actors/0", None, 1, "actor_fact_quote", "actors"),
        ("Registry API", "reference_only", "external_systems", "/external_systems/0", None, 2, "actor_fact_quote", "dependencies"),
        ("Archive API", "reference_only", "external_systems", "/external_systems/1", None, 0, "", "dependencies"),
        ("Record Engine", "reference_only", "internal_systems", "/internal_systems/0", None, 3, "actor_fact_quote", "dependencies"),
        ("Backup Engine", "reference_only", "internal_systems", "/internal_systems/1", None, 0, "", "dependencies"),
        ("prior state", "reference_only", "state_object", "/state_object", None, 0, "", "states"),
        ("Retain the accepted receipt", "reference_only", "operational_constraints", "/operational_constraints/0", None, 0, "", "constraints"),
        ("Record the accepted receipt", "reference_only", "component_responsibilities", "/component_responsibilities/0", None, 0, "", "actions"),
        ("submits", "reference_only", "first_path", "/first_path", first_path, 1, "action_verb_quote", "actions"),
        ("one permit", "reference_only", "first_path", "/first_path", first_path, 1, "target_quote", "actions"),
        ("supply", "reference_only", "first_path", "/first_path", first_path, 2, "action_verb_quote", "actions"),
        ("prior state", "reference_only", "first_path", "/first_path", first_path, 2, "target_quote", "actions"),
        ("record", "reference_only", "first_path", "/first_path", first_path, 3, "action_verb_quote", "actions"),
        ("approved state", "reference_only", "first_path", "/first_path", first_path, 3, "target_quote", "actions"),
        ("accepted receipt", "reference_only", "first_path", "/first_path", first_path, 3, "visible_result_quote", "outputs"),
    )
    expected_atoms = [
        _expected_atom(
            prompt=prompt,
            quote=quote,
            role=role,
            field=field,
            path=path,
            projection_value=projection_value,
            relation_order=order,
            relation_role=relation_role,
            category=category,
        )
        for quote, role, field, path, projection_value, order, relation_role, category in atom_specs
    ]
    actual_atoms = [
        _actual_atom(
            prompt=prompt,
            quote=quote,
            field=field,
            path=path,
            projection_value=projection_value,
            relation_order=order,
            relation_role=relation_role,
            category=category,
        )
        for quote, _role, field, path, projection_value, order, relation_role, category in atom_specs
    ]
    semantic_events: list[dict[str, object]] = []
    expected_events: list[dict[str, object]] = []
    path_bytes = first_path.encode("utf-8")
    for order, spec in enumerate(event_specs, start=1):
        event, actor_kind, actor, actor_path, owner, action, target, visible = spec
        source_start, source_end, event_sha = _span(prompt, event)
        event_start = path_bytes.index(event.encode("utf-8"))
        event_end = event_start + len(event.encode("utf-8"))
        owner_path = actor_path if actor_kind == "product" else ""
        semantic_events.append(
            {
                "order": order,
                "source_start_byte": source_start,
                "source_end_byte": source_end,
                "event_start_byte": event_start,
                "event_end_byte": event_end,
                "actor_kind": actor_kind,
                "actor_fact_path": actor_path,
                "actor_fact_quote": actor,
                "owner_system_path": owner_path,
                "owner_system_quote": owner,
                "event_quote": event,
                "action_verb_quote": action,
                "target_quote": target,
                "visible_result_quote": visible,
            }
        )
        expected_events.append(
            {
                "order": order,
                "source_start_byte": source_start,
                "source_end_byte": source_end,
                "event_start_byte": event_start,
                "event_end_byte": event_end,
                "event_sha256": event_sha,
                "actor_kind": actor_kind,
                "actor_fact_path": actor_path,
                "actor_fact_sha256": _sha(actor),
                "product_owner_path": owner_path,
                "product_owner_sha256": _sha(owner) if owner else "",
                "action_verb_sha256": _sha(action),
                "target_sha256": _sha(target) if target else "",
                "visible_result_sha256": _sha(visible) if visible else "",
            }
        )
    context_specs = (
        ("state_object", "/state_object", "prior state", 2),
        ("external_system", "/external_systems/0", "Registry API", 2),
        ("external_system", "/external_systems/1", "Archive API", 2),
        ("operational_constraint", "/operational_constraints/0", "Retain the accepted receipt", 0),
    )
    semantic_contexts: list[dict[str, object]] = []
    expected_contexts: list[dict[str, object]] = []
    for kind, path, quote, order in context_specs:
        start, end, _digest = _span(prompt, quote)
        semantic_contexts.append(
            {
                "context_kind": kind,
                "fact_path": path,
                "fact_quote": quote,
                "source_start_byte": start,
                "source_end_byte": end,
                "first_path_event_order": order,
            }
        )
        expected_contexts.append(
            {
                "context_kind": kind,
                "fact_path": path,
                "fact_sha256": _sha(quote),
                "source_start_byte": start,
                "source_end_byte": end,
                "first_path_event_order": order,
            }
        )
    semantics = {
        "version": AUTHORED_SEMANTICS_VERSION,
        "first_path_relations": semantic_events,
        "first_path_context_relations": semantic_contexts,
        "component_responsibility_relations": [
            {
                "responsibility_path": "/component_responsibilities/0",
                "responsibility_quote": "Record the accepted receipt",
                "owner_system_path": "/internal_systems/0",
                "owner_system_quote": "Record Engine",
                "first_path_event_order": 3,
                "responsibility_source": "accepted_fact",
            }
        ],
    }
    result = _commit_result(case, atoms=actual_atoms, facts=facts)
    snapshot = result.evidence["preconfirm_dry_run"]["semantic_snapshot"]
    snapshot["authored_semantics"] = semantics
    _refresh_relation_hash(result)
    annotation = {
        "expected_outcome": "commit",
        "expected_clarification": None,
        "complexity": deepcopy(snapshot["operating_envelope"]["complexity"]["dimensions"]),
        "atoms": expected_atoms,
        "relation_fidelity": {
            "version": RELATION_FIDELITY_ANNOTATION_VERSION,
            "first_path_events": expected_events,
            "context_relations": expected_contexts,
            "component_responsibility_relations": [
                {
                    "responsibility_path": "/component_responsibilities/0",
                    "responsibility_sha256": _sha("Record the accepted receipt"),
                    "product_owner_path": "/internal_systems/0",
                    "product_owner_sha256": _sha("Record Engine"),
                    "first_path_event_order": 3,
                    "responsibility_source": "accepted_fact",
                }
            ],
        },
    }
    return case, annotation, result


def _refresh_relation_hash(result: GreenfieldMatrixResult) -> None:
    snapshot = result.evidence["preconfirm_dry_run"]["semantic_snapshot"]
    semantics = snapshot["authored_semantics"]
    snapshot["authored_relation_set_sha256"] = authored_relation_set_sha256(
        semantics["first_path_relations"],
        semantics["component_responsibility_relations"],
        first_path_context_relations=semantics["first_path_context_relations"],
    )


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _repeated_relation_evidence() -> tuple[GreenfieldMatrixCase, dict[str, object], dict[str, object]]:
    event = "Operator records one receipt"
    first_path = f"{event}; {event}"
    prompt = f"Repeat Desk supports this path: {first_path}."
    case = _case("repeat-relations", expectation="transaction_committed", prompt=prompt)
    source_ranges = [_span(prompt, event, occurrence=index)[:2] for index in range(2)]
    projection_starts = (0, len(f"{event}; ".encode("utf-8")))
    semantic_events = []
    expected_events = []
    for index, ((source_start, source_end), projection_start) in enumerate(
        zip(source_ranges, projection_starts, strict=True),
        start=1,
    ):
        visible = "one receipt" if index == 2 else ""
        semantic_events.append(
            {
                "order": index,
                "source_start_byte": source_start,
                "source_end_byte": source_end,
                "event_start_byte": projection_start,
                "event_end_byte": projection_start + len(event.encode("utf-8")),
                "actor_kind": "human",
                "actor_fact_path": "/human_actors/0",
                "actor_fact_quote": "Operator",
                "owner_system_path": "",
                "owner_system_quote": "",
                "event_quote": event,
                "action_verb_quote": "records",
                "target_quote": "one receipt",
                "visible_result_quote": visible,
            }
        )
        expected_events.append(
            {
                "order": index,
                "source_start_byte": source_start,
                "source_end_byte": source_end,
                "event_start_byte": projection_start,
                "event_end_byte": projection_start + len(event.encode("utf-8")),
                "event_sha256": _sha(event),
                "actor_kind": "human",
                "actor_fact_path": "/human_actors/0",
                "actor_fact_sha256": _sha("Operator"),
                "product_owner_path": "",
                "product_owner_sha256": "",
                "action_verb_sha256": _sha("records"),
                "target_sha256": _sha("one receipt"),
                "visible_result_sha256": _sha(visible) if visible else "",
            }
        )
    semantics = {
        "version": AUTHORED_SEMANTICS_VERSION,
        "first_path_relations": semantic_events,
        "first_path_context_relations": [],
        "component_responsibility_relations": [
            {
                "responsibility_path": "/first_path",
                "responsibility_quote": "one receipt",
                "owner_system_path": "/title",
                "owner_system_quote": "Repeat Desk",
                "first_path_event_order": 2,
                "responsibility_source": "terminal_visible_result",
            }
        ],
    }
    snapshot = {
        "facts": {
            "title": "Repeat Desk",
            "first_path": first_path,
            "human_actors": ["Operator"],
        },
        "authored_semantics": semantics,
        "authored_relation_set_sha256": authored_relation_set_sha256(
            semantic_events,
            semantics["component_responsibility_relations"],
            first_path_context_relations=[],
        ),
    }
    atoms = [
        _expected_atom(prompt=prompt, quote="Operator", relation_order=1),
        _expected_atom(
            prompt=prompt,
            quote="Operator",
            role="reference_only",
            source_occurrence=1,
            relation_order=2,
        ),
        *[
            _expected_atom(
                prompt=prompt,
                quote=quote,
                role="reference_only",
                field="first_path",
                path="/first_path",
                projection_value=first_path,
                source_occurrence=occurrence,
                projection_occurrence=occurrence,
                relation_order=order,
                relation_role=role,
                category="actions",
            )
            for order, occurrence in ((1, 0), (2, 1))
            for quote, role in (("records", "action_verb_quote"), ("one receipt", "target_quote"))
        ],
        _expected_atom(
            prompt=prompt,
            quote="one receipt",
            role="reference_only",
            field="first_path",
            path="/first_path",
            projection_value=first_path,
            source_occurrence=1,
            projection_occurrence=1,
            relation_order=2,
            relation_role="visible_result_quote",
            category="outputs",
        ),
        _expected_atom(
            prompt=prompt,
            quote="Repeat Desk",
            role="reference_only",
            field="title",
            path="/title",
            relation_order=0,
            relation_role="",
            category="dependencies",
        ),
    ]
    annotation = {
        "atoms": atoms,
        "relation_fidelity": {
            "version": RELATION_FIDELITY_ANNOTATION_VERSION,
            "first_path_events": expected_events,
            "context_relations": [],
            "component_responsibility_relations": [
                {
                    "responsibility_path": "/first_path",
                    "responsibility_sha256": _sha("one receipt"),
                    "product_owner_path": "/title",
                    "product_owner_sha256": _sha("Repeat Desk"),
                    "first_path_event_order": 2,
                    "responsibility_source": "terminal_visible_result",
                }
            ],
        },
    }
    return case, annotation, snapshot
