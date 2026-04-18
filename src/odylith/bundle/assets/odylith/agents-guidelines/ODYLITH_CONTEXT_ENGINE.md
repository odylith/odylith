# Odylith Context Engine

## CLI-First Non-Negotiable
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, you must call the CLI command and you must not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code, so delegated work inherits the same contract.

## Core Rule
- Use Odylith packets and Odylith surfaces first for most grounded repo work, including in Odylith's own product repo.
- For Codex and Claude Code, Odylith-first retrieval is the default. Do not begin substantive repo work with ad-hoc `rg` or host-native search unless Odylith lacks seeds or explicitly recommends widening.
- Prefer fail-closed narrowing over broad prompt floods.
- Treat packet diagnostics and retained `routing_handoff` as part of the contract, not as consumer-facing chatter. Surface only the parts that materially change the work.
- Treat the Odylith runtime as a local accelerator layered on top of source truth, never as a replacement for tracked markdown/JSON authority.

## Odylith-First Loop
- Start open-ended or non-trivial repo work with the smallest fitting Odylith runtime lane:
  - `status`
  - `doctor`
  - `bootstrap-session`
  - `session-brief`
  - `query`
- Once explicit paths, refs, components, or workstream ids exist, stay on the smallest fitting packet:
  - `status`
  - `impact`
  - `architecture`
  - `governance-slice`
  - `bootstrap-session`
  - `context`
