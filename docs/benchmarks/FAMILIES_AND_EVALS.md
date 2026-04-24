# Benchmark Families And Eval Catalog

This is the reader-facing map for Odylith's tracked benchmark corpus.

The source of truth is
`odylith/runtime/source/optimization-evaluation-corpus.v1.json`.

## Coverage At A Glance

- Tracked corpus:
  `77` implementation scenarios plus `5` architecture scenarios, `82` total
- Current seriousness floor in tracked source truth:
  `41` write-plus-validator scenarios, `31` correctness-critical scenarios,
  and a mechanism-heavy implementation share of `0.286`
- Required coding-work and control families now present in tracked source truth:
  `api_contract_evolution`, `stateful_bug_recovery`,
  `external_dependency_recovery`, `destructive_scope_control`,
  `guidance_behavior`, and `discipline`
- Current published proof snapshot:
  read [Current Live Benchmark Snapshot](LIVE_BENCHMARK_SNAPSHOT.md)
- Current published diagnostic snapshot:
  read [Current Internal Diagnostic Benchmark Snapshot](GROUNDING_BENCHMARK_SNAPSHOT.md)
- Publication note:
  publication claims are only current when the selected report, generated
  snapshot docs, tables, graphs, and supporting governance truth are refreshed
  together from the same validated tree

## Developer-Priority Order

The benchmark is ordered the way a developer reads it, not the way a benchmark
author sorts by token delta.

| Archetype | Tracked Evals | Families | Current Read |
| --- | ---: | --- | --- |
| Bug Fixes | 8 | `validation_heavy_fix`, `stateful_bug_recovery`, `browser_surface_reliability`, `cli_contract_regression` | Stronger now because it includes real stateful recovery and not just isolated bug-fix slices. |
| Multi-File Features | 9 | `cross_file_feature`, `merge_heavy_change`, `api_contract_evolution` | Better representation of real feature and contract-evolution work spanning code, tests, and docs. |
| Runtime / Install / Security | 9 | `install_upgrade_runtime`, `agent_activation`, `daemon_security`, `consumer_profile_compatibility`, `external_dependency_recovery`, `runtime_state_integrity` | Now includes external wait/resume and dependency recovery instead of only local runtime repair. |
| Surface / UI Reliability | 2 | `dashboard_surface`, `compass_brief_freshness` | Browser-backed operator behavior stays visible as product work, not decorative HTML churn. |
| Docs + Code Closeout | 5 | `docs_code_closeout`, `governed_surface_sync`, `cross_surface_governance_sync` | Keeps code, docs, specs, and generated mirrors aligned. |
| Governance / Release Integrity | 9 | `component_governance`, `destructive_scope_control`, `live_proof_discipline`, `release_publication` | Now includes destructive-scope and fail-closed benchmark safety, not only publication truth. |
| Architecture Review | 5 | `architecture` | Keeps grounded design-review quality visible after direct implementation work. |
| Grounding / Orchestration Control | 35 | `broad_shared_scope`, `context_engine_grounding`, `execution_engine`, `guidance_behavior`, `discipline`, `exact_path_ambiguity`, `exact_anchor_recall`, `explicit_workstream`, `retrieval_miss_recovery`, `orchestration_feedback`, `orchestration_intelligence` | Explains how Odylith stays bounded on real coding work without pretending that control-plane metrics are the headline product claim. |

## Current Published Attention Areas

Current proof families still worth attention after the latest passing published
proof:

- `architecture`
- `browser_surface_reliability`
- `component_governance`
- `cross_surface_governance_sync`
- `governed_surface_sync`
- `orchestration_feedback`

Current diagnostic weak families:

- `browser_surface_reliability`
- `install_upgrade_runtime`
- `runtime_state_integrity`

## Current Corpus-Hardening Additions

The current hardening wave made the benchmark more serious by adding:

- multi-file surface synchronization and guardrail carry-through cases
- explicit API and report-contract evolution cases
- stateful recovery cases with checkpoint and queued-state behavior
- external wait/resume cases with semantic receipts and preflight evidence
- destructive-scope cases where fail-closed execution matters

For packet-only diagnostic families, some scenarios now also declare a bounded
`benchmark.packet_fixture`. That fixture is not a free extra truth channel. It
exists only to seed the exact proof-state, routing, or external-state fields
that the scenario is explicitly testing in packet carry-through, and it stays
whitelisted to the packet/runtime-summary seam instead of reaching into hidden
repo context.

## Family Summary

