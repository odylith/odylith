Status: In progress

Created: 2026-03-30

Updated: 2026-04-02

Backlog: B-027

Goal: Make Odylith's lane model explicit and durable by separating runtime,
write, and validation boundaries across maintainer and consumer guidance,
component specs, bundle assets, backlog truth, and Atlas, while keeping
consumer Odylith-fix requests in diagnosis-and-handoff mode, preserving cheap
refresh behavior, and making Atlas search discoverability match operator
expectations for short diagram-id tokens.

Assumptions:
- The runtime behavior is already mostly correct; the main gap is contract
  clarity and consistency.
- The product repo needs one explicit distinction between pinned dogfood proof
  and detached `source-local` live-source execution.
- Consumer repos need one explicit distinction between Odylith-managed runtime
  execution and consumer-toolchain validation.
- Dashboard refresh should stay deterministic and cheap even when Tribunal
  provider state is unavailable or unhealthy.

Constraints:
- Do not imply that consumer repos support `source-local`.
- Do not imply that pinned dogfood should execute live `src/odylith/*`
  changes.
- Keep maintainer-only overlays out of bundled consumer assets.

Reversibility: Reverting this slice restores the previous wording and diagram
contracts without changing underlying runtime mechanics.

Boundary Conditions:
- Scope includes constitutional docs, AGENTS guidance, key shared and
  maintainer skills, bundle mirrors, component specs, backlog records, Atlas
  diagrams, and the delivery-intelligence / Tribunal refresh contract that
  keeps shell refresh local and deterministic.
- Scope excludes implementation changes to the launcher or runtime-selection
  code.

Related Bugs:
- CB-025: product repo tooling shell hides runtime version badge after header freeze

## Context/Problem Statement
- [ ] Runtime boundary, write boundary, and validation boundary are not yet
      described as separate concepts.
- [ ] Pinned dogfood versus detached `source-local` is still too easy to blur
      in product-repo guidance.
- [ ] Consumer guidance does not yet say crisply enough that Odylith-managed
      runtime does not take over target-repo validation.
- [ ] Consumer installs do not yet carry an explicit write-authority contract
      that keeps Odylith product fixes in diagnosis-and-handoff mode.
- [ ] Bundle/install-facing copies need to stay aligned with the source-owned
      guidance.
- [ ] The subagent reasoning ladder and prompt-level orchestration contract
      still read as maintainer-shaped in some runtime, install, and Atlas
      surfaces even though the supported Codex lanes are broader.
- [ ] Atlas search does not yet treat short diagram-id suffixes as first-class
      search inputs.

## Success Criteria
- [ ] Constitutional docs expose one explicit lane matrix across consumer,
      maintainer mode, pinned dogfood posture, and detached `source-local`
      posture.
- [ ] Shared guidance and key skills say clearly that interpreter choice does
      not control file-edit authority.
- [ ] Maintainer guidance says clearly that pinned dogfood is proof posture and
      detached `source-local` is live-source execution posture.
- [ ] Maintainer guidance says explicitly that the Git `main` branch is
      read-only for authoring and that tracked changes must start from a
      non-`main` branch.
- [x] Maintainer guidance says explicitly that the dashboard shell header is a
      frozen contract across pinned dogfood and detached `source-local`
      maintainer-dev posture, including one compact product-repo runtime badge.
- [ ] Bundle assets and install-managed AGENTS text carry the same contract for
      new installs.
- [ ] Consumer installs persist a machine-readable write policy that protects
      `odylith/` and `.odylith/` by default.
- [ ] Atlas diagrams and catalog metadata reflect the same lane model.
- [ ] Atlas search matches short diagram-id tokens such as `45`, `045`, and
      `-045` without requiring the full canonical id.
- [ ] Subagent Router and Subagent Orchestrator contract surfaces say the
      reasoning ladder and prompt-level orchestration apply across consumer,
      pinned dogfood, and detached `source-local` maintainer-dev lanes.
- [ ] Delivery-intelligence refresh no longer waits on opportunistic
      provider-backed reasoning when the persisted Tribunal artifact is absent.
- [ ] Explicit Tribunal runs degrade coherently after a provider timeout or
      transport failure instead of multiplying the same stall across cases.

## Non-Goals
- [ ] Runtime-selection code changes.
- [ ] New CLI subcommands for graph rendering or source-lane activation.
- [ ] Consumer support for detached local source execution.

