"""Shared helpers for Claude Code host surfaces rendered from Odylith state.

The Claude Code host surfaces (statusline, PreCompact snapshot, baked hook
runtime modules) all read the same Compass runtime snapshot, resolve the
same Claude project memory directory, and emit the same canonical hook
payloads. This module keeps those helpers in one place so the individual
surface modules stay focused on argparse and stdout/stderr handling.

This module reads state, runs cheap subprocess probes, computes paths, and
appends to bounded local files. It deliberately does not raise into its
callers: every helper degrades to a fail-soft empty result on any I/O,
parse, or subprocess failure so the Claude hook layer never aborts a turn
because Odylith state was missing or partial.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping


_COMPASS_RUNTIME_RELATIVE = Path("odylith") / "compass" / "runtime" / "current.v1.json"
_CLAUDE_CONFIG_DIR_ENV = "CLAUDE_CONFIG_DIR"
_CLAUDE_CONFIG_DIR_DEFAULT = "~/.claude"
_CLAUDE_PROJECT_DIR_ENV = "CLAUDE_PROJECT_DIR"
_SLUG_UNSAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")

AUTO_MEMORY_IMPORT = "@odylith-governed-brief.md"
AUTO_MEMORY_NOTE = "odylith-governed-brief.md"

# Shared governed-edit predicates for host post-edit/post-bash hooks.
# These are the Odylith source-of-truth subtrees whose mutation should
# trigger a selective governance refresh. Both the Claude PostToolUse
# hook (direct Write/Edit/MultiEdit) and the Codex post-bash checkpoint
# (edit-like Bash commands such as ``apply_patch``) import these so the
# "what counts as a governed edit?" definition has one source of truth.
GOVERNED_SOURCE_PREFIXES: tuple[str, ...] = (
    "odylith/radar/source/",
    "odylith/technical-plans/",
    "odylith/casebook/bugs/",
    "odylith/registry/source/",
    "odylith/atlas/source/",
)
# Scoped guidance companions live inside governed subtrees but do not
# represent governance truth. Their edits never require a selective
# refresh.
GOVERNED_IGNORED_BASENAMES: frozenset[str] = frozenset({"AGENTS.md", "CLAUDE.md"})


def should_refresh_governed_edit(path_token: str) -> bool:
    """Return True if the given repo-relative path is a governed edit worth refreshing."""
    if not path_token:
        return False
    path = Path(path_token)
    if path.name in GOVERNED_IGNORED_BASENAMES:
        return False
    normalized = path.as_posix()
    return any(normalized.startswith(prefix) for prefix in GOVERNED_SOURCE_PREFIXES)
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


def resolve_repo_root(repo_root: Path | str = ".") -> Path:
    """Resolve a caller-supplied repo root hint to an absolute path."""
    return Path(repo_root).expanduser().resolve()


def canonical_repo_root(project_dir: Path | str) -> Path:
    """Return the canonical Git repo root for a project directory if resolvable.

    Falls back to the resolved project directory on any Git failure. Used to
    compute the stable Claude project slug so that worktrees, symlinks, and
    nested Git common dirs all map to the same project memory directory.
    """
    root = Path(project_dir).expanduser().resolve()
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
    repo = Path(parts[0])
    for part in parts[1:index]:
        repo /= part
    return repo.resolve()


def claude_config_dir() -> Path:
    """Return the resolved Claude config directory (``$CLAUDE_CONFIG_DIR`` or default)."""
    token = str(os.environ.get(_CLAUDE_CONFIG_DIR_ENV, _CLAUDE_CONFIG_DIR_DEFAULT)).strip()
    return Path(token or _CLAUDE_CONFIG_DIR_DEFAULT).expanduser().resolve()


def project_slug(project_dir: Path | str) -> str:
    """Return the stable Claude project slug derived from the canonical repo root."""
    normalized = canonical_repo_root(project_dir).as_posix()
    slug = _SLUG_UNSAFE_RE.sub("-", normalized)
    return slug if slug.startswith("-") else f"-{slug.lstrip('-')}"


def project_memory_dir(project_dir: Path | str) -> Path:
    """Return the Claude project auto-memory directory for the given repo root."""
    return claude_config_dir() / "projects" / project_slug(project_dir) / "memory"


def load_compass_runtime(repo_root: Path | str = ".") -> Mapping[str, Any] | None:
    """Return the parsed Compass runtime snapshot or ``None`` on any failure."""
    root = resolve_repo_root(repo_root)
    path = root / _COMPASS_RUNTIME_RELATIVE
    try:
        if not path.is_file():
            return None
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return None
    return payload if isinstance(payload, Mapping) else None


def active_workstream_from_runtime(payload: Mapping[str, Any] | None) -> str:
    """Extract the first active workstream id from a Compass runtime snapshot."""
    if not isinstance(payload, Mapping):
        return ""
    focus = payload.get("execution_focus")
    if not isinstance(focus, Mapping):
        return ""
    scope = focus.get("global")
    if not isinstance(scope, Mapping):
        return ""
    workstreams = scope.get("workstreams")
    if not isinstance(workstreams, list):
        return ""
    for token in workstreams:
        candidate = str(token or "").strip().upper()
        if candidate:
            return candidate
    return ""


def active_workstream_headline(payload: Mapping[str, Any] | None) -> str:
    """Extract the global execution-focus headline from the Compass runtime."""
    if not isinstance(payload, Mapping):
        return ""
    focus = payload.get("execution_focus")
    if not isinstance(focus, Mapping):
        return ""
    scope = focus.get("global")
    if not isinstance(scope, Mapping):
        return ""
    return " ".join(str(scope.get("headline") or "").split()).strip()


def brief_generated_at(payload: Mapping[str, Any] | None) -> dt.datetime | None:
    """Parse the ``generated_utc`` timestamp from a Compass runtime snapshot."""
    if not isinstance(payload, Mapping):
        return None
    stamp = str(payload.get("generated_utc") or "").strip()
    if not stamp:
        return None
    try:
        parsed = dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def freshness_label(
    payload: Mapping[str, Any] | None,
    *,
    now: dt.datetime | None = None,
) -> str:
    """Return a compact freshness label for a Compass runtime snapshot."""
    parsed = brief_generated_at(payload)
    if parsed is None:
        return "no snapshot"
    current = now if now is not None else dt.datetime.now(tz=dt.timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=dt.timezone.utc)
    delta = current - parsed
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        return "fresh"
    if total_seconds < 120:
        return "fresh"
    minutes = total_seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h"
    days = hours // 24
    return f"{days}d"


def detect_host_family() -> str:
    """Return a compact host-family token for the active runtime."""
    explicit = str(os.environ.get("ODYLITH_HOST_FAMILY") or "").strip().lower()
    if explicit in {"codex", "claude"}:
        return explicit
    if os.environ.get(_CLAUDE_PROJECT_DIR_ENV):
        return "claude"
    if os.environ.get("CODEX_HOME") or os.environ.get("CODEX_HOST_RUNTIME"):
        return "codex"
    return "unknown"


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string with ``Z`` suffix."""
    return dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def collapse_whitespace(value: object, *, limit: int = 220) -> str:
    """Normalize whitespace for single-line rendering and truncate past ``limit``."""
    text = " ".join(str(value or "").split()).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def load_payload(raw: str | None = None) -> dict[str, Any]:
    """Parse a Claude hook stdin payload, returning ``{}`` on any failure.

    Claude hooks pipe JSON to the configured command on stdin. Callers
    invoke this with ``raw=None`` to read from ``sys.stdin`` (the normal
    hook path) or with an explicit ``raw`` string in tests. Any decode
    failure or non-mapping payload degrades to an empty dict so the hook
    surface stays fail-soft.
    """
    text = raw if raw is not None else sys.stdin.read()
    try:
        payload = json.loads(text or "{}")
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def project_launcher(project_dir: Path | str) -> Path:
    """Return the absolute path to the repo-local Odylith launcher."""
    return Path(project_dir).expanduser().resolve() / ".odylith" / "bin" / "odylith"


