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
    activation: str = ""


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
                activation=(
                    "direct CLI fast path; analyzes local source evidence and prints advisory posture "
                    "without creating governance records"
                ),
            ),
            InventoryItem(
                name="Domain Intelligence",
                layer="analysis",
                kind="engine",
                owns=(
                    "provider-free greenfield project classification, backlog proposals, program "
                    "waves, provisional release plans, planned Registry components, draft Atlas "
                    "topology, assumptions, risks, validation obligations, deterministic proposal "
                    "Tribunal gating, and final visible surface refresh before source exists"
                ),
                commands=("odylith greenfield propose", "odylith greenfield apply", "odylith greenfield create"),
                anchors=("src/odylith/runtime/domain_intelligence/",),
                activation=(
                    "greenfield propose/create run the provider-free proposal builder, deterministic "
                    "proposal Tribunal, owned writer transaction, and final governed-surface refresh"
                ),
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
                commands=("odylith sync", "odylith governance-slice"),
                activation=(
                    "sync and governance-slice refresh the shared delivery snapshot so Radar, Registry, "
                    "Atlas, Casebook, Compass, and Proof State consume one delivery posture"
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
                commands=("odylith bug capture", "odylith greenfield propose"),
                anchors=(
                    "src/odylith/runtime/reasoning/tribunal_engine.py",
                    "src/odylith/runtime/domain_intelligence/proposal_tribunal.py",
                    "src/odylith/runtime/governance/artifact_tribunal.py",
                ),
                activation=(
                    "bug capture and greenfield proposal flows invoke deterministic Tribunal gates before "
                    "governed writes; provider enrichment remains evidence-gated and optional"
                ),
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
                anchors=(
                    "src/odylith/runtime/reasoning/",
                    "odylith/atlas/source/odylith-tribunal-multi-actor-reasoning-engine.mmd",
                ),
                activation=(
                    "reasoning packets are built from deterministic actor policy first and degrade "
                    "explicitly when provider-backed enrichment is unavailable"
                ),
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
                commands=("odylith context", "odylith governance-slice"),
                anchors=("src/odylith/runtime/execution_engine/", "docs/EXECUTION_ENGINE.md"),
                activation=(
                    "Context Engine packets attach the normalized execution handshake and compact "
                    "admissibility snapshot before a turn widens into implementation or verification"
                ),
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
                activation=(
                    "Delivery Intelligence and Execution Engine read proof-state posture as claim-tier "
                    "frontier data rather than regenerating proof status locally"
                ),
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
                commands=("odylith sync", "odylith dashboard refresh"),
                anchors=("src/odylith/runtime/governance/surface_refresh_fingerprint_dag.py",),
                activation=(
                    "refresh pipelines fingerprint source truth, renderer inputs, projection memory, and "
                    "delivery snapshots so unchanged surfaces stay cached and impacted surfaces rerender"
                ),
            ),
            InventoryItem(
                name="Topology Integrity",
                layer="topology",
                kind="integrity layer",
                owns=(
                    "shared Radar, Registry, Atlas, Program, Release, and wave topology: "
                    "traceability graph construction, structural edge validation, component and "
                    "diagram linkage checks, and topology-quality scoring before generated "
                    "surfaces claim coherence"
                ),
                commands=("odylith validate topology-integrity", "odylith architecture"),
                anchors=(
                    "src/odylith/runtime/governance/topology_integrity.py",
                    "src/odylith/runtime/governance/build_traceability_graph.py",
                    "src/odylith/runtime/governance/traceability_graph_spine.py",
                ),
                activation=(
                    "traceability graph builds and topology-integrity validation score structural Radar, "
                    "Registry, Atlas, Program, Release, and wave edges before surfaces claim coherence"
                ),
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
                anchors=("src/odylith/runtime/governance/",),
                activation=(
                    "CLI-first authoring and sync routes mutate governed truth through owned writers, "
                    "then rerender the relevant source-of-truth surfaces"
                ),
            ),
            InventoryItem(
                name="Governed Harness / Turn Gate",
                layer="operating-policy",
                kind="product control layer",
                owns=(
                    "general-purpose turn classification, evidence sufficiency checks, execution "
                    "capsule construction, tool and stop gates, proof receipts, and benchmark "
                    "observation through the same product path used by host adapters"
                ),
                commands=(
                    "odylith turn-gate decide",
                    "odylith turn-gate tool-check",
                    "odylith turn-gate stop-check",
                ),
                anchors=(
                    "src/odylith/runtime/governed_harness/",
                    "odylith/registry/source/components/governed-harness/CURRENT_SPEC.md",
                ),
                activation=(
                    "turn-gate commands classify the proposed move, check tool admission, and preserve "
                    "proof receipts without delegating the hot path to a host model"
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
                activation=(
                    "host status commands report visible-intervention readiness while conversation timing, "
                    "proposal shaping, and Assist closeout remain product-owned"
                ),
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
                anchors=("src/odylith/runtime/discipline/", "src/odylith/runtime/governance/validate_discipline.py"),
                activation=(
                    "discipline status/check/validate stay local and deterministic, enforcing hard laws "
                    "without provider calls, subagents, broad scans, or benchmark execution on the hot path"
                ),
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
                anchors=("src/odylith/runtime/evaluation/",),
                activation=(
                    "benchmark profiles provide explicit proof for public claims while quick families keep "
                    "developer-loop validation bounded"
                ),
            ),
            InventoryItem(
                name="Taxonomies and FSMs",
                layer="governance",
                kind="integrity layer",
                owns=(
                    "controlled product vocabularies and lifecycle state machines, including "
                    "Casebook status transitions, broad bug-type taxonomy, benchmark family "
                    "taxonomy, proposal state vocabulary, and migration-normalized legacy tokens"
                ),
                commands=("odylith casebook validate", "odylith validate guidance-behavior"),
                anchors=(
                    "src/odylith/runtime/common/casebook_metadata.py",
                    "src/odylith/runtime/governance/casebook_source_validation.py",
                    "src/odylith/runtime/evaluation/odylith_benchmark_taxonomy.py",
                    "src/odylith/runtime/domain_intelligence/proposal_contract.py",
                ),
                activation=(
                    "casebook and guidance validators normalize controlled vocabularies and lifecycle FSMs "
                    "before legacy or arbitrary tokens can enter governed truth"
                ),
            ),
        ),
    ),
    (
        "Memory, orchestration, and lifecycle",
        (
            InventoryItem(
                name="Context Engine",
                layer="memory",
                kind="engine",
                owns=(
                    "startup grounding, anchor resolution, context dossiers, query packets, "
                    "daemon-backed recall, and execution-handshake packets for bounded turns"
                ),
                commands=("odylith start", "odylith context", "odylith query", "odylith context-engine"),
                anchors=("src/odylith/runtime/context_engine/",),
                activation=(
                    "startup and context commands build bounded packets, resolve anchors, attach execution "
                    "handshakes, and reuse daemon-backed recall where available"
                ),
            ),
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
                activation=(
                    "context/query/session-brief paths read projection memory and bounded packets instead "
                    "of broad-scanning project history every turn"
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
                anchors=(
                    "src/odylith/runtime/orchestration/subagent_router.py",
                    "src/odylith/runtime/orchestration/subagent_router_runtime_policy.py",
                ),
                activation=(
                    "router commands score bounded delegation eligibility from host support, route policy, "
                    "context packets, and validation needs without spawning by themselves"
                ),
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
                anchors=(
                    "src/odylith/runtime/orchestration/subagent_orchestrator.py",
                    "src/odylith/runtime/orchestration/subagent_orchestrator_subtasks_runtime.py",
                ),
                activation=(
                    "orchestrator commands shape multi-leaf work into explicit owner, goal, termination, "
                    "and validation contracts while host policy decides whether native spawn is admissible"
                ),
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
                anchors=("src/odylith/install/",),
                activation=(
                    "install, upgrade, repair, rollback, and migration-gate commands verify release assets, "
                    "write runtime ledgers, and preserve consumer-governance truth"
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
                activation=(
                    "release verification and runtime-integrity checks validate provenance, digests, and "
                    "managed hot files before the repo-local launcher trusts an activated runtime"
                ),
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
            InventoryItem(
                name="Operator Experience",
                layer="operator-ui",
                kind="experience layer",
                owns=(
                    "the cross-host operator UX: stdout-clean fast paths, visible intervention "
                    "fallbacks, dashboard navigation, browser-rendered governance surfaces, "
                    "greenfield handoff clarity, and low-latency status/diagnostic commands"
                ),
                commands=(
                    "odylith show",
                    "odylith dashboard refresh",
                    "odylith codex intervention-status",
                    "odylith claude intervention-status",
                ),
                anchors=(
                    "src/odylith/runtime/surfaces/",
                    "src/odylith/runtime/intervention_engine/",
                    "src/odylith/runtime/analysis_engine/show_capabilities.py",
                ),
                activation=(
                    "show, dashboard refresh, and host intervention-status commands keep first-turn UX, "
                    "browser surfaces, and visible recovery affordances low-latency and host-agnostic"
                ),
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
    activation = str(item.get("activation") or "").strip()
    if activation:
        lines.append(f"  Activation: {activation}.")
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
