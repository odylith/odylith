Status: Done

Created: 2026-03-29

Updated: 2026-03-29

Backlog: B-024

Goal: Make Odylith's guidance, skills, bundle, and install-managed activation
encode the always-on governance-autopilot loop so agents search, extend,
create, capture, and sync backlog, Registry, Atlas, Casebook, Compass, and
session context by default.

Assumptions:
- Odylith already has most of the underlying governance surfaces and memory
  substrate; the gap is mostly contract clarity and install-time activation.
- The strongest near-term product change is to make the desired bookkeeping
  loop explicit and pre-baked instead of expecting operators or agents to infer
  it.

Constraints:
- Keep the contract fail-closed; do not encourage duplicate workstreams,
  speculative bug spam, or low-signal governance churn.
- Keep bundled consumer guidance and install-managed text aligned with the
  source-owned product guidance.
- Do not introduce maintainer-only release-process guidance into consumer
  installs.

Reversibility: Reverting this slice restores the prior guidance, skill, and
install activation wording without any data migration.

Boundary Conditions:
- Scope includes shared guidance, shared skills, bundled consumer assets,
  install-managed guidance strings, and focused install tests.
- Scope excludes runtime schema changes, hosted memory changes, and new
  approval-bypassing automation behavior.

Related Bugs:
- no related bug found

## Context/Problem Statement
- [x] Shared guidance still leaves too much of Odylith's bookkeeping loop
      implicit.
- [x] Shared skills do not yet encode the full always-on search, extend,
      suggest, create, capture, and sync workflow.
- [x] Fresh consumer installs still inject older managed guidance text instead
      of the stronger autopilot contract.

## Success Criteria
- [x] Shared guidance across all lanes explicitly treats backlog, plan,
      component, Atlas, Casebook, Compass, and session upkeep as part of normal
      grounded work.
- [x] Shared skills encode the same governance-autopilot loop.
- [x] Install-managed consumer guidance ships the stronger contract by default.
- [x] Bundle assets mirror the source guidance and skill contract.
- [x] Focused install tests pass against the stronger wording.
- [x] Workstream and plan indexes reconcile cleanly at closeout.

## Non-Goals
- [x] Runtime packet-schema changes.
- [x] Hosted or provider-backed memory redesign.
- [x] Any approval-bypassing automation behavior.

## Impacted Areas
- [x] [AGENTS.md](/Users/freedom/code/odylith/odylith/AGENTS.md)
- [x] [README.md](/Users/freedom/code/odylith/odylith/README.md)
- [x] [OPERATING_MODEL.md](/Users/freedom/code/odylith/odylith/OPERATING_MODEL.md)
- [x] [DELIVERY_AND_GOVERNANCE_SURFACES.md](/Users/freedom/code/odylith/odylith/agents-guidelines/DELIVERY_AND_GOVERNANCE_SURFACES.md)
- [x] [ODYLITH_CONTEXT_ENGINE.md](/Users/freedom/code/odylith/odylith/agents-guidelines/ODYLITH_CONTEXT_ENGINE.md)
- [x] [AGENTS.md](/Users/freedom/code/odylith/odylith/maintainer/AGENTS.md)
- [x] [RELEASE_BENCHMARKS.md](/Users/freedom/code/odylith/odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md)
- [x] [SKILL.md](/Users/freedom/code/odylith/odylith/maintainer/skills/release-benchmark-publishing/SKILL.md)
- [x] [agent-contracts.md](/Users/freedom/code/odylith/docs/specs/agent-contracts.md)
- [x] [odylith-repo-integration-contract.md](/Users/freedom/code/odylith/docs/specs/odylith-repo-integration-contract.md)
- [x] [AGENTS.md](/Users/freedom/code/odylith/src/odylith/bundle/assets/odylith/AGENTS.md)
- [x] [SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-delivery-governance-surface-ops/SKILL.md)
- [x] [SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-casebook-bug-preflight/SKILL.md)
- [x] [SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-casebook-bug-capture/SKILL.md)
- [x] [SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-component-registry/SKILL.md)
- [x] [SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-diagram-catalog/SKILL.md)
- [x] [SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-session-context/SKILL.md)
- [x] [agents.py](/Users/freedom/code/odylith/src/odylith/install/agents.py)
- [x] [manager.py](/Users/freedom/code/odylith/src/odylith/install/manager.py)
- [x] [test_agents.py](/Users/freedom/code/odylith/tests/unit/install/test_agents.py)
- [x] [test_manager.py](/Users/freedom/code/odylith/tests/integration/install/test_manager.py)

## Risks & Mitigations

- [x] Risk: the stronger contract encourages noisy governance churn.
  - [x] Mitigation: keep the workflow grounded-first, duplicate-averse, and
        fail-closed on weak evidence.
- [x] Risk: install-managed strings drift from bundled consumer guidance.
  - [x] Mitigation: update source, bundle, and install-managed text in the same
        slice and keep focused install assertions on the key contract phrases.
- [x] Risk: the autopilot language sounds broad but remains too vague to use.
  - [x] Mitigation: spell out the exact backlog, component, Atlas, Casebook,
        Compass, and session steps in both the guidance and supporting skills.

## Validation/Test Plan
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/unit/install/test_agents.py tests/integration/install/test_manager.py`
- [x] `git diff --check`
- [x] `./.odylith/bin/odylith sync --repo-root . --check-only`

## Rollout/Communication
- [x] Consumer bundle and install-managed guidance ship the stronger contract.
- [x] Product guidance mirrors the same autopilot behavior for dogfood use.

## Current Outcome
- Shared guidance, maintainer guidance, developer/dogfood contracts, and shared
  skills now describe the same governance-autopilot loop explicitly: search
  existing governed truth first, extend or reopen it, create missing
  workstream-plus-plan records only when the slice is genuinely new, and keep
  Registry, Atlas, Casebook, Compass, and session context in-band.
- Fresh consumer installs now ship the stronger repo-root managed block and
  Odylith bootstrap guidance by default, so the contract is pre-baked instead
  of depending on operator memory.
- Focused install tests passed, `git diff --check` passed, and Odylith sync was
  refreshed plus rechecked cleanly after the release and benchmark component
  forensics sidecars were regenerated.
