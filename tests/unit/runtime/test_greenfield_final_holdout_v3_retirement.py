from __future__ import annotations

import hashlib
import json
from pathlib import Path


_1BA7_RETIRED_HOLDOUT_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures/greenfield-release-corpus/retired-1ba7-v3-final-holdout-regressions.v1.json"
)
_1BA7_RETIRED_HOLDOUT = json.loads(
    _1BA7_RETIRED_HOLDOUT_PATH.read_text(encoding="utf-8")
)
_1BA7_RETIRED_HOLDOUT_CASES = tuple(_1BA7_RETIRED_HOLDOUT["cases"])
_1BA7_RETIRED_HOLDOUT_CASES_BY_ID = {
    str(case["case_id"]): case for case in _1BA7_RETIRED_HOLDOUT_CASES
}
_1BA7_RETIRED_HOLDOUT_ANNOTATIONS = tuple(_1BA7_RETIRED_HOLDOUT["annotations"])
_1BA7_RETIRED_HOLDOUT_ANNOTATIONS_BY_CASE_ID = {
    str(annotation["case_id"]): annotation
    for annotation in _1BA7_RETIRED_HOLDOUT_ANNOTATIONS
}
_1BA7_CLARIFICATION_CASES = tuple(
    case
    for case in _1BA7_RETIRED_HOLDOUT_CASES
    if case["expectation"] == "clarification_required"
)
_1BA7_TRANSACTION_CASES = tuple(
    case
    for case in _1BA7_RETIRED_HOLDOUT_CASES
    if case["expectation"] == "transaction_committed"
)


def _sealed_source_bytes() -> bytes:
    provenance = _1BA7_RETIRED_HOLDOUT["provenance"]
    source_document = {
        "version": provenance["source_version"],
        "claim_class": _1BA7_RETIRED_HOLDOUT["claim_class"],
        "authoring_method": provenance["authoring_method"],
        "source_policy": provenance["source_policy_at_authoring"],
        "cases": list(_1BA7_RETIRED_HOLDOUT_CASES),
        "annotations": list(_1BA7_RETIRED_HOLDOUT_ANNOTATIONS),
    }
    return (json.dumps(source_document, indent=2, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


def test_v3_failed_holdout_is_disclosed_with_terminal_custody_metadata() -> None:
    assert (
        _1BA7_RETIRED_HOLDOUT["version"]
        == "odylith.greenfield.retired-holdout-regression.v1"
    )
    assert _1BA7_RETIRED_HOLDOUT["disclosed"] is True
    assert _1BA7_RETIRED_HOLDOUT["retired_from"] == {
        "product_revision": "1ba7b4c0385ed36981c5d163439a49f3be703661",
        "holdout_sha256": "082a92fe9aea18a5ea2b88eefa5aae7853277119b8aa600251c24a4a4bfc45d9",
        "evaluation_manifest_sha256": (
            "40538d4100d9b2b8685c81c6680046ab179f971909db053c975841c66d8d2cb5"
        ),
        "result_sha256": "180437fd4000e8c46eefe19b1e44c0fce14fb53e6666bf18838a1894d7a2a988",
        "run_ledger_sha256": (
            "f55dae956631f50474c2b8c6e99a91e8719a3998fbe22965934c7f8b8e40a09f"
        ),
        "evaluated_on": "2026-08-16",
    }
    assert _1BA7_RETIRED_HOLDOUT["terminal_status"] == "failed"
    assert _1BA7_RETIRED_HOLDOUT["release_case_passed_count"] == 2
    assert _1BA7_RETIRED_HOLDOUT["release_case_failed_count"] == 22
    assert "tracked regression evidence" in _1BA7_RETIRED_HOLDOUT[
        "retirement_reason"
    ]


def test_v3_retired_corpus_round_trips_to_the_sealed_source_hash() -> None:
    coverage = _1BA7_RETIRED_HOLDOUT["coverage"]

    assert coverage["case_count"] == len(_1BA7_RETIRED_HOLDOUT_CASES) == 24
    assert (
        coverage["annotation_count"]
        == len(_1BA7_RETIRED_HOLDOUT_ANNOTATIONS)
        == 24
    )
    assert len(_1BA7_CLARIFICATION_CASES) == 7
    assert len(_1BA7_TRANSACTION_CASES) == 17
    assert hashlib.sha256(_sealed_source_bytes()).hexdigest() == (
        _1BA7_RETIRED_HOLDOUT["retired_from"]["holdout_sha256"]
    )


def test_v3_retired_cases_and_annotations_have_one_to_one_prompt_custody() -> None:
    assert len(_1BA7_RETIRED_HOLDOUT_CASES_BY_ID) == 24
    assert len(_1BA7_RETIRED_HOLDOUT_ANNOTATIONS_BY_CASE_ID) == 24
    assert _1BA7_RETIRED_HOLDOUT_CASES_BY_ID.keys() == (
        _1BA7_RETIRED_HOLDOUT_ANNOTATIONS_BY_CASE_ID.keys()
    )

    for case_id, case in _1BA7_RETIRED_HOLDOUT_CASES_BY_ID.items():
        annotation = _1BA7_RETIRED_HOLDOUT_ANNOTATIONS_BY_CASE_ID[case_id]
        prompt_sha256 = hashlib.sha256(str(case["prompt"]).encode("utf-8")).hexdigest()
        assert annotation["prompt_sha256"] == prompt_sha256
