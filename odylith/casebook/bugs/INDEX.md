# Bug Index

Last updated (UTC): 2026-04-08

## Open Bugs

| Bug ID | Date | Title | Severity | Components | Status | Link |
| --- | --- | --- | --- | --- | --- | --- |
| CB-069 | 2026-04-08 | Pinned dogfood proof benchmark can wedge mid corpus and block release proof | P0 | `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  benchmark progress finalization, benchmark cleanup/interruption handling,
  pinned-dogfood release proof, maintainer benchmark override contract. | Open | [2026-04-08-pinned-dogfood-proof-benchmark-can-wedge-mid-corpus-and-block-release-proof.md](2026-04-08-pinned-dogfood-proof-benchmark-can-wedge-mid-corpus-and-block-release-proof.md) |
| CB-059 | 2026-04-06 | Sync failure summary repeats verbose output and stale next action | P1 | `src/odylith/cli.py`,
  `src/odylith/runtime/governance/sync_workstream_artifacts.py`, sync error
  presentation and next-action routing. | Open | [2026-04-06-sync-failure-summary-repeats-verbose-output-and-stale-next-action.md](2026-04-06-sync-failure-summary-repeats-verbose-output-and-stale-next-action.md) |
| CB-055 | 2026-04-06 | Repair and reinstall do not converge after partial runtime failure | P0 | `src/odylith/install/runtime.py`,
  `src/odylith/install/manager.py`, runtime replacement helpers, repair
  lifecycle, reinstall flow. | Open | [2026-04-06-repair-and-reinstall-do-not-converge-after-partial-runtime-failure.md](2026-04-06-repair-and-reinstall-do-not-converge-after-partial-runtime-failure.md) |
| CB-054 | 2026-04-06 | Macos runtime metadata files break managed runtime trust validation | P0 | `src/odylith/install/runtime_integrity.py`,
  `src/odylith/install/runtime.py`, managed runtime trust policy, feature-pack
  preflight. | Open | [2026-04-06-macos-runtime-metadata-files-break-managed-runtime-trust-validation.md](2026-04-06-macos-runtime-metadata-files-break-managed-runtime-trust-validation.md) |
| CB-060 | 2026-04-06 | Lifecycle plans print full dirty overlap by default | P2 | `src/odylith/cli.py`,
  `src/odylith/runtime/governance/sync_workstream_artifacts.py`, lifecycle-plan
  printers. | Open | [2026-04-06-lifecycle-plans-print-full-dirty-overlap-by-default.md](2026-04-06-lifecycle-plans-print-full-dirty-overlap-by-default.md) |
| CB-058 | 2026-04-06 | Legacy radar index is not normalized before sync validation | P0 | `src/odylith/runtime/governance/validate_backlog_contract.py`,
  `src/odylith/runtime/governance/backlog_authoring.py`,
  `src/odylith/runtime/governance/sync_workstream_artifacts.py`, Radar source
  upgrade bridge. | Open | [2026-04-06-legacy-radar-index-is-not-normalized-before-sync-validation.md](2026-04-06-legacy-radar-index-is-not-normalized-before-sync-validation.md) |
| CB-057 | 2026-04-06 | Legacy migration omits stale odyssey reference audit | P1 | `src/odylith/install/manager.py`, migration summary and
  reporting, tracked-text audit policy. | Open | [2026-04-06-legacy-migration-omits-stale-odyssey-reference-audit.md](2026-04-06-legacy-migration-omits-stale-odyssey-reference-audit.md) |
| CB-052 | 2026-04-04 | Registry live forensics miss source owned bundle mirror component activity | P1 | `src/odylith/runtime/governance/component_registry_intelligence.py`,
  Registry forensic coverage, `tribunal`, `remediator`, source-owned bundled
  runtime docs, Registry detail rendering. | Open | [2026-04-04-registry-live-forensics-miss-source-owned-bundle-mirror-component-activity.md](2026-04-04-registry-live-forensics-miss-source-owned-bundle-mirror-component-activity.md) |
| CB-051 | 2026-04-03 | Upgrade spotlight live refresh updates version badge but keeps release note hidden | P1 | `src/odylith/runtime/surfaces/templates/tooling_dashboard/control.js`,
  `src/odylith/runtime/surfaces/shell_onboarding.py`, upgrade spotlight
  dismissal/reopen contract, shell live-refresh browser path,
  `tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py`. | Open | [2026-04-03-upgrade-spotlight-live-refresh-updates-version-badge-but-keeps-release-note-hidden.md](2026-04-03-upgrade-spotlight-live-refresh-updates-version-badge-but-keeps-release-note-hidden.md) |
| CB-049 | 2026-04-03 | Benchmark repair style live cases penalize validator backed no op completion | P0 | `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_prompt.py`, live
  repair/publication scenario contract in
  `odylith/runtime/source/optimization-evaluation-corpus.v1.json`, bundled
  corpus mirror, validator-backed no-op scoring discipline. | Open | [2026-04-03-benchmark-repair-style-live-cases-penalize-validator-backed-no-op-completion.md](2026-04-03-benchmark-repair-style-live-cases-penalize-validator-backed-no-op-completion.md) |
| CB-048 | 2026-04-03 | Benchmark live agent activation prefers speculative install guidance rewrites over validator backed no op | P0 | `src/odylith/runtime/evaluation/odylith_benchmark_live_prompt.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_prompt_payloads.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`, activation
  family benchmark corpus contract, install activation handoff, validator-first
  no-op discipline. | Open | [2026-04-03-benchmark-live-agent-activation-prefers-speculative-install-guidance-rewrites-over-validator-backed-no-op.md](2026-04-03-benchmark-live-agent-activation-prefers-speculative-install-guidance-rewrites-over-validator-backed-no-op.md) |
| CB-040 | 2026-04-02 | Benchmark warm cold proof instability flips narrow slice winners | P0 | `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_prompt.py`,
  Odylith context-engine cache posture, proof-lane warm/cold robustness
  contract. | Open | [2026-04-02-benchmark-warm-cold-proof-instability-flips-narrow-slice-winners.md](2026-04-02-benchmark-warm-cold-proof-instability-flips-narrow-slice-winners.md) |
| CB-043 | 2026-04-02 | Benchmark validator truth restore rehydrates ambient repo state outside scoped snapshot | P0 | `src/odylith/runtime/evaluation/odylith_benchmark_isolation.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  validator-truth restore contract, disposable worktree integrity, proof-lane
  validator-backed success. | Open | [2026-04-02-benchmark-validator-truth-restore-rehydrates-ambient-repo-state-outside-scoped-snapshot.md](2026-04-02-benchmark-validator-truth-restore-rehydrates-ambient-repo-state-outside-scoped-snapshot.md) |
