from __future__ import annotations

from odylith.runtime.context_engine.grounding_component_priority import prioritize_governance_components


def test_prioritize_governance_components_prefers_exact_component_scope_match() -> None:
    rows = [
        {
            "component_id": "odylith",
            "path": "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
        },
        {
            "component_id": "benchmark",
            "path": "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
        },
    ]

    ordered = prioritize_governance_components(
        rows=rows,
        changed_paths=[
            "odylith/registry/source/component_registry.v1.json",
            "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
        ],
    )

    assert [row["component_id"] for row in ordered] == ["benchmark", "odylith"]
