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

- Preclaim Recovery Finding (2026-08-15): The independently authored replacement holdout passed two review rounds, exact contract validation, tracked and retired duplicate checks, platform-custody preflight, and exact-candidate checksum proof, then the campaign runner rejected its durable external evaluation manifest during semantic input sealing because `manifest_path.relative_to(repo_root)` raised `ValueError`. The exclusive run ledger remained absent, product execution count remained zero, and the empty temporary parent was removed, so the holdout was not consumed. The unchanged read-only bytes were mirrored under the clean worktree's ignored `.odylith/runtime/release/` tree for the repo-relative execution contract while the independently hashed durable copy, authoring source, reviews, custody receipt, and ledger destination remained outside temporary storage. This exposes a contract tension: durable external custody is necessary, but the current sealer requires a repo-relative execution copy and fails with a raw path exception instead of a preflight finding.

- Replacement Custody Verification (2026-08-16 UTC): The authorized replacement was frozen under the durable evidence root with holdout SHA-256 `082a92fe9aea18a5ea2b88eefa5aae7853277119b8aa600251c24a4a4bfc45d9`, manifest SHA-256 `40538d4100d9b2b8685c81c6680046ab179f971909db053c975841c66d8d2cb5`, and independent freeze-review SHA-256 `0d5dc2b13a1dd77bef0eeb9ccb483d29ed8cb5aee01ad6372119869f327f7761`. The one-shot ledger reached terminal `failed`, bound exact candidate `1ba7b4c0385ed36981c5d163439a49f3be703661` to result SHA-256 `180437fd4000e8c46eefe19b1e44c0fce14fb53e6666bf18838a1894d7a2a988`, and remains durable with ledger SHA-256 `f55dae956631f50474c2b8c6e99a91e8719a3998fbe22965934c7f8b8e40a09f`. Independent run adjudication (`fa81048b515bdc0db98fd04c6ce8205ee7964e5ee5be9d862d0ce191f308838d`) verified every binding and marked the campaign temp parent cleanup-safe. The corpus is consumed, disclosed, and must be retired as regression evidence. This proves the replacement workaround, but CB-325 remains open because durable custody and external-manifest preflight are still procedural rather than a first-class fail-closed product contract.

- Code References: - scripts/release/greenfield_final_holdout_guard.py
- scripts/release/greenfield_evaluation_contract.py
- scripts/release/greenfield_matrix_campaign_runner.py