| Family | Eval Count | Real-World Shape |
| --- | ---: | --- |
| `agent_activation` | 1 | install-time activation of guidance, skills, and grounded operator posture |
| `api_contract_evolution` | 3 | producer-consumer contract evolution across runner output, docs, and public surfaces |
| `broad_shared_scope` | 2 | fail-closed narrowing on broad shared paths without flooding context |
| `browser_surface_reliability` | 2 | shell and onboarding browser reliability with headless proof |
| `cli_contract_regression` | 1 | public CLI regression repair with unit-test-backed operator contract |
| `compass_brief_freshness` | 1 | freshness and reactivity of Compass brief generation |
| `component_governance` | 2 | Registry and Atlas alignment for benchmark or component truth |
| `consumer_profile_compatibility` | 1 | consumer config and truth-root compatibility repair |
| `context_engine_grounding` | 4 | Context Engine packet-lane selection, scope resolution, and fail-closed ambiguity behavior |
| `cross_file_feature` | 3 | multi-file implementation with bounded packet discipline |
| `cross_surface_governance_sync` | 2 | synchronized truth across backlog, plans, Registry, Atlas, and mirrors |
| `daemon_security` | 1 | Context Engine daemon transport, lifecycle, and local security hardening |
| `dashboard_surface` | 1 | shell-renderer and runtime drawer work |
| `destructive_scope_control` | 3 | fail-closed destructive-command and destructive-subset blocking |
| `discipline` | 7 | hard-law, adaptive-stance, parity, silence, and learning-sovereignty pressure behavior on real host contracts |
| `docs_code_closeout` | 2 | governed closeout where docs, specs, README, and code all have to agree |
| `exact_anchor_recall` | 1 | dense grounded packets on exact workstream and path anchors |
| `exact_path_ambiguity` | 2 | exact-path boundedness even when historical fanout is ambiguous |
| `execution_engine` | 9 | Execution Engine contract posture, canonical identity hard cut, truthful next-move carry-through, fail-closed recovery, wait/resume behavior, host parity, consumer-lane guard posture, snapshot reuse, and hot-path cost measurement |
| `explicit_workstream` | 1 | explicit workstream grounding with compact route-ready packet shape |
| `external_dependency_recovery` | 3 | semantic waits, resumability, and external-state carry-through into public surfaces |
| `governed_surface_sync` | 1 | lifecycle closeout propagation across governed surfaces |
| `guidance_behavior` | 6 | high-risk guidance pressure cases around grounding, CLI-first truth, proof claims, delegation contracts, and visible intervention proof |
| `install_upgrade_runtime` | 2 | install or upgrade regressions across runtime activation and release truth |
| `live_proof_discipline` | 2 | live blocker proof control, claim-tier enforcement, and no-fake-precision packet behavior |
| `merge_heavy_change` | 3 | coordination-heavy multi-owner change with validation pressure |
| `orchestration_feedback` | 1 | closed-loop advisory posture for routing and leaf shaping |
| `orchestration_intelligence` | 1 | delegation and inspection-ledger visibility as system behavior |
| `release_publication` | 2 | release-safe benchmark publication, graphs, README, and comparison honesty |
| `retrieval_miss_recovery` | 1 | bounded sparse widening after retrieval misses |
| `runtime_state_integrity` | 1 | runtime state JSON/JS companion correctness across repo postures |
| `stateful_bug_recovery` | 3 | recovery after stale, interrupted, or contradictory runtime state |
| `validation_heavy_fix` | 2 | correctness-sensitive bug-fix work with strong validator pressure |
| `architecture` | 5 | grounded architecture dossier and design-review quality |

## Representative Evals

