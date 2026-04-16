"""Claude Code UserPromptSubmit hook: anchor-driven Odylith context resolution.

When the user submits a prompt, Claude Code fires the
``UserPromptSubmit`` hook with the prompt text. This baked module mirrors
the legacy ``.claude/hooks/user-prompt-context.py`` script and runs
``odylith context --repo-root . <ref>`` for the first ``B-NNN`` /
``CB-NNN`` / ``D-NNN`` anchor it finds in the prompt. The resulting
context summary is printed on stdout so Claude Code can fold it into the
turn without the user typing the explicit ``odylith context`` command.

Anchor parsing is conservative: only repo-style id tokens are picked up,
nothing fancier. Failures degrade to a no-op return.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping

from odylith.runtime.intervention_engine import conversation_surface
from odylith.runtime.intervention_engine import host_surface_runtime
from odylith.runtime.intervention_engine import surface_runtime as intervention_surface_runtime
from odylith.runtime.surfaces import claude_host_shared


_ANCHOR_RE = re.compile(r"\b(?:B|CB|D)-\d{3,}\b")


def _context_summary(output: str, ref: str) -> str:
    text = str(output or "").strip()
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    payload_text = ""
    for index, line in enumerate(lines):
        if line.startswith("{"):
            payload_text = "\n".join(lines[index:])
            break
    if not payload_text:
        return f"Odylith anchor {ref}: context resolved."
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        return f"Odylith anchor {ref}: context resolved."
    if not isinstance(payload, Mapping):
        return f"Odylith anchor {ref}: context resolved."
    targets = payload.get("target_resolution")
    if isinstance(targets, Mapping):
        candidates = targets.get("candidate_targets")
        if isinstance(candidates, list) and candidates:
            first = candidates[0]
            if isinstance(first, Mapping):
                path = str(first.get("path", "")).strip()
                if path:
                    return f"Odylith anchor {ref}: primary target {path}."
    docs = payload.get("relevant_docs")
    if isinstance(docs, list) and docs:
        return f"Odylith anchor {ref}: relevant doc {docs[0]}."
    return f"Odylith anchor {ref}: context resolved."


def _prompt_conversation_bundle(
    *,
    repo_root: Path | str,
    prompt: str,
    session_id: str = "",
    bundle_override: Mapping[str, Any] | None = None,
    intervention_bundle_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if isinstance(bundle_override, Mapping):
        return dict(bundle_override)
    observation = intervention_surface_runtime.observation_envelope(
        host_family="claude",
        turn_phase="prompt_submit",
        session_id=session_id,
        prompt_excerpt=prompt,
    )
    if isinstance(intervention_bundle_override, Mapping):
        return {"intervention_bundle": dict(intervention_bundle_override)}
    return conversation_surface.build_conversation_bundle(
        repo_root=Path(repo_root).expanduser().resolve(),
        observation=observation,
    )


def render_prompt_context(
    *,
    repo_root: Path | str = ".",
    prompt: str,
    session_id: str = "",
    context_output_override: str | None = None,
    conversation_bundle_override: Mapping[str, Any] | None = None,
    intervention_bundle_override: Mapping[str, Any] | None = None,
) -> str:
    """Pure renderer used by the live hook and by tests."""
    refs = list(dict.fromkeys(_ANCHOR_RE.findall(str(prompt or ""))))
    bundle = _prompt_conversation_bundle(
        repo_root=repo_root,
        prompt=prompt,
        session_id=session_id,
        bundle_override=conversation_bundle_override,
        intervention_bundle_override=intervention_bundle_override,
    )
    live_text = conversation_surface.render_live_text(
        bundle,
        markdown=False,
        include_proposal=False,
        prefer_ambient_over_teaser=True,
    )
    parts: list[str] = []
    if refs:
        ref = refs[0]
        if context_output_override is not None:
            parts.append(_context_summary(context_output_override, ref))
        else:
            completed = claude_host_shared.run_odylith(
                project_dir=repo_root,
                args=["context", "--repo-root", ".", ref],
                timeout=20,
            )
            if completed is not None:
                parts.append(_context_summary(completed.stdout or "", ref))
    if live_text:
        parts.append(live_text)
    return "\n\n".join(part for part in parts if part).strip()


def render_prompt_system_message(
    *,
    repo_root: Path | str = ".",
    prompt: str,
    session_id: str = "",
    conversation_bundle_override: Mapping[str, Any] | None = None,
    intervention_bundle_override: Mapping[str, Any] | None = None,
) -> str:
    bundle = _prompt_conversation_bundle(
        repo_root=repo_root,
        prompt=prompt,
        session_id=session_id,
        bundle_override=conversation_bundle_override,
        intervention_bundle_override=intervention_bundle_override,
    )
    return conversation_surface.render_live_text(
        bundle,
        markdown=False,
        include_proposal=False,
        prefer_ambient_over_teaser=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith claude prompt-context",
        description="Render the Odylith-grounded Claude UserPromptSubmit hook output.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for Odylith context resolution.")
    parser.add_argument(
        "--payload",
        default="",
        help="Optional explicit Claude UserPromptSubmit payload JSON (defaults to stdin).",
    )
    args = parser.parse_args(list(argv or sys.argv[1:]))
    repo_root = claude_host_shared.resolve_repo_root(args.repo_root)
    raw = args.payload if args.payload else None
    payload = claude_host_shared.load_payload(raw)
    prompt = str(payload.get("prompt", "")).strip()
    session_id = claude_host_shared.hook_session_id(payload)
    bundle = _prompt_conversation_bundle(
        repo_root=repo_root,
        prompt=prompt,
        session_id=session_id,
    )
    summary = render_prompt_context(
        repo_root=repo_root,
        prompt=prompt,
        session_id=session_id,
        conversation_bundle_override=bundle,
    )
    system_message = render_prompt_system_message(
        repo_root=repo_root,
        prompt=prompt,
        session_id=session_id,
        conversation_bundle_override=bundle,
    )
    if summary:
        sys.stdout.write(
            json.dumps(
                host_surface_runtime.claude_prompt_payload(
                    additional_context=summary,
                    system_message=system_message,
                )
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
