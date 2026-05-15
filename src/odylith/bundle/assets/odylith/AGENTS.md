# Odylith Repo Guidance

Scope: applies to the local customer-owned `odylith/` tree in this repository.

## Ownership
- This starter tree is local repo truth, not a copy of the Odylith product repo.
- `odylith/runtime/source/product-version.v1.json` pins the intended Odylith product version.
- `odylith/runtime/source/tooling_shell.v1.json` is local repo shell metadata and stays customer-owned.
- `.odylith/trust/managed-runtime-trust/` is local Odylith runtime trust state and may be refreshed by install, upgrade, feature-pack activation, or doctor.
- `odylith/surfaces/brand/` is an Odylith-managed starter asset set for local HTML surfaces; first install and explicit repair may restore it, but normal upgrades should not rewrite it.
- `.claude/`, `.codex/`, `.agents/skills/`, `odylith/AGENTS.md`, `odylith/CLAUDE.md`, the shipped scoped guidance companions under `odylith/**/AGENTS.md` and `odylith/**/CLAUDE.md`, `odylith/agents-guidelines/`, and `odylith/skills/` are Odylith-managed guidance assets and may be refreshed by install, upgrade, or doctor.
- Truth under `odylith/radar/`, `odylith/technical-plans/`, `odylith/casebook/`, `odylith/registry/`, and `odylith/atlas/` belongs to this repository and must not be rewritten by normal upgrades.
- Product runtime code and product-managed assets run from `.odylith/` and the installed Odylith runtime package.
- Do not treat this folder as disposable cache; it belongs to the repository using Odylith.

