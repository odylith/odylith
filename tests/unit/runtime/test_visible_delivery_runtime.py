from __future__ import annotations

from odylith.runtime.intervention_engine import visible_delivery_runtime


def test_visible_delivery_already_present_suppresses_stop_block() -> None:
    assert visible_delivery_runtime.visible_delivery_already_present(
        last_assistant_message="Implemented the fix.\n\n**Odylith Assist:** kept this grounded.",
        visible_text="**Odylith Assist:** kept this grounded.",
    )


def test_visible_delivery_already_present_requires_the_same_visible_labels() -> None:
    assert not visible_delivery_runtime.visible_delivery_already_present(
        last_assistant_message="Implemented the fix.\n\n**Odylith Observation:** The signal is real.",
        visible_text="**Odylith Assist:** kept this grounded.",
    )
    assert not visible_delivery_runtime.visible_delivery_already_present(
        last_assistant_message="Implemented the fix.\n\n**Odylith Observation:** The signal is real.",
        visible_text=(
            "**Odylith Observation:** The signal is real.\n\n"
            "**Odylith Assist:** kept this grounded."
        ),
    )
    assert visible_delivery_runtime.visible_delivery_already_present(
        last_assistant_message="Implemented the fix.\n\n**Odylith Observation:** The signal is real.",
        visible_text="---\n**Odylith Observation:** The signal is real.\n---",
    )
    assert visible_delivery_runtime.visible_delivery_already_present(
        last_assistant_message="Implemented the fix.\n\n---\n**Odylith Observation:** The signal is real.\n---",
        visible_text="---\n**Odylith Observation:** The signal is real.\n---",
    )
    assert visible_delivery_runtime.visible_delivery_already_present(
        last_assistant_message="Implemented the fix.\n\n---\n\n**Odylith Observation:** The signal is real.\n\n---",
        visible_text="---\n**Odylith Observation:** The signal is real.\n---",
    )
    assert not visible_delivery_runtime.visible_delivery_already_present(
        last_assistant_message=(
            "Implemented the fix.\n\n"
            "**Odylith Observation:** Older signal.\n\n"
            "**Odylith Assist:** Older closeout."
        ),
        visible_text=(
            "**Odylith Observation:** New signal.\n\n"
            "**Odylith Assist:** New closeout."
        ),
    )
    assert visible_delivery_runtime.visible_delivery_already_present(
        last_assistant_message=(
            "Implemented the fix.\n\n"
            "**Odylith Observation:** The signal is real.\n\n"
            "**Odylith Assist:** kept this grounded."
        ),
        visible_text=(
            "**Odylith Observation:** The signal is real.\n\n"
            "**Odylith Assist:** kept this grounded."
        ),
    )
    assert visible_delivery_runtime.visible_delivery_already_present(
        last_assistant_message=(
            "Implemented the fix.\n\n"
            "---\n\n"
            "**Odylith Observation:** The signal is real.\n\n"
            "**Odylith Assist:** kept this grounded.\n\n"
            "---"
        ),
        visible_text=(
            "**Odylith Observation:** The signal is real.\n\n"
            "**Odylith Assist:** kept this grounded."
        ),
    )
    assert visible_delivery_runtime.visible_delivery_already_present(
        last_assistant_message=(
            "---\n\n"
            "Odylith Observation: This request is making architecture, ownership, or boundary claims.\n\n"
            "---"
        ),
        visible_text=(
            "---\n\n"
            "**Odylith Observation:** This request is making architecture, ownership, or boundary claims.\n\n"
            "---"
        ),
    )
    assert visible_delivery_runtime.visible_delivery_already_present(
        last_assistant_message=(
            "Implemented the fix.\n\n"
            "---\n\n"
            "**Odylith Observation:** The signal is real.\n\n"
            "---\n\n"
            "**Odylith Assist:** kept this grounded."
        ),
        visible_text=(
            "**Odylith Observation:** The signal is real.\n\n"
            "**Odylith Assist:** kept this grounded."
        ),
    )
