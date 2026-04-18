#!/usr/bin/env python3
"""Shared helper utilities for Claude project hooks."""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any


AUTO_MEMORY_IMPORT = "@odylith-governed-brief.md"
AUTO_MEMORY_NOTE = "odylith-governed-brief.md"
AUTO_MEMORY_START = "<!-- odylith-auto-memory:start -->"
AUTO_MEMORY_END = "<!-- odylith-auto-memory:end -->"
_WORKSTREAM_RE = re.compile(r"\bB-\d{3,}\b")
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

_AGENT_HINTS: dict[str, str] = {
    "Explore": "Keep the main session narrow. Report the exact files, records, and validation obligations that matter next.",
    "Plan": "Return a bounded flat plan tied to the active Odylith slice, including proof and governance follow-through.",
    "odylith-atlas-diagrammer": "Edit Atlas source truth first: prefer `.mmd` and catalog records over derived dashboard artifacts.",
    "odylith-compass-briefer": "Use Compass runtime and brief state as evidence, not as permission to invent implementation progress.",
    "odylith-context-engine": "Stay inside packets, routing data, and narrowed retrieval evidence. Do not widen into broad repo search without cause.",
    "odylith-governance-scribe": "Update only source-of-truth governance records touched by the slice, then leave derived surface refresh explicit.",
    "odylith-registry-scribe": "Treat `components/*/CURRENT_SPEC.md` and registry source manifests as canonical. Do not edit generated registry HTML as source truth.",
    "odylith-reviewer": "Find bugs, regressions, risks, and missing proof first. Do not edit files.",
    "odylith-validator": "Run the smallest truthful validation surface and report exact command/file evidence.",
    "odylith-workstream": "Keep the active workstream explicit, preserve governance traceability, and avoid unrelated cleanup.",
}


def load_payload(raw: str | None = None) -> dict[str, Any]:
    text = raw if raw is not None else os.sys.stdin.read()
    try:
        payload = json.loads(text or "{}")
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def project_launcher(project_dir: Path) -> Path:
    return Path(project_dir).resolve() / ".odylith" / "bin" / "odylith"


