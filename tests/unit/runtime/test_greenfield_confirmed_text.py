from __future__ import annotations

from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_confirmed_text import confirmed_text_values


ROOT = Path(__file__).resolve().parents[3]
DOMAIN_INTELLIGENCE = ROOT / "src/odylith/runtime/domain_intelligence"
CONFIRMED_TEXT_PATH = DOMAIN_INTELLIGENCE / "greenfield_confirmed_text.py"


def test_confirmed_intent_list_text_coercion_stays_in_text_owner() -> None:
    text_source = CONFIRMED_TEXT_PATH.read_text(encoding="utf-8")
    assert "def confirmed_text_values" in text_source
    assert confirmed_text_values(" **Resident** confirms `booking` ") == ["Resident confirms booking"]
    assert confirmed_text_values([" - visible bullet text ", "", "`Queue` status"]) == [
        "- visible bullet text",
        "Queue status",
    ]
    assert confirmed_text_values({"mapping": "is not a confirmed list row"}) == []

    for path in (
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_intent.py",
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_intent_completion.py",
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_actor_completion.py",
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_system_completion.py",
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_intent_validation.py",
    ):
        source = path.read_text(encoding="utf-8")
        assert "def _strings" not in source
        assert "confirmed_text_values" in source
