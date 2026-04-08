Status: In progress

Created: 2026-04-07

Updated: 2026-04-08

Backlog: B-060

Goal: Turn the concrete `v0.1.9` release learnings into an explicit `v0.1.10`
release-hardening plan that restores full benchmark proof, removes the narrow
GitHub merge-identity exception, cleans up first-install shell proof, and keeps
post-publish maintainer state trustworthy.

Assumptions:
- `v0.1.9` was the right ship decision even though the release lane still
  exposed cleanup work for the next cut.
- The current benchmark override is a one-release exception, not a new normal.
- The first-install shell warning is a real polish and trust bug even though
  the broader consumer and GA gates recovered successfully.
- Welcome-screen and upgrade-popup UX are already strong enough that the next
  release should preserve them as proof gates, not redesign them again.

Constraints:
- Do not rewrite `v0.1.9` history or treat its GitHub-generated merge committer
  shape as canonical contributor policy.
- Keep the public install and upgrade contract stable while tightening the
  maintainer release path behind it.
- Benchmark-proof reinstatement for `v0.1.10` must be real proof, not a
  weaker metric disguised as a full audit.
- Do not normalize dirty post-publish maintainer worktrees as acceptable
  release aftermath.

Reversibility: This planning step is governance-only. Later implementation
should stay reversible by keeping release-lane hardening, benchmark proof,
CI pin refresh, and shell-refresh fixes in bounded slices with explicit proof.

Boundary Conditions:
- Scope includes canonical release identity posture, benchmark proof
  reinstatement, first-install shell refresh robustness, release workflow pin
  hygiene, and post-publish maintainer checkout cleanliness.
- Scope excludes unrelated new product features and any attempt to quietly
  weaken release authority checks for convenience.

Related Bugs:
- [CB-061](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-06-successful-trust-bootstrap-still-prints-scary-non-fatal-warnings.md)
  tracks the successful-verification warning spill and clarity contract.
- [CB-063](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-07-runtime-retention-prune-fails-on-read-only-stale-runtime-trees.md)
  tracks read-only stale-runtime retention cleanup aborting an otherwise healthy
  hosted-install upgrade.
- [CB-064](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-07-hosted-installer-upgrades-runtime-without-advancing-repo-pin.md)
  tracks the hosted installer activating a newer runtime without advancing the
  tracked repo pin.
- [CB-060](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-06-lifecycle-plans-print-full-dirty-overlap-by-default.md)
  remains the anchor for lifecycle-plan overlap messaging and may absorb the
  stronger churn-summary follow-up instead of opening a duplicate UX bug.
- [CB-065](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-07-sync-operator-surface-hides-real-controls-and-long-running-progress.md)
  tracks the downstream sync operator-surface gap: hidden public controls,
  silent long-running action steps, weak dirty-overlap acknowledgement, and
  warning/report discoverability.
- [CB-066](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-07-sync-refresh-rewrites-unchanged-artifacts-and-stales-generated-timestamps.md)
  tracks sync-owned generated JSON artifacts rewriting semantic no-op payloads
  and making embedded `generated_utc` disagree with filesystem mtimes.
- [CB-050](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-03-compass-explicit-refresh-fans-into-slow-live-scoped-narration-and-leaves-old-deterministic-brief-visible-on-interrupt.md)
  remains the Compass refresh trust anchor and now carries the downstream
  2026-04-07 proof that explicit `full` refresh still shares the bounded
  shell-safe timeout, points at the wrong recovery command, and can silently
  leave the old `shell-safe` payload active after failure.
- [CB-067](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-08-tooling-shell-refresh-can-look-fresh-while-compass-child-runtime-stays-stale.md)
  tracks the shell-host follow-up: after a failed deeper Compass refresh, a
  successful `tooling_shell` rerender can still leave the parent surface
  presenting the stale Compass brief with no shell-level freshness warning.

## Learnings
- [x] `v0.1.9` published on 2026-04-07, but canonical release proof still
      needed a narrow compatibility exception for the currently observed GitHub
      squash-merge shape on `main`: maintainer author plus
      `GitHub <noreply@github.com>` committer.
- [x] `make consumer-rehearsal PREVIOUS_VERSION=0.1.8` and
      `make ga-gate PREVIOUS_VERSION=0.1.8` both recovered successfully, but
      the first shell-only refresh in the disposable consumer repo still logged
      missing `radar.html`, `atlas.html`, `compass.html`, `registry.html`, and
      `casebook.html` before broad sync settled the repo into a healthy state.
