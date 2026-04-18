# Odylith

## Adaptive Agent Operating Character Contract
- For v0.1.11, Odylith owns Adaptive Agent Operating Character as a platform
  contract: local pressure observations, deterministic hard laws, adaptive
  stance facets, ranked affordances, credit-safe budgets, compact learning,
  Tribunal promotion, and benchmark sovereignty. The contract ids are
  `odylith_agent_operating_character.v1`,
  `odylith_agent_operating_character_learning.v1`, and
  `odylith_agent_operating_character_runtime_budget.v1`.
- The public command surface is `odylith character status/check/explain`,
  `odylith validate agent-operating-character --repo-root .`, and the existing
  `odylith benchmark --family agent_operating_character` path. Character hot
  paths are deterministic and must not spend host model or provider credits.
- The host/lane support contract is
  `odylith_agent_operating_character_host_lane_support.v1`: Codex and Claude
  are first-class host families, dev/dogfood/consumer are first-class lanes,
  and host model aliases resolve to adapter families without turning Character
  classification into a model-consuming path.
Last updated: 2026-04-15


Last updated (UTC): 2026-04-14

## Purpose
Odylith is the installable local governance and execution agent and platform
for the governance engine. It owns the public CLI, install and repair
lifecycle, tracked product truth under `odylith/`, mutable runtime state under
`.odylith/`, and the composition of grounding, delegation control, diagnosis,
remediation, and rendering.

## Scope And Non-Goals
### Odylith owns
- Product code under `src/odylith/`.
- Product documentation, specs, skills, bundled install assets, and the
  checked-in third-party attribution ledger.
- Product-owned governance records in this repository.
- Bootstrap of customer-owned repo truth plus local runtime activation and verification.
- Public CLI contract for operators and coding agents.

### Odylith explicitly does not own
- Consumer-repo plans, bugs, diagrams, specs, or runbooks outside their local
  repositories.
- Remote service state as the primary authority for product truth.
- Silent mutation of tracked repo truth from caches or local runtime artifacts.

## Developer Mental Model
- `src/odylith/cli.py` is the public front door. Every supported operator
  action fans out from that command surface.
- The hosted `install.sh` contract is one-command and non-interactive. Odylith
  detects the environment, selects the right managed assets, verifies release
  evidence, and installs the full stack without install-time prompts.
  The canonical hosted bootstrap command is
  `curl -fsSL https://odylith.ai/install.sh | bash`.
  The install posture is explicitly tuned for robustness, speed, availability,
  security, reliability, and zero-friction operator UX.
- In the public Odylith repo, `odylith/` is product-owned tracked truth plus
  checked-in generated surfaces. In a consumer repo, `odylith/` is a separate
  customer-owned bootstrap and local-truth tree.
- In a consumer repo, `odylith/agents-guidelines/` is the only subtree treated
  as Odylith-managed guidance that can be refreshed by normal lifecycle
  commands.
- `.odylith/` is local runtime state, staged product versions, ledgers, and
  activation metadata. Its cache-like portions are rebuildable, but uninstall
  preserves the tree because the local operational history belongs to the
  repository using Odylith.
- Install, doctor, repair, on/off, sync, routing, orchestration, diagnosis,
  and surface generation are all parts of one product, not separate tools that
  happen to share a repository.

### Control-plane leverage
- Odylith is not trying to beat the underlying model weights. It is trying to
  improve the default operating policy around the same model.
- In product terms, Odylith should improve:
  - context quality
  - search policy
  - validation policy
  - recovery policy
- A stronger base model still gets more leverage from Odylith than a weaker
  one. Odylith does not turn a weak model into a strong model by itself; it
  changes the execution frame around that model.
- That is why Odylith can still add value as a bolt-on:
  - it can narrow the repo to the right slice faster
  - it can inject the right intent, constraints, topology, and ownership
  - it can keep the agent from wandering into irrelevant surfaces
  - it can choose better validation loops
  - it can recover from bad first guesses more reliably
  - it can preserve repo truth across turns instead of forcing re-discovery
- The architectural claim is therefore control-plane leverage, not
  weight-level superiority. Odylith should beat a raw coding agent the way a
  stronger query planner beats a raw storage engine or a strong IDE beats a
  bare editor: by reducing entropy and increasing execution discipline.
- That product claim only counts when the benchmark also clears the same-repo
  and same-truth fairness bar documented in the
  [Benchmark](../benchmark/CURRENT_SPEC.md) component dossier.

## Public CLI Contract
### Install and runtime lifecycle
- `odylith start`
- `odylith install`
- `odylith reinstall`
- `odylith upgrade`
- `odylith rollback --previous`
- `odylith version`
- `odylith doctor`
- `odylith uninstall`
- `odylith on`
- `odylith off`

### Governance and surface materialization
- `odylith sync`
- `odylith dashboard refresh`
- `odylith release ...`
- `odylith governance ...`
- `odylith validate ...`
- `odylith validate self-host-posture ...`
- `odylith atlas ...`