| CB-046 | 2026-04-02 | Benchmark support doc selector overweights generic guidance on proof slices | P0 | `src/odylith/runtime/evaluation/odylith_benchmark_prompt_payloads.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_prompt.py`,
  proof support-doc ranking, bounded-slice widening contract. | Open | [2026-04-02-benchmark-support-doc-selector-overweights-generic-guidance-on-proof-slices.md](2026-04-02-benchmark-support-doc-selector-overweights-generic-guidance-on-proof-slices.md) |
| CB-044 | 2026-04-02 | Benchmark scoped workspace snapshot omits dirty same package python dependencies | P0 | `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  shared live-workspace snapshot contract, proof-lane validator imports,
  disposable package integrity, validator-backed proof accounting. | Open | [2026-04-02-benchmark-scoped-workspace-snapshot-omits-dirty-same-package-python-dependencies.md](2026-04-02-benchmark-scoped-workspace-snapshot-omits-dirty-same-package-python-dependencies.md) |
| CB-045 | 2026-04-02 | Benchmark live result recovery drops schema valid agent message when last message file is missing | P0 | `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  structured-output recovery contract, proof-lane completion accounting. | Open | [2026-04-02-benchmark-live-result-recovery-drops-schema-valid-agent-message-when-last-message-file-is-missing.md](2026-04-02-benchmark-live-result-recovery-drops-schema-valid-agent-message-when-last-message-file-is-missing.md) |
| CB-027 | 2026-04-01 | Benchmark live runner inherits ambient user state and breaks raw codex isolation | P0 | `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`, benchmark
  component integrity contract, temp worktree provisioning, validator
  execution environment, `odylith_off` publication proof. | Open | [2026-04-01-benchmark-live-runner-inherits-ambient-user-state-and-breaks-raw-codex-isolation.md](2026-04-01-benchmark-live-runner-inherits-ambient-user-state-and-breaks-raw-codex-isolation.md) |
| CB-023 | 2026-03-31 | Product repo doctor repair rewrites root agents to stale managed block | P1 | `src/odylith/install/agents.py`,
  `src/odylith/install/manager.py`, root `AGENTS.md`, maintainer
  `release-candidate` workflow, product-repo repair contract. | Open | [2026-03-31-product-repo-doctor-repair-rewrites-root-agents-to-stale-managed-block.md](2026-03-31-product-repo-doctor-repair-rewrites-root-agents-to-stale-managed-block.md) |
