from __future__ import annotations

import json
from typing import Any, Mapping
from typing import Sequence

from odylith.runtime.governance import component_registry_intelligence as component_registry


_FULL_DETAIL_LEVELS = {"", "full"}


def build_registry_detail(
    *,
    snapshot: Mapping[str, Any],
    component_id: str,
    detail_level: str = "full",
) -> dict[str, Any] | None:
    token = str(component_id or "").strip().lower()
    if not token:
        return None
    report = snapshot.get("report")
    if not isinstance(report, component_registry.ComponentRegistryReport):
        return None
    entry = report.components.get(token)
    if entry is None:
        return None
    spec_snapshot_lookup = snapshot.get("spec_snapshots", {})
    spec_snapshot = (
        spec_snapshot_lookup.get(token)
        if isinstance(spec_snapshot_lookup, Mapping)
        else None
    )
    if not isinstance(spec_snapshot, component_registry.ComponentSpecSnapshot):
        spec_snapshot = component_registry.ComponentSpecSnapshot(
            title="",
            last_updated="",
            feature_history=[],
            markdown="",
        )
    traceability_lookup = snapshot.get("traceability", {})
    traceability = (
        dict(traceability_lookup.get(token, {}))
        if isinstance(traceability_lookup, Mapping) and isinstance(traceability_lookup.get(token), Mapping)
        else {"runbooks": [], "developer_docs": [], "code_references": []}
    )
    normalized_detail_level = str(detail_level or "").strip().lower()
    timeline = []
    if normalized_detail_level in _FULL_DETAIL_LEVELS:
        timelines = component_registry.build_component_timelines(
            component_index=report.components,
            mapped_events=report.mapped_events,
        )
        timeline = list(timelines.get(token, []))
    coverage = report.forensic_coverage.get(
        token,
        component_registry.ComponentForensicCoverage(
            status="tracked_but_evidence_empty",
            timeline_event_count=0,
            explicit_event_count=0,
            recent_path_match_count=0,
            mapped_workstream_evidence_count=0,
            spec_history_event_count=0,
            empty_reasons=[],
        ),
    )
    return {
        "component": entry,
        "spec_snapshot": spec_snapshot,
        "traceability": traceability,
        "timeline": timeline,
        "forensic_coverage": coverage.as_dict(),
    }


def build_runtime_registry_detail(
    *,
    entry: component_registry.ComponentEntry,
    spec_row: Mapping[str, Any] | None,
    trace_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    feature_history: list[dict[str, Any]] = []
    title = ""
    last_updated = ""
    markdown = ""
    skill_trigger_tiers: dict[str, list[dict[str, Any]]] = {}
    skill_trigger_structure = "legacy"
    validation_playbook_commands: list[dict[str, str]] = []
    if isinstance(spec_row, Mapping):
        feature_history_payload = json.loads(str(spec_row.get("feature_history_json", "[]") or "[]"))
        skill_tiers_payload = json.loads(str(spec_row.get("skill_trigger_tiers_json", "{}") or "{}"))
        playbook_payload = json.loads(str(spec_row.get("validation_playbook_commands_json", "[]") or "[]"))
        feature_history = (
            [dict(item) for item in feature_history_payload if isinstance(item, Mapping)]
            if isinstance(feature_history_payload, list)
            else []
        )
        title = str(spec_row.get("title", "")).strip()
        last_updated = str(spec_row.get("last_updated", "")).strip()
        markdown = str(spec_row.get("markdown", "") or "")
        skill_trigger_tiers = (
            dict(skill_tiers_payload)
            if isinstance(skill_tiers_payload, Mapping)
            else {}
        )
        skill_trigger_structure = str(spec_row.get("skill_trigger_structure", "")).strip() or "legacy"
        validation_playbook_commands = (
            [dict(item) for item in playbook_payload if isinstance(item, Mapping)]
            if isinstance(playbook_payload, list)
            else []
        )
    spec_snapshot = component_registry.ComponentSpecSnapshot(
        title=title,
        last_updated=last_updated,
        feature_history=feature_history,
        markdown=markdown,
        skill_trigger_tiers=skill_trigger_tiers,
        skill_trigger_structure=skill_trigger_structure,
        validation_playbook_commands=validation_playbook_commands,
    )
    traceability: dict[str, list[str]] = {
        "runbooks": [],
        "developer_docs": [],
        "code_references": [],
    }
    for row in trace_rows:
        if not isinstance(row, Mapping):
            continue
        bucket = str(row.get("bucket", "")).strip()
        path = str(row.get("path", "")).strip()
        if not bucket or not path:
            continue
        traceability.setdefault(bucket, []).append(path)
    for bucket, values in traceability.items():
        seen: set[str] = set()
        deduped: list[str] = []
        for raw in values:
            token = str(raw).strip()
            if not token or token in seen:
                continue
            seen.add(token)
            deduped.append(token)
        traceability[bucket] = deduped
    spec_history_event_count = len(feature_history)
    coverage = component_registry.ComponentForensicCoverage(
        status="baseline_forensic_only" if spec_history_event_count > 0 else "tracked_but_evidence_empty",
        timeline_event_count=spec_history_event_count,
        explicit_event_count=0,
        recent_path_match_count=0,
        mapped_workstream_evidence_count=0,
        spec_history_event_count=spec_history_event_count,
        empty_reasons=[] if spec_history_event_count > 0 else ["no_forensic_baseline"],
    )
    return {
        "component": entry,
        "spec_snapshot": spec_snapshot,
        "traceability": traceability,
        "timeline": [],
        "forensic_coverage": coverage.as_dict(),
    }
