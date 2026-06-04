from __future__ import annotations

from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_confirmed_text import (
    CONFIRMED_INTENT_VALIDATION_STOPWORDS,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import confirmed_text_values
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import semantic_terms
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms


ROOT = Path(__file__).resolve().parents[3]
DOMAIN_INTELLIGENCE = ROOT / "src/odylith/runtime/domain_intelligence"
CONFIRMED_TEXT_PATH = DOMAIN_INTELLIGENCE / "greenfield_confirmed_text.py"


def test_confirmed_intent_list_text_coercion_stays_in_text_owner() -> None:
    text_source = CONFIRMED_TEXT_PATH.read_text(encoding="utf-8")
    assert "def confirmed_text_values" in text_source
    assert confirmed_text_values(" **Resident** confirms `booking` ") == [
        "Resident confirms booking"
    ]
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


def test_confirmed_intent_semantic_terms_stay_in_text_owner() -> None:
    text_source = CONFIRMED_TEXT_PATH.read_text(encoding="utf-8")
    index_source = (DOMAIN_INTELLIGENCE / "greenfield_domain_term_index.py").read_text(
        encoding="utf-8"
    )
    validation_source = (
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_intent_validation.py"
    ).read_text(encoding="utf-8")
    system_rows_source = (
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_system_rows.py"
    ).read_text(encoding="utf-8")

    assert "def semantic_terms" in text_source
    assert "stem_ing_minimum_length" in index_source
    assert "ordered_terms(" in text_source
    assert "CONFIRMED_INTENT_VALIDATION_STOPWORDS" in text_source
    assert "normalize_domain_token" not in text_source
    assert "for raw in re.findall" not in text_source
    assert "def _semantic_terms" not in validation_source
    assert "def _semantic_terms" not in system_rows_source
    assert "semantic_terms(" in validation_source
    assert "semantic_terms as _semantic_terms" in system_rows_source
    assert "normalize_domain_token" not in validation_source
    assert "normalize_domain_token" not in system_rows_source

    assert semantic_terms("Race readings and gearbox readings are reviewing status.") == {
        "race",
        "read",
        "gearbox",
        "review",
        "status",
    }
    assert ordered_terms(
        "Race readings and gearbox readings are reviewing status.",
        minimum=3,
        stem_ing=True,
        stem_ing_minimum_length=5,
        stopwords={"and", "are"},
    ) == ["race", "read", "gearbox", "review", "status"]
    assert "product" not in semantic_terms(
        "Product proof keeps a gearbox result ready.",
        stopwords=CONFIRMED_INTENT_VALIDATION_STOPWORDS,
    )


def test_confirmed_project_surface_word_count_stays_in_text_owner() -> None:
    text_source = CONFIRMED_TEXT_PATH.read_text(encoding="utf-8")
    project_brief_source = (
        DOMAIN_INTELLIGENCE / "greenfield_project_brief.py"
    ).read_text(encoding="utf-8")
    project_intelligence_source = (
        DOMAIN_INTELLIGENCE / "greenfield_project_intelligence.py"
    ).read_text(encoding="utf-8")

    assert "def word_count" in text_source
    assert "greenfield_confirmed_text import word_count" in project_brief_source
    assert "greenfield_confirmed_text import word_count" in project_intelligence_source
    assert "def _word_count" not in project_brief_source
    assert "def _word_count" not in project_intelligence_source
    assert word_count("Source-backed review/triage keeps `AI` CRM status visible.") == 9