## Impacted Areas
- [ ] [AGENTS.md](/Users/freedom/code/odylith/AGENTS.md)
- [ ] [odylith/AGENTS.md](/Users/freedom/code/odylith/odylith/AGENTS.md)
- [ ] [odylith/OPERATING_MODEL.md](/Users/freedom/code/odylith/odylith/OPERATING_MODEL.md)
- [ ] [odylith/README.md](/Users/freedom/code/odylith/odylith/README.md)
- [ ] [odylith/INSTALL_AND_UPGRADE_RUNBOOK.md](/Users/freedom/code/odylith/odylith/INSTALL_AND_UPGRADE_RUNBOOK.md)
- [x] [odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md](/Users/freedom/code/odylith/odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md)
- [ ] [odylith/agents-guidelines/VALIDATION_AND_TESTING.md](/Users/freedom/code/odylith/odylith/agents-guidelines/VALIDATION_AND_TESTING.md)
- [ ] [odylith/agents-guidelines/UPGRADE_AND_RECOVERY.md](/Users/freedom/code/odylith/odylith/agents-guidelines/UPGRADE_AND_RECOVERY.md)
- [x] [odylith/maintainer/AGENTS.md](/Users/freedom/code/odylith/odylith/maintainer/AGENTS.md)
- [ ] [odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md](/Users/freedom/code/odylith/odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md)
- [ ] [odylith/registry/source/components/subagent-orchestrator/CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/subagent-orchestrator/CURRENT_SPEC.md)
- [ ] [odylith/registry/source/components/subagent-router/CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/subagent-router/CURRENT_SPEC.md)
- [ ] [odylith/registry/source/components/odylith/CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith/CURRENT_SPEC.md)
- [ ] [odylith/registry/source/components/release/CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/release/CURRENT_SPEC.md)
- [x] [odylith/registry/source/components/dashboard/CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/dashboard/CURRENT_SPEC.md)
- [x] [src/odylith/runtime/surfaces/tooling_dashboard_frontend_contract.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/tooling_dashboard_frontend_contract.py)
- [x] [src/odylith/runtime/surfaces/tooling_dashboard_template_context.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/tooling_dashboard_template_context.py)
- [x] [src/odylith/runtime/surfaces/templates/tooling_dashboard/page.html.j2](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/templates/tooling_dashboard/page.html.j2)
- [x] [src/odylith/runtime/surfaces/templates/tooling_dashboard/style.css](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/templates/tooling_dashboard/style.css)
- [ ] [odylith/registry/source/components/tribunal/CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/tribunal/CURRENT_SPEC.md)
- [ ] [odylith/atlas/source/odylith-product-runtime-boundary-map.mmd](/Users/freedom/code/odylith/odylith/atlas/source/odylith-product-runtime-boundary-map.mmd)
- [ ] [odylith/atlas/source/odylith-self-host-runtime-and-release-gate.mmd](/Users/freedom/code/odylith/odylith/atlas/source/odylith-self-host-runtime-and-release-gate.mmd)
- [ ] [odylith/atlas/source/odylith-subagent-orchestrator-prompt-triage-and-routing-flow.mmd](/Users/freedom/code/odylith/odylith/atlas/source/odylith-subagent-orchestrator-prompt-triage-and-routing-flow.mmd)
- [ ] [odylith/atlas/source/catalog/diagrams.v1.json](/Users/freedom/code/odylith/odylith/atlas/source/catalog/diagrams.v1.json)
- [ ] [odylith/atlas/source/odylith-delivery-intelligence-closed-loop.mmd](/Users/freedom/code/odylith/odylith/atlas/source/odylith-delivery-intelligence-closed-loop.mmd)
- [ ] [odylith/atlas/source/odylith-tribunal-selection-funnel-and-queue-formation.mmd](/Users/freedom/code/odylith/odylith/atlas/source/odylith-tribunal-selection-funnel-and-queue-formation.mmd)
- [ ] [src/odylith/runtime/common/consumer_profile.py](/Users/freedom/code/odylith/src/odylith/runtime/common/consumer_profile.py)
- [ ] [src/odylith/runtime/orchestration/subagent_orchestrator.py](/Users/freedom/code/odylith/src/odylith/runtime/orchestration/subagent_orchestrator.py)
- [ ] [src/odylith/install/agents.py](/Users/freedom/code/odylith/src/odylith/install/agents.py)
- [ ] [src/odylith/install/manager.py](/Users/freedom/code/odylith/src/odylith/install/manager.py)
- [ ] [src/odylith/runtime/surfaces/render_mermaid_catalog.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_mermaid_catalog.py)
- [ ] [src/odylith/runtime/governance/delivery_intelligence_engine.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/delivery_intelligence_engine.py)
- [ ] [src/odylith/runtime/evaluation/tribunal_engine.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/tribunal_engine.py)
- [ ] [src/odylith/runtime/evaluation/odylith_reasoning.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_reasoning.py)
- [x] [tests/unit/runtime/test_tooling_dashboard_frontend_contract.py](/Users/freedom/code/odylith/tests/unit/runtime/test_tooling_dashboard_frontend_contract.py)
- [x] bundled consumer mirrors under [src/odylith/bundle/assets/odylith](/Users/freedom/code/odylith/src/odylith/bundle/assets/odylith)

## Risks & Mitigations

- [ ] Risk: one source file and one bundled copy drift.
  - [ ] Mitigation: patch source-owned and bundled copies in the same change.
