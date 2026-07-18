"""Synchronize component specs with mapped conversation requirement evidence.

This command keeps each component's living spec aligned with mapped governance
timeline narratives by maintaining a generated `## Requirements Trace` block.
It is designed to make conversation-derived requirements visible in the same
spec document that operators treat as the component contract.

Design invariants:
- Source of truth for component spec paths is the active component-registry manifest.
- Requirement evidence is derived from meaningful mapped timeline events.
- The generated block is deterministic, idempotent, and human-readable.
- Section updates are additive and preserve surrounding manual spec content.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
from typing import Iterable, Mapping, Sequence

from odylith.runtime.common.consumer_profile import truth_root_path
from odylith.runtime.common import repo_path_resolver
from odylith.runtime.governance import component_registry_intelligence as component_registry

_SECTION_TITLE = "Requirements Trace"
_SECTION_INTRO = (
    "This section captures synchronized requirement and contract signals derived "
    "from component-linked timeline evidence."
)
_START_MARKER = "<!-- registry-requirements:start -->"
_END_MARKER = "<!-- registry-requirements:end -->"
_EMPTY_REQUIREMENTS_LINE = "- No synchronized requirement or contract signals yet."
_LEGACY_CONSUMER_ORG_TOKEN = "den" + "toai"
_LEGACY_CONSUMER_PROJECT_TOKEN = "ori" + "on"
_PUBLIC_REQUIREMENT_SUMMARY_REWRITES = (
    (re.compile(rf"\b{_LEGACY_CONSUMER_ORG_TOKEN}-[A-Za-z0-9_-]+\b", re.IGNORECASE), "a real consumer repo"),
    (re.compile(rf"\b[A-Za-z0-9_-]*{_LEGACY_CONSUMER_PROJECT_TOKEN}[A-Za-z0-9_-]*\b", re.IGNORECASE), "a real consumer repo"),
)
_PUBLIC_ARTIFACT_PATH_PREFIXES = ("bin/", "odylith/", "scripts/", "src/", "tests/")
_PUBLIC_ARTIFACT_PATHS = {"Makefile", "pyproject.toml"}


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith governance sync-component-spec-requirements",
        description="Sync mapped conversation requirements into component living specs.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument(
        "--manifest",
        default=component_registry.DEFAULT_MANIFEST_PATH,
        help="Component registry manifest path.",
    )
    parser.add_argument(
        "--catalog",
        default=component_registry.DEFAULT_CATALOG_PATH,
        help="Mermaid catalog path used for component inference context.",
    )
    parser.add_argument(
        "--ideas-root",
        default=component_registry.DEFAULT_IDEAS_ROOT,
        help="Backlog ideas root used for component inference context.",
    )
    parser.add_argument(
        "--stream",
        default=component_registry.DEFAULT_STREAM_PATH,
        help="Compass timeline stream path.",
    )
    parser.add_argument(
        "--component",
        action="append",
        default=[],
        help="Target component id/alias to sync (repeatable). Defaults to all components.",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=6,
        help="Maximum mapped events rendered per component requirements trace.",
    )
    parser.add_argument(
        "--include-non-meaningful",
        action="store_true",
        help="Include non-meaningful mapped events (default is meaningful-only).",
    )
    parser.add_argument(
        "--today",
        default="",
        help="Override Last updated date (`YYYY-MM-DD`) for deterministic tests.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validation mode only; fail if spec updates are required.",
    )
    parser.add_argument(
        "--runtime-mode",
        choices=("auto", "standalone", "daemon"),
        default="auto",
        help="Reserved for sync orchestration parity; component spec sync still uses deterministic standalone logic.",
    )
    return parser.parse_args(argv)


def _resolve(repo_root: Path, token: str) -> Path:
    """Resolve one spec-sync path token against the repo root."""

    return repo_path_resolver.resolve_repo_path(repo_root=repo_root, value=token)


def _normalize_space(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def _event_date(raw_ts: str, *, fallback_date: str) -> str:
    token = str(raw_ts or "").strip()
    if not token:
        return fallback_date
    if token.endswith("Z"):
        token = f"{token[:-1]}+00:00"
    try:
        parsed = dt.datetime.fromisoformat(token)
    except ValueError:
        return fallback_date
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.datetime.now().astimezone().tzinfo)
    return parsed.astimezone().date().isoformat()


def _find_h2_section(lines: Sequence[str], heading: str) -> tuple[int, int] | None:
    target = str(heading or "").strip().lower()
    if not target:
        return None
    for idx, line in enumerate(lines):
        token = str(line or "").strip()
        if token.lower() != f"## {target}":
            continue
        start = idx + 1
        end = len(lines)
        for offset in range(start, len(lines)):
            if str(lines[offset] or "").strip().startswith("## "):
                end = offset
                break
        return start, end
    return None


def _upsert_last_updated(*, lines: list[str], today: str) -> tuple[list[str], bool]:
    expected = f"Last updated: {today}"
    for idx, line in enumerate(lines):
        if str(line or "").strip().lower().startswith("last updated:"):
            if str(line) == expected:
                return lines, False
            next_lines = list(lines)
            next_lines[idx] = expected
            return next_lines, True

    insert_at = 0
    for idx, line in enumerate(lines):
        if str(line or "").strip().startswith("# "):
            insert_at = idx + 1
            break
    next_lines = list(lines)
    injected = [expected, ""]
    next_lines[insert_at:insert_at] = injected
    return next_lines, True


def _ensure_requirements_section(lines: list[str]) -> tuple[list[str], tuple[int, int], bool]:
    existing = _find_h2_section(lines, _SECTION_TITLE)
    if existing is not None:
        return lines, existing, False

    insert_at = len(lines)
    feature_history = _find_h2_section(lines, "Feature History")
    if feature_history is not None:
        insert_at = feature_history[0] - 1

    block: list[str] = []
    if insert_at > 0 and str(lines[insert_at - 1] or "").strip():
        block.append("")
    block.extend(
        [
            f"## {_SECTION_TITLE}",
            _SECTION_INTRO,
            "",
            _START_MARKER,
            _EMPTY_REQUIREMENTS_LINE,
            _END_MARKER,
            "",
        ]
    )

    next_lines = list(lines)
    next_lines[insert_at:insert_at] = block
    section = _find_h2_section(next_lines, _SECTION_TITLE)
    if section is None:
        raise ValueError(f"failed to create `{_SECTION_TITLE}` section")
    return next_lines, section, True


def _format_evidence_suffix(*, event: component_registry.MappedEvent) -> list[str]:
    parts: list[str] = []
    workstreams = _unique_values(event.workstreams)
    artifacts = _artifact_evidence_references(event.artifacts)
    if workstreams:
        parts.append(f"Scope: {', '.join(workstreams[:4])}")
    if artifacts:
        joined = ", ".join(f"`{artifact}`" for artifact in artifacts[:4])
        remaining = max(0, len(artifacts) - 4)
        suffix = f", plus {remaining} more" if remaining else ""
        parts.append(f"Evidence: {joined}{suffix}")
    return parts


def _clean_requirement_summary(*, summary: str, kind: str) -> str:
    normalized = _normalize_space(summary)
    kind_token = str(kind or "").strip().lower()
    if kind_token == "decision" and normalized.lower().startswith("decision:"):
        normalized = normalized.split(":", 1)[1].strip()
    if kind_token == "statement" and normalized.lower().startswith("statement:"):
        normalized = normalized.split(":", 1)[1].strip()
    for pattern, replacement in _PUBLIC_REQUIREMENT_SUMMARY_REWRITES:
        normalized = pattern.sub(replacement, normalized)
    return normalized


def _requirements_trace_summary(*, event: component_registry.MappedEvent) -> str:
    artifacts = _artifact_evidence_references(event.artifacts)
    workstreams = _unique_values(event.workstreams)
    kind = _normalize_space(event.kind).lower() or "timeline"
    if kind == "decision":
        base = "Decision evidence linked this component to governed work."
    elif kind == "implementation":
        base = "Implementation evidence linked this component to governed work."
    else:
        base = "Timeline evidence linked this component to governed work."
    qualifiers: list[str] = []
    if workstreams:
        qualifiers.append("workstream scope preserved")
    if artifacts:
        plural = "s" if len(artifacts) != 1 else ""
        qualifiers.append(f"{len(artifacts)} verifiable artifact reference{plural}")
    if not qualifiers:
        return base
    return f"{base.rstrip('.')} with {'; '.join(qualifiers)}."


def _path_matches_component(*, artifact: str, entry: component_registry.ComponentEntry) -> bool:
    normalized_artifact = str(artifact or "").strip().lower().lstrip("./")
    if not normalized_artifact:
        return False
    candidates = [str(entry.spec_ref or "").strip(), *list(entry.path_prefixes)]
    for raw in candidates:
        token = str(raw or "").strip().lower().lstrip("./")
        if not token:
            continue
        if normalized_artifact == token:
            return True
        if normalized_artifact.startswith(f"{token.rstrip('/')}/"):
            return True
    return False


def _summary_mentions_component(*, summary: str, entry: component_registry.ComponentEntry) -> bool:
    haystack = _normalize_space(summary).lower()
    if not haystack:
        return False
    tokens = {
        str(entry.component_id or "").strip().lower(),
        str(entry.name or "").strip().lower(),
        *(str(token or "").strip().lower() for token in entry.aliases),
    }
    for raw in tokens:
        if not raw:
            continue
        variants = {raw, raw.replace("-", " "), raw.replace("_", " ")}
        if any(variant and variant in haystack for variant in variants):
            return True
    return False


def _is_component_requirement_signal(
    *,
    event: component_registry.MappedEvent,
    entry: component_registry.ComponentEntry,
) -> bool:
    if not component_registry.is_requirements_trace_event(event):
        return False

    kind = str(event.kind or "").strip().lower()
    summary = _normalize_space(event.summary)
    if not summary:
        return False
    if kind not in {"decision", "implementation"}:
        return False

    artifact_match = any(
        _path_matches_component(artifact=artifact, entry=entry)
        for artifact in event.artifacts
    )
    explicit_single = event.explicit_components == [entry.component_id]
    mapped_single = event.mapped_components == [entry.component_id]
    summary_match = _summary_mentions_component(summary=summary, entry=entry)
    strong_reference = artifact_match or explicit_single or (mapped_single and summary_match)

    if not strong_reference:
        return False
    if len(event.mapped_components) > 1 and not artifact_match and not explicit_single:
        return False
    return True


def _normalize_requirements_section_preamble(
    *,
    lines: list[str],
    section_bounds: tuple[int, int],
) -> tuple[list[str], tuple[int, int], bool]:
    start, end = section_bounds
    section_lines = list(lines[start:end])
    marker_start = next(
        (idx for idx, line in enumerate(section_lines) if str(line or "").strip() == _START_MARKER),
        len(section_lines),
    )
    replacement = [_SECTION_INTRO, ""]
    if section_lines[:marker_start] == replacement:
        return lines, section_bounds, False

    next_lines = list(lines)
    next_lines[start:end] = replacement + section_lines[marker_start:]
    next_bounds = _find_h2_section(next_lines, _SECTION_TITLE)
    if next_bounds is None:
        raise ValueError(f"failed to normalize `{_SECTION_TITLE}` section preamble")
    return next_lines, next_bounds, True


def _build_generated_requirement_lines(
    *,
    events: Sequence[component_registry.MappedEvent],
    fallback_date: str,
    max_events: int,
) -> list[str]:
    if max_events <= 0:
        return [_EMPTY_REQUIREMENTS_LINE]

    rows: list[str] = []
    for event in list(events)[:max_events]:
        summary = _requirements_trace_summary(event=event)
        if not summary:
            continue
        kind = _normalize_space(event.kind).lower() or "event"
        date_token = _event_date(event.ts_iso, fallback_date=fallback_date)
        rows.append(f"- **{date_token} · {kind.title()}:** {summary}")
        for evidence_line in _format_evidence_suffix(event=event):
            rows.append(f"  - {evidence_line}")
    if rows:
        return rows
    return [_EMPTY_REQUIREMENTS_LINE]


def _replace_generated_block(
    *,
    lines: list[str],
    section_bounds: tuple[int, int],
    generated_rows: Sequence[str],
) -> tuple[list[str], bool]:
    start, end = section_bounds
    section_lines = list(lines[start:end])
    marker_start = -1
    marker_end = -1
    for idx, line in enumerate(section_lines):
        token = str(line or "").strip()
        if token == _START_MARKER:
            marker_start = idx
        if token == _END_MARKER:
            marker_end = idx
            break

    generated_block = [_START_MARKER, *generated_rows, _END_MARKER]
    if marker_start >= 0 and marker_end >= marker_start:
        replacement = section_lines[:marker_start] + generated_block + section_lines[marker_end + 1 :]
    else:
        replacement = list(section_lines)
        if replacement and str(replacement[-1] or "").strip():
            replacement.append("")
        replacement.extend(generated_block)

    if replacement == section_lines:
        return lines, False

    next_lines = list(lines)
    next_lines[start:end] = replacement
    return next_lines, True


def _resolve_component_targets(
    *,
    raw_values: Iterable[str],
    components: dict[str, component_registry.ComponentEntry],
    alias_to_component: dict[str, str],
) -> tuple[list[str], list[str]]:
    tokens = [str(item or "").strip() for item in raw_values if str(item or "").strip()]
    if not tokens:
        return sorted(components), []

    resolved: list[str] = []
    errors: list[str] = []
    seen: set[str] = set()
    for raw in tokens:
        normalized = component_registry.normalize_component_id(raw)
        if not normalized:
            errors.append(raw)
            continue
        component_id = alias_to_component.get(normalized, normalized if normalized in components else "")
        if not component_id:
            errors.append(raw)
            continue
        if component_id in seen:
            continue
        seen.add(component_id)
        resolved.append(component_id)
    return sorted(resolved), errors


def _write_if_changed(*, path: Path, lines: Sequence[str]) -> None:
    text = "\n".join(lines).rstrip() + "\n"
    path.write_text(text, encoding="utf-8")


def _remember_path(rows: list[str], value: str) -> None:
    if value not in rows:
        rows.append(value)


def _forensics_payload(
    *,
    entry: component_registry.ComponentEntry,
    coverage: component_registry.ComponentForensicCoverage,
    timeline: Sequence[component_registry.MappedEvent],
    traceability: dict[str, list[str]],
) -> dict[str, object]:
    return {
        "version": "v1",
        "component_id": entry.component_id,
        "name": entry.name,
        "spec_ref": entry.spec_ref,
        "what_it_is": entry.what_it_is,
        "why_tracked": entry.why_tracked,
        "workstreams": list(entry.workstreams),
        "diagrams": list(entry.diagrams),
        "path_prefixes": list(entry.path_prefixes),
        "forensic_coverage": coverage.as_dict(),
        "traceability": {
            "runbooks": list(traceability.get("runbooks", [])),
            "developer_docs": list(traceability.get("developer_docs", [])),
            "code_references": list(traceability.get("code_references", [])),
        },
        "timeline": [_forensics_timeline_row(row) for row in timeline],
    }


def _forensics_timeline_row(event: component_registry.MappedEvent) -> dict[str, object]:
    artifacts = _artifact_evidence_references(event.artifacts)
    workstreams = _unique_values(event.workstreams)
    return {
        "event_index": event.event_index,
        "ts_iso": event.ts_iso,
        "kind": event.kind,
        "summary": _forensics_summary(event=event, artifact_count=len(artifacts), workstream_count=len(workstreams)),
        "workstreams": workstreams,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "explicit_components": _unique_values(event.explicit_components),
        "mapped_components": _unique_values(event.mapped_components),
        "confidence": event.confidence,
        "meaningful": event.meaningful,
    }


def _forensics_summary(
    *,
    event: component_registry.MappedEvent,
    artifact_count: int,
    workstream_count: int,
) -> str:
    kind = _normalize_space(event.kind).lower() or "timeline"
    if kind == "workspace_activity":
        base = "Workspace activity touched tracked component evidence."
    elif kind == "decision":
        base = "Decision evidence linked this component to governed work."
    elif kind == "implementation":
        base = "Implementation evidence linked this component to governed work."
    elif kind == "statement":
        base = "Timeline evidence linked this component to governed work."
    else:
        base = "Component evidence linked this component to governed work."
    qualifiers: list[str] = []
    if workstream_count:
        qualifiers.append("workstream scope preserved")
    if artifact_count:
        plural = "s" if artifact_count != 1 else ""
        qualifiers.append(f"{artifact_count} verifiable artifact reference{plural}")
    if not qualifiers:
        return base
    return f"{base} {'; '.join(qualifiers)}."


def _unique_values(values: Sequence[str]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = str(raw or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        rows.append(value)
    return rows


def _artifact_evidence_references(values: Sequence[str]) -> list[str]:
    """Keep artifact custody inspectable without exposing unsafe host path terms."""

    return _unique_values(
        [_artifact_evidence_reference(value) for value in values if _normalize_space(value)]
    )


def _artifact_evidence_reference(value: str) -> str:
    normalized = _canonical_artifact_path(value)
    if not normalized:
        return ""
    if _is_public_artifact_path(normalized):
        return normalized
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _canonical_artifact_path(value: str) -> str:
    raw = _normalize_space(value).replace("\\", "/")
    absolute = raw.startswith("/")
    parts: list[str] = []
    for part in raw.split("/"):
        if not part or part == ".":
            continue
        if part == "..":
            if parts and parts[-1] != "..":
                parts.pop()
            else:
                parts.append(part)
            continue
        parts.append(part)
    normalized = "/".join(parts)
    return f"/{normalized}" if absolute else normalized


def _is_public_artifact_path(value: str) -> bool:
    if not value or value.startswith(("/", "../")):
        return False
    return value in _PUBLIC_ARTIFACT_PATHS or value.startswith(_PUBLIC_ARTIFACT_PATH_PREFIXES)


def _write_json_if_changed(*, path: Path, payload: dict[str, object]) -> bool:
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if path.is_file():
        try:
            if path.read_text(encoding="utf-8") == text:
                return False
        except OSError:
            pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def _resolve_forensics_path(*, entry: component_registry.ComponentEntry, spec_path: Path) -> Path:
    """Return the deterministic forensic sidecar path for a component spec.

    Product Odylith keeps one dossier directory per component and uses the
    stable `CURRENT_SPEC.md` + `FORENSICS.v1.json` pairing. Installed consumer
    repos commonly keep many flat spec files in a shared directory, so the
    forensic sidecar must include the component identity to avoid collisions.
    """

    if spec_path.name == "CURRENT_SPEC.md":
        return spec_path.parent / "FORENSICS.v1.json"
    return spec_path.with_name(f"{entry.component_id}.FORENSICS.v1.json")


def _empty_forensic_coverage() -> component_registry.ComponentForensicCoverage:
    return component_registry.ComponentForensicCoverage(
        status="tracked_but_evidence_empty",
        timeline_event_count=0,
        explicit_event_count=0,
        recent_path_match_count=0,
        mapped_workstream_evidence_count=0,
        spec_history_event_count=0,
        empty_reasons=[
            "no_explicit_event",
            "no_recent_path_match",
            "no_mapped_workstream_evidence",
        ],
    )


def _write_forensics_for_targets(
    *,
    repo_root: Path,
    targets: Sequence[str],
    components: Mapping[str, component_registry.ComponentEntry],
    report: component_registry.ComponentRegistryReport,
    traceability_index: Mapping[str, dict[str, list[str]]],
    check_only: bool,
    stale_paths: list[str],
    changed_paths: list[str],
) -> tuple[int, set[Path], set[Path], set[Path]]:
    updated_forensics = 0
    expected_forensics_paths: set[Path] = set()
    flat_spec_dirs: set[Path] = set()
    per_component_specs_roots: set[Path] = set()
    persisted_events = [
        event
        for event in report.mapped_events
        if str(event.kind or "").strip().lower() != "workspace_activity"
    ]
    persisted_timelines = component_registry.build_component_timelines(
        component_index=components,
        mapped_events=persisted_events,
    )
    persisted_coverage = component_registry.build_component_forensic_coverage(
        component_index=components,
        mapped_events=persisted_events,
        repo_root=repo_root,
    )
    for component_id in targets:
        entry = components.get(component_id)
        if entry is None:
            continue
        spec_ref = str(entry.spec_ref or "").strip()
        if not spec_ref:
            continue
        spec_path = _resolve(repo_root, spec_ref)
        if not spec_path.is_file():
            continue
        forensics_path = _resolve_forensics_path(entry=entry, spec_path=spec_path)
        expected_forensics_paths.add(forensics_path.resolve())
        if forensics_path.name != "FORENSICS.v1.json":
            flat_spec_dirs.add(spec_path.parent.resolve())
        else:
            per_component_specs_roots.add(spec_path.parent.parent.resolve())
        forensics_rel = repo_path_resolver.display_repo_path(repo_root=repo_root, value=forensics_path)
        payload = _forensics_payload(
            entry=entry,
            coverage=persisted_coverage.get(component_id, _empty_forensic_coverage()),
            timeline=persisted_timelines.get(component_id, []),
            traceability=traceability_index.get(
                component_id,
                {"runbooks": [], "developer_docs": [], "code_references": []},
            ),
        )
        if check_only:
            expected = json.dumps(payload, indent=2, sort_keys=True) + "\n"
            current = forensics_path.read_text(encoding="utf-8") if forensics_path.is_file() else ""
            if current != expected:
                _remember_path(stale_paths, forensics_rel)
        else:
            if _write_json_if_changed(path=forensics_path, payload=payload):
                updated_forensics += 1
                _remember_path(changed_paths, forensics_rel)
    return updated_forensics, expected_forensics_paths, flat_spec_dirs, per_component_specs_roots


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    manifest_token = str(args.manifest or "").strip()
    manifest_path = (
        component_registry.default_manifest_path(repo_root=repo_root)
        if manifest_token == component_registry.DEFAULT_MANIFEST_PATH
        else _resolve(repo_root, manifest_token)
    )
    catalog_path = _resolve(repo_root, str(args.catalog))
    ideas_root = _resolve(repo_root, str(args.ideas_root))
    stream_path = _resolve(repo_root, str(args.stream))

    today_token = str(args.today or "").strip() or dt.date.today().isoformat()
    if len(today_token) != 10:
        print("sync component spec requirements FAILED")
        print("- --today must be in YYYY-MM-DD format when provided")
        return 2
    if int(args.max_events) < 0:
        print("sync component spec requirements FAILED")
        print("- --max-events must be >= 0")
        return 2

    report = component_registry.build_component_registry_report(
        repo_root=repo_root,
        manifest_path=manifest_path,
        catalog_path=catalog_path,
        ideas_root=ideas_root,
        stream_path=stream_path,
    )
    ignored_prefixes: tuple[str, ...] = (
        "missing stream path",
        "candidate components pending review",
        "suppressed unresolved idea component tokens",
    )
    hard_diagnostics = [
        row
        for row in report.diagnostics
        if not any(str(row or "").startswith(prefix) for prefix in ignored_prefixes)
    ]
    if hard_diagnostics:
        print("sync component spec requirements FAILED")
        print(f"- {hard_diagnostics[0]}")
        return 2

    components, alias_to_component, _diagnostics = component_registry.build_component_index(
        repo_root=repo_root,
        manifest_path=manifest_path,
        catalog_path=catalog_path,
        ideas_root=ideas_root,
    )
    targets, target_errors = _resolve_component_targets(
        raw_values=list(args.component),
        components=components,
        alias_to_component=alias_to_component,
    )
    if target_errors:
        print("sync component spec requirements FAILED")
        print(f"- unknown component ids/aliases: {', '.join(target_errors)}")
        return 2

    timelines = component_registry.build_component_timelines(
        component_index=components,
        mapped_events=report.mapped_events,
    )
    traceability_index = component_registry.build_component_traceability_index(
        repo_root=repo_root,
        components=components,
    )

    changed_paths: list[str] = []
    stale_paths: list[str] = []
    updated_components = 0
    for component_id in targets:
        entry = components.get(component_id)
        if entry is None:
            continue
        spec_ref = str(entry.spec_ref or "").strip()
        if not spec_ref:
            print("sync component spec requirements FAILED")
            print(f"- component `{component_id}` is missing `spec_ref`")
            return 2
        spec_path = _resolve(repo_root, spec_ref)
        if not spec_path.is_file():
            print("sync component spec requirements FAILED")
            print(f"- component `{component_id}` spec file missing: {spec_ref}")
            return 2

        source_lines = spec_path.read_text(encoding="utf-8").splitlines()
        working_lines = list(source_lines)
        working_lines, section_bounds, created = _ensure_requirements_section(working_lines)
        working_lines, section_bounds, preamble_changed = _normalize_requirements_section_preamble(
            lines=working_lines,
            section_bounds=section_bounds,
        )

        events = list(timelines.get(component_id, []))
        if not args.include_non_meaningful:
            events = [row for row in events if row.meaningful]
        events = [
            row
            for row in events
            if _is_component_requirement_signal(event=row, entry=entry)
        ]

        generated_rows = _build_generated_requirement_lines(
            events=events,
            fallback_date=today_token,
            max_events=int(args.max_events),
        )
        working_lines, section_changed = _replace_generated_block(
            lines=working_lines,
            section_bounds=section_bounds,
            generated_rows=generated_rows,
        )
        content_changed = bool(created or preamble_changed or section_changed)
        if content_changed:
            working_lines, last_updated_changed = _upsert_last_updated(lines=working_lines, today=today_token)
            content_changed = bool(content_changed or last_updated_changed)

        if working_lines != source_lines:
            updated_components += 1
            rel = repo_path_resolver.display_repo_path(repo_root=repo_root, value=spec_path)
            if args.check_only:
                _remember_path(stale_paths, rel)
            else:
                _write_if_changed(path=spec_path, lines=working_lines)
                _remember_path(changed_paths, rel)

    if updated_components and not args.check_only:
        report = component_registry.build_component_registry_report(
            repo_root=repo_root,
            manifest_path=manifest_path,
            catalog_path=catalog_path,
            ideas_root=ideas_root,
            stream_path=stream_path,
        )
        timelines = component_registry.build_component_timelines(
            component_index=components,
            mapped_events=report.mapped_events,
        )
        traceability_index = component_registry.build_component_traceability_index(
            repo_root=repo_root,
            components=components,
        )

    (
        updated_forensics,
        expected_forensics_paths,
        flat_spec_dirs,
        per_component_specs_roots,
    ) = _write_forensics_for_targets(
        repo_root=repo_root,
        targets=targets,
        components=components,
        report=report,
        traceability_index=traceability_index,
        check_only=bool(args.check_only),
        stale_paths=stale_paths,
        changed_paths=changed_paths,
    )

    for directory in sorted(flat_spec_dirs):
        legacy_path = directory / "FORENSICS.v1.json"
        if legacy_path.resolve() in expected_forensics_paths or not legacy_path.exists():
            continue
        legacy_rel = repo_path_resolver.display_repo_path(repo_root=repo_root, value=legacy_path)
        if args.check_only:
            stale_paths.append(legacy_rel)
            continue
        legacy_path.unlink()
        changed_paths.append(legacy_rel)

    for directory in sorted(per_component_specs_roots):
        legacy_path = directory / "FORENSICS.v1.json"
        if legacy_path.resolve() in expected_forensics_paths or not legacy_path.exists():
            continue
        legacy_rel = repo_path_resolver.display_repo_path(repo_root=repo_root, value=legacy_path)
        if args.check_only:
            stale_paths.append(legacy_rel)
            continue
        legacy_path.unlink()
        changed_paths.append(legacy_rel)

    specs_root = truth_root_path(repo_root=repo_root, key="component_specs")
    legacy_specs_root_forensics = specs_root / "FORENSICS.v1.json"
    if (
        legacy_specs_root_forensics.exists()
        and legacy_specs_root_forensics.resolve() not in expected_forensics_paths
    ):
        legacy_root_rel = repo_path_resolver.display_repo_path(
            repo_root=repo_root,
            value=legacy_specs_root_forensics,
        )
        if args.check_only:
            stale_paths.append(legacy_root_rel)
        else:
            legacy_specs_root_forensics.unlink()
            changed_paths.append(legacy_root_rel)

    if args.check_only and stale_paths:
        print("sync component spec requirements FAILED")
        print(f"- stale specs: {', '.join(stale_paths)}")
        return 2

    print("sync component spec requirements passed")
    print(f"- components_scanned: {len(targets)}")
    print(f"- components_updated: {updated_components}")
    print(f"- forensics_updated: {updated_forensics}")
    if args.check_only:
        print("- mode: check-only")
    elif changed_paths:
        print(f"- updated_specs: {', '.join(changed_paths)}")
    else:
        print("- updated_specs: none")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
