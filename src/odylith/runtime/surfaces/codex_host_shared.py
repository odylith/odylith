"""Shared helpers for Codex host surfaces rendered from Odylith state.

The first Codex parity slice shipped declarative `.codex/` assets, but the
runtime behavior still lived in standalone project-root hook scripts. This
module centralizes the shared helpers those hooks need so the supported Codex
host surfaces can live under `src/odylith/runtime/surfaces/` like the rest of
the product.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.surfaces import claude_host_shared


_WORKSTREAM_RE = re.compile(r"\bB-\d{3,}\b")
_ANCHOR_RE = re.compile(r"\b(?:B|CB|D)-\d{3,}\b")
_ACTION_TOKEN_RE = re.compile(
    r"\b("
    r"added|aligned|closed|fixed|hardened|implemented|materialized|passed|"
    r"proved|refreshed|regenerated|rendered|removed|shipped|specialized|"
    r"synced|tightened|updated|validated|verified|wired"
    r")\b",
    re.IGNORECASE,
)
_MARKDOWN_TOKEN_RE = re.compile(r"[*_`]+")
_CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_BLOCK_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(^|\s)rm\s+-rf(\s|$)"), "Destructive recursive deletion is blocked by repo policy."),
    (re.compile(r"git\s+reset\s+--hard(\s|$)"), "Hard reset is blocked by repo policy."),
    (re.compile(r"git\s+checkout\s+--(\s|$)"), "Discarding tracked changes with checkout is blocked by repo policy."),
    (re.compile(r"git\s+push\s+--force(?:-with-lease)?(\s|$)"), "Force-push is blocked by repo policy."),
    (re.compile(r"git\s+clean\s+-fdx(\s|$)"), "Full working-tree cleanup is blocked by repo policy."),
)
_EDIT_LIKE_RE = re.compile(
    r"\b("
    r"apply_patch|cp|mv|touch|mkdir|sed\s+-i|perl\s+-0pi|tee|cat\s+>|python3?\s+-c|node\s+-e"
    r")\b"
)
_PATCH_START_RE = re.compile(r"^\s*\*\*\* Begin Patch\b", re.MULTILINE)


resolve_repo_root = claude_host_shared.resolve_repo_root
load_compass_runtime = claude_host_shared.load_compass_runtime
active_workstream_headline = claude_host_shared.active_workstream_headline
freshness_label = claude_host_shared.freshness_label
collapse_whitespace = claude_host_shared.collapse_whitespace


def load_payload(raw: str | None = None) -> dict[str, Any]:
    text = raw if raw is not None else sys.stdin.read()
    try:
        payload = json.loads(text or "{}")
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def hook_session_id(payload: Mapping[str, Any] | None) -> str:
    if not isinstance(payload, Mapping):
        return agent_runtime_contract.fallback_session_token("codex")
    for key in ("session_id", "thread_id", "turn_id"):
        token = str(payload.get(key) or "").strip()
        if token:
            return token
    default = agent_runtime_contract.default_host_session_id()
    if default:
        return default
    return agent_runtime_contract.fallback_session_token("codex")


def _mapping_payload(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if not isinstance(value, str):
        return {}
    token = value.strip()
    if not token.startswith("{"):
        return {}
    try:
        parsed = json.loads(token)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, Mapping) else {}


def command_from_hook_payload(payload: Mapping[str, Any] | None) -> str:
    if not isinstance(payload, Mapping):
        return ""
    tool_name = str(
        payload.get("tool_name")
        or payload.get("toolName")
        or payload.get("name")
        or ""
    ).strip()
    for tool_input in (
        _mapping_payload(payload.get("tool_input")),
        _mapping_payload(payload.get("arguments")),
    ):
        command = str(tool_input.get("command") or tool_input.get("cmd") or payload.get("command") or "").strip()
        if command:
            return command
        patch = str(tool_input.get("patch") or tool_input.get("input") or "").strip()
        if patch and (tool_name == "apply_patch" or _PATCH_START_RE.search(patch)):
            return f"apply_patch <<'PATCH'\n{patch}\nPATCH"
    patch = str(payload.get("patch") or payload.get("input") or "").strip()
    if patch and (tool_name == "apply_patch" or _PATCH_START_RE.search(patch)):
        return f"apply_patch <<'PATCH'\n{patch}\nPATCH"
    return str(payload.get("command") or "").strip()


def project_launcher(project_dir: Path | str) -> Path:
    return resolve_repo_root(project_dir) / ".odylith" / "bin" / "odylith"


def run_odylith(
    *,
    project_dir: Path | str,
    args: list[str],
    timeout: int = 20,
) -> subprocess.CompletedProcess[str] | None:
    launcher = project_launcher(project_dir)
    if not launcher.is_file():
        return None
    try:
        return subprocess.run(
            [str(launcher), *args],
            cwd=str(resolve_repo_root(project_dir)),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def json_payload_from_output(output: str) -> dict[str, Any]:
    text = str(output or "").strip()
    if not text:
        return {}
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if not line.startswith("{"):
            continue
        payload_text = "\n".join(lines[index:])
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}
    return {}


def start_payload(project_dir: Path | str) -> Mapping[str, Any] | None:
    completed = run_odylith(project_dir=project_dir, args=["start", "--repo-root", "."], timeout=20)
    if completed is None:
        return None
    payload = json_payload_from_output(completed.stdout)
    return payload if payload else None


def start_summary(
    *,
    project_dir: Path | str,
    payload_override: Mapping[str, Any] | None = None,
) -> str:
    payload = payload_override if payload_override is not None else start_payload(project_dir)
    if not isinstance(payload, Mapping):
        return ""
    summary: list[str] = []
    selection_reason = str(payload.get("selection_reason", "")).strip()
    if selection_reason:
        summary.append(f"Selection: {selection_reason}.")
    relevant_docs = payload.get("relevant_docs")
    if isinstance(relevant_docs, list) and relevant_docs:
        summary.append(f"Relevant doc: {relevant_docs[0]}.")
    commands = payload.get("recommended_commands")
    if isinstance(commands, list) and commands:
        summary.append(f"Next command: {commands[0]}.")
    return " ".join(summary).strip()


def context_summary(
    *,
    project_dir: Path | str,
    ref: str,
    payload_override: Mapping[str, Any] | None = None,
) -> str:
    payload = payload_override
    if payload is None:
        completed = run_odylith(project_dir=project_dir, args=["context", "--repo-root", ".", ref], timeout=20)
        if completed is None:
            return ""
        payload = json_payload_from_output(completed.stdout)
    if not isinstance(payload, Mapping):
        return ""
    targets = payload.get("target_resolution", {})
    if isinstance(targets, Mapping):
        candidates = targets.get("candidate_targets", [])
        if isinstance(candidates, list) and candidates:
            first = candidates[0]
            if isinstance(first, Mapping):
                path = str(first.get("path", "")).strip()
                if path:
                    return f"Odylith anchor {ref}: primary target {path}."
    relevant_docs = payload.get("relevant_docs")
    if isinstance(relevant_docs, list) and relevant_docs:
        return f"Odylith anchor {ref}: relevant doc {relevant_docs[0]}."
    return f"Odylith anchor {ref}: context resolved."


def prompt_anchor(prompt: str) -> str:
    matches = list(dict.fromkeys(_ANCHOR_RE.findall(str(prompt or ""))))
    return matches[0] if matches else ""


def active_workstreams(payload: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(payload, Mapping):
        return []
    focus = payload.get("execution_focus")
    if not isinstance(focus, Mapping):
        return []
    scope = focus.get("global")
    if not isinstance(scope, Mapping):
        return []
    workstreams = scope.get("workstreams")
    if not isinstance(workstreams, list):
        return []
    collected: list[str] = []
    for token in workstreams:
        value = str(token or "").strip().upper()
        if value and value not in collected:
            collected.append(value)
        if len(collected) >= 6:
            break
    return collected


def next_action_lines(payload: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(payload, Mapping):
        return []
    actions = payload.get("next_actions")
    if not isinstance(actions, list):
        return []
    lines: list[str] = []
    for row in actions[:4]:
        if not isinstance(row, Mapping):
            continue
        idea_id = str(row.get("idea_id") or "").strip().upper()
        action = collapse_whitespace(row.get("action") or "")
        if not action:
            continue
        lines.append(f"- {idea_id}: {action}" if idea_id else f"- {action}")
    return lines


def risk_lines(payload: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(payload, Mapping):
        return []
    risks = payload.get("risks")
    if not isinstance(risks, Mapping):
        return []
    lines: list[str] = []
    for key in ("traceability_warnings", "traceability", "bugs"):
        value = risks.get(key)
        if not isinstance(value, list):
            continue
        for item in value[:2]:
            if isinstance(item, Mapping):
                text = collapse_whitespace(item.get("title") or item.get("summary") or item.get("bug_id") or "")
            else:
                text = collapse_whitespace(item)
            if text:
                lines.append(f"- {text}")
        if lines:
            break
    return lines[:3]


def blocked_bash_reason(command: str) -> str:
    token = str(command or "").strip()
    if not token:
        return ""
    for pattern, reason in _BLOCK_PATTERNS:
        if pattern.search(token):
            return reason
    return ""


def edit_like_bash(command: str) -> bool:
    return bool(_EDIT_LIKE_RE.search(str(command or "").strip()))


def meaningful_stop_summary(text: str) -> str:
    raw = str(text or "").strip()
    if len(raw) < 60:
        return ""
    text_wo_code = _CODE_FENCE_RE.sub(" ", raw)
    cleaned_lines: list[str] = []
    for raw_line in text_wo_code.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^#+\s*", "", line)
        line = re.sub(r"^[-*]\s+", "", line)
        line = _MARKDOWN_TOKEN_RE.sub("", line)
        line = " ".join(line.split()).strip()
        if line:
            cleaned_lines.append(line)
    if not cleaned_lines:
        return ""
    joined = " ".join(cleaned_lines)
    if joined.endswith("?"):
        return ""
    if not _ACTION_TOKEN_RE.search(joined):
        return ""
    if re.match(r"^(I can|Would you like|If you want)\b", joined, flags=re.IGNORECASE):
        return ""
    sentence = re.split(r"(?<=[.!])\s+", joined, maxsplit=1)[0]
    return collapse_whitespace(sentence, limit=180)


def extract_workstreams(text: str) -> list[str]:
    seen: set[str] = set()
    tokens: list[str] = []
    for match in _WORKSTREAM_RE.findall(str(text or "")):
        token = match.strip().upper()
        if token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def run_compass_log(
    *,
    project_dir: Path | str,
    summary: str,
    workstreams: list[str] | None = None,
) -> bool:
    args = ["compass", "log", "--repo-root", ".", "--kind", "implementation", "--summary", summary]
    for workstream in (workstreams or [])[:4]:
        args.extend(["--workstream", workstream])
    completed = run_odylith(project_dir=project_dir, args=args, timeout=20)
    return bool(completed and completed.returncode == 0)
