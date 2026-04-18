# Subagent Routing And Orchestration

## CLI-First Non-Negotiable
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, you must call the CLI command and you must not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code, so delegated work inherits the same contract.

- Native delegation through Odylith remains capability-gated by host contract, not by product loyalty. Codex executes routed leaves through `spawn_agent` and also supports checked-in project-native Codex assets under `.codex/` and `.agents/skills/`; Claude Code executes the same bounded delegation contract through Task-tool subagents plus the checked-in `.claude/` commands, hooks, rules, skills, and project assets.
- For both Codex and Claude Code, Odylith grounding comes before agent-native repo search on substantive repo work; local search is fallback after Odylith signals ambiguity, missing anchors, or widening.
- Use bounded delegation by default for substantive grounded work when the current host supports native spawn across the consumer lane and both Odylith product-repo maintainer postures, including pinned dogfood and detached `source-local` maintainer dev, when it improves correctness, speed, or separation of concerns.
- Consumer Odylith-fix requests are the hard exception: delegated leaves must not write under `odylith/` or `.odylith/`, and routed plans should stay local when the proposed fix is local Odylith mutation rather than diagnosis and handoff.
- Ground the slice through Odylith first, then delegate from retained evidence instead of paraphrasing it.
- On consumer turns, keep progress updates about the work itself. Do not narrate startup, routing, retained-packet, or fallback history. Do not surface routine `odylith start`, `odylith context`, or `odylith query` commands in progress updates, and never use control-plane receipt labels. Mention Odylith only when the user explicitly asks for the command, a current blocker requires it, or a lane distinction matters.
- Keep Odylith-derived commentary ambient by default. If routing or topology produces a real non-obvious point, weave it into the update first and reserve explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` labels for the rare cases that truly earn them.
- In the final handoff, one short `Odylith Assist:` line is optional if the routed or local result has concrete observed counts, measured deltas, or validation outcomes worth naming. Prefer `**Odylith Assist:**` when Markdown formatting is available. Lead with the user win, link updated governance IDs inline only when they actually changed, name affected governance-contract IDs from bounded request or packet truth when no governed file moved, and frame the edge against `odylith_off` or the broader unguided path when the evidence supports it. Keep it crisp, authentic, clear, simple, insightful, erudite in thought, soulful, friendly, free-flowing, human, and factual, not promotional. Silence is better than filler, so omit it when there is no clear user-facing delta.
- Every delegated task needs an owner, goal, validation expectation, and termination condition.
- Odylith Discipline keeps coordination adaptive rather than
  posture-rigid. Broad delegation is a deterministic hard-law violation until
  the route is bounded with owner, goal, expected output, stop condition,
  owned scope, validation expectation, and closeout state. Discipline checks
  may rank routing affordances, but they must not spawn subagents or spend
  host model credits to classify pressure.
- When a grounded slice touches a hand-maintained source file that is already
  beyond policy thresholds, keep the delegated or local plan aligned with
  [CODING_STANDARDS.md](./CODING_STANDARDS.md): refactor-first, bounded, and
  reuse-oriented instead of authorizing more in-place growth for the
  oversized file unless an explicit exception already exists.
- Prefer route-ready execution payloads over ad-hoc task drafting.
- Stay local when the task is under-specified, shared-write-heavy, or blocked on immediate adjudication.

## Prompt-Level Orchestration
- For substantive grounded work, prompt-level orchestration is the default next step after grounding across the consumer lane, pinned dogfood, and detached `source-local` maintainer-dev posture.
- Treat `local_only` as an explicit keep-local decision, not as a hint to manually force spawn anyway.
- If emitted routing stays `local_only` because consumer write policy blocks an Odylith fix, produce maintainer-ready feedback instead of overriding the route.
- Use `odylith subagent-orchestrator plan --repo-root . --input-file <file> --json` and follow the emitted `mode` literally.
- `local_only` keeps the work in the main thread, `single_leaf` spawns one bounded worker, `serial_batch` uses dependency order, and `parallel_batch` is only for emitted disjoint leaves.
- Keep `main_thread_followups` in the main thread after delegated leaves integrate; they are not missing worker tasks.
- Pass emitted `context_signals`, `spawn_task_message`, `model`, and `reasoning_effort` through unchanged instead of rebuilding the contract manually.
- Once the retained contract marks the slice route-ready, prefer spawning through the emitted payload instead of improvising your own model ladder or decomposition.
- In Claude Code, use the emitted plan to spawn the matching project subagent under `.claude/agents/` through the Task tool; the project subagents carry the same bounded-leaf contract as Codex routed spawns and resolve through the per-host-family execution profile ladder.
- In Codex, keep two layers distinct: routed `spawn_agent` still uses built-in agent roles only, while the checked-in `.codex/agents/*.toml`, `.codex/hooks.json`, and `.agents/skills/*/SKILL.md` files are repo-scoped Codex CLI project assets. Do not flatten those into one contract or claim named `.codex/agents/*` selection through `spawn_agent` until host proof exists.
- For other non-Codex, non-Claude agent runtimes, use the emitted plan together with the checked-in host assets as local execution guidance until that host is validated.

## Delegated Leaf Contract
- Spawn delegated leaves with the emitted `model` and `reasoning_effort` explicitly; never inherit parent-thread defaults.
- Let Odylith climb the reasoning ladder judiciously: lighter tiers for scout/support work, write-focused tiers for grounded implementation, and frontier tiers only after risk, validation pressure, or earned depth justify them.
- Preserve the emitted owner, goal, expected output, validation expectation, and termination condition.
- Conservative parallelism is intentional: read-only analysis may fan out, disjoint writes may fan out narrowly, and shared-write or adjudication-heavy slices stay serial or local.
- Close delegated agents after integration unless an immediate same-scope follow-up is already queued; `waiting on instruction` is an idle state that requires main-thread action.
- Do not treat desktop UI controls as proof of the delegated runtime pair; the prompt body must carry the requested `model` and `reasoning_effort` explicitly.
- The `guidance-bounded-delegation-contract` pressure case is the reusable
  guardrail for broad delegation requests. If a task cannot state owner, goal,
  expected output, termination condition, and validation expectation, it is
  not ready for routed native spawn yet. Narrow locally or keep the work in
  the main thread rather than emitting vague leaves.
- When a guidance behavior summary supplies a case-scoped validator command,
  carry that command into the leaf validation expectation. Do not replace
  specific pressure proof with an unqualified "run tests" instruction.

## Bounded Leaf Routing
- Use `odylith subagent-router` only after the slice is already bounded and grounded.
- Treat `main_thread` route results as scope warnings, not as a casual suggestion to override the policy.
- Route validation is fail-closed: malformed or incomplete route payloads should be repaired, not guessed through.
- Accuracy-first model selection remains intentional: lighter tiers for bounded read-only or mechanical work, stronger tiers for bounded implementation, and `xhigh` only for maximum-accuracy cases.

## Direct Native Spawn Defaults
- These defaults apply when the current host supports native spawn. Codex and Claude Code are both first-class delegation hosts for Odylith: Codex executes routed leaves through `spawn_agent` while the checked-in `.codex/` and `.agents/skills/` trees provide the separate repo-scoped Codex CLI project-asset layer, and Claude Code executes the same bounded delegation contract through Task-tool subagents and the checked-in `.claude/` project assets.
- The semantic profile ladder is host-portable. Odylith's execution-governance resolver returns `(model, reasoning_effort)` per `(host_family, profile)` through `execution_profile_runtime_fields`, so the same ladder position resolves to a real Codex tuple on Codex and a real Claude tuple on Claude Code.
- If no routed leaf exists and you still need direct delegation on a native-spawn-capable host, pick the semantic profile first and let the resolver pick the model:
  - bounded read-only exploration or evidence gathering: `analysis_medium`
    (Codex: `gpt-5.4-mini` / `medium`; Claude: `claude-haiku-4-5` / `medium`)
  - mechanical bounded transforms or fast triage: `fast_worker`
    (Codex: `gpt-5.3-codex-spark` / `medium`; Claude: `claude-haiku-4-5` / `medium`)
  - bounded code-write or test repair: `write_medium`
    (Codex: `gpt-5.3-codex` / `medium`; Claude: `claude-sonnet-4-6` / `medium`)
  - correctness-critical, ambiguous, or adjudication-heavy implementation: `frontier_high`
    (Codex: `gpt-5.4` / `high`; Claude: `claude-opus-4-6` / `high`)
  - reserve `frontier_xhigh` for maximum-accuracy or failure-driven cases after the narrower tiers look unsafe
    (Codex: `gpt-5.4` / `xhigh`; Claude: `claude-opus-4-6` / `xhigh`)
- When router/orchestrator already emitted a delegated leaf, prefer the routed native-spawn payload directly and pass `spawn_task_message` verbatim as the spawned message. On Claude Code, use the emitted profile together with the matching project subagent under `.claude/agents/` (for example `odylith-reviewer` for frontier-tier review, `odylith-context-engine` for haiku-tier retrieval) instead of improvising a local model override.
- For the Codex project-asset surface itself, see `CODEX_HOST_CONTRACT.md`; that document is the source of truth for trusted-project gating, supported hooks, skill shims, and the native-blocked gaps that remain outside the routed `spawn_agent` contract.
