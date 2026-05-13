"""Managed guidance and agent asset templates for installed repositories."""

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
GUIDANCE_FILENAMES = frozenset({"AGENTS.md", "CLAUDE.md"})


def managed_block(*, repo_role: str = "consumer_repo") -> str:
    product_repo = str(repo_role).strip() == "product_repo"
    lines = [
        SCOPE_START,
        "## Odylith Scope",
        "",
        "Paths under `odylith/` follow `odylith/AGENTS.md`; this root block is the hard-law kernel.",
        "",
        "- Work inside `odylith/` follows `odylith/AGENTS.md` first; repo-root guidance remains authoritative outside `odylith/`.",
        "- For substantive work, read the nearest `AGENTS.md`, run `./.odylith/bin/odylith start --repo-root .` first, then run `odylith context --repo-root . <ref>` only after startup when a precise anchor is known. Direct repo scan before that start step is a policy violation unless the task is trivial or Odylith is unavailable.",
        "- Do not run `odylith context`, `odylith query`, `git status`, broad repo search, or other repo-inspection commands in parallel with that start step. Let `start` finish first; then narrow.",
        "- CLI-first is non-negotiable for both Codex and Claude Code: use nearest `AGENTS.md`, repo-local launcher, truthful `odylith ... --help`, `odylith backlog ...`, `odylith governance ...`, `odylith validate plan-* ...`, `odylith bug ...`, `odylith component ...`, `odylith registry ...`, `odylith atlas ...`, and `odylith compass ...` before hand edits. Do not hand-edit governed files where a CLI exists. `odylith plan --help` is read-only; do not probe `odylith/technical-plans/source/`. Policy: `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by `CB-104`.",
        "- For `odylith ... --help` discovery, run the single authoritative help command first and do not run parallel exploratory filesystem probes whose failure can cancel the visible help call. If a guess is invalid, fall back to `odylith --help` and then the nearest listed subcommand.",
        "- Routine governance tasks that map to first-class CLI families such as `odylith bug capture`, `odylith backlog create`, `odylith component register`, `odylith atlas scaffold`, or `odylith compass log` go straight to that CLI; keep lookup and fallback details implicit unless they change the next action.",
        "- Empty/thin prompts route to `odylith greenfield propose --repo-root . --prompt \"<request>\"` for no-write Product Intent Confirmation. In chat, write live product story, actors, systems, assumptions, ambiguities, and a clear Next step block: Confirm to expand, Edit to correct, Reject to stop. Before confirmation, no backlog, Registry, Atlas, release waves, validation obligations, proposal JSON, or prompt-only `greenfield create`. After confirmation, run `odylith greenfield propose --confirm-intent`, author the project-specific proposal JSON from the confirmed product shape, then `odylith greenfield apply --repo-root . --proposal-file odylith-greenfield-proposal.json --confirm`; apply validates, Tribunal-gates, and writes records. No canned domain families, scaffolds, templates, or code. If CLI returns proposal stdout directly, show it; do not hide it behind collapsed tool output or replace it with a host-written summary.",
        "- `odylith backlog create` is fail-closed and must receive grounded Problem, Customer, Opportunity, Product View, and Success Metrics text; never create or accept a title-only, placeholder, or boilerplate Radar workstream.",
        "- For quick visibility after a narrow truth change, rerender only the owned surface: `odylith radar refresh`, `odylith registry refresh`, `odylith casebook refresh`, `odylith atlas refresh`, or `odylith compass refresh`; use `odylith compass deep-refresh` for brief settlement and `odylith sync` for the broader governance lane.",
        "- Keep startup, Context Engine, Execution Engine, memory substrate, Tribunal, Intervention Engine, observers, governance, subagent routing, Surface DAGs, delivery, analysis, and migration-breakage observation active. Optimize by routing, caching, batching, and shortening prompt surface, not by disabling engines.",
        "- Treat AI slop as a regression. Apply across lanes, hosts, languages, and any codebase or project surface. Move ownership, not just files; partial shared-kernel adoption is still incomplete; if the smell remains, the pass is incomplete. Prose-only hardening is incomplete. Repo-wide claims need fresh behavior proof for the touched slice and a fresh structural inventory for the claimed scope. Browser proof requires the headless browser matrix across normal, empty/fallback, and degraded or error states. Rule: `odylith/agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md`; use `odylith/skills/odylith-code-hygiene-guard/SKILL.md` under quality pressure.",
        "- For guidance behavior pressure cases or discipline pressure, use `odylith validate guidance-behavior --repo-root .`, `odylith benchmark --profile quick --family guidance_behavior`, quick discipline benchmarks, and `odylith discipline status/check/explain`; Discipline hot paths must not call host models, providers, subagents, broad scans, full validation, or projection expansion.",
        "- A plain `Odylith, help` request is the CLI help fast path. Use the first available `odylith --help` command and print stdout only.",
        "- A plain `Odylith, show me what you can do` request is the advisory `odylith show` repo-capability demo. It is not a request to prove intervention UX, diagnose install posture, run `start`, run `doctor`, explain missing launcher state, or build a sample application. Print first available show stdout only. If Odylith is not installed in the current folder, say so; do not substitute generic host work.",
        "- A request to list Odylith capabilities, engines, product architecture, or the capability map is the product-owned inventory path. Use `odylith capabilities` and print stdout only. Do not infer taxonomy from `odylith --help`, `odylith show`, Claude Code, Codex, or any host model capability surface.",
        (
            "- In Codex commentary, keep startup, fallback, routing, and packet-selection internals implicit. Describe task progress, not control-plane receipts, unless the user asks for the command, a real blocker requires it, or a consumer-versus-maintainer lane distinction matters. Never say `Startup fell back`."
            if product_repo
            else "- In coding-agent commentary, keep startup, fallback, routing, and packet-selection internals implicit. Describe task progress in terms of the exact file/workstream, the bug under test, or the validation in flight; never say `Startup fell back`. Do not surface routine `odylith start`, `odylith context`, or `odylith query` commands in progress updates, and never prefix commentary with control-plane receipt labels. Mention Odylith during the work only when the user explicitly asks for the command, a real blocker requires it, or a consumer-versus-maintainer lane distinction matters."
        ),
        "- Keep normal commentary task-first and human; reserve `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` for rare high-signal moments. Silence is better than filler.",
        "- Treat live teaser, `**Odylith Observation**`, and `Odylith Proposal` as the intervention-engine fast path; treat `Odylith Assist:` as the chatter-owned closeout. Do not collapse those layers. Observation stays one short labeled line like `Odylith Assist`; Proposal stays a short ruled block. Keep one stable intervention identity for a session-local moment.",
        "- Codex checkpoint hooks may carry hidden Observation/Proposal/Assist context and surface an earned beat; Claude direct-edit and Bash PostToolUse hooks stay silent on success and emit only compact failure/skipped-refresh status. Claude Stop is memory/logging only, not a fallback closeout.",
        "- Hook `systemMessage` or `additionalContext` is not chat-visible proof. Before claiming active intervention UX, run or cite `odylith codex intervention-status` or `odylith claude intervention-status`; it is the low-latency delivery record for Teaser, Ambient Highlight, Observation, Proposal, and Assist readiness. End-to-end proof requires `Activation: ready` plus chat visibility. If uncertain, run `odylith codex visible-intervention` or `odylith claude visible-intervention` and show that Markdown directly.",
        "- At closeout, add at most one `Odylith Assist:` or `**Odylith Assist:**` line only when it materially helps; normal non-passthrough prompts do not get an Assist line by default. Do not add Assist just because Odylith ran. Lead with the user win, link updated governance IDs inline when they changed, name affected governance-contract IDs only when no governed file moved, frame the edge against `odylith_off` or the broader unguided path when supported, keep it crisp, authentic, clear, simple, insightful, and ground the line in concrete observed counts, measured deltas, or validation outcomes, or a concrete chat-visibility complaint.",
        "- Explicit feedback that Odylith ambient highlights, interventions, Assist, Observations, Proposals, hooks, or chat output are not visible is a closeout signal; low-signal short turns stay silent.",
        "- In consumer repos, grounding Odylith is diagnosis authority, not blanket write authority: if the issue target is Odylith itself, stop at diagnosis and maintainer-ready feedback unless the operator explicitly authorizes Odylith mutation.",
        "- Treat `odylith upgrade`, `odylith reinstall`, `odylith doctor --repair`, `odylith sync`, and `odylith dashboard refresh` as writes when they change `odylith/` or `.odylith/`; do not run them autonomously as Odylith fixes in consumer repos.",
        "- Treat backlog/workstream, plan, Registry, Atlas, Casebook, Compass, and session upkeep as one grounded workflow: search existing truth first, extend or reopen existing records when present, and create new governed records only when the slice is genuinely new.",
        "- Queued backlog items, case queues, and shell or Compass queue previews are not implicit implementation instructions. Unless the user explicitly asks to work a queued item, do not pick it up automatically just because it appears in Radar, Compass, the shell, or another Odylith queue surface.",
        "- If the slice expands beyond one truthful record, use child workstreams or execution waves instead of flattening everything into one note, and carry forward intent, constraints, and validation obligations through Odylith session/context packets and Compass updates so repo context compounds over time.",
        "- `./.odylith/bin/odylith` chooses how Odylith runs; it does not decide which repo files the agent may edit, and target-repo code still validates on the target repo's own toolchain.",
        "- Before diagnosing install, upgrade, rollback, or launcher state, run `./.odylith/bin/odylith version --repo-root .` when the launcher exists and treat that live posture as authoritative over older Compass, shell, or release-history context.",
        "- If the launcher is missing, confirm that from the filesystem first and use Odylith's current repair contract instead of assuming the repo is on a legacy consumer path.",
        (
            "- In Codex, treat Odylith-routed native subagent spawn as default for substantive grounded work across the consumer lane and the Odylith product repo's maintainer mode, including pinned dogfood and detached `source-local` maintainer-dev posture, when the route is bounded and host policy allows; keep transport support separate from current-session spawn permission/effectiveness."
            if product_repo
            else "- Treat Odylith-routed native delegation as the default candidate for substantive grounded consumer-lane work when the route is bounded, the host transport supports it, and the active host policy allows it; keep transport support separate from current-session spawn permission/effectiveness."
        ),
        (
            "- Codex and Claude Code are both validated Odylith delegation hosts under the same grounding, routing, and validation contract. Codex emits routed `spawn_agent` payloads when host policy allows; Claude Code uses Task-tool subagents and checked-in `.claude/` assets."
            if product_repo
            else "- Codex and Claude Code are both validated Odylith delegation hosts under the same grounding and validation contract."
        ),
    ]
    if not product_repo:
        lines.insert(
            9,
            "- For live blocker lanes, never say `fixed`, `cleared`, or `resolved` without qualification unless the hosted proof moved past the prior failing phase. Force three checks first: same fingerprint as the last falsification or not, hosted frontier advanced or not, and whether the claim is code-only, preview-only, or live.",
        )
    if product_repo:
        lines.append(
            "- In the Odylith product repo, maintainer-only release and benchmark publishing work follows `odylith/maintainer/AGENTS.md`."
        )
        lines.append(
            "- In the Odylith product repo's maintainer mode, pinned dogfood is the default proof posture and detached `source-local` is the explicit dev posture."
        )
    lines.extend(
        [
            "",
            SCOPE_END,
            "",
        ]
    )
    return "\n".join(lines)


