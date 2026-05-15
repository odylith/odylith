"""Atlas diagram helpers for confirmed greenfield proposals."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def confirmed_diagrams(
    *,
    label: str,
    components: list[dict[str, Any]],
    diagram_slugs: Mapping[str, str],
) -> list[dict[str, Any]]:
    component_rows = [
        {"name": str(row["label"]), "description": str(row["responsibility"])}
        for row in components
    ]
    workstreams = [
        f"Establish {label} Program",
        f"Prove {label} First Workflow",
        f"Define {label} State And Evidence Boundaries",
    ]
    return [
        {
            "slug": diagram_slugs["context"],
            "title": "System Context View",
            "kind": "flowchart",
            "summary": f"Show {label.lower()} actors, workflow service, state store, evidence review, and external sources.",
            "owner": "repo",
            "status": "draft",
            "link_state": "atlas_first_draft",
            "components": component_rows,
            "related_workstream_titles": workstreams,
            "related_components": [str(row["component_id"]) for row in components],
            "watch_paths": [],
            "evidence_tier": "user_intent",
            "mermaid_source": _context_mermaid(label),
        },
        {
            "slug": diagram_slugs["sequence"],
            "title": "First Workflow Sequence",
            "kind": "sequenceDiagram",
            "summary": f"Walk the first {label.lower()} workflow from operator action to state replay and evidence review.",
            "owner": "repo",
            "status": "draft",
            "link_state": "atlas_first_draft",
            "components": component_rows,
            "related_workstream_titles": workstreams,
            "related_components": [str(row["component_id"]) for row in components],
            "watch_paths": [],
            "evidence_tier": "user_intent",
            "mermaid_source": _sequence_mermaid(label),
        },
        {
            "slug": diagram_slugs["ownership"],
            "title": "Ownership And Proof View",
            "kind": "flowchart",
            "summary": f"Show {label.lower()} workflow, state, evidence, access, and release proof ownership.",
            "owner": "repo",
            "status": "draft",
            "link_state": "atlas_first_draft",
            "components": component_rows,
            "related_workstream_titles": workstreams,
            "related_components": [str(row["component_id"]) for row in components],
            "watch_paths": [],
            "evidence_tier": "user_intent",
            "mermaid_source": _ownership_mermaid(label),
        },
    ]


def _context_mermaid(label: str) -> str:
    return (
        "flowchart LR\n"
        f"  operator[\"{label}<br/>operator\"] --> workflow[\"Workflow<br/>service\"]\n"
        "  workflow --> state[\"State<br/>store\"]\n"
        "  workflow --> evidence[\"Evidence<br/>review\"]\n"
        "  source[\"Fixture or<br/>sandbox source\"] --> workflow\n"
        "  evidence --> reviewer[\"Release<br/>reviewer\"]\n"
        "  classDef actor fill:#EFF6FF,stroke:#BFD7FE,color:#17233A,stroke-width:1px;\n"
        "  classDef service fill:#ECFDFB,stroke:#A7E9E3,color:#17233A,stroke-width:1px;\n"
        "  classDef proof fill:#F5F3FF,stroke:#DDD6FE,color:#17233A,stroke-width:1px;\n"
        "  class operator,reviewer actor;\n"
        "  class workflow,state service;\n"
        "  class evidence,source proof;\n"
    )


def _sequence_mermaid(label: str) -> str:
    return (
        "sequenceDiagram\n"
        "  autonumber\n"
        f"  participant O as {label} Operator\n"
        "  participant W as Workflow Service\n"
        "  participant S as State Store\n"
        "  participant E as Evidence Review\n"
        "  O->>W: submit first workflow input\n"
        "  W->>S: create or update state record\n"
        "  S-->>W: state snapshot and version\n"
        "  W->>E: assemble proof packet\n"
        "  E-->>O: release-ready status or blocking issue\n"
    )


def _ownership_mermaid(label: str) -> str:
    return (
        "flowchart TB\n"
        f"  lead[\"{label}<br/>workflow lead\"] --> workflow[\"Workflow commands<br/>and status\"]\n"
        "  workflow --> state[\"Versioned<br/>state record\"]\n"
        "  state --> replay[\"Replay<br/>check\"]\n"
        "  proof[\"Proof<br/>lead\"] --> evidence[\"Evidence packet<br/>and decision\"]\n"
        "  replay --> evidence\n"
        "  access[\"Access and<br/>privacy policy\"] --> workflow\n"
        "  access --> evidence\n"
        "  evidence --> release[\"Release<br/>gate\"]\n"
        "  classDef owner fill:#EFF6FF,stroke:#BFD7FE,color:#17233A,stroke-width:1px;\n"
        "  classDef state fill:#ECFDFB,stroke:#A7E9E3,color:#17233A,stroke-width:1px;\n"
        "  classDef gate fill:#FFF7ED,stroke:#FDBA74,color:#17233A,stroke-width:1px;\n"
        "  class lead,proof owner;\n"
        "  class workflow,state,replay,evidence state;\n"
        "  class access,release gate;\n"
    )


__all__ = ["confirmed_diagrams"]