### Grounding and evaluation runtime
- `odylith context-engine ...`
- `odylith benchmark`
- `odylith compass ...`

### Delegation control plane
- `odylith subagent-router ...`
- `odylith subagent-orchestrator ...`

Public docs should describe these commands, not direct module entrypoints.
- When a top-level command forwards into a backend parser, the top-level
  `--help` surface must expose the backend flags rather than a shim-only
  placeholder. `odylith bug capture --help` and `odylith compass log --help`
  are canonical examples of that forwarded-help contract.
- Forwarded help must preserve the public command identity and copy, not just
  the backend flags. `odylith atlas render --help` must not degrade to
  `cli.py`, `__main__.py`, or wrapper-internal descriptions when the command
  routes through a lightweight proxy module.

## Coding-Agent Host Contract
- The default Odylith host contract is shared across Codex and Claude Code:
  repo-root `AGENTS.md`, the repo-local launcher `./.odylith/bin/odylith`,
  truthful `odylith ... --help`, and the grounded governance workflow should
  mean the same thing on both hosts.
- The baseline-safe Codex lane is the repo-root `AGENTS.md` contract plus the
  repo-local launcher `./.odylith/bin/odylith`.
- The checked-in `.codex/` project assets and repo-root `.agents/skills/`
  shims are enhancements for hosts that honor them; they must not become the
  only way routine governance work stays safe or discoverable.
- Codex-specific shortcuts are only justified when a local capability probe or
  native host feature materially reduces hops compared with the shared CLI
  lane. The canonical proof surface for those optional optimizations is
  `odylith codex compatibility`.
- Repo-root `.agents/skills/` must stay a curated command-shim surface for the
  high-frequency Odylith CLI lane: `start`, `context`, `query`,
  `session-brief`, `sync`, `version`, `doctor`, `compass log`, and
  `compass refresh`.
- Specialist governance, packet, registry, diagram, and orchestration
  workflows remain under `odylith/skills/` rather than being mirrored into the
  default Codex discovery path.
- Common consumer-lane governance authoring should stay one direct CLI hop:
  `odylith bug capture --help`, `odylith backlog create --help`,
  `odylith component register --help`, `odylith atlas scaffold --help`, and
  `odylith compass log --help` must expose backend help instead of shim-only
  parser surfaces.
- Consumer-facing narration must keep `.agents/skills` lookup, missing-shim,
  and fallback-source-path details implicit unless they change the next
  user-visible action.

## Repository And State Layout
### Tracked product truth
- `odylith/`
  Product-owned docs, source catalogs, checked-in generated surfaces, runtime
  contracts, and governance records.
- `odylith/agents-guidelines/indexable-guidance-chunks.v1.json`
  Canonical product guidance manifest used by benchmark and runtime guidance
  memory, with a bundle mirror under
  `src/odylith/bundle/assets/odylith/agents-guidelines/`.
- `odylith/registry/source/component_registry.v1.json`
  Canonical product component inventory.
- `odylith/radar/source/`
  Product workstream backlog and ideas.
- `odylith/radar/source/releases/`
  Product repo-local release-planning truth for release catalog, alias
  ownership, and append-only workstream targeting history.
- `odylith/technical-plans/`
  Product implementation-plan record.
- `odylith/casebook/bugs/`
  Product bug history.
- `odylith/atlas/source/`
  Product diagram source tree.

### Mutable local runtime state
- `.odylith/install.json`
  Canonical local install state for active version, last-known-good version,
  installed versions, installed feature packs per version, and integration
  posture.
- `.odylith/install-ledger.v1.jsonl`
  Append-only local upgrade, rollback, detach, and integration event ledger.
- `.odylith/runtime/`
  Active runtime pointer, side-by-side installed product versions, Context
  Engine compiler outputs, local memory backend state, benchmark reports,
  watcher and daemon metadata, and other runtime data.
- `odylith/runtime/source/managed-runtime-trust/`
  Gitignored repo-root trust anchors for modern managed-runtime integrity.
- `.odylith/runtime/versions/<version>/runtime-feature-packs.v1.json`
  Per-runtime record of the installed managed context-engine pack overlay and
  its verification evidence.
- `.odylith/subagent_router/`
  Router tuning state.
- `.odylith/subagent_orchestrator/`
  Orchestrator tuning state and decision ledgers.

## Product Subsystems
- Shell and governance surfaces:
  [Dashboard](../dashboard/CURRENT_SPEC.md),
  [Radar](../radar/CURRENT_SPEC.md),
  [Atlas](../atlas/CURRENT_SPEC.md),
  [Compass](../compass/CURRENT_SPEC.md),
  [Registry](../registry/CURRENT_SPEC.md), and
  [Casebook](../casebook/CURRENT_SPEC.md).
