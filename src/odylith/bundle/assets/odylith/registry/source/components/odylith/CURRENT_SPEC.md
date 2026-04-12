# Odylith
Last updated: 2026-04-11


Last updated (UTC): 2026-04-08

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
- **2026-03-20 · Decision:** Successor created: B-266 reopens B-265 for active plan binding
  - Evidence: odylith/radar/source/INDEX.md, odylith/registry/source/components/casebook/CURRENT_SPEC.md +1 more
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
