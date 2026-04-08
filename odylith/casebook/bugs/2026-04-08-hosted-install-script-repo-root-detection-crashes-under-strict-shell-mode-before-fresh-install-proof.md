- Bug ID: CB-075

- Status: Closed

- Created: 2026-04-08

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: Canonical `v0.1.10` release candidate proof still failed after
  the hosted installer switched off the hidden `--align-pin` flag because the
  generated `install.sh` crashed during repo-root detection on a fresh nested
  workspace before it could climb to the repo's ancestor `AGENTS.md`. Under
  `set -u`, the script tested `git_candidate` before initializing it and
  aborted before the first-install smoke could even materialize the repo-local
  runtime.

- Impact: Canonical release-candidate proof could not complete the hosted
  fresh-install smoke, so the release lane still blocked before dispatch even
  after the earlier cross-version command compatibility fix landed.

- Components Affected: release asset publisher, generated `install.sh`,
  repo-root detection in strict shell mode, local release smoke harness,
  release component contract.

- Environment(s): Odylith product repo maintainer mode, canonical `main`,
  GitHub-hosted `release-candidate` workflow on Ubuntu 24.04, local hosted
  release smoke during `make release-preflight VERSION=0.1.10`.

- Root Cause: The hosted installer template runs in strict shell mode
  (`set -euo pipefail`) and its `detect_repo_root()` helper declared
  `git_candidate` as a local variable without assigning it. On a first-install
  smoke repo launched from a nested workspace, the first iteration had neither
  an `AGENTS.md` nor `.git` in the current candidate directory yet, so the
  later `[[ -z "$git_candidate" ... ]]` test raised an unbound-variable error
  before the helper could continue climbing toward the ancestor repo root.

- Solution: Keep the repo-root detection helper strict-mode safe by
  initializing optional shell locals before guard checks. Regression proof now
  exercises the generated installer in the nested fresh-install shape that
  originally tripped the GitHub-hosted candidate-proof lane.

- Verification: `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_release_bootstrap.py`;
  canonical `make release-preflight VERSION=0.1.10` after the template fix
  lands back on `main`.

- Prevention: Generated hosted installer shell helpers must be proved under the
  same strict shell mode they ship with, including nested first-install paths
  where optional locals remain unset until the helper climbs toward ancestor
  repo markers.

- Detected By: GitHub-hosted `release-candidate` workflow on 2026-04-08 after
  PR `#5` merged.

- Failure Signature: `/tmp/.../install.sh: line 58: git_candidate: unbound variable`
  while local release smoke ran `bash install.sh` from a nested fresh-install
  workspace.

- Trigger Path: Run canonical release candidate proof with the generated
  installer from a fresh nested folder before repo-root detection has climbed
  to the ancestor `AGENTS.md` or Git root.

- Ownership: Hosted installer publication flow, installer shell-template
  integrity, release smoke compatibility, release component contract.

- Timeline: surfaced immediately after the hidden-flag compatibility fix landed
  and the GitHub-hosted candidate-proof lane progressed into the fresh-install
  branch of local release smoke.

- Blast Radius: Canonical release-candidate proof, local release smoke, and
  trust in the hosted installer's ability to bootstrap a repo from a plain
  nested folder.

- SLO/SLA Impact: No customer outage; release-lane blocker in a P0 maintainer
  path.

- Data Risk: Low data risk, high release-operations risk.

- Security/Compliance: Low direct security risk; this is a strict-shell
  template correctness failure in release proof.

- Invariant Violated: Hosted installer shell helpers must stay strict-mode safe
  across `agents`, `git`, and plain `folder` repo-root detection branches.

- Workaround: None acceptable besides patching the installer template or
  weakening the fresh-install proof shape.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: When a generated hosted installer runs under
  `set -euo pipefail`, initialize every optional shell local before testing it
  and prove the nested first-install path in release smoke before relying on
  the template for canonical release proof.

- Preflight Checks: Inspect generated `install.sh` repo-root detection for
  strict-mode-safe variable initialization, then confirm fresh-install smoke
  still covers a nested folder before ancestor repo markers are discovered.

- Regression Tests Added: Generated install-script contract coverage now proves
  strict-mode-safe repo-root detection for the nested first-install path.

- Monitoring Updates: Treat future `unbound variable` failures in hosted
  installer proof as template regressions before blaming downstream repo state.

- Related Incidents/Bugs:
  [2026-04-08-hosted-install-script-uses-hidden-pin-alignment-flag-that-older-shipped-runtimes-do-not-understand.md](2026-04-08-hosted-install-script-uses-hidden-pin-alignment-flag-that-older-shipped-runtimes-do-not-understand.md)

- Version/Build: canonical `main` at `v0.1.10` preflight, before dispatch.

- Customer Comms: internal maintainer-only release-lane hosted-installer
  strict-mode fix.

- Code References: release asset publisher, generated `install.sh`, local
  release smoke harness, `tests/unit/install/test_release_bootstrap.py`

- Runbook References: `odylith/MAINTAINER_RELEASE_RUNBOOK.md`,
  `odylith/registry/source/components/release/CURRENT_SPEC.md`

- Fix Commit/PR: current branch `2026/freedom/v0.1.10-install-script-repo-root-guard`,
  pending commit/push.
