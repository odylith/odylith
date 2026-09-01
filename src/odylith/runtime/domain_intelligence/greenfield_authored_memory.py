"""Render accepted-memory views from verified model-authored Greenfield fields."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def render_authored_project_brief_lines(project_brief: Mapping[str, Any]) -> list[str]:
    """Render the authored brief structurally without parsing or repairing its prose."""

    lines: list[str] = []
    outcome = _text(project_brief.get("project_outcome"))
    principle = _text(project_brief.get("operating_principle"))
    if outcome:
        lines.append(f"- outcome: {outcome}")
    if principle:
        lines.append(f"- principle: {principle}")
    sections = _mapping_rows(project_brief.get("blueprint_sections"))
    if sections:
        _append_section(lines, "## Project Design Board")
        for row in sections:
            section = _text(row.get("section"))
            fact = _text(row.get("must_capture"))
            why = _text(row.get("why_it_matters"))
            if not section or not fact:
                continue
            lines.append(f"- {section}: {fact}")
            if why:
                lines.append(f"  - Why: {why}")
    gates = _strings(project_brief.get("coding_readiness_gates"))
    paths = _mapping_rows(project_brief.get("host_independent_paths"))
    if gates or paths:
        _append_section(lines, "## Governance Package")
    if gates:
        lines.append("- coding readiness gates:")
        lines.extend(f"  - {gate}" for gate in gates)
    if paths:
        lines.append("- host-independent customization paths:")
        for row in paths:
            path = _text(row.get("path"))
            command = _text(row.get("command"))
            works_in = _text(row.get("works_in"))
            use_when = _text(row.get("use_when"))
            parts = [value for value in (path, command, works_in, use_when) if value]
            if parts:
                lines.append("  - " + " | ".join(parts))
    return lines


def _append_section(lines: list[str], heading: str) -> None:
    if lines and lines[-1] != "":
        lines.append("")
    lines.append(heading)


def _mapping_rows(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(row for row in value if isinstance(row, Mapping))


def _strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(text for row in value if (text := _text(row)))


def _text(value: Any) -> str:
    return str(value or "").strip()


__all__ = ["render_authored_project_brief_lines"]
