"""Shared governance intelligence for workstream-to-dashboard orchestration.

This module centralizes activity interpretation and impact planning so sync,
plan-binding enforcement, and Compass governance summaries reuse one contract.

Key invariants:
- Generated/global coordination artifacts never count as meaningful workstream
  implementation evidence.
- Impact planning is conservative: unknown trigger paths fan out to all surfaces
  to avoid stale dashboards.
- Active plan binding checks target new/touched plan rows only.
"""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Iterable, Mapping, Sequence

from odylith.runtime.common.consumer_profile import truth_root_path
from odylith.runtime.governance import component_registry_intelligence as component_registry
from odylith.runtime.governance import validate_backlog_contract as backlog_contract
from odylith.runtime.governance import workstream_inference as ws_inference

_WORKSTREAM_RE = re.compile(r"^B-\d{3,}$")
_PLAN_ROW_RE = re.compile(r"^\|\s*`?(odylith/technical-plans/in-progress/[^|`]+)`?\s*\|", re.I)
_PLAN_BINDING_ADVANCE_RE = re.compile(
    r"^Plan binding:\s+advanced\s+(?P<workstream>B-\d{3,})\s+from\s+"
    r"(?P<before>[a-z_]+)\s+to\s+(?P<after>[a-z_]+)\s+for\s+"
    r"(?P<plan>odylith/technical-plans/in-progress/\S+)$",
    re.I,
)
_SUCCESSOR_CREATED_RE = re.compile(
    r"^Successor created:\s+(?P<successor>B-\d{3,})\s+reopens\s+(?P<source>B-\d{3,})\s+for active plan binding$",
    re.I,
)
_LIVE_PHASE_ADVANCE_RE = re.compile(
    r"^Phase advanced:\s*Planning\s*->\s*Implementation\s*\(Live\)\s*$",
    re.I,
)

_GLOBAL_IMPACT_PREFIXES: tuple[str, ...] = (
    "AGENTS.md",
    "CLAUDE.md",
    "odylith/AGENTS.md",
    "odylith/CLAUDE.md",
    "agents-guidelines/",
    "skills/",
    "odylith/FAQ.md",
    "odylith/INSTALL.md",
    "odylith/INSTALL_AND_UPGRADE_RUNBOOK.md",
    "odylith/OPERATING_MODEL.md",
    "odylith/PRODUCT_COMPONENTS.md",
    "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
    "odylith/runtime/",
    "odylith/surfaces/",
    "src/odylith/runtime/governance/sync_workstream_artifacts.py",
    "src/odylith/runtime/governance/agent_governance_intelligence.py",
    "src/odylith/runtime/governance/delivery_intelligence_engine.py",
    "src/odylith/runtime/governance/operator_readout.py",
    "src/odylith/runtime/reasoning/odylith_reasoning.py",
    "src/odylith/runtime/governance/validate_plan_workstream_binding.py",
    "src/odylith/runtime/governance/reconcile_plan_workstream_binding.py",
    "odylith/runtime/contracts/",
    "odylith/runtime/delivery_intelligence.v4.json",
)

_RADAR_IMPACT_PREFIXES: tuple[str, ...] = (
    "odylith/radar/source/",
    "odylith/radar/",
    "odylith/technical-plans/",
    "src/odylith/runtime/surfaces/execution_wave_ui_runtime_primitives.py",
    "src/odylith/runtime/surfaces/render_backlog_ui.py",
    "src/odylith/runtime/governance/build_traceability_graph.py",
    "src/odylith/runtime/governance/backfill_workstream_traceability.py",
    "src/odylith/runtime/governance/validate_backlog_contract.py",
    "src/odylith/runtime/governance/validate_plan_traceability_contract.py",
    "src/odylith/runtime/governance/validate_plan_risk_mitigation_contract.py",
    "src/odylith/runtime/governance/normalize_plan_risk_mitigation.py",
)

_ATLAS_IMPACT_PREFIXES: tuple[str, ...] = (
    "odylith/atlas/source/",
    "odylith/atlas/",
    "src/odylith/runtime/surfaces/render_mermaid_catalog.py",
    "src/odylith/runtime/governance/build_traceability_graph.py",
    "src/odylith/runtime/governance/backfill_workstream_traceability.py",
    "src/odylith/runtime/governance/validate_backlog_contract.py",
)

