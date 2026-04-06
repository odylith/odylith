- Bug ID: CB-022

- Status: Closed

- Created: 2026-03-29

- Fixed: 2026-03-29

- Severity: P0

- Reproducibility: Consistent

- Type: Product

- Description: Odylith's canonical maintainer release lane could consume patch
  versions without ever publishing them. If `make release-preflight` reserved a
  tag like `v0.1.3` and the attempt never reached a real GitHub release,
  subsequent retries still treated that unpublished tag as the "highest
  release" and advanced to `v0.1.4`, `v0.1.5`, and beyond.

- Impact: Maintainers lost the truthful next GA version, release/session output
  became misleading, and the product repo could drift its source version floor
  ahead of any real published release. That weakens confidence in the canonical
  release contract and makes rollback/support history harder to reason about.

- Components Affected: release semver resolution helpers, release session
  state helpers, maintainer release-version preview/show commands, release
  session contract, release component spec and runbook.

- Environment(s): Odylith product repo maintainer release lane using
  `make release-version-preview`, `make release-version-show`, and
  `make release-preflight`.

- Root Cause: Auto-version resolution anchored on the highest existing stable
  semver tag instead of the highest published GitHub release. On retry, the
  session initializer also skipped an already-existing chosen tag instead of
  reusing that same unpublished reservation or rebinding it to the current
  release commit.

- Solution: Anchor auto-version progression on the highest published canonical
  GitHub release, not the highest raw tag. If the chosen tag already exists but
  has no published GitHub release, reuse that same version; if it points at an
  older retry commit, safely rebind the unpublished tag to the current `HEAD`
  before dispatch. Surface the published-vs-tag distinction in
  `release-version-show`.

- Verification: `PYTHONPATH=src python -m pytest -q
  tests/unit/install/test_release_version_session.py` passed; the added tests
  prove unpublished-tag reuse, rebinding on retry after a fix, and
  published-release anchoring in the maintainer state readout. `make
  release-session-clear`, `make release-version-show`, and
  `make release-version-preview` now resolve the next automatic GA candidate
  back to `v0.1.3` even though raw local tags run through `v0.1.5`.

- Prevention: Canonical release versioning must distinguish "tag exists" from
  "release exists". Unpublished tags are reservations, not completed releases,
  and the maintainer surface must show both views explicitly.

- Detected By: maintainer review of skipped `v0.1.3` / `v0.1.4` / `v0.1.5`
  tags against the actual published GitHub releases, plus direct user report.

- Failure Signature: `odylith upgrade`/docs/source truth moved toward `0.1.5`
  while GitHub still showed `v0.1.2` as latest, and plain release retries kept
  proposing the next higher patch instead of the same unpublished candidate.

- Trigger Path: reserve a canonical patch tag during preflight, fail or abandon
  the lane before release publication, then rerun `make release-preflight` or
  inspect `make release-version-show`.

- Ownership: release semver resolution, release session initialization, and
  maintainer release truth presentation.

- Timeline: reproduced and repaired on 2026-03-29 after the maintainer release
  lane had already burned unpublished `v0.1.3` / `v0.1.4` / `v0.1.5` tags.

- Blast Radius: product maintainers, release notes/version truth, upgrade
  expectations, and any downstream trust in Odylith's canonical GA history.

- SLO/SLA Impact: no user-runtime outage, but severe release-governance and
  product-version trust degradation.

- Data Risk: medium. The bug can push repo source truth and session state ahead
  of actual published releases, which is a correctness problem for operators.

- Security/Compliance: no direct security exploit, but release provenance and
  signed-publication history become less trustworthy when tags are consumed
  without releases.

- Invariant Violated: a failed or incomplete release attempt must not consume a
  new canonical patch version. The same unpublished candidate must be reused
  until a real release exists.

- Workaround: before the fix, maintainers had to manually reason about GitHub
  releases versus raw tags and reset source version truth by hand.

- Rollback/Forward Fix: Forward fix. Reverting this slice reintroduces skipped
  patch versions and misleading maintainer state output.

- Agent Guardrails: Never treat an unpublished tag as a completed release. Do
  not "solve" a failed release by silently burning the next patch version.

- Preflight Checks: inspect this bug, `make release-version-show`,
  `make release-version-preview`, the Release component spec, and
  [tests/unit/install/test_release_version_session.py](../../../tests/unit/install/test_release_version_session.py)
  before changing release version/session behavior again.

- Regression Tests Added:
  `test_release_session_auto_tag_reuses_same_unpublished_tag_on_retry`,
  `test_release_session_rebinds_unpublished_tag_to_current_head_on_retry_after_fix`,
  and `test_show_release_version_state_prefers_highest_published_release_over_higher_unpublished_tags`.

- Monitoring Updates: maintainer release-version state now reports both highest
  published release and highest raw semver tag so drift is visible immediately.

- Related Incidents/Bugs: no direct predecessor bug captured; this emerged from
  the current canonical release lane itself.

- Version/Build: workspace state on 2026-03-29 before published-release
  anchoring and unpublished-tag reuse hardening.

- Config/Flags: canonical maintainer release lane, `origin` remote, sticky
  release session file, optional explicit `VERSION=X.Y.Z`.

- Customer Comms: tell maintainers Odylith now reuses the same unpublished
  release candidate instead of silently skipping to a new patch version. If a
  release never completed, the truthful next GA tag stays the same.

- Code References: release semver resolution helpers, release session state
  helpers, `tests/unit/install/test_release_version_session.py`,
  `odylith/registry/source/components/release/CURRENT_SPEC.md`,
  `odylith/MAINTAINER_RELEASE_RUNBOOK.md`

- Runbook References: `odylith/MAINTAINER_RELEASE_RUNBOOK.md`

- Fix Commit/PR: `B-026` closed on 2026-03-29 after published-release anchoring
  and unpublished-tag reuse landed together.
