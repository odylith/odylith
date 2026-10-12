- Bug ID: CB-360

- Status: Open

- Created: 2026-10-12

- Severity: P1

- Reproducibility: Consistent

- Type: Product

- Description: The fresh installed case01 diagnostic seals its initial proposal, then rejects EDIT before source verification because the installed task and host reconstruction order the same seven required action keys differently. Eight pure processes reproduce the mismatch without provider calls. The original diagnostic remains failed; no edited candidate, commit or browser ran.

- Impact: Valid source-grounded EDIT can stop before verification and publication despite unchanged evidence.

- Components Affected: domain-intelligence

- Environment(s): Odylith maintainer installed b589 diagnostic, pinned Astra medium, independent installed and host Python processes.

- Detected By: Fresh genuine case01 initial-to-EDIT diagnostic followed by independent retained-artifact review and eight pure cross-seed reproductions.

- Failure Signature: Installed source ledger preflight lacks a bound decision task; prepare exits 2 after authority and inventory, before verifier or candidate.

- Trigger Path: odylith greenfield prepare with retained transaction hash, delivered completion receipt, exact original prompt and authorized edit; independent processes reconstruct source_duty_entailment_task.

- Ownership: Domain Intelligence source-duty task construction in greenfield_source_duty_entailment._prior_duties.

- Timeline: Captured 2026-10-12 through `odylith bug capture`.

- Blast Radius: EDIT preparation with accepted prior actions; initial task construction is not implicated by this reproduction.

- SLO/SLA Impact: Delivery risk: valid EDIT requests cannot complete when independent Python processes choose different task orders; no successful journey or timing qualification is earned.

- Data Risk: No observed data loss or edited publication. Refusal preserves the accepted prior record and blocks any candidate from gaining authority.

- Security/Compliance: Security checks fail closed on exact task equality. Privacy is preserved because no edited package is published; semantic and citation validation remain mandatory.

- Invariant Violated: Identical authenticated source, inventory and prior contract must construct identical canonical verifier tasks and digests across processes.

- Root Cause: _prior_duties enumerates ACTION_SECTIONS, a frozenset. Its insertion order becomes the JSON schema required array and changes the bound verifier task digest across Python hash seeds.

- Solution: Enumerate prior action sections in the existing deterministic declared section order. Preserve membership, all seven required keys, exact equality, hashes, limits and the single-pass stage sequence.

- Verification: The corrected owner passes 117 nearest tests, including original-code RED and corrected GREEN cross-process and mapping-order controls. Five distinct retained receipts verify exact bytes. Independent review CLEAR at /private/tmp/odylith-v52-edit-preflight-determinism-review-20261010/report.md. Original native failure remains failed; a corrected installed journey is required.

- Agent Guardrails: Do not set a global hash seed, relax task equality, increase limits, retry unchanged input or regrade the failed run.

- Version/Build: 0.1.15 development diagnostic at b589a31dceea749efe231862910a36e10c7cdd79

- Related Incidents/Bugs: B-142; CB-324 source custody; CB-347 release diagnostics; D-047 campaign progress.

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_source_duty_entailment.py
- src/odylith/runtime/domain_intelligence/greenfield_host_source_phase.py