| CB-016 | 2026-03-28 | Release preflight fails when dist contains stale wheel | P1 | `bin/release-preflight`, release asset publisher,
  maintainer release proof lane, release asset staging contract. | Open | [2026-03-28-release-preflight-fails-when-dist-contains-stale-wheel.md](2026-03-28-release-preflight-fails-when-dist-contains-stale-wheel.md) |
| CB-015 | 2026-03-28 | Release download cache and runtime restage lose atomicity on failure | P1 | `src/odylith/install/release_assets.py`,
  `src/odylith/install/runtime.py`, install-state file writes, local release
  smoke coverage. | Open | [2026-03-28-release-download-cache-and-runtime-restage-lose-atomicity-on-failure.md](2026-03-28-release-download-cache-and-runtime-restage-lose-atomicity-on-failure.md) |
| CB-014 | 2026-03-28 | Public consumer rollback to legacy preview runtime fails | P0 | `src/odylith/install/runtime.py`,
  `src/odylith/install/manager.py`, maintainer rehearsal lane,
  `bin/consumer-rehearsal`, launcher/runtime trust boundary. | Open | [2026-03-28-public-consumer-rollback-to-legacy-preview-runtime-fails.md](2026-03-28-public-consumer-rollback-to-legacy-preview-runtime-fails.md) |
| CB-013 | 2026-03-28 | Public consumer install depends on machine python | P0 | Release installer asset-generation lane,
  `src/odylith/install/runtime.py`, `src/odylith/install/release_assets.py`,
  Release installer contract, maintainer rehearsal lane. | Open | [2026-03-28-public-consumer-install-depends-on-machine-python.md](2026-03-28-public-consumer-install-depends-on-machine-python.md) |
| CB-012 | 2026-03-28 | Local release smoke installer rejects localhost assets with port | P1 | hosted installer allowlist logic, local maintainer
  release smoke, release preflight proof lane. | Open | [2026-03-28-local-release-smoke-installer-rejects-localhost-assets-with-port.md](2026-03-28-local-release-smoke-installer-rejects-localhost-assets-with-port.md) |
| CB-011 | 2026-03-28 | Local release adapter omits manifest and sigstore assets | P1 | local release adapter, verified-release download path,
  local maintainer hosted-asset smoke. | Open | [2026-03-28-local-release-adapter-omits-manifest-and-sigstore-assets.md](2026-03-28-local-release-adapter-omits-manifest-and-sigstore-assets.md) |
| CB-010 | 2026-03-28 | Local macos release build fails when linux runtime archive is expanded on case insensitive fs | P1 | release asset publisher, managed runtime bundle
  assembly, local maintainer preflight proof lane. | Open | [2026-03-28-local-macos-release-build-fails-when-linux-runtime-archive-is-expanded-on-case-insensitive-fs.md](2026-03-28-local-macos-release-build-fails-when-linux-runtime-archive-is-expanded-on-case-insensitive-fs.md) |
| CB-009 | 2026-03-28 | Linux arm64 context engine pack build fails without watchdog wheel | P0 | `src/odylith/install/managed_runtime.py`, release asset
  publisher, release asset build lane, context-engine watcher acceleration
  contract. | Open | [2026-03-28-linux-arm64-context-engine-pack-build-fails-without-watchdog-wheel.md](2026-03-28-linux-arm64-context-engine-pack-build-fails-without-watchdog-wheel.md) |
| CB-008 | 2026-03-28 | Github test workflow bypasses hatch managed environment | P1 | `.github/workflows/test.yml`, Hatch environment
  contract, repo CI posture. | Open | [2026-03-28-github-test-workflow-bypasses-hatch-managed-environment.md](2026-03-28-github-test-workflow-bypasses-hatch-managed-environment.md) |
| CB-007 | 2026-03-28 | Generated installer validator over escapes wheel regex | P1 | hosted installer validator, release manifest proof
  contract, local maintainer release smoke. | Open | [2026-03-28-generated-installer-validator-over-escapes-wheel-regex.md](2026-03-28-generated-installer-validator-over-escapes-wheel-regex.md) |
| CB-006 | 2026-03-28 | Generated installer misses runtime versions directory before activation | P1 | hosted installer activation path, local maintainer
  release smoke. | Open | [2026-03-28-generated-installer-misses-runtime-versions-directory-before-activation.md](2026-03-28-generated-installer-misses-runtime-versions-directory-before-activation.md) |
