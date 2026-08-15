- Bug ID: CB-325

- Status: Open

- Created: 2026-08-15

- Severity: P1

- Reproducibility: Consistent

- Type: DataLoss

- Description: A frozen Greenfield final-holdout corpus and its evaluation-split manifest were kept only in temporary filesystem roots. Both immutable inputs disappeared before the one-shot ledger was claimed, leaving only expected hashes and no recoverable bytes. The release gate could not execute or adjudicate the authorized candidate and required explicit operator authorization for a genuinely new replacement split.

- Impact: Blocks release adjudication and destroys the evidentiary object needed to prove an untouched final holdout; no product or customer data is affected.

- Components Affected: release

- Environment(s): Odylith product-repo maintainer release lane on macOS; pre-disclosure Greenfield semantic holdout stored under /private/tmp.

- Detected By: Preflight existence and SHA-256 verification before final-holdout ledger claim.

- Failure Signature: Final holdout path and evaluation manifest path both absent; exhaustive filename/hash/recovery search found no byte-identical copy; one-shot ledger remained absent.

- Trigger Path: Prepare a frozen holdout and manifest only under temporary roots, defer execution, then re-enter release preflight after temporary storage is cleaned or expires.

- Ownership: Release evidence custody and Greenfield final-holdout preflight.

- Timeline: Observed before product execution on 2026-08-15. Expected holdout and manifest hashes were known, both paths were absent, and the ledger had never been created. Recovery searches found no copy. Operator authorized a replacement frozen holdout.

- Blast Radius: Any release candidate whose sole undisclosed final-holdout inputs are stored in volatile temporary roots.

- SLO/SLA Impact: Release closure is blocked until an explicitly authorized, independently authored replacement holdout is frozen and consumed once.

- Data Risk: Loss of release-evaluation evidence only; no customer, production, or governed product data loss.

- Security/Compliance: No secret or PII exposure observed; integrity and auditability are degraded because the sealed evidence bytes are unavailable.

- Invariant Violated: A frozen undisclosed final holdout and manifest must remain hash-verifiable under durable custody from freeze through terminal ledger completion and independent adjudication.

- Workaround: Retire the unrecoverable split by hash and create a genuinely new independent split only after explicit operator authorization.

- Root Cause: The only copies were placed in volatile /private/tmp locations with no durable custody root, redundant immutable copy, or pre-run availability guard.

- Solution: Store replacement inputs in durable ignored Odylith runtime state, freeze and hash them before execution, keep the one-shot ledger outside the sealed-input root, retain terminal result/adjudication artifacts, and require exact existence/hash preflight before ledger claim.

- Rollback/Forward Fix: Forward-fix only; the lost bytes cannot be reconstructed without invalidating blindness.

- Verification: A replacement corpus and manifest are independently authored and reviewed, contract validation passes, their hashes remain stable through the exact one-shot run, and the terminal ledger plus result and adjudication artifacts remain readable after temporary campaign cleanup.

- Prevention: Add a durable release-evidence custody contract that rejects final-holdout paths under volatile temporary roots unless a verified durable immutable copy exists.

- Agent Guardrails: Never reconstruct a lost holdout from hashes, prior notes, or retired cases; never claim the ledger before all frozen-input and candidate provenance checks pass; require explicit authorization before replacing an unrecoverable split.

- Preflight Checks: Verify durable holdout, manifest, tracked corpus, distribution provenance, implementation revision, absent fresh ledger, and independent review receipt by SHA-256 before one-shot execution.

- Version/Build: Odylith 0.1.15 candidate 1ba7b4c0385ed36981c5d163439a49f3be703661

- Related Incidents/Bugs: CB-303, CB-312, CB-313, CB-314

- Code References: - scripts/release/greenfield_final_holdout_guard.py
- scripts/release/greenfield_evaluation_contract.py
- scripts/release/greenfield_matrix_campaign_runner.py
