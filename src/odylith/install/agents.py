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
        "- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, call the CLI command and do not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code so delegated work inherits the same contract.",
        "- Default to the nearest `AGENTS.md`, the repo-local launcher, and truthful `odylith ... --help` for routine backlog, plan, bug, spec, component, and diagram upkeep. Treat `.agents/skills/` and `odylith/skills/` as specialist overlays for advanced packet control, orchestration, or high-risk lanes rather than as the default path.",
        "- When a routine governance task already maps to a first-class CLI family such as `odylith bug capture`, `odylith backlog create`, `odylith component register`, `odylith atlas scaffold`, or `odylith compass log`, go straight to that CLI and keep any `.agents/skills` lookup, missing-shim, or fallback-path details implicit unless they change the next user-visible action.",
        "- `odylith backlog create` is fail-closed and must receive grounded Problem, Customer, Opportunity, Product View, and Success Metrics text; never create or accept a title-only, placeholder, or boilerplate Radar workstream.",
        "- For quick visibility after a narrow truth change, rerender only the owned surface: `odylith radar refresh`, `odylith registry refresh`, `odylith casebook refresh`, `odylith atlas refresh`, or `odylith compass refresh`. Use `odylith compass deep-refresh` when you also want brief settlement. Keep `odylith sync` as the broader governance and correctness lane.",
        "- Keep the default operating lane shared across Codex and Claude Code: repo-root guidance, the repo-local launcher, truthful `odylith ... --help`, and the grounded governance workflow should mean the same thing on both hosts. Add host-specific tips only when the host exposes a real native capability that materially reduces hops.",
        "- Treat AI slop as a regression. Apply that bar across any language and across runtime code, hooks, prompts, docs, config, templates, generators, and managed assets. Apply it to any codebase or project surface: services, libraries, apps, CLIs, infra glue, scripts, docs, prompts, hooks, templates, config, and generated assets all count. No transitional states: do not replace one slop class with another, move ownership not just file boundaries, and do not treat a shared helper or kernel as a cleanup ornament. Partial shared-kernel adoption is still incomplete; if a shared helper or kernel lands, the touched callers must adopt it or the pass is incomplete. Do not call a slop cleanup complete just because the first smell disappeared; if the replacement smell still exists in the touched slice, the pass is incomplete. When the user asks for repo-wide or lane-wide anti-slop hardening, update guidance, skills, install-generated guidance, host contracts, mirrors, and enforcement tests together; prose-only hardening is incomplete. Repo-wide or lane-wide anti-slop claims require two proof layers: fresh behavior proof for the touched slice and a fresh structural inventory for the claimed scope. One does not substitute for the other. Use `odylith/agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md` and `odylith/skills/odylith-code-hygiene-guard/SKILL.md` when quality pressure is high.",
        "- For guidance behavior pressure cases, use `odylith validate guidance-behavior --repo-root .` for deterministic proof and `odylith benchmark --profile quick --family guidance_behavior` for benchmark-family proof. Compact packet summaries only prove the proof path is available; fresh validation still requires the explicit command.",
        "- Odylith Discipline is the v0.1.11 shared Codex/Claude behavior contract: hard laws are deterministic, runtime pressure is open-world, stance is local and credit-safe, passing checks stay quiet, and durable learning requires validator, benchmark, or Tribunal/governance proof. Use `odylith discipline status/check/explain`, `odylith validate discipline --repo-root .`, and `odylith benchmark --profile quick --family discipline --no-write-report --json`; none of those discipline hot paths may call host models, providers, subagents, broad scans, full validation, or projection expansion.",
        "- A plain `Odylith, show me what you can do` request is the advisory `odylith show` repo-capability demo. It is not a request to prove intervention UX, diagnose install posture, run `start`, run `doctor`, or explain missing launcher state. Use the first available show command and print stdout only.",
        (
            "- In Codex commentary, keep startup, fallback, routing, and packet-selection internals implicit. Describe progress in task terms like the exact file/workstream, the bug under test, or the validation in flight. If an earlier repo-local start attempt degraded but work can continue safely, do not narrate that history. Do not surface routine `odylith start`, `odylith context`, or `odylith query` commands in progress updates, and never prefix commentary with control-plane receipt labels. Mention Odylith during the work only when the user explicitly asks for the command, a real blocker requires it, or a consumer-versus-maintainer lane distinction matters."
            if str(repo_role).strip() == "product_repo"
            else "- In coding-agent commentary, keep startup, fallback, routing, and packet-selection internals implicit. Describe progress in task terms like the exact file/workstream, the bug under test, or the validation in flight. If an earlier repo-local start attempt degraded but work can continue safely, do not narrate that history. Do not surface routine `odylith start`, `odylith context`, or `odylith query` commands in progress updates, and never prefix commentary with control-plane receipt labels. Mention Odylith during the work only when the user explicitly asks for the command, a real blocker requires it, or a consumer-versus-maintainer lane distinction matters."
        ),
        "- Keep normal commentary task-first and human. Weave Odylith-grounded facts into ordinary updates when they change the next move, and reserve explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` labels for rare high-signal moments. Pick the strongest one or stay quiet.",
        "- Treat live teaser, `**Odylith Observation**`, and `Odylith Proposal` as the\n  intervention-engine fast path. Treat `Odylith Assist:` as the chatter-owned\n  closeout. Do not collapse those two layers into one ad hoc narration path.",
        "- When the shared conversation-observation runtime earns a full\n  `**Odylith Observation**` or `**Odylith Proposal**`, preserve those exact\n  labels, keep the markdown warm and human, and keep the moment rooted in the\n  original user prompt rather than Odylith's own pending/applied summary\n  strings.",
        "- Preserve the shipped shape too: Observation should look like\n  `Odylith Assist`, which means one short labeled line. Proposal should be a\n  short ruled block with the heading, a couple of lines, a few bullets, and\n  the confirmation line.",
        "- Keep one stable intervention identity across teaser, Observation, and\n  Proposal for the same session-local moment. Later hooks may add evidence or\n  surface the first eligible Proposal, but they must not make the same moment\n  feel like a fresh branded interruption.",
        "- For Codex and Claude checkpoint hooks, keep the full Observation,\n  Proposal, and Assist bundle in hidden developer context for continuity, but\n  surface the earned Observation/Proposal beat visibly at the hook moment when\n  the host renders hook output. If the host keeps hook output hidden, render\n  the assistant-visible fallback Markdown in chat instead of claiming the\n  engine is active. Stop is the fallback closeout and live-beat recovery lane,\n  not the primary intervention moment; unseen Ambient Highlight,\n  Observation, or Proposal beats may replay there before Assist.",
        "- Hook `systemMessage` or `additionalContext` generation is not proof of\n  chat-visible UX. The user-visible contract is satisfied only by rendered\n  chat text or by a host channel that is proven visible in the active session.\n  When in doubt, run `odylith codex visible-intervention` or `odylith claude\n  visible-intervention` and show that Markdown directly.",
        "- Before claiming the intervention UX is active in a specific chat, run or\n  cite `odylith codex intervention-status` or `odylith claude\n  intervention-status` for that host/session. That status surface is the\n  low-latency delivery ledger for Teaser, Ambient Highlight, Observation,\n  Proposal, and Assist readiness; hook payload generation alone is not enough.",
        "- Existing Codex and Claude sessions may not hot-reload changed hooks,\n  guidance, or source-local runtime code. After changing intervention\n  visibility behavior, prove it in a newly started or explicitly reloaded\n  session, or render `visible-intervention` output directly in the existing\n  chat instead of claiming other open sessions are active.",
        "- If you need to show that UX to a human in-chat, prefer rendered Markdown or\n  plain prose. Do not wrap the product moment in fenced raw Markdown unless\n  the task is explicitly about debugging the raw source text.",
        "- At closeout, you may add at most one short `Odylith Assist:` line if it helps the user understand what Odylith materially contributed. Prefer `**Odylith Assist:**` when Markdown formatting is available; otherwise use `Odylith Assist:`. Lead with the user win, link updated governance IDs inline when they were actually changed, and when no governed file moved, name the affected governance-contract IDs from bounded request or packet truth without calling them updated. Frame the edge against `odylith_off` or the broader unguided path when the evidence supports it. Keep it crisp, authentic, clear, simple, insightful, erudite in thought, soulful, friendly, free-flowing, human, and factual. Ground the line in concrete observed counts, measured deltas, or validation outcomes. Humor is fine only when the evidence makes it genuinely funny. Silence is better than filler. At most one supplemental closeout line may appear, chosen from `Odylith Risks:`, `Odylith Insight:`, or `Odylith History:` when the signal is real.",
        "- Explicit feedback that Odylith ambient highlights, interventions, Assist,\n  Observations, Proposals, hooks, or chat output are not visible is a real\n  closeout signal. A short `Odylith Assist:` may acknowledge that visibility\n  continuity without claiming artifact updates; ordinary low-signal short\n  turns should still stay silent.",
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
            else "- Treat Odylith-routed native delegation as the default execution path for substantive grounded consumer-lane work when the current host supports it unless Odylith explicitly keeps the slice local."
        ),
        (
            "- Codex and Claude Code are both validated Odylith delegation hosts under the same grounding, routing, and validation contract. Codex executes routed leaves through `spawn_agent`; Claude Code executes the same bounded delegation contract through Task-tool subagents and the checked-in `.claude/` project assets."
            if str(repo_role).strip() == "product_repo"
            else "- Codex and Claude Code are both validated Odylith delegation hosts under the same grounding and validation contract. Codex uses routed `spawn_agent` payloads; Claude Code uses Task-tool subagents plus the installed `.claude/` project assets."
        ),
        "- Repo-root guidance in this file remains authoritative for paths outside `odylith/`.",
    ]
    if str(repo_role).strip() != "product_repo":
        lines.insert(
            9,
            "- For live blocker lanes, never say `fixed`, `cleared`, or `resolved` without qualification unless the hosted proof moved past the prior failing phase. Force three checks first: same fingerprint as the last falsification or not, hosted frontier advanced or not, and whether the claim is code-only, preview-only, or live.",
        )
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


def update_guidance_file(path: Path, *, install_active: bool, repo_role: str = "consumer_repo") -> None:
    original = path.read_text(encoding="utf-8")
    updated = inject_managed_block(original, repo_role=repo_role) if install_active else remove_managed_block(original)
    if updated != original:
        path.write_text(updated, encoding="utf-8")


def update_agents_file(path: Path, *, install_active: bool, repo_role: str = "consumer_repo") -> None:
    update_guidance_file(path, install_active=install_active, repo_role=repo_role)
