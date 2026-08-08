from __future__ import annotations

from pathlib import Path


_ROOT = Path(__file__).resolve().parents[3]


def _source(path: str) -> str:
    return (_ROOT / path).read_text(encoding="utf-8")


def test_greenfield_touched_normalizers_have_one_owner() -> None:
    fields = _source(
        "src/odylith/runtime/domain_intelligence/greenfield_component_contract_fields.py"
    )
    support = _source(
        "src/odylith/runtime/domain_intelligence/greenfield_component_semantic_contract_support.py"
    )
    diagram = _source(
        "src/odylith/runtime/domain_intelligence/greenfield_confirmed_diagram_text.py"
    )
    project_text = _source(
        "src/odylith/runtime/project_intelligence/greenfield_project_text.py"
    )
    participant_cards = _source(
        "src/odylith/runtime/project_intelligence/greenfield_participant_cards.py"
    )
    job_cards = _source(
        "src/odylith/runtime/project_intelligence/greenfield_job_cards.py"
    )

    assert "def _dedupe_adjacent_words" not in fields
    assert "def _dedupe_adjacent_words" not in support
    assert "def _balance_label" not in diagram
    assert "def _repeat_key" not in project_text
    assert "def _repeat_key" not in participant_cards
    assert "def _desired_risk" not in project_text
    assert "def _dedupe_text" not in participant_cards
    assert "greenfield_participant_cards import _repeat_key" not in job_cards


def test_greenfield_tail_cleanup_has_no_regex_word_towers() -> None:
    diagram = _source(
        "src/odylith/runtime/domain_intelligence/greenfield_confirmed_diagram_text.py"
    )
    mermaid = _source("src/odylith/runtime/common/mermaid_text.py")
    sequence_labels = _source(
        "src/odylith/runtime/domain_intelligence/greenfield_sequence_labeling.py"
    )
    semantic_model = _source(
        "src/odylith/runtime/domain_intelligence/greenfield_semantic_model.py"
    )

    assert "strip_dangling_word_tail" in diagram
    assert "actionable|an|and|as|at|because|blocking" not in diagram
    assert "def _strip_dangling_tail" not in mermaid
    assert "an|and|as|at|because|by|for|from" not in mermaid
    assert "accepted|actionable|an|and|as|at|because" not in sequence_labels
    assert "a|an|and|as|at|because|before|by|can" not in semantic_model


def test_greenfield_materiality_has_one_prewrite_owner() -> None:
    materialization = _source(
        "src/odylith/runtime/domain_intelligence/greenfield_prompt_intent_materialization.py"
    )
    staging = _source(
        "src/odylith/runtime/domain_intelligence/greenfield_candidate_intent_stage.py"
    )

    assert not (
        _ROOT
        / "src/odylith/runtime/domain_intelligence/greenfield_preconfirm_transaction_authority.py"
    ).exists()
    assert "materialize_prompt_confirmed_intent" not in materialization
    assert "restage_compiled_candidate_intent" not in staging
    assert "stage_candidate_intent(" in materialization
