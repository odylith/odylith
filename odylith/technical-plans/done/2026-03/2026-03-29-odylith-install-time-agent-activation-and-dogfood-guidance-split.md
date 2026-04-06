Status: Done

Created: 2026-03-29

Updated: 2026-03-29

Backlog: B-016

Goal: Make install activate Odylith-first agent guidance and skills correctly in
consumer repos while keeping maintainer-only guidance scoped to dogfood/product
repo use.

Assumptions:
- The consumer guidance and skills content was already strong enough; the main
  gap was install-time activation and syncing.
- Product-repo dogfood needs a maintainer overlay, not a second consumer
  contract.
- The managed repo-root `AGENTS.md` block is the right place to activate
  Odylith-first behavior without taking over unrelated repo-root guidance.

Constraints:
- Do not leak maintainer-only release-process guidance into consumer installs.
- Do not overwrite source-owned `odylith/AGENTS.md` inside the product repo.
- Keep the install contract aligned with the real Codex-only native spawn
  boundary.

Reversibility: Reverting this slice restores the prior install bootstrap and
repo-root AGENTS injection without requiring data migration.

Boundary Conditions:
- Scope included install/bootstrap/repair synchronization, repo-root AGENTS
  injection, consumer `odylith/AGENTS.md`, and install validation.
- Scope excluded broader content rewrites for consumer guidance and maintainer
  release process.

Related Bugs:
- no related bug found

## Context/Problem Statement
- [x] Consumer install did not yet activate Odylith strongly enough in the
  repo-root `AGENTS.md`.
- [x] Consumer bootstrap did not guarantee sync of `odylith/skills/`.
- [x] Dogfood activation needed a clean maintainer overlay without copying that
  overlay into consumer repos.
- [x] Install/repair tests did not yet prove the full consumer-versus-product
  guidance split.

## Success Criteria
- [x] Repo-root `AGENTS.md` gets a stronger managed Odylith activation block at
  install time.
- [x] Consumer installs sync `odylith/skills/` alongside
  `odylith/agents-guidelines/`.
- [x] Consumer-installed `odylith/AGENTS.md` reflects the full consumer
  contract.
- [x] Product-repo install/repair paths keep maintainer-only guidance scoped to
  `odylith/maintainer/`.
- [x] Unit and integration install tests prove the contract end to end.

## Non-Goals
- [x] Claude Code native subagent spawn enablement.
- [x] New maintainer content beyond activation/scope.
- [x] General onboarding redesign.

## Impacted Areas
- [x] [agents.py](/Users/freedom/code/odylith/src/odylith/install/agents.py)
- [x] [manager.py](/Users/freedom/code/odylith/src/odylith/install/manager.py)
- [x] [cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)
- [x] [AGENTS.md](/Users/freedom/code/odylith/odylith/AGENTS.md)
- [x] [AGENTS.md](/Users/freedom/code/odylith/src/odylith/bundle/assets/odylith/AGENTS.md)
- [x] [test_agents.py](/Users/freedom/code/odylith/tests/unit/install/test_agents.py)
- [x] [test_manager.py](/Users/freedom/code/odylith/tests/integration/install/test_manager.py)
- [x] [simulator.py](/Users/freedom/code/odylith/tests/integration/install/simulator.py)
- [x] [test_cli.py](/Users/freedom/code/odylith/tests/unit/test_cli.py)

## Risks & Mitigations

- [x] Risk: product-repo bootstrap overwrites source-owned guidance files.
  - [x] Mitigation: consumer-only managed guidance refresh, plus product-repo
    integration coverage.
- [x] Risk: consumer installs pick up maintainer-only content.
  - [x] Mitigation: sync only consumer-safe bundle trees and assert the
    maintainer overlay stays repo-root-only in product-repo tests.
- [x] Risk: install copy promises more activation than the synced files
  - [ ] Mitigation: TODO (add explicit mitigation).
  actually provide.
- [ ] Risk: Unspecified risk (legacy backfill).
  - [x] Mitigation: assert on installed file contents and CLI output directly.

## Validation/Test Plan
- [x] `python -m py_compile src/odylith/install/agents.py src/odylith/install/manager.py src/odylith/cli.py tests/unit/install/test_agents.py tests/integration/install/test_manager.py tests/integration/install/simulator.py tests/unit/test_cli.py`
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/unit/install/test_agents.py tests/integration/install/test_manager.py tests/unit/test_cli.py`
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/unit/install/test_repair.py tests/integration/install/test_lifecycle_simulator.py`
- [x] `git diff --check`

## Rollout/Communication
- [x] Keep the public consumer contract Codex-first but Claude-safe.
- [x] Keep maintainer-only activation inside `odylith/maintainer/`.
- [x] Update backlog and plan indexes when the slice closes.

## Current Outcome
- Consumer install now refreshes a stronger repo-root AGENTS activation block
  and the consumer `odylith/AGENTS.md`, `odylith/agents-guidelines/`, and
  `odylith/skills/` operating layer together.
- Consumer upgrade now resyncs managed guidance and skills instead of leaving
  stale local guidance behind.
- Product-repo dogfood preserves source-owned Odylith guidance and only adds the
  repo-root maintainer overlay that points release work at
  `odylith/maintainer/AGENTS.md`.
- Coverage now proves the consumer-versus-product split across install, upgrade,
  repair, and lifecycle simulation.
