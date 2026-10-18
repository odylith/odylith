- Bug ID: CB-320

## Approved canonical metadata correction (2026-10-16)

The operator delegated the decision in response to the exact single-commit
correction and temporary account-exception request. The strict-lease replacement
completed: main now points to `9d3674c0a4384e76279d42985c862eaa712046f7`.
Its tree `1363fd148b7ae7cb7369a0aa6a210e90fd401336`, parent, message and
timestamps match the original merge; only maintainer author and committer
identity changed. The original failed merge and identity refusal remain retained.

Only the canonical maintainer account received a temporary ruleset exception.
It was removed immediately after the push; independent readback confirms the
original active rules, conditions and enforcement with an empty bypass list.
An earlier preflight refused before mutation because the exact configured SSH
alias was absent from its allowlist; fresh SSH authentication verified the
canonical account before the corrected preflight proceeded.

Execution custody is `canonical-merge-identity-approved-execution.json` in the
release evidence directory. Both original source CI runs remain successful,
each with 11,665 tests passed. Canonical main CI `39009177640` is running;
full unfiltered benchmark is now running in the preserved proof checkout.
Signed-package qualification is still required. No identity
rule, historical cutoff or external contributor authorship was changed.
This narrow correction does not close CB-320 or grant release qualification.

## Fresh squash author refusal (2026-10-16)

Both PR #34 test runs passed on `4c42a04335907f5b7262f30027c19001981a25d4`,
each with 11,665 passed, 10 skipped and 12 warnings. The ordinary guarded
GitHub squash merge created `ff509ef985d932f9a0e6b4233c6cce03ee9e5997`.
The merge command returned HTTP 502 after acceptance; authenticated PR and
main readback confirmed the merge, so the command was not repeated.

GitHub selected the account display name for the maintainer author. The
unchanged history guard correctly rejects that fresh alias beyond the
historical cutoff. Local Git configuration and the authenticated account
were canonical; those checks do not control GitHub's squash author name.
The merged tree exactly matches the tested source tree, but this commit is
ineligible for release. No benchmark or package qualification has started.
Hosted main run `38894541984` confirms the same identity refusal; its dependent
test and Claude asset jobs were skipped. The original two successful branch
runs remain retained. The hosted failure log has SHA-256
`faf8c800c45e4df96c205945e0238fcc361f86675f05a6c50c2a96df034c2cd1`.

A replacement commit, `9d3674c0a4384e76279d42985c862eaa712046f7`, preserves
the exact tree, parent and message with canonical maintainer author and
committer fields. Its history check passes; the original check fails.
The commit object is prepared locally, with no repair ref or remote change.
Replacing the single published main commit requires explicit authorization
and an exact lease against the original commit. That approval is pending.
The original merge and refusal remain retained in
`canonical-H-checkout.json` and `canonical-merge-identity-repair-proposal.json`
in the release evidence directory.

Do not advance the historical cutoff, weaken the fresh-author rule or rewrite
external contributor authorship to admit this commit. Future maintainer
merges must verify the raw authored identity before publication rather than
assuming local Git identity determines a server-authored squash commit.

## Published history integration refusal (2026-10-10)

The push of `7752855fdfcd30a39a2cf59b02a089dab3ef875c` is refused by the
history guard because published main commit
`4a6c37a8633e1af50bb7898303edc23b41e65d74` retains the historical maintainer
name. This immutable August commit was outside the old trusted cutoff at
`fae446995e13e12409e50f944a336dbc846db90a`. Both newly authored commits use
the canonical identity; the refusal appears only after incorporating published
main ancestry. Rewriting the published commit would damage history.

Advance the exact immutable ancestry cutoff to that already published main
commit. Preserve the existing alias allowlist, raw-object inspection, assistant
attribution rejection and canonical identity requirement for every new commit.
All 43 identity tests pass, including bounded historical acceptance and rejection
of a fresh legacy alias after the cutoff. This changes no runtime or customer
data. The rejected push remains retained in the release integration evidence;
successful current-history validation and a normal guarded push are still required.

- Status: Open

- Created: 2026-08-04

- Severity: P1

- Reproducibility: Always

- Type: CI

- Description: The history identity validator required every reachable commit to use the freedom-research maintainer identity. Legitimate commits from external human contributors therefore failed pull-request CI, and the written policy encouraged rewriting immutable contributor authorship instead of preserving credit.

- Impact: External contributors cannot pass the identity job or retain authorship under the documented merge policy.

- Components Affected: release

- Environment(s): Odylith product-repo pull_request, release-candidate, and release workflows using scripts/validate_git_identity.py history

- Detected By: Adversarial review of external PR #32 followed by direct identity-validator reproduction

- Failure Signature: validate_git_identity.py history exits 1 for thejesh23-authored commits solely because the author is not freedom-research

- Trigger Path: python scripts/validate_git_identity.py history --repo-root . 94e1f5268668d63b25f6fc11bf970030854faa27

- Ownership: Release identity validation and repository contributor policy

- Timeline: Captured 2026-08-04 through `odylith bug capture`.

- Blast Radius: All external human contributors, pull-request identity CI, and maintainer merge decisions

- SLO/SLA Impact: Blocks external contribution delivery and forces unnecessary maintainer-only commit rewriting

- Data Risk: No product data loss; immutable authorship and attribution integrity are at risk

- Security/Compliance: Maintainer credential controls remain necessary, but conflating them with contributor authorship creates governance and attribution risk

- Invariant Violated: External human contributors retain original Git authorship while maintainer credentials and assistant-attribution safeguards remain pinned

- Root Cause: Canonical maintainer identity was incorrectly applied to every commit author instead of only maintainer credentials, maintainer-authored commits, and repository-owned metadata

- Solution: Allow external human authors in history validation, require exact canonical maintainer aliases when used, and continue rejecting assistant/model/tool identities and attribution

- Rollback/Forward Fix: Forward fix on the active v0.1.15 release branch

- Verification: Identity unit suite passes; external PR head passes history validation; canonical maintainer config remains strict; guidance/install parity tests pass

- Prevention: Keep external-human acceptance and assistant-attribution rejection as explicit regression cases

- Agent Guardrails: Never rewrite legitimate external Git authorship to the maintainer identity; separate maintainer credential proof from contribution-history safety

- Preflight Checks: Read CB-070, AGENTS.md, CLAUDE.md, CONTRIBUTING.md, the identity validator, its tests, and all workflow callers together

- Regression Tests Added: tests/unit/test_validate_git_identity.py covers external humans, partial maintainer aliases, assistant identities, human co-authors, and assistant attribution

- Monitoring Updates: The existing pull_request and release identity jobs exercise the revised shared validator

- Version/Build: 2026/freedom/v0.1.15

- Related Incidents/Bugs: CB-070

- Code References: - scripts/validate_git_identity.py
- tests/unit/test_validate_git_identity.py
- src/odylith/install/agents.py

- Runbook References: - AGENTS.md
- CONTRIBUTING.md

- Fix Commit/PR: current branch 2026/freedom/v0.1.15
