---
status: implementation
idea_id: B-083
title: Claude Guidance Surface Parity and Install Contract Support
date: 2026-04-10
priority: P0
commercial_value: 5
product_impact: 5
market_value: 4
impacted_parts: repo-root guidance detection, install and repair flows, root guidance toggles, managed consumer bootstrap files, benchmark workspace guidance handling, runtime guidance heuristics, and Claude-facing docs plus tests
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: Odylith already claims Claude Code support, but too much of the product still treats AGENTS-only guidance as the install and runtime contract. Until repo-root detection, managed bootstrap guidance, and shared runtime heuristics treat `CLAUDE.md` as a first-class companion surface, Claude support stays interpretive instead of dependable.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-10-claude-guidance-surface-parity-and-install-contract-support.md
execution_model: standard
workstream_type: umbrella
workstream_parent:
workstream_children: B-084
workstream_depends_on: B-069
workstream_blocks:
related_diagram_ids: D-019,D-020,D-023,D-033,D-034,D-035
workstream_reopens:
workstream_reopened_by:
workstream_split_from:
workstream_split_into:
workstream_merged_into:
workstream_merged_from:
supersedes:
superseded_by:
---

## Problem
Odylith's shared product contract now talks honestly about Codex and Claude
Code, but the install and runtime guidance surface still assumes `AGENTS.md`
is the only durable repo instruction entrypoint. Repo-root detection, managed
bootstrap writes, dirty-path reasoning, workstream inference, benchmark
workspace handling, and several hot-path heuristics still special-case
`AGENTS.md` while treating `CLAUDE.md` as incidental or invisible.

That means Claude compatibility depends on maintainers remembering to add
manual shims instead of the product carrying that contract itself.

## Customer
- Primary: operators who use Odylith through Claude Code and need the same
  first-run guidance contract that Codex already gets automatically.
- Secondary: maintainers who need install, repair, benchmark, and runtime
  heuristics to describe one truthful host contract instead of a Codex-first
  default with Claude exceptions layered on top.

## Opportunity
Make `CLAUDE.md` a first-class managed companion surface: root detection can
bootstrap from it, install and repair flows can materialize it, runtime
heuristics can classify it as guidance, and the shipped `odylith/` tree can
present the same scoped contract naturally to Claude Code.

## Proposed Solution
- accept either `AGENTS.md` or `CLAUDE.md` as the repo-root guidance marker
- always materialize a repo-root `CLAUDE.md` companion when Odylith installs
  or repairs guidance
- ship a managed `odylith/CLAUDE.md` companion in the product repo and bundle
- update shared runtime heuristics so `CLAUDE.md` participates anywhere
  guidance files currently influence routing, dirty-overlap summaries,
  benchmark isolation, or workstream inference
- update the public and install-facing docs and tests so Claude support is
  product truth instead of a manual aftercare step

## Scope
- repo-root guidance creation, detection, and toggle flows
- consumer bootstrap guidance materialization under `odylith/`
- runtime heuristics that classify or preserve repo guidance files
- install script repo-root detection contract
- Claude-facing docs and validation coverage

## Non-Goals
- claiming Claude-native native-spawn parity before it is proven
- publishing Claude-host benchmark proof without a fresh matched-host run
- replacing `AGENTS.md` as the canonical cross-host repo contract

## Risks
- partial path coverage could leave some runtime heuristics treating
  `CLAUDE.md` as ordinary docs instead of governed guidance
- install or repair could become more invasive if the Claude companion file is
  not clearly scoped as a managed Odylith surface
- docs could overstate support if capability limits and proof limits are not
  kept explicit

## Dependencies
- `B-069` already separated the shared host contract from Codex-only canon and
  provides the truthful baseline this Claude support push extends

## Success Metrics
- a repo with only root `CLAUDE.md` can still be detected and bootstrapped
  correctly
- install, reinstall, upgrade refresh, and repair materialize both root
  `CLAUDE.md` and `odylith/CLAUDE.md` companion surfaces
- shared runtime heuristics treat `CLAUDE.md` as guidance wherever guidance
  drives routing or benchmark isolation behavior
- docs and tests describe Claude as a first-class supported host while keeping
  native-spawn and benchmark-proof limits explicit

## Validation
- `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_agents.py tests/unit/install/test_release_bootstrap.py tests/unit/install/test_manager.py tests/integration/install/test_bundle.py tests/integration/install/test_manager.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_workstream_inference.py tests/unit/runtime/test_tooling_context_routing.py tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_live_execution.py tests/unit/runtime/test_hygiene.py`
- `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone`
- `git diff --check`

## Rollout
Land the repo-root and bundled Claude companion files first, then widen the
install/runtime heuristics and finish by refreshing docs plus validation
coverage.

## Why Now
Claude support is already part of the product claim. The contract has to be
first-class in the product itself before more host-specific proof or transport
work is worth doing.

## Product View
Claude support should not depend on maintainers remembering to hand-place one
compatibility file after the fact.

## Impacted Components
- `odylith`
- `odylith-context-engine`
- `benchmark`

## Interface Changes
- repo-root bootstrap and detection now recognize `CLAUDE.md` as a guidance
  marker alongside `AGENTS.md`
- the managed `odylith/` tree now includes `CLAUDE.md` as a first-class
  companion guidance file

## Migration/Compatibility
- additive: `AGENTS.md` remains canonical and existing installs stay valid
- consumer repos that upgrade or repair receive the new Claude companion
  surfaces without changing their repo-owned truth model

## Test Strategy
- add direct installer and release-bootstrap coverage for Claude-only repo
  roots
- extend runtime and benchmark tests anywhere repo guidance paths are treated
  specially
- keep strict sync and diff checks at closeout

## Open Questions
- whether maintained subtree-specific `CLAUDE.md` companions beyond
  `odylith/CLAUDE.md` are worth adding after the root and Odylith-root contract
  proves stable