| CB-005 | 2026-03-28 | Full stack managed runtime payloads are too large for install and upgrade | P0 | release asset build lane,
  `src/odylith/install/release_assets.py`, `src/odylith/install/runtime.py`,
  `src/odylith/install/manager.py`, release asset contract, runtime retention
  contract. | Open | [2026-03-28-full-stack-managed-runtime-payloads-are-too-large-for-install-and-upgrade.md](2026-03-28-full-stack-managed-runtime-payloads-are-too-large-for-install-and-upgrade.md) |
| CB-004 | 2026-03-28 | Fresh consumer bootstrap misses backlog and plan starter contract | P0 | `src/odylith/install/manager.py`, consumer starter
  bootstrap contract, maintainer rehearsal lane, `bin/consumer-rehearsal`,
  backlog and plan starter indexes. | Open | [2026-03-28-fresh-consumer-bootstrap-misses-backlog-and-plan-starter-contract.md](2026-03-28-fresh-consumer-bootstrap-misses-backlog-and-plan-starter-contract.md) |
| CB-003 | 2026-03-28 | First install and same version upgrade mutate live runtime before fail closed proof | P1 | `src/odylith/install/manager.py`,
  `src/odylith/install/runtime.py`, fresh consumer install lifecycle,
  same-version upgrade contract, install smoke coverage. | Open | [2026-03-28-first-install-and-same-version-upgrade-mutate-live-runtime-before-fail-closed-proof.md](2026-03-28-first-install-and-same-version-upgrade-mutate-live-runtime-before-fail-closed-proof.md) |

## Closed Bugs

| Bug ID | Date | Title | Severity | Components | Status | Link |
| --- | --- | --- | --- | --- | --- | --- |
| CB-067 | 2026-04-08 | Tooling shell refresh can look fresh while compass child runtime stays stale | P1 | `src/odylith/runtime/surfaces/render_tooling_dashboard.py`,
  `src/odylith/runtime/surfaces/templates/tooling_dashboard/control.js`,
  `src/odylith/runtime/governance/sync_workstream_artifacts.py`, tooling shell
  refresh contract, Compass child-runtime freshness projection, shell runtime
  status messaging. | Closed | [2026-04-08-tooling-shell-refresh-can-look-fresh-while-compass-child-runtime-stays-stale.md](2026-04-08-tooling-shell-refresh-can-look-fresh-while-compass-child-runtime-stays-stale.md) |
| CB-071 | 2026-04-08 | Release workflows still pin first party actions on node 20 runtime | P1 | `.github/workflows/release.yml`,
  `.github/workflows/release-candidate.yml`, `.github/workflows/test.yml`,
  maintainer release workflow pin policy, release component contract. | Closed | [2026-04-08-release-workflows-still-pin-first-party-actions-on-node-20-runtime.md](2026-04-08-release-workflows-still-pin-first-party-actions-on-node-20-runtime.md) |
| CB-070 | 2026-04-08 | Release identity guard still depends on github generated committer metadata | P0 | `scripts/validate_git_identity.py`,
  `tests/unit/test_validate_git_identity.py`, release workflow identity guard,
  maintainer release contract. | Closed | [2026-04-08-release-identity-guard-still-depends-on-github-generated-committer-metadata.md](2026-04-08-release-identity-guard-still-depends-on-github-generated-committer-metadata.md) |
| CB-068 | 2026-04-08 | Explicit compass full refresh can pass with deterministic or stale runtime state | P0 | `src/odylith/runtime/surfaces/render_compass_dashboard.py`,
  `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`,
  `src/odylith/runtime/surfaces/compass_standup_brief_narrator.py`,
  `src/odylith/runtime/governance/dashboard_refresh_contract.py`,
  `src/odylith/runtime/governance/sync_workstream_artifacts.py`,
  Compass full-refresh contract, shell/browser freshness proof. | Closed | [2026-04-08-explicit-compass-full-refresh-can-pass-with-deterministic-or-stale-runtime-state.md](2026-04-08-explicit-compass-full-refresh-can-pass-with-deterministic-or-stale-runtime-state.md) |
| CB-066 | 2026-04-07 | Sync refresh rewrites unchanged artifacts and stales generated timestamps | P1 | `src/odylith/runtime/governance/backfill_workstream_traceability.py`,
  `src/odylith/runtime/governance/delivery_intelligence_engine.py`,
  stable generated-timestamp handling, and sync-owned generated JSON artifacts. | Closed | [2026-04-07-sync-refresh-rewrites-unchanged-artifacts-and-stales-generated-timestamps.md](2026-04-07-sync-refresh-rewrites-unchanged-artifacts-and-stales-generated-timestamps.md) |
