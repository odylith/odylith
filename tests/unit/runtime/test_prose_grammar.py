from __future__ import annotations

from odylith.runtime.common.prose_grammar import strip_leading_action_modal
from odylith.runtime.common.prose_grammar import strip_trailing_subject_modal
from odylith.runtime.common.prose_grammar import third_person_action_verb


def test_third_person_action_verb_handles_irregular_base_forms() -> None:
    assert third_person_action_verb("be") == "is"
    assert third_person_action_verb("do") == "does"
    assert third_person_action_verb("have") == "has"


def test_action_modal_boundaries_separate_actor_from_action() -> None:
    assert strip_trailing_subject_modal("Digestive health patients can") == "Digestive health patients"
    assert strip_leading_action_modal("can log meals") == "log meals"
    assert strip_leading_action_modal("need to review evidence") == "review evidence"
