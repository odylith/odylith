# Odylith AGENTS

Scope: applies to Odylith paths under `odylith/`.

## CLI-First Non-Negotiable
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting.
- When an Odylith CLI command exists for an operation, you must call the CLI command and you must not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference.
- The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`.
- The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code, so delegated work inherits the same contract.

## Purpose
- Keep Odylith guidance, runtime surfaces, and execution helpers product-owned.
- Keep Odylith behavior scoped to Odylith paths and Odylith-owned tasks.
- Keep product-maintainer release guidance and skills explicit instead of
  leaking them into bundled consumer instructions.
- In consumer repos, keep Odylith-fix requests in diagnosis-and-handoff mode
  instead of local Odylith patching.

## What Odylith Owns Here
- guidance under `odylith/agents-guidelines/`
- skills under `odylith/skills/`
- maintainer-only release guidance and skills under `odylith/maintainer/`
- product overview docs at `odylith/*.md`
- runtime docs/assets under `odylith/runtime/`
- shell-wide surface assets under `odylith/surfaces/`
- surface-owned truth under `odylith/radar/`, `odylith/atlas/`, `odylith/compass/`, `odylith/registry/`, and `odylith/casebook/`
- repo-local governance truth under `odylith/technical-plans/`, `odylith/radar/source/`, `odylith/casebook/bugs/`, and `odylith/registry/source/`
- Registry-owned component dossiers under `odylith/registry/source/components/`

## Working Rule
- For work under `odylith/`, read this file first.
- For repo-owned paths outside `odylith/`, defer to the repo root guidance.
- When both apply, treat the repo root as authoritative for repo-owned policy and this file as authoritative for Odylith-owned product behavior.
- In repos that carry Odylith under `odylith/`, use the repo-local launcher `./.odylith/bin/odylith` for Odylith CLI workflows.
- When the launcher is absent in a consumer repo, the canonical first bootstrap
  and rescue command is `curl -fsSL https://odylith.ai/install.sh | bash`.
- Keep the lane matrix explicit:
  - consumer lane: installed Odylith runtime only, no `source-local`
  - product-repo maintainer mode: the Odylith product repo itself
  - maintainer mode has two postures:
    - pinned dogfood for shipped-runtime proof
    - detached `source-local` for live unreleased source execution
- In the Odylith product repo's maintainer mode, the Git `main` branch is read-only for authoring. This is non-negotiable.
- Never perform code or tracked-file edits on `main`; if the current branch is `main`, create and switch to a new branch before the first edit, stage, or commit, and if work is already on a non-`main` branch, keep using that branch.
- Keep the three boundaries explicit:
  - runtime boundary: which interpreter runs Odylith
  - write boundary: which files the agent may edit
  - validation boundary: which toolchain proves the target repo still works
- When repo-root guidance points at Odylith governance or runtime behavior, this file and the nearest local `AGENTS.md` under `odylith/` are the authority for that slice.
- For installed consumer guidance, any substantive repo scan or code change outside trivial fixes must start from the repo-local Odylith entrypoint, with the active workstream, component, or packet kept in scope before raw repo search, tests, or edits.
- Direct repo scan before that start step is a policy violation unless the task is trivial or Odylith is unavailable.
- Start substantive turns with `./.odylith/bin/odylith start --repo-root .`; it chooses the safe first lane and prints the exact next command when Odylith still needs narrower evidence.
- When you already know the exact workstream, component, path, or id, use `./.odylith/bin/odylith context --repo-root . <ref>` before raw repo search. Use `./.odylith/bin/odylith query --repo-root . "<terms>"` only after concrete anchors already exist. Keep `odylith context-engine ...` for advanced packet control.
- Default to the nearest `AGENTS.md`, the repo-local launcher, and truthful `odylith ... --help` for routine backlog, plan, bug, spec, component, and diagram upkeep. Treat repo-root `.agents/skills/` shims and `odylith/skills/` as specialist overlays rather than as the default path.
- When a routine governance task already maps to a first-class CLI family such as `odylith bug capture`, `odylith backlog create`, `odylith component register`, `odylith atlas scaffold`, or `odylith compass log`, go straight to that CLI and keep any `.agents/skills` lookup, missing-shim, or fallback-path details implicit unless they change the next user-visible action.
- `odylith backlog create` is fail-closed and must receive grounded Problem, Customer, Opportunity, Product View, and Success Metrics text; never create or accept a title-only, placeholder, or boilerplate Radar workstream.
- For quick visibility after a narrow truth change, rerender only the owned surface: `odylith radar refresh`, `odylith registry refresh`, `odylith casebook refresh`, `odylith atlas refresh`, or `odylith compass refresh`. Use `odylith compass deep-refresh` when you also want brief settlement. Keep `odylith sync` as the broader governance and correctness lane.
- Keep the default operating lane shared across Codex and Claude Code: repo-root guidance, the repo-local launcher, truthful `odylith ... --help`, and the grounded governance workflow should mean the same thing on both hosts. Add host-specific tips only when the host exposes a real native capability that materially reduces hops.
- Treat AI slop as a regression. Apply that bar across consumer and
  maintainer lanes, across
  Codex and Claude. Codex and Claude must enforce the same anti-slop contract
  across consumer and maintainer lanes. Treat the slop class, not the
  language syntax, as the thing to ban. Consumer repos may be Python,
  TypeScript, JavaScript, Go, Rust, Java, shell, SQL, or mixed-language; the
  language changes, the anti-slop bar does not. Do not ship fake
  modularization, `bind(host)` globals injection, alias walls, duplicated
  micro-helpers, phase-mixed monoliths, near-identical host mirrors, or
  filler comments in runtime code, docs, hooks, prompts, or config surfaces.
  Use
  `agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md` and
  `skills/odylith-code-hygiene-guard/SKILL.md` when quality pressure is high.
- For guidance behavior pressure cases, use `odylith validate guidance-behavior --repo-root .` for deterministic proof and `odylith benchmark --profile quick --family guidance_behavior` for benchmark-family proof. Compact packet summaries only prove the proof path is available; fresh validation still requires the explicit command.
- Odylith Discipline is the v0.1.11 shared Codex/Claude behavior contract: hard laws are deterministic, runtime pressure is open-world, stance is local and credit-safe, passing checks stay quiet, and durable learning requires validator, benchmark, or Tribunal/governance proof. Use `odylith discipline status/check/explain`, `odylith validate discipline --repo-root .`, and `odylith benchmark --profile quick --family discipline --no-write-report --json`; none of those discipline hot paths may call host models, providers, subagents, broad scans, full validation, or projection expansion.
- In coding-agent commentary, keep startup, fallback, routing, and packet-selection internals implicit. Describe progress in task terms like the exact file/workstream, the bug under test, or the validation in flight. If an earlier repo-local start attempt degraded but work can continue safely, do not narrate that history. Do not surface routine `odylith start`, `odylith context`, or `odylith query` commands in progress updates, and never prefix commentary with control-plane receipt labels. Mention Odylith during the work only when the user explicitly asks for the command, a real blocker requires it, or a consumer-versus-maintainer lane distinction matters.
- Keep normal commentary task-first and human. Weave Odylith-grounded facts into ordinary updates when they change the next move, and reserve explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` labels for rare high-signal moments. Pick the strongest one or stay quiet.
- Treat live teaser, `**Odylith Observation**`, and `Odylith Proposal` as the
  intervention-engine fast path. Treat `Odylith Assist:` as the chatter-owned
  closeout. Do not collapse those two layers into one ad hoc narration path.
- When the shared conversation-observation runtime earns a full
  `**Odylith Observation**` or `**Odylith Proposal**`, preserve that exact
  label contract and keep the markdown clear, warm, and human. Do not flatten
  it into mechanical alert copy, alternate host-specific labels, or rigid
  compliance prose.
- Preserve the shipped shape too: Observation should look like
  `Odylith Assist`, which means one short labeled line. Proposal should be a
  short ruled block with the heading, a couple of lines, a few bullets, and
  the confirmation line.
- Keep one stable intervention identity across teaser, observation, and
  proposal for the same session-local moment. Later hooks may add evidence or
  surface the first eligible proposal, but they must not make the same moment
  feel like a fresh branded interruption.
- For Codex and Claude checkpoint hooks, keep the full Observation,
  Proposal, and Assist bundle in hidden developer context for continuity, but
  surface the earned Observation/Proposal beat visibly at the hook moment when
  the host renders hook output. If the host keeps hook output hidden, render
  the assistant-visible fallback Markdown in chat instead of claiming the
  engine is active. Stop is the fallback closeout and live-beat recovery lane,
  not the primary intervention moment; unseen Ambient Highlight,
  Observation, or Proposal beats may replay there before Assist.
- Hook `systemMessage` or `additionalContext` generation is not proof of
  chat-visible UX. The user-visible contract is satisfied only by rendered
  chat text or by a host channel that is proven visible in the active session.
  When in doubt, run `odylith codex visible-intervention` or `odylith claude
  visible-intervention` and show that Markdown directly.
- Before claiming the intervention UX is active in a specific chat, run or
  cite `odylith codex intervention-status` or `odylith claude
  intervention-status` for that host/session. That status surface is the
  low-latency delivery ledger for Teaser, Ambient Highlight, Observation,
  Proposal, and Assist readiness; hook payload generation alone is not enough.
- A plain `Odylith, show me what you can do` request is the advisory
  `odylith show` repo-capability demo. It is not a request to prove
  intervention UX, diagnose install posture, run `start`, run `doctor`, or
  explain missing launcher state. Use the first available show command and
  print stdout only.
- Existing Codex and Claude sessions may not hot-reload changed hooks,
  guidance, or source-local runtime code. After changing intervention
  visibility behavior, prove it in a newly started or explicitly reloaded
  session, or render `visible-intervention` output directly in the existing
  chat instead of claiming other open sessions are active.
- If you need to show that UX to a human in-chat, prefer rendered Markdown or
  plain prose. Do not wrap the product moment in fenced raw Markdown unless
  the task is explicitly about debugging the raw source text.
- Keep those Observation/Proposal moments rooted in the user's actual prompt
  and evidence across teaser, observation, proposal, apply, and decline
  phases. Do not let later hooks or derived surfaces fall back to Odylith's own
  pending/applied summary strings as if they were conversation truth.
- That observation/proposal voice is a product invariant across Codex,
  Claude, maintainer `source-local`, pinned dogfood, and consumer lanes:
  friendly, delightful, soulful, insightful, simple, clear, accurate,
  precise, and above all human. Future voice packs may tune the voice later;
  the shipped default brand voice is non-negotiable now.
- At closeout, you may add at most one short `Odylith Assist:` line if it helps the user understand what Odylith materially contributed. Prefer `**Odylith Assist:**` when Markdown formatting is available; otherwise use `Odylith Assist:`. Lead with the user win, link updated governance IDs inline when they were actually changed, and when no governed file moved, name the affected governance-contract IDs from bounded request or packet truth without calling them updated. Frame the edge against `odylith_off` or the broader unguided path when the evidence supports it. Keep it crisp, authentic, clear, simple, insightful, erudite in thought, soulful, friendly, free-flowing, human, and factual. Ground the line in concrete observed counts, measured deltas, or validation outcomes. Humor is fine only when the evidence makes it genuinely funny. Silence is better than filler. At most one supplemental closeout line may appear, chosen from `Odylith Risks:`, `Odylith Insight:`, or `Odylith History:` when the signal is real.
- Explicit feedback that Odylith ambient highlights, interventions, Assist,
  Observations, Proposals, hooks, or chat output are not visible is a real
  closeout signal. A short `Odylith Assist:` may acknowledge that visibility
  continuity without claiming artifact updates; ordinary low-signal short
  turns should still stay silent.
- For live blocker lanes, never say `fixed`, `cleared`, or `resolved` without qualification unless the hosted proof moved past the prior failing phase. Force three checks first: same fingerprint as the last falsification or not, hosted frontier advanced or not, and whether the claim is code-only, preview-only, or live.
- For substantive tasks, follow this workflow check in order: read the nearest `AGENTS.md`; run the repo-local `odylith start`/`odylith context` step; identify the active workstream, component, or packet; then move into repo scan, tests, and edits.
- In consumer repos, grounding Odylith is diagnosis authority, not blanket
  write authority: if the issue target is Odylith itself, inspect, cite
  evidence, and hand off to the platform maintainer unless the operator
  explicitly authorizes local Odylith mutation.
- Treat self-directed `odylith upgrade`, `odylith reinstall`,
  `odylith doctor --repair`, `odylith sync`, and `odylith dashboard refresh`
  as forbidden Odylith-fix paths in consumer repos because they are writes, not
  neutral inspection.
- Use direct `rg`, targeted source reads, or standalone host search only when Odylith is unavailable, the task stays within the trivial-fix exception, or Odylith explicitly recommends widening or fallback.
- For substantive grounded repo work, treat backlog, plan, Registry, Atlas,
  Casebook, Compass, and session upkeep as part of implementation, not
  optional aftercare, but switch to evidence-and-handoff when the issue is
  Odylith itself in a consumer repo.
- Queued backlog items, case queues, and shell or Compass queue previews are not implicit implementation instructions. Unless the user explicitly asks to work a queued item, do not pick it up automatically just because it appears in Radar, Compass, the shell, or another Odylith queue surface.
- Search existing workstream, active plan, related bugs, related components,
  related diagrams, and recent Odylith session or Compass context first; for
  consumer Odylith-fix requests, cite that evidence and hand it off instead of
  extending, consolidating, reopening, or creating Odylith truth locally.
- If grounded evidence shows the slice is genuinely new and it is repo-owned
  non-product work, create the missing workstream and bound plan before
  continuing non-trivial implementation; if the issue is Odylith itself in a
  consumer repo, produce a maintainer-ready feedback packet instead.
- Keep intent, constraints, validation obligations, and major decisions alive through Odylith session packets and Compass updates so later turns accumulate context instead of restarting from scratch.
- Dogfood this same policy in the Odylith product repo: maintainers and product docs should model Odylith-first retrieval instead of bypassing it with ad-hoc repo search.
- `./.odylith/bin/odylith` running on Odylith's managed runtime never means "only Odylith files can be edited". File-edit authority follows repo scope, not interpreter choice.
- In consumer repos, validate repo code with the repo's own `python`, `uv`, Poetry, Conda, or equivalent project toolchain after Odylith work narrows the slice.
- In the Odylith product repo, use pinned dogfood for shipped-runtime proof and detached `source-local` only when maintainer work intentionally needs live unreleased `src/odylith/*` execution.
- Treat routed or orchestrated native delegation as the default execution path for substantive grounded work when the current host supports it across the consumer lane and both Odylith product-repo maintainer postures: pinned dogfood and detached `source-local` maintainer dev, unless Odylith explicitly keeps the slice local.
- Codex and Claude Code are both validated Odylith delegation hosts under the same grounding, routing, and validation contract. Codex uses routed `spawn_agent` payloads; Claude Code uses the same bounded delegation contract through Task-tool subagents and the checked-in `.claude/` project assets.

## Coding Standards
- Treat AI slop as a regression in Odylith-owned code and guidance.
- The shared anti-slop and decomposition contract now lives in
  `agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md`; that guide is
  consumer-safe, host-shared, and language-agnostic. Use it for the explicit
  ban list, decomposition triggers, docstring bar, and proof expectations.
- The shared Odylith coding baseline now lives in
  `agents-guidelines/CODING_STANDARDS.md`; that file is consumer-safe and
  defers to consumer repo standards for consumer-owned code.
- Maintainer-only Odylith product coding policy now lives in
  `maintainer/agents-guidelines/CODING_STANDARDS.md`; use it in maintainer
  mode for deep-scan expectations, inline documentation bar, source-file
  discipline, refactor-first posture, and coding validation expectations.

## Governance Contract
- For non-trivial work touching Odylith governance under `odylith/`, create or update the bound plan under `odylith/technical-plans/` per `technical-plans/AGENTS.md`.
- Do not continue non-trivial implementation unless the active slice is already bound to a valid Radar workstream under `odylith/radar/source/`, or you backfill that workstream in the same change.
- Review matching bug records under `odylith/casebook/bugs/` before implementation and record matching bug ids or `no related bug found` in the active technical plan or handoff.
- Before final handoff, reconcile lifecycle truth across the touched plan, workstream, bug, and rendered governance surfaces by following the source contracts under `odylith/`.

## Product Boundary
- Shared Odylith product code, shared guidance, and shared runtime/surface files under `odylith/` should be fixed in `/Users/freedom/code/odylith` first.
- In consumer repos, stop at diagnosis and maintainer feedback for Odylith
  product issues; do not patch `odylith/` or `.odylith/` locally as a
  self-directed fix.
- After a product fix lands there, refresh the local `odylith/` tree through
  maintainer- or operator-authorized lifecycle commands.
- Repo-local records under `odylith/radar/source/`,
  `odylith/technical-plans/`, `odylith/casebook/bugs/`, and
  `odylith/registry/source/` remain editable when they describe this repo's
  own workstreams, bugs, and governance state, but they are read-only for
  consumer Odylith-fix requests.

## Routing
- Code hygiene and decomposition: `agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md`
- Context engine behavior: `agents-guidelines/ODYLITH_CONTEXT_ENGINE.md`
- Shared coding standards baseline: `agents-guidelines/CODING_STANDARDS.md`
- Maintainer coding standards: `maintainer/agents-guidelines/CODING_STANDARDS.md`
- Grounding and narrowing: `agents-guidelines/GROUNDING_AND_NARROWING.md`
- Governance and delivery surfaces: `agents-guidelines/DELIVERY_AND_GOVERNANCE_SURFACES.md`
- Security and trust boundary: `agents-guidelines/SECURITY_AND_TRUST.md`
- Subagent routing and execution posture: `agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md`
- Product surfaces and runtime: `agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md`
- Validation and testing: `agents-guidelines/VALIDATION_AND_TESTING.md`
- Install, upgrade, and recovery: `agents-guidelines/UPGRADE_AND_RECOVERY.md`
- Maintainer-only release work: `maintainer/AGENTS.md`
- Workstream source contracts: `radar/source/AGENTS.md`
- Technical-plan lifecycle: `technical-plans/AGENTS.md`
- Bug-record lifecycle: `casebook/bugs/AGENTS.md`
- Registry source contracts: `registry/source/AGENTS.md`

## Specialist Skills
- Routine backlog, plan, bug, spec, component, and diagram upkeep should stay on `AGENTS.md`, the repo-local launcher, and truthful `odylith ... --help` first.
- Repo-root `.agents/skills/` is the only Codex-specific shortcut surface worth curating, and only for the high-frequency CLI lane rather than as a mirror of the full specialist inventory.
Shared and consumer-compatible skills:
- `skills/casebook-bug-capture/`
- `skills/casebook-bug-investigation/`
- `skills/casebook-bug-preflight/`
- `skills/compass-executive/`
- `skills/compass-timeline-stream/`
- `skills/code-hygiene-guard/`
- `skills/component-registry/`
- `skills/odylith-context-engine-operations/`
- `skills/odylith-guidance-behavior/`
- `skills/diagram-catalog/`
- `skills/registry-spec-sync/`
- `skills/schema-registry-governance/`
- `skills/subagent-orchestrator/`
- `skills/subagent-router/`
- `skills/session-context/`
- `skills/delivery-governance-surface-ops/`
- `skills/security-hardening/`