- Use raw `rg`, targeted source reads, and direct tests only when Odylith cannot seed the slice from the prompt or worktree, or a packet reports `full_scan_recommended`, `diagram_watch_gaps`, unresolved ambiguity, or another explicit widen signal.
- After the evidence cone is grounded, stay on the smallest fitting Odylith packet by default and only widen back to focused `rg`, targeted tests, and direct source reads when the packet tells you to widen.
- In consumer commentary, keep the packet step implicit. Describe narrowing, exact-ref lookup, or context recovery in task terms. If an earlier repo-local start attempt degraded but work can continue, keep that history out of the update unless it is still the live blocker.
- Keep Odylith ambient by default during work. Weave grounded packet facts into normal commentary when they materially change the next move, and only emit explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` lines when that signal is strong enough to deserve the interruption.
- If you mention Odylith by name in the final handoff, keep it to one short `Odylith Assist:` line. Prefer `**Odylith Assist:**` when Markdown formatting is available. Lead with the user win, link updated governance IDs inline only when they actually changed, name affected governance-contract IDs from bounded request or packet truth when no governed file moved, and frame the edge against `odylith_off` or the broader unguided path when the evidence supports it. Keep it crisp, authentic, clear, simple, insightful, erudite in thought, soulful, friendly, free-flowing, human, and factual. Use only concrete observed counts, measured deltas, or validation outcomes. Silence is better than filler. Omit it when the evidence is thin or the user-facing delta is not clear.

## Packet Ladder
- `impact` is the default grounded coding packet for explicit paths and implementation slices.
- `architecture` is for topology, authority-boundary, shared-stack, control-plane, and diagram-watch work.
- `governance-slice` is for backlog/workstream, plan, component, diagram, bug, and closeout coordination around one bounded slice.
- `bootstrap-session` is the session bootstrap for new or shared-dirty local loops when claim data is available.
- `session-brief` is for dirty-session deltas when `impact` is not enough.
- `context` is for exact refs, aliases, and direct path resolution.
- `query` is lexical recall after the slice is already grounded.

## Packet Reading Contract
- Keep prompt assembly layered: `policy -> routing -> payload`.
- Treat `routing_handoff` as the compact execution bridge into router/orchestrator flows; pass it through unchanged when it already exists.
- Treat `context_packet` and `evidence_pack` as the retained downstream contracts when a richer but still bounded packet is needed.
- Use `bootstrap-session`, `session-brief`, and `governance-slice` to recover active intent, constraints, validation obligations, related workstreams, components, diagrams, and bugs before substantive edits or closeout.
- Treat retained session and governance packets as cumulative repo memory; carry forward affirmed context instead of rediscovering it every turn.
- Read `retrieval_plan`, `guidance_brief`, and `narrowing_guidance` first to see why the packet won and what extra anchor would unlock a better one.
- Read `packet_quality` literally: `anchor_quality`, `guidance_coverage`, `evidence_consensus`, `precision_score`, and `ambiguity_class` tell you whether the packet is merely compact or actually precise.
- Read `packet_metrics` literally: `estimated_bytes` is the serialized payload size, and `sections.largest` is the supported hotspot summary when the packet is still too large.
- Read `context_packet.security_posture` and `evidence_pack.provenance` before forwarding runtime context into delegated work.
- If `routing_handoff.narrowing_required=true`, narrow locally before delegating.
- If `selection_state=ambiguous|none`, `working_tree_scope_degraded=true`, `diagram_watch_gaps` is present, or `full_scan_recommended=true`, widen back to raw discovery before acting.

## Guidance Behavior Packet Contract
- Guidance Behavior is packet evidence, not a hidden background validator. When
  the slice touches high-risk guidance, host contracts, skill descriptions,
  agent instructions, or the `guidance_behavior` benchmark family, the Context
  Engine should attach a compact `guidance_behavior_summary` to relevant
  packets.
- That summary may carry case ids, source fingerprints, related guidance refs,
  a validator command, runtime-layer wiring, and a Tribunal-ready readout. It
  must not run the full validator, call a provider, expand the context store,
  or widen into a repo-wide scan on the live packet path.
- The full validator remains explicit proof:
  `odylith validate guidance-behavior --repo-root .`. Case-scoped packet
  commands should keep `--case-id` so broad proof does not replace the pressure
  case the packet actually surfaced.
- The same compact summary should empower the next layer rather than become
  another document to reread: Execution Engine consumes the validator command,
  Memory Contracts preserve the compact fields, intervention evidence turns
  material failures into one supported fact, and Tribunal references the
  precomputed signal without doing live reasoning work.

## Odylith Discipline Packet Contract
- Odylith Discipline is a compact packet contract, not a
  hidden validator. The Context Engine owns the Attention facet by surfacing
  ambiguity, anchors, proof posture, workstream/component refs, and any
  existing guidance behavior summary as local inputs for the Odylith Discipline
  contract.
- Packet construction may attach a compact discipline summary when pressure
  or benchmark family context makes it relevant. That summary must come from
  Tier 0 or bounded Tier 1 inputs only: prompt features, already-selected
  packet truth, cached priors, fingerprints, and explicit source refs.
- The packet hot path must not call Codex, Claude, providers, subagents, full
  validation, benchmark execution, broad repo scans, projection expansion, or
  broad delivery-ledger reads. Visibility-ledger reads are only allowed when
  the active pressure explicitly requires visible-intervention proof.
- Unknown pressure stays open-world. If uncertainty is high, the packet should
  recommend narrowing or a lower-risk local affordance instead of faking a
  closed posture classification.

## Runtime Contract
- The Odylith context-engine runtime is the canonical compiler for local maintainer projections built from the component registry, knowledge-base docs, code/test structure, agent events, and advisory local pytest/session state.
- `odylith context-engine` is the only supported daemon/client surface for querying those projections.
- Daemon request/response payloads, local projection/session schemas, and cache-backed lookup inputs must evolve additively and fail open to standalone parsing.
- Local state under `.odylith/runtime/` and `.odylith/cache/odylith-context-engine/` is advisory maintainer state only and must never become tracked or canonical repo truth.
- Non-in-process daemon reuse is local-only: accept Unix/TCP transport hints
  only when the owner pid is live, the TCP host stays loopback-only, and the
  request can carry the daemon auth token.

## Reuse Invariants
- Shared projection/compiler/backend reuse is allowed only when the runtime can
  prove one exact provenance tuple for the candidate substrate:
  - `repo_root`
  - `projection_scope`
  - `projection_fingerprint`
  - `sync_generation` when an active sync session exists
  - `code_version`
  - output-affecting `flags`
- Treat derivation generation as the active truth phase for one sync:
  derivation-input mutations such as Registry truth, traceability truth,
  delivery-intelligence truth, and Atlas catalog truth must invalidate the old
  generation immediately.
- Fail closed on reuse. If provenance, generation, or required-table
  expectations do not match, rebuild locally instead of guessing.
- Shared reuse stops at the low-level substrate. Compass, Radar, Registry, and
  other surfaces may share compiler/backend artifacts, but each surface still
  owns its final payload shaping and final rendered bytes.
- Use `odylith sync --repo-root . --debug-cache` when you need an operator
  explanation for reuse versus rebuild; the same run should also leave a debug
  manifest under `.odylith/cache/odylith-context-engine/`.

## Daemon And Session Lifecycle
- Default rich-context posture is `--client-mode auto`.
- Use `warmup` when you expect repeated local packet reads; keep manual `serve` for intentionally warm long-lived loops.
- `auto` may answer without a daemon or reuse an already-running healthy daemon, but background lifecycle must remain explicit and observable.
- Do not silently detach a new background daemon unless an explicit Odylith autospawn opt-in is present.
- Unexpected live daemons or leaked helper processes are bugs, not acceptable steady state.
- Session claims under `.odylith/runtime/sessions/*.json` are advisory concurrency controls, not hard coordination locks or rollout state.
- Session rows with a different branch or head fingerprint should downgrade conflict severity rather than override current-session ownership evidence.

## Architecture And Benchmark Lanes
- Treat `architecture` as a compiled topology dossier, not only a path-to-diagram lookup.
- Read `authority_graph`, `authority_chain`, `blast_radius`, `contract_touchpoints`, `validation_obligations`, `historical_evidence`, `benchmark_summary`, and `execution_hint` before acting on a topology-sensitive packet.
- If architecture cues appear inside a broad shared-scope `impact` packet, read them as warnings, not as proof of full topology coverage.
- Use `benchmark --json` when validating packet-shaping, parity, or optimization changes rather than inferring success from one interactive packet.
- If guidance chunk metadata changes and you need to inspect the compiled catalog directly, use `odylith atlas render --repo-root .`.

## Retrieval And Truthfulness
- Retrieval is deterministic and lexical/path-scoped, not proof of full-repo discovery parity on arbitrary prompts.
- FTS-only or otherwise ungrounded results must raise `full_scan_recommended` instead of pretending the repo is fully covered.
- Advisory local evidence such as `.pytest_cache/v/cache/lastfailed` may shape recommended tests or conflict hints, but absent or corrupt local cache state must fail open back to source parsing.
- Workstream inference is advisory evidence, not canonical truth: only `selection_state=explicit|inferred_confident` may auto-populate a session claim, while `ambiguous|none` must leave ownership unclaimed.
- Topology domains, linked diagrams, and watch-gap warnings are useful acceleration cues, not architecture proof. Any payload with `diagram_watch_gaps` or `full_scan_recommended` requires direct diagram/topology review before acting on it as complete.

## When To Widen
- If the slice is open-ended but still repo-grounded, begin with `status`, `bootstrap-session`, `session-brief`, or `query`; do not default to broad repo scans as the first move.
- If the user already supplied explicit paths or the worktree already narrows the slice, go straight to `impact` or `architecture` instead of repeating a broad repo scan.
- If a packet reports `full_scan_recommended`, `diagram_watch_gaps`, or unresolved ambiguity, stop and widen to `rg` plus direct reads before acting.
- Treat runtime-backed lookup as local-only additive recall, not as a replacement for markdown source-of-truth files.
- For grounded implementation, debugging, and coordination work, Odylith should be the normal operating lane rather than an occasional optional lookup.

## Operator Checks And Standalone Fallback
- Use `status` or `doctor` to inspect lifecycle truth before deciding whether a daemon action is even needed.
- Check `status` or `doctor` before starting an explicit `serve`; warm daemons are for intentionally repeated loops, not the default bootstrap path.
- If recovery needs `doctor --repair --reset-local-state`, stop or let Odylith
  stop the live daemon first rather than deleting runtime artifacts underneath
  it.
- For deploy-, publish-, release-, and pre-commit-adjacent validation, standalone non-daemon CLI execution remains the authoritative fallback.
- `odylith compass watch-transactions` should wait on live daemon change signals first, reuse the same local watcher stack directly when the daemon is unavailable, and fall back to coarse deterministic fingerprint polling only as a last resort.
