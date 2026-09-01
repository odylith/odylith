from __future__ import annotations

from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    prompt_only_material_decision_error,
)
from odylith.runtime.project_intelligence import intent_confirmation
from odylith.runtime.project_intelligence.intent_confirmation import format_confirmation_choice_lines


def test_relation_free_confirmation_seams_remain_absent() -> None:
    assert not hasattr(greenfield_proposals, "load_confirmed_intent_args")
    assert not hasattr(greenfield_proposals, "_confirmed_intent_markdown_source_path")
    assert not hasattr(intent_confirmation, "build_product_intent_confirmation")
    assert not hasattr(intent_confirmation, "format_product_intent_confirmation_text")


def test_confirmation_choice_block_highlights_exact_allowed_commands() -> None:
    transaction_hash = "a" * 64
    lines = format_confirmation_choice_lines(
        (
            (f"CONFIRM {transaction_hash}", "Commit the validated package."),
            (f"EDIT {transaction_hash} <corrections>", "Rebuild from the corrected evidence."),
            (f"REJECT {transaction_hash}", "Stop without writing records."),
        )
    )
    rendered = "\n".join(lines)

    assert rendered.startswith("## Choose one command")
    assert "For EDIT, replace `<corrections>` with your changes" in rendered
    assert "approval code binds your choice to this reviewed package" in rendered
    assert "### CONFIRM" in rendered
    assert "### EDIT" in rendered
    assert "### REJECT" in rendered
    assert rendered.count("```text") == 3
    assert f"CONFIRM {transaction_hash}" in rendered
    assert f"EDIT {transaction_hash} <corrections>" in rendered
    assert f"REJECT {transaction_hash}" in rendered
    assert "Command buttons" not in rendered
    assert "Copy-ready reply" not in rendered


def test_materiality_recovery_asks_one_focused_question() -> None:
    message = str(prompt_only_material_decision_error())

    assert message.count("?") == 1
    assert "who uses it" not in message
    assert "state changes" not in message
