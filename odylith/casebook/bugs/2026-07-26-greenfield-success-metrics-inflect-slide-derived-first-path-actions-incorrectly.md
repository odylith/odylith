- Bug ID: CB-293

- Status: Open

- Created: 2026-07-26

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: Slide-form product evidence can recover a coherent typed first path with a modal actor clause, but confirmed-intent completion renders the first success metric from an actor-led sentence. The metric says an evaluator exports instead of proving the capability to export, weakening the first-path contract and dropping the expected actionable phrase from the root workstream.

- Impact: The proposal can pass structural checks while a core success metric becomes less actionable and less faithful to the accepted first path.

- Components Affected: greenfield-governance

- Environment(s): Product-repo maintainer source-local proof

- Detected By: Focused prewrite transaction regression suite

- Failure Signature: Slide-style proof metric omits the accepted base-form action phrase despite the typed first path containing it.

- Trigger Path: greenfield proposal completion from slide-form evidence with a modal first workflow

- Ownership: Greenfield confirmed-intent completion and first-path metric projection

- Timeline: Captured 2026-07-26 through `odylith bug capture`.

- Blast Radius: Recovered slide-form prompts and any modal actor path projected into the root success metric.

- SLO/SLA Impact: Allows a lower-quality governed package to reach the pre-confirm tribunal.

- Data Risk: No committed-artifact loss; defect is limited to pre-confirm generated metric quality.

- Security/Compliance: Policy, privacy, accessibility, and safety assessment: no boundary change; degraded metric language can obscure the proof action but does not bypass any access or safety control.

- Invariant Violated: The root success metric must preserve the accepted first path as a clear, actionable capability and visible proof outcome.

- Root Cause: Metric projection chooses an actor-led finite sentence instead of the shared normalized action fragment from the typed first path.

- Solution: Generate the metric capability from the shared action-chain fragment so the metric retains base-form actions and the visible outcome before sealing.

- Rollback/Forward Fix: No rollback required because the defect is pre-confirm; repair the typed projection and keep the tribunal as the fail-closed boundary.

- Verification: The slide-form regression and focused prewrite suite retain export a reproducible evidence packet and exported reproducible evidence packet in the completed root metric.

- Prevention: Use the shared first-path action representation for capability metrics; do not derive metrics from actor-led display sentences.

- Agent Guardrails: Do not soften the semantic compiler or change the test to accept an inflected substitute.

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent_completion.py
- src/odylith/runtime/domain_intelligence/greenfield_first_path_fragments.py
