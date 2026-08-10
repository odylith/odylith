from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_component_term_index import component_domain_terms
from odylith.runtime.domain_intelligence import greenfield_confirmed_components
from odylith.runtime.domain_intelligence.greenfield_confirmed_components import confirmed_components


def test_sparse_record_component_uses_the_accepted_state_object_for_specificity() -> None:
    rows = confirmed_components(
        label="Semiconductor Reliability Lab Custody",
        label_slug="semiconductor-reliability-lab-custody",
        internal_systems=[
            "Chain-of-custody Evidence Recordkeeping — preserves chain-of-custody evidence and handoff context",
        ],
        first_path="A lab user preserves chain-of-custody evidence for a wafer lot sample.",
        state_object="The primary state object is a wafer lot sample.",
        proof_boundary="Engineering review can inspect custody proof for the wafer lot sample.",
    )

    label = rows[0]["label"]
    assert label == "Wafer Sample Chain-of-custody Evidence Recordkeeping Service"
    assert len(component_domain_terms(label)) >= 4


def test_specific_record_component_does_not_absorb_an_unrelated_state_prefix() -> None:
    rows = confirmed_components(
        label="Weather Radar Calibration Setup Workspace",
        label_slug="weather-radar-calibration-setup-workspace",
        internal_systems=[
            "Beam Blockage Evidence Recordkeeping — preserves beam blockage evidence and handoff context",
        ],
        first_path="A meteorologist manages a radar scan and preserves beam blockage evidence.",
        state_object="The primary state object is a radar scan.",
        proof_boundary="A calibration reviewer can inspect beam blockage evidence.",
    )

    assert rows[0]["label"] == "Beam Blockage Evidence Recordkeeping Service"


def test_each_component_rebuild_uses_its_own_source_action(monkeypatch) -> None:  # noqa: ANN001
    seen: list[tuple[str, str]] = []

    def responsibility(label: str, _contract, *, source_action: str = "") -> str:  # noqa: ANN001
        seen.append((label, source_action))
        return f"{label}: {source_action}"

    monkeypatch.setattr(greenfield_confirmed_components, "_generated_or_weak", lambda _value: True)
    monkeypatch.setattr(greenfield_confirmed_components, "responsibility_from_contract", responsibility)

    confirmed_components(
        label="Decision Workspace",
        label_slug="decision-workspace",
        internal_systems=[
            "Queue Intake — captures submitted requests and validation context",
            "Decision Review — presents accepted decisions and blocked reasons",
        ],
        first_path="A reviewer captures a request and presents a decision.",
        state_object="The primary state object is a request.",
        proof_boundary="The accepted decision is reviewable.",
    )

    rebuilt = seen[-2:]
    assert rebuilt[0][1] == "captures submitted requests and validation context"
    assert rebuilt[1][1] == "presents accepted decisions and blocked reasons"
