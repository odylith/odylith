Status: In progress

Created: 2026-03-30

Updated: 2026-04-05

Backlog: B-033

Goal: Turn the concrete learnings from `v0.1.5` into a `v0.1.6` release plan
that hardens release machinery before more surface expansion, promotes
source-authored release explanation into the product, and executes a targeted
large-file refactor wave under explicit repo policy.

Assumptions:
- `v0.1.5` surfaced real release-system weaknesses, not just one-off operator
  mistakes.
- Existing in-progress workstreams such as `B-028`, `B-030`, and `B-021`
  should be reused where they already match this release scope.
- A repo-wide large-file rewrite in the same release window would add
  regression risk to central paths that were just changed.

Constraints:
- Release machinery hardening must happen before or alongside new feature
  surface that depends on release storytelling.
- Consumer guidance must stay free of maintainer-only release-process detail.
- Large-file refactor work must be prioritized by size x churn x centrality,
  not by a blind repo-wide threshold alone.
- Generated or mirrored bundle assets are excluded from file-size policy;
  govern their source-of-truth files instead.

Reversibility: The backlog and policy records are reversible if priorities
change. Implementation changes under this plan should remain additive or
behavior-preserving where possible, and refactor waves should land as bounded
extractions with characterization coverage first.

Boundary Conditions:
- Scope includes release-candidate proof, version-truth generation,
  maintainer-lane introspection, release-session validity, product-repo
  repair and dogfood idempotence, authored release notes, shell explanation,
  version-delta UX, empty-repo onboarding, benchmark compare and history
  visibility, and targeted large-file decomposition.
- Scope excludes a repo-wide all-files-above-X rewrite, broad hosted release
  operations redesign, and unrelated shell IA changes that do not materially
  improve `v0.1.6`.

Related Bugs:
- [2026-03-28-release-preflight-fails-when-dist-contains-stale-wheel.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-28-release-preflight-fails-when-dist-contains-stale-wheel.md)
- [2026-03-29-release-auto-tagging-burns-unpublished-patch-versions-and-skips-ga-candidates.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-29-release-auto-tagging-burns-unpublished-patch-versions-and-skips-ga-candidates.md)
- [2026-03-28-public-consumer-rollback-to-legacy-preview-runtime-fails.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-28-public-consumer-rollback-to-legacy-preview-runtime-fails.md)
- [2026-04-01-runtime-launcher-wrapper-recursion-and-trust-boundary-hardening.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-01-runtime-launcher-wrapper-recursion-and-trust-boundary-hardening.md)

## Learnings
- `v0.1.5` on 2026-03-30 taught us that product work was ahead of the release
  machinery.
- Release truth was too fragmented. We had to realign
  [pyproject.toml](/Users/freedom/code/odylith/pyproject.toml),
  [__init__.py](/Users/freedom/code/odylith/src/odylith/__init__.py), and
  [product-version.v1.json](/Users/freedom/code/odylith/odylith/runtime/source/product-version.v1.json)
  by hand.
- Governance drift was caught too late. Backlog contract failures blocked
  `release-preflight` instead of being burned down continuously from
  [odylith/radar/source](/Users/freedom/code/odylith/odylith/radar/source).
- The release lane was under-tested in the exact path that matters most:
  isolated canonical checkout. That is where
  [ga-gate](/Users/freedom/code/odylith/bin/ga-gate),
  [dogfood-activate](/Users/freedom/code/odylith/bin/dogfood-activate), and
  [runtime.py](/Users/freedom/code/odylith/src/odylith/install/runtime.py)
  broke.
- Consumer UX was the right bet, but it exposed missing product language:
  users still do not naturally understand Radar, Registry, Atlas, and Compass
  from the shell alone.
- Benchmarks need to become a hard release signal earlier. The prompt-token
  regression should have been caught before release crunch.

## Must-Ship
- [x] Add a pre-merge release-candidate lane that runs `release-preflight`,
      isolated-checkout `ga-gate`, benchmark compare against the last shipped
      release, and docs/version/source-of-truth consistency checks.
- [x] Make release truth single-sourced and generated outward rather than
      manually synchronized across three files.
