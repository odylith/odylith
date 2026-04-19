"""Cross-host status surface for Odylith Observation, Proposal, and Assist."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any
from typing import Mapping

from odylith.common.json_objects import load_json_object
from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.common import claude_cli_capabilities
from odylith.runtime.intervention_engine import delivery_ledger
from odylith.runtime.intervention_engine import visibility_contract
from odylith.runtime.intervention_engine import visibility_broker
from odylith.runtime.intervention_engine import visibility_replay
from odylith.runtime.intervention_engine.visibility_contract import normalize_string as _normalize_string
from odylith.runtime.intervention_engine.visibility_contract import normalize_token as _normalize_token


def _load_json(path: Path) -> dict[str, Any]:
    return load_json_object(path)


def _matcher_tokens(value: Any) -> set[str]:
    matcher = _normalize_string(value)
    if matcher in {"*", ".*"}:
        return {"*"}
    return {token.strip() for token in re.split(r"[|,\s]+", matcher) if token.strip()}


def _matcher_covers(value: Any, required: tuple[str, ...]) -> bool:
    tokens = _matcher_tokens(value)
    return "*" in tokens or all(token in tokens for token in required)


def _codex_hook_command_present(
    payload: Mapping[str, Any],
    event_name: str,
    command_token: str,
    *,
    matcher_tokens: tuple[str, ...] = (),
) -> bool:
    bucket = payload.get(event_name)
    if not isinstance(bucket, list):
        return False
    for group in bucket:
        if not isinstance(group, Mapping):
            continue
        if not _matcher_covers(group.get("matcher"), matcher_tokens):
            continue
        hooks = group.get("hooks")
        if not isinstance(hooks, list):
            continue
        for hook in hooks:
            if isinstance(hook, Mapping) and command_token in str(hook.get("command") or ""):
                return True
    return False


def _codex_hooks_feature_configured(repo_root: Path) -> bool:
    path = repo_root / ".codex" / "config.toml"
    if not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    return bool(re.search(r"(?m)^\s*codex_hooks\s*=\s*true\s*$", text))


def _codex_static_readiness(repo_root: Path) -> dict[str, Any]:
    hooks = _load_json(repo_root / ".codex" / "hooks.json")
    checks = {
        "launcher": (repo_root / ".odylith" / "bin" / "odylith").is_file(),
        "repo_guidance": (repo_root / "AGENTS.md").is_file(),
        "codex_hooks_feature_configured": _codex_hooks_feature_configured(repo_root),
        "prompt_context_hook": _codex_hook_command_present(hooks, "UserPromptSubmit", "codex prompt-context"),
        "post_bash_checkpoint_hook": _codex_hook_command_present(
            hooks,
            "PostToolUse",
            "codex post-bash-checkpoint",
            matcher_tokens=("Bash",),
        ),
        "stop_summary_hook": _codex_hook_command_present(hooks, "Stop", "codex stop-summary"),
    }
    return {
        "host_family": "codex",
        "ready": all(checks.values()),
        "checks": checks,
        "activation_note": (
            "Codex hook wiring is statically ready; trusted-project approval and a fresh/reloaded session are still required for live host delivery."
        ),
    }


def _claude_static_readiness(repo_root: Path) -> dict[str, Any]:
    claude_cli_capabilities.clear_claude_cli_capability_cache()
    snapshot = claude_cli_capabilities.inspect_claude_cli_capabilities(
        repo_root=repo_root,
        probe_version=False,
    )
    checks = {
        "launcher": bool(snapshot.launcher_present),
        "repo_guidance": bool(snapshot.repo_claude_md_present or snapshot.repo_agents_md_present),
        "project_settings": bool(snapshot.project_settings_present),
        "prompt_context_hook": bool(snapshot.supports_prompt_context_hook),
        "prompt_teaser_hook": bool(snapshot.supports_prompt_teaser_hook),
        "post_edit_checkpoint_hook": bool(snapshot.supports_post_edit_checkpoint_hook),
        "post_bash_checkpoint_hook": bool(snapshot.supports_post_bash_checkpoint_hook),
        "stop_summary_hook": bool(snapshot.supports_stop_summary_hook),
    }
    return {
        "host_family": "claude",
        "ready": all(checks.values()),
        "checks": checks,
        "activation_note": "Claude project hooks are statically ready; restart the session if this repo changed after the current chat opened.",
    }


def _static_readiness(*, repo_root: Path, host_family: str) -> dict[str, Any]:
    host = _normalize_token(host_family)
    if host == "claude":
        return _claude_static_readiness(repo_root)
    return _codex_static_readiness(repo_root)


def _chat_visible_proof(*, ledger: Mapping[str, Any], static_ready: bool) -> dict[str, Any]:
    visible_count = int(ledger.get("visible_event_count") or 0)
    chat_confirmed_count = int(ledger.get("chat_confirmed_event_count") or 0)
    unconfirmed_count = int(ledger.get("unconfirmed_event_count") or 0)
    status = visibility_contract.proof_status_from_counts(
        visible_count=visible_count,
        chat_confirmed_count=chat_confirmed_count,
        unconfirmed_count=unconfirmed_count,
        static_ready=static_ready,
    )
    latest = ledger.get("latest_visible_event") if isinstance(ledger.get("latest_visible_event"), Mapping) else {}
    latest_unconfirmed = (
        ledger.get("latest_unconfirmed_event")
        if isinstance(ledger.get("latest_unconfirmed_event"), Mapping)
        else {}
    )
    if status in {
        "chat_confirmed_with_pending_confirmation",
        "ledger_visible_with_pending_confirmation",
        "pending_confirmation",
    }:
        latest_status = _normalize_token(latest_unconfirmed.get("delivery_status")) or "unknown"
        latest_channel = _normalize_token(latest_unconfirmed.get("delivery_channel")) or "unknown"
        visible_prefix = (
            f"{visible_count} ledger-visible event(s) exist, {chat_confirmed_count} chat-confirmed, but "
            if visible_count
            else "No ledger-visible or chat-confirmed event is recorded yet, and "
        )
        return {
            "status": status,
            "summary": (
                f"{visible_prefix}{unconfirmed_count} Odylith beat(s) still require exact chat confirmation; "
                f"latest pending delivery is {latest_status} via {latest_channel}."
            ),
            "latest_delivery_channel": latest_channel,
            "visible_event_count": visible_count,
            "chat_confirmed_event_count": chat_confirmed_count,
            "unconfirmed_event_count": unconfirmed_count,
        }
    if status == "proven_this_session":
        channel = _normalize_token(latest.get("delivery_channel")) or "unknown"
        return {
            "status": status,
            "summary": f"{chat_confirmed_count} chat-confirmed Odylith event(s) recorded for this session; latest via {channel}.",
            "latest_delivery_channel": channel,
            "visible_event_count": visible_count,
            "chat_confirmed_event_count": chat_confirmed_count,
            "unconfirmed_event_count": 0,
        }
    if status == "ledger_visible_unconfirmed":
        channel = _normalize_token(latest.get("delivery_channel")) or "unknown"
        return {
            "status": status,
            "summary": (
                f"{visible_count} ledger-visible event(s) recorded for this session, "
                f"but 0 chat-confirmed; latest via {channel}."
            ),
            "latest_delivery_channel": channel,
            "visible_event_count": visible_count,
            "chat_confirmed_event_count": chat_confirmed_count,
            "unconfirmed_event_count": 0,
        }
    if status == "unproven_this_session":
        return {
            "status": status,
            "summary": (
                "No ledger-visible or chat-confirmed event is recorded for this session; the assistant must render the "
                "visible-intervention fallback directly before claiming the UX is active."
            ),
            "latest_delivery_channel": "",
            "visible_event_count": 0,
            "chat_confirmed_event_count": 0,
            "unconfirmed_event_count": 0,
        }
    return {
        "status": "degraded",
        "summary": "Static readiness is degraded; do not claim live intervention visibility for this session.",
        "latest_delivery_channel": "",
        "visible_event_count": 0,
        "chat_confirmed_event_count": 0,
        "unconfirmed_event_count": 0,
    }


def inspect_intervention_status(
    *,
    repo_root: Path | str = ".",
    host_family: str,
    session_id: str = "",
    limit: int = 200,
    last_assistant_message: str = "",
) -> dict[str, Any]:
    root = Path(repo_root).expanduser().resolve()
    host = _normalize_token(host_family) or "codex"
    resolved_session = _normalize_string(session_id) or agent_runtime_contract.default_host_session_id()
    readiness = _static_readiness(repo_root=root, host_family=host)
    confirmed_events = visibility_broker.confirm_assistant_chat_delivery(
        repo_root=root,
        host_family=host,
        session_id=resolved_session,
        last_assistant_message=last_assistant_message,
        render_surface=f"{host}_intervention_status",
    ) if _normalize_string(last_assistant_message) else []
    ledger = delivery_ledger.delivery_snapshot(
        repo_root=root,
        host_family=host,
        session_id=resolved_session,
        limit=limit,
    )
    activation = "ready" if bool(readiness.get("ready")) else "degraded"
    proof = _chat_visible_proof(
        ledger=ledger,
        static_ready=bool(readiness.get("ready")),
    )
    replay_blocks = visibility_replay.replayable_chat_blocks(
        repo_root=root,
        host_family=host,
        session_id=resolved_session,
        limit=limit,
        include_assist=True,
        include_teaser=False,
    )
    replay_markdown = "\n\n".join(
        visibility_contract.normalize_block_string(row.get("display_markdown"))
        for row in replay_blocks
        if visibility_contract.normalize_block_string(row.get("display_markdown"))
    ).strip()
    pending = ledger.get("pending_proposal_state") if isinstance(ledger.get("pending_proposal_state"), Mapping) else {}
    return {
        "version": "v1",
        "host_family": host,
        "repo_root": str(root),
        "session_id": resolved_session,
        "activation": activation,
        "static_readiness": readiness,
        "chat_visibility_contract": (
            "Use hook output when the host visibly renders it; otherwise the assistant-render fallback must speak the same Markdown directly."
        ),
        "chat_visible_proof": proof,
        "assistant_visible_replay_markdown": replay_markdown,
        "assistant_visible_replay_count": len(replay_blocks),
        "assistant_visible_replay_blocks": replay_blocks,
        "active_lanes": delivery_ledger.active_lane_matrix(host_family=host),
        "delivery_ledger": ledger,
        "chat_confirmed_event_count": len(confirmed_events),
        "pending_proposal_count": int(pending.get("pending_count") or 0),
        "fresh_session_required_after_runtime_change": True,
        "smoke_command": (
            f"odylith {host} visible-intervention --repo-root . --phase prompt_submit "
            '--prompt "I do not think it is working"'
        ),
    }


def _check_label(value: bool) -> str:
    return "yes" if bool(value) else "no"


def _format_ratio(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "n/a"


def render_intervention_status(report: Mapping[str, Any]) -> str:
    host = _normalize_token(report.get("host_family")) or "codex"
    host_label = "Claude" if host == "claude" else "Codex"
    activation = _normalize_token(report.get("activation")) or "unknown"
    readiness = report.get("static_readiness") if isinstance(report.get("static_readiness"), Mapping) else {}
    checks = readiness.get("checks") if isinstance(readiness.get("checks"), Mapping) else {}
    ledger = report.get("delivery_ledger") if isinstance(report.get("delivery_ledger"), Mapping) else {}
    proof = report.get("chat_visible_proof") if isinstance(report.get("chat_visible_proof"), Mapping) else {}
    latest = ledger.get("latest_visible_event") if isinstance(ledger.get("latest_visible_event"), Mapping) else {}
    pending_count = int(report.get("pending_proposal_count") or 0)
    lines = [
        "**Odylith Intervention Status**",
        f"Host: {host_label}",
        f"Activation: {activation}",
        f"Session: `{_normalize_string(report.get('session_id')) or 'unknown'}`",
        f"Chat-visible contract: {_normalize_string(report.get('chat_visibility_contract'))}",
        (
            "Chat-visible proof: "
            f"{_normalize_token(proof.get('status')) or 'unknown'} - "
            f"{_normalize_string(proof.get('summary')) or 'no proof summary available.'}"
        ),
    ]
    activation_note = _normalize_string(readiness.get("activation_note"))
    if activation_note:
        lines.append(f"Fresh-session note: {activation_note}")
    lines.append("")
    lines.append("Readiness checks:")
    for key, value in checks.items():
        label = key.replace("_", " ")
        lines.append(f"- {label}: {_check_label(bool(value))}")
    lines.append("")
    lines.append("Active UX lanes:")
    lanes = report.get("active_lanes") if isinstance(report.get("active_lanes"), list) else []
    for lane in lanes:
        if not isinstance(lane, Mapping):
            continue
        lines.append(
            f"- {_normalize_string(lane.get('lane'))}: {_normalize_string(lane.get('phase'))}; {_normalize_string(lane.get('visibility'))}."
        )
    lines.append("")
    if latest:
        lines.append(
            "Last visible Odylith beat: "
            f"{_normalize_string(latest.get('kind')) or 'event'} via "
            f"{_normalize_string(latest.get('delivery_channel')) or 'unknown'}"
            f" at {_normalize_string(latest.get('ts_iso')) or 'unknown time'}."
        )
    else:
        lines.append("Last visible Odylith beat: none recorded for this session yet.")
    lines.append(
        f"Ledger: {int(ledger.get('event_count') or 0)} recent event(s), "
        f"{int(ledger.get('visible_event_count') or 0)} ledger-visible event(s), "
        f"{int(ledger.get('chat_confirmed_event_count') or 0)} chat-confirmed event(s), "
        f"{int(ledger.get('unconfirmed_event_count') or 0)} pending chat-confirmation event(s), "
        f"{pending_count} pending proposal(s)."
    )
    visibility_ratios = ledger.get("visibility_ratios")
    if isinstance(visibility_ratios, Mapping):
        lines.append("Visibility ratios:")
        for family, label in (
            ("teaser", "Teaser diagnostic"),
            ("ambient", "Ambient"),
            ("intervention", "Observation/Proposal"),
            ("assist", "Assist"),
        ):
            bucket = visibility_ratios.get(family)
            if not isinstance(bucket, Mapping):
                continue
            total = int(bucket.get("total") or 0)
            ledger_visible = int(bucket.get("ledger_visible") or 0)
            chat_confirmed = int(bucket.get("chat_confirmed") or 0)
            pending_confirmation = int(bucket.get("pending_confirmation") or 0)
            lines.append(
                f"- {label}: ledger {ledger_visible}/{total} ({_format_ratio(bucket.get('ledger_visible_ratio'))}); "
                f"chat-confirmed {chat_confirmed}/{total} ({_format_ratio(bucket.get('chat_confirmed_ratio'))}); "
                f"pending confirmation {pending_confirmation}."
            )
    confirmed_count = int(report.get("chat_confirmed_event_count") or 0)
    if confirmed_count:
        lines.append(f"Chat transcript confirmations recorded on this probe: {confirmed_count}.")
    replay = visibility_contract.normalize_block_string(report.get("assistant_visible_replay_markdown"))
    if replay:
        lines.append("")
        lines.append("Assistant-visible replay:")
        lines.append(replay)
    lines.append(f"Fast smoke: `{_normalize_string(report.get('smoke_command'))}`")
    return "\n".join(lines).strip()


def main_with_host(host_family: str, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=f"odylith {host_family} intervention-status",
        description="Report low-latency Odylith intervention activation and visible-delivery posture.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for intervention status.")
    parser.add_argument("--session-id", default="", help="Host session id to inspect.")
    parser.add_argument("--limit", type=int, default=200, help="Recent intervention events to inspect.")
    parser.add_argument(
        "--last-assistant-message",
        default="",
        help="Optional latest assistant text; confirms exact Odylith Markdown as chat-visible proof.",
    )
    parser.add_argument("--json", action="store_true", help="Emit status as JSON.")
    args = parser.parse_args(list(argv or sys.argv[1:]))
    report = inspect_intervention_status(
        repo_root=args.repo_root,
        host_family=host_family,
        session_id=args.session_id,
        limit=args.limit,
        last_assistant_message=args.last_assistant_message,
    )
    if args.json:
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(render_intervention_status(report) + "\n")
    return 0 if _normalize_token(report.get("activation")) == "ready" else 1


__all__ = ["inspect_intervention_status", "main_with_host", "render_intervention_status"]