- [x] Benchmark proof for `v0.1.9` was intentionally skipped under a tracked
      maintainer override and must come back as a first-class release gate for
      `v0.1.10`.
- [x] The GitHub release workflow succeeded but surfaced an upcoming Node 20
      deprecation warning on pinned first-party actions.
- [x] `make dogfood-activate` refreshed tracked generated surfaces in the
      maintainer checkout after publish, leaving real post-release drift behind
      unless that worktree is moved onto a branch.
- [x] Welcome-screen and upgrade-popup proof stayed green and should remain
      locked as regression coverage while the release lane underneath them gets
      stricter.
- [x] Real downstream hosted-install upgrade feedback on 2026-04-07 added two
      more concrete closeout gaps: stale read-only runtime trees can fail the
      retention-prune tail after successful activation, and the hosted installer
      can leave the repo in `diverged_verified_version` by upgrading the active
      runtime without advancing the tracked repo pin.
- [x] Real downstream sync feedback on 2026-04-07 added a broader operator
      trust slice: the engine planned and validated well, but `odylith sync`
      still hid supported controls at the public help surface, stayed too quiet
      during some long phases, under-signaled high-overlap mutation risk, and
      rewrote some unchanged generated artifacts in ways that broke audit
      timestamps.
- [x] Real downstream Compass refresh feedback on 2026-04-07 showed the
      remaining explicit-refresh trust gap: bounded `shell-safe` refresh stayed
      healthy, but explicit `full` still inherited the same 45-second wrapper
      timeout, surfaced `odylith compass update --repo-root .` as a bogus next
      command, and left the old `shell-safe` payload active with no visible
      failure marker when deeper refresh did not land.
- [x] Real downstream shell follow-up feedback on 2026-04-08 showed the parent
      surface still overstated freshness after the Compass-side fix: a
      successful `tooling_shell` rerender could leave the visible Compass brief
      on an older child snapshot with no shell-level warning that Compass had
      not actually been rerendered.

## Must-Ship
- [ ] Remove dependency on GitHub-generated merge committer metadata from the
      canonical release ancestry rule, or replace the merge/publication posture
      with a cleaner path that preserves canonical maintainer identity end to
      end.
- [ ] Retire the `v0.1.9` benchmark-proof override and restore full benchmark
      audit plus publication-quality proof for `v0.1.10`.
- [ ] Make first-install, consumer-rehearsal, and GA-gate shell refresh render
      cleanly without transient missing-surface warnings before broad sync.
- [ ] Make hosted-install closeout converge on one truthful posture: healthy
      activation, best-effort stale cleanup, and matching active-plus-pinned
      versions when the public installer upgrades an existing consumer repo.
- [ ] Make `odylith sync` operator proof honest and discoverable: visible help
      for supported controls, heartbeat progress for long action-backed steps,
      explicit acknowledgement past large dirty-overlap thresholds, structured
      warning pointers, and truthful audit metadata for semantic no-op artifact
      refreshes.
- [x] Make explicit Compass full refresh operator-truthful: align the renderer
      default with `shell-safe`, give `full` a viable timeout budget, replace
      the bogus `compass update` failure hint with a real rerender command, and
      mark the live Compass payload when a requested deeper refresh fails so
      the shell cannot silently keep serving the old bounded snapshot.
- [x] Make shell refresh truthful about Compass child-runtime freshness: when
      the wrapper rerenders without Compass, project the current Compass
      runtime age and last failed deeper-refresh state into the shell so the
      Compass tab admits it is showing an older child snapshot instead of
      implying fresh brief data.
- [ ] Refresh pinned first-party GitHub Actions inputs so the release workflow
      no longer carries the Node 20 deprecation warning.
- [ ] Keep post-publish `dogfood-activate` and surface refresh from dirtying
      the active maintainer checkout, or move that generated refresh into an
      isolated proof workspace by design.

## Should-Ship
- [ ] Thread the `v0.1.10` release feedback into one reusable maintainer-facing
      checklist so the same proof holes do not have to be rediscovered during
      future release crunch.
- [ ] Keep welcome-screen and upgrade-popup browser proof in the main release
      lane so `B-030` gains do not silently regress while release plumbing
      changes.
- [ ] Make the next release proof report name any remaining maintainer
      overrides explicitly instead of burying them in source artifacts.

