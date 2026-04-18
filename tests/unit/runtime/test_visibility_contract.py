from __future__ import annotations

from odylith.runtime.intervention_engine import visibility_contract


def test_visibility_contract_infers_host_family_from_legacy_render_surface() -> None:
    assert visibility_contract.event_host_family({"render_surface": "codex_visible_intervention"}) == "codex"
    assert visibility_contract.event_host_family({"render_surface": "claude_visible_intervention"}) == "claude"
    assert visibility_contract.event_host_family({"host_family": "Codex"}) == "codex"


def test_visibility_contract_classifies_visible_families_from_labels_and_kinds() -> None:
    assert (
        visibility_contract.event_visibility_family(
            {"display_markdown": "---\n\n**Odylith Risks:** compact risk.\n\n---"}
        )
        == "ambient"
    )
    assert (
        visibility_contract.event_visibility_family(
            {"display_markdown": "---\n\n**Odylith Observation:** compact observation.\n\n---"}
        )
        == "intervention"
    )
    assert visibility_contract.event_visibility_family({"summary": "**Odylith Assist:** closeout."}) == "assist"
    assert visibility_contract.event_visibility_family({"kind": "intervention_teaser"}) == "teaser"


def test_visibility_contract_separates_ledger_visible_from_chat_confirmed() -> None:
    manual_visible = {"delivery_channel": "manual_visible_command", "delivery_status": "manual_visible"}
    chat_confirmed = {
        "delivery_channel": "assistant_chat_transcript",
        "delivery_status": "assistant_chat_confirmed",
    }
    hidden_ready = {
        "delivery_channel": "system_message_and_assistant_fallback",
        "delivery_status": "assistant_fallback_ready",
        "display_markdown": "**Odylith Observation:** hidden.",
    }

    assert visibility_contract.event_visible(manual_visible) is True
    assert visibility_contract.event_chat_confirmed(manual_visible) is False
    assert visibility_contract.event_visible(chat_confirmed) is True
    assert visibility_contract.event_chat_confirmed(chat_confirmed) is True
    assert visibility_contract.event_visible(hidden_ready) is False
    assert visibility_contract.event_requires_chat_confirmation(hidden_ready) is True


def test_visibility_contract_proof_status_from_counts() -> None:
    assert (
        visibility_contract.proof_status_from_counts(
            visible_count=1,
            chat_confirmed_count=0,
            unconfirmed_count=1,
        )
        == "ledger_visible_with_pending_confirmation"
    )
    assert (
        visibility_contract.proof_status_from_counts(
            visible_count=1,
            chat_confirmed_count=0,
            unconfirmed_count=0,
        )
        == "ledger_visible_unconfirmed"
    )
    assert (
        visibility_contract.proof_status_from_counts(
            visible_count=1,
            chat_confirmed_count=1,
            unconfirmed_count=0,
        )
        == "proven_this_session"
    )
    assert (
        visibility_contract.proof_status_from_counts(
            visible_count=0,
            chat_confirmed_count=0,
            unconfirmed_count=0,
            static_ready=False,
        )
        == "degraded"
    )


def test_visibility_contract_normalizes_string_lists_with_deduping_and_limits() -> None:
    assert visibility_contract.normalize_string_list(["  B-001  ", "B-001", "", "CB-104"]) == [
        "B-001",
        "CB-104",
    ]
    assert visibility_contract.normalize_string_list(["one", "two", "three"], limit=2) == ["one", "two"]
    assert visibility_contract.normalize_string_list(" single ") == ["single"]


def test_visibility_contract_mapping_copy_and_join_blocks_are_stable() -> None:
    payload = {"key": "value"}

    assert visibility_contract.mapping_copy(payload) == {"key": "value"}
    assert visibility_contract.mapping_copy(None) == {}
    assert visibility_contract.join_blocks(" first ", "\n\nfirst\n", "second") == "first\n\nsecond"