| CB-065 | 2026-04-07 | Sync operator surface hides real controls and long running progress | P1 | `src/odylith/cli.py`,
  `src/odylith/runtime/governance/sync_workstream_artifacts.py`,
  `src/odylith/runtime/governance/validate_component_registry_contract.py`,
  sync CLI help and forwarding, sync execution-plan UX, operator warning
  summaries, overlap guardrails, and legacy-normalization reporting. | Closed | [2026-04-07-sync-operator-surface-hides-real-controls-and-long-running-progress.md](2026-04-07-sync-operator-surface-hides-real-controls-and-long-running-progress.md) |
| CB-063 | 2026-04-07 | Runtime retention prune fails on read only stale runtime trees | P1 | `src/odylith/install/manager.py`, retention cleanup for
  `.odylith/runtime/versions/` and `.odylith/cache/releases/`, hosted installer
  finish path, upgrade and reinstall lifecycle closeout. | Closed | [2026-04-07-runtime-retention-prune-fails-on-read-only-stale-runtime-trees.md](2026-04-07-runtime-retention-prune-fails-on-read-only-stale-runtime-trees.md) |
| CB-064 | 2026-04-07 | Hosted installer upgrades runtime without advancing repo pin | P1 | hosted installer publication flow,
  `src/odylith/cli.py`, install manager pin-alignment semantics in
  `src/odylith/install/manager.py`, and public install and upgrade guidance. | Closed | [2026-04-07-hosted-installer-upgrades-runtime-without-advancing-repo-pin.md](2026-04-07-hosted-installer-upgrades-runtime-without-advancing-repo-pin.md) |
| CB-061 | 2026-04-06 | Successful trust bootstrap still prints scary non fatal warnings | P1 | `src/odylith/install/release_assets.py`,
  `src/odylith/cli.py`, install and repair success messaging, release-note copy. | Closed | [2026-04-06-successful-trust-bootstrap-still-prints-scary-non-fatal-warnings.md](2026-04-06-successful-trust-bootstrap-still-prints-scary-non-fatal-warnings.md) |
| CB-062 | 2026-04-06 | Radar topology deep links fall through to stale filtered selection and browser proof misses disclosure gated routes | P0 | `src/odylith/runtime/surfaces/render_backlog_ui_html_runtime.py`,
  bundled Radar `backlog-app.v1.js` mirrors, Radar explicit-selection routing,
  and the Playwright browser proof lane in
  `tests/integration/runtime/test_surface_browser_deep.py`,
  `tests/integration/runtime/test_surface_browser_smoke.py`, and
  `tests/integration/runtime/test_surface_browser_ux_audit.py`. | Closed | [2026-04-06-radar-topology-deep-links-fall-through-to-stale-filtered-selection-and-browser-proof-misses-disclosure-gated-routes.md](2026-04-06-radar-topology-deep-links-fall-through-to-stale-filtered-selection-and-browser-proof-misses-disclosure-gated-routes.md) |
| CB-056 | 2026-04-06 | Doctor and version disagree on wrapped runtime trust degradation | P1 | `src/odylith/install/manager.py`,
  `src/odylith/cli.py`, runtime-source derivation, self-host posture
  validation. | Closed | [2026-04-06-doctor-and-version-disagree-on-wrapped-runtime-trust-degradation.md](2026-04-06-doctor-and-version-disagree-on-wrapped-runtime-trust-degradation.md) |
| CB-053 | 2026-04-05 | Memory substrate stale runtime reuse and projection scope thrash | P0 | `src/odylith/runtime/context_engine/odylith_context_engine_projection_search_runtime.py`, `src/odylith/runtime/context_engine/odylith_context_engine_projection_compiler_runtime.py`, `src/odylith/runtime/context_engine/odylith_context_engine.py`, `src/odylith/runtime/memory/odylith_memory_backend.py`, `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`, memory freshness contracts, benchmark warm-cache preparation, local LanceDB and Tantivy runtime posture. | Closed | [2026-04-05-memory-substrate-stale-runtime-reuse-and-projection-scope-thrash.md](2026-04-05-memory-substrate-stale-runtime-reuse-and-projection-scope-thrash.md) |
| CB-050 | 2026-04-03 | Compass explicit refresh fans into slow live scoped narration and leaves old deterministic brief visible on interrupt | P1 | `src/odylith/runtime/governance/sync_workstream_artifacts.py`,
  `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`,
  `src/odylith/runtime/surfaces/compass_standup_brief_narrator.py`,
  `src/odylith/runtime/surfaces/render_compass_dashboard.py`, Compass standup
  refresh contract, shell-facing refresh UX. | Closed | [2026-04-03-compass-explicit-refresh-fans-into-slow-live-scoped-narration-and-leaves-old-deterministic-brief-visible-on-interrupt.md](2026-04-03-compass-explicit-refresh-fans-into-slow-live-scoped-narration-and-leaves-old-deterministic-brief-visible-on-interrupt.md) |