## Defer
- [ ] Do not reopen `v0.1.9` just to erase its already-shipped compatibility
      exception.
- [ ] Do not bundle unrelated feature work into this release-hardening wave.
- [ ] Do not treat a passing broad sync as an excuse to keep the first shell
      refresh noisy.

## Success Criteria
- [ ] Canonical release proof for `v0.1.10` passes without relying on the
      GitHub-generated `noreply@github.com` committer exception.
- [ ] `v0.1.10` release prep and GA proof include full benchmark audit again.
- [ ] Disposable consumer proof repos render the shell cleanly on first refresh
      with zero transient missing-surface warnings.
- [ ] Hosted installer upgrades on already-installed consumer repos finish with
      zero retention-cleanup hard failures from read-only stale runtimes and
      zero silent active-versus-pin divergence.
- [ ] Release CI no longer emits the Node 20 deprecation warning on pinned
      first-party actions.
- [ ] Post-publish maintainer checkout either remains clean or uses an isolated
      refresh path that keeps generated drift out of the active branch.
- [ ] Welcome-screen and upgrade-popup browser proof stay green while the above
      hardening lands.
- [ ] Consumer sync proof shows `odylith sync --help` advertising real controls,
      action-backed heartbeat output on long phases, large overlap gated behind
      explicit acknowledgement, and unchanged generated JSON artifacts staying
      current instead of being falsely rewritten.
- [ ] Downstream Compass refresh proof shows explicit `full` refresh using a
      larger timeout budget than bounded `shell-safe`, a truthful next command,
      and an explicit stale-and-failed warning when the requested deeper
      refresh does not land.

## Non-Goals
- [ ] Changing the canonical hosted installer entrypoint away from
      `curl -fsSL https://odylith.ai/install.sh | bash`.
- [ ] Replacing authored release notes or the upgrade spotlight contract.
- [ ] Treating benchmark publication polish as optional once the proof lane is
      reinstated.

## Impacted Areas
- [ ] [MAINTAINER_RELEASE_RUNBOOK.md](/Users/freedom/code/odylith/odylith/MAINTAINER_RELEASE_RUNBOOK.md)
- [x] [AGENTS.md](/Users/freedom/code/odylith/odylith/maintainer/AGENTS.md)
- [ ] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/release/CURRENT_SPEC.md)
- [x] [v0.1.10.md](/Users/freedom/code/odylith/odylith/runtime/source/release-notes/v0.1.10.md)
- [x] [v0.1.10.md](/Users/freedom/code/odylith/src/odylith/bundle/assets/odylith/runtime/source/release-notes/v0.1.10.md)
- [ ] [cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)
- [ ] [release_assets.py](/Users/freedom/code/odylith/src/odylith/install/release_assets.py)
- [ ] [INSTALL_AND_UPGRADE_RUNBOOK.md](/Users/freedom/code/odylith/odylith/INSTALL_AND_UPGRADE_RUNBOOK.md)
- [ ] Maintainer contributor-identity guard
- [ ] [test_validate_git_identity.py](/Users/freedom/code/odylith/tests/unit/test_validate_git_identity.py)
- [ ] [release.yml](/Users/freedom/code/odylith/.github/workflows/release.yml)
- [ ] [release-maintainer-overrides.v1.json](/Users/freedom/code/odylith/odylith/runtime/source/release-maintainer-overrides.v1.json)
- [ ] [manager.py](/Users/freedom/code/odylith/src/odylith/install/manager.py)
- [ ] [sync_workstream_artifacts.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/sync_workstream_artifacts.py)
- [ ] [render_compass_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_compass_dashboard.py)
- [ ] [validate_component_registry_contract.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/validate_component_registry_contract.py)
- [ ] [backfill_workstream_traceability.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/backfill_workstream_traceability.py)
- [ ] [delivery_intelligence_engine.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/delivery_intelligence_engine.py)
- [ ] [render_tooling_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_tooling_dashboard.py)
- [ ] [test_release_bootstrap.py](/Users/freedom/code/odylith/tests/unit/install/test_release_bootstrap.py)
- [ ] [test_cli.py](/Users/freedom/code/odylith/tests/unit/test_cli.py)
- [ ] [test_manager.py](/Users/freedom/code/odylith/tests/integration/install/test_manager.py)
- [ ] [test_sync_cli_compat.py](/Users/freedom/code/odylith/tests/unit/runtime/test_sync_cli_compat.py)
- [ ] [test_render_compass_dashboard.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_compass_dashboard.py)
- [ ] [test_backfill_workstream_traceability.py](/Users/freedom/code/odylith/tests/unit/runtime/test_backfill_workstream_traceability.py)
- [ ] [test_delivery_intelligence_engine.py](/Users/freedom/code/odylith/tests/unit/runtime/test_delivery_intelligence_engine.py)
- [ ] [test_release_assets.py](/Users/freedom/code/odylith/tests/unit/install/test_release_assets.py)
- [ ] [test_tooling_dashboard_onboarding_browser.py](/Users/freedom/code/odylith/tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py)
- [ ] [test_odylith_benchmark_corpus.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_corpus.py)
- [ ] [test_odylith_benchmark_runner.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_runner.py)

