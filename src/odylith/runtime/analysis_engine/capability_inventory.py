"""Host-agnostic Odylith capability and engine inventory."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Sequence


@dataclass(frozen=True)
class InventoryItem:
    name: str
    layer: str
    kind: str
    owns: str
    commands: tuple[str, ...] = ()
    anchors: tuple[str, ...] = ()


_ENGINE_GROUPS: tuple[tuple[str, tuple[InventoryItem, ...]], ...] = (
    (
        "Analysis, reasoning, and delivery intelligence",
        (
            InventoryItem(
                name="Analysis Engine",
                layer="analysis",
                kind="engine",
                owns=(
                    "repo-source scanning, capability discovery, app-boundary proposals, and the "
                    "`odylith show` advisory demo; it explains what Odylith can do for this repo "
                    "without mutating governed truth"
                ),
                commands=("odylith show", "odylith capabilities"),
                anchors=("src/odylith/runtime/analysis_engine/",),
            ),
            InventoryItem(
                name="Delivery Intelligence",
                layer="delivery",
                kind="engine",
                owns=(
                    "scope synthesis across Radar, Registry, Atlas, Casebook, Compass, runtime "
                    "evidence, Tribunal rows, and Proof State so every surface consumes one "
                    "delivery posture instead of rebuilding local summaries"
                ),
                anchors=(
                    "src/odylith/runtime/governance/delivery_intelligence_engine.py",
                    "odylith/runtime/delivery_intelligence.v4.json",
                ),
            ),
            InventoryItem(
                name="Tribunal",
                layer="reasoning",
                kind="engine",
                owns=(
                    "diagnosis: dossier construction, fixed actor memos, adjudication, confidence "
                    "scoring, provider-gated enrichment, ranked case rows, and bounded correction "
                    "packets"
                ),
                anchors=("src/odylith/runtime/reasoning/tribunal_engine.py",),
            ),
            InventoryItem(
                name="Reasoning Engine",
                layer="reasoning",
                kind="engine family",
                owns=(
                    "the host-model-agnostic reasoning layer behind Tribunal: deterministic actor "
                    "policy first, optional provider enrichment only when evidence-gated, and "
                    "degraded states that remain explicit"
                ),
                anchors=("src/odylith/runtime/reasoning/", "odylith/runtime/odylith-reasoning.v4.json"),
            ),
            InventoryItem(
                name="Execution Engine",
                layer="execution",
                kind="engine",
                owns=(
                    "next-action admissibility: execution contracts, allowed and forbidden moves, "
                    "frontier state, closure, waits, receipts, contradiction records, and validation "
                    "obligations"
                ),
                anchors=("src/odylith/runtime/execution_engine/", "docs/EXECUTION_ENGINE.md"),
            ),
            InventoryItem(
                name="Proof State",
                layer="proof",
                kind="engine",
                owns=(
                    "live blocker frontier, claim-tier posture, falsification memory, and proof "
                    "resolution fields consumed by Delivery Intelligence and Execution Engine"
                ),
                anchors=("odylith/registry/source/components/proof-state/CURRENT_SPEC.md",),
            ),
            InventoryItem(
                name="Surface DAGs",
                layer="surface-integrity",
                kind="integrity layer",
                owns=(
                    "fingerprint-gated dependency graphs for Compass, Radar, Registry, Atlas, "
                    "Casebook, and the Dashboard Shell so rendered surfaces refresh from their "
                    "owned source truth, renderer inputs, projection memory, and Delivery "
                    "Intelligence instead of stale local summaries"
                ),
                anchors=("src/odylith/runtime/governance/surface_refresh_fingerprint_dag.py",),
            ),
        ),
    ),
    (
        "Governance and intervention",
        (
            InventoryItem(
                name="Governance Engine",
                layer="governance",
                kind="engine family",
                owns=(
                    "CLI-first authoring, validation, reconciliation, and sync for Radar, Registry, "
                    "Atlas, Casebook, Compass, technical plans, releases, programs, and waves"
                ),
                commands=(
                    "odylith sync",
                    "odylith governance",
                    "odylith validate",
                    "odylith backlog",
                    "odylith component",
                    "odylith atlas",
                    "odylith bug",
                    "odylith compass",
                ),
            ),
            InventoryItem(
                name="Governance Intervention Engine",
                layer="intervention",
                kind="engine",
                owns=(
                    "conversation timing and product voice for Teaser, Odylith Observation, "
                    "Odylith Proposal, and Odylith Assist without tying the behavior to one host model"
                ),
                commands=("odylith claude intervention-status", "odylith codex intervention-status"),
                anchors=("src/odylith/runtime/intervention_engine/",),
            ),
            InventoryItem(
                name="Discipline Engine",
                layer="discipline",
                kind="engine",
                owns=(
                    "deterministic hard laws, open-world runtime pressure, local stance, and "
                    "credit-safe validation for shared Codex and Claude behavior"
                ),
                commands=("odylith discipline", "odylith validate discipline"),
            ),
            InventoryItem(
                name="Benchmark Harness",
                layer="proof",
                kind="engine",
                owns=(
                    "quick and full benchmark-family proof for discipline, guidance behavior, "
                    "release gates, and public product claims"
                ),
                commands=("odylith benchmark",),
            ),
        ),
    ),
    (
        "Memory, orchestration, and lifecycle",
        (
            InventoryItem(
                name="Memory Substrate",
                layer="memory",
                kind="substrate",
                owns=(
                    "Context Engine packet retrieval, projection memory, memory backend/contracts, "
                    "anchor resolution, lexical query, session briefs, and bounded packet expansion"
                ),
                commands=("odylith context", "odylith query", "odylith session-brief", "odylith context-engine"),
                anchors=(
                    "src/odylith/runtime/context_engine/",
                    "odylith/registry/source/components/odylith-memory-backend/CURRENT_SPEC.md",
                    "odylith/registry/source/components/odylith-memory-contracts/CURRENT_SPEC.md",
                ),
            ),
            InventoryItem(
                name="Subagent Router",
                layer="orchestration",
                kind="engine",
                owns=(
                    "bounded route selection, host capability shaping, and delegation eligibility "
                    "without making host transport a product capability boundary"
                ),
                commands=("odylith subagent-router",),
            ),
            InventoryItem(
                name="Subagent Orchestrator",
                layer="orchestration",
                kind="engine",
                owns=(
                    "multi-leaf task decomposition, worker contract shaping, validation handoff, "
                    "and serial or parallel execution-wave discipline"
                ),
                commands=("odylith subagent-orchestrator",),
            ),
            InventoryItem(
                name="Install, Upgrade, and Migration Runtime",
                layer="lifecycle",
                kind="engine family",
                owns=(
                    "hosted bootstrap, release verification, repo-local runtime activation, repair, "
                    "rollback, uninstall semantics, migration ledgers, and migration-readiness evidence"
                ),
                commands=(
                    "odylith install",
                    "odylith upgrade",
                    "odylith doctor",
                    "odylith rollback",
                    "odylith uninstall",
                    "odylith release migration-gate",
                ),
            ),
            InventoryItem(
                name="Security and Trust",
                layer="trust",
                kind="engine family",
                owns=(
                    "release provenance, SBOM and digest checks, trust receipts, hot-file integrity, "
                    "runtime metadata, and archive-safety validation"
                ),
                anchors=("src/odylith/install/runtime_integrity.py", "src/odylith/install/release_assets.py"),
            ),
        ),
    ),
)

_SURFACE_GROUPS: tuple[tuple[str, tuple[InventoryItem, ...]], ...] = (
    (
        "Governed source-of-truth surfaces",
        (
            InventoryItem(
                name="Radar",
                layer="governance",
                kind="surface",
                owns="workstream backlog, ranking posture, programs, releases, and execution waves",
                commands=("odylith backlog", "odylith radar", "odylith release", "odylith program", "odylith wave"),
            ),
            InventoryItem(
                name="Registry",
                layer="governance",
                kind="surface",
                owns="component inventory, living specs, dossiers, forensics, and ownership boundaries",
                commands=("odylith component", "odylith registry"),
            ),
            InventoryItem(
                name="Atlas",
                layer="architecture",
                kind="surface",
                owns="architecture diagrams, Mermaid source, rendered artifacts, and catalog truth",
                commands=("odylith atlas",),
            ),
            InventoryItem(
                name="Casebook",
                layer="quality",
                kind="surface",
                owns="bug records with reproduced failure evidence and lifecycle status",
                commands=("odylith bug", "odylith casebook", "odylith github"),
            ),
            InventoryItem(
                name="Compass",
                layer="runtime",
                kind="surface",
                owns="standup brief, timeline audit, live runtime state, blockers, and session continuity",
                commands=("odylith compass", "odylith dashboard refresh"),
            ),
            InventoryItem(
                name="Technical Plans",
                layer="delivery",
                kind="surface",
                owns="bounded implementation plans, done/parked state, and risk/mitigation contracts",
                commands=("odylith governance", "odylith validate plan-*", "odylith plan"),
            ),
        ),
    ),
    (
        "Host adapters and operator surfaces",
        (
            InventoryItem(
                name="Codex Adapter",
                layer="host-adapter",
                kind="adapter",
                owns="Codex hook payloads, routed spawn support, visible-intervention status, and Codex project assets",
                commands=("odylith codex",),
            ),
            InventoryItem(
                name="Claude Code Adapter",
                layer="host-adapter",
                kind="adapter",
                owns=(
                    "Claude hooks, Task-tool delegation contracts, statusline, "
                    "visible-intervention status, and Claude project assets"
                ),
                commands=("odylith claude",),
            ),
            InventoryItem(
                name="Dashboard Shell",
                layer="operator-ui",
                kind="surface",
                owns="the local HTML launchpad that links Radar, Registry, Atlas, Compass, and Casebook",
                commands=("odylith dashboard refresh",),
            ),
        ),
    ),
)


def inventory_payload() -> dict[str, object]:
    """Return the product-owned capability inventory as structured data."""
    return {
        "schema": "odylith.capability_inventory.v1",
        "posture": "host-model-agnostic",
        "note": (
            "Codex and Claude Code are host adapters. The engines below are Odylith "
            "product capabilities and should not be inferred from one host model's CLI output."
        ),
        "engine_groups": [
            {
                "name": group_name,
                "items": [asdict(item) for item in items],
            }
            for group_name, items in _ENGINE_GROUPS
        ],
        "surface_groups": [
            {
                "name": group_name,
                "items": [asdict(item) for item in items],
            }
            for group_name, items in _SURFACE_GROUPS
        ],
    }


def _format_item(item: dict[str, object]) -> list[str]:
    lines = [f"- {item['name']} ({item['kind']}, {item['layer']}): {item['owns']}."]
    commands = tuple(item.get("commands") or ())
    if commands:
        lines.append(f"  Commands: {', '.join(f'`{command}`' for command in commands)}.")
    anchors = tuple(item.get("anchors") or ())
    if anchors:
        lines.append(f"  Anchors: {', '.join(f'`{anchor}`' for anchor in anchors)}.")
    return lines


def format_text(payload: dict[str, object]) -> str:
    """Render the inventory in a compact operator-readable form."""
    lines = [
        "Odylith capabilities and engines",
        "",
        "Host model: agnostic. Codex and Claude Code are adapters; the capability map is product-owned.",
        "Use `odylith --help` for command syntax. Use this inventory for product capability taxonomy.",
        "",
        "Core engines",
    ]

    for group in payload["engine_groups"]:  # type: ignore[index]
        group_payload = dict(group)  # type: ignore[arg-type]
        lines.extend(("", str(group_payload["name"])))
        for item in group_payload["items"]:  # type: ignore[index]
            lines.extend(_format_item(dict(item)))  # type: ignore[arg-type]

    lines.extend(("", "Governed surfaces and adapters"))
    for group in payload["surface_groups"]:  # type: ignore[index]
        group_payload = dict(group)  # type: ignore[arg-type]
        lines.extend(("", str(group_payload["name"])))
        for item in group_payload["items"]:  # type: ignore[index]
            lines.extend(_format_item(dict(item)))  # type: ignore[arg-type]

    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith capabilities",
        description="List Odylith's host-agnostic product capabilities, engines, surfaces, and adapters.",
    )
    parser.add_argument("--repo-root", default=".", help=argparse.SUPPRESS)
    parser.add_argument("--format", choices=("text", "json"), default="text", dest="output_format")
    parser.add_argument("--json", action="store_true", help="Emit structured JSON.")
    args = parser.parse_args(argv)

    payload = inventory_payload()
    if args.json or args.output_format == "json":
        print(json.dumps(payload, indent=2, sort_keys=False))
    else:
        print(format_text(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
