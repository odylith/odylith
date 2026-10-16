- Bug ID: CB-210

- Status: FixedPendingRelease

- Created: 2026-06-30

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: The raw generated Project Brief is grammatically acceptable, but package readback normalizes the whole Markdown record into one prose stream. That collapses a first-path bullet ending in a modal clause with the following indented Why rationale, producing a synthetic chunk like Programmers can publish accessible screening readiness - Why: A narrow first path keeps the first release testable and prevents broad platform drift. The release matrix correctly fails that normalized package with a 6/10 cap, while greenfield create itself reports issue_count 0 and commits records.

- Impact: A real installed greenfield create can write complete governed records while the independent release matrix later caps the artifact score at 6/10 for a Project Brief grammar finding, so operators can receive records that are not proven by the strongest package-quality lens.

- Components Affected: domain-intelligence

- Environment(s): Odylith maintainer installed local release dist odylith-local-release-0.1.15-2a389428 on macOS consumer-lane simulation

- Detected By: Fresh high-variance installed greenfield matrix with browser proof on 2026-06-30

- Failure Signature: film festival accessibility screening scored 6/10: Project brief project-brief.v1.md has coordinated modal grammar drift near and prevents; greenfield create manifest reported zero issues and committed records

- Trigger Path: scripts/release/greenfield_preconfirm_matrix.py --dist-dir odylith-local-release-0.1.15-2a389428 --case-file /tmp/odylith-fresh-variance-20260630-f853743a.json --include-browser-proof

- Ownership: Greenfield artifact package quality and post-confirm write-transaction custody

- Timeline: Captured 2026-06-30 through `odylith bug capture`. Fixed in
  source the same day by preserving Project Brief Markdown boundaries in
  package readback and adding persisted Project Brief text to the final
  greenfield write-transaction package gate.

- Blast Radius: Project Brief readback, release-matrix scoring, final greenfield quality gate parity, and any generated Markdown surface normalized before QA

- SLO/SLA Impact: Standard post-confirm latency stayed under 60s, but release readiness is blocked because premium artifact quality is not consistently enforced before write completion

- Data Risk: No user data exposure observed; risk is governed-record quality and operator trust

- Security/Compliance: No direct security control bypass observed; compliance risk is misleading release evidence for governed artifacts

- Invariant Violated: The final post-confirm gate and release matrix must evaluate the same generated artifact package boundaries before claiming governed records are release quality

- Root Cause: Rendered package quality normalized persisted Project Brief
  Markdown into one document-wide prose stream before sentence checks. That
  collapsed a valid first-path bullet and its following rationale into a false
  coordinated-modal grammar failure. Separately, the final greenfield create
  package gate did not include the persisted Project Brief record text, so the
  release matrix and write transaction were not evaluating the same artifact
  package.

- Solution: Preserve Project Brief Markdown boundaries when building rendered
  artifact readback units, while retaining normalization only for blankness
  checks. Include `odylith/runtime/source/project-brief.v1.md` in the final
  `GreenfieldCompletionPackage` so committed writes and release-matrix proof
  share the same Project Brief readback lens.

- Rollback/Forward Fix: Forward fix only; do not weaken modal grammar gates or add domain-specific vocabulary.

- Verification: Added focused package/readback parity coverage and reran the
  widened greenfield suite with 276 passing tests. Fresh installed dist
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-clear-list-fix`
  passed the maintained release matrix: 13/13 standard cases at hard 10/10,
  max standard create 30.563s, average 27.854s, zero quality/browser/platform
  leakage issues, browser proof passed for every case, temp cleanup passed,
  synthetic rescue passed in 38.917s, and natural provider-backed structured
  rescue passed in 60.926s with governed writes committed.

- Prevention: Use typed artifact quality units and source-path custody for generated Markdown readback; avoid normalized whole-document prose checks when a surface has structured rows.

- Agent Guardrails: Do not repair by adding film festival vocabulary, weakening the coordinated modal detector, or stacking phrase exceptions. Repair boundary custody and quality-lens parity.

- Preflight Checks: Search CB-205, CB-208, and CB-209 before touching modal grammar or greenfield package quality; confirm prior failed mechanisms are not repeated.

- Monitoring Updates: Fresh high-variance installed matrix must remain the release monitor for this class

- Version/Build: dist odylith-local-release-0.1.15-2a389428; repo commit f853743a

- Config/Flags: include-browser-proof enabled; rescue proofs skipped for the fresh variance run

- Customer Comms: No public customer communication required before release

- Related Incidents/Bugs: CB-205, CB-208, CB-209

- Code References: - src/odylith/runtime/artifact_quality/greenfield_package_quality.py
- src/odylith/runtime/artifact_quality/greenfield_rendered_artifacts.py
- scripts/release/greenfield_preconfirm_matrix.py

- Runbook References: - B-142 greenfield typed semantic compiler and patchset repair plan