## Risks & Mitigations
- [ ] Risk: the GitHub committer exception stays convenient enough that nobody
      actually removes it.
  - [ ] Mitigation: make the `v0.1.10` release lane fail on lingering
        exception-only ancestry instead of documenting the problem after ship.
- [ ] Risk: benchmark proof returns in a weak or partial form.
  - [ ] Mitigation: tie `v0.1.10` release proof to the full benchmark audit and
        publication contract, not just a smoke benchmark.
- [ ] Risk: fixing the first-install shell wobble by broadening sync too early
      slows the consumer lane.
  - [ ] Mitigation: make the first refresh surface-safe without turning every
        upgrade into a full expensive governance pass by default.
- [ ] Risk: post-publish cleanliness is "solved" by teaching maintainers to
      ignore generated drift.
  - [ ] Mitigation: either keep the active checkout clean or make the dirty
        output live only in an isolated proof workspace.
- [ ] Risk: sync UX hardening broadens noise or latency instead of making the
      path clearer.
  - [ ] Mitigation: keep heartbeat output thresholded, keep overlap gating
        explicit and bounded, and point warning-heavy passes at durable report
        artifacts instead of dumping more terminal text.
- [ ] Risk: the explicit Compass full-refresh fix only raises the timeout and
      still leaves operators unable to tell whether deeper refresh landed.
  - [ ] Mitigation: update the live Compass payload on failure, clear that
        marker on success, and point operators at a real rerender command
        instead of the event-writing `compass update` path.
- [ ] Risk: audit-fidelity fixes accidentally rotate timestamps on every no-op
      run.
  - [ ] Mitigation: preserve stable `generated_utc` behavior and stop rewriting
        semantic no-op JSON payloads instead of forcing timestamp churn.

## Validation/Test Plan
- [ ] `make release-preflight VERSION=0.1.10`
- [ ] `make consumer-rehearsal PREVIOUS_VERSION=0.1.9`
- [ ] `make ga-gate PREVIOUS_VERSION=0.1.9`
- [ ] full benchmark audit and release-proof rerun for `v0.1.10`
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/integration/install/test_manager.py tests/unit/install/test_release_bootstrap.py tests/unit/test_cli.py`
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/test_cli.py tests/unit/runtime/test_sync_cli_compat.py tests/unit/runtime/test_backfill_workstream_traceability.py tests/unit/runtime/test_delivery_intelligence_engine.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_sync_cli_compat.py tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_compass_dashboard_runtime.py`
      (`54 passed`)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_release_bootstrap.py tests/unit/test_cli.py tests/unit/runtime/test_sync_cli_compat.py tests/integration/install/test_manager.py::test_install_bundle_align_pin_advances_existing_repo_pin_to_active_runtime tests/integration/install/test_manager.py::test_upgrade_prunes_runtime_and_release_cache_retention tests/integration/install/test_manager.py::test_upgrade_warns_and_continues_when_retention_prune_stays_permission_denied`
      (`116 passed`)
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/integration/install/test_manager.py tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_compass_refresh_contract.py tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_compass_standup_brief_narrator.py tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/runtime/test_render_casebook_dashboard.py tests/unit/runtime/test_shell_onboarding.py tests/unit/runtime/test_release_notes.py`
      (`121 passed`)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_surface_browser_deep.py tests/integration/runtime/test_surface_browser_ux_audit.py tests/integration/runtime/test_surface_browser_filter_audit.py tests/integration/runtime/test_surface_browser_layout_audit.py -k 'compass or shell or casebook'`
      (`33 passed, 18 deselected`)
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/test_validate_git_identity.py tests/unit/runtime/test_odylith_benchmark_corpus.py tests/unit/runtime/test_odylith_benchmark_runner.py`
- [ ] `git diff --check`

