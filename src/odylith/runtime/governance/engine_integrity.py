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
    purpose: str = ""


@dataclass(frozen=True)
class EngineFinding:
    severity: str
    area: str
    message: str
    action: str = ""


ENGINE_AREAS: tuple[EngineArea, ...] = (
    EngineArea("Context Engine", ("Context Engine",), ("odylith start", "odylith context")),
    EngineArea("Execution Engine", ("Execution Engine",), purpose="Context handoff and admissibility must stay distinct."),
    EngineArea("Tribunal", ("Tribunal",), purpose="Reasoning adjudication must stay explicit and evidence-gated."),
    EngineArea(
        "Intervention Engine",
        ("Governance Intervention Engine",),
        ("odylith codex intervention-status", "odylith claude intervention-status"),
    ),
    EngineArea("Governance", ("Governance Engine",), ("odylith sync", "odylith validate")),
    EngineArea("Subagent Orchestration", ("Subagent Router", "Subagent Orchestrator")),
    EngineArea("Discipline", ("Discipline Engine",), ("odylith discipline", "odylith validate discipline")),
    EngineArea("Surface DAGs", ("Surface DAGs",)),
    EngineArea("Delivery", ("Delivery Intelligence",)),
    EngineArea("Analysis", ("Analysis Engine",), ("odylith show", "odylith capabilities")),
    EngineArea("Memory Substrate", ("Memory Substrate",), ("odylith query", "odylith session-brief")),
    EngineArea("Topology", ("Topology Integrity",), ("odylith validate topology-integrity",)),
    EngineArea("Taxonomies and FSMs", ("Taxonomies and FSMs",), ("odylith casebook validate",)),
    EngineArea(
        "Greenfield proposals and domain intelligence",
        ("Domain Intelligence",),
        ("odylith greenfield propose", "odylith greenfield create"),
    ),
    EngineArea("Overall UX", ("Operator Experience",), ("odylith dashboard refresh",)),
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


def evaluate_engine_integrity(repo_root: Path, *, strict: bool = False) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    inventory = _inventory_items()
    findings: list[EngineFinding] = []
    area_rows: list[dict[str, Any]] = []
    command_backed = 0
    anchor_backed = 0
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
        if item_commands:
            command_backed += 1
        if item_anchors:
            anchor_backed += 1
        for item in present_items:
            findings.extend(_item_findings(repo_root=root, area=area, item=item))
        area_rows.append(
            {
                "area": area.area,
                "inventory_names": list(area.inventory_names),
                "present": not missing,
                "command_backed": bool(item_commands),
                "anchor_backed": bool(item_anchors),
                "commands": item_commands,
                "anchors": item_anchors,
                "purpose": area.purpose,
            }
        )

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
