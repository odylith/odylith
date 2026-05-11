"""Low-latency integrity checks for Odylith engine activation truth."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.analysis_engine import capability_inventory
from odylith.runtime.common import repo_path_resolver


@dataclass(frozen=True)
class EngineArea:
    area: str
    inventory_names: tuple[str, ...]
    required_commands: tuple[str, ...] = ()
    fits_as: str = ""
    purpose: str = ""
    requires_command_backing: bool = True
    requires_anchor_backing: bool = True
    requires_activation: bool = True


@dataclass(frozen=True)
class EngineFinding:
    severity: str
    area: str
    message: str
    action: str = ""


@dataclass(frozen=True)
class EngineHandshake:
    source: str
    target: str
    contract: str


ENGINE_AREAS: tuple[EngineArea, ...] = (
    EngineArea(
        "Analysis Engine",
        ("Analysis Engine",),
        ("odylith show", "odylith capabilities"),
        "repo and source discovery plus capability explanation",
    ),
    EngineArea(
        "Domain Intelligence",
        ("Domain Intelligence",),
        ("odylith greenfield propose", "odylith greenfield create"),
        "greenfield and project-shape intelligence before governed writes",
    ),
    EngineArea(
        "Delivery Intelligence",
        ("Delivery Intelligence",),
        ("odylith sync", "odylith governance-slice"),
        "unified delivery and readiness posture",
    ),
    EngineArea(
        "Tribunal",
        ("Tribunal",),
        ("odylith bug capture", "odylith greenfield propose"),
        "adjudication, diagnosis, and correction reasoning",
        purpose="Reasoning adjudication must stay explicit and evidence-gated.",
    ),
    EngineArea(
        "Reasoning Engine",
        ("Reasoning Engine",),
        ("odylith bug capture", "odylith greenfield propose"),
        "deterministic and provider-gated reasoning family",
    ),
    EngineArea(
        "Execution Engine",
        ("Execution Engine",),
        ("odylith context", "odylith governance-slice"),
        "next admissible move and execution handshake",
        purpose="Context handoff and admissibility must stay distinct.",
    ),
    EngineArea(
        "Proof State",
        ("Proof State",),
        ("odylith sync", "odylith governance-slice"),
        "claim tiers, blocker frontier, falsification, and proof posture",
    ),
    EngineArea(
        "Surface DAGs",
        ("Surface DAGs",),
        ("odylith sync", "odylith dashboard refresh"),
        "generated-surface dependency integrity",
    ),
    EngineArea(
        "Topology Integrity",
        ("Topology Integrity",),
        ("odylith validate topology-integrity",),
        "graph coherence across Radar, Registry, Atlas, and related surfaces",
    ),
    EngineArea(
        "Governance Engine",
        ("Governance Engine",),
        ("odylith sync", "odylith validate"),
        "governed writes, validation, and sync",
    ),
    EngineArea(
        "Governed Harness / Turn Gate",
        ("Governed Harness / Turn Gate",),
        ("odylith turn-gate decide", "odylith turn-gate tool-check", "odylith turn-gate stop-check"),
        "host turn classification, execution capsule, tool gates, and stop gates",
    ),
    EngineArea(
        "Intervention Engine",
        ("Governance Intervention Engine",),
        ("odylith codex intervention-status", "odylith claude intervention-status"),
        "visible Observation, Proposal, and Assist timing and voice",
    ),
    EngineArea(
        "Discipline Engine",
        ("Discipline Engine",),
        ("odylith discipline", "odylith validate discipline"),
        "hard laws, restraint, and credit-safe behavior",
    ),
    EngineArea(
        "Benchmark Harness",
        ("Benchmark Harness",),
        ("odylith benchmark",),
        "product proof and benchmark-backed claims",
    ),
    EngineArea(
        "Taxonomies and FSMs",
        ("Taxonomies and FSMs",),
        ("odylith casebook validate",),
        "controlled vocabularies and lifecycle legality",
    ),
    EngineArea(
        "Context Engine",
        ("Context Engine",),
        ("odylith start", "odylith context"),
        "grounding, packets, retrieval, and anchor resolution",
    ),
    EngineArea(
        "Memory Substrate",
        ("Memory Substrate",),
        ("odylith query", "odylith session-brief"),
        "projection memory, retrieval backend, and session memory",
    ),
    EngineArea(
        "Subagent Router",
        ("Subagent Router",),
        ("odylith subagent-router",),
        "route and delegation eligibility",
    ),
    EngineArea(
        "Subagent Orchestrator",
        ("Subagent Orchestrator",),
        ("odylith subagent-orchestrator",),
        "multi-leaf task decomposition and handoff",
    ),
    EngineArea(
        "Install / Upgrade / Migration Runtime",
        ("Install / Upgrade / Migration Runtime",),
        ("odylith install", "odylith upgrade", "odylith doctor"),
        "lifecycle, repair, rollback, and migration gates",
    ),
    EngineArea(
        "Security and Trust",
        ("Security and Trust",),
        ("odylith version", "odylith doctor"),
        "release integrity, provenance, SBOM, and digest trust",
    ),
    EngineArea(
        "Operator Experience",
        ("Operator Experience",),
        ("odylith show", "odylith dashboard refresh"),
        "cross-host UX, dashboard navigation, and visible recovery paths",
    ),
)

ENGINE_HANDSHAKES: tuple[EngineHandshake, ...] = (
    EngineHandshake(
        "Operator Experience",
        "Analysis Engine",
        "first-turn UX and show/help paths start from repo-local capability discovery",
    ),
    EngineHandshake(
        "Analysis Engine",
        "Domain Intelligence",
        "repo/source discovery feeds project-shape and greenfield interpretation",
    ),
    EngineHandshake(
        "Domain Intelligence",
        "Tribunal",
        "project-shape proposals are adjudicated before governed writes",
    ),
    EngineHandshake(
        "Reasoning Engine",
        "Tribunal",
        "deterministic and provider-gated reasoning feeds adjudication",
    ),
    EngineHandshake(
        "Discipline Engine",
        "Reasoning Engine",
        "hard laws constrain reasoning, credit, and provider use",
    ),
    EngineHandshake(
        "Tribunal",
        "Governance Engine",
        "accepted judgments gate Radar, Registry, Atlas, Casebook, Compass, and plan writes",
    ),
    EngineHandshake(
        "Taxonomies and FSMs",
        "Governance Engine",
        "controlled vocabularies and lifecycle legality constrain governed writes",
    ),
    EngineHandshake(
        "Governance Engine",
        "Surface DAGs",
        "owned writes trigger dependency-aware surface refresh",
    ),
    EngineHandshake(
        "Surface DAGs",
        "Topology Integrity",
        "generated-surface dependencies feed graph-coherence validation",
    ),
    EngineHandshake(
        "Surface DAGs",
        "Operator Experience",
        "fresh surfaces become dashboard navigation and visible recovery paths",
    ),
    EngineHandshake(
        "Topology Integrity",
        "Proof State",
        "graph coherence and gaps become claim, blocker, and falsification posture",
    ),
    EngineHandshake(
        "Benchmark Harness",
        "Proof State",
        "benchmark-backed results become product-proof claims",
    ),
    EngineHandshake(
        "Proof State",
        "Delivery Intelligence",
        "claim tiers, blockers, and proof gaps feed readiness posture",
    ),
    EngineHandshake(
        "Delivery Intelligence",
        "Execution Engine",
        "delivery posture constrains the next admissible move",
    ),
    EngineHandshake(
        "Memory Substrate",
        "Context Engine",
        "projection memory and retrieval backend feed bounded grounding packets",
    ),
    EngineHandshake(
        "Context Engine",
        "Execution Engine",
        "grounding packets and anchors constrain admissibility",
    ),
    EngineHandshake(
        "Execution Engine",
        "Governed Harness / Turn Gate",
        "admissible moves are checked at host turn, tool, and stop gates",
    ),
    EngineHandshake(
        "Governed Harness / Turn Gate",
        "Intervention Engine",
        "turn outcomes control visible Observation, Proposal, and Assist timing",
    ),
    EngineHandshake(
        "Subagent Router",
        "Subagent Orchestrator",
        "delegation eligibility shapes bounded multi-leaf work",
    ),
    EngineHandshake(
        "Subagent Orchestrator",
        "Execution Engine",
        "leaf handoffs return bounded work contracts and validation obligations",
    ),
    EngineHandshake(
        "Security and Trust",
        "Install / Upgrade / Migration Runtime",
        "provenance, digests, SBOM, and hot-file checks gate lifecycle changes",
    ),
    EngineHandshake(
        "Install / Upgrade / Migration Runtime",
        "Operator Experience",
        "install, repair, rollback, and migration status surface as visible recovery paths",
    ),
)

KNOWN_TOP_LEVEL_COMMANDS = frozenset(
    {
        "architecture",
        "atlas",
        "backlog",
        "benchmark",
        "bug",
        "capabilities",
        "casebook",
        "claude",
        "codex",
        "compass",
        "component",
        "context",
        "context-engine",
        "dashboard",
        "discipline",
        "doctor",
        "governance",
        "governance-slice",
        "greenfield",
        "install",
        "migrate-legacy-install",
        "on",
        "off",
        "plan",
        "program",
        "query",
        "radar",
        "registry",
        "release",
        "reinstall",
        "rollback",
        "session-brief",
        "show",
        "start",
        "subagent-orchestrator",
        "subagent-router",
        "sync",
        "turn-gate",
        "uninstall",
        "upgrade",
        "validate",
        "version",
        "wave",
    }
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith validate engine-integrity",
        description="Validate the low-latency engine inventory, activation commands, and source anchors.",
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit the report as JSON.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as failures. Useful for release proof, not required for quick local diagnostics.",
    )
    return parser.parse_args(argv)


def _resolve(repo_root: Path, token: str) -> Path:
    return repo_path_resolver.resolve_repo_path(repo_root=repo_root, value=token)


def _inventory_items() -> dict[str, dict[str, Any]]:
    payload = capability_inventory.inventory_payload()
    rows: dict[str, dict[str, Any]] = {}
    for group_key in ("engine_groups", "surface_groups"):
        for group in payload.get(group_key, []):  # type: ignore[union-attr]
            if not isinstance(group, Mapping):
                continue
            for raw_item in group.get("items", []):
                if not isinstance(raw_item, Mapping):
                    continue
                item = dict(raw_item)
                name = str(item.get("name", "")).strip()
                if name:
                    rows[name] = item
    return rows


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _top_level_command(command: str) -> str:
    parts = str(command or "").strip().split()
    if len(parts) < 2 or parts[0] != "odylith":
        return ""
    return parts[1]


def _unknown_top_level_commands(commands: Sequence[str]) -> list[str]:
    return [
        command
        for command in commands
        if (root := _top_level_command(command)) and root not in KNOWN_TOP_LEVEL_COMMANDS
    ]


def _anchor_status(repo_root: Path, anchors: Sequence[str]) -> tuple[list[str], list[str]]:
    existing: list[str] = []
    missing: list[str] = []
    for anchor in anchors:
        path = _resolve(repo_root, anchor)
        if path.exists():
            existing.append(anchor)
        else:
            missing.append(anchor)
    return existing, missing


def _item_findings(*, repo_root: Path, area: EngineArea, item: Mapping[str, Any]) -> list[EngineFinding]:
    findings: list[EngineFinding] = []
    name = str(item.get("name", "")).strip()
    owns = str(item.get("owns", "")).strip()
    activation = str(item.get("activation", "")).strip()
    commands = _string_tuple(item.get("commands"))
    anchors = _string_tuple(item.get("anchors"))
    if len(owns) < 80:
        findings.append(
            EngineFinding(
                "warning",
                area.area,
                f"`{name}` has a thin capability description.",
                "Give the inventory enough ownership detail for operators and agents to reason from it.",
            )
        )
    if not commands and not anchors:
        findings.append(
            EngineFinding(
                "error",
                area.area,
                f"`{name}` is neither command-backed nor anchor-backed.",
                "Add at least one operator command or canonical source anchor.",
            )
        )
    unknown_commands = _unknown_top_level_commands(commands)
    if unknown_commands:
        findings.append(
            EngineFinding(
                "error",
                area.area,
                f"`{name}` references unknown top-level command(s): {', '.join(unknown_commands)}.",
                "Fix the product-owned capability inventory before operators rely on the activation path.",
            )
        )
    if area.requires_activation and len(activation) < 80:
        findings.append(
            EngineFinding(
                "error",
                area.area,
                f"`{name}` is missing a concrete activation contract.",
                "State how this engine is activated or wired on the low-latency path, not only what it owns.",
            )
        )
    for required in area.required_commands:
        if required not in commands:
            findings.append(
                EngineFinding(
                    "error",
                    area.area,
                    f"`{name}` is missing required command `{required}`.",
                    "Update the capability inventory to expose the active operator path.",
                )
            )
    if anchors:
        existing, missing = _anchor_status(repo_root, anchors)
        if not existing:
            findings.append(
                EngineFinding(
                    "error",
                    area.area,
                    f"`{name}` declares anchors, but none exist in this checkout.",
                    f"Fix or remove stale anchors: {', '.join(missing)}",
                )
            )
        elif missing:
            findings.append(
                EngineFinding(
                    "warning",
                    area.area,
                    f"`{name}` has stale anchor references: {', '.join(missing)}.",
                    "Keep the product-owned inventory aligned with current source truth.",
            )
        )
    return findings


def _area_is_active(row: Mapping[str, Any]) -> bool:
    return bool(
        row.get("present")
        and row.get("command_backed")
        and row.get("anchor_backed")
        and row.get("activation_backed")
    )


def _handshake_report(area_rows: list[dict[str, Any]], findings: list[EngineFinding]) -> list[dict[str, Any]]:
    configured_areas = {area.area for area in ENGINE_AREAS}
    rows_by_area = {str(row.get("area", "")): row for row in area_rows}
    incoming: dict[str, list[str]] = {name: [] for name in rows_by_area}
    outgoing: dict[str, list[str]] = {name: [] for name in rows_by_area}
    integrated_areas: set[str] = set()
    handshakes: list[dict[str, Any]] = []

    for handshake in ENGINE_HANDSHAKES:
        if handshake.source not in configured_areas:
            findings.append(
                EngineFinding(
                    "error",
                    handshake.source,
                    f"Engine handshake references unknown source area `{handshake.source}`.",
                    "Fix `ENGINE_HANDSHAKES` so every source is a configured engine area.",
                )
            )
        if handshake.target not in configured_areas:
            findings.append(
                EngineFinding(
                    "error",
                    handshake.target,
                    f"Engine handshake references unknown target area `{handshake.target}`.",
                    "Fix `ENGINE_HANDSHAKES` so every target is a configured engine area.",
                )
            )

        source_row = rows_by_area.get(handshake.source)
        target_row = rows_by_area.get(handshake.target)
        wired = bool(source_row and target_row and _area_is_active(source_row) and _area_is_active(target_row))
        if source_row is not None:
            outgoing.setdefault(handshake.source, []).append(handshake.target)
        if target_row is not None:
            incoming.setdefault(handshake.target, []).append(handshake.source)
        if wired:
            integrated_areas.add(handshake.source)
            integrated_areas.add(handshake.target)
        else:
            findings.append(
                EngineFinding(
                    "error",
                    f"{handshake.source} -> {handshake.target}",
                    "Engine handshake is not fully backed by present, command-backed, anchor-backed, activated areas.",
                    "Repair the endpoint inventory rows before claiming the engine spine is active.",
                )
            )
        handshakes.append(
            {
                "source": handshake.source,
                "target": handshake.target,
                "contract": handshake.contract,
                "wired": wired,
            }
        )

    for row in area_rows:
        area = str(row.get("area", ""))
        row["handoff_in"] = incoming.get(area, [])
        row["handoff_out"] = outgoing.get(area, [])
        row["integration_backed"] = area in integrated_areas
        if not row["integration_backed"]:
            findings.append(
                EngineFinding(
                    "error",
                    area,
                    "Engine area is inventory-backed but not connected to the end-to-end handshake spine.",
                    "Add the missing upstream or downstream handshake before release proof relies on it.",
                )
            )

    return handshakes


def evaluate_engine_integrity(repo_root: Path, *, strict: bool = False) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    inventory = _inventory_items()
    findings: list[EngineFinding] = []
    area_rows: list[dict[str, Any]] = []
    command_backed = 0
    anchor_backed = 0
    activation_backed = 0
    for area in ENGINE_AREAS:
        missing = [name for name in area.inventory_names if name not in inventory]
        if missing:
            findings.append(
                EngineFinding(
                    "error",
                    area.area,
                    f"Missing capability inventory item(s): {', '.join(missing)}.",
                    "Add the missing engine row to `odylith capabilities`.",
                )
            )
        present_items = [inventory[name] for name in area.inventory_names if name in inventory]
        item_commands = sorted({cmd for item in present_items for cmd in _string_tuple(item.get("commands"))})
        item_anchors = sorted({anchor for item in present_items for anchor in _string_tuple(item.get("anchors"))})
        item_activations = sorted(
            {
                str(item.get("activation", "")).strip()
                for item in present_items
                if str(item.get("activation", "")).strip()
            }
        )
        if item_commands:
            command_backed += 1
        if item_anchors:
            anchor_backed += 1
        if item_activations and len(item_activations) == len(present_items):
            activation_backed += 1
        if present_items and area.requires_command_backing and not item_commands:
            findings.append(
                EngineFinding(
                    "error",
                    area.area,
                    "Requested engine area has no operator command backing.",
                    "Expose the low-latency activation path in `odylith capabilities`.",
                )
            )
        if present_items and area.requires_anchor_backing and not item_anchors:
            findings.append(
                EngineFinding(
                    "error",
                    area.area,
                    "Requested engine area has no source anchor backing.",
                    "Expose the canonical source owner in `odylith capabilities`.",
                )
            )
        for item in present_items:
            findings.extend(_item_findings(repo_root=root, area=area, item=item))
        area_rows.append(
            {
                "area": area.area,
                "inventory_names": list(area.inventory_names),
                "fits_as": area.fits_as,
                "present": not missing,
                "command_backed": bool(item_commands),
                "anchor_backed": bool(item_anchors),
                "activation_backed": bool(item_activations) and len(item_activations) == len(present_items),
                "commands": item_commands,
                "anchors": item_anchors,
                "activations": item_activations,
                "purpose": area.purpose,
            }
        )

    handshakes = _handshake_report(area_rows, findings)
    handshakes_wired = sum(1 for handshake in handshakes if handshake["wired"])
    integration_backed = sum(1 for row in area_rows if row["integration_backed"])
    counts = {
        "error": sum(1 for finding in findings if finding.severity == "error"),
        "warning": sum(1 for finding in findings if finding.severity == "warning"),
    }
    failed = counts["error"] > 0 or (strict and counts["warning"] > 0)
    return {
        "contract": "odylith.engine_integrity.v1",
        "status": "fail" if failed else "pass",
        "strict": strict,
        "repo_root": str(root),
        "areas_checked": len(ENGINE_AREAS),
        "areas_present": sum(1 for row in area_rows if row["present"]),
        "command_backed_areas": command_backed,
        "anchor_backed_areas": anchor_backed,
        "activation_backed_areas": activation_backed,
        "integration_backed_areas": integration_backed,
        "handshakes_checked": len(ENGINE_HANDSHAKES),
        "handshakes_wired": handshakes_wired,
        "handshakes": handshakes,
        "findings": [asdict(finding) for finding in findings],
        "counts": counts,
        "areas": area_rows,
        "recommended_fast_proof": [
            "odylith validate engine-integrity --repo-root .",
            "odylith validate discipline --repo-root .",
            "odylith validate guidance-behavior --repo-root .",
            "odylith validate topology-integrity --repo-root .",
        ],
    }


def _format_text(report: Mapping[str, Any]) -> str:
    counts = dict(report.get("counts", {})) if isinstance(report.get("counts"), Mapping) else {}
    lines = [
        "Odylith engine integrity report",
        f"- status: {report.get('status', 'fail')}",
        f"- areas: {report.get('areas_present', 0)}/{report.get('areas_checked', 0)} present",
        f"- command_backed: {report.get('command_backed_areas', 0)}",
        f"- anchor_backed: {report.get('anchor_backed_areas', 0)}",
        f"- activation_backed: {report.get('activation_backed_areas', 0)}",
        f"- integration_backed: {report.get('integration_backed_areas', 0)}",
        f"- handshakes: {report.get('handshakes_wired', 0)}/{report.get('handshakes_checked', 0)} wired",
        f"- findings: {int(counts.get('error', 0) or 0)} error(s), {int(counts.get('warning', 0) or 0)} warning(s)",
    ]
    findings = report.get("findings", [])
    if isinstance(findings, list) and findings:
        lines.append("")
        for raw in findings:
            if not isinstance(raw, Mapping):
                continue
            lines.append(
                f"{str(raw.get('severity', 'warning')).upper()} {raw.get('area', '-')}: {raw.get('message', '')}"
            )
            action = str(raw.get("action", "")).strip()
            if action:
                lines.append(f"  action: {action}")
    else:
        lines.append("- result: all requested engine areas are inventory-backed and have active command or source anchors.")
    areas = report.get("areas", [])
    if isinstance(areas, list) and areas:
        lines.append("")
        lines.append("Engine spine")
        for raw in areas:
            if not isinstance(raw, Mapping):
                continue
            fits_as = str(raw.get("fits_as", "")).strip()
            suffix = f" - {fits_as}" if fits_as else ""
            lines.append(f"- {raw.get('area', '-')}{suffix}")
    handshakes = report.get("handshakes", [])
    if isinstance(handshakes, list) and handshakes:
        lines.append("")
        lines.append("Engine handshakes")
        for raw in handshakes:
            if not isinstance(raw, Mapping):
                continue
            status = "wired" if raw.get("wired") else "unwired"
            lines.append(
                f"- {raw.get('source', '-')} -> {raw.get('target', '-')} ({status}): {raw.get('contract', '')}"
            )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    report = evaluate_engine_integrity(Path(args.repo_root), strict=bool(args.strict))
    if args.as_json:
        print(json.dumps(report, indent=2, sort_keys=False))
    else:
        print(_format_text(report))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
