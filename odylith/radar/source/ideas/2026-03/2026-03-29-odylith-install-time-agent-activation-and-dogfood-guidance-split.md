---
status: finished
idea_id: B-016
title: Install-Time Agent Activation and Dogfood Guidance Split
date: 2026-03-29
priority: P0
commercial_value: 5
product_impact: 5
market_value: 4
impacted_parts: consumer install bootstrap, repo-root AGENTS activation, consumer guidelines and skills sync, dogfood maintainer guidance activation, and install validation
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: Odylith already has the product guidance, skills, and routed spawn contract, but consumer installs still do not activate them strongly enough in the repo root and do not reliably sync the full skills payload. That makes the post-install agent posture weaker than the product contract. Fixing install-time activation should make Odylith feel materially more powerful immediately without changing the user’s base agent.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-03/2026-03-29-odylith-install-time-agent-activation-and-dogfood-guidance-split.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-005, B-015
workstream_blocks:
related_diagram_ids:
workstream_reopens:
workstream_reopened_by:
workstream_split_from:
workstream_split_into:
workstream_merged_into:
workstream_merged_from:
supersedes:
superseded_by: B-069
---

## Historical Note
This slice remains the factual record of the first install-time activation
hardening. Treat Codex-first activation language here as historical. `B-069`
now owns the current host-neutral install and guidance contract, including the
explicit separation between shared product behavior and host-specific
delegation transport.

## Problem
Odylith now has a strong consumer guidance and skills layer, but install still
undershoots the intended activation contract. Consumer repos do not yet get a
strong Odylith-first repo-root `AGENTS.md` block, the full consumer skills set
is not guaranteed to land with install, and dogfood activation still needs a
clean maintainer-only overlay without leaking release-process guidance into
consumer repos.

## Customer
- Primary: consumer repos that install Odylith and expect the local coding agent
  to start using Odylith heavily right away.
- Secondary: Odylith maintainers dogfooding the product in the product repo and
  needing maintainer-specific guidance without polluting the public consumer
  contract.

## Opportunity
If install makes Odylith the obvious local operating layer immediately, then
the first consumer session will start with the right guidance, the right
skills, and the right validated delegation posture already activated. That
should improve the practical product delta versus unguided coding-agent usage
without changing the underlying host.

## Proposed Solution
Strengthen install-time repo-root `AGENTS.md` injection, sync consumer-safe
Odylith guidelines and skills into the installed repo every time the managed
bootstrap runs, and preserve a clean product-repo path where dogfood activation
adds maintainer-specific overlays only inside the Odylith product boundary.

## Scope
- strengthen the managed repo-root `AGENTS.md` install block so Odylith-backed
  workflows and validated native-spawn posture are explicit
- sync consumer `odylith/skills/` during bootstrap, upgrade, and repair
- keep consumer-installed `odylith/AGENTS.md` aligned with the richer consumer
  contract
- preserve maintainer-only activation in the product repo via
  `odylith/maintainer/AGENTS.md`
- prove the contract with unit and integration install coverage

## Non-Goals
- enabling native spawn in Claude Code
- copying maintainer release-process guidance into consumer repos
- redesigning consumer guidance content outside the install activation path

## Risks
- making install rewrite product-repo guidance that should stay source-owned
- leaking maintainer-only skills or release notes into consumer repos
- claiming install-time activation that is not actually reflected in the synced
  files

## Dependencies
- `B-005` established the install/bootstrap contract Odylith must now enrich
- `B-015` tightened the consumer subagent and guidance contract install should
  now activate by default

## Success Metrics
- consumer installs leave behind a repo-root `AGENTS.md` block that explicitly
  defaults grounded work to Odylith guidance, skills, and validated
  native-spawn posture when allowed
- consumer installs sync consumer-safe `odylith/skills/` and
  `odylith/agents-guidelines/` reliably
- dogfood activation preserves maintainer-only guidance without leaking it into
  consumer installs
- install and repair validation passes with targeted coverage for both consumer
  and product-repo roles

## Validation
- `PYTHONPATH=src python -m pytest -q tests/unit/install/test_agents.py tests/integration/install/test_manager.py tests/unit/test_cli.py`

## Rollout
Ship as an install-contract tightening slice. Consumer installs should become
more opinionated about using Odylith immediately, while the product repo keeps
its maintainer-only overlay inside `odylith/maintainer/`.

## Why Now
The install path is the first product contact. If Odylith does not activate its
own guidance and spawn posture there, the product undersells itself before the
agent even starts working.

## Product View
Odylith should not require a second round of manual setup to feel powerful. The
install should leave the repo in the product's intended operating posture.

## Impacted Components
- `odylith`
- `odylith-context-engine`
- `subagent-orchestrator`
- `subagent-router`

## Interface Changes
- repo-root `AGENTS.md` now activates Odylith guidance more aggressively on
  install
- consumer installs now sync the full consumer-safe guidelines and skills set
- dogfood activation keeps maintainer-only guidance separate

## Migration/Compatibility
- compatible with existing installs through upgrade and repair
- no user content migration required
- maintainer-only guidance stays out of consumer repos

## Test Strategy
- add install-path coverage for consumer AGENTS activation
- add install-path coverage for consumer skill and guideline sync
- prove dogfood installs keep the maintainer overlay isolated

## Open Questions
- should install surface an even more explicit post-install note when native
  spawn is active on the current host but other hosts still remain local-only

## Outcome
- consumer installs now refresh repo-root AGENTS activation plus the consumer
  `odylith/AGENTS.md`, `odylith/agents-guidelines/`, and `odylith/skills/`
  operating layer together
- consumer upgrades now resync the managed guidance and skills set instead of
  leaving stale local guidance behind
- product-repo dogfood keeps its source-owned `odylith/` guidance tree and only
  gains the repo-root maintainer overlay
- install, upgrade, repair, and lifecycle tests now prove the consumer-versus-
  dogfood split directly