- [x] Add explicit lane introspection such as `odylith lane status` or
      equivalent supported status output.
- [x] Make release sessions self-invalidating when `HEAD` changes.
- [x] Make maintainer repair and dogfood flows fully idempotent in
      product-repo mode so they never leave tracked guidance drift behind.
- [x] Add the repo-level large-file discipline to AGENTS guidance and use it to
      gate refactor planning for this release.
- [x] Run a dedicated refactor wave prioritized by size x churn x centrality,
      not size alone.

## Should-Ship
- [x] Promote plain-English release notes into a maintained source artifact
      that powers both the popup and a permanent release-notes page.
- [ ] Add one crisp first-use explainer sentence each for Radar, Registry,
      Atlas, and Compass.
- [ ] Add a persistent "What changed since my version?" view for consumer
      repos.
- [x] Improve empty-repo onboarding so Odylith helps shape a repo before there
      is much local code to inspect.
- [ ] Add benchmark history UI that shows better, worse, or unchanged versus
      the last release directly in maintainer workflow.

## Defer
- [ ] Do not run a repo-wide "all files above X" rewrite in `v0.1.6`.
- [ ] Do not use release polish as a reason to take on a big-bang dashboard IA
      redesign.
- [ ] Do not keep manual multi-file version synchronization as the fallback
      source-of-truth contract.

## Refactor Evidence Snapshot
- [ ] Current scan snapshot provided for this release plan:
  - 223 code or web files scanned
  - 47 files over `1000` lines
  - 28 files over `2000` lines
  - 11 files over `3000` lines
  - 6 files over `5000` lines
- [ ] `src/*.py` snapshot provided for this plan:
  - p50: `286`
  - p75: `1059`
  - p90: `2862`
  - max: `21538`
- [ ] Highest-priority offenders called out for the first decomposition wave:
  - [odylith_context_engine_store.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_store.py): `21538` lines, touched 4 times in 90 days
  - [render_backlog_ui.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_backlog_ui.py): `6308`
  - [subagent_router.py](/Users/freedom/code/odylith/src/odylith/runtime/orchestration/subagent_router.py): `6190`
  - [subagent_orchestrator.py](/Users/freedom/code/odylith/src/odylith/runtime/orchestration/subagent_orchestrator.py): `5908`
  - [compass_dashboard_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/compass_dashboard_runtime.py): `5808`, touched 4 times in 90 days
  - [tooling_dashboard_shell_presenter.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/tooling_dashboard_shell_presenter.py): `4197`, touched 4 times in 90 days

## Success Criteria
- [x] Release-candidate proof fails before release crunch when release truth,
      docs, benchmark signals, or canonical-checkout behavior drift.
- [x] One source of truth generates release-facing version state outward to the
      files that currently need manual sync.
- [x] Maintainers can inspect current lane, posture, and release eligibility
      from one supported command.
- [x] Release sessions cannot outlive `HEAD` drift silently.
- [x] Product-repo repair and dogfood flows can be rerun without leaving
      tracked guidance drift.
- [x] Release notes are authored once and reused by popup and permanent page.
- [ ] The shell explains Radar, Registry, Atlas, and Compass clearly on first
      use.
- [ ] Consumers can inspect version-delta story after the popup moment, not
      only during upgrade.
- [ ] Benchmark compare and history are visible in maintainer workflow before
      release dispatch.
- [x] Large-file refactor work follows targeted decomposition waves and does
      not turn into one repo-wide rewrite.

## Non-Goals
- [ ] Launching a repo-wide large-file refactor in `v0.1.6`.
- [ ] Replacing all existing in-progress workstreams with one giant umbrella
      implementation PR.
- [ ] Shipping maintainer-only release lane mechanics into bundled consumer
      guidance.
- [ ] Treating onboarding or other shell polish as more important than release
      truth and proof.

