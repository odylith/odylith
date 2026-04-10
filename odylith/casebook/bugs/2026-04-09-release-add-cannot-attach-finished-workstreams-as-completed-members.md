- Bug ID: CB-082

- Status: Closed

- Created: 2026-04-09

- Severity: P2

- Reproducibility: High

- Type: Product

- Description: `odylith release add` rejected already `finished`
  workstreams, even though active release read models already know how to
  surface finished members as completed release history after an add/remove
  sequence. That made it impossible to repair missing release membership for a
  finished workstream such as `B-066` without bypassing the governed authoring
  path.

- Impact: Maintainers could not attach a finished workstream to the current
  release after the fact, so release membership truth could remain incomplete
  even when the UI and read model contract expected that workstream to appear
  under completed members.

- Components Affected: `src/odylith/runtime/governance/release_planning_authoring.py`,
  `src/odylith/runtime/governance/release_planning_view_model.py`,
  release-planning CLI authoring, current-release completed-membership views.

- Environment(s): Maintainer release-planning lane in the Odylith product repo.

- Root Cause: The release-planning validator correctly forbade a finished
  workstream from remaining an active release target, but the authoring path
  only knew how to emit a single `add` event. There was no supported way to
  record completed release membership for an already finished workstream.

- Solution: Teach `odylith release add` to emit an immediate `add` plus
  `remove` pair when the target workstream is already `finished`, and reject
  duplicate completed-member additions for the same release.

- Verification: `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_release_planning.py`
  passed (`9 passed`). `PYTHONPATH=src python3 -m odylith.cli release add --repo-root . B-066 current --json`
  succeeded and recorded paired `add`/`remove` history. `PYTHONPATH=src python3 -m odylith.cli release show --repo-root . --json current`
  now shows `B-066` under `completed_workstreams`.

- Prevention: Release authoring must support the same completed-membership
  semantics that governed read models already surface, instead of forcing
  maintainers to choose between incorrect active targeting and missing release
  history.

- Detected By: Maintainer request to assign `B-066` to the current release on
  2026-04-09.

- Failure Signature: `PYTHONPATH=src python3 -m odylith.cli release add --repo-root . B-066 current --dry-run --json`
  failed with `` `B-066` with status `finished` cannot target active release `release-0-1-11` ``.

- Trigger Path: 1. Finish a workstream. 2. Discover that the current release
  is missing that workstream under completed members. 3. Try to attach it with
  `odylith release add`.

- Ownership: Release-planning authoring contract.

- Invariant Violated: A finished workstream must be attachable to a live
  release as completed history without becoming an active target again.

- Workaround: Manually append paired add/remove release-assignment events in
  tracked truth. That was not an acceptable default operator contract.

- Rollback/Forward Fix: Forward fix.

- Regression Tests Added: `tests/unit/runtime/test_release_planning.py`

- Monitoring Updates: Watch for any `release add` attempt on a finished
  workstream that fails instead of producing completed release membership.

- Residual Risk: Low. The remaining release-membership risk is stale read
  surfaces, which is already covered by `CB-081`.

- Related Incidents/Bugs:
  [2026-04-09-compass-release-targets-can-pin-closed-workstreams-until-runtime-refresh.md](2026-04-09-compass-release-targets-can-pin-closed-workstreams-until-runtime-refresh.md)

- Version/Build: Odylith product repo working tree on 2026-04-09.

- Code References: `src/odylith/runtime/governance/release_planning_authoring.py`,
  `tests/unit/runtime/test_release_planning.py`
