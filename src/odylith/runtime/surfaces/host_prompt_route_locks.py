"""Shared prompt-submit route locks for host fast paths."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

from odylith.runtime.intervention_engine import prompt_signal_runtime

_ROUTE_LOCK_DIR = Path(".odylith") / "runtime" / "host-route-locks"
_ROUTE_LOCK_TTL_SECONDS = 15 * 60
_FALLBACK_SESSION = "latest"


def _host_name(host_family: str) -> str:
    token = str(host_family or "").strip().casefold()
    if token == "claude":
        return "Claude Code"
    if token == "codex":
        return "Codex"
    return "the active host"


def _host_inventory_terms(host_family: str) -> str:
    token = str(host_family or "").strip().casefold()
    if token == "claude":
        return "Claude tools, skills, memory, local files, or generic Claude Code capability prose"
    if token == "codex":
        return "Codex tools, skills, local files, or generic Codex capability prose"
    return "host tools, skills, local files, or generic host capability prose"


def _route_label(*, host_family: str, route: str) -> str:
    token = str(host_family or "").strip().casefold()
    prefix = "Odylith Codex" if token == "codex" else "Odylith"
    return f"{prefix} {route}"


def _host_token(host_family: str) -> str:
    token = str(host_family or "").strip().casefold()
    return re.sub(r"[^a-z0-9_-]+", "-", token or "host").strip("-") or "host"


def _session_token(session_id: object) -> str:
    token = str(session_id or "").strip()
    if not token:
        return _FALLBACK_SESSION
    return re.sub(r"[^A-Za-z0-9._-]+", "-", token).strip("-")[:80] or _FALLBACK_SESSION


def _route_lock_path(repo_root: Path | str, *, host_family: str, session_id: object) -> Path:
    return (
        Path(repo_root).expanduser().resolve()
        / _ROUTE_LOCK_DIR
        / f"{_host_token(host_family)}-{_session_token(session_id)}.json"
    )


def _route_lock_paths(repo_root: Path | str, *, host_family: str, session_id: object) -> tuple[Path, ...]:
    session_path = _route_lock_path(repo_root, host_family=host_family, session_id=session_id)
    fallback_path = _route_lock_path(repo_root, host_family=host_family, session_id=_FALLBACK_SESSION)
    return (session_path,) if session_path == fallback_path else (session_path, fallback_path)


def record_active_route_lock(
    *,
    repo_root: Path | str,
    host_family: str,
    prompt: object,
    session_id: object = "",
) -> None:
    """Persist a short-lived route lock for host Bash guards."""

    route = prompt_signal_runtime.passthrough_prompt_kind(prompt)
    if route not in {"show", "help", "capabilities"}:
        clear_active_route_lock(repo_root=repo_root, host_family=host_family, session_id=session_id)
        return
    payload = {
        "route": route,
        "created_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "session_id": str(session_id or "").strip(),
    }
    for path in _route_lock_paths(repo_root, host_family=host_family, session_id=session_id):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
        except OSError:
            continue


def clear_active_route_lock(
    *,
    repo_root: Path | str,
    host_family: str,
    session_id: object = "",
) -> None:
    """Clear any active route lock for the current host/session."""

    for path in _route_lock_paths(repo_root, host_family=host_family, session_id=session_id):
        try:
            path.unlink()
        except FileNotFoundError:
            continue
        except OSError:
            continue


def _load_active_route_lock(
    *,
    repo_root: Path | str,
    host_family: str,
    session_id: object = "",
) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    for path in _route_lock_paths(repo_root, host_family=host_family, session_id=session_id):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
        if not isinstance(payload, dict):
            continue
        stamp = str(payload.get("created_utc") or "").strip()
        try:
            created = dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except ValueError:
            continue
        if created.tzinfo is None:
            created = created.replace(tzinfo=dt.timezone.utc)
        if (now - created).total_seconds() > _ROUTE_LOCK_TTL_SECONDS:
            clear_active_route_lock(repo_root=repo_root, host_family=host_family, session_id=session_id)
            continue
        route = str(payload.get("route") or "").strip()
        if route in {"show", "help", "capabilities"}:
            return route
    return ""


def _normalize_command_segment(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+2>\s*/dev/null", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _allowed_segment_for_route(segment: str, route: str) -> bool:
    text = _normalize_command_segment(segment)
    if route == "show":
        return bool(re.fullmatch(r"(?:\./\.odylith/bin/odylith|odylith) show --repo-root \.", text))
    if route == "help":
        return bool(re.fullmatch(r"(?:\./\.odylith/bin/odylith|odylith) --help", text))
    if route == "capabilities":
        return bool(re.fullmatch(r"(?:\./\.odylith/bin/odylith|odylith) capabilities --repo-root \.", text))
    return False


def bash_route_lock_denial_reason(
    *,
    repo_root: Path | str,
    host_family: str,
    session_id: object = "",
    command: object,
) -> str:
    """Return a deny reason when Bash drifts outside an active passthrough route."""

    route = _load_active_route_lock(repo_root=repo_root, host_family=host_family, session_id=session_id)
    if not route:
        return ""
    command_text = str(command or "").strip()
    if not command_text:
        return ""
    segments = [segment for segment in re.split(r"\s*\|\|\s*", command_text) if segment.strip()]
    if segments and all(_allowed_segment_for_route(segment, route) for segment in segments):
        return ""
    if route == "show":
        expected = "./.odylith/bin/odylith show --repo-root ."
    elif route == "help":
        expected = "./.odylith/bin/odylith --help"
    else:
        expected = "./.odylith/bin/odylith capabilities --repo-root ."
    return (
        f"Odylith {route} route lock is active. Run only `{expected}`, return stdout verbatim, "
        "and stop the turn; extra Bash probes are blocked."
    )


def route_lock_context(*, host_family: str, prompt: object) -> str:
    """Return first-match route-lock context for prompt-only Odylith lanes."""

    kind = prompt_signal_runtime.passthrough_prompt_kind(prompt)
    host_name = _host_name(host_family)
    if kind == "show":
        return (
            f"{_route_label(host_family=host_family, route='show-me')} first-match route lock: "
            "this prompt asks for the advisory "
            "`odylith show` repo-capability demo. You must not answer as generic "
            f"{host_name}, list {host_name} tool, skill, or memory inventories, inspect docs, "
            "list repository files, report branch cleanliness, dirty paths, or tmp clone noise, "
            "describe install posture, mention impact packets, summarize module counts, "
            "explain spawn policy, or ask what the user wants. You must not write a "
            "hand-authored demonstration summary. You must not create, scaffold, edit, or test "
            "example application files such as HTML/CSS/JS demos, toy apps, sample devices, or "
            "placeholder products just because the repo is empty. Use the `odylith-show-me` skill if it is available. "
            "Otherwise run the first command that works from the repo root and capture stdout only: "
            "`./.odylith/bin/odylith show --repo-root .`; `odylith show --repo-root .`. "
            "Return that stdout directly, then end the turn immediately. Do not run any other Bash command before or after it. "
            "Do not run `start`, `doctor`, `version`, "
            "`intervention-status`, `visible-intervention`, host compatibility checks, "
            "or launcher-state explanations unless the user explicitly asks for diagnostics. "
            "If neither command can run, report only the shortest actionable Odylith show blocker; "
            "do not substitute generic host work."
        )
    if kind == "help":
        return (
            f"{_route_label(host_family=host_family, route='help')} first-match route lock: "
            "this prompt asks for the CLI help surface, "
            f"not a host capability summary, generic {host_name} capabilities, install, runtime, intervention, launcher, "
            "or repo diagnosis. Run the first command that works from the repo root and "
            "capture stdout only: `./.odylith/bin/odylith --help`; `odylith --help`. "
            "Return that stdout directly, then end the turn immediately. Do not run any other Bash command before or after it. "
            "Do not run `start`, `show`, `doctor`, `version`, "
            "`intervention-status`, `visible-intervention`, host compatibility checks, "
            "or launcher-state explanations unless the user explicitly asks for diagnostics."
        )
    if kind == "capabilities":
        return (
            f"{_route_label(host_family=host_family, route='capability-inventory')} route lock: "
            "this prompt asks for Odylith's "
            "product-owned capabilities, engines, and architecture map. Do not infer "
            "the taxonomy from `odylith --help`, `odylith show`, "
            f"{_host_inventory_terms(host_family)}. Run the first command that works from "
            "the repo root and capture stdout only: "
            "`./.odylith/bin/odylith capabilities --repo-root .`; "
            "`odylith capabilities --repo-root .`. Return that stdout directly, "
            "then end the turn immediately. Do not run any other Bash command before or after it."
        )
    return ""