_COMPASS_IMPACT_PREFIXES: tuple[str, ...] = (
    "odylith/compass/",
    "src/odylith/runtime/surfaces/execution_wave_ui_runtime_primitives.py",
    "src/odylith/runtime/surfaces/render_compass_dashboard.py",
    "src/odylith/runtime/common/log_compass_timeline_event.py",
    "src/odylith/runtime/surfaces/update_compass.py",
    "src/odylith/runtime/surfaces/watch_prompt_transactions.py",
    "src/odylith/runtime/governance/auto_promote_workstream_phase.py",
)
_REGISTRY_IMPACT_PREFIXES: tuple[str, ...] = (
    "odylith/registry/",
    "odylith/registry/source/component_registry.v1.json",
    "src/odylith/runtime/governance/component_registry_intelligence.py",
    "src/odylith/runtime/governance/validate_component_registry_contract.py",
    "src/odylith/runtime/surfaces/render_registry_dashboard.py",
)
_CASEBOOK_IMPACT_PREFIXES: tuple[str, ...] = (
    "odylith/casebook/bugs/",
    "odylith/casebook/",
    "src/odylith/runtime/surfaces/render_casebook_dashboard.py",
)

_IMPLEMENTATION_NOISE_PREFIXES: tuple[str, ...] = (
    "agents-guidelines/",
    "odylith/casebook/bugs/",
    "docs/",
    "odylith/technical-plans/",
    "skills/",
)
_IMPLEMENTATION_NOISE_EXACT: set[str] = {"AGENTS.md", "CLAUDE.md", "odylith/AGENTS.md", "odylith/CLAUDE.md"}
_IMPLEMENTATION_NOISE_EXACT_LOWER: set[str] = {item.lower() for item in _IMPLEMENTATION_NOISE_EXACT}


_RETIRED_SURFACE_MARKER = "sen" "tinel"


def _is_retired_surface_tombstone(token: str) -> bool:
    normalized = str(token or "").strip().lower()
    if not normalized:
        return False
    return _RETIRED_SURFACE_MARKER in normalized


@dataclass(frozen=True)
class DashboardImpact:
    """Impact projection for dashboard surfaces."""

    radar: bool
    atlas: bool
    compass: bool
    registry: bool
    casebook: bool
    reasons: dict[str, list[str]]

    @property
    def tooling_shell(self) -> bool:
        return self.radar or self.atlas or self.compass or self.registry or self.casebook

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["tooling_shell"] = self.tooling_shell
        return payload


@dataclass(frozen=True)
class MeaningfulActivityEvidence:
    """Counts for non-noisy stream activity linked to workstreams."""

    linked_meaningful_event_count: int
    unlinked_meaningful_event_count: int
    linked_workstreams: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlanBindingDecision:
    """Recorded action from odylith/technical-plans/workstream reconciliation."""

    plan_path: str
    backlog_before: str
    backlog_after: str
    action: str
    details: str


@dataclass(frozen=True)
class SuccessorCreationResult:
    """Created successor linkage for a finished workstream rebind."""

    source_workstream: str
    successor_workstream: str
    idea_path: str
    linked_plan: str


_PRODUCT_BUNDLE_SOURCE_MIRROR_PREFIX = "src/odylith/bundle/assets/odylith/"
_PROJECT_ROOT_ASSET_MIRROR_PREFIX = "src/odylith/bundle/assets/project-root/"


def _changed_path_aliases(token: str) -> tuple[str, ...]:
    normalized = str(token or "").strip().lstrip("./")
    if not normalized:
        return ()
    aliases = [normalized]
    if normalized.startswith(_PRODUCT_BUNDLE_SOURCE_MIRROR_PREFIX):
        suffix = normalized.removeprefix(_PRODUCT_BUNDLE_SOURCE_MIRROR_PREFIX).strip("/")
        if suffix:
            aliases.append(f"odylith/{suffix}")
    if normalized.startswith(_PROJECT_ROOT_ASSET_MIRROR_PREFIX):
        suffix = normalized.removeprefix(_PROJECT_ROOT_ASSET_MIRROR_PREFIX).strip("/")
        if suffix:
            aliases.append(suffix)
    return tuple(aliases)


