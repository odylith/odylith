- Bug ID: CB-353

- Status: Open

- Created: 2026-10-02

- Severity: P2

- Reproducibility: Always

- Type: Test

- Description: The installed civic v10 discovery matrix failed source-ledger preflight before verification or package creation, yet onboarding_quality_scorecard evidence says one non-clarification case compiled a usable transaction and one committed case exposes completed governance surfaces. The score is zero, but the explanatory evidence contradicts the retained case result.

- Impact: Release reviewers can mistake a failed pre-confirm attempt for a committed package when reading scorecard evidence.

- Components Affected: domain-intelligence-greenfield

- Environment(s): Product repo source-local release matrix, 2026-10-02, unchanged public civic case 057

- Detected By: Readback of retained installed v10 matrix result

- Failure Signature: case status case-execution-exception and create_returncode 1 with scorecard evidence claiming a usable transaction and committed case

- Trigger Path: scripts/release/greenfield_preconfirm_matrix.py discovery run followed by build_onboarding_quality_scorecard

- Ownership: Greenfield installed release evaluation and scorecard narration

- Timeline: Captured 2026-10-02 through `odylith bug capture`.

- Blast Radius: Failed non-clarification matrix cases and release reviewers

- SLO/SLA Impact: Release-evidence trust; no consumer transaction latency impact

- Data Risk: No data mutation; misleading evidence text only

- Security/Compliance: No direct security impact; audit claim accuracy affected

- Invariant Violated: Release evidence must describe observed completion, not intended case expectation.

- Root Cause: The scorecard names every non-clarification case a committed transaction and emits unconditional success prose while the failure scores remain zero.

- Solution: Use neutral selected-case wording and conditional observed results; add a failed-case regression.

- Verification: A failed preflight case must produce score zero with no statement that a transaction compiled, committed, or passed.

- Related Incidents/Bugs: CB-324 public semantic gate failure exposed this scorecard defect.

- Code References: - scripts/release/greenfield_onboarding_quality_scorecard.py

## Source-local repair evidence (2026-10-02)

Scorecard evidence now reports observed per-check pass counts over selected
transaction cases. It no longer describes a selected non-clarification case as
compiled or committed. A regression supplies a failed-before-preflight case
with zero completion and asserts the narrative cannot claim publication.
The focused scorecard suite passes `10/10`. Replaying the retained civic v10
result through the revised source-local scorecard still reports `failed`, with
`0/1` passing operator-usefulness and implementation-prompt checks and no
compiled/committed claim. The installed release report has not been rebuilt;
keep this record open until an installed run proves the corrected narration.
