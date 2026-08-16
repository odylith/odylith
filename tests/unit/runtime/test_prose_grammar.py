from __future__ import annotations

import pytest

from odylith.runtime.common.prose_grammar import contains_finite_action
from odylith.runtime.common.prose_grammar import contains_subject_finite_action
from odylith.runtime.common.prose_grammar import strip_leading_action_modal
from odylith.runtime.common.prose_grammar import strip_trailing_subject_modal
from odylith.runtime.common.prose_grammar import past_action_verb
from odylith.runtime.common.prose_grammar import third_person_action_verb
from odylith.runtime.common.prose_tail import has_incomplete_public_tail
from odylith.runtime.common.prose_tail import strip_incomplete_public_tail


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        ("processing continues", True),
        ("the clerk signs it", True),
        ("approval arrives", True),
        ("operations team records status", True),
        ("it arrives", True),
        ("signs it", False),
        ("records team", False),
        ("the records team", False),
        ("the operations team", False),
        ("customer success team", False),
    ),
)
def test_contains_subject_finite_action_requires_a_complete_clause(value: str, expected: bool) -> None:
    assert contains_subject_finite_action(value) is expected


@pytest.mark.parametrize("value", ("signs it", "adds peptide"))
def test_contains_finite_action_preserves_legacy_fragment_detection(value: str) -> None:
    assert contains_finite_action(value)


def test_third_person_action_verb_handles_irregular_base_forms() -> None:
    assert third_person_action_verb("be") == "is"
    assert third_person_action_verb("do") == "does"
    assert third_person_action_verb("have") == "has"


def test_past_action_verb_recovers_registered_regular_and_irregular_actions() -> None:
    assert past_action_verb("archived") == "archive"
    assert past_action_verb("generated") == "generate"
    assert past_action_verb("published") == "publish"
    assert past_action_verb("approved") == "approve"
    assert past_action_verb("identified") == "identify"
    assert past_action_verb("occupied") == "occupy"
    assert past_action_verb("submitted") == "submit"
    assert past_action_verb("shown") == "show"
    assert past_action_verb("unrelated") == ""


def test_action_modal_boundaries_separate_actor_from_action() -> None:
    assert strip_trailing_subject_modal("Digestive health patients can") == "Digestive health patients"
    assert strip_leading_action_modal("can log meals") == "log meals"
    assert strip_leading_action_modal("need to review evidence") == "review evidence"


def test_clipped_transitive_tail_requires_an_object() -> None:
    assert has_incomplete_public_tail("Dashboard shows".split())
    assert not has_incomplete_public_tail("The show".split())
    assert has_incomplete_public_tail("The clerk records status and sees".split())
    assert strip_incomplete_public_tail("The clerk records status and sees") == "The clerk records status"
    assert not has_incomplete_public_tail("The clerk sees what remains".split())
    assert not has_incomplete_public_tail("Questions remain".split())
    clipped_boundary = "Release 0.0.1 proves one accepted coordination path while private details remain"
    assert has_incomplete_public_tail(clipped_boundary.split())
    assert strip_incomplete_public_tail(clipped_boundary) == (
        "Release 0.0.1 proves one accepted coordination path"
    )
    assert has_incomplete_public_tail(
        "Fixture includes required fields late-fee rule apartment resident drill return".split()
    )
    assert not has_incomplete_public_tail("The workspace tracks every patient sample return".split())
    for verb in ("displays", "provides", "shows"):
        clipped = f"The dashboard opens the record and it {verb}"
        assert has_incomplete_public_tail(clipped.split())
        assert strip_incomplete_public_tail(clipped) == "The dashboard opens the record"


def test_clipped_transitive_tail_removes_an_incomplete_terminal_sentence() -> None:
    assert strip_incomplete_public_tail("The dashboard opens the record. It shows") == (
        "The dashboard opens the record"
    )
    assert strip_incomplete_public_tail("The dashboard shows") == ""


def test_clipped_label_tail_can_preserve_a_complete_subject_noun_phrase() -> None:
    assert strip_incomplete_public_tail("The final summary includes", preserve_subject=True) == (
        "The final summary"
    )
    assert strip_incomplete_public_tail("The workspace tracks every patient sample return") == (
        "The workspace tracks every patient sample return"
    )
