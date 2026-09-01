from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import sys

import pytest

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT
from tests.unit.install import test_greenfield_semantic_release_score as support


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import greenfield_semantic_release_score as score_module
from greenfield_matrix_corpus_provenance import GreenfieldCaseProvenance
from greenfield_matrix_metamorphic import evaluate_metamorphic_outputs
from greenfield_matrix_types import GreenfieldMatrixResult
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase


TRANSACTION_HASH = "c" * 64
SOURCE_HASH = "d" * 64


@pytest.fixture(autouse=True)
def _use_structural_ledger_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(score_module, "require_atomic_fact_ledger", lambda *_args, **_kwargs: None)


def test_paraphrased_sources_with_the_same_canonical_ids_and_graph_pass() -> None:
    cases, annotations, results = _equivalent_pair()

    report = _score(cases=cases, annotations=annotations, results=results)
    digests = report["normalized_semantic_digests"]
    evaluation = evaluate_metamorphic_outputs(
        cases=cases,
        results=tuple(_completed(result) for result in results),
        semantic_digests=digests,
    )

    assert report["passed"] is True
    assert len(set(digests.values())) == 1
    assert evaluation["status"] == "passed"


def test_same_topology_with_different_canonical_ids_fails() -> None:
    cases, annotations, results = _equivalent_pair()
    changed = deepcopy(annotations)
    for atom in changed[cases[1].case_id]["atoms"]:
        atom["id"] = f"different:{atom['id']}"

    report = _score(cases=cases, annotations=changed, results=results)
    digests = report["normalized_semantic_digests"]
    evaluation = evaluate_metamorphic_outputs(
        cases=cases,
        results=tuple(_completed(result) for result in results),
        semantic_digests=digests,
    )

    assert report["passed"] is True
    assert len(set(digests.values())) == 2
    assert evaluation["status"] == "failed"
    assert any("canonical semantic identities" in issue for issue in evaluation["issues"])


def test_relation_mismatch_emits_no_digest_and_fails_closed() -> None:
    cases, annotations, results = _equivalent_pair()
    damaged = deepcopy(results[1])
    snapshot = damaged.evidence["preconfirm_dry_run"]["semantic_snapshot"]
    snapshot["authored_semantics"]["first_path_relations"][0]["action_verb_quote"] = "reviews"
    support._refresh_relation_hash(damaged)

    report = _score(cases=cases, annotations=annotations, results=(results[0], damaged))
    evaluation = evaluate_metamorphic_outputs(
        cases=cases,
        results=tuple(_completed(result) for result in (results[0], damaged)),
        semantic_digests=report["normalized_semantic_digests"],
    )

    assert cases[1].case_id not in report["normalized_semantic_digests"]
    assert evaluation["status"] == "failed"
    assert any("lacks a verified normalized semantic digest" in issue for issue in evaluation["issues"])


def _equivalent_pair() -> tuple[
    tuple[GreenfieldMatrixCase, GreenfieldMatrixCase],
    dict[str, dict[str, object]],
    tuple[GreenfieldMatrixResult, GreenfieldMatrixResult],
]:
    provenance = GreenfieldCaseProvenance(
        source_id="permit-equivalence",
        source_artifact_sha256=SOURCE_HASH,
    )
    paraphrase = support.PROMPT + " Put another way, the operator completes that same permit review."
    cases = (
        replace(
            support._case("permit-direct", expectation="transaction_committed"),
            provenance=provenance,
            metamorphic_group="permit-equivalence",
            metamorphic_transform="direct",
        ),
        replace(
            support._case("permit-paraphrase", expectation="transaction_committed", prompt=paraphrase),
            provenance=provenance,
            metamorphic_group="permit-equivalence",
            metamorphic_transform="paraphrase",
        ),
    )
    annotations = {
        cases[0].case_id: support._commit_annotation(prompt=cases[0].prompt),
        cases[1].case_id: support._commit_annotation(prompt=cases[1].prompt),
    }
    return cases, annotations, tuple(support._commit_result(case) for case in cases)


def _score(
    *,
    cases: tuple[GreenfieldMatrixCase, GreenfieldMatrixCase],
    annotations: dict[str, dict[str, object]],
    results: tuple[GreenfieldMatrixResult, GreenfieldMatrixResult],
) -> dict[str, object]:
    return score_module.evaluate_semantic_release(
        cases=cases,
        annotations=annotations,
        results=results,
        floors=support.FLOORS,
        _include_model_profiles=False,
        _allow_not_applicable_metrics=True,
    )


def _completed(result: GreenfieldMatrixResult) -> GreenfieldMatrixResult:
    evidence = deepcopy(result.evidence)
    evidence["preconfirm_dry_run"].update(
        {"status": "compiled", "transaction_hash": TRANSACTION_HASH}
    )
    return replace(
        result,
        evidence=evidence,
        commit_manifest_summary={
            "write_transaction": {
                "commit_only": True,
                "prewrite_clean_before_commit": True,
                "product_create_transaction_hash": TRANSACTION_HASH,
            },
            "product_create_transaction": {"transaction_hash": TRANSACTION_HASH},
        },
    )
