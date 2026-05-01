"""Shared prompt-submit route locks for host fast paths."""

from __future__ import annotations

from odylith.runtime.intervention_engine import prompt_signal_runtime


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
            "hand-authored demonstration summary. Use the `odylith-show-me` skill if it is available. "
            "Otherwise run the first command that works from the repo root and capture stdout only: "
            "`./.odylith/bin/odylith show --repo-root .`; `odylith show --repo-root .`. "
            "Return that stdout directly. Do not run `start`, `doctor`, `version`, "
            "`intervention-status`, `visible-intervention`, host compatibility checks, "
            "or launcher-state explanations unless the user explicitly asks for diagnostics. "
            "If neither command can run, report only the shortest actionable Odylith show blocker."
        )
    if kind == "help":
        return (
            f"{_route_label(host_family=host_family, route='help')} first-match route lock: "
            "this prompt asks for the CLI help surface, "
            f"not a host capability summary, generic {host_name} capabilities, install, runtime, intervention, launcher, "
            "or repo diagnosis. Run the first command that works from the repo root and "
            "capture stdout only: `./.odylith/bin/odylith --help`; `odylith --help`. "
            "Return that stdout directly. Do not run `start`, `show`, `doctor`, `version`, "
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
            "`odylith capabilities --repo-root .`. Return that stdout directly."
        )
    return ""
