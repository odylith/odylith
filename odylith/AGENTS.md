# Odylith AGENTS

Scope: applies to Odylith paths under `odylith/`.

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
- In Codex commentary, keep startup, fallback, routing, and packet-selection internals implicit. Describe progress in task terms like the exact file/workstream, the bug under test, or the validation in flight. If an earlier repo-local start attempt degraded but work can continue safely, do not narrate that history. Do not surface routine `odylith start`, `odylith context`, or `odylith query` commands in progress updates, and never prefix commentary with control-plane receipt labels. Mention Odylith during the work only when the user explicitly asks for the command, a real blocker requires it, or a consumer-versus-maintainer lane distinction matters.
- At closeout, you may add at most one short `Odylith assist:` line if it helps the user understand what Odylith materially contributed. Prefer `**Odylith assist:**` when Markdown formatting is available; otherwise use `Odylith assist:`. Lead with the user win, not Odylith mechanics. When the evidence supports it, frame the edge against `odylith_off` or the broader unguided path. Keep it soulful, friendly, authentic, and factual, not slogan-like. Use only concrete observed counts, measured deltas, or validation outcomes; if you cannot show a user-facing delta, omit the line.
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
- In Codex, treat routed or orchestrated native spawn as the default execution path for substantive grounded work across the consumer lane and both Odylith product-repo maintainer postures: pinned dogfood and detached `source-local` maintainer dev, unless Odylith explicitly keeps the slice local.
- Consumer-side native subagent spawning is a Codex-only workflow today. Do not assume the same spawn contract is supported in Claude Code.

## Source File Size Discipline
- This file-size policy is non-negotiable for Odylith-owned product code in
  this repo.
- For hand-maintained Odylith source, follow the repo-root file-size policy:
  `800` LOC soft limit, `1200` LOC refactor-plan trigger, `2000+` red-zone
  exception only, and a `1500` LOC ceiling for tests.
- When an Odylith-owned hand-maintained source file is already beyond those
  thresholds, treat the next meaningful change as refactor-first work:
  decompose the file into multiple focused files or modules with robustness,
  reliability, and reusability as explicit goals instead of extending the
  oversized file in place.
- Generated or mirrored bundle assets are excluded from this size discipline;
  govern their source-of-truth files instead.
- Prefer `1-2` file decompositions with characterization tests first, and
  prioritize refactor waves by size x churn x centrality rather than launching
  repo-wide "all files above X" rewrites.

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
- Context engine behavior: `agents-guidelines/ODYLITH_CONTEXT_ENGINE.md`
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

## Skills
Shared and consumer-compatible skills:
- `skills/casebook-bug-capture/`
- `skills/casebook-bug-investigation/`
- `skills/casebook-bug-preflight/`
- `skills/compass-executive/`
- `skills/compass-timeline-stream/`
- `skills/component-registry/`
- `skills/odylith-context-engine-operations/`
- `skills/diagram-catalog/`
- `skills/registry-spec-sync/`
- `skills/schema-registry-governance/`
- `skills/subagent-orchestrator/`
- `skills/subagent-router/`
- `skills/session-context/`
- `skills/delivery-governance-surface-ops/`
- `skills/security-hardening/`