| Family | Representative Evals |
| --- | --- |
| `agent_activation` | `install-time-agent-activation-contract` |
| `api_contract_evolution` | `benchmark-live-comparison-contract-and-report-schema`, `live-observed-path-attribution-contract-parity`, `program-wave-and-release-authoring-status-schema` |
| `broad_shared_scope` | `broad-shared-guarding`, `session-brief-broad-shared-guarding` |
| `browser_surface_reliability` | `shell-and-compass-browser-reliability`, `tooling-dashboard-onboarding-browser-contract` |
| `cli_contract_regression` | `cli-install-first-run-onboarding-contract` |
| `compass_brief_freshness` | `compass-brief-freshness-and-reactivity` |
| `component_governance` | `benchmark-component-governance-truth`, `benchmark-component-honesty-governance` |
| `consumer_profile_compatibility` | `consumer-profile-truth-root-compatibility` |
| `context_engine_grounding` | `context-engine-split-adaptive-grounding`, `context-engine-governance-boundary-grounding`, `context-engine-broad-scope-fail-closed`, `context-engine-release-resolution-grounding` |
| `cross_file_feature` | `cross-file-feature-budget-discipline`, `benchmark-taxonomy-and-heatmap-family-order-evolution`, `tooling-dashboard-shell-render-contract` |
| `cross_surface_governance_sync` | `cross-surface-governance-sync-truth`, `benchmark-corpus-expansion-mirror-integrity` |
| `daemon_security` | `context-engine-daemon-security-hardening` |
| `dashboard_surface` | `dashboard-shell-optimization-surface` |
| `destructive_scope_control` | `resource-closure-destructive-subset-blocking`, `codex-bash-guard-destructive-command-blocking`, `claude-bash-guard-destructive-command-blocking` |
| `discipline` | `discipline-hard-law-zero-credit`, `discipline-unknown-pressure-adaptive-stance`, `discipline-host-lane-parity-matrix`, `discipline-benchmark-sovereignty-public-claim` |
| `docs_code_closeout` | `docs-code-governed-closeout`, `benchmark-docs-and-readme-closeout` |
| `exact_anchor_recall` | `exact-workstream-anchor-density` |
| `exact_path_ambiguity` | `runtime-path-ambiguity`, `session-brief-runtime-path-ambiguity` |
| `execution_engine` | `execution-engine-contract-verify-closure-discipline`, `execution-engine-runtime-surface-phase-carry-through`, `execution-engine-router-recovery-posture`, `execution-engine-claude-external-wait-resume`, `execution-engine-historical-id-fails-closed` |
| `explicit_workstream` | `wave3-explicit-workstream` |
| `external_dependency_recovery` | `github-actions-semantic-wait-and-resume-token-contract`, `live-preflight-evidence-disposable-workspace-contract`, `runtime-surface-wait-status-carry-through` |
| `governed_surface_sync` | `closeout-surface-path-normalization` |
| `guidance_behavior` | `guidance-ground-before-broad-search`, `guidance-cli-first-governed-truth`, `guidance-fresh-proof-completion-claim`, `guidance-visible-intervention-proof` |
| `install_upgrade_runtime` | `consumer-install-upgrade-runtime-contract`, `managed-runtime-repair-and-rollback-contract` |
| `live_proof_discipline` | `live-proof-frontier-verified-control-panel`, `live-proof-no-fake-precision-without-a-lane` |
| `merge_heavy_change` | `merge-heavy-router-doc-sync`, `compass-wave-and-release-posture-surface-sync`, `subagent-routing-and-remediator-guardrail-carry-through` |
| `orchestration_feedback` | `orchestration-control-advisory-loop` |
| `orchestration_intelligence` | `orchestrator-ledger-closeout` |
| `release_publication` | `release-benchmark-publication-proof`, `benchmark-raw-baseline-publication-contract` |
| `retrieval_miss_recovery` | `wave4-runtime-sparse-miss-recovery` |
| `runtime_state_integrity` | `product-runtime-state-js-companion-contract` |
| `stateful_bug_recovery` | `benchmark-progress-checkpoint-and-resume-recovery`, `compass-refresh-queued-state-recovery`, `execution-engine-contradiction-reanchor-recovery` |
| `validation_heavy_fix` | `validation-heavy-router-fix`, `benchmark-raw-baseline-runner-gate` |

## Architecture Dossier Evals

These come from `architecture_scenarios` rather than the implementation-family
list:

- `architecture-odylith-self-grounding`
- `architecture-context-engine-split-boundary-contract`
- `architecture-release-install-runtime-boundary`
- `architecture-benchmark-proof-publication-lane`
- `architecture-benchmark-honest-baseline-contract`

## Interpretation Notes

- This catalog exists to make benchmark scope inspectable before anyone trusts
  the scorecard.
- When a no-op benchmark result is justified by focused preflight evidence
  instead of the broad validator lane, the report now marks that explicitly as
  `validator_status_basis=focused_noop_proxy` so reviewers can see the real
  basis instead of mistaking it for an ordinary validator pass.
- The corpus is still repo-grounded and Odylith-shaped, but it now has enough
  validator-backed feature, recovery, and destructive-scope work to support a
  more serious coding-agent claim.
- Governance and architecture cases stay in the corpus because they are real
  product truth, but they no longer dominate the benchmark story or the
  seriousness floor.
