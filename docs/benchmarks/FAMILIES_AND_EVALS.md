# Benchmark Families And Eval Catalog

This is the reader-facing map for Odylith's tracked benchmark corpus.

The source of truth is
`odylith/runtime/source/optimization-evaluation-corpus.v1.json`.

## Coverage At A Glance

- Tracked corpus:
  `33` implementation scenarios plus `4` architecture scenarios, `37` total
- Latest published proof snapshot:
  report `52aa3f76538cf12f`, status `provisional_pass`, `37` scenarios
- Latest published diagnostic snapshot:
  report `74cbe36427f2c375`, status `hold`, `37` scenarios

## Developer-Priority Order

The benchmark is ordered the way a developer reads it, not the way a benchmark
author sorts by token delta.

| Archetype | Tracked Evals | Families | Current Read |
| --- | ---: | --- | --- |
| Bug Fixes | 5 | `validation_heavy_fix`, `browser_surface_reliability`, `cli_contract_regression` | Strong developer story, but browser reliability and CLI regression handling are still live risks. |
| Multi-File Features | 2 | `cross_file_feature`, `merge_heavy_change` | Bounded multi-file implementation work with validation pressure. |
| Runtime / Install / Security | 6 | `install_upgrade_runtime`, `agent_activation`, `daemon_security`, `consumer_profile_compatibility`, `runtime_state_integrity` | High-value because install, activation, runtime integrity, and repair are real developer pain. |
| Surface / UI Reliability | 2 | `dashboard_surface`, `compass_brief_freshness` | Browser-backed product behavior, not static HTML edits. |
| Docs + Code Closeout | 5 | `docs_code_closeout`, `governed_surface_sync`, `cross_surface_governance_sync` | Keeps code, docs, specs, and mirrors aligned. |
| Governance / Release Integrity | 4 | `component_governance`, `release_publication` | Important to product truth, but not the first public developer story. |
| Architecture Review | 4 | `architecture` | Keeps grounded design-review quality visible after direct coding work. |
| Grounding / Orchestration Control | 9 | `broad_shared_scope`, `exact_path_ambiguity`, `exact_anchor_recall`, `explicit_workstream`, `retrieval_miss_recovery`, `orchestration_feedback`, `orchestration_intelligence` | Explains Odylith's mechanism without dominating the public story. |

## Current Published Attention Areas

Current proof families still worth attention after the passing full proof:

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

## Next Developer-Core Additions

The current expansion wave is biased toward developer-legible shapes:

- CLI contract regressions with direct unit-test proof
- consumer compatibility bugs
- runtime state integrity across consumer and product postures
- deeper install, repair, and rollback cases
- stateful browser-backed onboarding and shell behavior

## Family Summary

| Family | Eval Count | Real-World Shape |
| --- | ---: | --- |
| `agent_activation` | 1 | install-time activation of guidance, skills, and grounded operator posture |
| `broad_shared_scope` | 2 | fail-closed narrowing on broad shared paths without flooding context |
| `browser_surface_reliability` | 2 | shell and onboarding browser reliability with headless proof |
| `cli_contract_regression` | 1 | public CLI regression repair with unit-test-backed operator contract |
| `compass_brief_freshness` | 1 | freshness and reactivity of Compass brief generation |
| `component_governance` | 2 | Registry and Atlas alignment for benchmark or component truth |
| `consumer_profile_compatibility` | 1 | consumer config and truth-root compatibility repair |
| `cross_file_feature` | 1 | multi-file implementation with bounded packet discipline |
| `cross_surface_governance_sync` | 2 | synchronized truth across backlog, plans, Registry, Atlas, and mirrors |
| `daemon_security` | 1 | Context Engine daemon transport, lifecycle, and local security hardening |
| `dashboard_surface` | 1 | shell-renderer and runtime drawer work |
| `docs_code_closeout` | 2 | governed closeout where docs, specs, README, and code all have to agree |
| `exact_anchor_recall` | 1 | dense grounded packets on exact workstream and path anchors |
| `exact_path_ambiguity` | 2 | exact-path boundedness even when historical fanout is ambiguous |
| `explicit_workstream` | 1 | explicit workstream grounding with compact route-ready packet shape |
| `governed_surface_sync` | 1 | lifecycle closeout propagation across governed surfaces |
| `install_upgrade_runtime` | 2 | install or upgrade regressions across runtime activation and release truth |
| `merge_heavy_change` | 1 | coordination-heavy multi-owner change with validation pressure |
| `orchestration_feedback` | 1 | closed-loop advisory posture for routing and leaf shaping |
| `orchestration_intelligence` | 1 | delegation and inspection-ledger visibility as system behavior |
| `release_publication` | 2 | release-safe benchmark publication, graphs, README, and comparison honesty |
| `retrieval_miss_recovery` | 1 | bounded sparse widening after retrieval misses |
| `runtime_state_integrity` | 1 | runtime state JSON/JS companion correctness across repo postures |
| `validation_heavy_fix` | 2 | correctness-sensitive bug-fix work with strong validator pressure |
| `architecture` | 4 | grounded architecture dossier and design-review quality |