## Working Rule
- For work under `odylith/`, read this file first.
- Use `./.odylith/bin/odylith` for Odylith CLI workflows in this repository.
- Before any substantive repo scan or code change outside trivial fixes, run `./.odylith/bin/odylith start --repo-root .` first and keep the active workstream, component, or packet in scope before raw repo search, tests, or edits. Direct repo scan before that start step is a policy violation unless the task is trivial or Odylith is unavailable.
- Do not run `odylith context`, `odylith query`, `git status`, broad repo search, or other repo-inspection commands in parallel with that start step. Let `start` finish first; then run `odylith context --repo-root . <ref>` only when the user, start output, or governed truth gives an exact anchor.
- Keep startup, Context Engine, Execution Engine, memory substrate, Tribunal, Intervention Engine, observers, governance, subagent routing, Surface DAGs, delivery, analysis, and migration-breakage observation active. Improve latency by routing, caching, batching, and shortening always-loaded guidance, not by disabling engines.
- The repo-root managed `AGENTS.md` block is the shared hard-law kernel for both Codex and Claude Code. It owns help/show/capabilities fast paths, commentary discipline, queue adoption, governance refresh, target-repo validation, guidance-behavior proof, Discipline proof, and the default Codex/Claude lane; do not duplicate or weaken those rules here.
- Codex and Claude Code share the same default Odylith lane: the repo-root `AGENTS.md` contract, `./.odylith/bin/odylith`, truthful `odylith ... --help`, and the grounded governance workflow. Keep host-specific tips rare and capability-gated.
- In coding-agent commentary, keep startup, fallback, routing, and packet-selection internals implicit. Describe progress in task terms like the exact file/workstream, the bug under test, or the validation in flight. If startup needs narrowing but work can continue, do not narrate it, and never say `Startup fell back`. Do not surface routine `odylith start`, `odylith context`, or `odylith query` commands in progress updates, and never prefix commentary with control-plane receipt labels. Keep normal commentary task-first and human. Reserve `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` for rare high-signal moments.
- Capability inventory is product-owned and host-agnostic: if the user asks for Odylith capabilities, engines, product architecture, or the capability map, run `odylith capabilities` and print stdout only. Do not infer the taxonomy from `odylith --help`, `odylith show`, Claude Code, Codex, or any other host model capability surface.
- Help and technical-plan command discovery use the single authoritative help path: do not run parallel exploratory filesystem probes whose failure can cancel the visible help call. `odylith plan --help` is read-only; do not invent plan write flows or probe `odylith/technical-plans/source/`.
- CLI-first is non-negotiable here too: default to the nearest `AGENTS.md`, the repo-local launcher, and truthful `odylith ... --help`; use `odylith backlog ...`, `odylith governance ...`, `odylith validate plan-* ...`, `odylith bug ...`, `odylith component ...`, `odylith registry ...`, `odylith atlas ...`, and `odylith compass ...` before hand edits. Do not hand-edit governed files where a CLI exists. `odylith backlog create` remains fail-closed and must receive grounded Problem, Customer, Opportunity, Product View, and Success Metrics text.
- Empty or thin consumer repos can still receive project-first governance from user intent. Use `odylith greenfield propose --repo-root . --prompt "<request>"` for the no-write Product Intent Confirmation request, then write a compact product-first interpretation in chat from live reasoning: product story, actors, systems, assumptions, ambiguities, and a clear Next step block with Confirm, Edit, and Reject choices. Do not generate backlog, Registry, Atlas, release waves, validation obligations, proposal JSON, or create writes before intent confirmation. After confirmation, write that same visible Product Intent Confirmation to `.odylith/runtime/greenfield/confirmed-intent.md`, then run `odylith greenfield create --repo-root . --prompt "<request>" --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release 0.0.1`; Odylith builds the apply-ready proposal from the accepted narrative, validates it, runs the Tribunal write gate, writes records, and refreshes readable views. `odylith greenfield propose --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm-intent --format json` is only an optional review artifact when explicitly requested; feed that exact generated JSON to `greenfield apply` if using the file workflow. Do not ask the operator to inspect proposal JSON or confirm a second time by default. Do not inspect Odylith source files, Python modules, `.odylith`, local examples, or bundle assets to discover schema fields, and do not hand-author or repair proposal JSON. Do not run confirmed create from a thin prompt without `--intent-file`. No canned domain families, scaffolds, or code before product gates. Surface only the human-readable created-record summary or validation/Tribunal blockers.
- Treat live teaser, `**Odylith Observation**`, and `Odylith Proposal` as the intervention-engine fast path; treat `Odylith Assist:` as the chatter-owned closeout. Do not collapse those layers.
- Codex checkpoint hooks may keep hidden Observation/Proposal/Assist continuity and surface earned notes; Claude direct-edit and Bash PostToolUse hooks stay silent on success and emit only compact failure/skipped-refresh status. Claude Stop is memory/logging only, not a fallback closeout or live-note recovery lane.
- Hook `systemMessage` or `additionalContext` generation is not proof of chat-visible UX. Before claiming the intervention UX is active in a specific chat, run or cite `odylith codex intervention-status` or `odylith claude intervention-status`; it is the low-latency delivery record for Teaser, Ambient Highlight, Observation, Proposal, and Assist readiness. Only call a session fully end to end after it reports `Activation: ready` and a chat-visibility line is confirmed. Treat recorded-only and waiting-for-chat states as partial proof. When needed, run `odylith codex visible-intervention` or `odylith claude visible-intervention` and show that Markdown directly.
- Existing Codex and Claude sessions may not hot-reload changed hooks, guidance, or source-local runtime code; prove changed visibility behavior in a fresh/reloaded session or render `visible-intervention` output in the existing chat.
- At closeout, or when a visible-intervention recovery renders a prompt-submit or visibility-proof note, add at most one short `Odylith Assist:` or `**Odylith Assist:**` line only when it helps the user understand material value; normal non-passthrough prompts do not get an Assist line by default. Do not add Assist just because Odylith ran. Lead with the user win, updated governance IDs inline when changed, affected governance-contract IDs when no governed file moved, the `odylith_off` or broader unguided path edge when supported, keep it crisp, authentic, clear, simple, insightful, and ground the line in concrete observed counts, measured deltas, or validation outcomes, or a concrete chat-visibility complaint. Use `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` only for rare high-signal moments. Silence is better than filler.
- For live blocker lanes, never say `fixed`, `cleared`, or `resolved` without qualification unless the hosted proof moved past the prior failing phase. Force three checks first: same fingerprint as the last falsification or not, hosted frontier advanced or not, and whether the claim is code-only, preview-only, or live.
- In consumer repos, grounding Odylith is diagnosis authority, not blanket write authority: if the issue target is Odylith itself, stop at diagnosis and maintainer-ready feedback unless the operator explicitly authorizes Odylith mutation.
- Treat `odylith upgrade`, `odylith reinstall`, `odylith doctor --repair`, `odylith sync`, and `odylith dashboard refresh` as writes when they change `odylith/` or `.odylith/`; do not run them autonomously as Odylith fixes in consumer repos.
- Treat backlog/workstream, plan, Registry, Atlas, Casebook, Compass, and session upkeep as part of the same grounded Odylith workflow rather than optional aftercare; search existing workstream, plan, bug, component, diagram, and recent session/Compass context first. If the slice is genuinely new and it is repo-owned non-product work, create the missing workstream and bound plan before non-trivial implementation; if the issue is Odylith itself in a consumer repo, produce a maintainer-ready feedback packet instead.
- Queued backlog items, case queues, and shell or Compass queue previews are not implicit implementation instructions. Unless the user explicitly asks to work a queued item, do not pick it up automatically just because it appears in Radar, Compass, the shell, or another Odylith queue surface.
- When a routine governance task already maps to a first-class CLI family such as `odylith bug capture`, `odylith backlog create`, `odylith component register`, `odylith atlas scaffold`, or `odylith compass log`, go straight to that CLI. For quick visibility after a narrow truth change, rerender only the owned surface: `odylith radar refresh`, `odylith registry refresh`, `odylith casebook refresh`, `odylith atlas refresh`, or `odylith compass refresh`; use `odylith compass deep-refresh` for brief settlement and `odylith sync` for the broader governance lane.
- Treat routed or orchestrated native delegation as the default candidate for substantive grounded consumer-lane work when the route is bounded, the host transport supports it, and the active host policy allows it; keep transport support separate from current-session spawn permission/effectiveness.
- Treat AI slop as a regression. Apply that bar across consumer and maintainer lanes, Codex and Claude, any language, runtime code, hooks, prompts, docs, config, templates, generators, and managed assets. Codex and Claude must enforce the same anti-slop contract across consumer and maintainer lanes. Treat the slop class, not the language syntax, as the thing to ban. Consumer repos may be Python, TypeScript, JavaScript, Go, Rust, Java, shell, SQL, or mixed-language; any codebase or project surface counts. No transitional states: move ownership, not just file boundaries; partial shared-kernel adoption is still incomplete; if the replacement smell still exists in the touched slice, the pass is incomplete. Prose-only hardening is incomplete. Repo-wide or lane-wide anti-slop claims require two proof layers: fresh behavior proof for the touched slice and a fresh structural inventory for the claimed scope. Browser-rendered surfaces require the full headless browser matrix across normal, empty/fallback, and degraded or error states. Full rule: `odylith/agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md`; use `odylith/skills/odylith-code-hygiene-guard/SKILL.md` when quality pressure is high.
- For guidance behavior pressure cases, use `odylith validate guidance-behavior --repo-root .` for deterministic proof and `odylith benchmark --profile quick --family guidance_behavior` for benchmark-family proof. Compact packet summaries only prove the proof path is available; fresh validation still requires the explicit command.
- Use native host capabilities where they exist: Codex uses `.codex/` hooks/config/agents plus curated `.agents/skills/` command shims in trusted projects; Claude uses `.claude/` hooks, commands, skills, Task subagents, rules, statusline, and auto-memory. Keep both on the same grounding, memory, surfaces, and orchestration contract without mixing host-only fields.
- Treat the managed guidance files under `.claude/`, `.codex/`, the curated `.agents/skills/` command shims, `odylith/AGENTS.md`, `odylith/CLAUDE.md`, the shipped scoped `odylith/**/AGENTS.md` and `odylith/**/CLAUDE.md` companions, `odylith/agents-guidelines/`, and the specialist references under `odylith/skills/` as the Odylith operating layer; keep repo-specific truth in the governance surfaces beside them.