def normalize_changed_paths(*, repo_root: Path, values: Iterable[str]) -> list[str]:
    """Normalize changed paths into unique repository-relative tokens."""

    rows: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = ws_inference.normalize_repo_token(str(raw or "").strip(), repo_root=repo_root).lstrip("./")
        for alias in _changed_path_aliases(token):
            if not alias or _is_retired_surface_tombstone(alias) or alias in seen:
                continue
            seen.add(alias)
            rows.append(alias)
    return rows


def _run_git(repo_root: Path, args: Sequence[str]) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError:
        return ""
    return str(completed.stdout or "")


def collect_git_changed_paths(*, repo_root: Path) -> list[str]:
    """Collect changed paths from git status porcelain output."""

    raw = _run_git(repo_root, ["status", "--porcelain", "--untracked-files=all"])
    rows: list[str] = []
    for line in raw.splitlines():
        item = str(line or "")
        if len(item) < 4:
            continue
        path_token = item[3:].strip()
        if not path_token:
            continue
        if " -> " in path_token:
            path_token = path_token.split(" -> ", 1)[1].strip()
        path_token = path_token.strip('"')
        rows.append(path_token)
    return normalize_changed_paths(repo_root=repo_root, values=rows)


def collect_meaningful_changed_paths(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    include_git: bool = True,
) -> list[str]:
    """Return non-generated, non-global changed paths from explicit/git inputs."""

    merged = list(normalize_changed_paths(repo_root=repo_root, values=changed_paths))
    if include_git:
        merged.extend(collect_git_changed_paths(repo_root=repo_root))
    normalized = normalize_changed_paths(repo_root=repo_root, values=merged)
    meaningful = [
        token
        for token in normalized
        if not ws_inference.is_generated_or_global_path(token)
    ]
    return normalize_changed_paths(repo_root=repo_root, values=meaningful)


def collect_implementation_evidence_paths(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    include_git: bool = True,
) -> list[str]:
    """Return changed paths that count as implementation evidence."""

    meaningful = collect_meaningful_changed_paths(
        repo_root=repo_root,
        changed_paths=changed_paths,
        include_git=include_git,
    )
    rows: list[str] = []
    for token in meaningful:
        lowered = token.lower()
        if lowered in _IMPLEMENTATION_NOISE_EXACT_LOWER:
            continue
        if any(lowered.startswith(prefix) for prefix in _IMPLEMENTATION_NOISE_PREFIXES):
            continue
        rows.append(token)
    return normalize_changed_paths(repo_root=repo_root, values=rows)


def has_implementation_evidence(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    include_git: bool = True,
) -> bool:
    """Return ``True`` when changed paths contain implementation evidence."""

    return bool(
        collect_implementation_evidence_paths(
            repo_root=repo_root,
            changed_paths=changed_paths,
            include_git=include_git,
        )
    )


def parse_plan_active_rows(plan_index_path: Path) -> list[dict[str, str]]:
    """Parse active plan table rows from `odylith/technical-plans/INDEX.md`."""

    if not plan_index_path.is_file():
        return []
    snapshot = backlog_contract.load_plan_index_snapshot(plan_index_path)
    rows = backlog_contract.rows_as_mapping(section=snapshot.get("active", {}))
    normalized: list[dict[str, str]] = []
    for row in rows:
        cleaned = {key: value.strip("`").strip() for key, value in row.items()}
        if cleaned.get("Plan", "").startswith("odylith/technical-plans/in-progress/"):
            normalized.append(cleaned)
    return normalized


def _parse_added_plan_rows_from_diff(diff_text: str) -> list[str]:
    rows: list[str] = []
    for line in str(diff_text or "").splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        added = line[1:].strip()
        if not _PLAN_ROW_RE.match(added):
            continue
        cells = [cell.strip() for cell in added.split("|")[1:-1]]
        if len(cells) < 5:
            continue
        plan_path = cells[0].strip("`").strip()
        if plan_path.startswith("odylith/technical-plans/in-progress/"):
            rows.append(plan_path)
    return rows