## Representative Evals

| Family | Representative Evals |
| --- | --- |
| `agent_activation` | `install-time-agent-activation-contract` |
| `broad_shared_scope` | `broad-shared-guarding`, `session-brief-broad-shared-guarding` |
| `browser_surface_reliability` | `shell-and-compass-browser-reliability`, `tooling-dashboard-onboarding-browser-contract` |
| `cli_contract_regression` | `cli-install-first-run-onboarding-contract` |
| `compass_brief_freshness` | `compass-brief-freshness-and-reactivity` |
| `component_governance` | `benchmark-component-governance-truth`, `benchmark-component-honesty-governance` |
| `consumer_profile_compatibility` | `consumer-profile-truth-root-compatibility` |
| `cross_file_feature` | `cross-file-feature-budget-discipline` |
| `cross_surface_governance_sync` | `cross-surface-governance-sync-truth`, `benchmark-corpus-expansion-mirror-integrity` |
| `daemon_security` | `context-engine-daemon-security-hardening` |
| `dashboard_surface` | `dashboard-shell-optimization-surface` |
| `docs_code_closeout` | `docs-code-governed-closeout`, `benchmark-docs-and-readme-closeout` |
| `exact_anchor_recall` | `exact-workstream-anchor-density` |
| `exact_path_ambiguity` | `runtime-path-ambiguity`, `session-brief-runtime-path-ambiguity` |
| `explicit_workstream` | `wave3-explicit-workstream` |
| `governed_surface_sync` | `closeout-surface-path-normalization` |
| `install_upgrade_runtime` | `consumer-install-upgrade-runtime-contract`, `managed-runtime-repair-and-rollback-contract` |
| `merge_heavy_change` | `merge-heavy-router-doc-sync` |
| `orchestration_feedback` | `orchestration-control-advisory-loop` |
| `orchestration_intelligence` | `orchestrator-ledger-closeout` |
| `release_publication` | `release-benchmark-publication-proof`, `benchmark-raw-baseline-publication-contract` |
| `retrieval_miss_recovery` | `wave4-runtime-sparse-miss-recovery` |
| `runtime_state_integrity` | `product-runtime-state-js-companion-contract` |
| `validation_heavy_fix` | `validation-heavy-router-fix`, `benchmark-raw-baseline-runner-gate` |

## Architecture Dossier Evals

These come from `architecture_scenarios` rather than the implementation-family
list:

- `architecture-odylith-self-grounding`
- `architecture-release-install-runtime-boundary`
- `architecture-benchmark-proof-publication-lane`
- `architecture-benchmark-honest-baseline-contract`

## Interpretation Notes

- This catalog exists to make benchmark scope inspectable before anyone trusts
  the scorecard.
- The corpus is still repo-grounded and Odylith-shaped, but the visible order
  now emphasizes developer-legible coding work first.
- Governance and architecture cases stay in the corpus because they are real
  product truth, but they no longer lead the public benchmark story.
