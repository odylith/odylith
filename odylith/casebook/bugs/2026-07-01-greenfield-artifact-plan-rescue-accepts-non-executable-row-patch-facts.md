- Bug ID: CB-213

- Status: FixedPendingRelease

- Created: 2026-07-01

- Severity: P2

- Reproducibility: Always

- Type: Product

- Description: Greenfield artifact-plan rescue accepts non-executable row patch facts

- Impact: Confirmed greenfield create can enter the 90-second rescue path, receive a valid host-planned Registry projection repair, and still fail before governed records are written because the artifact-plan executor cannot materialize the replacement fact onto the targeted component row.

- Components Affected: domain-intelligence

- Environment(s): Installed consumer lane on Odylith 0.1.15 local release a4d30f6a, reproduced from source-local maintainer diagnosis with the saved confirmed intent.

- Detected By: User live repro in /Users/freedom/mock/gene-expression-prediction plus maintainer replay in disposable temp repo using the installed launcher.

- Failure Signature: Final blocker: Registry component spec Results Review Workspace has modal/base-form grammar drift near to flags; manifest pass 0 and pass 1 both report component_contract_quality, package_changed=false, while last_repair_patchset_request contains replacement_fact results-review-workspace -> review predictions with QC flags, uncertainty, and downloadable outputs.

- Trigger Path: Run odylith greenfield create --repo-root <repo> --prompt <confirmed request> --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release 0.0.1 --repair-tier auto --json on the saved confirmed intent.

- Ownership: Domain Intelligence post-confirm package findings, Tribunal structured patch planner materialization, ArtifactPlanIR patch executor, Registry projection rerender custody, and final package quality gates.

- Timeline: Captured 2026-07-01 through `odylith bug capture`.

- Blast Radius: Any greenfield domain where a rendered Registry component spec quality failure maps to projection-level Registry repair instead of an exact component row and field; rescue can spend time and return no executable change.

- SLO/SLA Impact: Standard path remains under 60 seconds for clean cases, but repairable Registry failures can consume rescue time near 90 seconds and still write no governed records.

- Data Risk: Fail-closed transaction prevents bad governed records from being written; accepted product intent remains saved but unmaterialized.

- Security/Compliance: Compliance, policy, privacy, accessibility, and safety posture are protected by fail-closed writes, but release evidence remains incomplete until typed repair facts can be applied without mutating rendered prose or bypassing review gates.

- Invariant Violated: A rescue PatchSet accepted as planned must be executable against a sanctioned SemanticModelIR or ArtifactPlanIR source fact, or it must be rejected before the next pass rather than rerun unchanged.

- Root Cause: The first failure was not the gene-expression project. Odylith collapsed a rendered Registry spec quality defect to `prewrite_package.registry`, so the PatchSet repair target was not an executable ArtifactPlanIR path. After package findings were source-addressed to `components[3].component_contract.produced_outputs`, the host planner could still time out, proving the localized contract-output repair should not require host reasoning. When the deterministic contract patch first applied, the proposal row and `semantic_model.components` mirror drifted because the patch executor updated only one copy of the component contract fact.

- Failed Mechanisms: Re-running rescue with the same projection-level `prewrite_package.registry` path produced `package_changed=false`; accepting a host-planned compact component-key fact without row materialization did not guarantee a source mutation; relying on a 45-second host planner for an already localized component contract defect breached the low-latency rescue objective; patching only `proposal.components[].component_contract` created a `GreenfieldSemanticModel` drift failure before governed writes.

- Fix: Registry package findings now map rendered component spec failures back to the exact component contract ArtifactPlanIR path when the rendered spec key matches exactly one proposal component row. The ArtifactPlanIR patch executor now supports nested row paths, compact row-keyed registry patches, and atomic synchronization from changed component contract fields into `semantic_model.components`. The rescue planner now fills deterministic source-derived replacement facts for localized component contract output paths before invoking host reasoning, leaving host planning for ambiguous semantic repairs.

- Verification: Source-local replay of the saved `/Users/freedom/mock/gene-expression-prediction` confirmed intent now writes governed records in 29.797s whole-project time. The manifest passed after 2 passes, repaired `component_contract_quality`, committed 4 workstreams, 5 components, 6 diagrams, and reported zero final issues. Focused regression proof passed `test_greenfield_artifact_plan_patch_executor.py` (9 tests), selected prewrite/package finding tests (2 tests), selected proposal quality-gate tests (2 tests), `test_greenfield_preconfirm_patch_payload.py` deterministic repair tests, the broader post-confirm pack (48 tests), and semantic drift/pass fixtures (2 tests). No `to flags` or related repair diagnostic leaked into generated Radar, Registry, Atlas, or project brief artifacts.