- [ ] Risk: the guidance still sounds like interpreter choice controls edit
    authority.
  - [ ] Mitigation: use one repeated three-boundary framing across docs and
    skills.
- [ ] Risk: maintainer overlay leaks into consumer bundle language.
  - [ ] Mitigation: keep consumer bundles explicit that maintainer-only release
    overlays remain product-repo-only.
- [ ] Risk: making sync faster by silently removing Tribunal coverage.
  - [ ] Mitigation: preserve deterministic Tribunal `case_queue` generation for
    delivery refresh and test it directly.
- [ ] Risk: provider timeout still multiplies across explicit Tribunal cases.
  - [ ] Mitigation: disable provider enrichment for the rest of the run after
    the first timeout or transport failure and record the degraded reason.

## Validation/Test Plan
- [x] `PYTHONPATH=src python -m pytest -q tests/unit/install/test_agents.py`
- [x] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_consumer_profile.py tests/unit/runtime/test_subagent_reasoning_ladder.py tests/unit/runtime/test_render_mermaid_catalog.py`
- [x] `PYTHONPATH=src python -m pytest -q tests/integration/install/test_manager.py::test_install_bundle_bootstraps_customer_owned_tree_without_copying_product_bundle tests/integration/install/test_manager.py::test_upgrade_install_resyncs_consumer_guidance_and_skills tests/integration/install/test_manager.py::test_install_bundle_product_repo_preserves_source_owned_odylith_guidance_and_activates_maintainer_overlay tests/integration/runtime/test_surface_browser_deep.py::test_atlas_navigation_filters_and_context_links`
- [x] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_delivery_intelligence_engine.py tests/unit/runtime/test_tribunal_engine.py tests/unit/runtime/test_odylith_reasoning.py`
- [x] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_tooling_dashboard_frontend_contract.py tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/runtime/test_brand_assets.py`
- [x] `make dev-validate`
- [x] `./.odylith/bin/odylith atlas render --repo-root . --fail-on-stale`
- [x] `git diff --check`

## Rollout/Communication
- [x] Land the backlog and plan records first so the wording change is tracked.
- [x] Keep the same lane matrix language in the product docs and the bundled
      consumer docs.
- [x] Rerender Atlas after the source diagrams change so the surface and source
      truth stay aligned.

## Current Outcome
- [x] Bound to `B-027`; the runtime/write/validation boundary framing now lands
      across root guidance, Odylith docs, maintainer overlays, bundled
      consumer assets, component specs, and Atlas.
- [x] Maintainer-lane branch safety now states explicitly across source,
      generated, and spec surfaces that the Git `main` branch is read-only for
      authoring and that tracked edits must start from a non-`main` branch,
      while bundled consumer guidance keeps that rule product-repo-only.
- [x] Compass global refresh no longer reuses stale last-known-good cache when
      provider narration is unavailable or empty, and explicit Tribunal runs
      degrade the rest of the run back to deterministic reasoning after the
      first provider failure.
- [x] The subagent reasoning ladder and prompt-level orchestration contract now
      read the same across consumer lane, pinned dogfood, and detached
      `source-local` maintainer-dev surfaces in runtime help, install-managed
      AGENTS text, Registry specs, and the Atlas orchestration diagram.
- [x] Maintainer guidance now says explicitly that the dashboard shell header
      is frozen across pinned dogfood and detached `source-local`
      maintainer-dev posture, and that the only stateful header badge there is
      the compact product-repo runtime/version chip derived from self-host
      posture.
- [x] Consumer guidance, install-managed AGENTS text, bundle assets, and
      routing policy now say the same thing: grounding Odylith is diagnosis
      authority, not blanket write authority, and consumer Odylith fixes stay
      diagnosis-and-handoff only unless the operator authorizes mutation.
- [x] Consumer installs now persist a machine-readable Odylith write policy so
      router and orchestrator flows can keep `odylith/` and `.odylith/`
      protected without adding background work or provider calls.
- [x] Atlas search now matches short diagram-id suffixes such as `45`, `045`,
      and `-045` instead of requiring the full canonical token.
- [x] Focused validation passed on 2026-04-02 for consumer-profile policy,
      router/orchestrator local-guard behavior, install-guidance bundle sync,
      Atlas renderer output, the checked-in generated Atlas app, and browser
      proof of short-token Atlas search.
- [x] The tooling shell now fails closed when the frozen source-owned header
      template or header CSS drifts, so accidental consumer-facing header
      mutations surface during render instead of shipping silently.
- [x] Focused validation on 2026-03-31 passed for install and orchestration
      contract coverage, and Atlas rerendered successfully without the stale
      freshness gate even though unrelated stale diagrams still block
      `--fail-on-stale`.
- [x] Validation passed on 2026-03-30 via focused unit tests, full
      `make dev-validate`, `odylith atlas render --fail-on-stale`, and
      `git diff --check`.
