# Subagent Routing And Orchestration

- Native subagent spawning through Odylith is capability-gated. Codex is the currently validated native-spawn host; treat Claude Code as local-guidance-only until Odylith's spawn contract is explicitly tested there.
- For both Codex and Claude Code, Odylith grounding comes before agent-native repo search on substantive repo work; local search is fallback after Odylith signals ambiguity, missing anchors, or widening.
- Use bounded delegation by default for substantive grounded work when the current host supports native spawn across the consumer lane and both Odylith product-repo maintainer postures, including pinned dogfood and detached `source-local` maintainer dev, when it improves correctness, speed, or separation of concerns.
- Consumer Odylith-fix requests are the hard exception: delegated leaves must not write under `odylith/` or `.odylith/`, and routed plans should stay local when the proposed fix is local Odylith mutation rather than diagnosis and handoff.
- Ground the slice through Odylith first, then delegate from retained evidence instead of paraphrasing it.
- On consumer turns, keep progress updates about the work itself. Do not narrate startup, routing, retained-packet, or fallback history. Do not surface routine `odylith start`, `odylith context`, or `odylith query` commands in progress updates, and never use control-plane receipt labels. Mention Odylith only when the user explicitly asks for the command, a current blocker requires it, or a lane distinction matters.
- Keep Odylith-derived commentary ambient by default. If routing or topology produces a real non-obvious point, weave it into the update first and reserve explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` labels for the rare cases that truly earn them.
- In the final handoff, one short `Odylith Assist:` line is optional if the routed or local result has concrete observed counts, measured deltas, or validation outcomes worth naming. Prefer `**Odylith Assist:**` when Markdown formatting is available. Lead with the user win, link updated governance ids inline when they were actually changed, and frame the edge against `odylith_off` or the broader unguided path when the evidence supports it. Keep it crisp, authentic, clear, simple, insightful, erudite in thought, soulful, friendly, free-flowing, human, and factual, not promotional. Silence is better than filler, so omit it when there is no clear user-facing delta.
- Every delegated task needs an owner, goal, validation expectation, and termination condition.
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
- In Claude Code or any non-Codex agent runtime, use the emitted plan as local execution guidance and do not try to spawn native subagents.

## Delegated Leaf Contract
- Spawn delegated leaves with the emitted `model` and `reasoning_effort` explicitly; never inherit parent-thread defaults.
- Let Odylith climb the reasoning ladder judiciously: lighter tiers for scout/support work, write-focused tiers for grounded implementation, and frontier tiers only after risk, validation pressure, or earned depth justify them.
- Preserve the emitted owner, goal, expected output, validation expectation, and termination condition.
- Conservative parallelism is intentional: read-only analysis may fan out, disjoint writes may fan out narrowly, and shared-write or adjudication-heavy slices stay serial or local.
- Close delegated agents after integration unless an immediate same-scope follow-up is already queued; `waiting on instruction` is an idle state that requires main-thread action.
- Do not treat desktop UI controls as proof of the delegated runtime pair; the prompt body must carry the requested `model` and `reasoning_effort` explicitly.

## Bounded Leaf Routing
- Use `odylith subagent-router` only after the slice is already bounded and grounded.
- Treat `main_thread` route results as scope warnings, not as a casual suggestion to override the policy.
- Route validation is fail-closed: malformed or incomplete route payloads should be repaired, not guessed through.
- Accuracy-first model selection remains intentional: lighter tiers for bounded read-only or mechanical work, stronger tiers for bounded implementation, and `xhigh` only for maximum-accuracy cases.

## Direct Native Spawn Defaults
- These defaults apply only when the current host supports native spawn. Codex is the validated host today; other runtimes should treat the ladder as local guidance until their native spawn path is proven.
- If no routed leaf exists and you still need direct delegation on a native-spawn-capable host:
  - bounded read-only exploration or evidence gathering: `gpt-5.4-mini` with `medium`
  - mechanical bounded transforms or fast triage: `gpt-5.3-codex-spark` with `medium`
  - bounded code-write or test repair: `gpt-5.3-codex` with `medium`
  - correctness-critical, ambiguous, or adjudication-heavy implementation: `gpt-5.4` with `high`
  - reserve `xhigh` for maximum-accuracy or failure-driven cases after the narrower tiers look unsafe
- When router/orchestrator already emitted a delegated leaf, prefer the routed native-spawn payload directly and pass `spawn_task_message` verbatim as the spawned message.