## Impacted Areas
- [ ] [AGENTS.md](/Users/freedom/code/odylith/AGENTS.md)
- [ ] [odylith/AGENTS.md](/Users/freedom/code/odylith/odylith/AGENTS.md)
- [ ] [odylith/maintainer/AGENTS.md](/Users/freedom/code/odylith/odylith/maintainer/AGENTS.md)
- [ ] [odylith/radar/source/INDEX.md](/Users/freedom/code/odylith/odylith/radar/source/INDEX.md)
- [ ] [odylith/technical-plans/INDEX.md](/Users/freedom/code/odylith/odylith/technical-plans/INDEX.md)
- [ ] [README.md](/Users/freedom/code/odylith/README.md)
- [ ] [docs/benchmarks/README.md](/Users/freedom/code/odylith/docs/benchmarks/README.md)
- [ ] [docs/benchmarks/REVIEWER_GUIDE.md](/Users/freedom/code/odylith/docs/benchmarks/REVIEWER_GUIDE.md)
- [ ] [benchmark CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/benchmark/CURRENT_SPEC.md)
- [ ] [release CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/release/CURRENT_SPEC.md)
- [ ] [GTM_AND_RELEASE_CHECKLIST.md](/Users/freedom/code/odylith/odylith/maintainer/GTM_AND_RELEASE_CHECKLIST.md)
- [ ] [pyproject.toml](/Users/freedom/code/odylith/pyproject.toml)
- [ ] [__init__.py](/Users/freedom/code/odylith/src/odylith/__init__.py)
- [ ] [product-version.v1.json](/Users/freedom/code/odylith/odylith/runtime/source/product-version.v1.json)
- [ ] [ga-gate](/Users/freedom/code/odylith/bin/ga-gate)
- [ ] [dogfood-activate](/Users/freedom/code/odylith/bin/dogfood-activate)
- [ ] [runtime.py](/Users/freedom/code/odylith/src/odylith/install/runtime.py)
- [ ] existing `B-006`, `B-021`, `B-022`, `B-028`, and `B-030` execution
      surfaces, plus any child refactor workstreams opened from this plan

## Risks & Mitigations
- [ ] Risk: the release umbrella turns into mush and loses execution discipline.
  - [ ] Mitigation: execute in bounded waves and open child workstreams when a
        slice deserves its own owner and validation lane.
- [ ] Risk: refactor work destabilizes central release-critical paths.
  - [ ] Mitigation: prioritize size x churn x centrality, use characterization
        tests first, and keep refactors to 1-2 files per PR where possible.
- [ ] Risk: release notes, popup copy, and persistent history diverge.
  - [ ] Mitigation: make release notes a real source artifact that downstream
        surfaces read instead of re-summarizing by hand.
- [ ] Risk: benchmark regressions still arrive too late.
  - [ ] Mitigation: make last-shipped benchmark compare part of pre-merge
        release-candidate proof.

## Validation/Test Plan
- [ ] `make release-preflight`
- [ ] isolated-checkout `ga-gate`
- [ ] benchmark compare against last shipped release
- [ ] docs/version/source-of-truth consistency checks
- [x] focused browser proof for release-note, explainer, and version-delta UX
- [x] characterization tests ahead of each large-file extraction wave
- [x] `git diff --check`

## Rollout/Communication
- [x] Capture the release learnings and feature asks in one umbrella backlog
      workstream and bound technical plan before implementation fans out.
- [x] Encode the large-file discipline in AGENTS guidance before the refactor
      wave begins.
- [ ] Execute release machinery hardening before net-new product surface that
      depends on the release lane.
- [ ] Reuse `B-006`, `B-021`, `B-022`, `B-028`, and `B-030` where they already
      match this release scope; open child workstreams only for genuinely new
      slices.

## Current Outcome
- [x] `B-033` now carries the `v0.1.6` umbrella scope.
- [x] This plan records the release learnings, must-ship list, should-ship
      product features, and the targeted refactor call for `v0.1.6`.
- [x] README and benchmark docs now lead with a benchmark-first evaluation
      frame and ship a reusable reviewer guide that tells human and AI
      reviewers to judge Odylith on execution deltas before structural overlap.
- [x] The root README now stays closer to a front-door landing page, while the
      fuller evaluation protocol, operating-model detail, governance-surface
      examples, and repo disclosures live in linked deep docs under `docs/`
      and `odylith/`.
- [x] A follow-on README compaction wave moved first-run workflow, repo-local
      truth, install-roots detail, repo-layout detail, and license/attribution
      explanation fully out of the landing page and into linked docs.