def managed_claude_bridge_block(*, repo_role: str = "consumer_repo") -> str:
    """Return the lean Claude bridge block for root `CLAUDE.md`.

    Claude already imports `AGENTS.md`; duplicating the full managed contract in
    `CLAUDE.md` materially increases every Claude turn. Keep only the ordering
    and host-delta rules that must be visible before the import lands.
    """

    lines = [
        SCOPE_START,
        "## Odylith Scope",
        "",
        "- Load `@AGENTS.md` as the authoritative shared Odylith contract; do not duplicate that contract in Claude-specific memory.",
        "- For substantive work, run repo-local `odylith start` first. Run `odylith context --repo-root . <ref>` only after startup and only when an exact anchor is known.",
        "- Keep routine startup, context, query, fallback, and packet-selection internals out of normal chat updates unless the user asks for the command or a real blocker requires it.",
        "- Preserve the intervention pipeline: prompt-bundle may surface earned Observation or Proposal output, while normal low-signal prompts stay quiet unless a visibility recovery or Odylith-directed receipt is needed.",
        "- Claude PostToolUse hooks stay silent on success; Claude Stop is memory/logging only.",
        "- Claude Code uses the checked-in `.claude/` project assets for hooks, commands, rules, skills, subagents, statusline, and auto-memory; keep those assets aligned with the shared `AGENTS.md` contract.",
        "- First-match help, show-me, and capability inventory routes stay stdout-clean: use `odylith --help`, `odylith show`, or `odylith capabilities` as appropriate before any diagnostics.",
        "- Commit messages must use only the `freedom-research` contributor identity and must not include coding-assistant trailers.",
    ]
    if str(repo_role).strip() == "product_repo":
        lines.append(
            "- In the Odylith product repo, maintainer-only release and benchmark publishing work follows `odylith/maintainer/AGENTS.md`."
        )
        lines.append(
            "- In maintainer mode, pinned dogfood is the default proof posture and detached `source-local` is the explicit live-source posture."
        )
    lines.extend(["", SCOPE_END, ""])
    return "\n".join(lines)


def _managed_block_for_path(path: Path, *, repo_role: str) -> str:
    if path.name == "CLAUDE.md":
        return managed_claude_bridge_block(repo_role=repo_role)
    return managed_block(repo_role=repo_role)


def inject_managed_block(text: str, *, repo_role: str = "consumer_repo", path: Path | None = None) -> str:
    current = remove_managed_block(text).rstrip("\n")
    block = (
        _managed_block_for_path(path, repo_role=repo_role)
        if path is not None
        else managed_block(repo_role=repo_role)
    ).rstrip("\n")
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


def update_guidance_file(path: Path, *, install_active: bool, repo_role: str = "consumer_repo") -> None:
    original = path.read_text(encoding="utf-8")
    updated = (
        inject_managed_block(original, repo_role=repo_role, path=path)
        if install_active
        else remove_managed_block(original)
    )
    if updated != original:
        path.write_text(updated, encoding="utf-8")


def update_agents_file(path: Path, *, install_active: bool, repo_role: str = "consumer_repo") -> None:
    update_guidance_file(path, install_active=install_active, repo_role=repo_role)
