- Bug ID: CB-226

- Status: FixedPendingRelease

- Fixed: Pending

- Created: 2026-07-10

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: Installed greenfield transaction compilation materializes a complete staged repository, then Atlas refresh validates staged catalog links against the original consumer target root. Valid staged backlog links are reported missing, creation-ready confirmation is withheld, and bounded repair retries repeat an infrastructure-invariant failure that semantic repair cannot change.

- Impact: Consumers cannot reach creation-ready confirmation for valid greenfield intent because every installed maintained case fails the pre-confirm Atlas surface proof. The commit-only post-confirm boundary remains protected and no governed records are written.

- Components Affected: domain-intelligence-greenfield

- Environment(s): Fresh consumer repos using committed local release dist 0.1.15 at 1b2072f0f; reproduced across the maintained installed greenfield post-confirm matrix and a preserved disposable staging root.

- Detected By: Installed release-tier greenfield-post-confirm matrix followed by preserved-stage direct Atlas refresh diagnosis.

- Failure Signature: Atlas catalog validation says every staged related_backlog path does not exist under the consumer target repo even though each file exists under the pre-confirm staging repo; the surface proof collapses the path evidence to a generic Atlas failed blocker.

- Trigger Path: make greenfield-post-confirm-matrix VERSION=0.1.15 DIST=/tmp/odylith-local-release-0.1.15-1b2072f0f; or compile a greenfield transaction in a fresh installed repo while preserving the prewrite staging root, then run atlas refresh against that root.

- Ownership: Domain Intelligence compiled Atlas catalog path custody and prewrite surface proof.

- Timeline: Captured 2026-07-10 through `odylith bug capture`.

- Blast Radius: All installed greenfield create flows that compile Atlas-linked governed packages before confirmation; all maintained release-matrix cases failed by the same mechanism.

- SLO/SLA Impact: Blocks first-run product creation before confirmation and exceeds the 60-second standard-path target through repeated no-progress repair passes.

- Data Risk: No governed target-repo writes occurred in observed failures; staged data is disposable. Risk is availability and operator trust, not application-data loss.

- Security/Compliance: No credential, private-data, or compliance exposure observed. Cross-repository path custody is an isolation invariant and must remain fail-closed.

- Invariant Violated: Every pre-confirm surface compiler must resolve repository-relative truth exclusively against the isolated staging root; confirmation must be withheld only for real package defects, and deterministic infrastructure failures must not enter semantic repair loops.

- Root Cause: The prewrite compiler rebased traceability paths to absolute consumer-target paths before sealing Atlas catalog rows. The staging root then materialized those target-bound catalog bytes exactly, so Atlas correctly rejected the links as missing inside the isolated staged repository. Replaying with `runtime_mode=standalone` produced the same failure and disproved runtime-daemon reuse as the mechanism.

- Solution: Compile Atlas `related_backlog` links as validated repository-relative paths. Reject links that resolve outside the target repository, preserve exact compiled catalog bytes across staging and commit, and remove the deterministic `Product product boundary` generator defect that had forced a model-backed pre-confirm copy repair in the same replay.

- Rollback/Forward Fix: Forward fix before further release proof; post-confirm commit-only semantics remain unchanged.

- Verification: Focused path-custody and slop tests passed. A source-local replay of the preserved flood-shelter intent compiled a creation-ready transaction in 35.86 seconds with quality and validation passed, 57 sealed writes, six Atlas previews, repository-relative backlog links, no patch ledger, and no model repair. The final confirmed command completed in 0.52 seconds and wrote four workstreams, three component specs, and six diagrams through the commit-only path. Committed-dist rebuild and full installed matrix replay remain release gates.

- Prevention: Keep governed catalog links repository-relative at the compiler owner, reject cross-root absolute paths before sealing, and exercise target and staging roots as intentionally different repositories in regression and installed release proof.

- Agent Guardrails: Do not move this failure after confirmation, bypass Atlas validation, lower the Tribunal, or ask the consumer to repair links. Fix stage-root custody before compiling the confirmation transaction.

- Preflight Checks: Before release proof, validate staged Atlas related_backlog links with target and staging roots intentionally different and assert diagnostics name the actual blocking path.

- Regression Tests Added: `test_prewrite_atlas_catalog_rebases_absolute_backlog_links_to_repo_paths`, `test_prewrite_atlas_catalog_rejects_backlog_links_outside_repo`, `test_prewrite_atlas_catalog_rejects_symlinked_backlog_escape`, prewrite-package relative-link assertions, installed apply traceability relative-link assertions, and `test_product_suffixed_project_label_does_not_trigger_atlas_copy_repair`.

- Monitoring Updates: Persist per-surface refresh stderr and retry classification in installed greenfield matrix evidence so no-progress infrastructure failures are visible.

- Version/Build: 0.1.15 local dist from commit 1b2072f0f

- Config/Flags: Both `runtime_mode=auto` and `runtime_mode=standalone` reproduced the failing build; runtime mode was not causal.

- Customer Comms: None before release; the defect was caught in maintainer installed-release proof.

- Related Incidents/Bugs: CB-038, CB-099, CB-173

- Fixed In: Pending 0.1.15 release proof

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_apply_diagrams.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_diagrams.py
- src/odylith/runtime/surfaces/render_mermaid_catalog.py
- tests/unit/runtime/test_greenfield_atlas_contract.py
- tests/unit/runtime/test_greenfield_confirmed_diagrams.py
- tests/unit/runtime/test_greenfield_prewrite_transaction.py
