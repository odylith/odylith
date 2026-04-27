"""Parse live benchmark host artifacts and score observed-path behavior.

This module owns the stream parsing, workspace path extraction, and precision
metrics used by the live benchmark runner. Keeping these helpers out of the
runner avoids turning one hot execution file into a mixed-phase parser,
differ, and scorer blob.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from odylith.runtime.evaluation import odylith_benchmark_live_diagnostics
from odylith.runtime.reasoning import odylith_reasoning


_STATUS_VALUES = {"completed", "blocked", "failed"}
_LIVE_RESULT_REQUIRED_KEYS = frozenset(
    (
        "status",
        "summary",
        "changed_files",
        "validation_commands_run",
        "validation_summary",
        "notes",
    )
)
_JSON_PATH_TOKEN = re.compile(r"(?P<token>/[^ \n\r\t\"'`]+|(?:\./|\.\./)?[A-Za-z0-9_][A-Za-z0-9_./-]*\.[A-Za-z0-9_./-]+)")
_PATH_LISTING_COMMAND = re.compile(r"(^|[\\/'\"\s])(rg|grep|find|fd|ls)(\s|$)")
_GREP_LIKE_LISTING_COMMAND = re.compile(r"(^|[\\/'\"\s])(rg|grep)(\s|$)")
_LEADING_ENV_AND_ODYLITH_COMMAND = re.compile(
    r"^(?P<prefix>(?:[A-Za-z_][A-Za-z0-9_]*=(?:'[^']*'|\"[^\"]*\"|[^\s]+)\s+)*)odylith(?P<suffix>(?:\s|$).*)$"
)
_CLAUDE_COMMAND_TOOL_NAMES = frozenset({"Bash", "Read", "Glob", "Grep", "Edit", "Write"})
_CLAUDE_WRITE_TOOL_NAMES = frozenset({"Edit", "Write"})
_NEUTRAL_VALIDATOR_LAUNCHER_PATHS = frozenset({"src/odylith/cli.py"})
_NON_PRODUCT_WRITE_PREFIXES: tuple[str, ...] = (
    ".pytest-tmp/",
    ".pytest_cache/",
    ".tmp-pytest-",
    ".tmp-pytest-cache-",
    ".tmp-benchmark-",
    ".venv/",
    "tmp/pytest",
)


def _dedupe_strings(rows: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in rows:
        token = str(raw or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def _relative_workspace_path(path: Path, *, workspace_root: Path) -> str:
    try:
        resolved_path = _safe_resolve_path(path)
        resolved_workspace_root = _safe_resolve_path(workspace_root)
        if resolved_path is None or resolved_workspace_root is None:
            return ""
        return resolved_path.relative_to(resolved_workspace_root).as_posix()
    except ValueError:
        return ""


def _safe_resolve_path(path: Path) -> Path | None:
    with contextlib.suppress(OSError, RuntimeError):
        return path.resolve()
    return None


def _safe_is_file(path: Path) -> bool:
    with contextlib.suppress(OSError):
        return path.is_file()
    return False


def _existing_file_paths(*, workspace_root: Path, paths: Sequence[str]) -> list[str]:
    rows: list[str] = []
    for raw in paths:
        token = str(raw or "").strip()
        if not token:
            continue
        candidate = _safe_resolve_path(workspace_root / token)
        if candidate is not None and _safe_is_file(candidate):
            rows.append(token)
    return _dedupe_strings(rows)


def _resolve_workspace_file(token: str, *, workspace_root: Path) -> str:
    raw = str(token or "").strip().strip("`'\"")
    if not raw:
        return ""
    raw = raw.rstrip(",:;])}")
    candidate = Path(raw)
    if candidate.is_absolute():
        resolved_candidate = _safe_resolve_path(candidate)
        if resolved_candidate is not None and _safe_is_file(resolved_candidate):
            return _relative_workspace_path(resolved_candidate, workspace_root=workspace_root)
        return ""
    relative = raw
    while relative.startswith("./"):
        relative = relative[2:]
    resolved = _safe_resolve_path(workspace_root / relative)
    if resolved is None or not _safe_is_file(resolved):
        return ""
    return _relative_workspace_path(resolved, workspace_root=workspace_root)


def _extract_workspace_paths_from_text(text: str, *, workspace_root: Path) -> list[str]:
    if not text:
        return []
    rows: list[str] = []
    for match in _JSON_PATH_TOKEN.finditer(str(text)):
        token = str(match.group("token") or "").strip()
        if not token:
            continue
        resolved = _resolve_workspace_file(token, workspace_root=workspace_root)
        if resolved:
            rows.append(resolved)
    return _dedupe_strings(rows)


def _listing_output_path_candidates(*, command: str, line: str) -> list[str]:
    normalized_command = str(command or "").strip().lower()
    token = str(line or "").strip()
    if not token:
        return []
    if "git status" in normalized_command:
        status_path = token[3:].strip() if len(token) > 3 else ""
        if " -> " in status_path:
            status_path = status_path.rsplit(" -> ", 1)[-1]
        return [status_path] if status_path else []
    if "git diff --stat" in normalized_command:
        prefix = token.split("|", 1)[0].strip()
        return [prefix] if prefix else []
    if "git grep" in normalized_command or _GREP_LIKE_LISTING_COMMAND.search(normalized_command):
        prefix = token.split(":", 1)[0].strip()
        return [prefix] if prefix else []
    return [token]


def _extract_workspace_paths_from_listing_output(
    *,
    command: str,
    output: str,
    workspace_root: Path,
) -> list[str]:
    if not output:
        return []
    rows: list[str] = []
    for raw_line in str(output).splitlines():
        for candidate in _listing_output_path_candidates(command=command, line=raw_line):
            resolved = _resolve_workspace_file(candidate, workspace_root=workspace_root)
            if resolved:
                rows.append(resolved)
    return _dedupe_strings(rows)


def _parse_json_lines(stream_text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw_line in str(stream_text or "").splitlines():
        line = str(raw_line or "").strip()
        if not line.startswith("{") or not line.endswith("}"):
            continue
        with contextlib.suppress(json.JSONDecodeError):
            payload = json.loads(line)
            if isinstance(payload, Mapping):
                rows.append(dict(payload))
    return rows


def _event_content_blocks(payload: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(payload, Mapping):
        content = payload.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, Mapping):
                    rows.append(dict(item))
        for key in ("message", "item"):
            nested = payload.get(key)
            if isinstance(nested, Mapping):
                rows.extend(_event_content_blocks(nested))
    return rows


def _text_candidates(value: Any) -> list[str]:
    rows: list[str] = []
    if isinstance(value, str):
        token = value.strip()
        if token:
            rows.append(token)
        return rows
    if isinstance(value, Mapping):
        for key in ("text", "result", "output", "content"):
            rows.extend(_text_candidates(value.get(key)))
        return rows
    if isinstance(value, list):
        for item in value:
            rows.extend(_text_candidates(item))
    return rows


def _structured_output_from_events(events: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    for event in reversed(events):
        text_candidates: list[str] = []
        item = dict(event.get("item", {})) if isinstance(event.get("item"), Mapping) else {}
        if str(item.get("type", "")).strip() == "agent_message":
            text_candidates.extend(_text_candidates(item.get("text")))
        if str(event.get("type", "")).strip() in {"agent_message", "assistant_message"}:
            text_candidates.extend(_text_candidates(event.get("text")))
        text_candidates.extend(_text_candidates(event.get("result")))
        for block in _event_content_blocks(event):
            text_candidates.extend(_text_candidates(block))
        for candidate in text_candidates:
            payload = odylith_reasoning._parse_structured_mapping_text(candidate)  # noqa: SLF001
            rows = _normalized_structured_output_payload(payload)
            if rows is not None:
                return rows
    return None


def _normalized_structured_output_payload(payload: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, Mapping):
        return None
    rows = dict(payload)
    if not _LIVE_RESULT_REQUIRED_KEYS.issubset(rows):
        return None
    status = str(rows.get("status", "")).strip().lower()
    if status not in _STATUS_VALUES:
        rows["status"] = "failed"
    return rows


def _usage_from_events(events: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    for event in reversed(events):
        usage = _usage_mapping(event)
        if usage is None:
            continue
        return usage
    return {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}


def _usage_mapping(payload: Any) -> dict[str, int] | None:
    if isinstance(payload, Mapping):
        usage = payload.get("usage")
        if isinstance(usage, Mapping):
            return {
                "input_tokens": int(usage.get("input_tokens", 0) or 0),
                "cached_input_tokens": int(usage.get("cached_input_tokens", 0) or 0),
                "output_tokens": int(usage.get("output_tokens", 0) or 0),
            }
        if any(key in payload for key in ("input_tokens", "cached_input_tokens", "output_tokens")):
            return {
                "input_tokens": int(payload.get("input_tokens", 0) or 0),
                "cached_input_tokens": int(payload.get("cached_input_tokens", 0) or 0),
                "output_tokens": int(payload.get("output_tokens", 0) or 0),
            }
        for key in ("result", "message", "item"):
            nested = _usage_mapping(payload.get(key))
            if nested is not None:
                return nested
    return None


def _tool_result_text_by_id(events: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    rows: dict[str, str] = {}
    for event in events:
        for block in _event_content_blocks(event):
            if str(block.get("type", "")).strip() != "tool_result":
                continue
            tool_use_id = str(block.get("tool_use_id", "")).strip() or str(block.get("id", "")).strip()
            if not tool_use_id or tool_use_id in rows:
                continue
            text = "\n".join(_text_candidates(block))
            if text.strip():
                rows[tool_use_id] = text.strip()
    return rows


def _tool_use_blocks(events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    tool_results = _tool_result_text_by_id(events)
    rows: list[dict[str, Any]] = []
    for event in events:
        for block in _event_content_blocks(event):
            if str(block.get("type", "")).strip() != "tool_use":
                continue
            tool_id = str(block.get("id", "")).strip()
            rows.append(
                {
                    "id": tool_id,
                    "name": str(block.get("name", "")).strip(),
                    "input": dict(block.get("input", {})) if isinstance(block.get("input"), Mapping) else {},
                    "output_text": tool_results.get(tool_id, ""),
                }
            )
    return rows


def _claude_tool_command(tool_name: str, tool_input: Mapping[str, Any]) -> str:
    name = str(tool_name or "").strip()
    payload = dict(tool_input)
    if name == "Bash":
        return str(payload.get("command", "") or payload.get("cmd", "")).strip()
    if name == "Grep":
        path = str(payload.get("path", "") or payload.get("file_path", "")).strip()
        pattern = str(payload.get("pattern", "")).strip()
        return " ".join(token for token in ("Grep", pattern, path) if token)
    if name == "Glob":
        path = str(payload.get("path", "")).strip()
        pattern = str(payload.get("pattern", "")).strip()
        return " ".join(token for token in ("Glob", pattern, path) if token)
    path = str(payload.get("path", "") or payload.get("file_path", "")).strip()
    return " ".join(token for token in (name, path) if token)


def _command_events(events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in events:
        item = dict(event.get("item", {})) if isinstance(event.get("item"), Mapping) else {}
        if str(item.get("type", "")).strip() != "command_execution":
            continue
        rows.append(item)
    for block in _tool_use_blocks(events):
        tool_name = str(block.get("name", "")).strip()
        if tool_name not in _CLAUDE_COMMAND_TOOL_NAMES:
            continue
        rows.append(
            {
                "type": "command_execution",
                "command": _claude_tool_command(tool_name, dict(block.get("input", {}))),
                "aggregated_output": str(block.get("output_text", "")).strip(),
            }
        )
    return rows


def _command_output_is_path_listing(command: str) -> bool:
    token = str(command or "").strip().lower()
    if not token:
        return False
    return bool(_PATH_LISTING_COMMAND.search(token)) or any(
        marker in token
        for marker in (
            "git grep",
            "git ls-files",
            "git diff --name-only",
            "git diff --stat",
            "git show --name-only",
            "git status",
        )
    )


def _file_change_paths(events: Sequence[Mapping[str, Any]], *, workspace_root: Path) -> list[str]:
    rows: list[str] = []
    for event in events:
        item = dict(event.get("item", {})) if isinstance(event.get("item"), Mapping) else {}
        if str(item.get("type", "")).strip() != "file_change":
            continue
        changes = item.get("changes", [])
        if not isinstance(changes, list):
            continue
        for change in changes:
            if not isinstance(change, Mapping):
                continue
            token = _resolve_workspace_file(str(change.get("path", "")).strip(), workspace_root=workspace_root)
            if token:
                rows.append(token)
    for block in _tool_use_blocks(events):
        tool_name = str(block.get("name", "")).strip()
        if tool_name not in _CLAUDE_WRITE_TOOL_NAMES:
            continue
        tool_input = dict(block.get("input", {}))
        token = _resolve_workspace_file(
            str(tool_input.get("path", "") or tool_input.get("file_path", "")).strip(),
            workspace_root=workspace_root,
        )
        if token:
            rows.append(token)
    return _dedupe_strings(rows)


def _candidate_write_paths(
    *,
    events: Sequence[Mapping[str, Any]],
    workspace_root: Path,
    structured_output: Mapping[str, Any],
) -> list[str]:
    structured_changed_files = (
        [str(token).strip() for token in structured_output.get("changed_files", []) if str(token).strip()]
        if isinstance(structured_output.get("changed_files"), list)
        else []
    )
    return _existing_file_paths(
        workspace_root=workspace_root,
        paths=[*_file_change_paths(events, workspace_root=workspace_root), *structured_changed_files],
    )


def _workspace_state_changed_paths(*, workspace_state: Mapping[str, Any]) -> list[str]:
    rows: list[str] = []
    git_status_paths = workspace_state.get("git_status_paths")
    if isinstance(git_status_paths, list):
        rows.extend(str(token).strip() for token in git_status_paths if str(token).strip())
    differences = workspace_state.get("differences")
    if isinstance(differences, list):
        for item in differences:
            if not isinstance(item, Mapping):
                continue
            token = str(item.get("path", "")).strip()
            status = str(item.get("status", "")).strip()
            if not token or not status:
                continue
            if status in {"different_file", "workspace_extra", "workspace_missing"}:
                rows.append(token)
    return _dedupe_strings(rows)


def _workspace_file_fingerprint(*, workspace_root: Path, relative_path: str) -> str:
    token = str(relative_path or "").strip()
    if not token:
        return ""
    resolved = _safe_resolve_path(workspace_root / token)
    if resolved is None:
        return "missing"
    with contextlib.suppress(OSError):
        if resolved.is_file():
            return hashlib.sha256(resolved.read_bytes()).hexdigest()
        if resolved.is_dir():
            return "dir"
    return "missing"


def _workspace_git_status_snapshot(*, workspace_root: Path) -> dict[str, Any]:
    workspace_state = odylith_benchmark_live_diagnostics.workspace_state_diff(
        repo_root=workspace_root,
        workspace_root=workspace_root,
        tracked_paths=[],
    )
    git_status_paths = _dedupe_strings(
        [
            str(token).strip()
            for token in workspace_state.get("git_status_paths", [])
            if str(token).strip()
        ]
    )
    return {
        "git_status_paths": git_status_paths,
        "fingerprints": {
            token: _workspace_file_fingerprint(workspace_root=workspace_root, relative_path=token)
            for token in git_status_paths
        },
    }


def _workspace_state_delta_paths(
    *,
    baseline: Mapping[str, Any],
    workspace_root: Path,
    workspace_state: Mapping[str, Any],
    ignored_paths: Sequence[str] = (),
) -> list[str]:
    ignored = {
        str(token).strip().replace("\\", "/")
        for token in ignored_paths
        if str(token).strip()
    }
    before_paths = {
        str(token).strip().replace("\\", "/")
        for token in baseline.get("git_status_paths", [])
        if str(token).strip() and str(token).strip().replace("\\", "/") not in ignored
    }
    before_fingerprints = (
        {
            str(key).strip().replace("\\", "/"): str(value).strip()
            for key, value in baseline.get("fingerprints", {}).items()
            if str(key).strip() and str(key).strip().replace("\\", "/") not in ignored
        }
        if isinstance(baseline.get("fingerprints"), Mapping)
        else {}
    )
    after_paths = {
        str(token).strip().replace("\\", "/")
        for token in workspace_state.get("git_status_paths", [])
        if str(token).strip() and str(token).strip().replace("\\", "/") not in ignored
    }
    changed = set(after_paths.difference(before_paths))
    for token in before_paths:
        if token not in after_paths:
            changed.add(token)
            continue
        current_fingerprint = _workspace_file_fingerprint(workspace_root=workspace_root, relative_path=token)
        if current_fingerprint != before_fingerprints.get(token, ""):
            changed.add(token)
    return sorted(changed)


def _meaningful_candidate_write_paths(candidate_write_paths: Sequence[str]) -> list[str]:
    rows: list[str] = []
    for raw in candidate_write_paths:
        token = str(raw).strip()
        if not token:
            continue
        normalized = token.replace("\\", "/")
        if any(normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in _NON_PRODUCT_WRITE_PREFIXES):
            continue
        rows.append(token)
    return _dedupe_strings(rows)


def _observed_paths_from_events(
    *,
    events: Sequence[Mapping[str, Any]],
    workspace_root: Path,
    structured_output: Mapping[str, Any],
    prompt_payload: Mapping[str, Any] | None = None,
    raw_prompt_visible_paths: Sequence[str] = (),
    excluded_commands: Sequence[str] = (),
    neutral_paths: Sequence[str] = (),
) -> list[str]:
    return _observed_path_details_from_events(
        events=events,
        workspace_root=workspace_root,
        structured_output=structured_output,
        prompt_payload=prompt_payload,
        raw_prompt_visible_paths=raw_prompt_visible_paths,
        excluded_commands=excluded_commands,
        neutral_paths=neutral_paths,
    )["paths"]


def _observed_path_details_from_events(
    *,
    events: Sequence[Mapping[str, Any]],
    workspace_root: Path,
    structured_output: Mapping[str, Any],
    prompt_payload: Mapping[str, Any] | None = None,
    raw_prompt_visible_paths: Sequence[str] = (),
    excluded_commands: Sequence[str] = (),
    neutral_paths: Sequence[str] = (),
) -> dict[str, Any]:
    rows: list[str] = []
    sources: list[str] = []
    prompt_payload_paths = odylith_benchmark_live_diagnostics.prompt_payload_observed_paths(
        prompt_payload=prompt_payload
    )
    if prompt_payload_paths:
        rows.extend(prompt_payload_paths)
        sources.append("odylith_prompt_payload")
    raw_prompt_paths = _dedupe_strings([str(token).strip() for token in raw_prompt_visible_paths if str(token).strip()])
    if raw_prompt_paths:
        rows.extend(raw_prompt_paths)
        sources.append("raw_prompt_visible_paths")
    excluded = {" ".join(str(token).split()).strip() for token in excluded_commands if str(token).strip()}
    neutral = {str(token).strip() for token in neutral_paths if str(token).strip()}
    command_text_paths: list[str] = []
    listing_output_paths: list[str] = []
    for item in _command_events(events):
        command = str(item.get("command", "")).strip()
        normalized_command = " ".join(command.split()).strip()
        if normalized_command in excluded:
            continue
        command_text_paths.extend(_extract_workspace_paths_from_text(command, workspace_root=workspace_root))
        if _command_output_is_path_listing(command):
            listing_output_paths.extend(
                _extract_workspace_paths_from_listing_output(
                    command=command,
                    output=str(item.get("aggregated_output", "")).strip(),
                    workspace_root=workspace_root,
                )
            )
    if command_text_paths:
        rows.extend(command_text_paths)
        sources.append("command_text")
    if listing_output_paths:
        rows.extend(listing_output_paths)
        sources.append("listing_output")
    file_change_paths = _file_change_paths(events, workspace_root=workspace_root)
    if file_change_paths:
        rows.extend(file_change_paths)
        sources.append("file_change_events")
    changed_files = [
        _resolve_workspace_file(str(token).strip(), workspace_root=workspace_root)
        for token in structured_output.get("changed_files", [])
        if isinstance(structured_output.get("changed_files"), list)
    ]
    changed_files = [token for token in changed_files if token]
    if changed_files:
        rows.extend(changed_files)
        sources.append("structured_output_changed_files")
    paths = _dedupe_strings([token for token in rows if token and token not in neutral])
    return {
        "paths": paths,
        "sources": _dedupe_strings(sources),
    }


def _prompt_supplied_paths_from_commands(
    *,
    workspace_root: Path,
    commands: Sequence[str],
) -> list[str]:
    rows: list[str] = []
    for raw in commands:
        rows.extend(
            _extract_workspace_paths_from_text(
                str(raw or "").strip(),
                workspace_root=workspace_root,
            )
        )
    return _dedupe_strings(rows)


def _scenario_explicit_anchor_paths(scenario: Mapping[str, Any]) -> set[str]:
    rows: list[str] = []
    for key in (
        "required_paths",
        "critical_paths",
        "supporting_paths",
        "expected_write_paths",
        "changed_paths",
    ):
        values = scenario.get(key, [])
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
            continue
        rows.extend(str(token).strip() for token in values if str(token).strip())
    return {token for token in _dedupe_strings(rows) if token}


def _meaningful_preflight_command_paths(
    *,
    scenario: Mapping[str, Any],
    command_paths: Sequence[str],
) -> list[str]:
    explicit_anchors = _scenario_explicit_anchor_paths(scenario)
    rows: list[str] = []
    for raw in command_paths:
        token = str(raw or "").strip()
        if not token:
            continue
        if token in _NEUTRAL_VALIDATOR_LAUNCHER_PATHS and token not in explicit_anchors:
            continue
        rows.append(token)
    return _dedupe_strings(rows)


def _path_recall(
    *,
    required_paths: Sequence[str],
    observed_paths: Sequence[str],
) -> tuple[float, list[str]]:
    required = {str(token).strip() for token in required_paths if str(token).strip()}
    observed = {str(token).strip() for token in observed_paths if str(token).strip()}
    if not required:
        return 1.0, []
    misses = sorted(required.difference(observed))
    return round((len(required) - len(misses)) / max(1, len(required)), 3), misses


def _scenario_supporting_paths(scenario: Mapping[str, Any]) -> list[str]:
    raw_paths = scenario.get("supporting_paths", [])
    if not isinstance(raw_paths, list):
        return []
    return _dedupe_strings([str(token).strip() for token in raw_paths if str(token).strip()])


def _scenario_expected_write_paths(scenario: Mapping[str, Any]) -> list[str]:
    if not bool(scenario.get("needs_write")):
        return []
    raw_expected = scenario.get("expected_write_paths", [])
    explicit_paths = _dedupe_strings(
        [str(token).strip() for token in raw_expected if str(token).strip()]
        if isinstance(raw_expected, list)
        else []
    )
    if explicit_paths:
        return explicit_paths
    raw_changed = scenario.get("changed_paths", [])
    if not isinstance(raw_changed, list):
        return []
    return _dedupe_strings([str(token).strip() for token in raw_changed if str(token).strip()])


def _precision_metrics(
    *,
    required_paths: Sequence[str],
    supporting_paths: Sequence[str] = (),
    observed_paths: Sequence[str],
    expected_write_paths: Sequence[str],
    candidate_write_paths: Sequence[str],
) -> dict[str, Any]:
    required = {str(token).strip() for token in required_paths if str(token).strip()}
    supporting = {str(token).strip() for token in supporting_paths if str(token).strip()}
    relevant = required.union(supporting)
    observed = {str(token).strip() for token in observed_paths if str(token).strip()}
    expected_write = {str(token).strip() for token in expected_write_paths if str(token).strip()}
    candidate_write = {str(token).strip() for token in candidate_write_paths if str(token).strip()}

    observed_supporting = sorted(supporting.intersection(observed))
    observed_relevant = sorted(relevant.intersection(observed))
    hallucinated_surfaces = sorted(observed.difference(relevant))
    required_path_precision = (
        round(len(observed_relevant) / max(1, len(observed)), 3)
        if observed
        else 1.0
        if not relevant
        else 0.0
    )
    hallucinated_surface_rate = (
        round(len(hallucinated_surfaces) / max(1, len(observed)), 3)
        if observed
        else 0.0
    )

    matched_write_paths = sorted(expected_write.intersection(candidate_write))
    unnecessary_widening_paths = sorted(candidate_write.difference(expected_write))
    write_surface_precision = (
        round(len(matched_write_paths) / max(1, len(candidate_write)), 3)
        if candidate_write
        else 1.0
        if not expected_write
        else 0.0
    )
    unnecessary_widening_rate = (
        round(len(unnecessary_widening_paths) / max(1, len(candidate_write)), 3)
        if candidate_write
        else 0.0
    )

    return {
        "observed_path_count": len(observed),
        "supporting_path_count": len(supporting),
        "supporting_path_hits": observed_supporting,
        "required_path_precision_basis": "required_plus_supporting_paths" if supporting else "required_paths",
        "required_path_precision": required_path_precision,
        "hallucinated_surface_count": len(hallucinated_surfaces),
        "hallucinated_surface_rate": hallucinated_surface_rate,
        "hallucinated_surfaces": hallucinated_surfaces[:12],
        "expected_write_path_count": len(expected_write),
        "candidate_write_path_count": len(candidate_write),
        "candidate_write_paths": sorted(candidate_write)[:12],
        "write_surface_precision": write_surface_precision,
        "unnecessary_widening_count": len(unnecessary_widening_paths),
        "unnecessary_widening_rate": unnecessary_widening_rate,
        "unnecessary_widening_paths": unnecessary_widening_paths[:12],
    }
