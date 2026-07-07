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
        "- CLI-first is non-negotiable for both Codex and Claude Code: use nearest `AGENTS.md`, repo-local launcher, truthful `odylith ... --help`, and relevant `odylith backlog ...`, `governance ...`, `validate plan-* ...`, `bug ...`, `component ...`, `registry ...`, `atlas ...`, or `compass ...` commands before hand edits. Do not hand-edit governed files where a CLI exists. `odylith plan --help` is read-only; do not probe `odylith/technical-plans/source/`. Policy: `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by `CB-104`.",
        "- For `odylith ... --help` discovery, run the single authoritative help command first and do not run parallel exploratory filesystem probes whose failure can cancel the visible help call. If a guess is invalid, fall back to `odylith --help` and then the nearest listed subcommand.",
        "- Routine governance tasks that map to first-class CLI families such as `odylith bug capture`, `odylith backlog create`, `odylith component register`, `odylith atlas scaffold`, or `odylith compass log` go straight to that CLI; keep lookup and fallback details implicit unless they change the next action.",
        "- Empty/thin prompts use `odylith greenfield propose --repo-root . --prompt \"<request>\"` for project-first Product Intent Confirmation as sectioned Markdown: Product story, State object, First complete path, Proof boundary. Before confirmation: no source/backlog/Registry/Atlas/release/validation writes; transaction staging only. Save the same visible Product Intent Confirmation to `.odylith/runtime/greenfield/confirmed-intent.md`; run `odylith greenfield compile-transaction --repo-root . --prompt \"<request>\" --intent-file .odylith/runtime/greenfield/confirmed-intent.md --output .odylith/runtime/greenfield/product-create-transaction.v1.json --release 0.0.1`; Odylith may write `.odylith/runtime/greenfield/confirmed-intent.json`, then builds, repairs, validates, quality-gates, and hashes the ProductCreateTransaction. Confirm with `odylith greenfield create --repo-root . --transaction-file .odylith/runtime/greenfield/product-create-transaction.v1.json --transaction-hash <hash> --confirm`; confirmed create verifies hash, writes atomically, validates readback, refreshes, and reports. Treat edits as new evidence and rebuild. Do not inspect Odylith source, hand-author/repair proposal JSON, narrate parser/schema retries, or stop after repairable transaction-compile issues. Do not ask the operator to inspect proposal JSON or confirm a second time around uncompiled Markdown. Surface only final summary or blockers.",
        "- `odylith backlog create` is fail-closed and must receive grounded Problem, Customer, Opportunity, Product View, and Success Metrics text; never create or accept a title-only, placeholder, or boilerplate Radar workstream.",
        "- For quick visibility after a narrow truth change, rerender only the owned surface: `odylith radar refresh`, `odylith registry refresh`, `odylith casebook refresh`, `odylith atlas refresh`, or `odylith compass refresh`; use `odylith compass deep-refresh` for brief settlement and `odylith sync` for the broader governance lane.",
        "- Keep startup, Context Engine, Execution Engine, memory substrate, Tribunal, Intervention Engine, observers, governance, subagent routing, Surface DAGs, delivery, analysis, and migration-breakage observation active. Optimize by routing, caching, batching, and shortening prompt surface, not by disabling engines.",
        "- Treat AI slop as a regression. This covers any codebase or project surface: code, docs, prompts, hooks, config, templates, and generated assets. Partial shared-kernel adoption is still incomplete; prose-only hardening is incomplete; if smell remains, the pass is incomplete. Claims need fresh behavior proof for the touched slice and a fresh structural inventory for the claimed scope; headless browser matrix needs normal, empty/fallback, and degraded or error states. See `odylith/agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md`; use `odylith/skills/odylith-code-hygiene-guard/SKILL.md`.",
        "- Generated human-visible content has a non-negotiable clarity floor across all lanes: simple, legible, grammatical, clear; broken copy is AI slop, so fix source rule or generator.",
        "- For guidance behavior pressure cases or discipline pressure, use `odylith validate guidance-behavior --repo-root .`, `odylith benchmark --profile quick --family guidance_behavior`, quick discipline benchmarks, and `odylith discipline status/check/explain`; Discipline hot paths must not call host models, providers, subagents, broad scans, full validation, or projection expansion.",
        "- A plain `Odylith, help` request is the CLI help fast path. Use the first available `odylith --help` command and print stdout only.",
        "- A plain `Odylith, show me what you can do` request is the advisory `odylith show` repo-capability demo: print first available show stdout only, then stop without extra probes. If Odylith is not installed, say so; do not substitute generic host work.",
        "- A request to list Odylith capabilities, engines, product architecture, or the capability map is the product-owned inventory path. Use `odylith capabilities` and print stdout only. Do not infer taxonomy from `odylith --help`, `odylith show`, Claude Code, Codex, or any host model capability surface.",
        (
            "- In Codex commentary, keep startup, fallback, routing, and packet-selection internals implicit. Describe task progress, not control-plane receipts, unless the user asks for the command, a real blocker requires it, or a consumer-versus-maintainer lane distinction matters. Never say `Startup fell back`."
            if product_repo
            else "- In coding-agent commentary, keep startup, fallback, routing, and packet-selection internals implicit; never say `Startup fell back`; never prefix commentary with control-plane receipt labels. Describe task progress, and mention Odylith only when the user asks, a real blocker requires it, or lane distinction matters."
        ),
        "- Keep normal commentary task-first and human; reserve `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` for rare high-signal moments. Silence is better than filler.",
        "- Treat live teaser, `**Odylith Observation**`, and `Odylith Proposal` as intervention-engine output; treat `Odylith Assist:` as chatter closeout. Do not collapse those layers. Observation stays one short line; Proposal stays a ruled block.",
        "- Codex hooks may carry hidden Observation/Proposal/Assist context and surface an earned beat; Claude direct-edit and Bash PostToolUse hooks stay silent on success and emit only compact failure/skipped-refresh status. Claude Stop is memory/logging only, not a fallback closeout.",
        "- Hook `systemMessage` or `additionalContext` is not chat-visible proof. Before claiming active intervention UX, run or cite `odylith codex intervention-status` or `odylith claude intervention-status`; it is the low-latency delivery record for Teaser, Ambient Highlight, Observation, Proposal, and Assist readiness. End-to-end proof requires `Activation: ready` plus chat visibility; if uncertain, run `visible-intervention` and show that Markdown directly.",
        "- At closeout, add at most one `Odylith Assist:` line only when useful; normal non-passthrough prompts do not get an Assist line by default. Do not add Assist just because Odylith ran. Lead with the user win, changed governance IDs, the `odylith_off` edge, and concrete observed counts, measured deltas, or validation outcomes. Generic activity receipts are not premium interventions.",
        "- Explicit Odylith visibility-failure feedback is a closeout signal; low-signal short turns stay silent.",
        "- In consumer repos, grounding Odylith is diagnosis authority, not blanket write authority: if the issue target is Odylith itself, stop at diagnosis and maintainer-ready feedback unless the operator explicitly authorizes Odylith mutation.",
        "- Treat `odylith upgrade`, `odylith reinstall`, `odylith doctor --repair`, `odylith sync`, and `odylith dashboard refresh` as writes when they change `odylith/` or `.odylith/`; do not run them autonomously as Odylith fixes in consumer repos.",
        "- Treat backlog/workstream, plan, Registry, Atlas, Casebook, Compass, and session upkeep as one grounded Odylith workflow: search existing workstream, plan, bug, component, diagram, and recent session/Compass context first. Create missing work only for genuinely new non-product slices; consumer-found Odylith issues get maintainer-ready feedback.",
        "- Governance-learning is mandatory across maintainer, pinned dogfood, detached `source-local`, installed consumer repos, Codex, Claude Code, and bundled/generated guidance. Durable errors, failed mechanisms/simulations, bad artifacts, semantic drift, gate failures, latency breaches, decisions, validation results, and release-risk learning update the right governed surface before continuing, committing, building, releasing, or claiming completion. Before fixes, search existing Casebook/governance artifacts, read prior failed mechanisms, failed fix attempts, and guardrails, do not repeat a fix path that already failed, search existing truth first, avoid duplicate Casebook bugs, use Odylith CLI paths where they exist, and never treat chat/final summaries as durable truth.",
        "- Queued backlog items, case queues, and shell or Compass queue previews are not implicit implementation instructions. Unless the user explicitly asks to work a queued item, do not pick it up automatically just because it appears in Radar, Compass, the shell, or another Odylith queue surface.",
        "- If the slice expands beyond one truthful record, use child workstreams or execution waves instead of flattening everything into one note, and carry forward intent, constraints, and validation obligations through Odylith session/context packets and Compass updates so repo context compounds over time.",
        "- `./.odylith/bin/odylith` chooses how Odylith runs; it does not decide which repo files the agent may edit, and target-repo code still validates on the target repo's own toolchain.",
        "- Before diagnosing install, upgrade, rollback, or launcher state, run `./.odylith/bin/odylith version --repo-root .` when the launcher exists and treat that live posture as authoritative over older Compass, shell, or release-history context.",
        "- If the launcher is missing, confirm that from the filesystem first and use Odylith's current repair contract instead of assuming the repo is on a legacy consumer path.",
        (
            "- In Codex, treat Odylith-routed native subagent spawn as default for substantive grounded work across the consumer lane and the Odylith product repo's maintainer mode, including pinned dogfood and detached `source-local` maintainer-dev posture, when bounded and host policy allows; keep transport separate from spawn permission/effectiveness."
            if product_repo
            else "- Treat Odylith-routed native delegation as the default candidate for substantive grounded consumer-lane work when the route is bounded, the host transport supports it, and the active host policy allows it; keep transport separate from spawn permission/effectiveness."
        ),
        (
            "- Codex and Claude Code are both validated Odylith delegation hosts under the same grounding, routing, and validation contract."
            if product_repo
            else "- Codex and Claude Code are both validated Odylith delegation hosts under the same grounding and validation contract."
        ),
    ]
    if not product_repo:
        lines.insert(
            9,
            "- For live blocker lanes, never say `fixed`, `cleared`, or `resolved` without qualification unless hosted proof moved past the prior failing phase; check same fingerprint as the last falsification or not, frontier advanced or not, and code/preview/live.",
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
        "- Governance-learning rules from `AGENTS.md` apply to Claude too: durable errors go to Casebook, planned work to Radar or technical plans, component-contract changes to Registry, flow/topology changes to Atlas, and durable decisions or proof checkpoints to Compass before closeout. Before fixing a bug, search Casebook and related governance truth, read prior failed mechanisms, failed fix attempts, and guardrails, do not repeat a fix path that already failed, and capture new mechanism-level learning.",
        "- First-match help, show-me, and capability inventory routes stay stdout-clean: use `odylith --help`, `odylith show`, or `odylith capabilities` as appropriate before any diagnostics.",
    ]
    if str(repo_role).strip() == "product_repo":
        lines.append(
            "- Commit messages must use only the `freedom-research` contributor identity and must not include coding-assistant trailers."
        )
        lines.append(
            "- In the Odylith product repo, maintainer-only release and benchmark publishing work follows `odylith/maintainer/AGENTS.md`."
        )
        lines.append(
            "- In maintainer mode, pinned dogfood is the default proof posture and detached `source-local` is the explicit live-source posture."
        )
    else:
        lines.append(
            "- Use the consumer repo's Git identity and commit policy; do not apply Odylith product-repo maintainer identity rules outside the product repo."
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