## Common Fast Paths
- `./.odylith/bin/odylith bug capture --help`
- `./.odylith/bin/odylith backlog create --help`
- `./.odylith/bin/odylith greenfield propose --help`
- `./.odylith/bin/odylith component register --help`
- `./.odylith/bin/odylith atlas scaffold --help`
- `./.odylith/bin/odylith compass log --help`
- Technical-plan maintenance: `./.odylith/bin/odylith governance --help` and `./.odylith/bin/odylith validate --help`; `./.odylith/bin/odylith plan --help` is a read-only command guide.
- `./.odylith/bin/odylith radar refresh --repo-root .`
- `./.odylith/bin/odylith registry refresh --repo-root .`
- `./.odylith/bin/odylith casebook refresh --repo-root .`
- `./.odylith/bin/odylith atlas refresh --repo-root . --atlas-sync`
- `./.odylith/bin/odylith compass refresh --repo-root .`
- `./.odylith/bin/odylith compass deep-refresh --repo-root .`
- `./.odylith/bin/odylith validate guidance-behavior --repo-root .`
- `./.odylith/bin/odylith benchmark --profile quick --family guidance_behavior`
- Codex-only when useful: `./.odylith/bin/odylith codex compatibility --repo-root .` tells you whether optional project-asset optimizations are actually active on this host.
- Keep `.agents/skills` lookup, missing-shim, and fallback-source details implicit unless they change the next user-visible action.

