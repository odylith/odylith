from __future__ import annotations

import json
from pathlib import Path
import re

import pytest

from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery import (
    intent_hypothesis_from_operator_evidence,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_intent_source
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization import (
    materialize_prompt_intent_hypothesis,
)


_CORPUS_PATH = (
    Path(__file__).parents[2]
    / "fixtures"
    / "greenfield-release-corpus"
    / "retired-aa51-final-holdout-regressions.v1.json"
)
_CORPUS = json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))
_CASES = {row["case_id"]: row for row in _CORPUS["cases"]}
_COMMIT_EXAMPLES = [
    (_CASES[annotation["case_id"]], annotation)
    for annotation in _CORPUS["annotations"]
    if annotation["expected_outcome"] == "commit"
]


def test_prompt_source_preserves_complete_workflow_and_separates_prohibition() -> None:
    prompt = (
        "Northstar helps Mina, the quality lead, receive inspection alerts and attach field evidence. "
        "Mina routes a review request. A conflict moves the request to blocked state; otherwise it enters ready state. "
        "The routine path publishes a signed decision, while the exception path requests owner approval. "
        "It must not activate equipment remotely."
    )

    source = prompt_intent_source(prompt)
    hypothesis = intent_hypothesis_from_operator_evidence(prompt, prefer_product_title=True)

    assert source.title == "Northstar"
    assert source.actor == "Mina, the quality lead"
    assert "receive inspection alerts" in source.first_path
    assert "routes a review request" in source.first_path
    assert "blocked state" in source.first_path
    assert "publishes a signed decision" in source.first_path
    assert "requests owner approval" in source.first_path
    assert "activate equipment remotely" not in source.first_path
    assert hypothesis["non_goals"] == ("It must not activate equipment remotely",)


def test_terminal_deliverable_completes_a_multi_action_first_path(tmp_path: Path) -> None:
    prompt = str(_CASES["ih-08-carbon"]["prompt"])

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="",
    )

    assert "publish a verification-ready carbon packet" in str(intent["first_path"]).casefold()
    assert "issue tradeable credits" in " ".join(intent["non_goals"]).casefold()


def test_inline_without_boundary_stays_out_of_path_and_does_not_fabricate_external_system(
    tmp_path: Path,
) -> None:
    prompt = (
        "Create a greenfield proposal for an open source security embargo room that receives vulnerability reports, "
        "coordinates maintainer triage, tracks affected package evidence, records disclosure approvals, and shows "
        "advisory readiness without sending public announcements in the first release."
    )

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="",
    )

    assert all("embargo room" not in str(row).casefold() for row in intent["external_systems"])
    assert "public announcements" not in str(intent["first_path"]).casefold()
    assert intent["non_goals"] == ["without sending public announcements in the first release."]


def test_collective_relative_actor_keeps_a_complete_path_and_inline_non_goal(tmp_path: Path) -> None:
    prompt = (
        "Create a greenfield proposal for a multi-party security disclosure council that coordinates "
        "external vulnerability reports, affected partner review, embargo decisions, evidence custody, "
        "legal signoff, and public advisory release readiness without personalized notification campaigns "
        "in the first release."
    )

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="",
    )

    assert intent["first_path"].startswith("A multi-party security disclosure council can coordinate")
    assert "public advisory release readiness" in intent["first_path"].casefold()
    assert intent["non_goals"] == ["without personalized notification campaigns in the first release."]