| CB-047 | 2026-04-02 | Compass dashboard refresh shell safe keeps timeline audit pinned to stale snapshot | P1 | `src/odylith/runtime/surfaces/render_compass_dashboard.py`,
  `src/odylith/runtime/surfaces/compass_dashboard_runtime.py`,
  `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`,
  Compass shell-safe refresh contract,
  `tests/unit/runtime/test_render_compass_dashboard.py`,
  `tests/unit/runtime/test_compass_dashboard_runtime.py`. | Closed | [2026-04-02-compass-dashboard-refresh-shell-safe-keeps-timeline-audit-pinned-to-stale-snapshot.md](2026-04-02-compass-dashboard-refresh-shell-safe-keeps-timeline-audit-pinned-to-stale-snapshot.md) |
| CB-041 | 2026-04-02 | Benchmark public subagent validator wrapper misorders repo root | P0 | `src/odylith/cli.py`,
  `src/odylith/runtime/common/command_surface.py`, benchmark proof validator
  contract, `subagent-router` public CLI wrapper,
  `subagent-orchestrator` public CLI wrapper. | Closed | [2026-04-02-benchmark-public-subagent-validator-wrapper-misorders-repo-root.md](2026-04-02-benchmark-public-subagent-validator-wrapper-misorders-repo-root.md) |
| CB-034 | 2026-04-02 | Benchmark live public pair ran serially despite isolated workspaces | P1 | `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  benchmark live execution scheduling, benchmark runtime efficiency contract. | Closed | [2026-04-02-benchmark-live-public-pair-ran-serially-despite-isolated-workspaces.md](2026-04-02-benchmark-live-public-pair-ran-serially-despite-isolated-workspaces.md) |
| CB-036 | 2026-04-02 | Benchmark live proof overstates paired session metrics and reuses packet era guardrails | P0 | `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_graphs.py`, benchmark
  publication contract, README benchmark framing, benchmark reviewer guidance. | Closed | [2026-04-02-benchmark-live-proof-overstates-paired-session-metrics-and-reuses-packet-era-guardrails.md](2026-04-02-benchmark-live-proof-overstates-paired-session-metrics-and-reuses-packet-era-guardrails.md) |
| CB-039 | 2026-04-02 | Benchmark live prompt surfaced routing metadata instead of concrete focus | P0 | `src/odylith/runtime/evaluation/odylith_benchmark_live_prompt.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`, proof prompt
  contract, architecture benchmark handoff, benchmark README and SVG wording. | Closed | [2026-04-02-benchmark-live-prompt-surfaced-routing-metadata-instead-of-concrete-focus.md](2026-04-02-benchmark-live-prompt-surfaced-routing-metadata-instead-of-concrete-focus.md) |
| CB-035 | 2026-04-02 | Benchmark live path resolution crashes on impossible lane output | P0 | `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  live observed-path attribution, candidate-write detection, benchmark proof
  stability. | Closed | [2026-04-02-benchmark-live-path-resolution-crashes-on-impossible-lane-output.md](2026-04-02-benchmark-live-path-resolution-crashes-on-impossible-lane-output.md) |