## Routing
- Code hygiene and decomposition: `agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md`
- Context engine behavior: `agents-guidelines/ODYLITH_CONTEXT_ENGINE.md`
- Grounding and narrowing: `agents-guidelines/GROUNDING_AND_NARROWING.md`
- Governance and delivery surfaces: `agents-guidelines/DELIVERY_AND_GOVERNANCE_SURFACES.md`
- Product surfaces and runtime: `agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md`
- Security and trust boundaries: `agents-guidelines/SECURITY_AND_TRUST.md`
- Subagent routing and execution posture: `agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md`
- Validation and testing: `agents-guidelines/VALIDATION_AND_TESTING.md`
- Install, upgrade, and recovery: `agents-guidelines/UPGRADE_AND_RECOVERY.md`

## Specialist Skills
- `odylith/skills/` is a specialist reference layer. Routine backlog, technical-plan, bug, spec, component, and diagram upkeep should stay on `AGENTS.md`, the repo-local launcher, and truthful `odylith ... --help` first. `odylith plan --help` is a read-only guide; use `odylith governance ...` and `odylith validate plan-* ...` for technical-plan maintenance and validation.
- `skills/delivery-governance-surface-ops/`
- `skills/odylith-context-engine-operations/`
- `skills/odylith-guidance-behavior/`
- `skills/subagent-router/`
- `skills/subagent-orchestrator/`
- `skills/session-context/`
- `skills/component-registry/`
- `skills/diagram-catalog/`
- `skills/casebook-bug-capture/`
- `skills/casebook-bug-investigation/`
- `skills/casebook-bug-preflight/`
- `skills/compass-executive/`
- `skills/compass-timeline-stream/`
- `skills/code-hygiene-guard/`
- `skills/registry-spec-sync/`
- `skills/schema-registry-governance/`
- `skills/security-hardening/`

## Consumer Boundary
- Consumer installs intentionally exclude Odylith product-maintainer release workflow from the local repo guidance and skill set.
- Use the installed Odylith guidance as the default lane here, and pull in specialist skills only when the task is genuinely advanced or high-risk; do not mirror the Odylith product repo release process into this repository.
