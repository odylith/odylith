- Bug ID: CB-350

- Status: FixedPendingRelease

- Created: 2026-09-30

- Severity: P2

- Reproducibility: Always

- Type: Product

- Description: The public Greenfield operating-envelope document advertises envelope v5, model-profile v23, and authoring v68. The active runtime constants are envelope v6, model-profile v24, and authoring v77. Several named profile IDs and authoring-review statements in that document are historical.

- Impact: Operators cannot use the public document to determine the supported current Greenfield input and model profile, so release claims are not auditable from the published specification.

- Components Affected: domain-intelligence

- Environment(s): Odylith product-repo maintainer branch 2026/freedom/v0.1.15 at f03f7f6a2, detached source-local posture.

- Detected By: Direct comparison of published specification and runtime constants during Greenfield release audit.

- Failure Signature: docs/specs/greenfield-operating-envelope.md declares v5/v23/v68 while greenfield_operating_envelope.py, greenfield_model_profile_contract.py, and greenfield_model_intent_authoring.py declare v6/v24/v77.

- Trigger Path: Read docs/specs/greenfield-operating-envelope.md beside the three active runtime contract modules.

- Ownership: Domain-intelligence Greenfield contract and public product documentation.

- Timeline: Captured 2026-09-30 through `odylith bug capture`.

- Blast Radius: Every operator or release reviewer relying on the public envelope document.

- SLO/SLA Impact: Blocks an evidence-backed production release claim until documentation and runtime agree.

- Data Risk: No observed governed data mutation.

- Security/Compliance: No direct security failure observed; stale claims could misstate supported safety boundaries.

- Invariant Violated: The published supported envelope and pinned model profile must describe the active executable contract.

- Workaround: Treat executable v6/v24/v77 constants as current and withhold release qualification until the public document is reconciled.

- Related Incidents/Bugs: CB-324: public semantic gate remains red independently of this documentation defect.

- Code References: - docs/specs/greenfield-operating-envelope.md
- src/odylith/runtime/domain_intelligence/greenfield_operating_envelope.py
- src/odylith/runtime/domain_intelligence/greenfield_model_profile_contract.py
- src/odylith/runtime/domain_intelligence/greenfield_model_intent_authoring.py

- Fixed: 2026-09-30

- Fixed In: 0.1.15

- Solution: The public document now describes envelope v6, profile v24,
  current host candidate and canonical authoring versions, the one gate and
  candidate flow, deterministic sealing, exact source context custody, and
  the current support and timing boundaries. Historical experiments remain
  labeled historical.

- Verification: A runtime-to-document marker check passed for the active
  envelope, profile IDs, authoring, semantics, and host format. Independent
  rereview found the document accurate against the current contract. That
  rereview separately found a closed profile-evidence schema defect in the
  new timing observation; CB-346 owns that fix. Public semantic qualification
  remains blocked by CB-324.
