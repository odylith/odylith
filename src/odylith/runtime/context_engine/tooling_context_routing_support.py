"""Support helpers for Context Engine routing fallback and count signals."""

from __future__ import annotations

import shlex
from typing import Any, Mapping, Sequence

from odylith.runtime.common.value_coercion import dedupe_strings
from odylith.runtime.common.value_coercion import int_value

__all__ = (
    "count_or_list_len",
    "fallback_anchor_commands",
    "fallback_scan_commands",
    "normalized_string_list",
    "shell_quote",
    "truncate",
)


def truncate(text: str, *, max_chars: int = 140) -> str:
    """Collapse whitespace and shorten user-facing routing summaries."""

    normalized = " ".join(str(text or "").strip().split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max(0, max_chars - 1)].rstrip() + "…"


def normalized_string_list(value: Any) -> list[str]:
    """Return trimmed scalar-or-sequence rows while preserving duplicate entries."""

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [str(item).strip() for item in value if str(item).strip()]
    token = str(value or "").strip()
    return [token] if token else []


def count_or_list_len(payload: Mapping[str, Any], *, list_key: str, count_key: str) -> int:
    """Prefer explicit counts but preserve routing's non-empty list counting."""

    value = payload.get(list_key)
    list_count = (
        len([row for row in value if row not in ("", [], {}, None)])
        if isinstance(value, list)
        else len(normalized_string_list(value))
    )
    return max(
        list_count,
        int_value(payload.get(count_key)),
    )


def shell_quote(value: str) -> str:
    """Quote a shell token for generated fallback commands."""

    return shlex.quote(str(value or "").strip())


def fallback_anchor_commands(anchor: Mapping[str, Any]) -> tuple[str, str]:
    """Return the context command and optional read follow-up for an anchor."""

    value = str(anchor.get("value", "")).strip()
    if not value:
        return "", ""
    next_command = f"./.odylith/bin/odylith context --repo-root . {shell_quote(value)}"
    anchor_kind = str(anchor.get("kind", "")).strip()
    followup = ""
    if anchor_kind in {"doc", "path"} or "/" in value:
        followup = f"sed -n '1,200p' {shell_quote(value)}"
    return next_command, followup


def fallback_scan_commands(
    *,
    fallback_scan: Mapping[str, Any],
    retained_paths: Sequence[str],
) -> tuple[str, str]:
    """Return a narrowed search command and optional first-source read command."""

    query = str(fallback_scan.get("query", "")).strip()
    candidate_paths = dedupe_strings(
        [
            *normalized_string_list(fallback_scan.get("changed_paths")),
            *(str(token).strip() for token in retained_paths if str(token).strip()),
        ]
    )
    followup = ""
    if candidate_paths:
        followup = f"sed -n '1,200p' {shell_quote(candidate_paths[0])}"
    if query and candidate_paths:
        scoped_paths = " ".join(shell_quote(path) for path in candidate_paths[:4])
        return f"rg -n --context 2 {shell_quote(query)} -- {scoped_paths}", followup
    if query:
        return f"rg -n --context 2 {shell_quote(query)} .", ""
    if candidate_paths:
        pattern = "|".join(
            str(path).replace("\\", "\\\\").replace(".", r"\.")
            for path in candidate_paths[:4]
        )
        return f"rg --files | rg {shell_quote(pattern)}", followup
    return (
        r"rg --files | rg 'AGENTS\.md|CLAUDE\.md|odylith/(AGENTS|CLAUDE)\.md|pyproject\.toml'",
        "if [ -f AGENTS.md ]; then sed -n '1,200p' AGENTS.md; else sed -n '1,200p' CLAUDE.md; fi",
    )