- Governance engine runtime:
  [Security](../security/CURRENT_SPEC.md),
  [Odylith Context Engine](../odylith-context-engine/CURRENT_SPEC.md),
  [Odylith Projection Bundle](../odylith-projection-bundle/CURRENT_SPEC.md),
  [Odylith Projection Snapshot](../odylith-projection-snapshot/CURRENT_SPEC.md),
  [Odylith Memory Backend](../odylith-memory-backend/CURRENT_SPEC.md),
  [Odylith Remote Retrieval](../odylith-remote-retrieval/CURRENT_SPEC.md),
  [Odylith Memory Contracts](../odylith-memory-contracts/CURRENT_SPEC.md),
  [Benchmark](../benchmark/CURRENT_SPEC.md),
  [Odylith Chatter](../odylith-chatter/CURRENT_SPEC.md),
  [Subagent Router](../subagent-router/CURRENT_SPEC.md),
  [Subagent Orchestrator](../subagent-orchestrator/CURRENT_SPEC.md),
  [Tribunal](../tribunal/CURRENT_SPEC.md), and
  [Remediator](../remediator/CURRENT_SPEC.md).
- Install/runtime management:
  `src/odylith/install/` for versioned install, upgrade, rollback, doctor,
  on/off, and uninstall behavior.
- Canonical release management:
  [Release](../release/CURRENT_SPEC.md) plus `.github/workflows/release.yml`
  and the maintainer `bin/` lane for sticky version-session resolution,
  authoritative publication, dogfood activation, and consumer rehearsal.

## Self-Hosting Posture Contract
- Top-level environments are:
  - consumer lane
  - product-repo maintainer mode
- Product-repo maintainer mode has two explicit postures:
  - `pinned_release` for normal dogfood proof
  - detached `source-local` for explicit live-source development
- The public Odylith repo is a special `product_repo` role derived from repo
  shape, not from an extra tracked metadata file.
- The normal dogfood lane for that repo is `pinned_release`:
  active runtime equals the tracked pin, the live runtime pointer under
  `.odylith/runtime/current` resolves cleanly, and source version,
  `odylith.__version__`, and repo pin stay aligned.
- Detached `source-local` remains legal only as an explicit development
  override. It is intentionally loud and release-ineligible.
- A pinned local wrapper runtime is not enough for release eligibility.
  The product repo is release-eligible only when the active pinned runtime is a
  verified staged runtime, not just a version-aligned wrapper.
- `odylith version` and `odylith doctor` must report:
  `Repo role`, `Posture`, `Runtime source`, `Release eligible`,
  `Context engine mode`, and `Context engine pack`.
- When a pinned managed runtime is still runnable but trust evidence has
  drifted, `odylith version` and `odylith doctor` must describe the same
  trust-degraded wrapped-runtime posture instead of letting doctor fall back to
  a generic failure summary.
- `odylith validate self-host-posture --mode local-runtime` validates the live
  maintainer checkout posture against the active runtime pointer.
- `odylith validate self-host-posture --mode release --expected-tag vX.Y.Z`
  validates source-only release invariants so CI can gate release cutting
  without a local `.odylith/` runtime.

## Cross-Component Control Flow
### 1. Materialize and attach
1. `odylith install` bootstraps a minimal customer-owned `odylith/` tree and
   activates a full-stack local runtime under `.odylith/runtime/versions/`
   using a verified base runtime plus a verified managed context-engine pack.
   Fresh consumer install does not become live until that full stack passes
   activation smoke.
2. `odylith upgrade` stages a verified base runtime side-by-side, reuses or
   reinstalls the matching managed context-engine pack, health-checks the full
   result, and atomically switches `.odylith/runtime/current` without rewriting
   tracked customer truth.
   The only allowed consumer-tree refresh is `odylith/agents-guidelines/`.
   `odylith upgrade --source-repo ...` is an explicit detached development
   override and always activates `source-local` rather than a repo-pinned
   release.
   If the requested release already matches the active verified full-stack
   runtime, upgrade stays a no-op and repair owns any same-version restage.
3. `odylith rollback --previous` switches back to the prior verified local
   runtime version when an operational rollback is needed, then prunes retained
   runtimes and release caches down to the active version plus one rollback
   target.
4. `odylith on` enables Odylith for coding agents by restoring the managed root
   `AGENTS.md` pointer so Odylith becomes the default first path again, starting
   from `odylith start`.
5. `odylith off` disables Odylith for coding agents without destroying tracked
   product truth and falls back to the surrounding repo's default coding-agent
   behavior.

### 2. Compile and ground
1. `odylith sync` validates governance inputs and regenerates checked-in
   surfaces.
   Missing Tribunal cache must not force `odylith sync` onto an opportunistic
   provider-backed reasoning path; delivery-intelligence refresh stays
   deterministic and local by default.
2. `odylith context-engine` warms projections, session packets, and local
   memory.
3. Surfaces and coding-agent workflows read deterministic packets from the
   Context Engine rather than reparsing the repo every time.

### Governed sync derivation contract
- `odylith sync` is not allowed to behave like a bag of unrelated helpers that
  all rediscover repo root, consumer profile, path canon, backlog specs,
  Registry report state, and delivery inputs independently.
