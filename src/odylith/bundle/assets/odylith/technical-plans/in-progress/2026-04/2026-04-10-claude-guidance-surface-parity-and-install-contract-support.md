Status: In progress

Created: 2026-04-10

Updated: 2026-04-10

Backlog: B-083

Goal: Make Claude Code a first-class supported Odylith host by treating
`CLAUDE.md` as a managed companion guidance surface across repo-root
detection, install and repair flows, the shipped `odylith/` tree, and shared
runtime heuristics, while keeping native-spawn and benchmark-proof limits
truthful.

Assumptions:
- `AGENTS.md` remains the canonical cross-host contract, with `CLAUDE.md` as a
  Claude-native companion entrypoint into the same policy.
- Claude support must become product truth in install and runtime behavior,
  not just copy in the README.
- Native spawn and benchmark proof stay host-scoped and must not be overclaimed
  during this guidance-surface push.

Constraints:
- Do not replace or weaken the existing `AGENTS.md` contract.
- Keep install and repair additive: create or refresh managed Claude companion
  files without turning repo-owned guidance into product-owned content.
- Do not claim Claude-native delegation parity or fresh Claude benchmark proof
  unless the repo gains explicit measured evidence in a later slice.

Reversibility: This work is additive. If the Claude companion contract proves
too aggressive, the rollback path is to stop materializing the extra
`CLAUDE.md` files while leaving the existing `AGENTS.md`-based product
contract intact.

Boundary Conditions:
- Scope includes repo-root guidance creation and detection, `on` and `off`
  install toggles, consumer bootstrap materialization under `odylith/`,
  shared runtime heuristics that special-case guidance files, benchmark
  workspace guidance handling, and the matching docs plus tests.
- Scope excludes Claude-native native spawn enablement, fresh Claude benchmark
  publication, and bundle-wide subtree shims beyond the Odylith-root
  companion unless the base contract proves insufficient.

Related Bugs:
- [CB-084](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-09-host-contract-drift-leaks-codex-only-policy-into-claude-and-shared-runtime-surfaces.md)

## Learnings
- [ ] Claude support is not real if repo-root detection and install repair
      still ignore the host's native instruction surface.
- [ ] Keeping `AGENTS.md` canonical and `CLAUDE.md` companion is cleaner than
      forking the repo contract into two divergent truths.

## Must-Ship
- [ ] Bind this plan to `B-083` and keep the cross-host scope honest against
      `B-069`.
- [ ] Add a repo-root `CLAUDE.md` companion contract to managed install flows.
- [ ] Add a managed `odylith/CLAUDE.md` companion file in the source tree and
      shipped bundle.
- [ ] Accept `CLAUDE.md` as a repo-root guidance marker in install and runtime
      detection.
- [ ] Extend guidance-sensitive runtime heuristics and benchmark handling to
      treat `CLAUDE.md` as a first-class guidance surface.

## Should-Ship
- [ ] Refresh the public install and repo-integration docs so Claude guidance
      parity is stated explicitly.
- [ ] Add focused installer, runtime, and benchmark tests that cover
      Claude-only repo roots and Claude companion files.

## Defer
- [ ] Claude-native native-spawn transport work.
- [ ] Fresh Claude-host benchmark proof publication.
- [ ] Additional subtree-level `CLAUDE.md` companions beyond the Odylith root
      unless the base contract proves insufficient.

## Success Criteria
- [ ] Install and repair can bootstrap from `CLAUDE.md` and materialize the
      Claude companion files automatically.
- [ ] Shared runtime heuristics no longer treat `CLAUDE.md` as invisible or
      ordinary documentation.
- [ ] Product docs and tests describe one truthful Claude support contract
      without inventing unsupported capabilities.

## Non-Goals
- [ ] Replacing `AGENTS.md` as the canonical Odylith repo contract.
- [ ] Claiming benchmark or native-spawn parity that the product has not yet
      proved.

## Impacted Areas
- [ ] [2026-04-10-claude-guidance-surface-parity-and-install-contract-support.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-10-claude-guidance-surface-parity-and-install-contract-support.md)
- [ ] [2026-04-10-claude-guidance-surface-parity-and-install-contract-support.md](/Users/freedom/code/odylith/odylith/technical-plans/in-progress/2026-04/2026-04-10-claude-guidance-surface-parity-and-install-contract-support.md)
- [ ] [AGENTS.md](/Users/freedom/code/odylith/AGENTS.md)
- [ ] [CLAUDE.md](/Users/freedom/code/odylith/CLAUDE.md)
- [ ] [README.md](/Users/freedom/code/odylith/README.md)
- [ ] [odylith/README.md](/Users/freedom/code/odylith/odylith/README.md)
- [ ] [odylith/CLAUDE.md](/Users/freedom/code/odylith/odylith/CLAUDE.md)
- [ ] [docs/specs/odylith-repo-integration-contract.md](/Users/freedom/code/odylith/docs/specs/odylith-repo-integration-contract.md)
- [ ] [src/odylith/install/agents.py](/Users/freedom/code/odylith/src/odylith/install/agents.py)
- [ ] [src/odylith/install/manager.py](/Users/freedom/code/odylith/src/odylith/install/manager.py)
- [ ] [scripts/release/publish_release_assets.py](/Users/freedom/code/odylith/scripts/release/publish_release_assets.py)
- [ ] [src/odylith/runtime/common/consumer_profile.py](/Users/freedom/code/odylith/src/odylith/runtime/common/consumer_profile.py)
- [ ] [src/odylith/runtime/common/dirty_overlap.py](/Users/freedom/code/odylith/src/odylith/runtime/common/dirty_overlap.py)
- [ ] [src/odylith/runtime/governance/workstream_inference.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/workstream_inference.py)
- [ ] [src/odylith/runtime/evaluation/odylith_benchmark_runner.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_runner.py)
- [ ] [tests/unit/install/test_release_bootstrap.py](/Users/freedom/code/odylith/tests/unit/install/test_release_bootstrap.py)
- [ ] [tests/integration/install/test_bundle.py](/Users/freedom/code/odylith/tests/integration/install/test_bundle.py)

## Rollout
1. Add the governed workstream and plan for the Claude support push.
2. Land the root and bundled Claude companion files plus install detection.
3. Extend runtime guidance heuristics and benchmark handling.
4. Refresh docs, run focused validation, and sync the governed surfaces.

## Validation
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_agents.py tests/unit/install/test_release_bootstrap.py tests/unit/install/test_manager.py tests/integration/install/test_bundle.py tests/integration/install/test_manager.py`
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_workstream_inference.py tests/unit/runtime/test_tooling_context_routing.py tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_live_execution.py tests/unit/runtime/test_hygiene.py`
- [ ] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone`
- [ ] `git diff --check`

## Outcome Snapshot
- [ ] Claude support no longer depends on manually adding one root compatibility
      file outside the product contract.
- [ ] Install, repair, runtime heuristics, and the shipped `odylith/` tree all
      recognize the Claude guidance surface explicitly.
- [ ] Capability claims remain honest: guidance parity lands here, while
      native spawn and benchmark proof stay deferred until measured.
