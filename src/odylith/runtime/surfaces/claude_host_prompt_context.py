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


def render_prompt_context(
    *,
    repo_root: Path | str = ".",
    prompt: str,
    context_output_override: str | None = None,
) -> str:
    """Pure renderer used by the live hook and by tests."""
    refs = list(dict.fromkeys(_ANCHOR_RE.findall(str(prompt or ""))))
    if not refs:
        return ""
    ref = refs[0]
    if context_output_override is not None:
        return _context_summary(context_output_override, ref)
    completed = claude_host_shared.run_odylith(
        project_dir=repo_root,
        args=["context", "--repo-root", ".", ref],
        timeout=20,
    )
    if completed is None:
        return ""
    return _context_summary(completed.stdout or "", ref)


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
    if not claude_host_shared.project_launcher(repo_root).is_file():
        return 0
    raw = args.payload if args.payload else None
    payload = claude_host_shared.load_payload(raw)
    prompt = str(payload.get("prompt", "")).strip()
    summary = render_prompt_context(repo_root=repo_root, prompt=prompt)
    if summary:
        sys.stdout.write(summary + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