def run_odylith(
    *,
    project_dir: Path | str,
    args: list[str],
    timeout: int = 20,
) -> subprocess.CompletedProcess[str] | None:
    """Run the repo-local Odylith launcher with cheap timeouts and fail-soft.

    Returns the completed process on success, ``None`` on a missing
    launcher, OS error, or subprocess error. Callers must always check
    the return value before reading ``stdout``/``stderr``/``returncode``.
    """
    launcher = project_launcher(project_dir)
    if not launcher.is_file():
        return None
    try:
        return subprocess.run(
            [str(launcher), *args],
            cwd=str(Path(project_dir).expanduser().resolve()),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def load_runtime_snapshot(project_dir: Path | str) -> dict[str, Any]:
    """Return the Compass runtime snapshot as a dict, or ``{}`` on any failure.

    Some baked hook callers prefer a concrete dict (with mutating helpers
    operating on it) over the read-only mapping returned by
    :func:`load_compass_runtime`. This thin wrapper materializes the
    snapshot as a dict and degrades to an empty dict on any error.
    """
    payload = load_compass_runtime(project_dir)
    if not isinstance(payload, Mapping):
        return {}
    return dict(payload)


def _workstream_title_map(snapshot: Mapping[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for collection_key in ("current_workstreams", "workstream_catalog"):
        collection = snapshot.get(collection_key)
        if not isinstance(collection, list):
            continue
        for row in collection:
            if not isinstance(row, dict):
                continue
            idea_id = str(
                row.get("idea_id") or row.get("workstream") or row.get("id") or ""
            ).strip().upper()
            title = collapse_whitespace(row.get("title") or "")
            if idea_id and title and idea_id not in mapping:
                mapping[idea_id] = title
    return mapping


def active_workstream_lines(snapshot: Mapping[str, Any]) -> list[str]:
    """Return up to six markdown bullets describing the active workstream focus."""
    if not isinstance(snapshot, Mapping):
        return []
    focus = snapshot.get("execution_focus")
    if not isinstance(focus, Mapping):
        return []
    global_focus = focus.get("global")
    if not isinstance(global_focus, Mapping):
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


def next_action_lines(snapshot: Mapping[str, Any]) -> list[str]:
    """Return up to four markdown bullets describing the next-action queue."""
    if not isinstance(snapshot, Mapping):
        return []
    actions = snapshot.get("next_actions")
    if not isinstance(actions, list):
        return []
    lines: list[str] = []
    for row in actions[:4]:
        if not isinstance(row, dict):
            continue
        idea_id = str(row.get("idea_id") or "").strip().upper()
        action = collapse_whitespace(row.get("action") or "")
        if not action:
            continue
        lines.append(f"- {idea_id}: {action}" if idea_id else f"- {action}")
    return lines


def risk_lines(snapshot: Mapping[str, Any]) -> list[str]:
    """Return up to three markdown bullets describing live risk signals."""
    if not isinstance(snapshot, Mapping):
        return []
    risks = snapshot.get("risks")
    if not isinstance(risks, Mapping):
        return []
    lines: list[str] = []
    for key in ("traceability_warnings", "traceability", "bugs"):
        value = risks.get(key)
        if not isinstance(value, list):
            continue
        for item in value[:2]:
            if isinstance(item, dict):
                title = collapse_whitespace(
                    item.get("title") or item.get("summary") or item.get("bug_id") or ""
                )
                if title:
                    lines.append(f"- {title}")
            else:
                title = collapse_whitespace(item)
                if title:
                    lines.append(f"- {title}")
        if lines:
            break
    return lines[:3]


def build_memory_note(
    *,
    project_dir: Path | str,
    snapshot: Mapping[str, Any],
    start_output: str = "",
) -> str:
    """Render the canonical Claude project auto-memory brief markdown body.

    Pure function: identical inputs always produce identical output. The
    memory note is used both by the SessionStart bake (live write) and by
    the PreCompact snapshot writer (cross-compaction handoff).
    """
    lines = [
        "# Odylith Governed Brief",
        "",
        "This note is managed by the repo's Claude SessionStart hook.",
        "Treat it as a current cross-session grounding snapshot derived from Odylith runtime state, not as source-of-truth governance.",
        "",
    ]
    generated = ""
    if isinstance(snapshot, Mapping):
        generated = collapse_whitespace(
            snapshot.get("generated_utc") or snapshot.get("now_local_iso") or ""
        )
    if generated:
        lines.append(f"- Updated: {generated}")
    lines.append(
        "- Source: `odylith/compass/runtime/current.v1.json` when present, otherwise the repo-local `odylith start` result."
    )
    lines.append("")
    if isinstance(snapshot, Mapping) and snapshot:
        focus = snapshot.get("execution_focus")
        global_focus = focus.get("global") if isinstance(focus, Mapping) else {}
        headline = collapse_whitespace(
            global_focus.get("headline") if isinstance(global_focus, Mapping) else ""
        )
        if headline:
            lines.extend(["## Live Focus", f"- Headline: {headline}"])
            active = active_workstream_lines(snapshot)
            if active:
                lines.append("- Active workstreams:")
                lines.extend(active)
            verified = snapshot.get("verified_scoped_workstreams")
            verified_24h = (
                verified.get("24h") if isinstance(verified, Mapping) else []
            )
            if isinstance(verified_24h, list) and verified_24h:
                tokens = ", ".join(
                    str(item).strip() for item in verified_24h[:8] if str(item).strip()
                )
                if tokens:
                    lines.append(f"- Verified in last 24h: {tokens}")
            lines.append("")
        next_lines = next_action_lines(snapshot)
        if next_lines:
            lines.append("## Next Actions")
            lines.extend(next_lines)
            lines.append("")
        risks = risk_lines(snapshot)
        if risks:
            lines.append("## Risks")
            lines.extend(risks)
            lines.append("")
    summary = collapse_whitespace(start_output)
    if summary:
        lines.extend(["## Startup", f"- {summary}", ""])
    return "\n".join(lines).rstrip() + "\n"


def write_project_memory(
    *,
    project_dir: Path | str,
    snapshot: Mapping[str, Any],
    start_output: str = "",
) -> Path | None:
    """Write the auto-memory note + managed import block, fail-soft on errors.

    Creates ``$CLAUDE_CONFIG_DIR/projects/<slug>/memory/odylith-governed-brief.md``
    and ensures the project ``MEMORY.md`` carries the managed import block.
    Returns the absolute path to the brief on success, ``None`` on failure.
    """
    try:
        memory_dir = project_memory_dir(project_dir)
        memory_dir.mkdir(parents=True, exist_ok=True)
        note_path = memory_dir / AUTO_MEMORY_NOTE
        note_path.write_text(
            build_memory_note(
                project_dir=project_dir,
                snapshot=snapshot,
                start_output=start_output,
            ),
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


def build_subagent_context(*, project_dir: Path | str, agent_type: str = "") -> str:
    """Render the canonical Claude SubagentStart additionalContext payload."""
    snapshot = load_runtime_snapshot(project_dir)
    lines = ["Odylith subagent grounding:"]
    if snapshot:
        focus = snapshot.get("execution_focus")
        global_focus = focus.get("global") if isinstance(focus, Mapping) else {}
        headline = collapse_whitespace(
            global_focus.get("headline") if isinstance(global_focus, Mapping) else ""
        )
        if headline:
            lines.append(f"- Live focus: {headline}")
        active = active_workstream_lines(snapshot)
        if active:
            lines.append("- Active workstreams:")
            lines.extend(active[:4])
        next_actions = next_action_lines(snapshot)
        if next_actions:
            lines.append("- Next actions:")
            lines.extend(next_actions[:3])
    lines.append("- Keep nearest `AGENTS.md` and `CLAUDE.md` guidance authoritative for this slice.")
    lines.append("- Prefer source-of-truth governance records over derived surfaces, and keep validation obligations explicit.")
    hint = _AGENT_HINTS.get(str(agent_type or "").strip(), "")
    if hint:
        lines.append(f"- Agent-specific constraint: {hint}")
    return "\n".join(lines)


def meaningful_stop_summary(text: str) -> str:
    """Extract a single short sentence from a Stop hook payload, or return ''.

    The Stop hook receives the assistant's final response. Many turns end
    with chit-chat ("Would you like ..."), code blocks, or trivial
    acknowledgements that should not be logged to Compass. This filter
    keeps only summaries that are at least 60 characters, contain an
    action verb, and do not look like questions or offers.
    """
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
    return collapse_whitespace(sentence, limit=180)


def extract_workstreams(text: str) -> list[str]:
    """Return de-duplicated ``B-NNN`` workstream tokens in encounter order."""
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
    """Append a Compass timeline event for a meaningful Claude stop summary."""
    workstreams = workstreams or []
    args = [
        "compass",
        "log",
        "--repo-root",
        ".",
        "--kind",
        "implementation",
        "--summary",
        summary,
    ]
    for workstream in workstreams[:4]:
        args.extend(["--workstream", workstream])
    completed = run_odylith(project_dir=project_dir, args=args, timeout=20)
    return bool(completed and completed.returncode == 0)


def append_agent_stream_event(
    *,
    project_dir: Path | str,
    event: dict[str, Any],
) -> Path | None:
    """Append one JSONL event to the Compass agent-stream log, fail-soft on errors."""
    runtime_dir = Path(project_dir).expanduser().resolve() / "odylith" / "compass" / "runtime"
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