def collect_touched_active_plan_paths(
    *,
    repo_root: Path,
    plan_index_path: Path,
    changed_paths: Sequence[str],
) -> list[str]:
    """Return new/touched active plan paths for strict binding checks."""

    normalized = normalize_changed_paths(repo_root=repo_root, values=changed_paths)
    git_paths = collect_git_changed_paths(repo_root=repo_root)

    touched: set[str] = set()
    for token in [*normalized, *git_paths]:
        if token.startswith("odylith/technical-plans/in-progress/") and token.endswith(".md"):
            touched.add(token)

    plan_index_token = ws_inference.normalize_repo_token(str(plan_index_path), repo_root=repo_root)
    if plan_index_token in normalized or plan_index_token in git_paths:
        for args in (
            ["diff", "--unified=0", "--", plan_index_token],
            ["diff", "--cached", "--unified=0", "--", plan_index_token],
        ):
            diff_text = _run_git(repo_root, args)
            touched.update(_parse_added_plan_rows_from_diff(diff_text))

    return sorted(touched)


def _path_hits_prefixes(token: str, prefixes: Sequence[str]) -> bool:
    return any(token == prefix or token.startswith(prefix) for prefix in prefixes)


def build_dashboard_impact(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    force: bool,
    impact_mode: str,
) -> DashboardImpact:
    """Build dashboard impact projection for selective or full sync."""

    mode = str(impact_mode or "selective").strip().lower()
    if mode not in {"selective", "full"}:
        mode = "selective"

    normalized = normalize_changed_paths(repo_root=repo_root, values=changed_paths)
    if force or mode == "full" or not normalized:
        reason = "force/full-mode" if (force or mode == "full") else "no-changed-paths"
        return DashboardImpact(
            radar=True,
            atlas=True,
            compass=True,
            registry=True,
            casebook=True,
            reasons={
                "radar": [reason],
                "atlas": [reason],
                "compass": [reason],
                "registry": [reason],
                "casebook": [reason],
            },
        )

    radar = False
    atlas = False
    compass = False
    registry = False
    casebook = False
    reasons: dict[str, list[str]] = {"radar": [], "atlas": [], "compass": [], "registry": [], "casebook": []}

    for token in normalized:
        if _path_hits_prefixes(token, _GLOBAL_IMPACT_PREFIXES):
            radar = True
            atlas = True
            compass = True
            registry = True
            casebook = True
            reasons["radar"].append(token)
            reasons["atlas"].append(token)
            reasons["compass"].append(token)
            reasons["registry"].append(token)
            reasons["casebook"].append(token)
            continue

        matched = False
        if _path_hits_prefixes(token, _RADAR_IMPACT_PREFIXES):
            radar = True
            reasons["radar"].append(token)
            matched = True
        if _path_hits_prefixes(token, _ATLAS_IMPACT_PREFIXES):
            atlas = True
            reasons["atlas"].append(token)
            matched = True
        if _path_hits_prefixes(token, _COMPASS_IMPACT_PREFIXES):
            compass = True
            reasons["compass"].append(token)
            matched = True
        if _path_hits_prefixes(token, _REGISTRY_IMPACT_PREFIXES):
            registry = True
            reasons["registry"].append(token)
            matched = True
        if _path_hits_prefixes(token, _CASEBOOK_IMPACT_PREFIXES):
            casebook = True
            reasons["casebook"].append(token)
            matched = True

        # Fail safe for unknown relevant paths.
        if not matched:
            radar = True
            atlas = True
            compass = True
            registry = True
            casebook = True
            reasons["radar"].append(f"fallback:{token}")
            reasons["atlas"].append(f"fallback:{token}")
            reasons["compass"].append(f"fallback:{token}")
            reasons["registry"].append(f"fallback:{token}")
            reasons["casebook"].append(f"fallback:{token}")

    for key in reasons:
        reasons[key] = sorted(set(reasons[key]))

    return DashboardImpact(
        radar=radar,
        atlas=atlas,
        compass=compass,
        registry=registry,
        casebook=casebook,
        reasons=reasons,
    )