- The correct execution shape is one sync-scoped derivation engine:
  - one canonical repo root
  - one consumer profile and truth-root resolution
  - one canonical path-token space
  - one shared parsed backlog/spec read model
  - one shared Registry and delivery-intelligence evidence substrate
  - one shared live governance context for release, workstream, and
    execution-wave truth consumed by Compass and other runtime-backed surfaces
- That shared derivation engine now owns one explicit derivation-generation
  contract:
  - projection/compiler/backend reuse is only legal when the runtime can prove
    the active derivation generation still matches the substrate generation for
    the current sync phase
  - derivation generation advances on derivation-input mutations such as Atlas
    catalog truth, Registry truth, traceability truth, and
    delivery-intelligence truth, not on arbitrary generated HTML/JS churn
- Shared projection substrates are immutable and content-addressed. The minimum
  provenance tuple is:
  - `repo_root`
  - `projection_scope`
  - `projection_fingerprint`
  - `sync_generation`
  - `code_version`
  - output-affecting `flags`
- Reuse must stay truthful:
  - cache keys derive from content truth, generator code, and execution flags
  - stat metadata may accelerate lookup, but it must not be the sole authority
  - standalone and check-only posture must stay fail-closed and source-truth
    equivalent
  - if provenance, generation, or required-table expectations do not match,
    the caller must rebuild locally instead of guessing
- Shared reuse stops at the low-level substrate. Compass, Radar, Registry, and
  other governed surfaces may share compiler/back-end substrates, but each
  surface still owns its final payload shaping and final output bytes.
- Generated outputs are content-addressed products of source truth. If a render
  step produces byte-identical output for byte-identical inputs, Odylith should
  not rewrite the file, should not dirty git, and should not invalidate
  downstream derived work.
- Heavy governed surfaces must also fingerprint their watched input cone and
  emitted bundle set before payload construction so no-op Radar, Registry,
  Casebook, and tooling-shell rerenders can exit before rebuilding the same
  HTML/JS payloads.
- When `odylith sync` has already selected a generated-surface render step,
  that sync plan becomes the rebuild authority for the step. Radar, Registry,
  Casebook, and tooling-shell renderers must therefore be able to bypass their
  own expensive refresh-guard tree scan in that lane instead of paying for a
  second rebuild decision before doing the real render work.
- Runtime-backed render steps must run against settled truth. Atlas review and
  catalog mutations, Registry spec reconciliation, and delivery-intelligence
  refresh must settle before Compass, Radar, Registry, and shell consume the
  projection/runtime lane, so one final warm can serve that whole render phase.
- Selective sync also has a truth-only lane: when the explicit changed-path
  slice is limited to Casebook bug markdown, active-plan files, and Registry
  living-spec docs, `odylith sync` should validate and mirror that governed
  memory slice without widening into Atlas, delivery-intelligence, or
  dashboard renders. When those explicit changed paths already determine the
  owned surfaces, the entrypoint must skip broad planner and git-rescan work
  and keep only the targeted Radar/backlog validation still required by the
  touched slice.
- Forced/full sync must not pay the governance-packet reasoning lane just to
  rediscover an all-surfaces impact set, and a direct sync projection warm must
  prime the same-process runtime warm cache so later surface readers do not
  rebuild the default projection again.
- Within one sync phase, runtime-backed readers must reuse one already-warm
  verdict per scope and one delivery-surface payload per argument set instead
  of recomputing the same projection fingerprint chain on every load. Sync
  must invalidate those session-scoped caches exactly when repo-owned truth or
  delivery-intelligence artifacts change the active derivation phase.
- Compass live governance context reuse must be keyed by the active sync
  generation plus the settled traceability signature. If either changes, the
  runtime must treat the previous release/workstream/wave snapshot as stale and
  rebuild it locally instead of reusing a warm result.
- Compass backlog-row reuse must also be keyed by the active sync generation
  plus runtime mode. If either changes, or if the active sync session is
  absent, Compass must rebuild the backlog rows locally instead of trusting a
  stale warm payload.
- Repo-scoped invalidation must also clear projected-input fingerprint caches,
  not only warm verdicts, because generated derivation inputs such as the
  traceability graph and delivery-intelligence artifact do not necessarily move
  the workspace-activity token that guards projection fingerprint reuse.
- Compass, Radar, and Registry payloads must carry additive runtime provenance
  that explains:
  - `projection_fingerprint`
  - `projection_scope`
  - `generation`
  - `cache_hit`
  - `built_from`
  - `invalidated_by_step`
- Projection-input tree signatures should be memoized per repo-state across
  compatible scopes so default/reasoning/full compatibility checks do not keep
  rescanning the same watched directories during one sync phase.
- Projection invalidation must follow derivation inputs, not output noise:
  generated HTML or JS writes are not allowed to clear warmed runtime state
  unless they changed a projection input such as traceability truth,
  delivery-intelligence truth, or other projection-owned source records.
- Sync-side invalidation and any follow-up rerun lane must check the watched
  derivation outputs before clearing warm state. Byte-identical traceability or
  delivery outputs are not allowed to trigger a second compatible warm or a
  second rerender just because the step executed.
