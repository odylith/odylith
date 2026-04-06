from __future__ import annotations

from typing import Any, Mapping

from odylith.runtime.delivery import delivery_intelligence_narrator as narrator


class _ValidProvider:
    def generate_cards(self, *, prompt_payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
        assert prompt_payload["scope_id"] == "registry"
        return {
            "executive_thesis": "Registry is tightening around a shared delivery intelligence boundary.",
            "delivery_tension": "Execution is moving faster than the old local summaries can explain.",
            "why_now": "Operators are already using the dashboard as a control surface.",
            "blast_radius": "Registry, Radar, Atlas, Compass, and Odylith all depend on this readout.",
            "next_forcing_function": "Keep the shared snapshot authoritative before more renderer logic is added.",
        }


class _InvalidProvider:
    def generate_cards(self, *, prompt_payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
        return {
            "executive_thesis": "See src/odylith/runtime/surfaces/render_registry_dashboard.py for the current implementation.",
            "delivery_tension": "This card is invalid because it leaks a raw path.",
            "why_now": "Why now is still important.",
            "blast_radius": "Blast radius is broad.",
            "next_forcing_function": "Take action now.",
        }


def _snapshot() -> dict[str, Any]:
    return {
        "scope_type": "component",
        "scope_id": "registry",
        "scope_label": "Registry",
        "posture_mode": "execution_outrunning_governance",
        "trajectory": "drifting",
        "confidence": "Low",
        "scores": {
            "governance_lag": 88,
            "decision_debt": 74,
        },
        "cards": {
            "executive_thesis": "Registry is seeing implementation before explicit governance capture.",
            "delivery_tension": "Execution has started, but the decision trail is still thin.",
            "why_now": "The dashboard is central enough that this gap changes trust immediately.",
            "blast_radius": "Registry, Radar, Compass, and Atlas will all reflect the same ambiguity.",
            "next_forcing_function": "Log the explicit Compass checkpoint before calling this governed progress.",
        },
        "evidence_context": {
            "basis": "inferred",
            "freshness": "current",
            "linked_workstreams": ["B-040"],
            "linked_components": ["registry"],
            "linked_diagrams": ["D-008"],
            "linked_surfaces": ["Registry", "Radar", "Atlas", "Compass"],
        },
        "explanation_facts": [
            "workspace activity is present",
            "explicit checkpoints are absent",
        ],
    }


def test_narrate_snapshot_uses_valid_provider_output() -> None:
    result = narrator.narrate_snapshot(
        snapshot=_snapshot(),
        provider=_ValidProvider(),
        mode="auto",
    )
    assert result.source == "hybrid-model"
    assert result.cards["executive_thesis"].startswith("Registry is tightening")


def test_narrate_snapshot_falls_back_on_invalid_provider_output() -> None:
    baseline = _snapshot()["cards"]
    result = narrator.narrate_snapshot(
        snapshot=_snapshot(),
        provider=_InvalidProvider(),
        mode="auto",
    )
    assert result.source == "rules"
    assert result.cards == baseline
    assert any("raw path in card: executive_thesis" in item for item in result.diagnostics)