| CB-037 | 2026-04-02 | Benchmark diagnostic probes could reenter live codex and leak temp state | P0 | `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  diagnostic latency probes, benchmark runtime hygiene contract, benchmark
  publication semantics. | Closed | [2026-04-02-benchmark-diagnostic-probes-could-reenter-live-codex-and-leak-temp-state.md](2026-04-02-benchmark-diagnostic-probes-could-reenter-live-codex-and-leak-temp-state.md) |
| CB-033 | 2026-04-02 | Benchmark default cli collapsed developer signal and publication proof | P1 | `src/odylith/runtime/context_engine/odylith_context_engine.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`, benchmark CLI
  contract, benchmark component spec, release benchmark runbooks. | Closed | [2026-04-02-benchmark-default-cli-collapsed-developer-signal-and-publication-proof.md](2026-04-02-benchmark-default-cli-collapsed-developer-signal-and-publication-proof.md) |
| CB-038 | 2026-04-02 | Atlas refresh diagnostics and surface selection clarity | P1 | `src/odylith/cli.py`,
  `src/odylith/runtime/governance/sync_workstream_artifacts.py`,
  `src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py`,
  `src/odylith/runtime/surfaces/assets/mermaid_cli_worker.mjs`, dashboard
  refresh operator contract, Atlas refresh diagnostics. | Closed | [2026-04-02-atlas-refresh-diagnostics-and-surface-selection-clarity.md](2026-04-02-atlas-refresh-diagnostics-and-surface-selection-clarity.md) |
| CB-042 | 2026-04-02 | Atlas mermaid preflight false fails on dompurify hook drift | P1 | `src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py`,
  `src/odylith/runtime/surfaces/assets/mermaid_cli_worker.mjs`, Atlas refresh
  validation contract, strict sync lane. | Closed | [2026-04-02-atlas-mermaid-preflight-false-fails-on-dompurify-hook-drift.md](2026-04-02-atlas-mermaid-preflight-false-fails-on-dompurify-hook-drift.md) |
| CB-026 | 2026-04-01 | Runtime launcher wrapper recursion and trust boundary hardening | P0 | `src/odylith/install/runtime.py`,
  `src/odylith/install/manager.py`, repo launcher and bootstrap launcher shell
  contract, wrapped-runtime fallback normalization, product-repo detached
  `source-local` repair path, consumer and dogfood runtime trust boundary. | Closed | [2026-04-01-runtime-launcher-wrapper-recursion-and-trust-boundary-hardening.md](2026-04-01-runtime-launcher-wrapper-recursion-and-trust-boundary-hardening.md) |
| CB-025 | 2026-04-01 | Product repo tooling shell hides runtime version badge | P1 | `src/odylith/runtime/surfaces/render_tooling_dashboard.py`,
  `src/odylith/runtime/surfaces/tooling_dashboard_template_context.py`,
  `src/odylith/runtime/surfaces/templates/tooling_dashboard/page.html.j2`,
  `src/odylith/runtime/surfaces/templates/tooling_dashboard/style.css`,
  dashboard header contract. | Closed | [2026-04-01-product-repo-tooling-shell-hides-runtime-version-badge.md](2026-04-01-product-repo-tooling-shell-hides-runtime-version-badge.md) |
| CB-030 | 2026-04-01 | Benchmark sandbox strip policy deletes truth bearing maintainer docs | P0 | `src/odylith/runtime/evaluation/odylith_benchmark_isolation.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  sandbox strip policy, benchmark trust boundary, benchmark doc availability in
  disposable worktrees. | Closed | [2026-04-01-benchmark-sandbox-strip-policy-deletes-truth-bearing-maintainer-docs.md](2026-04-01-benchmark-sandbox-strip-policy-deletes-truth-bearing-maintainer-docs.md) |
| CB-032 | 2026-04-01 | Benchmark relative efficiency guardrails punish success against failed baseline | P0 | `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  benchmark acceptance semantics, benchmark component status contract, release
  benchmark publication guidance, reviewer framing. | Closed | [2026-04-01-benchmark-relative-efficiency-guardrails-punish-success-against-failed-baseline.md](2026-04-01-benchmark-relative-efficiency-guardrails-punish-success-against-failed-baseline.md) |
| CB-031 | 2026-04-01 | Benchmark observed path attribution counts transitive links from doc content | P0 | `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  live observed-path attribution, required-path precision, hallucinated-surface
  rate, benchmark family deltas. | Closed | [2026-04-01-benchmark-observed-path-attribution-counts-transitive-links-from-doc-content.md](2026-04-01-benchmark-observed-path-attribution-counts-transitive-links-from-doc-content.md) |
| CB-029 | 2026-04-01 | Benchmark live prompt drops selected docs before codex handoff | P0 | `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  benchmark prompt-token accounting, live prompt contract, benchmark accuracy
  interpretation. | Closed | [2026-04-01-benchmark-live-prompt-drops-selected-docs-before-codex-handoff.md](2026-04-01-benchmark-live-prompt-drops-selected-docs-before-codex-handoff.md) |
| CB-028 | 2026-04-01 | Benchmark gate can pass when both live lanes fail | P0 | `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  benchmark hard-quality gate, live benchmark status publication. | Closed | [2026-04-01-benchmark-gate-can-pass-when-both-live-lanes-fail.md](2026-04-01-benchmark-gate-can-pass-when-both-live-lanes-fail.md) |
| CB-024 | 2026-03-31 | Radar backlog index uses absolute workstation links and breaks clean checkout proof | P1 | `odylith/radar/source/INDEX.md`,
  `src/odylith/runtime/governance/backlog_authoring.py`,
  `src/odylith/runtime/governance/reconcile_plan_workstream_binding.py`,
  `src/odylith/runtime/governance/validate_backlog_contract.py`,
  backlog portability hygiene coverage. | Closed | [2026-03-31-radar-backlog-index-uses-absolute-workstation-links-and-breaks-clean-checkout-proof.md](2026-03-31-radar-backlog-index-uses-absolute-workstation-links-and-breaks-clean-checkout-proof.md) |
