from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization import (
    GreenfieldClarificationRequired,
)
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization import (
    materialize_prompt_intent_hypothesis,
)
from odylith.runtime.domain_intelligence.greenfield_material_clarification import has_explicit_visible_result


_CORPUS_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures/greenfield-release-corpus/retired-1ba7-v3-final-holdout-regressions.v1.json"
)
_CORPUS = json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))
_CASES = {str(case["case_id"]): case for case in _CORPUS["cases"]}
_ANNOTATIONS = {str(row["case_id"]): row for row in _CORPUS["annotations"]}
_CLARIFICATION_IDS = (
    "gfhi-005",
    "gfhi-006",
    "gfhi-013",
    "gfhi-014",
    "gfhi-020",
    "gfhi-022",
    "gfhi-024",
)
_COMMIT_IDS = ("gfhi-010", "gfhi-019", "gfhi-023")
_MATERIAL_FACT_TERMS = {
    "gfhi-010": ("digest editor", "review seal", "local queue history", "glossary index"),
    "gfhi-019": ("reviewer", "ready marker", "local proposal list"),
    "gfhi-023": ("keeper", "completion marker", "repo checkpoint ledger"),
}
_PRESENTATION_ONLY_TERMS = {
    "gfhi-010": (),
    "gfhi-019": ("color or symbol scheme",),
    "gfhi-023": ("wording or icon scheme",),
}


@pytest.mark.parametrize("case_id", _CLARIFICATION_IDS)
def test_v3_material_gaps_ask_once_before_writes_or_subprocesses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case_id: str,
) -> None:
    calls: list[object] = []

    def unexpected_subprocess(*args: object, **kwargs: object) -> None:
        calls.append((args, kwargs))
        raise AssertionError("clarification must precede subprocess work")

    monkeypatch.setattr(subprocess, "run", unexpected_subprocess)
    monkeypatch.setattr(subprocess, "Popen", unexpected_subprocess)
    case = _CASES[case_id]

    with pytest.raises(GreenfieldClarificationRequired) as error:
        materialize_prompt_intent_hypothesis(
            prompt=str(case["prompt"]),
            repo_root=tmp_path,
            fallback_title=str(case["name"]),
        )

    assert error.value.required_fields == tuple(_ANNOTATIONS[case_id]["expected_question_fields"])
    assert error.value.question.count("?") == 1
    assert calls == []
    assert not (tmp_path / ".odylith/runtime/greenfield").exists()


@pytest.mark.parametrize("case_id", _COMMIT_IDS)
def test_v3_nonmaterial_or_resolved_evidence_materializes_without_leakage(
    tmp_path: Path,
    case_id: str,
) -> None:
    case = _CASES[case_id]
    intent = materialize_prompt_intent_hypothesis(
        prompt=str(case["prompt"]),
        repo_root=tmp_path,
        fallback_title=str(case["name"]),
    )

    product_facts = {
        key: value
        for key, value in intent.items()
        if key not in {"product_intent_authority", "prompt"}
    }
    rendered = json.dumps(product_facts, sort_keys=True).casefold()
    assert intent["product_intent_authority"]["materiality_status"] == "passed"
    assert all(term in rendered for term in _MATERIAL_FACT_TERMS[case_id])
    assert all(term not in rendered for term in _PRESENTATION_ONLY_TERMS[case_id])
    assert (tmp_path / ".odylith/runtime/greenfield/candidate-intent.json").is_file()


def test_v3_relation_conflict_detection_keeps_domain_outcomes_nonmaterial(tmp_path: Path) -> None:
    prompt = (
        "Build a Quantum Networking Lab Management App where lab operators reserve a calibrated entanglement "
        "link for an experiment, confirm device and calibration availability, record either a conflict or an "
        "accepted reservation, and see an auditable ready-to-run reservation."
    )

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Quantum Networking Lab Management App",
    )

    assert "record either a conflict or an accepted reservation" in str(intent["first_path"]).casefold()


def test_product_output_sentence_supplies_a_visible_result() -> None:
    assert has_explicit_visible_result("The product generates an intake receipt.")


def test_observable_verification_status_supplies_a_visible_result() -> None:
    assert has_explicit_visible_result(
        "A program lead registers a readiness dossier, selects a review disposition, "
        "and verifies a publication status."
    )
    assert not has_explicit_visible_result("A program lead verifies an identifier before intake.")


def test_named_product_workspace_in_an_accepted_path_is_not_an_external_gap(tmp_path: Path) -> None:
    prompt = (
        "Create Corridor Console for a dispatcher who records a lane closure in Review Desk "
        "and sees a published status."
    )

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Corridor Console",
    )

    assert "review desk" in str(intent["first_path"]).casefold()
    assert not any("review desk" in str(row).casefold() for row in intent["external_systems"])


def test_explicit_source_matching_the_product_identity_requires_clarification(tmp_path: Path) -> None:
    prompt = "Atlas helps a reviewer approve one request and see a signed decision. Read from Atlas."

    with pytest.raises(GreenfieldClarificationRequired) as error:
        materialize_prompt_intent_hypothesis(
            prompt=prompt,
            repo_root=tmp_path,
            fallback_title="Atlas",
        )

    assert error.value.required_fields == ("external_systems",)
    assert error.value.question == (
        "Is Atlas the product itself, or an external system required by the first path?"
    )
    assert not (tmp_path / ".odylith/runtime/greenfield").exists()