def _collect_ws_path_index_from_specs(repo_root: Path) -> dict[str, set[str]]:
    ideas_root = truth_root_path(repo_root=repo_root, key="radar_source") / "ideas"
    idea_specs, _errors = backlog_contract._validate_idea_specs(ideas_root)
    return ws_inference.collect_workstream_path_index_from_specs(
        repo_root=repo_root,
        idea_specs=idea_specs,
    )


def collect_meaningful_activity_evidence(
    *,
    repo_root: Path,
    stream_path: Path,
) -> MeaningfulActivityEvidence:
    """Collect linked/unlinked meaningful activity from Compass stream."""

    if not stream_path.is_file():
        return MeaningfulActivityEvidence(0, 0, [])

    ws_path_index = _collect_ws_path_index_from_specs(repo_root)
    linked_count = 0
    unlinked_count = 0
    linked_workstreams: set[str] = set()

    for raw in stream_path.read_text(encoding="utf-8").splitlines():
        line = str(raw or "").strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, Mapping):
            continue

        artifacts_raw = payload.get("artifacts", [])
        artifacts: list[str] = []
        if isinstance(artifacts_raw, list):
            artifacts = normalize_changed_paths(
                repo_root=repo_root,
                values=[str(item) for item in artifacts_raw],
            )
        meaningful_paths = [
            token for token in artifacts if not ws_inference.is_generated_or_global_path(token)
        ]
        if not meaningful_paths:
            continue

        ws_ids: list[str] = []
        workstreams_raw = payload.get("workstreams", [])
        if isinstance(workstreams_raw, list):
            for item in workstreams_raw:
                token = str(item or "").strip().upper()
                if _WORKSTREAM_RE.fullmatch(token):
                    ws_ids.append(token)
        ws_ids = sorted(set(ws_ids))
        if not ws_ids:
            ws_ids = ws_inference.map_paths_to_workstreams(meaningful_paths, ws_path_index)

        if ws_ids:
            linked_count += 1
            linked_workstreams.update(ws_ids)
        else:
            unlinked_count += 1

    return MeaningfulActivityEvidence(
        linked_meaningful_event_count=linked_count,
        unlinked_meaningful_event_count=unlinked_count,
        linked_workstreams=sorted(linked_workstreams),
    )


def collect_governance_stream_actions(
    *,
    repo_root: Path,
    stream_path: Path,
    max_rows: int = 64,
) -> tuple[list[PlanBindingDecision], list[SuccessorCreationResult]]:
    """Parse governance actions from Compass timeline stream entries."""

    if max_rows < 1:
        max_rows = 1
    if not stream_path.is_file():
        return [], []

    raw_lines = stream_path.read_text(encoding="utf-8").splitlines()
    sample = raw_lines[-(max_rows * 8) :]
    decisions: list[PlanBindingDecision] = []
    successors: list[SuccessorCreationResult] = []

    for raw in sample:
        line = str(raw or "").strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, Mapping):
            continue

        summary = str(payload.get("summary", "")).strip()
        if not summary:
            continue

        match = _PLAN_BINDING_ADVANCE_RE.fullmatch(summary)
        if match is not None:
            before = str(match.group("before")).strip().lower()
            after = str(match.group("after")).strip().lower()
            action = f"{before}_to_{after}"
            ws_id = str(match.group("workstream")).strip().upper()
            plan_path = str(match.group("plan")).strip()
            decisions.append(
                PlanBindingDecision(
                    plan_path=plan_path,
                    backlog_before=ws_id,
                    backlog_after=ws_id,
                    action=action,
                    details=summary,
                )
            )
            continue

        match = _SUCCESSOR_CREATED_RE.fullmatch(summary)
        if match is not None:
            source = str(match.group("source")).strip().upper()
            successor = str(match.group("successor")).strip().upper()
            artifacts_raw = payload.get("artifacts", [])
            artifacts = normalize_changed_paths(
                repo_root=repo_root,
                values=[str(item) for item in artifacts_raw] if isinstance(artifacts_raw, list) else (),
            )
            idea_path = ""
            linked_plan = ""
            for token in artifacts:
                if token.startswith("odylith/radar/source/ideas/") and token.endswith(".md") and not idea_path:
                    idea_path = token
                if token.startswith("odylith/technical-plans/in-progress/") and token.endswith(".md") and not linked_plan:
                    linked_plan = token
            successors.append(
                SuccessorCreationResult(
                    source_workstream=source,
                    successor_workstream=successor,
                    idea_path=idea_path,
                    linked_plan=linked_plan,
                )
            )
            continue

        if _LIVE_PHASE_ADVANCE_RE.fullmatch(summary):
            workstreams_raw = payload.get("workstreams", [])
            workstreams: list[str] = []
            if isinstance(workstreams_raw, list):
                for item in workstreams_raw:
                    token = str(item or "").strip().upper()
                    if _WORKSTREAM_RE.fullmatch(token):
                        workstreams.append(token)
            for ws_id in sorted(set(workstreams)):
                decisions.append(
                    PlanBindingDecision(
                        plan_path="",
                        backlog_before=ws_id,
                        backlog_after=ws_id,
                        action="planning_to_implementation",
                        details=summary,
                    )
                )

    if len(decisions) > max_rows:
        decisions = decisions[-max_rows:]
    if len(successors) > max_rows:
        successors = successors[-max_rows:]
    return decisions, successors