- [x] The final landing-page cleanup also removed the public-history note and
      moved the "do not clone for install" guidance into the install runbook
      with an explicit README link.
- [x] Quick Start now links out to `odylith/README.md#first-run` for the full
      post-install walkthrough, starter prompts, shell behavior, and reduced
      no-git bootstrap details instead of carrying that whole block on the
      landing page.
- [x] Release hardening now ships a supported `odylith lane status` CLI,
      `odylith benchmark compare`, a pre-merge `release-candidate` lane,
      self-invalidating release sessions, command-enforced maintainer branch
      safety, and version-truth sync driven outward from `pyproject.toml`.
- [x] Normal maintainer validation now checks version truth plus backlog,
      registry, plan binding, plan traceability, and plan risk-mitigation drift
      before release crunch.
- [x] Product-repo repair now stays source-aware to the repo under repair, and
      repeated repair leaves tracked guidance and governed source files
      unchanged while only refreshing `.odylith/` runtime state.
- [x] Launcher and bootstrap trust now fail closed on self-referential
      wrappers, unverified managed runtime candidates, and poisoned launcher
      fallback authority, while repair reuses healthy repo-local wrapped
      runtimes instead of recreating recursive launcher state.
- [x] The remaining stale product-repo `AGENTS.md` generator drift that only
      surfaced in clean release-candidate CI is now covered by live-root
      contract tests and tracked in Casebook as `CB-023`.
- [x] Release notes now live as authored source under
      [odylith/runtime/source/release-notes](/Users/freedom/code/odylith/odylith/runtime/source/release-notes)
      and drive both the upgrade spotlight and the permanent release-notes
      page.
- [x] Radar workstream detail language now presents product judgment instead
      of founder-branded copy: `Product View`, `Decision Basis`, `Priority
      Override`, and clearer ranking-basis bullets now read like maintained
      product reasoning instead of one-off founder rationale.
- [x] Release launch readiness now has a reusable maintainer
      [GTM and Release Checklist](/Users/freedom/code/odylith/odylith/maintainer/GTM_AND_RELEASE_CHECKLIST.md)
      wired into the canonical Release component and maintainer runbook so
      future launches reuse one asset-review and claim-discipline overlay
      instead of version-specific one-off notes.
- [x] The first bounded refactor wave is landed: shell release-note, welcome,
      runtime-payload, template-context, and system-status seams are extracted,
      `render_tooling_dashboard.py` is reduced to renderer and file I/O, and
      Compass self-host plus timeline-narrative helpers are split into sibling
      modules.
- [x] The shell presenter dropped from `3653` to `2807` lines in this wave
      without changing its public render entrypoints.
- [x] Focused validation for the landed waves is green:
  - [x] `python3 -m pytest -q tests/unit/install/test_release_version_session.py tests/unit/install/test_release_bootstrap.py tests/unit/runtime/test_validate_self_host_posture.py tests/unit/runtime/test_version_truth.py tests/unit/runtime/test_benchmark_compare.py tests/unit/runtime/test_maintainer_lane_status.py tests/unit/runtime/test_release_notes.py tests/unit/test_cli_maintainer_lane.py tests/unit/test_cli.py` -> `101 passed`
  - [x] `python3 -m pytest -q tests/unit/install/test_runtime.py tests/integration/install/test_manager.py tests/unit/runtime/test_tooling_dashboard_template_context.py tests/unit/runtime/test_compass_narrative_runtime.py tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/runtime/test_tooling_dashboard_runtime_builder.py tests/unit/runtime/test_compass_self_host_runtime.py tests/unit/runtime/test_shell_onboarding.py tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py` -> `105 passed, 1 skipped`
  - [x] `pytest tests/unit/install/test_runtime.py -q` -> `23 passed`
  - [x] `pytest tests/integration/install/test_manager.py -q` -> `64 passed`
- [ ] Remaining `v0.1.6` should-ship follow-through stays open for a later wave:
  explainer copy for Radar/Registry/Atlas/Compass, a persistent
  "what changed since my version?" view, and benchmark history UI.
