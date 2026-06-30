from odylith.runtime.surfaces import atlas_box_terms


def test_tracked_object_phrase_prefers_owned_domain_object() -> None:
    phrase = atlas_box_terms.tracked_object_phrase(
        "Plant owner owns potted plants. Care event log records release proof."
    )

    assert phrase == "potted plant"


def test_tracked_object_phrase_falls_back_to_generic_record() -> None:
    phrase = atlas_box_terms.tracked_object_phrase(
        "First governed proof path stays visible through release review."
    )

    assert phrase == "tracked record"