- Runtime projection readers for backlog rows, plan rows, bug rows, component
  index, and Registry snapshots must reuse one signature-scoped row payload
  within a stable projection fingerprint instead of reopening and reshaping the
  same tables for later Compass, Radar, and Registry surfaces in the same run.
- In-process heartbeat output is an operator hint, not a fixed per-step tax.
  Sync must delay heartbeat emission until a step crosses a real slow-step
  threshold, and fast steps must complete without paying a steady polling lane
  or emitting misleading heartbeat chatter.
- Projection/compiler/backend writes remain single-writer and atomic. Lock
  batching is allowed, but the product must not weaken advisory-lock plus
  atomic-replace semantics in order to chase latency.
- Sync and runtime reuse must leave an operator-readable cache-explain trail
  under `.odylith/cache/odylith-context-engine/` so invalidation events,
  generation shifts, and surface reuse/rebuild decisions can be inspected after
  the fact.
- Component-artifact matching on the sync hot path must use indexed canonical
  prefixes rather than repeated O(events x components x prefixes) normalization
  scans, and follow-on Registry requirement sync passes must account for later
  shell-facing steps that can still shift evidence consumed by component
  forensics instead of running by superstition or skipping by false economy.
- Source-bundle mirror artifacts under
  `src/odylith/bundle/assets/odylith/...` must inherit canonical
  generated/global policy when they are only echoing derived or coordination
  truth, but mirror-only source docs must still map back to the owning
  component. Registry workspace-activity collection must therefore dedupe
  mirror/canonical aliases into one stable evidence token instead of treating
  the final mirror step as fresh work every run.
- The long-term ceiling is a reverse-dependency fixpoint engine or resident
  daemon, but the first non-negotiable contract is simpler: one sync run must
  reuse one shared read model instead of repeatedly reconstructing it.
- Atlas auto-update is part of that fail-closed contract: `--all-stale`
  review-only selections must not short-circuit on cached guard hits while the
  catalog still reports stale diagrams, or sync and standalone proof will
  diverge on the same source truth.

### 3. Decide execution posture
1. `odylith subagent-router` decides whether one bounded task stays local or is
   delegated, and with what model/reasoning profile.
2. `odylith subagent-orchestrator` decides whether a prompt should stay local,
   become one routed leaf, or decompose into a serial or parallel plan.

### 4. Diagnose and remediate
1. Delivery posture and scope evidence flow into Tribunal.
2. Tribunal emits ranked cases, explanations, confidence, and one correction
   packet per case.
   If provider enrichment times out or loses transport in that run, Tribunal
   must keep the rest of the queue deterministic instead of multiplying the
   provider stall across every case.
3. Remediator compiles deterministic, hybrid, AI-engine, or manual packets.
4. Higher-level product flows decide whether to present, approve, or execute
   those packets.

## Product-Wide Invariants
- Tracked markdown, JSON, and checked-in generated artifacts remain
  authoritative.
- Normal upgrades must not rewrite tracked customer truth under `odylith/`.
- Existing-customer upgrades must fail closed instead of silently recreating
  missing starter-tree files outside `odylith/agents-guidelines/`.
- On supported consumer platforms, Odylith owns and activates its own managed
  runtime on macOS (Apple Silicon) and Linux. It must not depend on or
  silently adopt the consumer repo's active Python toolchain.
- Supported install and normal pinned upgrade remain full-stack by default even
  though release transport is split into a base runtime plus a managed
  context-engine pack.
- Verified cached assets for the requested release should be reused when
  possible so retries and repeated upgrade attempts do not redownload the same
  heavy payloads unnecessarily.
- Incremental upgrades should reuse an unchanged managed context-engine pack
  whenever the target verified manifest still matches the previously installed
  asset name and digest.
- Same-version upgrade must not restage the already live runtime in place.
  Safe same-version restage belongs to `odylith doctor --repo-root . --repair`.
- After successful install, upgrade, or rollback, Odylith retains only the
  active runtime, one rollback target, and the matching cached release
  payloads.
- There is no shell-level interpreter switching between Odylith and the
  consumer repo. The invoked executable determines the runtime boundary.
- The runtime boundary does not define file-edit authority. Odylith running on
  its own managed runtime may still edit any in-scope repo files.
- The validation boundary stays separate: consumer repo code must be proved on
  the consumer repo's own toolchain, while Odylith CLI commands prove
  Odylith-owned governance, runtime, and surface contracts.
- `./.odylith/bin/odylith` and runtime bundle wrappers must scrub ambient
  `VIRTUAL_ENV`, `CONDA_*`, `PYTHONHOME`, `PYTHONPATH`,
  `PYTHONEXECUTABLE`, `PYENV_VERSION`, `UV_*`, Poetry/Pipenv/PDM selectors,
  and user-site leakage before starting the Odylith runtime.
- Detached `source-local` activation is allowed only as an explicit
  development override; it is not a canonical repo pin and must be reported as
  detached by status and doctor flows.