| CB-022 | 2026-03-29 | Release auto tagging burns unpublished patch versions and skips ga candidates | P0 | release semver resolution helpers, release session
  state helpers, maintainer release-version preview/show commands, release
  session contract, release component spec and runbook. | Closed | [2026-03-29-release-auto-tagging-burns-unpublished-patch-versions-and-skips-ga-candidates.md](2026-03-29-release-auto-tagging-burns-unpublished-patch-versions-and-skips-ga-candidates.md) |
| CB-021 | 2026-03-29 | Odylith context engine daemon transport auth and repair hardening gap | P1 | `src/odylith/runtime/context_engine/odylith_context_engine.py`,
  `src/odylith/runtime/context_engine/odylith_context_engine_store.py`,
  `src/odylith/install/repair.py`, Odylith Context Engine local daemon
  transport contract, repair reset-local-state flow, daemon hardening tests. | Closed | [2026-03-29-odylith-context-engine-daemon-transport-auth-and-repair-hardening-gap.md](2026-03-29-odylith-context-engine-daemon-transport-auth-and-repair-hardening-gap.md) |
| CB-020 | 2026-03-29 | Compass standup brief fails to use local provider and stays deterministic | P1 | `src/odylith/runtime/evaluation/odylith_reasoning.py`,
  `src/odylith/runtime/surfaces/compass_dashboard_runtime.py`,
  `src/odylith/runtime/surfaces/compass_standup_brief_narrator.py`, Compass
  standup-brief cache contract, shared local-provider selection path. | Closed | [2026-03-29-compass-standup-brief-fails-to-use-local-provider-and-stays-deterministic.md](2026-03-29-compass-standup-brief-fails-to-use-local-provider-and-stays-deterministic.md) |
| CB-019 | 2026-03-29 | Compass runtime freshness regressed brief risk and timeline trust | P1 | `src/odylith/runtime/surfaces/render_compass_dashboard.py`,
  `src/odylith/runtime/surfaces/compass_standup_brief_narrator.py`,
  `src/odylith/runtime/context_engine/odylith_context_engine_store.py`,
  `src/odylith/runtime/context_engine/surface_projection_fingerprint.py`,
  Compass runtime freshness contract, shell UX/browser proof lane. | Closed | [2026-03-29-compass-runtime-freshness-regressed-brief-risk-and-timeline-trust.md](2026-03-29-compass-runtime-freshness-regressed-brief-risk-and-timeline-trust.md) |
| CB-018 | 2026-03-29 | Compass live self host risk was hidden by utc date and kpi omission | P1 | `src/odylith/runtime/surfaces/compass_dashboard_shell.py`,
  `src/odylith/runtime/surfaces/compass_dashboard_runtime.py`, Compass live KPI
  render path, self-host posture risk rows, browser smoke coverage. | Closed | [2026-03-29-compass-live-self-host-risk-was-hidden-by-utc-date-and-kpi-omission.md](2026-03-29-compass-live-self-host-risk-was-hidden-by-utc-date-and-kpi-omission.md) |
| CB-017 | 2026-03-29 | Atlas tab reuses cross surface shell state and shows inconsistent diagram counts | P1 | `src/odylith/runtime/surfaces/templates/tooling_dashboard/control.js`,
  `src/odylith/runtime/surfaces/render_mermaid_catalog.py`,
  Atlas shell query-state contract, Atlas filter normalization behavior,
  headless browser surface proof lane. | Closed | [2026-03-29-atlas-tab-reuses-cross-surface-shell-state-and-shows-inconsistent-diagram-counts.md](2026-03-29-atlas-tab-reuses-cross-surface-shell-state-and-shows-inconsistent-diagram-counts.md) |
| CB-002 | 2026-03-24 | Odylith autospawn daemon ownership and lifetime leak | P0 | `src/odylith/runtime/context_engine/odylith_context_engine.py`, Odylith daemon autospawn lifecycle, `tests/unit/runtime/test_odylith_context_engine.py`, Odylith context-engine guidance/specs. | Closed | [2026-03-24-odylith-autospawn-daemon-ownership-and-lifetime-leak.md](2026-03-24-odylith-autospawn-daemon-ownership-and-lifetime-leak.md) |
| CB-001 | 2026-02-15 | Mirror registry barrier deadlock in tests | P2 | Tooling/tests only (mirror registry concurrency tests). | Closed | [2026-02-15-mirror-registry-barrier-deadlock-in-tests.md](2026-02-15-mirror-registry-barrier-deadlock-in-tests.md) |
