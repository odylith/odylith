"""Persisted governance readback checks for greenfield matrix scoring."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string


NON_ARTIFACT_MARKDOWN_FILES = {"AGENTS.md", "CLAUDE.md", "INDEX.md", "README.md"}
COMPASS_RECORD_PATHS = (
    "odylith/compass/runtime/agent-stream.v1.jsonl",
    "odylith/compass/runtime/current.v1.json",
    "odylith/compass/compass-source-truth.v1.json",
)
SURFACE_PAYLOAD_GLOBALS = {
    "radar": ("odylith/radar/backlog-payload.v1.js", "__ODYLITH_BACKLOG_DATA__"),
    "registry": ("odylith/registry/registry-payload.v1.js", "__ODYLITH_REGISTRY_DATA__"),
    "atlas": ("odylith/atlas/mermaid-payload.v1.js", "__ODYLITH_MERMAID_DATA__"),
    "compass": ("odylith/compass/compass-payload.v1.js", "__ODYLITH_COMPASS_SHELL_DATA__"),
    "casebook": ("odylith/casebook/casebook-payload.v1.js", "__ODYLITH_CASEBOOK_DATA__"),
    "tooling": ("odylith/tooling-payload.v1.js", "__ODYLITH_TOOLING_DATA__"),
}


@dataclass(frozen=True)
class GovernedReadback:
    release_catalogs: Mapping[str, Mapping[str, Any]]
    release_events: Mapping[str, tuple[Mapping[str, Any], ...]]
    program_records: Mapping[str, Mapping[str, Any]]
    compass_records: Mapping[str, Any]
    surface_payloads: Mapping[str, Mapping[str, Any]]

    @property
    def tooling_payload(self) -> Mapping[str, Any]:
        return _mapping(self.surface_payloads.get("tooling"))


def collect_governed_readback(repo_root: Path) -> GovernedReadback:
    """Read persisted governed records that file-count proof cannot validate."""

    root = Path(repo_root)
    return GovernedReadback(
        release_catalogs=_read_release_catalogs(root),
        release_events=_read_release_events(root),
        program_records=_read_program_records(root),
        compass_records=_read_compass_records(root),
        surface_payloads=_read_surface_payloads(root),
    )


def release_record_count(readback: GovernedReadback) -> int:
    return len(readback.release_catalogs) + len(readback.release_events)


def program_record_count(readback: GovernedReadback) -> int:
    return len(readback.program_records)


def compass_record_count(readback: GovernedReadback) -> int:
    return len(readback.compass_records)


def governed_readback_findings(
    readback: GovernedReadback,
    *,
    release_selector: str = "",
    release_workstream_ids: Sequence[str] = (),
) -> tuple[tuple[str, str], ...]:
    """Return dimension/message pairs for persisted governance proof gaps."""

    findings: list[tuple[str, str]] = []
    findings.extend(_release_findings(readback, release_selector=release_selector, workstream_ids=release_workstream_ids))
    findings.extend(_unexpected_program_findings(readback))
    findings.extend(_compass_findings(readback))
    findings.extend(_surface_payload_findings(readback))
    return tuple(dict.fromkeys(findings))


def _read_release_catalogs(repo_root: Path) -> dict[str, Mapping[str, Any]]:
    root = repo_root / "odylith/radar/source/releases"
    catalogs: dict[str, Mapping[str, Any]] = {}
    if not root.is_dir():
        return catalogs
    for path in sorted(root.rglob("*.json")):
        if path.name in NON_ARTIFACT_MARKDOWN_FILES:
            continue
        payload = _read_json_mapping(path)
        releases = _mapping_rows(payload.get("releases"))
        if not releases:
            continue
        if not any(_release_row_is_valid(row) for row in releases):
            continue
        catalogs[str(path.relative_to(repo_root))] = payload
    return catalogs


def _read_release_events(repo_root: Path) -> dict[str, tuple[Mapping[str, Any], ...]]:
    root = repo_root / "odylith/radar/source/releases"
    events: dict[str, tuple[Mapping[str, Any], ...]] = {}
    if not root.is_dir():
        return events
    for path in sorted(root.rglob("*.jsonl")):
        rows = tuple(row for row in _read_jsonl_mappings(path) if _release_event_is_valid(row))
        if rows:
            events[str(path.relative_to(repo_root))] = rows
    return events


def _read_program_records(repo_root: Path) -> dict[str, Mapping[str, Any]]:
    """Return every program JSON artifact; Greenfield must not create any of them."""

    root = repo_root / "odylith/radar/source/programs"
    programs: dict[str, Mapping[str, Any]] = {}
    if not root.is_dir():
        return programs
    for path in sorted(root.rglob("*.json")):
        if path.name in NON_ARTIFACT_MARKDOWN_FILES:
            continue
        payload = _read_json_mapping(path)
        programs[str(path.relative_to(repo_root))] = payload
    return programs


def _read_compass_records(repo_root: Path) -> dict[str, Any]:
    records: dict[str, Any] = {}
    for relative in COMPASS_RECORD_PATHS:
        path = repo_root / relative
        if path.suffix == ".jsonl":
            rows = tuple(row for row in _read_jsonl_mappings(path) if _compass_event_is_valid(row))
            if rows:
                records[relative] = rows
            continue
        payload = _read_json_mapping(path)
        if _compass_mapping_is_valid(payload):
            records[relative] = payload
    return records


def _read_surface_payloads(repo_root: Path) -> dict[str, Mapping[str, Any]]:
    payloads: dict[str, Mapping[str, Any]] = {}
    for surface, (relative, global_name) in SURFACE_PAYLOAD_GLOBALS.items():
        payload = _read_js_payload(repo_root / relative, global_name=global_name)
        if payload:
            payloads[surface] = payload
    return payloads


def _release_findings(
    readback: GovernedReadback,
    *,
    release_selector: str,
    workstream_ids: Sequence[str],
) -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    if not readback.release_catalogs:
        findings.append(("operator_usefulness", "persisted release readback has no valid release catalog"))
    selector = normalize_string(release_selector)
    if selector and readback.release_catalogs and not _release_selector_present(readback.release_catalogs, selector):
        findings.append(("operator_usefulness", f"persisted release readback does not include release {selector}"))
    expected = _normalized_ids(workstream_ids)
    if expected:
        assigned = _release_event_workstream_ids(readback.release_events)
        missing = sorted(expected - assigned)
        if missing:
            findings.append(
                ("engineer", f"persisted release assignment events do not cover workstream(s): {', '.join(missing[:5])}")
            )
    return findings


def _unexpected_program_findings(readback: GovernedReadback) -> list[tuple[str, str]]:
    """Greenfield onboarding must not add Compass programs or execution waves."""

    if not readback.program_records:
        return []
    return [("engineer", "Greenfield commit created unexpected Compass program record(s)")]


def _compass_findings(readback: GovernedReadback) -> list[tuple[str, str]]:
    if readback.compass_records:
        return []
    return [("operator_usefulness", "persisted Compass readback has no valid source or runtime record")]


def _surface_payload_findings(readback: GovernedReadback) -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    payloads = readback.surface_payloads
    for surface in SURFACE_PAYLOAD_GLOBALS:
        if surface not in payloads:
            findings.append(("browser_surface_proof", f"{surface} surface payload readback is missing or invalid"))
    if "radar" in payloads and len(_mapping_rows(payloads["radar"].get("entries"))) < 4:
        findings.append(("governance_depth", "Radar surface payload exposes fewer than four workstreams"))
    if "registry" in payloads and len(_mapping_rows(payloads["registry"].get("components"))) < 3:
        findings.append(("architect", "Registry surface payload exposes fewer than three components"))
    if "atlas" in payloads and len(_mapping_rows(payloads["atlas"].get("diagrams"))) < 4:
        findings.append(("architect", "Atlas surface payload exposes fewer than four diagrams"))
    if "compass" in payloads:
        compass = payloads["compass"]
        if not normalize_string(compass.get("runtime_json_href")) or not normalize_string(compass.get("source_truth_href")):
            findings.append(("operator_usefulness", "Compass surface payload does not link runtime and source truth"))
    if "casebook" in payloads:
        casebook = payloads["casebook"]
        if "bugs" not in casebook or "counts" not in casebook:
            findings.append(("browser_surface_proof", "Casebook surface payload lacks bug list or counts readback"))
    tooling = _mapping(payloads.get("tooling"))
    if tooling:
        for key in ("radar_href", "registry_href", "atlas_href", "compass_href", "casebook_href"):
            if not normalize_string(tooling.get(key)):
                findings.append(("browser_surface_proof", f"tooling shell payload is missing {key}"))
        if "project_intelligence" not in tooling:
            findings.append(("operator_usefulness", "tooling shell payload is missing Project intelligence readback"))
        if "surface_runtime_status" not in tooling:
            findings.append(("browser_surface_proof", "tooling shell payload is missing surface runtime status"))
    return findings


def _release_selector_present(catalogs: Mapping[str, Mapping[str, Any]], selector: str) -> bool:
    token = selector.casefold()
    for catalog in catalogs.values():
        for row in _mapping_rows(catalog.get("releases")):
            if normalize_string(row.get("version")).casefold() == token:
                return True
            if normalize_string(row.get("release_id")).casefold() == token:
                return True
    return False


def _release_event_workstream_ids(events: Mapping[str, Sequence[Mapping[str, Any]]]) -> set[str]:
    return {
        normalize_string(row.get("workstream_id")).upper()
        for rows in events.values()
        for row in rows
        if normalize_string(row.get("workstream_id"))
    }


def _release_row_is_valid(row: Mapping[str, Any]) -> bool:
    return bool(
        normalize_string(row.get("release_id"))
        and normalize_string(row.get("version"))
        and normalize_string(row.get("status"))
    )


def _release_event_is_valid(row: Mapping[str, Any]) -> bool:
    return bool(
        normalize_string(row.get("action"))
        and normalize_string(row.get("release_id") or row.get("to_release_id") or row.get("from_release_id"))
        and normalize_string(row.get("workstream_id"))
        and normalize_string(row.get("recorded_at"))
    )


def _compass_event_is_valid(row: Mapping[str, Any]) -> bool:
    return bool(
        normalize_string(row.get("summary"))
        and (normalize_string(row.get("kind")) or normalize_string(row.get("ts_iso")))
    )


def _compass_mapping_is_valid(payload: Mapping[str, Any]) -> bool:
    if len(payload) < 2:
        return False
    evidence_keys = {
        "version",
        "generated_utc",
        "release_summary",
        "sources",
        "kpis",
        "digest",
        "workstreams",
        "timeline",
    }
    return bool(evidence_keys & set(str(key) for key in payload))


def _read_json_mapping(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return _mapping(payload)


def _read_jsonl_mappings(path: Path) -> tuple[Mapping[str, Any], ...]:
    if not path.is_file():
        return ()
    rows: list[Mapping[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        row = _mapping(payload)
        if row:
            rows.append(row)
    return tuple(rows)


def _read_js_payload(path: Path, *, global_name: str) -> Mapping[str, Any]:
    text = _read_text(path)
    if not text or global_name not in text:
        return {}
    start = text.find("{")
    if start < 0:
        return {}
    try:
        payload, _end = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError:
        return {}
    return _mapping(payload)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(errors="replace")
    except FileNotFoundError:
        return ""


def _normalized_ids(values: Sequence[str] | set[str]) -> set[str]:
    return {normalize_string(value).upper() for value in values if normalize_string(value)}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _mapping_rows(value: Any) -> tuple[Mapping[str, Any], ...]:
    return tuple(row for row in _sequence(value) if isinstance(row, Mapping))


def _sequence(value: Any) -> tuple[Any, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(value)
    return ()


__all__ = [
    "COMPASS_RECORD_PATHS",
    "GovernedReadback",
    "SURFACE_PAYLOAD_GLOBALS",
    "collect_governed_readback",
    "compass_record_count",
    "governed_readback_findings",
    "program_record_count",
    "release_record_count",
]