- In the product repo's maintainer lane, the Git `main` branch is read-only
  for authoring. This rule is non-negotiable.
- Tracked code, docs, and generated surfaces must never be edited directly on
  `main`; if the current branch is `main`, create and switch to a fresh branch
  before the first edit, stage, or commit, and if work is already on a
  non-`main` branch, keep using that branch.
- In the product repo's maintainer lane, the repo-root source-file size policy
  is also non-negotiable: `800` LOC is the soft limit, `1200` LOC requires an
  explicit exception and decomposition plan, `2000+` LOC is red-zone
  exception only, tests cap at `1500`, and mirrored or generated bundle
  assets are governed at their source-of-truth files instead.
- In the product repo, only detached `source-local` is allowed to execute
  live unreleased `src/odylith/*` changes. Pinned dogfood remains the proof
  posture for the shipped runtime.
- Consumer repos must fail closed rather than activating `source-local`.
- `odylith version` and `odylith doctor` must report context-engine mode and
  managed context-engine pack state in addition to repo role, posture, runtime
  source, and release eligibility.
- Active runtime pointers and launcher fallbacks must stay inside
  `.odylith/runtime/versions/`; Odylith must not follow drifted runtime
  pointers into arbitrary host paths.
- The live runtime pointer wins over stale install state when determining
  active runtime posture.
- The public product repo is release-eligible only when source version,
  package version, tracked pin, active posture, and active runtime provenance
  all align on the pinned lane.
- Product-managed assets must not be copied from the public Odylith repo into a
  consumer repo's `odylith/` tree.
- `THIRD_PARTY_ATTRIBUTION.md` must stay aligned with the runtime dependency
  closure and bundled managed-runtime suppliers, and the maintainer lane must
  fail closed on unknown, commercial/proprietary, or otherwise disallowed
  licenses.
- Deterministic local logic is the product baseline; optional provider
  enrichment or delegated execution must degrade safely.
- Generated surfaces are derived outputs. Developers should change renderer or
  source inputs, then regenerate.
- Public contract text must stay generic and product-owned. Consumer-specific
  naming does not belong in Odylith public docs.

## Install, Repair, And Detach Semantics
- `odylith doctor --repair` is non-destructive.
- `odylith doctor --repair --reset-local-state` is the destructive local-state
  recovery path for poisoned caches, locks, compiler artifacts, and other
  mutable runtime state under `.odylith/`.
- In consumer repos, `odylith doctor --repair` must restage the pinned managed
  runtime and the pinned managed context-engine pack when the full-stack
  runtime is incomplete.
- `odylith uninstall` detaches the managed root `AGENTS.md` block and marks the
  local install detached, but it preserves both customer-owned `odylith/`
  truth and local `.odylith/` state.
- `odylith on` and `odylith off` are intentional operator states and should be
  treated as valid posture, not as broken installs. `off` means repo-root
  Odylith-first guidance is detached while the runtime and context remain
  installed; `on` means that guidance is restored.

## Failure And Recovery Model
- If tracked truth and generated surfaces drift, rerun `odylith sync`.
- If grounding state is stale or poisoned, rebuild `.odylith/runtime/` via
  Context Engine warmup or doctor/repair.
- If install state or local runtime is compromised, use the doctor repair path.
- If agent integration is intentionally disabled, use `odylith on` to reattach
  instead of reinstalling the product.

## Developer Change Rules
- Extend the public CLI only through `src/odylith/cli.py` and the install/runtime
  modules it dispatches to.
- Keep `odylith/` docs and `src/odylith/bundle/assets/odylith/` docs aligned.
- Do not place rebuildable caches or host-specific state under `odylith/`.
- Do not reintroduce product-bundle copying into consumer `odylith/` trees.
- When a change affects checked-in rendered surfaces, regenerate the outputs
  instead of patching the generated file as source.
- When a change alters a runtime or surface contract, update the corresponding
  Registry dossier under `odylith/registry/source/components/`.

## Practical Extension Checklist
- New operator command:
  add parser wiring in `src/odylith/cli.py`, implement the command in the
  owning module, document it here and in the owning component spec, and update
  bundled docs.
- New mutable runtime artifact:
  store it under `.odylith/`, make it rebuildable, and document the recovery
  path.
- New tracked generated artifact:
  document the renderer/source ownership and regenerate it from source.
- New governance-engine component:
  register it in the component registry, add a Registry-owned dossier, and
  link it from [PRODUCT_COMPONENTS.md](PRODUCT_COMPONENTS.md).

## Validation Playbook
### Product
- `odylith doctor --repo-root .`
- `odylith sync --repo-root . --check-only`
- `odylith validate component-registry --repo-root .`
- `pytest -q tests/unit tests/integration`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- **2026-04-11 · Implementation:** B-090 is closed.
  - Scope: B-090
