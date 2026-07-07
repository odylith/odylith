- Bug ID: CB-225

- Status: Open

- Created: 2026-07-07

- Severity: P1

- Reproducibility: Consistent

- Type: Product

- Description: Installed 120-case volume discovery against dist 0.1.15-051d6c1e stopped at procurement supplier risk board. Post-confirm generated previews but refused governed writes because the Radar package did not prove semantic coverage for SemanticModelIR.first_path_contract.

- Impact: Confirmed greenfield create can still fail after intent confirmation for a valid supplier-risk proposal, leaving no Radar, Registry, Atlas, release, project brief, or traceability records written.

- Components Affected: greenfield-post-confirm

- Environment(s): maintainer local dist /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-051d6c1e, installed matrix volume-discovery tier

- Detected By: greenfield matrix campaign volume-discovery 120-case fail-fast run

- Failure Signature: prewrite Radar package missing semantic coverage for first path; cluster manifest.semantic-alignment.semantic-model-compiler.radar.semanticmodelir-first-path-contract

- Trigger Path: GREENFIELD_MATRIX_VOLUME_CASE_FILES=... make greenfield-matrix-campaign VERSION=0.1.15 DIST=/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-051d6c1e

- Ownership: greenfield semantic model compiler and Radar projection contract

- Timeline: 2026-07-07: exact autonomous failed subset passed on 051d6c1e; follow-up 120-case volume run passed 46 cases and stopped on procurement supplier risk board at case hv-20260703-g-063.

- Blast Radius: Any post-confirm greenfield proposal whose typed first-path contract is not represented in Radar semantic coverage can fail before governed writes.

- SLO/SLA Impact: Violates the non-negotiable post-confirm completion objective for affected valid inputs.

- Data Risk: No governed records are committed; risk is availability and operator trust, not partial data mutation.

- Security/Compliance: No security boundary bypass observed; compliance-sensitive supplier-risk workflows cannot be created until fixed.

- Invariant Violated: After confirmed intent passes materiality and sufficiency gates, post-confirm compilers must compile typed first-path facts into all governed projection contracts or repair internally before write.

- Workaround: No user workaround. The platform must repair the semantic projection or coverage gate before rerun.

- Solution: Patch the generic Radar semantic projection or coverage owner so first_path_contract coverage is produced from typed facts, then replay the exact failed subset before resuming volume discovery.

- Rollback/Forward Fix: Forward fix only; rollback would reintroduce earlier post-confirm failures.

- Verification: Replay /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-051d6c1e/failed-subset-replay/failed-subset-001.cases.json, then rerun the 120-case volume campaign and strict release proof.

- Prevention: Add unit regression for supplier-risk first-path semantic coverage and keep the high-variance matrix as a release gate.

- Agent Guardrails: Do not mutate generated consumer projects; fix Odylith semantic projection and coverage contracts. Do not weaken the semantic-alignment gate.

- Preflight Checks: Read failed result JSON and failed-subset case file; verify no governed records were written before patching.

- Monitoring Updates: Matrix failure cluster captured for semantic-alignment telemetry.

- Version/Build: 0.1.15-051d6c1e

- Config/Flags: GREENFIELD_MATRIX_STOP_AFTER_FAILURES=1; GREENFIELD_MATRIX_STOP_AFTER_CLUSTER_FAILURES=1

- Customer Comms: Not public; internal maintainer hardening.

- GitHub Status: needs_info

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_post_confirm_package_findings.py
- src/odylith/runtime/domain_intelligence/greenfield_post_confirm_completion.py
- src/odylith/runtime/domain_intelligence/greenfield_semantic_compiler.py
