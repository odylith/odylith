- Bug ID: CB-336

- Frozen Checkpoint Verification (2026-09-09): The final frozen gate passes all 5,002 runtime checks, including the unchanged hotfile guard, plus 1,168 install checks, 340 browser checks (one fixture-specific skip), ten current-record desktop/mobile checks and three root CLI checks. All 3,191 selected inputs are identical before, during and after the run; every process is terminal before the freeze is released. The previous size failure is resolved by duplicate-loop removal, not a waived limit. This qualifies the bounded source checkpoint; the full Greenfield release remains unqualified.

- Independent Structural Acceptance (2026-09-09): The consolidation passes 41 independent tests in 26.55 seconds, including fourteen hash-verified differential comparisons with the accepted collector and five ordering/default/cache characterizations. No regression or scoring-policy change is found. Per-changed-path sharedness, direct-before-trace ordering, source kinds, duplicates and cached-row immutability hold. The fresh frozen integration gate remains required before a stable checkpoint.

- Structural Correction (2026-09-09): Consolidating the duplicate direct/traceability loops into one ordered typed evidence pass reduces the scope owner from 1,587 to 1,571 lines, below the unchanged 1,576 ceiling. Direct rows are copied and typed before unchanged traceability rows; cached rows, ordering, source-kind defaults, scoring and selection policy are preserved. Five characterization checks pass before the consolidation; the final focused set passes 227 checks in 83.53 seconds, the entire hygiene module passes 56, and the independent set passes 22. Fourteen independent probe outputs are byte-identical to the accepted semantic correction. Independent equivalence review and a fresh frozen integration gate remain required. This removes real duplication; it does not resolve the pre-existing oversized-owner debt.

- Frozen Integration Gate (2026-09-09): All 3,191 selected files remain identical across the full run. Runtime passes 4,996 checks and fails one structural guard because the scope owner grew to 1,587 lines above its pinned 1,576-line ceiling. All ten prior runtime failures are cleared by the integrated corrections; the new size failure is not waived. Install passes 1,168, browser passes 340 with one fixture-specific skip, and current-record readback passes ten desktop/mobile controls. Remove real duplication or move a cohesive path-evidence phase into its existing owner, preserving the reviewed meaning and the pinned ceiling. Run the existing hygiene guard before another expensive gate; a documented size exception alone did not satisfy this stricter maintained inventory.

- Independent Revised Acceptance (2026-09-09): Re-review resolves the earlier P1 with no remaining actionable finding in this bounded patch. Twenty-two independent checks pass in 13.13 seconds, plus fourteen baseline/current probe replays. Overlapping support, per-changed-path locality, cached requests, genuine ownership, explicit overrides and memory boundaries hold. Collector complexity remains O(references times changed paths), with one additional supporting-reference matching pass. This is source-level acceptance, not measured consumer latency, full runtime or release qualification.

- Matched-reference Correction (2026-09-09): Shared support is now derived per changed path using the existing normalized path matcher, so overlapping directory and exact-file references agree about sharedness. The rejected equal-target grouping is removed. All 43 added overlap/locality/authority controls fail before that correction and pass afterward; the combined focused suite passes 222 checks in 83.35 seconds. Dedicated paths, unrelated subtrees, exact code/contract/direct ownership, explicit overrides and valid memory remain supported. The total source delta is 16 insertions and 3 deletions; no new scoring layer or filename rules are introduced. Independent re-review and frozen broader validation still gate acceptance.

- Independent Candidate Rejection (2026-09-09): The first relationship-based candidate still keys sharedness by equal target paths. Independent real-collector proof uses one directory-level doc reference and two doc/runbook references to a changed file beneath it. Baseline scores 98/77/72 remain ambiguous, but the candidate demotes only the exact-file supporters and manufactures a confident directory supporter at 98/-63/-65 with zero strong signals. Cold and cached results agree. This is a new regression, not an expected-output update. Derive shared supporting ownership from the references that actually match each changed path, preserving unrelated subtrees and genuine ownership. Do not accept the 179-pass count as class-level proof; broader validation remains held until independent re-review.

- Rejected Candidate Focused Proof (2026-09-09): Distinct valid owners of normalized typed doc/runbook references supplied the existing shared-evidence path; component and diagram associations remained available. Memory confirmation requires current non-shared or strong evidence, retaining the existing ambiguity classifications. Typed shared documentation under source directories cannot acquire implementation strength from its location. The first source candidate changed by 14 insertions and 3 deletions; its equal-target grouping failed independent review as recorded above.

- Causal Controls (2026-09-09): On the old source, 147 shared-support controls fail while seven genuine ownership controls pass; the additional source-directory support case also fails. The final focused run passes 179 controls in 65.61 seconds. A provenance-only comparison retains identical paths and memberships: removing shared provenance yields scores 146/110/74 and a confident choice; retaining it yields 9/-27/-63 and ambiguity. Independent review and a fresh full runtime/install/browser gate remain required; this is not release qualification.

- Status: Open

- Created: 2026-09-09

- Severity: P1

- Reproducibility: Consistent

- Type: Product

- Description: A document referenced by several workstreams is useful shared context, but accumulated component memberships can turn that shared support into a confident unique workstream selection with zero strong ownership signals.

- Impact: Odylith can recommend a single governed workstream and remove narrowing guidance even when the changed document does not identify an exclusive owner.

- Components Affected: odylith-context-engine

- Environment(s): Product-repo maintainer source-local proof after grounded traceability updates to 25 active plans.

- Detected By: Frozen runtime integration failures and independent controlled projection comparison.

- Failure Signature: One shared runbook gives three candidates score 74; unequal broad component memberships produce scores 146, 110 and 74 and inferred_confident with zero strong candidates.

- Trigger Path: Context Engine governance-slice and session-brief preparation for documentation-only changed paths; test_governance_slice_hot_path_limits_operator_payload_lists and related controls.

- Ownership: Context Engine typed path evidence and workstream selection.

- Timeline: Captured 2026-09-09 through `odylith bug capture`.

- Blast Radius: Governance packets, recommended workstream scope, route readiness and downstream execution guidance across both host adapters.

- SLO/SLA Impact: Misroutes work and undermines bounded reliable integration; no consumer latency exception is permitted.

- Data Risk: No incorrect governed write observed in the probe; inferred scope can direct downstream work to the wrong records.

- Security/Compliance: Safety risk is incorrect execution scope; no credential exposure or native trust mutation occurred in the probe.

- Invariant Violated: Shared supporting evidence and broad component memberships must not establish exclusive workstream ownership.

- Root Cause: Runbook and documentation evidence is classified as non-shared by filename rather than its actual cross-workstream relationships; component score additions manufacture the required selection gap.

- Solution: Preserve typed supporting-reference provenance and its shared ownership before selection; retain explicit overrides, exact implementation or contract evidence and independently established dedicated documentation ownership.

- Verification: All nine original context failures reproduce in 6.70 seconds. Removing only 109 added traceability tuples in a copied projection restores weak ambiguous behavior; no repository files are reverted. Add renamed-runbook, unequal-component, duplicate-reference and order controls, plus explicit-owner and genuine code or documentation ownership positives.

- Agent Guardrails: Do not add filename lists, scenario IDs, a new scoring system, or disable all weak context. Do not delete valid plan links or change old expected IDs to the new wrong winner. Keep corpus support declarations separate from this product defect.

- Related Incidents/Bugs: CB-046, CB-072, CB-119, CB-334

- Code References: - src/odylith/runtime/context_engine/odylith_context_engine_hot_path_scope_runtime.py
- src/odylith/runtime/context_engine/odylith_context_engine_hot_path_runtime.py