- **2026-04-11 · Implementation:** B-089 has landed on 2026/freedom/v0.1.11 as the planned two-commit pair, working tree clean: 9402f5d — Mirror Codex host parity into Claude with baked CLI dispatchers (56 files:...
  - Scope: B-089
- **2026-04-05 · Implementation:** Refreshed the benchmark publication story to the April 5 source-local full proof pass 52aa3f76538cf12f: README, benchmark docs, registry spec, plans, and radar now reflect that odylith_on clears the hard gate and secondary guardrails against odylith_off while benchmark_compare still warns until the first shipped release baseline exists.
  - Scope: B-021, B-022
  - Evidence: README.md, docs/benchmarks/README.md +3 more
- **2026-03-23 · Decision:** Successor created: B-280 reopens B-279 for active plan binding
  - Evidence: odylith/radar/source/INDEX.md, odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md +1 more
- **2026-03-23 · Decision:** Successor created: B-279 reopens B-278 for active plan binding
  - Evidence: odylith/radar/source/INDEX.md, odylith/registry/source/components/dashboard/CURRENT_SPEC.md +3 more
- **2026-03-23 · Decision:** Successor created: B-276 reopens B-275 for active plan binding
  - Evidence: odylith/radar/source/INDEX.md, odylith/registry/source/components/subagent-orchestrator/CURRENT_SPEC.md +2 more
<!-- registry-requirements:end -->

## Feature History
- 2026-03-26: Bootstrapped Odylith's public self-governance registry, component specs, and product-owned governance roots so the product can govern itself without relying on any other repo as the source of record. (Plan: [B-001](odylith/radar/radar.html?view=plan&workstream=B-001))
- 2026-03-27: Added explicit product-repo self-host posture modeling, source-only release validation, and governed-surface readouts for pinned vs detached dogfood posture. (Plan: [B-004](odylith/radar/radar.html?view=plan&workstream=B-004))
- 2026-03-27: Added a governed canonical release subsystem with sticky semver sessions, commit-bound dispatch, and maintainer release/runbook artifacts for the first hosted publication lane. (Plan: [B-005](odylith/radar/radar.html?view=plan&workstream=B-005))
- 2026-03-28: Promoted the supported hosted install/upgrade contract to GA on macOS Apple Silicon and Linux after the first published release completed dogfood, consumer rehearsal, and GA gate proof. (Plan: [B-007](odylith/radar/radar.html?view=plan&workstream=B-007))
- 2026-03-28: Added durable judgment memory and promoted Odylith Memory Backend into a first-class governed subsystem so local retrieval, onboarding continuity, contradictions, and proof outcomes can persist without becoming source truth. (Plan: [B-010](odylith/radar/radar.html?view=plan&workstream=B-010))
- 2026-03-31: Added Odylith Chatter as a first-class governed subsystem so mid-task narration stays task-first and any Odylith-by-name closeout stays final-only, user-win-first, soulful, friendly, authentic, factual, and evidence-backed against `odylith_off` or the broader unguided path. (Plan: [B-031](odylith/radar/radar.html?view=plan&workstream=B-031))
- 2026-04-02: Clarified the core product claim as control-plane leverage around the same base coding model, explicitly tying Odylith's value to improved context quality, search, validation, and recovery rather than any claim of beating model weights. (Plan: [B-033](odylith/radar/radar.html?view=plan&workstream=B-033))
- 2026-04-05: Promoted the canonical benchmark guidance manifest into tracked product truth so benchmark and runtime guidance memory resolve from one family-tagged source instead of an implicit zero-guidance fallback. (Plan: [B-021](odylith/radar/radar.html?view=plan&workstream=B-021))
- 2026-04-07: Split the hidden memory substrate into explicit governed subcomponents for projection bundle, projection snapshot, remote retrieval, and packet contracts so Registry can show the real memory topology instead of one coarse silhouette. (Plan: [B-058](odylith/radar/radar.html?view=plan&workstream=B-058))
- 2026-04-08: Added `odylith release ...` and the repo-local release-planning contract so workstreams can target explicit ship lanes without smuggling release scope into prose, execution waves, or publication-only lore. (Plan: [B-063](odylith/radar/radar.html?view=plan&workstream=B-063))
- 2026-04-12: Bound governed sync to a shared-read-model and content-addressed-write architecture so the product can cut warm sync latency by reusing one truthful derivation context instead of repeatedly rediscovering the same repo state. (Plan: [B-091](odylith/radar/radar.html?view=plan&workstream=B-091))
- 2026-04-12: Tightened the governed sync fast path again so Compass reads backlog rows from the already-settled Radar source truth during sync and only the genuinely slow in-process render steps keep heartbeat wrapping; the same-day source-local proof came back at `5.9s` sync-reported / `6.96s` wall with `load_backlog_rows()` reduced to `0.034s` and `select.poll` reduced to `1.066s`. (Plan: [B-091](odylith/radar/radar.html?view=plan&workstream=B-091))
- 2026-04-14: Added truthful forwarded-help exposure for backend-owned CLI subcommands and a selective truth-only governed-memory sync lane so routine bug/plan/spec upkeep no longer requires source spelunking or a render-heavy sync wave. (Plan: [B-091](odylith/radar/radar.html?view=plan&workstream=B-091))
- 2026-04-14: Extended the quick-update contract so routine authoring commands rerender only their owned surface by default (`backlog create` -> Radar, `component register` -> Registry, `atlas scaffold` -> Atlas, `compass log` -> Compass), while selective direct Radar/Registry/Atlas/Casebook truth edits refresh the same surface-local lane and keep the shared projection compiler plus local LanceDB/Tantivy substrate fresh. (Plan: [B-091](odylith/radar/radar.html?view=plan&workstream=B-091))
- 2026-04-14: Propagated that owned-surface quick-refresh contract across repo-root guidance, consumer guidance, bundled docs, Codex shims, and Claude helper commands so dev, dogfood, and consumer lanes all teach the same single-surface refresh commands instead of a stale `dashboard refresh --surfaces <surface>` hop. (Plan: [B-091](odylith/radar/radar.html?view=plan&workstream=B-091))
- 2026-04-14: Tightened that quick-update lane again so explicit truth-only selective sync slices skip the runtime governance-packet planner and broad backlog preflight when the changed paths already determine the owned surfaces, source-truth bundle mirroring stays scoped to the explicit files instead of rescanning git, and single-surface Radar/Registry/Casebook refreshes stay on the in-process runtime fast path when the local LanceDB/Tantivy backend is ready. The same-day source-local proof came back at `radar refresh: 1.78s` wall, `registry refresh: 5.03s` wall, `casebook refresh: 1.67s` warm wall, `atlas refresh --atlas-sync: 0.35s` wall, and a four-surface selective sync at `6.9s` sync-reported / `7.33s` wall while the memory backend still reported `ready: true`. (Plan: [B-091](odylith/radar/radar.html?view=plan&workstream=B-091))
- 2026-04-14: Added a low-RAM-aware command-scoped `RuntimeReadSession`, one shared byte-budgeted process cache for hot runtime facts, an incremental `odylith show` import-graph manifest under `.odylith/runtime/latency-cache/`, fingerprint-gated no-op dashboard refresh reuse, and a shared Claude/Codex SessionStart stale-brief queue so repeated reads and refreshes stop widening into redundant work while the same LanceDB/Tantivy and surface-freshness invariants stay intact. (Plan: [B-091](odylith/radar/radar.html?view=plan&workstream=B-091))
- 2026-04-18: Hardened the governed sync executor after B-110 QA exposed a structured-refresh return bug: callable sync steps now coerce pass/fail/queued dictionaries into explicit exit status, preserve queued refreshes as non-failures, and fail closed on malformed counters or failed structured payloads. (Plan: [B-110](odylith/radar/radar.html?view=plan&workstream=B-110))
- 2026-04-14: Hardened the Codex post-bash governed-refresh lane so command-scoped selective sync stays exact under dirty worktrees, rename/move operations, shell control and redirection tails, and explicit inline `python -c` / `node -e` file-write one-liners, while Claude preserved the direct exact-path `PostToolUse` lane as the parity reference. (Plan: [B-091](odylith/radar/radar.html?view=plan&workstream=B-091))
- 2026-04-14: Re-profiled the old worst-row CLI lanes on the live source-local runtime and confirmed the earlier screenshot-class latency is stale: `dashboard refresh` now measures `7.75s` cold / `0.98s` warm, `context-engine warmup` `5.00s` cold / `1.47s` warm, `show` `1.03s` cold / `0.53s` warm, `governance-slice` `0.89s`, `query` `1.45s` cold / `1.37s` warm, `context-engine query` `1.40s` cold / `1.32s` warm, and `claude session-start` `1.96s` cold / `2.14s` warm. `impact` remains the main cold-path outlier at `5.65s` cold / `1.90s` warm. (Plan: [B-091](odylith/radar/radar.html?view=plan&workstream=B-091))
- 2026-04-14: Narrowed the repo-root Codex skill surface to explicit command shims for the high-frequency CLI lane so routine governance upkeep defaults back to `AGENTS.md`, the launcher, and truthful help instead of a mirrored specialist skill stack. (Plan: [B-088](odylith/radar/radar.html?view=plan&workstream=B-088))
- 2026-04-14: Extended the consumer-lane fast path so common governed authoring commands (`bug capture`, `backlog create`, `component register`, `atlas scaffold`, `compass log`) forward backend help and the installed guidance keeps shim and fallback plumbing out of normal user-facing narration. (Plan: [B-088](odylith/radar/radar.html?view=plan&workstream=B-088))
- 2026-04-14: Tightened the forwarded-help contract so Atlas public help surfaces keep the real `odylith atlas ...` command name and user-facing descriptions instead of leaking `cli.py`, `__main__.py`, or refresh-wrapper copy. (Plan: [B-088](odylith/radar/radar.html?view=plan&workstream=B-088))
- 2026-04-14: Reframed the host guidance so the default lane stays shared across Codex and Claude Code, while Codex-only advice is limited to capability-gated project-asset optimizations such as `odylith codex compatibility`. (Plan: [B-088](odylith/radar/radar.html?view=plan&workstream=B-088))
