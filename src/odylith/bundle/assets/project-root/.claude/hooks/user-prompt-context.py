#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys


_ANCHOR_RE = re.compile(r"\b(?:B|CB|D)-\d{3,}\b")


def _payload() -> dict[str, object]:
    try:
        raw = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return {}
    return raw if isinstance(raw, dict) else {}


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
    if not isinstance(payload, dict):
        return f"Odylith anchor {ref}: context resolved."
    targets = payload.get("target_resolution", {})
    if isinstance(targets, dict):
        candidates = targets.get("candidate_targets", [])
        if isinstance(candidates, list) and candidates:
            first = candidates[0]
            if isinstance(first, dict):
                path = str(first.get("path", "")).strip()
                if path:
                    return f"Odylith anchor {ref}: primary target {path}."
    docs = payload.get("relevant_docs")
    if isinstance(docs, list) and docs:
        return f"Odylith anchor {ref}: relevant doc {docs[0]}."
    return f"Odylith anchor {ref}: context resolved."


def main() -> int:
    project_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    launcher = project_dir / ".odylith" / "bin" / "odylith"
    if not launcher.is_file():
        return 0
    payload = _payload()
    prompt = str(payload.get("prompt", "")).strip()
    refs = list(dict.fromkeys(_ANCHOR_RE.findall(prompt)))
    if not refs:
        return 0
    ref = refs[0]
    try:
        completed = subprocess.run(
            [str(launcher), "context", "--repo-root", ".", ref],
            cwd=str(project_dir),
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return 0
    summary = _context_summary(completed.stdout, ref)
    if summary:
        print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