## Rollout/Communication
- [x] Capture `v0.1.9` release feedback in a dedicated `v0.1.10` workstream and
      plan before implementation fans out.
- [x] Move the dirty post-release maintainer worktree off `main` and onto
      `2026/freedom/v0.1.10` so the follow-up work starts from the truthful
      release aftermath.
- [ ] Keep the `v0.1.9` benchmark override explicitly documented as expired for
      the next release.
- [ ] Communicate the long-term merge-identity cleanup as a deliberate next
      release objective instead of letting the temporary compatibility rule look
      canonical.

## Current Outcome
- [x] `B-060` now carries the `v0.1.10` release-feedback scope.
- [x] This plan captures the narrow `v0.1.9` identity exception, the first
      shell-refresh wobble, the skipped benchmark proof, the CI runtime warning,
      and the dirty post-publish maintainer checkout as explicit next-release
      engineering work.
- [x] The active branch `2026/freedom/v0.1.10` now holds the real post-release
      worktree drift that was previously sitting dirty on `main`.
- [x] First-install bootstrap now skips the known-doomed shell-only render when
      Radar, Atlas, Compass, Registry, or Casebook HTML is still absent and
      goes straight to full sync, so fresh installs stop printing transient
      missing-surface failures before the repo settles.
- [x] The hosted installer now filters the known benign offline Sigstore/TUF
  warnings that still accompany successful verification on the bootstrap
  path, while preserving real verifier stderr for actual failures.
- [x] Hosted-install closeout now aligns the tracked repo pin with the verified
      runtime it just activated, so existing consumer installs stop landing in
      `diverged_verified_version` after a successful hosted upgrade.
- [x] Runtime retention cleanup now retries stale-path permission hardening and
      degrades to explicit remediation warnings instead of overturning a
      healthy activation when a read-only old tree still cannot be removed.
- [x] Lifecycle dry-run overlap summaries now group dirty entries by area so
      dirty consumer repos get a stronger preflight readout without dumping the
      full overlap list by default.
- [ ] Sync operator hardening is next in this same workstream: publish the real
      `odylith sync` control surface, add long-step heartbeats plus overlap
      gating, point warning-heavy passes at durable reports, and stop semantic
      no-op generated artifacts from being falsely rewritten.
- [x] Compass explicit-refresh hardening landed: the renderer now defaults to
      `shell-safe`, the dashboard wrapper gives explicit `full` refresh a
      larger timeout budget, failed deeper refreshes stamp the live payload
      with an explicit warning instead of silently serving the old bounded
      snapshot, and the bogus `odylith compass update --repo-root .` next hint
      is replaced by a real rerender command.
- [x] Shell-host Compass freshness projection landed: `tooling_shell` refresh
      now states when it only updated wrapper assets, surfaces failed deeper
      Compass rerenders on the Compass tab, and stops stale child-runtime data
      from masquerading as the result of the shell refresh.
- [x] `v0.1.10` authored release-note source is now in place and mirrored into
      the bundle assets, and the upgrade-spotlight browser proof now runs
      against that note instead of the prior release copy.
- [x] Focused shell-host proof passed:
      `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/runtime/test_sync_cli_compat.py tests/unit/runtime/test_render_compass_dashboard.py`
      (`54 passed`) plus `python3 -m py_compile src/odylith/runtime/surfaces/tooling_dashboard_surface_status.py src/odylith/runtime/surfaces/render_tooling_dashboard.py src/odylith/runtime/governance/sync_workstream_artifacts.py src/odylith/runtime/surfaces/render_compass_dashboard.py`.
- [x] Focused proof passed:
      `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_release_bootstrap.py tests/unit/test_cli.py tests/unit/runtime/test_sync_cli_compat.py tests/integration/install/test_manager.py::test_install_bundle_align_pin_advances_existing_repo_pin_to_active_runtime tests/integration/install/test_manager.py::test_upgrade_prunes_runtime_and_release_cache_retention tests/integration/install/test_manager.py::test_upgrade_warns_and_continues_when_retention_prune_stays_permission_denied`
      (`116 passed`) plus targeted compile proof for
      `src/odylith/install/manager.py`, `src/odylith/cli.py`, and
      `src/odylith/runtime/common/dirty_overlap.py`.
