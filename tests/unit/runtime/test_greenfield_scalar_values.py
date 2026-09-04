from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_scalar_values import (
    nested_text_values,
    scalar_word_count,
    unique_text_values,
)


def test_nested_text_values_flattens_typed_values_without_phrase_parsing() -> None:
    assert nested_text_values(
        {
            "first": ["  Saved   receipt  ", "VISIBLE RESULT"],
            "second": ("visible result", None, 4),
        }
    ) == ("Saved receipt", "VISIBLE RESULT", "4")


def test_unique_text_values_preserves_first_case_and_scalar_word_boundaries() -> None:
    assert unique_text_values([" Owner ", ["owner", "API-to-store"]]) == (
        "Owner",
        "API-to-store",
    )
    assert scalar_word_count("API-to-store: v2") == 4
