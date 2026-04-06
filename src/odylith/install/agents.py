from __future__ import annotations

import re
from pathlib import Path

SCOPE_START = "<!-- odylith-scope:start -->"
SCOPE_END = "<!-- odylith-scope:end -->"
LEGACY_MANAGED_START = "<!-- odylith-managed:start -->"
LEGACY_MANAGED_END = "<!-- odylith-managed:end -->"
_BLOCK_MARKERS = (
    (SCOPE_START, SCOPE_END),
    (LEGACY_MANAGED_START, LEGACY_MANAGED_END),
)
_BLOCK_PATTERNS = tuple(
    re.compile(rf"\n?{re.escape(start)}.*?{re.escape(end)}\n?", re.DOTALL)
    for start, end in _BLOCK_MARKERS
)


def managed_block(*, repo_role: str = "consumer_repo") -> str:
    lines = [
        SCOPE_START,
        "## Odylith Scope",
        "",
        "Paths under `odylith/` follow `odylith/AGENTS.md`.",
        "",
        "- Work inside `odylith/` should follow `odylith/AGENTS.md` first.",
        "- Before any substantive repo scan or code change outside trivial fixes, the agent must start from the repo-local Odylith entrypoint and keep the active workstream, component, or packet in scope before raw repo search, tests, or edits.",
        "- Direct repo scan before that start step is a policy violation unless the task is trivial or Odylith is unavailable.",
        "- Start substantive turns with `./.odylith/bin/odylith start --repo-root .`; it chooses the safe first lane and prints the exact next command when Odylith cannot narrow the slice yet.",
        "- When you already know the exact workstream, component, path, or id, use `./.odylith/bin/odylith context --repo-root . <ref>` before raw repo search. Use `./.odylith/bin/odylith query --repo-root . \"<terms>\"` only after concrete anchors already exist.",
        "- In Codex commentary, keep startup, fallback, routing, and packet-selection internals implicit. Describe progress in task terms like the exact file/workstream, the bug under test, or the validation in flight. If an earlier repo-local start attempt degraded but work can continue safely, do not narrate that history. Do not surface routine `odylith start`, `odylith context`, or `odylith query` commands in progress updates, and never prefix commentary with control-plane receipt labels. Mention Odylith during the work only when the user explicitly asks for the command, a real blocker requires it, or a consumer-versus-maintainer lane distinction matters.",
        "- At closeout, you may add at most one short `Odylith assist:` line if it helps the user understand what Odylith materially contributed. Prefer `**Odylith assist:**` when Markdown formatting is available; otherwise use `Odylith assist:`. Lead with the user win, not Odylith mechanics. When the evidence supports it, frame the edge against `odylith_off` or the broader unguided path. Keep it soulful, friendly, authentic, and factual, not slogan-like. Use only concrete observed counts, measured deltas, or validation outcomes; if you cannot show a user-facing delta, omit the line.",
        "- For substantive tasks, follow this workflow check in order: read the nearest `AGENTS.md`; run the repo-local `odylith start`/`odylith context` step; identify the active workstream, component, or packet; then move into repo scan, tests, and edits.",
        "- In consumer repos, grounding Odylith is diagnosis authority, not blanket write authority: if the issue target is Odylith itself, stop at diagnosis and maintainer-ready feedback unless the operator explicitly authorizes Odylith mutation.",
        "- Treat `odylith upgrade`, `odylith reinstall`, `odylith doctor --repair`, `odylith sync`, and `odylith dashboard refresh` as writes when they change `odylith/` or `.odylith/`; do not run them autonomously as Odylith fixes in consumer repos.",
        "- Treat backlog/workstream, plan, Registry, Atlas, Casebook, Compass, and session upkeep as part of the same grounded Odylith workflow; search existing workstream, plan, bug, component, diagram, and recent session/Compass context first, extend or reopen existing truth when present, and create new governed records only when the slice is genuinely new.",
        "- Queued backlog items, case queues, and shell or Compass queue previews are not implicit implementation instructions. Unless the user explicitly asks to work a queued item, do not pick it up automatically just because it appears in Radar, Compass, the shell, or another Odylith queue surface.",
        "- If the slice expands beyond one truthful record, use child workstreams or execution waves instead of flattening everything into one note, and carry forward intent, constraints, and validation obligations through Odylith session/context packets and Compass updates so repo context compounds over time.",
        "- `./.odylith/bin/odylith` chooses how Odylith runs; it does not decide which repo files the agent may edit, and target-repo code still validates on the target repo's own toolchain.",
        "- Before diagnosing install, upgrade, rollback, or launcher state, run `./.odylith/bin/odylith version --repo-root .` when the launcher exists and treat that live posture as authoritative over older Compass, shell, or release-history context.",
        "- If the launcher is missing, confirm that from the filesystem first and use Odylith's current repair contract instead of assuming the repo is on a legacy consumer path.",
        (
            "- In Codex, treat Odylith-routed native subagent spawn as the default execution path for substantive grounded work across the consumer lane and the Odylith product repo's maintainer mode, including pinned dogfood and detached `source-local` maintainer-dev posture, unless Odylith explicitly keeps the slice local."
            if str(repo_role).strip() == "product_repo"
            else "- In Codex, treat Odylith-routed native subagent spawn as the default execution path for substantive grounded consumer-lane work unless Odylith explicitly keeps the slice local."
        ),
        "- In Claude Code, use Odylith grounding, memory, surfaces, and local orchestration guidance, but do not assume native spawn support.",
        "- Repo-root guidance in this file remains authoritative for paths outside `odylith/`.",
    ]
    if str(repo_role).strip() == "product_repo":
        lines.append(
            "- In the Odylith product repo, maintainer-only release and benchmark publishing work follows `odylith/maintainer/AGENTS.md`."
        )
        lines.append(
            "- In the Odylith product repo's maintainer mode, pinned dogfood is the default proof posture and detached `source-local` is the explicit dev posture for live unreleased `src/odylith/*` execution."
        )
    lines.extend(
        [
            "",
            SCOPE_END,
            "",
        ]
    )
    return "\n".join(lines)


def inject_managed_block(text: str, *, repo_role: str = "consumer_repo") -> str:
    current = remove_managed_block(text).rstrip("\n")
    block = managed_block(repo_role=repo_role).rstrip("\n")
    if not current:
        return block + "\n"
    lines = current.splitlines()
    if lines[0].startswith("#"):
        remainder = "\n".join(lines[1:]).lstrip("\n")
        if remainder:
            return f"{lines[0]}\n\n{block}\n\n{remainder}\n"
        return f"{lines[0]}\n\n{block}\n"
    return f"{block}\n\n{current}\n"


def remove_managed_block(text: str) -> str:
    if not has_managed_block(text):
        return text
    cleaned = text
    for pattern in _BLOCK_PATTERNS:
        cleaned = pattern.sub("\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).rstrip("\n")
    return cleaned + "\n"


def has_managed_block(text: str) -> bool:
    return any(start in text for start, _ in _BLOCK_MARKERS)


def update_agents_file(path: Path, *, install_active: bool, repo_role: str = "consumer_repo") -> None:
    original = path.read_text(encoding="utf-8")
    updated = inject_managed_block(original, repo_role=repo_role) if install_active else remove_managed_block(original)
    if updated != original:
        path.write_text(updated, encoding="utf-8")