def run_odylith(*, project_dir: Path, args: list[str], timeout: int = 20) -> subprocess.CompletedProcess[str] | None:
    launcher = project_launcher(project_dir)
    if not launcher.is_file():
        return None
    try:
        return subprocess.run(
            [str(launcher), *args],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def canonical_repo_root(project_dir: Path) -> Path:
    root = Path(project_dir).resolve()
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return root
    token = str(completed.stdout or "").strip()
    if completed.returncode != 0 or not token:
        return root
    common_dir = Path(token)
    if not common_dir.is_absolute():
        common_dir = (root / common_dir).resolve()
    parts = common_dir.parts
    if ".git" not in parts:
        return root
    index = parts.index(".git")
    if index <= 0:
        return root
    repo_root = Path(parts[0])
    for part in parts[1:index]:
        repo_root /= part
    return repo_root.resolve()


def claude_config_dir() -> Path:
    token = str(os.environ.get("CLAUDE_CONFIG_DIR", "~/.claude")).strip() or "~/.claude"
    return Path(token).expanduser().resolve()


def project_slug(project_dir: Path) -> str:
    normalized = canonical_repo_root(project_dir).as_posix()
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", normalized)
    return slug if slug.startswith("-") else f"-{slug.lstrip('-')}"


def project_memory_dir(project_dir: Path) -> Path:
    return claude_config_dir() / "projects" / project_slug(project_dir) / "memory"


def load_runtime_snapshot(project_dir: Path) -> dict[str, Any]:
    path = Path(project_dir).resolve() / "odylith" / "compass" / "runtime" / "current.v1.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _single_line(raw: object, *, limit: int = 220) -> str:
    text = " ".join(str(raw or "").split()).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _workstream_title_map(snapshot: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for collection_key in ("current_workstreams", "workstream_catalog"):
        collection = snapshot.get(collection_key)
        if not isinstance(collection, list):
            continue
        for row in collection:
            if not isinstance(row, dict):
                continue
            idea_id = str(row.get("idea_id") or row.get("workstream") or row.get("id") or "").strip().upper()
            title = _single_line(row.get("title") or "")
            if idea_id and title and idea_id not in mapping:
                mapping[idea_id] = title
    return mapping


def _active_workstream_lines(snapshot: dict[str, Any]) -> list[str]:
    focus = snapshot.get("execution_focus")
    if not isinstance(focus, dict):
        return []
    global_focus = focus.get("global")
    if not isinstance(global_focus, dict):
        return []
    active = global_focus.get("workstreams")
    if not isinstance(active, list):
        return []
    title_map = _workstream_title_map(snapshot)
    lines: list[str] = []
    for token in active[:6]:
        idea_id = str(token or "").strip().upper()
        if not idea_id:
            continue
        title = title_map.get(idea_id, "")
        lines.append(f"- {idea_id}: {title}" if title else f"- {idea_id}")
    return lines


def _next_action_lines(snapshot: dict[str, Any]) -> list[str]:
    actions = snapshot.get("next_actions")
    if not isinstance(actions, list):
        return []
    lines: list[str] = []
    for row in actions[:4]:
        if not isinstance(row, dict):
            continue
        idea_id = str(row.get("idea_id") or "").strip().upper()
        action = _single_line(row.get("action") or "")
        if not action:
            continue
        lines.append(f"- {idea_id}: {action}" if idea_id else f"- {action}")
    return lines


def _risk_lines(snapshot: dict[str, Any]) -> list[str]:
    risks = snapshot.get("risks")
    if not isinstance(risks, dict):
        return []
    lines: list[str] = []
    for key in ("traceability_warnings", "traceability", "bugs"):
        value = risks.get(key)
        if not isinstance(value, list):
            continue
        for item in value[:2]:
            if isinstance(item, dict):
                title = _single_line(item.get("title") or item.get("summary") or item.get("bug_id") or "")
                if title:
                    lines.append(f"- {title}")
            else:
                title = _single_line(item)
                if title:
                    lines.append(f"- {title}")
        if lines:
            break
    return lines[:3]


def build_memory_note(*, project_dir: Path, snapshot: dict[str, Any], start_output: str = "") -> str:
    lines = [
        "# Odylith Governed Brief",
        "",
        "This note is managed by the repo's Claude SessionStart hook.",
        "Treat it as a current cross-session grounding snapshot derived from Odylith runtime state, not as source-of-truth governance.",
        "",
    ]
    generated = _single_line(snapshot.get("generated_utc") or snapshot.get("now_local_iso") or "")
    if generated:
        lines.append(f"- Updated: {generated}")
    lines.append("- Source: `odylith/compass/runtime/current.v1.json` when present, otherwise the repo-local `odylith start` result.")
    lines.append("")
    if snapshot:
        focus = snapshot.get("execution_focus")
        global_focus = focus.get("global") if isinstance(focus, dict) else {}
        headline = _single_line(global_focus.get("headline") if isinstance(global_focus, dict) else "")
        if headline:
            lines.extend(["## Live Focus", f"- Headline: {headline}"])
            active_lines = _active_workstream_lines(snapshot)
            if active_lines:
                lines.append("- Active workstreams:")
                lines.extend(active_lines)
            verified = snapshot.get("verified_scoped_workstreams")
            verified_24h = verified.get("24h") if isinstance(verified, dict) else []
            if isinstance(verified_24h, list) and verified_24h:
                lines.append(f"- Verified in last 24h: {', '.join(str(item).strip() for item in verified_24h[:8] if str(item).strip())}")
            lines.append("")
        next_lines = _next_action_lines(snapshot)
        if next_lines:
            lines.append("## Next Actions")
            lines.extend(next_lines)
            lines.append("")
        risk_lines = _risk_lines(snapshot)
        if risk_lines:
            lines.append("## Risks")
            lines.extend(risk_lines)
            lines.append("")
    start_summary = _single_line(start_output)
    if start_summary:
        lines.extend(["## Startup", f"- {start_summary}", ""])
    return "\n".join(lines).rstrip() + "\n"


def write_project_memory(*, project_dir: Path, snapshot: dict[str, Any], start_output: str = "") -> Path | None:
    try:
        memory_dir = project_memory_dir(project_dir)
        memory_dir.mkdir(parents=True, exist_ok=True)
        note_path = memory_dir / AUTO_MEMORY_NOTE
        note_path.write_text(
            build_memory_note(project_dir=project_dir, snapshot=snapshot, start_output=start_output),
            encoding="utf-8",
        )
        memory_index = memory_dir / "MEMORY.md"
        managed_block = "\n".join(
            [
                AUTO_MEMORY_START,
                "## Odylith Auto Memory",
                "",
                "This managed block keeps Claude's project auto-memory anchored to the latest Odylith runtime snapshot.",
                AUTO_MEMORY_IMPORT,
                AUTO_MEMORY_END,
            ]
        )
        existing = memory_index.read_text(encoding="utf-8") if memory_index.is_file() else ""
        if AUTO_MEMORY_START in existing and AUTO_MEMORY_END in existing:
            updated = re.sub(
                rf"{re.escape(AUTO_MEMORY_START)}.*?{re.escape(AUTO_MEMORY_END)}",
                managed_block,
                existing,
                count=1,
                flags=re.DOTALL,
            )
        elif existing.strip():
            updated = existing.rstrip() + "\n\n" + managed_block + "\n"
        else:
            updated = managed_block + "\n"
        memory_index.write_text(updated, encoding="utf-8")
        return note_path
    except OSError:
        return None


def build_subagent_context(*, project_dir: Path, agent_type: str = "") -> str:
    snapshot = load_runtime_snapshot(project_dir)
    lines = ["Odylith subagent grounding:"]
    if snapshot:
        focus = snapshot.get("execution_focus")
        global_focus = focus.get("global") if isinstance(focus, dict) else {}
        headline = _single_line(global_focus.get("headline") if isinstance(global_focus, dict) else "")
        if headline:
            lines.append(f"- Live focus: {headline}")
        active = _active_workstream_lines(snapshot)
        if active:
            lines.append("- Active workstreams:")
            lines.extend(active[:4])
        next_actions = _next_action_lines(snapshot)
        if next_actions:
            lines.append("- Next actions:")
            lines.extend(next_actions[:3])
    lines.append("- Keep nearest `AGENTS.md` and `CLAUDE.md` guidance authoritative for this slice.")
    lines.append("- Prefer source-of-truth governance records over derived surfaces, and keep validation obligations explicit.")
    hint = _AGENT_HINTS.get(agent_type.strip(), "")
    if hint:
        lines.append(f"- Agent-specific constraint: {hint}")
    return "\n".join(lines)


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
        if not line:
            continue
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
    return _single_line(sentence, limit=180)


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


def run_compass_log(*, project_dir: Path, summary: str, workstreams: list[str] | None = None) -> bool:
    workstreams = workstreams or []
    args = ["compass", "log", "--repo-root", ".", "--kind", "implementation", "--summary", summary]
    for workstream in workstreams[:4]:
        args.extend(["--workstream", workstream])
    completed = run_odylith(project_dir=project_dir, args=args, timeout=20)
    return bool(completed and completed.returncode == 0)


def utc_now_iso() -> str:
    return dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def append_agent_stream_event(*, project_dir: Path, event: dict[str, Any]) -> Path | None:
    runtime_dir = Path(project_dir).resolve() / "odylith" / "compass" / "runtime"
    if not runtime_dir.is_dir():
        return None
    stream_path = runtime_dir / "agent-stream.v1.jsonl"
    try:
        stream_path.parent.mkdir(parents=True, exist_ok=True)
        with stream_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
    except OSError:
        return None
    return stream_path