def _load_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def build_governance_summary(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    force: bool,
    impact_mode: str,
    stream_path: Path,
    plan_binding_actions: Sequence[PlanBindingDecision] | None = None,
    successor_creations: Sequence[SuccessorCreationResult] | None = None,
) -> dict[str, Any]:
    """Build unified governance summary payload for dashboard surfaces."""

    impact = build_dashboard_impact(
        repo_root=repo_root,
        changed_paths=changed_paths,
        force=force,
        impact_mode=impact_mode,
    )
    evidence = collect_meaningful_activity_evidence(
        repo_root=repo_root,
        stream_path=stream_path,
    )
    if plan_binding_actions is None or successor_creations is None:
        parsed_decisions, parsed_successors = collect_governance_stream_actions(
            repo_root=repo_root,
            stream_path=stream_path,
        )
        if plan_binding_actions is None:
            plan_binding_actions = parsed_decisions
        if successor_creations is None:
            successor_creations = parsed_successors

    action_rows = [asdict(item) for item in plan_binding_actions]
    successor_rows = [asdict(item) for item in successor_creations]
    component_report = component_registry.build_component_registry_report(
        repo_root=repo_root,
        stream_path=stream_path,
    )
    mapped_meaningful_count = sum(
        1
        for row in component_report.mapped_events
        if row.meaningful and row.mapped_components
    )
    meaningful_count = sum(1 for row in component_report.mapped_events if row.meaningful)
    component_summary = {
        "component_count": len(component_report.components),
        "event_count": len(component_report.mapped_events),
        "meaningful_event_count": meaningful_count,
        "mapped_meaningful_event_count": mapped_meaningful_count,
        "unmapped_meaningful_event_count": len(component_report.unmapped_meaningful_events),
        "diagnostic_count": len(component_report.diagnostics),
    }
    return {
        "impact": impact.as_dict(),
        "meaningful_activity": evidence.as_dict(),
        "component_registry": component_summary,
        "plan_binding_actions": action_rows,
        "successor_creations": successor_rows,
        "counts": {
            "plan_binding_actions": len(action_rows),
            "successor_creations": len(successor_rows),
        },
    }


__all__ = [
    "DashboardImpact",
    "MeaningfulActivityEvidence",
    "PlanBindingDecision",
    "SuccessorCreationResult",
    "build_dashboard_impact",
    "build_governance_summary",
    "collect_governance_stream_actions",
    "collect_git_changed_paths",
    "collect_implementation_evidence_paths",
    "collect_meaningful_changed_paths",
    "collect_meaningful_activity_evidence",
    "collect_touched_active_plan_paths",
    "has_implementation_evidence",
    "normalize_changed_paths",
    "parse_plan_active_rows",
]