@pytest.mark.parametrize(
    ("case", "annotation"),
    _COMMIT_EXAMPLES,
    ids=[case["case_id"] for case, _annotation in _COMMIT_EXAMPLES],
)
def test_retired_commit_prompts_preserve_every_annotated_path_claim(
    case: dict[str, object],
    annotation: dict[str, object],
) -> None:
    source = prompt_intent_source(str(case["prompt"]))
    hypothesis = intent_hypothesis_from_operator_evidence(str(case["prompt"]), prefer_product_title=True)
    normalized_path = " ".join(source.first_path.casefold().split())
    normalized_prompt = _normalized_text(str(case["prompt"]))

    for category in ("actions", "states", "outputs"):
        for claim in annotation[category]:
            expected = " ".join(str(claim["source_quote"]).casefold().split())
            assert expected in normalized_path
    for claim in annotation["non_goals"]:
        prohibited = " ".join(str(claim["source_quote"]).casefold().split())
        assert prohibited not in normalized_path

    actor_labels = [str(row).partition(":")[0] for row in hypothesis["human_actors"]]
    for actor in actor_labels:
        assert _without_leading_article(_normalized_text(actor)) in normalized_prompt
    for claim in annotation["actors"]:
        expected = _without_leading_article(_normalized_text(str(claim["source_quote"])))
        assert any(expected == _without_leading_article(_normalized_text(label)) for label in actor_labels)

    external_rows = [_normalized_text(str(row)) for row in hypothesis["external_systems"]]
    assert sorted(external_rows) == sorted(
        _normalized_text(str(claim["source_quote"])) for claim in annotation["dependencies"]
    )

    state_object = str(hypothesis["state_object"])
    state_value = state_object.removeprefix("The primary state object is ").rstrip(".")
    assert _source_entails_phrase(source=str(case["prompt"]), phrase=state_value)


@pytest.mark.parametrize(
    ("case", "annotation"),
    _COMMIT_EXAMPLES,
    ids=[case["case_id"] for case, _annotation in _COMMIT_EXAMPLES],
)
def test_retired_commit_prompts_materialize_every_annotated_atomic_fact(
    case: dict[str, object],
    annotation: dict[str, object],
    tmp_path: Path,
) -> None:
    intent = materialize_prompt_intent_hypothesis(
        prompt=str(case["prompt"]),
        repo_root=tmp_path,
        fallback_title="",
    )
    atoms = intent["product_intent_authority"]["atomic_facts"]

    for category in ("actors", "actions", "states", "outputs", "dependencies", "non_goals"):
        accepted = [
            str(row["normalized_value"])
            for row in atoms
            if category in row["categories"] and row["custody_state"] == "accepted_fact"
        ]
        for claim in annotation[category]:
            assert any(
                _semantic_claim_covered(str(claim["source_quote"]), value)
                for value in accepted
            ), (category, claim["source_quote"], accepted)


def _normalized_text(value: str) -> str:
    return " ".join(value.casefold().replace(",", "").split())


def _without_leading_article(value: str) -> str:
    parts = value.split()
    return " ".join(parts[1:] if parts and parts[0] in {"a", "an", "the"} else parts)


def _source_entails_phrase(*, source: str, phrase: str) -> bool:
    source_terms = set(re.findall(r"[a-z0-9][a-z0-9'-]*", source.casefold()))
    phrase_terms = [
        term
        for term in re.findall(r"[a-z0-9][a-z0-9'-]*", phrase.casefold())
        if term not in {"a", "an", "the"}
    ]
    for term in phrase_terms:
        variants = {term, f"{term}s", f"{term}es"}
        if term.endswith("y") and len(term) > 1:
            variants.add(f"{term[:-1]}ies")
        if not variants & source_terms:
            return False
    return bool(phrase_terms)


def _semantic_claim_covered(claim: str, value: str) -> bool:
    claim_terms = _stemmed_terms(claim)
    value_terms = _stemmed_terms(value)
    return bool(claim_terms and (claim_terms <= value_terms or value_terms <= claim_terms))


def _stemmed_terms(value: str) -> set[str]:
    terms: set[str] = set()
    for token in re.findall(r"[a-z0-9]+", value.casefold()):
        if token in {"a", "an", "and", "the", "to", "with"}:
            continue
        if len(token) > 5 and token.endswith("ies"):
            token = f"{token[:-3]}y"
        elif len(token) > 4 and token.endswith("es"):
            token = token[:-2] if token[:-2].endswith(("ch", "o", "s", "sh", "x", "z")) else token[:-1]
        elif len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
            token = token[:-1]
        if len(token) > 5 and token.endswith("e"):
            token = token[:-1]
        terms.add(token)
    return terms
